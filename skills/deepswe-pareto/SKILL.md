---
name: deepswe-pareto
description: Add a job to the DeepSWE Pareto chart, generate or update the pareto report from jobs/, or refresh deepswe-pareto.html. Use after a full-set (113-task) Auggie run is downloaded and grouped under jobs/.
---

# DeepSWE Pareto chart

`deepswe-pareto.html` at the workspace root plots Auggie pass rate against token
cost per task, one curve per model. Its data is the JSON block
`<script type="application/json" id="data">` inside the file. `scripts/pareto.py`
edits that block and nothing else. Run it from the workspace root; set `S` to the
`scripts/` folder next to this `SKILL.md`. It imports `load_job` from
`~/.agents/skills/effort-sweep-report/scripts/sweep_report.py`, so cost matches
the sweep reports (LiteLLM pricing, no 1.3x billing multiplier).

Only full-set runs go on the chart. Efforts with other than 113 trials are
skipped with a message on stderr. A warning names efforts whose trials lack a
trajectory; their cost is understated.

## Add a job

```bash
uv run python "$S/pareto.py" add "jobs/<group>" --model "<display name>" --setup "prompt-iteration-4a, Daytona" [--pricing <litellm entry>] [--efforts low,high]
```

Points are keyed by model and effort, so re-running replaces the same points and
prints `old -> new`. `--pricing` is required for a new model and must match the
stored entry for an existing one. A new model gets the next unused palette colour.

## Refresh

```bash
uv run python "$S/pareto.py" refresh
```

Recomputes passed, tasks, and cost for every point whose `jobs/<job>` folder
exists and prints the ones that changed. Points without a local job are kept and
listed.

## Pricing for a new model

Find the entry in `litellm.model_cost` (`uv run python -c "import litellm; print([m for m in litellm.model_cost if 'kimi' in m])"`)
and check its cost against Auggie's reported cost (`reported` in `load_job`
stats, or Harbor's cost in the status output). Entries in use:

| Model | Pricing entry | Note |
|---|---|---|
| GPT Luna 6 | `gpt-6-luna` | |
| GPT-6.1 Sol | `gpt-6.1-sol` | |
| Claude Sonnet 5.5 | `claude-sonnet-5-5` | |
| Claude Haiku 5.5 | `claude-haiku-5-5` | |
| Kimi K3 | `moonshot/kimi-k3` | LiteLLM has no plain `kimi-k3` entry |
| DeepSeek V4.1 Flash (`deepseek-4-1-flash-1017`) | `together_ai/deepseek-ai/DeepSeek-V4.1-Flash-1017` | $0.30 in, $1.20 out, $0.006 cached read per M; matches Auggie's reported cost |

## Check the page

Open `deepswe-pareto.html` and look at both axis modes. If labels overlap, set
the model's `"label": {"at": "<effort>", "offset": [dx, dy]}` in the JSON block
(`at` picks the labelled point, default last; `offset` is in pixels and draws a
leader line) and reload. Points outside the Fixed range are listed under the
chart rather than drawn.
