import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple

LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"
COMMANDS_LOG_PATH = LOGS_DIR / "commands.jsonl"

class CommandBlockedError(Exception):
    """Raised when a safety hook blocks an untrusted command before dispatch."""
    pass

# Suspicious patterns to detect prompt injection, exfiltration, or destructive behavior
BLOCKED_PATTERNS = [
    r"rm\s+-rf\s+/(?:\s|$|\*)",                # Destructive root deletion
    r"curl.*(?:\$API_KEY|\.env|exfil|token)",   # Secret exfiltration
    r"wget.*(?:\$API_KEY|\.env|exfil|token)",   # Secret exfiltration
    r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:", # Fork bomb
    r"dd\s+if=/dev/zero\s+of=/dev/sda",         # Raw disk wipe
    r"cat\s+.*\.env\s*\|\s*(?:curl|nc|bash)",   # Pipeline exfiltration
]

def append_command_log(sandbox_name: str, command: str, decision: str):
    """Appends audited command execution attempt to logs/commands.jsonl."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()
    record = {
        "ts": ts,
        "sandbox_name": sandbox_name,
        "command": command.strip(),
        "decision": decision,
        "execution_target": "celesto_sandbox"
    }
    with open(COMMANDS_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

def evaluate_command_safety(sandbox_name: str, command: str) -> Tuple[bool, str]:
    """Safety callback that inspects commands before they reach the guest VM."""
    cmd = command.strip()
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, cmd, re.IGNORECASE):
            append_command_log(sandbox_name, cmd, decision="block")
            return False, f"Command blocked by safety hook: matched rule '{pattern}'"
    
    append_command_log(sandbox_name, cmd, decision="allow")
    return True, "Command allowed"

