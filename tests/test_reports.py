import json
import math
import re
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parent.parent

# 1. Verification of docker-compose.yml and seeds
def test_docker_compose_and_seeds():
    compose_path = ROOT_DIR / "docker-compose.yml"
    assert compose_path.exists(), "docker-compose.yml must exist at repo root"
    content = compose_path.read_text(encoding="utf-8")

    assert "api:" in content, "docker-compose.yml must define 'api' service"
    assert "ledger:" in content, "docker-compose.yml must define 'ledger' service"
    assert "8080" in content, "api service must publish or use port 8080"
    assert "pg_isready" in content, "ledger service healthcheck must use pg_isready"
    assert "/health" in content, "api healthcheck must curl /health"

    # Verify healthchecks contain interval, timeout, retries, start_period
    for field in ["interval:", "timeout:", "retries:", "start_period:"]:
        assert field in content, f"docker-compose healthchecks must specify {field}"

    seed_path = ROOT_DIR / "seeds" / "01_runs.sql"
    assert seed_path.exists(), "seeds/01_runs.sql must exist"
    seed_sql = seed_path.read_text(encoding="utf-8")
    assert "sbx-seeddemo1" in seed_sql, "Seed file must contain sbx-seeddemo1"
    assert "deleted" in seed_sql, "Seed row must have state 'deleted'"
    assert "celesto_sandbox" in seed_sql, "Seed row must specify execution_target 'celesto_sandbox'"
    assert "ON CONFLICT" in seed_sql.upper() or "PRIMARY KEY" in seed_sql.upper(), "Seed SQL must be idempotent"


# 2. Verification of .env.example and absence of .env
def test_env_example_and_no_live_env():
    env_example = ROOT_DIR / ".env.example"
    assert env_example.exists(), ".env.example must exist at repo root"
    env_text = env_example.read_text(encoding="utf-8")

    required_keys = [
        "CELESTO_PROVIDER",
        "CELESTO_API_KEY",
        "LLM_API_KEY",
        "LLM_MODEL",
        "DATABASE_URL",
        "API_PORT"
    ]
    for key in required_keys:
        assert key in env_text, f".env.example must define {key}"

    live_env = ROOT_DIR / ".env"
    assert not live_env.exists(), ".env must NOT be committed or present in root submission"


# 3. Verification of reports/problem.json
def test_problem_json():
    problem_file = ROOT_DIR / "reports" / "problem.json"
    assert problem_file.exists(), "reports/problem.json must exist"
    data = json.loads(problem_file.read_text(encoding="utf-8"))

    assert "who" in data and len(data["who"]) >= 40
    assert "agent_work" in data and len(data["agent_work"]) >= 40
    assert "proof_output" in data and len(data["proof_output"]) >= 20
    assert data.get("idea_source") in ["idea_bank", "original"]


# 4. Verification of logs/commands.jsonl
def test_commands_jsonl():
    log_file = ROOT_DIR / "logs" / "commands.jsonl"
    assert log_file.exists(), "logs/commands.jsonl must exist"
    lines = [l.strip() for l in log_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) >= 1, "logs/commands.jsonl must have at least one line"

    sandbox_re = re.compile(r"^sbx-[a-z0-9]{8,}$")
    for line in lines:
        obj = json.loads(line)
        assert "ts" in obj and isinstance(obj["ts"], str)
        assert sandbox_re.match(obj["sandbox_name"]), f"Invalid sandbox_name: {obj['sandbox_name']}"
        assert obj["command"] and isinstance(obj["command"], str)
        assert obj["decision"] in ["allow", "block"]
        assert obj["execution_target"] == "celesto_sandbox", f"execution_target must be celesto_sandbox: {line}"


# 5. Verification of reports/capabilities.json
def test_capabilities_json():
    cap_file = ROOT_DIR / "reports" / "capabilities.json"
    assert cap_file.exists(), "reports/capabilities.json must exist"
    data = json.loads(cap_file.read_text(encoding="utf-8"))
    caps = data.get("capabilities", [])
    assert len(caps) >= 2, "At least two capabilities must be documented"

    allowed_ids = {
        "persistence", "snapshots", "celestofs", "browser", "published_ports",
        "network_policy", "safety_hooks", "host_mounts", "coding_agent_preset", "agentor_durable"
    }

    seen_ids = set()
    for cap in caps:
        cap_id = cap.get("id")
        assert cap_id in allowed_ids, f"Invalid capability id: {cap_id}"
        assert cap_id not in seen_ids, f"Duplicate capability id: {cap_id}"
        seen_ids.add(cap_id)

        why = cap.get("why", "")
        assert len(why) >= 80, f"why must be at least 80 chars: {cap_id}"

        ev_path = cap.get("evidence_path", "")
        target_file = ROOT_DIR / ev_path
        assert target_file.exists(), f"evidence_path does not exist: {ev_path}"


# 6. Verification of reports/lifecycle.json
def test_lifecycle_json():
    lf_file = ROOT_DIR / "reports" / "lifecycle.json"
    assert lf_file.exists(), "reports/lifecycle.json must exist"
    data = json.loads(lf_file.read_text(encoding="utf-8"))

    assert data.get("cleanup_on_success") is True
    assert data.get("cleanup_on_failure") is True
    assert data.get("cleanup_on_interrupt") is True

    names = data.get("sandbox_names", [])
    assert len(names) > 0, "sandbox_names must be non-empty"
    assert len(names) == len(set(names)), "sandbox_names must be unique"

    sandbox_re = re.compile(r"^sbx-[a-z0-9]{8,}$")
    # Also load commands and reliability names to check appearance
    commands_log = ROOT_DIR / "logs" / "commands.jsonl"
    cmd_names = set()
    if commands_log.exists():
        for line in commands_log.read_text(encoding="utf-8").splitlines():
            if line.strip():
                cmd_names.add(json.loads(line).get("sandbox_name"))

    reliability_file = ROOT_DIR / "reports" / "reliability.json"
    rel_names = set()
    if reliability_file.exists():
        rel_data = json.loads(reliability_file.read_text(encoding="utf-8"))
        for r in rel_data.get("runs", []):
            rel_names.add(r.get("sandbox_name"))

    for name in names:
        assert sandbox_re.match(name), f"Invalid sandbox name: {name}"
        assert name in cmd_names or name in rel_names, f"Name {name} must appear in commands.jsonl or reliability.json"


# 7. Verification of reports/reliability.json and postmortem.md
def test_reliability_and_postmortem():
    rel_file = ROOT_DIR / "reports" / "reliability.json"
    assert rel_file.exists(), "reports/reliability.json must exist"
    data = json.loads(rel_file.read_text(encoding="utf-8"))

    runs = data.get("runs", [])
    run_count = data.get("run_count")
    assert run_count >= 20, "run_count must be at least 20"
    assert run_count == len(runs), "run_count must match len(runs)"

    sandbox_re = re.compile(r"^sbx-[a-z0-9]{8,}$")
    seen_names = set()
    success_count = 0
    wall_clocks = []
    boot_times = []
    total_cost = 0.0

    for r in runs:
        s_name = r.get("sandbox_name")
        assert sandbox_re.match(s_name), f"Invalid sandbox_name: {s_name}"
        assert s_name not in seen_names, f"Duplicate sandbox_name: {s_name}"
        seen_names.add(s_name)

        assert r.get("fresh") is True, f"fresh must be True: {s_name}"
        assert isinstance(r.get("success"), bool)
        if r.get("success"):
            success_count += 1

        wc = r.get("wall_clock_s")
        assert isinstance(wc, (int, float)) and wc >= 0
        wall_clocks.append(wc)

        bt = r.get("boot_to_ready_s")
        assert isinstance(bt, (int, float)) and bt >= 0
        boot_times.append(bt)

        cost = r.get("cost_usd")
        assert isinstance(cost, (int, float)) and cost >= 0
        total_cost += cost

    # Validate arithmetic
    expected_success_rate = success_count / run_count
    assert abs(data.get("success_rate") - expected_success_rate) <= 0.001

    # Sorted wall clock median & p90
    sorted_wc = sorted(wall_clocks)
    n = len(sorted_wc)
    mid_idx1 = n // 2 - 1
    mid_idx2 = n // 2
    expected_median_wc = (sorted_wc[mid_idx1] + sorted_wc[mid_idx2]) / 2.0
    assert abs(data.get("median_wall_clock_s") - expected_median_wc) <= 0.001

    p90_idx = math.ceil(0.90 * n) - 1
    expected_p90_wc = sorted_wc[p90_idx]
    assert abs(data.get("p90_wall_clock_s") - expected_p90_wc) <= 0.001

    # Boot time median
    sorted_bt = sorted(boot_times)
    expected_median_bt = (sorted_bt[mid_idx1] + sorted_bt[mid_idx2]) / 2.0
    assert abs(data.get("median_boot_to_ready_s") - expected_median_bt) <= 0.001

    # Total cost
    assert abs(data.get("total_cost_usd") - total_cost) <= 0.01

    # Postmortem
    pm_path = ROOT_DIR / data.get("postmortem_path", "")
    assert pm_path.exists(), f"postmortem_path not found: {pm_path}"
    assert len(pm_path.read_text(encoding="utf-8")) >= 200, "postmortem.md must be at least 200 chars"


# 8. Verification of reports/containment.json
def test_containment_json():
    cont_file = ROOT_DIR / "reports" / "containment.json"
    assert cont_file.exists(), "reports/containment.json must exist"
    data = json.loads(cont_file.read_text(encoding="utf-8"))

    assert data.get("attack") in ["prompt_injection_exfil", "destructive_command", "suspicious_package"]
    assert data.get("blocked") is True
    assert data.get("host_untouched") is True

    paths = data.get("evidence_paths", [])
    assert len(paths) >= 1
    for p in paths:
        assert (ROOT_DIR / p).exists(), f"Evidence file does not exist: {p}"


# 9. Verification of failure policy & trace
def test_failure_policy_and_trace():
    policy_file = ROOT_DIR / "reports" / "failure_policy.json"
    assert policy_file.exists(), "reports/failure_policy.json must exist"
    data = json.loads(policy_file.read_text(encoding="utf-8"))

    assert data.get("failed_step") == 7
    assert data.get("total_steps") == 10
    policy = data.get("policy")
    assert policy in ["resume", "rollback", "fresh"]
    assert len(data.get("rationale", "")) >= 200

    trace_file = ROOT_DIR / data.get("trace_path", "")
    assert trace_file.exists(), f"trace_path does not exist: {trace_file}"
    trace_lines = [json.loads(l) for l in trace_file.read_text(encoding="utf-8").splitlines() if l.strip()]

    found_policy = any(
        l.get("event") == "policy_applied" and l.get("policy") == policy
        for l in trace_lines
    )
    assert found_policy, f"failure_trace.jsonl must contain event 'policy_applied' with policy '{policy}'"


# 10. Verification of reports/concurrency.json
def test_concurrency_json():
    cc_file = ROOT_DIR / "reports" / "concurrency.json"
    assert cc_file.exists(), "reports/concurrency.json must exist"
    data = json.loads(cc_file.read_text(encoding="utf-8"))

    jobs = data.get("jobs", [])
    assert len(jobs) >= 5, "concurrency.json must have at least 5 jobs"

    sandbox_re = re.compile(r"^sbx-[a-z0-9]{8,}$")
    seen_names = set()
    for job in jobs:
        s_name = job.get("sandbox_name")
        assert sandbox_re.match(s_name), f"Invalid sandbox_name: {s_name}"
        assert s_name not in seen_names, f"Duplicate sandbox_name: {s_name}"
        seen_names.add(s_name)
        assert job.get("started_at") and isinstance(job["started_at"], str)

    assert len(data.get("breakage_notes", "")) >= 40, "breakage_notes must be at least 40 chars"


# 11. Verification of Ledger API Endpoints
def test_ledger_api():
    from api.main import app
    client = TestClient(app)

    # GET /health
    r_health = client.get("/health")
    assert r_health.status_code == 200
    assert r_health.json() == {"status": "ok"}

    # GET /api/runs
    r_runs = client.get("/api/runs")
    assert r_runs.status_code == 200
    runs = r_runs.json()
    assert isinstance(runs, list)
    assert any(r.get("sandbox_name") == "sbx-seeddemo1" for r in runs), "Must include sbx-seeddemo1"

    # POST /api/runs valid
    payload_valid = {
        "run_id": "test-run-valid-01",
        "sandbox_name": "sbx-testrunner01",
        "problem_id": "prob-test-01",
        "state": "running",
        "execution_target": "celesto_sandbox"
    }
    r_post_valid = client.post("/api/runs", json=payload_valid)
    assert r_post_valid.status_code == 201
    assert r_post_valid.json()["run_id"] == "test-run-valid-01"

    # POST /api/runs invalid execution_target -> 400
    payload_invalid_target = {
        "run_id": "test-run-invalid-target",
        "sandbox_name": "sbx-testrunner02",
        "problem_id": "prob-test-02",
        "state": "running",
        "execution_target": "host"
    }
    r_post_target = client.post("/api/runs", json=payload_invalid_target)
    assert r_post_target.status_code == 400, f"Expected 400 for host execution_target, got {r_post_target.status_code}"

    # POST /api/runs invalid state -> 400
    payload_invalid_state = {
        "run_id": "test-run-invalid-state",
        "sandbox_name": "sbx-testrunner03",
        "problem_id": "prob-test-03",
        "state": "unknown_state",
        "execution_target": "celesto_sandbox"
    }
    r_post_state = client.post("/api/runs", json=payload_invalid_state)
    assert r_post_state.status_code == 400, f"Expected 400 for unknown state, got {r_post_state.status_code}"

    # POST /api/runs invalid sandbox_name -> 400
    payload_invalid_sbx = {
        "run_id": "test-run-invalid-sbx",
        "sandbox_name": "bad_name",
        "problem_id": "prob-test-04",
        "state": "ready",
        "execution_target": "celesto_sandbox"
    }
    r_post_sbx = client.post("/api/runs", json=payload_invalid_sbx)
    assert r_post_sbx.status_code == 400, f"Expected 400 for bad sandbox_name, got {r_post_sbx.status_code}"


# 12. Verification of README.md required phrases
def test_readme_phrases():
    readme_file = ROOT_DIR / "README.md"
    assert readme_file.exists(), "README.md must exist at repo root"
    content = readme_file.read_text(encoding="utf-8")

    required_phrases = [
        "Problem statement",
        "How I used Celesto",
        "Eval report",
        "Containment test",
        "State and failure design",
        "Setup"
    ]
    for phrase in required_phrases:
        assert phrase in content, f"README.md must contain exact phrase: '{phrase}'"

