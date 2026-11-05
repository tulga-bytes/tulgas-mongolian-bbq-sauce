---
name: download-dev-box-jobs
description: Download or refresh benchmark jobs from the user's dev-box into this workspace and group them into viewer jobs. Use when asked to fetch a run by name or ID, download new or finished jobs, or sync all jobs locally.
---

# Download benchmark jobs from dev-box

## Connection and paths

- Connect using the user's `dev-box` command, available in interactive zsh.
- Remote jobs: `/home/augment/Workspace/bench-maxxing/jobs/`.
- Local jobs: `jobs/` under this workspace root.
- The previously supplied `/Workspace/bench-maxxing` was not an absolute remote
  path: the actual project is under `/home/augment/Workspace/bench-maxxing`.
- Run commands from the workspace root. This skill's `scripts/ssh_transport.py`
  forwards rsync's remote command through `/bin/zsh -ic` and the existing alias,
  so connection settings and credentials stay outside the skill.
- Remote runs are named job folders, usually `<group>/<variant>`, for example
  `gpt-6.1-sol sweep/low` or `gpt-6-1-sol deep-swe-1-1 prompt-iteration-3a/xhigh-no-subagents`.
  Retries of a variant are separate jobs named `<variant>-retry`. Older runs use
  timestamp IDs such as `2026-10-06__14-10-00`.

## Local layout

The viewer (`http://127.0.0.1:8080/jobs/<job>`) treats every subfolder of a job as
a trial, so nested `<group>/<variant>/` folders display as one pending trial. Local
runs are therefore kept as **grouped jobs**: one folder per group with all trials at
the top level, produced by `scripts/group_jobs.py`:

```text
jobs/<group>/
  <task>__<id>/                    trials from every variant, agent relabelled <agent>-<variant>
  config.json, result.json         combined config and stats
  grouping.json                    source job, variant, and trial list for each grouped run
  original-jobs/<agent>/<variant>/ the run's config.json, result.json, job.log, lock.json
    retry/                         the retry job's metadata, if a retry was merged
    unused/                        replaced or unreadable trial folders, kept for reference
```

Current groups:

| Local group | Remote source | `--agent` | Variants |
|---|---|---|---|
| `Prompt Iteration 2 on 6.1 Sol` | `gpt-6-1-sol deep-swe-1-1 prompt-iteration-2/*` | `auggie` | `medium`, `high`, `max`, and `*-no-subagents` |
| `Prompt Iteration 3a on 6.1 Sol (Pareto)` | `gpt-6-1-sol deep-swe-1-1 prompt-iteration-3a/*` | `auggie` | `<effort>-no-subagents` |
| `Prompt Iteration 3b on 6.1 Sol` | `gpt-6-1-sol deep-swe-1-1 prompt-iteration-3b/*` | `auggie` | `<effort>-no-subagents` |
| `Prompt Iteration 4 on 6.1 Sol` | `gpt-6-1-sol prompt-iteration-4a max deep-swe-1-1` | `auggie` | `max-prompt-iteration-4a` (plus `medium-no-subagents`, combined from 30+83 runs) |
| `Claude Sonnet 5-5 sweep (Pareto)` | `claude-sonnet-5-5 prompt-iteration-4 <effort> deep-swe-1-1` | `auggie` | `<effort>-prompt-iteration-4` for `low`, `medium`, `high`, `xhigh`, `max` |
| `Claude Sonnet 5-5 Claude Code Sweep` | `claude-sonnet-5-5 claude-code <effort> deep-swe-1-1` | `claude-code` | `low`, `medium`, `high`, `xhigh`, `max` |
| `gpt-6.1-sol sweep` | `gpt-6.1-sol sweep/*` | `codex` | `low`, `medium`, `high`, `xhigh` |
| `gpt-6-luna sweep` | `gpt-6-luna sweep/*` | `auggie` | `none`, `low`, `medium`, `high`, `xhigh`, `max` |
| `Prompt Iteration 4a on GPT Luna 6` | `gpt-6-luna prompt-iteration-4a sweep/*` | `auggie` | `low`, `medium`, `high`, `xhigh`, `max` |

For a new group, ask the user for the local name. Single timestamp-ID runs that are
already flat (trials at the top level) need no grouping.

## Workflow

1. Determine the requested scope: a specific run, new runs, or all jobs. Do not
   sync every job if the user asked for just one. Before inserting a job name into
   shell commands, reject names that start with `/`, contain `..`, quotes,
   backslashes, or newlines. For "latest" or "new", list remote directory names
   and compare with `grouping.json` source jobs and local names instead of guessing.
   Download only finished jobs (`finished_at` set in the job's `result.json`) unless
   the user asks for a snapshot of a running job; never group a running job.
2. Check the remote directory with `dev-box`, using an interactive zsh command.
   List only names, sizes, and counts; do not print logs, session contents,
   credentials, `.env`, or shell/SSH configuration. Confirm the local destination
   is inside this workspace (not a symlink to somewhere else), and check free
   disk space. Read-only remote discovery can use:

   ```bash
   /bin/zsh -ic 'dev-box "ls -1 /home/augment/Workspace/bench-maxxing/jobs; du -sh /home/augment/Workspace/bench-maxxing/jobs"'
   df -h .
   ```

3. Use rsync with the bundled transport. The remote shell prints a startup line
   such as `Agent pid 12345`, breaking ordinary rsync **and SFTP/scp**. The helper
   strips only this known line and forwards all other bytes unchanged. Unexpected
   banners should cause a transfer failure, not be silently discarded. Never run
   the helper directly: its stdout is a binary rsync stream.
4. Set `SRC` to the remote job path relative to `jobs/` and `DST` to the local
   destination. For grouped runs, `DST` is `<local group>/<variant>` (or
   `<local group>/<variant>-retry`), even if the group already exists. Spaces in the
   remote path must be backslash-escaped for rsync. Preview the transfer:

   ```bash
   SRC="gpt-6.1-sol sweep/xhigh"; DST="gpt-6.1-sol sweep/xhigh"; R="${SRC// /\\ }"
   mkdir -p "jobs/$DST"
   rsync -an --stats -e "python3 $HOME/.agents/skills/download-dev-box-jobs/scripts/ssh_transport.py" "dev-box:/home/augment/Workspace/bench-maxxing/jobs/$R/" "jobs/$DST/"
   ```

   Never rsync a remote group folder onto a grouped local job root: grouping moves
   files, so rsync would re-create the nested variant folders.

5. Preserve existing local jobs. Keep all temporary files under `/tmp`, never in
   the workspace: create one unique temporary directory for the download, put
   backups of replaced files and any scratch output (rsync stats, error logs) in
   it, then perform the transfer:

   ```bash
   tmp_dir=$(mktemp -d /tmp/dev-box-jobs.XXXXXX)
   backup_dir="$tmp_dir/backup"
   rsync -ab --backup-dir="$backup_dir" --stats -e "python3 $HOME/.agents/skills/download-dev-box-jobs/scripts/ssh_transport.py" "dev-box:/home/augment/Workspace/bench-maxxing/jobs/$R/" "jobs/$DST/"
   ```

   Check the rsync exit status before proceeding. For an explicitly requested
   full sync, use the remote `jobs/` root and local `jobs/`, both with trailing
   slashes. For new jobs only, transfer each missing run separately. Never use
   `--delete`, remove remote data, overwrite authentication settings, or change
   remote shell startup files.
6. Verify using `rsync -ani` with the same transport, source, and destination.
   Zero exit status alone is not enough: inspect itemized changes. For a finished
   run, require no differences; use `-anci` for a checksum comparison when the
   user explicitly requests content verification. Check the expected run
   directories and, where relevant, completed trial counts in `result.json`
   using an allowlist of numeric fields rather than dumping the file.
7. A running job can change between transfer and verification. If all remaining
   differences belong to an active run, refresh it once, verify completed runs
   separately, and clearly report the active run as a snapshot. Do not repeatedly
   chase changing logs or claim an exact match for a live run.
8. Group verified runs. Download every variant and its `-retry` job (if any) for
   the group first, then run, for example:

   ```bash
   uv run python ~/.agents/skills/download-dev-box-jobs/scripts/group_jobs.py "jobs/gpt-6.1-sol sweep" --agent codex xhigh
   ```

   The script refuses unfinished jobs and variants already in `grouping.json`, and
   adds new variants to an existing group. For each task it keeps one trial,
   preferring a scored one, then a readable one, then the original; replaced and
   empty or corrupt records go to `unused/`. When combining a `deep-swe-1-1-30`
   run with its `deep-swe-1-1-83` remainder, add `--full-set` (see the `deepswe-sets` skill).
   Check the printed per-variant trial,
   error, and pass counts, then confirm the viewer shows the same counts:

   ```bash
   curl -s "http://127.0.0.1:8080/api/jobs/<url-encoded group>" | python3 -c "import json,sys;r=json.load(sys.stdin);print(r['n_total_trials'],r['stats']['n_errored_trials'],list(r['stats']['evals']))"
   ```

9. Clean up: once transfer, verification, and grouping have all succeeded,
   remove the temporary directory with `rm -rf "$tmp_dir"` (only that
   `/tmp/dev-box-jobs.*` path). If any step failed and the backup holds replaced
   files, keep it and report its path instead.
10. Summarize the downloaded runs, local destination, verification performed,
   grouping results, cleanup or any retained backup, and any failures or
   active-run limitations. Do not claim success after a failed transfer or
   unresolved verification mismatch.

## Troubleshooting

- If `dev-box` is not found, check `/bin/zsh -ic 'whence -w dev-box'`. Do not dump
  alias definitions, shell startup files, SSH configuration, or authentication.
- The rsync remote source must be `dev-box:...`, not `user@dev-box:...`; the alias
  already selects the user and host. The helper rejects other rsync targets.
- Requirements: local Python 3, zsh, rsync, working dev-box authentication, and
  remote rsync. Do not install new dependencies without permission.
- Keep tool output metadata-only. Downloaded job artifacts may contain sensitive
  session data; never print their raw contents while transferring or verifying.
