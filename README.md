# tulgas-not-so-secret-sauce

A plugin with my agent skills.

## Skills

| Skill | What it does |
|---|---|
| `run-dev-box-evals` | Asks which dataset, model, and efforts to run, then launches Auggie evals on a dev-box with Daytona sandboxes, reports their status, and adds finished runs to a pass-rate-vs-cost chart. |

`run-dev-box-evals` expects a `dev-box` shell command, a Harbor benchmark workspace on the dev-box, and the `download-dev-box-jobs` and `effort-sweep-report` skills. Those are not in this repository.

## Install

Claude Code:

```text
/plugin marketplace add tulga-bytes/tulgas-not-so-secret-sauce
/plugin install tulgas-not-so-secret-sauce@tulgas-not-so-secret-sauce
```

Or copy a folder from `skills/` into your agent's skills directory.
