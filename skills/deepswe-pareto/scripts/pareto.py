"""Add or refresh points in deepswe-pareto.html's JSON data block.

Run from the workspace root:
    uv run python <skill>/scripts/pareto.py add "jobs/<group>" --model "<display name>" \
        --setup "<setup>" [--pricing <litellm entry>] [--efforts low,high] [--html deepswe-pareto.html]
    uv run python <skill>/scripts/pareto.py refresh [--html deepswe-pareto.html]
"""

import argparse
import json
import re
import sys
from functools import cache
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".agents/skills/effort-sweep-report/scripts"))
import sweep_report as sr  # noqa: E402

FULL_SET = 113
PALETTE = ["#2563eb", "#8250df", "#d9480f", "#0d9488", "#db2777", "#ca8a04", "#0891b2", "#65a30d", "#dc2626", "#4b5563"]
BLOCK = re.compile(r'(<script type="application/json" id="data">)(.*?)(</script>)', re.S)


def read_html(path: Path) -> tuple[str, dict]:
    text = path.read_text()
    if not BLOCK.search(text):
        raise SystemExit(f"{path}: no <script type=\"application/json\" id=\"data\"> block")
    return text, json.loads(BLOCK.search(text).group(2))


def write_html(path: Path, text: str, data: dict) -> None:
    path.write_text(BLOCK.sub(lambda m: f"{m.group(1)}\n{dump_data(data)}\n{m.group(3)}", text, count=1))


def dump_point(p: dict) -> str:
    fields = {k: (f"{v:.2f}" if k == "cost" else json.dumps(v)) for k, v in p.items()}
    return "{" + ", ".join(f'"{k}": {v}' for k, v in fields.items()) + "}"


def dump_model(m: dict) -> str:
    head = ", ".join(f'"{k}": {json.dumps(m[k])}' for k in ("model", "color", "pricing"))
    lines = [f"    {{{head},"]
    if "label" in m:
        lines.append(f'     "label": {json.dumps(m["label"])},')
    points = ",\n".join(f"       {dump_point(p)}" for p in m["points"])
    lines.append(f'     "points": [\n{points}\n     ]}}')
    return "\n".join(lines)


def dump_data(data: dict) -> str:
    models = ",\n".join(dump_model(m) for m in data["models"])
    return f'{{\n  "axes": {json.dumps(data["axes"])},\n  "models": [\n{models}\n  ]\n}}'


@cache
def load_stats(job: Path, pricing: str) -> dict:
    stats, _ = sr.load_job(job, "auggie", sr.Pricing(pricing), 1.3)
    return stats


def full_set_stats(job: Path, pricing: str, efforts: list[str] | None, context: str) -> dict[str, dict]:
    out = {}
    for effort, s in load_stats(job, pricing).items():
        if efforts is not None and effort not in efforts:
            continue
        if int(s["n"]) != FULL_SET:
            print(f"skip {context} {effort}: {int(s['n'])} trials, chart takes only {FULL_SET}-task runs", file=sys.stderr)
            continue
        if s["no_data"]:
            print(f"warning {context} {effort}: {int(s['no_data'])} trials have no trajectory, cost understated", file=sys.stderr)
        out[effort] = {"passed": int(s["passed"]), "tasks": int(s["n"]), "cost": round(s["cost"], 2)}
    return out


def describe(p: dict) -> str:
    return f"{p['passed']}/{p['tasks']} ${p['cost']:.2f}"


def cmd_add(args: argparse.Namespace) -> None:
    text, data = read_html(args.html)
    job = Path(args.job)
    if not job.is_dir():
        raise SystemExit(f"{job}: not a directory")
    model = next((m for m in data["models"] if m["model"] == args.model), None)
    if model is None:
        if not args.pricing:
            raise SystemExit(f"{args.model!r} is new; pass --pricing <litellm entry>")
        used = {m["color"] for m in data["models"]}
        color = next((c for c in PALETTE if c not in used), None)
        if color is None:
            raise SystemExit("palette exhausted; add a colour to PALETTE")
        model = {"model": args.model, "color": color, "pricing": args.pricing, "points": []}
        data["models"].append(model)
    elif args.pricing and args.pricing != model["pricing"]:
        raise SystemExit(f"{args.model!r} is stored with pricing {model['pricing']!r}, not {args.pricing!r}")

    efforts = args.efforts.split(",") if args.efforts else None
    stats = full_set_stats(job, model["pricing"], efforts, job.name)
    if not stats:
        raise SystemExit(f"{job}: no full-set efforts to add")
    by_effort = {p["effort"]: p for p in model["points"]}
    for effort in sorted(stats, key=sr.effort_key):
        new = {"effort": effort, **stats[effort], "job": job.name, "setup": args.setup}
        old = by_effort.get(effort)
        if old == new:
            print(f"{args.model} {effort}: unchanged {describe(new)}")
        elif old:
            print(f"{args.model} {effort}: {describe(old)} ({old['job']}) -> {describe(new)}")
        else:
            print(f"{args.model} {effort}: added {describe(new)}")
        by_effort[effort] = new
    model["points"] = [by_effort[e] for e in sorted(by_effort, key=sr.effort_key)]
    write_html(args.html, text, data)


def cmd_refresh(args: argparse.Namespace) -> None:
    text, data = read_html(args.html)
    changed = 0
    for m in data["models"]:
        for p in m["points"]:
            job = Path("jobs") / p["job"]
            if not job.is_dir():
                print(f"{m['model']} {p['effort']}: no local {job}, kept as is")
                continue
            s = full_set_stats(job, m["pricing"], [p["effort"]], job.name).get(p["effort"])
            if s is None:
                print(f"{m['model']} {p['effort']}: not a full-set run any more, kept as is")
                continue
            if any(p[k] != s[k] for k in s):
                print(f"{m['model']} {p['effort']}: {describe(p)} -> {describe(s)}")
                p.update(s)
                changed += 1
    write_html(args.html, text, data)
    print(f"{changed} point(s) changed")


def main() -> None:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--html", type=Path, default=Path("deepswe-pareto.html"))
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    add = sub.add_parser("add", parents=[common], help="add or replace a job's points for one model")
    add.add_argument("job", help="local grouped job, e.g. jobs/<group>")
    add.add_argument("--model", required=True, help="display name on the chart")
    add.add_argument("--setup", required=True, help="shown on hover, e.g. 'prompt-iteration-4a, Daytona'")
    add.add_argument("--pricing", help="LiteLLM price entry; required for a new model")
    add.add_argument("--efforts", help="comma-separated efforts to take from the job (default: all)")
    add.set_defaults(run=cmd_add)
    refresh = sub.add_parser("refresh", parents=[common], help="recompute every point whose job exists under jobs/")
    refresh.set_defaults(run=cmd_refresh)
    args = parser.parse_args()
    args.run(args)


if __name__ == "__main__":
    main()
