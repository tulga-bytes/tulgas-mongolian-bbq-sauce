---
name: deepswe-sets
description: Choose which DeepSWE 1.1 task set to run (30-task sample, 83-task remainder, full 113, small 10), reuse a matching 30-task run so a full run only needs the other 83, and combine the two into one 113-task result. Use before launching any DeepSWE eval and when grouping a 30-task and an 83-task job.
---

# DeepSWE sets

Run from the bench-maxxing workspace root. The dev-box copy is
`/home/augment/Workspace/bench-maxxing`.

## Sets

| Set | Path | Tasks |
|---|---|---|
| Full | `benchmarks/deep-swe-1-1` | 113 |
| 30-task sample | `benchmarks/deep-swe-1-1-30` | 30, `random.Random(42).sample` of the full set |
| Remainder | `benchmarks/deep-swe-1-1-83` | the other 83 |
| Small | `benchmarks/deep-swe-1-1-10` | first 10 alphabetically |

`deep-swe-1-1-30` and `deep-swe-1-1-83` do not overlap and together equal the
full set. All tasks are identical copies, and each `dataset.toml` pins the task
digests.

## Choose a set

1. **Tests and experiments** (new prompts, builds, or options): run individual
   tasks or `deep-swe-1-1-30`.
2. **Full run requested**: look for an existing `deep-swe-1-1-30` run with
   exactly the same setup. If one exists, run only `deep-swe-1-1-83` and
   combine the two. Run `benchmarks/deep-swe-1-1` only when no such run exists.

Search both local `jobs/` and the dev-box `jobs/`. A run counts as the same
setup only if all of these match:

- The finished job's `config.json` `agents` entry: agent `name`, `model_name`,
  and every `kwargs` value (for Auggie: `reasoning_effort`, `version`,
  `system_prompt_path`, `disable_subagents`, and any other option).
- Any prompt file the run used is unchanged since then. Compare checksums with
  git history or the dev-box copy.
- The environment (`-e daytona`; earlier `environments.gcp:GKENodepool` runs
  do not match) and the dataset
  (`benchmarks/deep-swe-1-1-30`).

An unpinned agent `version` never matches, since the installed build may have
changed. If anything differs or is unclear, treat it as no prior run and say why.

Name the remainder job after the 30-task job, with `deep-swe-83` in place of
`deep-swe-30`, for example `claude-haiku-5-5 prompt-iteration-4 deep-swe-83`.
Use the same command and options as the 30-task run, changing only `-p` and
`--job-name`.

## Combine a 30-task and an 83-task run

1. Download both finished jobs into one local group with the
   `download-dev-box-jobs` skill: the 30-task job as `jobs/<group>/<variant>/`
   and the 83-task job as `jobs/<group>/<variant>-retry/`.
2. Group them with `--full-set`:

   ```bash
   uv run python ~/.agents/skills/download-dev-box-jobs/scripts/group_jobs.py "jobs/<group>" --agent auggie <variant> --full-set
   ```

   The retry merge keeps one trial per task, so the two sets combine into one
   113-trial variant. `--full-set` records every trial, and the group's
   `config.json`, as `benchmarks/deep-swe-1-1`, so the result reads as one full
   run. `original-jobs/` keeps the two source jobs' own metadata.
3. Check that the variant has 113 trials under a single `…__deep-swe-1-1` entry
   in the group's `result.json`, and report results over all 113 tasks. Say
   that the two halves ran at different times, since API load can affect agent
   time.
