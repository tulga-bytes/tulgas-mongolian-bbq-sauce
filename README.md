# tulgas-mongolian-bbq-sauce

A plugin with my agent skills.

## Skills

| Skill | What it does |
|---|---|
| `run-dev-box-evals` | Asks which dataset, model, and efforts to run, then launches Auggie evals on a dev-box with Daytona sandboxes, reports their status, and adds finished runs to a pass-rate-vs-cost chart. |
| `download-dev-box-jobs` | Downloads benchmark jobs from a dev-box into the local `jobs/` folder and groups them into viewer jobs. |

Both skills expect a `dev-box` shell command and the bench-maxxing Harbor workspace on the dev-box. `run-dev-box-evals` also uses the `deepswe-sets` and `deepswe-pareto` skills, which live in the bench-maxxing repository under `.agents/skills/`.

## Install

Copy a folder from `skills/` into your agent's skills directory.
