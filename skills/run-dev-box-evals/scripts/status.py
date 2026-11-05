# Runs on the dev-box: python3 - [FILTER] < status.py
# One line per Daytona job, newest first. FILTER keeps job names containing it.
import glob
import json
import os
import sys
from datetime import datetime

ROOT = "/home/augment/Workspace/bench-maxxing/jobs"
STALL_MINUTES = 30
needle = sys.argv[1] if len(sys.argv) > 1 else ""

names = [n for n in os.listdir(ROOT) if "daytona" in n and needle in n and os.path.isdir(os.path.join(ROOT, n))]
for name in sorted(names, key=lambda n: -os.path.getmtime(os.path.join(ROOT, n))):
    job = os.path.join(ROOT, name)
    if not os.path.exists(f"{job}/result.json") or not os.path.exists(f"{job}/config.json"):
        print(f"{name} | starting (no result.json yet)")
        continue
    r = json.load(open(f"{job}/result.json"))
    s = r.get("stats", {})
    agent = json.load(open(f"{job}/config.json"))["agents"][0]
    kw = agent.get("kwargs", {})
    passed = 0
    for path in glob.glob(f"{job}/*/result.json"):
        try:
            rewards = (json.load(open(path)).get("verifier_result") or {}).get("rewards") or {}
        except (OSError, ValueError):
            continue
        passed += rewards.get("reward") == 1
    if r.get("finished_at"):
        state = "FINISHED"
    else:
        updated = datetime.fromisoformat((r.get("updated_at") or r["started_at"]).replace("Z", "+00:00"))
        idle = (datetime.now(updated.tzinfo) - updated).total_seconds() / 60
        state = f"STALLED {idle / 60:.1f}h" if idle > STALL_MINUTES else "running"
    total = r.get("n_total_trials") or 0
    done = s.get("n_completed_trials") or 0
    print(" | ".join([
        name, state, f"done {done}/{total}", f"err {s.get('n_errored_trials')}",
        f"pass {passed} ({passed / total:.1%})" if total else "pass 0",
        f"${s.get('cost_usd') or 0:.2f}", str(agent.get("model_name")), str(kw.get("reasoning_effort")),
        os.path.basename(str(kw.get("system_prompt_path"))),
        (r.get("started_at") or "")[:16], (r.get("finished_at") or "")[:16],
    ]))
