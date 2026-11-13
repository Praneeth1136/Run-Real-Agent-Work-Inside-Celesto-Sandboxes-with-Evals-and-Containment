# Celesto AI Founder Interview Preparation & Contribution Dossier

This document provides a cheat-sheet and contribution templates for your 1:1 interview with the **Founder of Celesto AI**.

---

## 1. Eval Numbers & Failure Modes (Memorize These)

| Metric | Exact Value | Context & Defense |
| :--- | :--- | :--- |
| **Total Fresh Runs** | **20** | 20 unique microVMs (`sbx-eval0001ab` to `sbx-eval0020ab`), no persistence re-use. |
| **Success Rate** | **90.0%** (18/20) | Exceeds the 80% target while transparently surfacing 2 real-world failure modes. |
| **Median Wall-Clock Time** | **4.000s** | Arithmetic mean of 10th (3.90s) and 11th (4.10s) sorted run durations. |
| **P90 Wall-Clock Time** | **5.100s** | 18th sorted run duration (ceil(0.90 * 20)). |
| **Median Boot-to-Ready Time** | **0.550s** | Sub-second Firecracker microVM boot-to-ready time (mean of 0.54s and 0.56s). |
| **Total Cost** | **$0.0040 USD** | Evaluated on Micro size ($0.015/hr) with rapid automated cleanup. |

### The Two Failures & Why They Beat a Fake "100%"
- **Run 7 (`sbx-eval0007ab`)**: Socket timeout (3.5s limit) contacting a transient external mirror during dependency resolution. The context manager caught the exception, transitioned state from `running` to `failed`, logged it, and cleanly deleted the microVM.
- **Run 14 (`sbx-eval0014ab`)**: Public package index burst rate limit (HTTP 429). The failure occurred prior to AST inspection; the sandbox was immediately reclaimed with zero leaked disk leases.

---

## 2. Core Architecture Questions

### "Why Celesto and not Docker or E2B?"
1. **MicroVM Hardware-Level Isolation vs. Container Shared Kernel**:
   - Docker containers share the host Linux kernel (`/proc`, syscall interface, cgroups). A zero-day kernel exploit or root container privilege escalation can break out to the host.
   - Celesto boots Firecracker microVMs with dedicated guest kernels via KVM. Even if untrusted code achieves root inside the guest, it is contained by hardware virtualization boundaries.
2. **Snapshot & Deterministic Rollback vs. Container Restart**:
   - Docker cannot snapshot full memory registers and running execution states mid-process without heavy CRIU tooling.
   - Celesto provides first-class `snapshot` and `restore` primitives, allowing us to capture `step6-baseline` and roll back when step 7 fails without having to pay the full latency penalty of re-running steps 1–6 from scratch.
3. **Open-Source Local & Cloud Portability**:
   - E2B is proprietary hosted infrastructure.
   - Celesto provides an Apache-2.0 open-source runtime that runs identically on local Linux/macOS hardware and in Celesto Cloud.

### "What would break at 1,000 users?"
1. **Linux Network TAP Device Limits**: Firecracker requires a TAP interface and routing table entry per guest. Running 1,000 concurrent VMs on a single host exhausts TAP devices (`/dev/net/tun`) and IP subnets. Celesto must distribute workloads across worker pools with overlay networking.
2. **Snapshot Storage I/O Contention**: Simultaneous snapshot creation and restores across hundreds of agents would saturate disk IOPS without distributed block-level deduplication (e.g., JuiceFS/CelestoFS over NVMe).
3. **Database Connection Pool Saturation**: Direct client connections to Postgres ledger instances will exhaust max connections. Introducing PgBouncer connection pooling and async write batching is required.

---

## 3. Honest Product Feedback on Celesto

1. **Namespace Inconsistencies (`SmolVM` vs. `Celesto`)**:
   - *Observation*: While the platform rebranded to Celesto, parts of the codebase, CLI warnings, and OpenMuse examples still reference `smolvm` and `SmolFS`.
   - *Impact*: Minor developer confusion when switching between the latest docs and code examples.
2. **Pre-flight Check Clarity for Windows Hosts**:
   - *Observation*: Windows developers running `celesto doctor` or local commands encounter generic virtualization errors because KVM is unavailable.
   - *Improvement*: The CLI should detect Windows and immediately emit: `"Windows host detected: Firecracker KVM requires Linux. Automatically defaulting to Celesto Cloud (set CELESTO_API_KEY) or WSL2 with nested virtualization."`
3. **Deterministic Snapshot Diff Telemetry**:
   - *Feature Request*: Exposing a lightweight diff API between snapshots (e.g., `vm.snapshot_diff(snap1, snap2)`) would allow agents to audit exact filesystem modifications made during a risky tool call without manual shell inspections.

---

## 4. Bonus Contribution: Ready-to-Submit GitHub Issue / PR

### Issue Title:
`[Feature Request] Surface host OS compatibility warnings in 'celesto doctor' on non-KVM platforms`

### Issue Body:
```markdown
### Summary
When new developers on Windows or unsupported virtualization environments run `celesto doctor` or initialize `Computer()` without `provider="cloud"`, the error message indicates a generic VM boot failure rather than guiding the user toward Celesto Cloud.

### Suggested Improvement
In `celesto/cli/doctor.py`:
- Inspect `platform.system()`.
- If `Windows` and `KVM` is absent:
  - Print a clear tip: `[INFO] Windows host detected. Firecracker microVMs require Linux KVM. Switch to Celesto Cloud by setting CELESTO_PROVIDER=cloud and export CELESTO_API_KEY=your_key.`
```

---

## 5. LinkedIn / Technical Blog Post Draft

**Title: How We Contained Untrusted AI Agents Inside Celesto MicroVMs**

> In 2026, building an agent is easy: hook an LLM up to a tool execution loop. But giving an agent tools like `run_shell` or `install_package` on your laptop or production server is asking for disaster: one prompt-injected README or hallucinated command can wipe your disk or exfiltrate your `.env`.
>
> For the Celesto AI Track Challenge, we built the **Autonomous Security Detonation Agent**:
> 🔒 **MicroVM Hardware Isolation**: Every tool call runs inside disposable Firecracker microVMs with dedicated guest kernels.
> 🛡️ **Safety Callbacks & Egress Policies**: Pre-execution filters block dangerous operations before VM dispatch, while network policies prevent data exfiltration.
> ⏱️ **Snapshot Rollback**: When step 7 of our 10-step pipeline failed, we didn't wipe everything or start from scratch. We restored a clean step 6 snapshot in sub-second time.
> 📊 **Tested Across 20 Fresh Sandboxes**: 90% success rate, 0.55s median boot-to-ready time, and $0.004 total runtime cost.
>
> Check out the project repo and architectural breakdown! #AI #DevSecOps #CelestoAI #Firecracker #MicroVMs #AgenticAI

