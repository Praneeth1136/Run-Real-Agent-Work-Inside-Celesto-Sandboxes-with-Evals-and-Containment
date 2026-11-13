# Autonomous Security Detonation Agent in Celesto Sandboxes

An autonomous agent orchestrator and run ledger built for the **Celesto AI Track Challenge**. This project executes untrusted package detonation, AST security audits, and containment verification inside hardware-isolated **Celesto microVM sandboxes** with pre-execution safety hooks and network policies.

---

## Architecture Diagram

The system separates trust zones into a **Trusted Control Plane** (FastAPI ledger + Postgres) and an **
