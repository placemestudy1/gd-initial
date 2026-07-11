"""
run_agents.py — Convenience launcher for all 3 agent workers in development.

Run this alongside server.py to have the agents ready for dispatch.
In production, you'd deploy each agent worker separately.

Usage:
  .venv\\Scripts\\python run_agents.py          # Start all 3 agents
  .venv\\Scripts\\python run_agents.py mod      # Moderator only
  .venv\\Scripts\\python run_agents.py aarav    # Aarav only
  .venv\\Scripts\\python run_agents.py priya    # Priya only
"""
import subprocess
import sys
import os
import signal
from pathlib import Path

# Fix Windows console encoding for UTF-8 output
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ─── Resolve the correct Python interpreter ───────────────────────────────────
# Prefer the .venv inside the project directory if it exists.
# This ensures agent subprocesses use the same venv with all packages installed.
_base_dir = Path(__file__).parent
_venv_python = _base_dir / ".venv" / "Scripts" / "python.exe"

if _venv_python.exists():
    PYTHON = str(_venv_python)
elif sys.executable:
    PYTHON = sys.executable  # fallback: whatever interpreter ran this script
else:
    PYTHON = "python"

print(f"Using Python: {PYTHON}")

# ─── Agent module mapping ─────────────────────────────────────────────────────
MODULE_MAP = {
    "agents/moderator.py":     "agents.moderator",
    "agents/debater_aarav.py": "agents.debater_aarav",
    "agents/debater_priya.py": "agents.debater_priya",
}

procs = []

def start_worker(script: str, agent_name: str, extra_args=None):
    # Use -m module mode so relative imports (from .prompts import ...) work
    module = MODULE_MAP.get(script, script.replace("/", ".").removesuffix(".py"))
    args = [PYTHON, "-m", module, "dev"]
    if extra_args:
        args.extend(extra_args)
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    proc = subprocess.Popen(args, cwd=str(_base_dir), env=env)
    procs.append(proc)
    print(f"[OK] Started {agent_name} worker (PID {proc.pid})")
    return proc

def stop_all(sig=None, frame=None):
    print("\nStopping all agent workers...")
    for p in procs:
        try:
            p.terminate()
        except Exception:
            pass
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT,  stop_all)
    signal.signal(signal.SIGTERM, stop_all)

    target = sys.argv[1] if len(sys.argv) > 1 else "all"

    print("=" * 50)
    print("PlaceMe GD Arena - Agent Workers")
    print("=" * 50)

    if target in ("all", "mod"):
        start_worker("agents/moderator.py", "Moderator (Kavya)")

    if target in ("all", "aarav"):
        start_worker("agents/debater_aarav.py", "Aarav Debater")

    if target in ("all", "priya"):
        start_worker("agents/debater_priya.py", "Priya Debater")

    if not procs:
        print(f"Unknown target: {target}. Use: all | mod | aarav | priya")
        sys.exit(1)

    print(f"\n{len(procs)} worker(s) running. Press Ctrl+C to stop.\n")

    # Wait for all workers
    try:
        for p in procs:
            p.wait()
    except KeyboardInterrupt:
        stop_all()
