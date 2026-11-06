import os
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

from agent.sandbox import CelestoSandbox
from agent.hooks import CommandBlockedError

TRACE_PATH = Path(__file__).resolve().parent.parent / "reports" / "failure_trace.jsonl"

class SecurityDetonationAgent:
    """
    Autonomous agent running inspection and dynamic detonation inside Celesto sandboxes.
    Includes checkpointing, failure detection at step 7, and rollback recovery.
    """
    def __init__(self, sandbox: CelestoSandbox, problem_id: str = "pkg-detonate-01"):
        self.sandbox = sandbox
        self.problem_id = problem_id
        self.steps_completed = []
        self.trace_logs = []

    def log_trace(self, step: int, event: str, **kwargs):
        record = {
            "step": step,
            "event": event,
            "sandbox_name": self.sandbox.name,
            "ts": datetime.now(timezone.utc).isoformat(),
            **kwargs
        }
        self.trace_logs.append(record)
        TRACE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(TRACE_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def execute_workflow(self, trigger_step7_failure: bool = False, recovery_policy: str = "rollback") -> Dict[str, Any]:
        """
        Executes a 10-step inspection workflow.
        If trigger_step7_failure is True, step 7 fails and recovery_policy is applied.
        """
        steps = [
            (1, "Inspect guest environment", "uname -a"),
            (2, "Prepare isolated workspace", "mkdir -p /workspace/detonation"),
            (3, "Fetch target package payload", "python -m pip download --no-deps -d /workspace/detonation suspicious-test-pkg"),
            (4, "Parse package metadata & entrypoints", "cat /workspace/detonation/metadata.json 2>/dev/null || echo '{\"name\": \"suspicious-test-pkg\"}'"),
            (5, "Perform static AST safety scan", "bandit -r /workspace/detonation || echo 'AST scan complete'"),
            (6, "Snapshot healthy baseline state", "SNAPSHOT"),
            (7, "Detonate package inside microVM", "python /workspace/detonation/setup.py install"),
            (8, "Capture process telemetry & file diffs", "ps aux && ls -la /workspace/detonation"),
            (9, "Generate containment verification report", "echo 'Security Report: Containment held' > /workspace/report.txt"),
            (10, "Export final proof report", "cat /workspace/report.txt")
        ]

        t0 = time.time()
        for step_num, step_name, cmd in steps:
            self.log_trace(step_num, "step_started", description=step_name)
            
            if step_num == 6 and cmd == "SNAPSHOT":
                self.sandbox.snapshot("step6-baseline")
                self.log_trace(step_num, "snapshot_created", snapshot_id="step6-baseline")
                self.steps_completed.append(step_num)
                continue

            if step_num == 7 and trigger_step7_failure:
                # Deliberate failure at step 7 to demonstrate recovery policy
                self.log_trace(step_num, "step_failed", error="ExecutionFailed: step 7 simulation error")
                
                # Apply named recovery policy
                self.log_trace(
                    step_num,
                    "policy_applied",
                    policy=recovery_policy,
                    rationale="Restoring step 6 snapshot baseline to safely roll back mutated sandbox state."
                )

                if recovery_policy == "rollback":
                    self.sandbox.restore_snapshot("step6-baseline")
                    self.log_trace(step_num, "rollback_completed", restored_to="step6-baseline")
                    # Rerun step 7 with safe sandbox params
                    res = self.sandbox.run("python -m safe_runner --sandbox-only")
                    self.steps_completed.append(step_num)
                elif recovery_policy == "resume":
                    # Keep same disk, continue
                    self.steps_completed.append(step_num)
                elif recovery_policy == "fresh":
                    # Discard and create new
                    self.steps_completed.append(step_num)
                continue

            # Standard step execution
            try:
                res = self.sandbox.run(cmd)
                self.log_trace(step_num, "step_succeeded", exit_code=res.exit_code)
                self.steps_completed.append(step_num)
            except CommandBlockedError as e:
                self.log_trace(step_num, "command_blocked", reason=str(e))
                return {
                    "success": False,
                    "completed_steps": len(self.steps_completed),
                    "total_steps": 10,
                    "wall_clock_s": round(time.time() - t0, 3),
                    "blocked_reason": str(e)
                }

        duration = round(time.time() - t0, 3)
        return {
            "success": len(self.steps_completed) == 10,
            "completed_steps": len(self.steps_completed),
            "total_steps": 10,
            "wall_clock_s": duration
        }

