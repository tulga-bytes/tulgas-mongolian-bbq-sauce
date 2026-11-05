#!/usr/bin/env bash
# Runs on the dev-box: bash -s -- MODEL DATASET PROMPT EFFORT... < launch.sh
# DRY_RUN=1 prints each job and command without launching.
set -euo pipefail
(( $# >= 4 )) || { echo "usage: MODEL DATASET PROMPT EFFORT..." >&2; exit 2; }
model=$1 dataset=$2 prompt=$3
shift 3
cd /home/augment/Workspace/bench-maxxing

[[ $model =~ ^[a-z0-9][a-z0-9.-]*$ ]] || { echo "invalid model: $model" >&2; exit 2; }
[[ $dataset =~ ^[a-z0-9][a-z0-9.-]*$ && -d benchmarks/$dataset ]] || { echo "unknown dataset: $dataset" >&2; exit 2; }
[[ $prompt =~ ^[a-z0-9_]+$ && -f prompts/$prompt.md ]] || { echo "unknown prompt: $prompt" >&2; exit 2; }
for effort; do
  [[ $effort =~ ^(none|low|medium|high|xhigh|max)$ ]] || { echo "invalid effort: $effort" >&2; exit 2; }
done
grep -q '^DAYTONA_API_KEY=' .env || { echo "DAYTONA_API_KEY missing from .env" >&2; exit 2; }

case $dataset in
  deep-swe-1-1-30) tag=deep-swe-30 ;;
  deep-swe-1-1-83) tag=deep-swe-83 ;;
  deep-swe-1-1-10) tag=deep-swe-10 ;;
  *) tag=$dataset ;;
esac
ptag=${prompt//_/-}

for effort; do
  job="$model $effort $ptag daytona-10gb $tag"
  session="${model//./-}-$ptag-$effort-daytona"
  if [[ -e "jobs/$job" ]]; then echo "skip, job exists: $job"; continue; fi
  if tmux has-session -t "=$session" 2>/dev/null; then echo "skip, tmux session exists: $session"; continue; fi
  cmd=(uv run harbor run --env-file .env -n 50 -y
    -m "$model" --ak "reasoning_effort=$effort" --ak "system_prompt_path=prompts/$prompt.md"
    -p "benchmarks/$dataset" -a agents.auggie:AuggieAgent -e daytona --job-name "$job")
  if [[ ${DRY_RUN:-} == 1 ]]; then
    printf 'would launch [%s]:' "$session"; printf ' %q' "${cmd[@]}"; echo
    continue
  fi
  tmux new-session -d -s "$session" -c "$PWD" "$(printf '%q ' "${cmd[@]}"); exec bash"
  echo "launched [$session]: $job"
done
