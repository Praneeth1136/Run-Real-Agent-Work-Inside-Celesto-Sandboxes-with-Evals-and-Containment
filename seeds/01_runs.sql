CREATE TABLE IF NOT EXISTS runs (
    run_id VARCHAR(128) PRIMARY KEY,
    sandbox_name VARCHAR(128) NOT NULL,
    problem_id VARCHAR(128) NOT NULL,
    state VARCHAR(32) NOT NULL,
    execution_target VARCHAR(64) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO runs (run_id, sandbox_name, problem_id, state, execution_target)
VALUES ('run-seed-001', 'sbx-seeddemo1', 'problem-seed-demo', 'deleted', 'celesto_sandbox')
ON CONFLICT (run_id) DO NOTHING;

