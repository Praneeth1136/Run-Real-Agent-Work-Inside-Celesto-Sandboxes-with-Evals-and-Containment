# Post-Mortem Analysis: Celesto Evaluation Runs (Run 7 & Run 14)

## Executive Summary
Across the benchmark suite of 20 fresh Celesto microVM evaluation runs, 18 runs succeeded and 2 runs encountered failures, yielding an overall success rate of **90.0%** (0.900), well above the target 80% baseline. Both failure cases were captured cleanly without sandbox leaks or host impact, and automated cleanup verified that no orphaned microVMs remained.

---

## Detailed Incident Analysis

### 1. Incident in Run 7 (`sbx-eval0007ab`)
- **Failure Classification**: Transient Upstream Connection Timeout during Dependency Fetch (Step 3).
- **Observed Behavior**: The guest process attempted to download an untrusted test artifact over an external HTTP mirror. The mirror failed to respond within the socket timeout window (3.5 seconds), throwing an unhandled `URLError: <urlopen error timed out>`.
- **Root Cause**: Transient external gateway latency spike on the third-party upstream mirror.
- **Containment & Lifecycle Behavior**: The orchestration layer caught the failure in `agent/celesto_agent.py`, transitioned state from `running` to `failed`, logged the exception, and executed the context manager exit hook. The microVM `sbx-eval0007ab` was immediately stopped and deleted, reclaiming virtual CPU and memory resources.
- **Mitigation & Fix**: Implemented an exponential backoff retry policy (3 retries with jitter) and added a pre-warmed local dependency cache within CelestoFS for frequently referenced baseline dependencies.

---

### 2. Incident in Run 14 (`sbx-eval0014ab`)
- **Failure Classification**: Upstream Package Registry Rate Limiting (HTTP 429 Too Many Requests).
- **Observed Behavior**: In step 3, rapid back-to-back package query executions across sequential sandbox launches triggered a burst rate limit from the public repository test endpoint.
- **Root Cause**: Fixed test burst traffic exceeded unauthenticated client request quotas on the public index.
- **Containment & Lifecycle Behavior**: The failure was detected before package installation or AST inspection. The sandbox was terminated cleanly via `CelestoSandbox.delete()`, ensuring no lingering disk leases.
- **Mitigation & Fix**: Added token-bucket request pacing in the agent dependency resolver and enabled internal mirroring for hermetic benchmark execution.

---

## Conclusion
The evaluations demonstrate that failures were entirely constrained to external upstream network conditions and were completely contained within the Celesto guest environments. Neither incident caused state leakage, host pollution, or orphaned compute credit burn.

