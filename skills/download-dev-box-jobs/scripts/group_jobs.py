"""Flatten downloaded variant jobs into one grouped job the viewer can display.

Usage (from the workspace root):
    uv run python ~/.agents/skills/download-dev-box-jobs/scripts/group_jobs.py "jobs/<group>" --agent <agent> <variant> [...]

Each variant must be a finished Harbor job at jobs/<group>/<variant>/. An optional
finished jobs/<group>/<variant>-retry/ job is merged: a retry trial replaces an original
trial for the same task when the original is unscored or has an unreadable result.json.
Running again on an already grouped job adds the new variants to it.

With --full-set, trials from benchmarks/deep-swe-1-1-30 and -83 are recorded as
benchmarks/deep-swe-1-1, so a 30-task run plus its 83-task remainder reads as one full run.
"""

import argparse
import hashlib
import json
import re
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from harbor.metrics.mean import Mean
from harbor.models.job.result import JobStats
from harbor.models.trial.result import TrialResult
from harbor.utils.pass_at_k import compute_pass_at_k_by_evals

META_FILES = ("config.json", "result.json", "job.log", "lock.json")


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(p):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return None


def rank(r):
    if r is None:
        return 0
    return 2 if ((r.get("verifier_result") or {}).get("rewards") or {}).get("reward") is not None else 1


def trials_of(job):
    out = {}
    for d in sorted(x for x in job.iterdir() if x.is_dir() and "__" in x.name):
        r = load(d / "result.json")
        task = r["task_name"].split("/")[-1] if r else d.name.rsplit("__", 1)[0]
        out.setdefault(task, []).append((d, r))
    return out


def to_full_set(s):
    s = re.sub(r"benchmarks/deep-swe-1-1-(?:30|83)/", "benchmarks/deep-swe-1-1/", s)
    return re.sub(r'"deep-swe-1-1-(?:30|83)"', '"deep-swe-1-1"', s)


def move_meta(src, dst):
    dst.mkdir(parents=True)
    for f in META_FILES:
        if (src / f).exists():
            (src / f).rename(dst / f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("--agent", required=True, help="label prefix, e.g. auggie or codex")
    ap.add_argument("variants", nargs="+")
    ap.add_argument("--full-set", action="store_true", help="record deep-swe-1-1-30/-83 trials as deep-swe-1-1")
    a = ap.parse_args()
    root, agent = a.root, a.agent

    gpath = root / "grouping.json"
    grouping = load(gpath) or {"viewer_only": True, "original_jobs": []}
    done = {(j["agent"], j["variant"]) for j in grouping["original_jobs"]}
    old_cfg, old_res = load(root / "config.json"), load(root / "result.json")
    if gpath.exists():
        assert old_cfg and old_res, "grouped job is missing config.json or result.json"

    plan = []
    for v in a.variants:
        sub, retry = root / v, root / f"{v}-retry"
        assert (agent, v) not in done, f"{agent}/{v} is already grouped"
        for j in (sub, retry):
            if j.exists():
                assert (load(j / "result.json") or {}).get("finished_at"), f"{j} is not a finished job"
        assert sub.is_dir(), f"missing {sub}"
        plan.append((v, sub, retry if retry.is_dir() else None))

    configs, results = [], [old_res] if old_res else []
    for v, sub, retry in plan:
        label, meta = f"{agent}-{v}", root / "original-jobs" / agent / v
        orig, extra = trials_of(sub), trials_of(retry) if retry else {}
        keep, unused, replaced = [], [], []
        for task in sorted(set(orig) | set(extra)):
            cands = [(d, r, "original") for d, r in orig.get(task, [])] + [(d, r, "retry") for d, r in extra.get(task, [])]
            best = max(cands, key=lambda c: (rank(c[1]), c[2] == "original"))
            keep.append(best)
            unused += [c for c in cands if c is not best]
            if best[2] == "retry" and task in orig:
                replaced.append(task)
        entries = []
        for d, r, src in keep:
            assert r is not None, f"no readable result.json for {d}"
            rp = d / "result.json"
            original = sha(rp)
            r["agent_info"]["name"] = label
            if a.full_set:
                r = json.loads(to_full_set(json.dumps(r)))
                for f in ("config.json", "lock.json"):
                    if (d / f).exists():
                        (d / f).write_text(to_full_set((d / f).read_text()))
            rp.write_text(json.dumps(r, indent=4))
            assert not (root / d.name).exists(), f"{d.name} already exists in {root}"
            d.rename(root / d.name)
            entries.append({"name": d.name, "source": src, "result_sha256": sha(root / d.name / "result.json"),
                            "original_result_sha256": original})
        move_meta(sub, meta)
        record = {"source_job": f"{root.name}/{v}", "agent": agent, "variant": v, "relabelled_agent_name": label,
                  "metadata_directory": str(meta.relative_to(root)), "trials": entries}
        configs.append(load(meta / "config.json"))
        results.append(load(meta / "result.json"))
        if retry:
            move_meta(retry, meta / "retry")
            results.append(load(meta / "retry" / "result.json"))
            record.update(retry_metadata_directory=str((meta / "retry").relative_to(root)), retry_replacements=replaced)
        if unused:
            (meta / "unused").mkdir(parents=True)
            for d, _, src in unused:
                d.rename(meta / "unused" / f"{src}-{d.name}")
            record["unused_trials"] = [f"{src}-{d.name}" for d, _, src in unused]
        for j in (sub, retry):
            if j and j.exists():
                leftover = list(j.iterdir())
                assert not leftover, f"unexpected files left in {j}: {[p.name for p in leftover][:5]}"
                j.rmdir()
        grouping["original_jobs"].append(record)
        print(f"{label}: kept {len(entries)} (from retry {sum(e['source'] == 'retry' for e in entries)}), set aside {len(unused)}")

    cfg = dict(old_cfg or configs[0])
    agents = list((old_cfg or {}).get("agents", []))
    for c in configs:
        for ag in c["agents"]:
            ag = dict(ag)
            if ":" in ag["name"]:
                ag["import_path"], ag["name"] = ag.get("import_path") or ag["name"], agent
            agents.append(ag)
    cfg.update(job_name=root.name, jobs_dir="jobs", agents=agents)
    if a.full_set:
        cfg["datasets"] = [{"path": "benchmarks/deep-swe-1-1"}]
    (root / "config.json").write_text(json.dumps(cfg, indent=4))

    trs = [TrialResult.model_validate_json(p.read_text()) for p in sorted(root.glob("*__*/result.json"))]
    stats = JobStats.from_trial_results(trs)
    rw = defaultdict(list)
    for t in trs:
        key = JobStats.format_agent_evals_key(t.agent_info.name, t.agent_info.model_info.name if t.agent_info.model_info else None, t.source or "adhoc")
        rw[key].append(t.verifier_result.rewards if t.verifier_result else None)
    for key, x in rw.items():
        stats.evals[key].metrics.append(Mean().compute(x))
    for key, pk in compute_pass_at_k_by_evals(trs).items():
        stats.evals[key].pass_at_k = pk
    ns = json.loads(stats.model_dump_json())
    pick = lambda k, f: f(r[k] for r in results if r and r.get(k))
    (root / "result.json").write_text(json.dumps({"id": (old_res or {}).get("id") or str(uuid.uuid4()),
        "started_at": pick("started_at", min), "updated_at": pick("updated_at", max), "finished_at": pick("finished_at", max),
        "n_total_trials": len(trs), "stats": ns}, indent=4))
    grouping["grouped_at"] = datetime.now(timezone.utc).isoformat()
    gpath.write_text(json.dumps(grouping, indent=2))
    print("total", len(trs), {k: round(ns[k] or 0, 2) for k in ("n_completed_trials", "n_errored_trials", "cost_usd")})
    for k, e in ns["evals"].items():
        print(f"  {k.split('__')[0]:32} trials {e['n_trials']} errors {e['n_errors']} passes {len(e['reward_stats']['reward'].get('1', []))}")


if __name__ == "__main__":
    main()
