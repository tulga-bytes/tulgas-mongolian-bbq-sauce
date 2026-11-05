---
name: run-dev-box-evals
description: Launch, monitor, download, and chart Auggie evals that run on the dev-box with Daytona sandboxes. Use for "run evals", "kick off <model> at <effort>", "check eval status", "what's running on the dev-box", or adding a finished run to deepswe-pareto.html.
---

# Run dev-box evals

Evals run on the dev-box in tmux, one Harbor job per model and effort, on Daytona
(`-e daytona`) with 50 concurrent trials. Fixed setup: Auggie
(`agents.auggie:AuggieAgent`) with `prompts/prompt_iteration_4a.md`. Use a
different prompt only when the user names one.

Run every command from the local workspace root. Set `S` to the `scripts/`
folder next to this `SKILL.md`. Reach the dev-box only through
`/bin/zsh -ic 'dev-box "…"'`, as in `download-dev-box-jobs`. Filter its startup
lines with `grep -v -e '^Agent pid' -e '^Identity added'`. Never print `.env`,
logs, or session contents.

## 1. Ask what to run

Skip this step for status-only requests. Otherwise ask with `ask-user`, even when
the request seems to answer a question. Confirm the parsed value as the
recommended option.

1. First call, two questions:
   - **Dataset.** Options: `deep-swe-1-1-30` (recommended for experiments),
     `deep-swe-1-1` (full), `deep-swe-1-1-small`, `deep-swe-1-1-83`. Other
     folders under `benchmarks/` can be typed.
   - **Model.** Run `auggie models list --json` locally. Offer up to three
     models with non-empty `selectableEffortLevels`, starting with the ones in
     recent jobs. Other models can be typed. Reject a typed model that isn't in
     the list.
2. Second call, after the model is known:
   - **Efforts.** Offer only that model's `selectableEffortLevels`. With four
     or fewer, use `multiSelect: true` with one option per level. With more,
     use single-select presets ("All supported levels", plus two subsets that
     fit the request). The user can type a custom list.
3. For `deep-swe-1-1`, apply the reuse rule in the `deepswe-sets` skill. When a matching
   `deep-swe-1-1-30` run exists, launch `deep-swe-1-1-83` instead and say which
   30-task job it completes.

## 2. Launch

Dry-run first. Show the user the output, then launch:

```bash
/bin/zsh -ic "dev-box 'DRY_RUN=1 bash -s -- MODEL DATASET prompt_iteration_4a EFFORT...' < $S/launch.sh"
/bin/zsh -ic "dev-box 'bash -s -- MODEL DATASET prompt_iteration_4a EFFORT...' < $S/launch.sh"
```

`launch.sh` validates its inputs and checks that `DAYTONA_API_KEY` is set
(the value is never printed). It names each job
`<model> <effort> prompt-iteration-4a daytona-10gb <dataset tag>`. The tag is
`deep-swe-1-1`, `deep-swe-30`, `deep-swe-83`, or `deep-swe-small`. It skips jobs
and tmux sessions that already exist, and it starts one tmux session per effort.
All efforts run at the same time. If many trials error with sandbox or rate
limits, launch the remaining efforts one at a time.

## 3. Status

```bash
/bin/zsh -ic "dev-box 'python3 - [FILTER]' < $S/status.py"
```

Each line shows the state, trials done, errors, passes, Harbor's cost, the
model, the effort, and the prompt. `STALLED` means the job is unfinished and
hasn't updated in 30 minutes. Report stalled jobs to the user. Don't relaunch
them or mark them finished without asking. Compare finished jobs with local
`jobs/*/grouping.json` sources to list the ones not yet downloaded.

## 4. Download and group

Follow the `download-dev-box-jobs` skill. For a new model, name
the group `Prompt Iteration 4a on <Model> (Pareto)`. Download into
`<group>/<effort>` and run `group_jobs.py` with `--agent auggie`. Add
`--full-set` when combining 30 and 83.

## 5. Add to `deepswe-pareto.html`

Follow the `deepswe-pareto` skill in this plugin. Its
`pareto.py add` writes the job's full-set points into the chart's JSON block;
the skill lists the LiteLLM price entry per model and how to pick one for a new
model.
