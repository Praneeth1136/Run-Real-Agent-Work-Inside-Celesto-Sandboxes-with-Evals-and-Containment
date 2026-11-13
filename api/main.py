import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from api.models import RunCreate, RunResponse, VALID_STATES, SANDBOX_REGEX
from api.database import init_db, list_runs, insert_run

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Try connecting / initializing Postgres table
    try:
        init_db()
    except Exception as e:
        print(f"Database init warning: {e}")
    yield

app = FastAPI(
    title="Celesto Run Ledger API",
    description="Control plane ledger recording agent runs inside isolated Celesto sandboxes",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": "Validation error", "errors": exc.errors()},
    )

@app.get("/health")
def get_health():
    return {"status": "ok"}

@app.get("/api/runs")
def get_runs():
    runs = list_runs()
    return runs

@app.post("/api/runs", status_code=status.HTTP_201_CREATED)
def create_run(payload: dict):
    # Explicit validation to ensure HTTP 400 for any invalid field
    run_id = payload.get("run_id")
    sandbox_name = payload.get("sandbox_name")
    problem_id = payload.get("problem_id")
    state = payload.get("state")
    execution_target = payload.get("execution_target")

    if not run_id or not isinstance(run_id, str):
        raise HTTPException(status_code=400, detail="run_id is required and must be a string")

    if not sandbox_name or not isinstance(sandbox_name, str) or not SANDBOX_REGEX.match(sandbox_name):
        raise HTTPException(
            status_code=400,
            detail=f"sandbox_name must match '^sbx-[a-z0-9]{{8,}}$', got '{sandbox_name}'"
        )

    if not problem_id or not isinstance(problem_id, str):
        raise HTTPException(status_code=400, detail="problem_id is required and must be a string")

    if state not in VALID_STATES:
        raise HTTPException(
            status_code=400,
            detail=f"state must be one of {list(VALID_STATES)}, got '{state}'"
        )

    if execution_target != "celesto_sandbox":
        raise HTTPException(
            status_code=400,
            detail=f"execution_target must be exactly 'celesto_sandbox', got '{execution_target}'"
        )

    saved = insert_run({
        "run_id": run_id,
        "sandbox_name": sandbox_name,
        "problem_id": problem_id,
        "state": state,
        "execution_target": execution_target
    })
    return saved

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("API_PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)

