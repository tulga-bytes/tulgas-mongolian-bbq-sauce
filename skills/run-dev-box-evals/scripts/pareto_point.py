"""Print deepswe-pareto.html DATA points for a downloaded, grouped job.

uv run python <skill>/scripts/pareto_point.py "jobs/<group>" <litellm pricing model> "<setup>"
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".agents/skills/effort-sweep-report/scripts"))
import sweep_report as sr  # noqa: E402

group, pricing_model, setup = sys.argv[1], sys.argv[2], sys.argv[3]
stats, _ = sr.load_job(Path(group), "auggie", sr.Pricing(pricing_model), 1.3)
for effort in sorted(stats, key=sr.effort_key):
    s = stats[effort]
    if s["no_data"]:
        print(f"// {effort}: {int(s['no_data'])} trials have no trajectory, so cost is understated", file=sys.stderr)
    print(
        f'{{ effort: "{effort}", passed: {int(s["passed"])}, tasks: {int(s["n"])}, cost: {s["cost"]:.2f}, '
        f'job: "{Path(group).name}", setup: "{setup}" }},'
    )
