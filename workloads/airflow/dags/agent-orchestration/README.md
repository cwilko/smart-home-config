# Agent Orchestration

Runs Claude Code ("claudebox") agents as one-shot Kubernetes pods, scheduled and
wired up by Airflow. This doc covers the architecture end to end: why Airflow,
how agents are configured, storage, secrets, agent tools, and the operational
gotchas that actually broke this in production before they were understood.

## Why Airflow

This cluster already runs Airflow for its data-collection DAGs, so reusing it
here avoids standing up a second scheduler/queue/worker stack. Concretely, it's
doing the job management a bespoke system would otherwise need to reimplement:

- **Scheduling** — cron triggers for agents with no external event to react to
  (`scheduled_agents_dag.py`), and on-demand triggers for event-driven ones
  (`agent_router_dag.py`).
- **Concurrency control** — [Pools](#pools-and-concurrency) serialize
  invocations per agent so two runs never race against the same session state.
- **Retries, logging, a UI to see what ran and why** — all for free, rather
  than hand-rolled.
- **A durable task graph** — "create the PVCs and pools, *then* launch the
  pod" is naturally expressed as task dependencies, and failures at any step
  are visible per-task rather than buried in one opaque script.

Airflow is not running the agent's actual work — it's just the thing that
decides *when* a claudebox pod should exist and *what prompt* to hand it. All
the real work happens inside that pod, driven by Claude Code itself.

## Two paths in, one shared launch mechanism

```
   incoming event                         cron schedule
        │                                       │
        ▼                                       ▼
 agent_router_dag.py                  scheduled_agents_dag.py
 (schedule=None, triggered            (one Airflow DAG per
  externally per event)                "scheduled" entry in
        │                               agents.json)
        │ LLM classifies the
        │ event → agent_type
        │ + refined_task
        ▼                                       │
        └───────────────┬───────────────────────┘
                         ▼
              agent_lib.build_launch_task()
              (KubernetesPodOperator, shared
               by both paths — see below)
                         ▼
              one-shot claudebox pod
```

- **`agent_router_dag.py`** — event-driven. One DAG run per incoming event.
  This DAG does not listen for MQTT itself; a separate, external
  MQTT-to-Airflow bridge (**not built yet**) would subscribe to the relevant
  topic(s) and call `POST /api/v1/dags/agent_router/dagRuns` with the raw
  event payload as `conf`. A `@task.virtualenv` task (`route_event`) then
  classifies that payload with Gemini (`gemini-2.5-flash`, via
  `langchain-google-genai`, structured output against a Pydantic schema) into
  one of the configured `routed` agent types — or `none` — and derives a
  self-contained task prompt for whichever agent is chosen. A `@task.branch`
  task fans out to that agent's launch task (or a no-op `EmptyOperator` if
  nothing matched).
- **`scheduled_agents_dag.py`** — cron-driven. Dynamically builds one Airflow
  DAG per entry in `agents.json`'s `scheduled` section (via `globals()`
  assignment in a loop — standard Airflow pattern for "one DAG per config
  entry"). No event to classify, so it launches directly with a fixed
  `scheduled_task` prompt from the config.

Both converge on `agent_lib.build_launch_task()`, which builds the actual
`KubernetesPodOperator` — image, volumes, pool, env vars, the init container
that fetches the agent's skill config. The only thing that differs between the
two callers is the `arguments` list (where the prompt comes from); everything
else about how a claudebox pod gets launched is identical regardless of which
path triggered it.

## Agent configuration model

All agents are defined in `agents.json`, under exactly one of two sections —
an agent is event-reachable or cron-driven, not both, until there's an actual
case for needing either path:

```json
{
    "routed": {
        "<agent_type>": {"description": "..."}
    },
    "scheduled": {
        "<agent_type>": {"schedule": "0 3 * * 0", "scheduled_task": "..."}
    }
}
```

- **`routed`**: handled by `agent_router_dag.py`'s event-driven classifier.
  `description` feeds that classifier's prompt directly — write it for that
  audience ("what kinds of incoming events does this agent handle"), not for
  the agent itself. That's what each agent's own `skills/<agent_type>/SKILL.md`
  is for.
- **`scheduled`**: handled by `scheduled_agents_dag.py`, one Airflow DAG per
  entry here. `scheduled_task` is the fixed `-p` prompt used for those runs —
  there's no incoming event to derive one from.

Both DAGs discover their own section from `agents.json` at **DAG-parse time**
(`agent_lib.discover_routed_agents()` / `discover_scheduled_agents()`) — the
number of Pools/launch tasks (and, for `scheduled_agents_dag.py`, the number
of DAGs) is structurally needed at parse time and can't be deferred into a
task.

**Adding a new agent** is adding a new entry to the right section plus a
`skills/<agent_type>/SKILL.md` (and `.mcp.json` if it needs tools) — no DAG
code change needed. **Removing/disabling an agent** is deleting its entry.
**Moving an agent between the two models** is moving its entry from one
section to the other, swapping `description` for `schedule`/`scheduled_task`
(or vice versa).

### Why only `data_collector` exists today

Several other agent concepts were scoped during this project's design
conversation but aren't implemented yet:

- **Social media / Work assistant**: need new external credentials (social
  platform APIs, Slack/email/calendar) not yet wired up.
- **Family assistant**: a structurally different shape — "one agent per
  family member," not a single named bucket like the others — deferred
  pending that design.
- **Business leads/marketing**: no blocker, just not prioritized yet for this
  prototype.

## Agent skills (`skills/<agent_type>/`)

Each agent gets a folder with two files, both pure static config (no
agent-grown content lives here — that would need to survive across pods, and
these files are re-fetched fresh on every launch, see below):

- **`SKILL.md`** — the agent-facing instructions: what it's for, what it can
  and can't do, and how to use whatever tools its `.mcp.json` gives it.
  Claude Code auto-loads this from the workspace root.
- **`.mcp.json`** (optional) — MCP server definitions for this agent's tools.
  Auto-discovered from the workspace root since `claude -p` is invoked
  without `--bare`.

`data_collector` is the one implemented agent today: it compares
`cwilko/marketinsights-collector`'s documented pipeline coverage
(`resources/API_SOURCES.md`) against its own prior proposals
(`resources/CANDIDATE_SOURCES.md`), and if it finds a genuinely new,
undocumented data source, opens a pull request proposing it — gated to one
pending proposal at a time so the review queue never backs up. See
`skills/data_collector/SKILL.md` for the full instructions it operates under.

### Getting skill files into the pod

This is deliberately **not** the same mechanism that gets the DAG code itself
onto the cluster:

- **DAG code** (`agent_lib.py`, `agent_router_dag.py`, `scheduled_agents_dag.py`,
  `agents.json`) reaches the scheduler/worker pods via the `git-sync` sidecar
  already running on the Airflow deployment (polls `origin/master` every 60s)
  — see `workloads/airflow/deployment.yaml`.
- **Skill files** (`SKILL.md`/`.mcp.json`) are fetched by a dedicated init
  container (`fetch-skill-config`, `alpine/git:latest`) on the claudebox pod
  itself, on *every single launch* — a fresh shallow clone of this repo, every
  time, copying just that agent's two files into its workspace. Always
  overwrite, never seed-once: both files are pure git-authored config with
  nothing agent-grown left to protect, so there's no reason to special-case
  "first run vs. subsequent run."

This means a change to a `SKILL.md` takes effect on the very next launch of
that agent — no restart, no re-sync wait, since the init container always
pulls fresh from GitHub directly. A change to `agents.json` (DAG-parse-time
config) does need the scheduler's git-sync to catch up first (worst case ~60s).

## Storage

Two NFS-backed PVCs, shared across **every** agent rather than one PVC each
(`agent_lib.py`'s `ensure_storage()`, idempotent — a 409 on create means it
already exists, the expected steady state after the first run):

- `claudebox-workspaces-pvc` (5Gi) — mounted at `/workspace`.
- `claudebox-state-pvc` (2Gi) — mounted at `/home/aicode/.claude`, the Claude
  Code session-state directory `--continue` reads/writes.

Per-agent isolation comes from `subPathExpr` with `$(AGENT_TYPE)`, not from
separate PVCs — each agent gets its own subdirectory within both volumes.
Adding a new agent needs no new Kubernetes storage object at all.

This is **not local/ephemeral storage**: it persists across runs, which is
exactly what lets `--continue` resume an agent's prior Claude Code session
(the claudebox image's own behavior — `claudebox-agent` always adds
`--continue`) rather than starting cold every time.

### The NFS ownership gotcha

The underlying NFS export (TrueNAS) leaves new subdirectories owned by
`1003:100` with `root_squash` enabled — see
[Known issues / operational gotchas](#known-issues--operational-gotchas) for
why that broke the claudebox image outright, and how it's fixed.

## Secrets

One SealedSecret, `ai-secrets` (`workloads/airflow/secrets/ai-sealed-secrets.yaml`),
holding three keys, `envFrom`'d into the Airflow **worker** deployment
(`workloads/airflow/airflow-worker.yaml` — not the scheduler/webserver, since
that's where both `route_event` and the `KubernetesPodOperator` launch tasks
actually execute):

- `CLAUDE_CODE_OAUTH_TOKEN` — subscription-backed token (`sk-ant-oat01-...`,
  from `claude setup-token`), **not** an API key. This is what the real
  `claude` CLI inside each claudebox pod authenticates with, scoped only to
  Claude Code inference. Passed through explicitly as an env var on the
  `KubernetesPodOperator` (`agent_lib.build_launch_task`), since pod env vars
  don't inherit from the worker's own environment.
- `GEMINI_API_KEY` — a *separate* credential, for `route_event`'s classifier
  call (Gemini's free tier — no credit card, ~1500 req/day — a good fit for
  one small classification call per event). `ChatGoogleGenerativeAI` picks
  this up automatically from the environment; no explicit wiring needed
  beyond the worker's `envFrom`.
- `GITHUB_PERSONAL_ACCESS_TOKEN` — a fine-grained PAT scoped to one repo
  (`cwilko/marketinsights-collector`, for `data_collector` today). Also
  passed through explicitly as a pod env var. **Not** referenced directly in
  any `.mcp.json` — instead, a skill's `.mcp.json` uses `${GITHUB_PERSONAL_ACCESS_TOKEN}`
  and Claude Code's own CLI-only env substitution resolves it against the
  pod's environment at startup. This is the load-bearing reason nothing here
  ever commits a real secret value into a git-tracked `.mcp.json` — only the
  `${VAR}` placeholder lives in git.

The Airflow scheduler also needed one RBAC addition
(`workloads/airflow/af-rbac.yaml`) — `get`/`list`/`create` on
`persistentvolumeclaims` — for `ensure_storage()` to be able to create the two
PVCs above from inside a task.

## Agent tools (MCP)

Agents get capabilities through MCP servers declared in their `.mcp.json`,
auto-discovered from the workspace root. `data_collector`'s today:

- **`github`** — [`github/github-mcp-server`](https://github.com/github/github-mcp-server),
  fetched as a native binary release at container start (`curl | tar`, stdio
  transport) rather than via Docker-in-Docker. `GITHUB_TOOLSETS=repos,pull_requests`
  scopes it to only what this agent needs — reading files, listing/creating
  branches and PRs — nothing broader than that fine-grained PAT already
  allows.
- **`mqtt`** — [`eduard256/mqtt-mcp-server`](https://github.com/eduard256/mqtt-mcp-server),
  installed on the fly (`pip install -q mqtt-mcp-server`) and run over stdio.
  Chosen specifically *because* it's stdio, not HTTP — no persistent service
  to deploy, fits the one-shot ephemeral-pod model directly. Lets an agent
  **raise events** onto the same MQTT bus every other event-driven thing in
  this homelab already uses, rather than Airflow trying to capture and
  interpret Claude Code's stdout/XCom (fragile, and would need overriding the
  claudebox image's `cmds`, which is deliberately never done — see below).
  The actual topic convention an agent publishes to is documented in each
  agent's own `SKILL.md` (see `skills/data_collector/SKILL.md`'s "Raising an
  event" section) and in `MQTT_TOPICS.md` at the repo root, which is the
  canonical reference for this homelab's full set of MQTT conventions.

This event-raising model is deliberately decoupled from Airflow: any number
of independent subscribers (a Slack notifier, another agent, anything) can
act on an agent's findings without Airflow's task-return-value mechanics
being involved at all.

## The claudebox image, and why it's not `psyb0t/claudebox` directly

The pod template (`pod_templates/claudebox_pod_template.yaml`) runs
[`psyb0t/docker-claudebox`](https://github.com/psyb0t/docker-claudebox) (image
`psyb0t/claudebox`) — Claude Code CLI in a container, built on the
agent-agnostic [`psyb0t/docker-aicodebox`](https://github.com/psyb0t/docker-aicodebox)
base. Its `claudebox-entrypoint` must run **unmodified** — no `cmds=` override
on the `KubernetesPodOperator` — since it's what installs the Claude Code CLI
on first boot (not baked into the image; Anthropic's CLI is proprietary) and
dispatches to `claudebox-agent`, which adds `--continue` (resume this agent's
last session) and `--permission-mode bypassPermissions`.

In practice, though, the pod template points at
[`wilkobets/claudebox-k8s`](https://github.com/cwilko/claudebox-k8s) — a thin
derivative (`FROM psyb0t/claudebox:latest`, one file swapped) that patches a
real bug in the base image's entrypoint. See
[Known issues / operational gotchas](#known-issues--operational-gotchas)
below for what the bug actually is; the fix has also been filed upstream
([psyb0t/docker-aicodebox#1](https://github.com/psyb0t/docker-aicodebox/issues/1)).
`claudebox-k8s` rebuilds weekly (GitHub Actions, multi-arch) to stay current
with upstream `psyb0t/claudebox:latest`, plus on any push to its own `main`.

## Pools and concurrency

One 1-slot Airflow Pool per agent type (`agent_lib.ensure_pools()`, named
`agent_<agent_type>`), not a global concurrency limit. This exists because
`--continue` reads/writes that agent's live session-state subdirectory — two
concurrent pods for the *same* agent would race on that shared state.
Different agents run freely in parallel: separate pools, separate PVC
subdirectories, no shared state between them.

Pools are self-healing (`create_or_update_pool`, idempotent) and (re)created
at the top of every DAG run, before the branch/launch step — a task queued
against a pool that doesn't exist yet just sits stuck forever rather than
erroring, which is exactly the kind of silent failure this guards against.

## Known issues / operational gotchas

Three real bugs were hit (and fixed) getting this running for the first time
in production. Documented here because none of them fail loudly in an
obvious way — each one just left tasks sitting in `queued` or a pod silently
failing to start, with no clear error pointing at the actual cause.

1. **Every task needs `queue="celery"` explicitly.** This cluster's
   `CeleryKubernetesExecutor` does *not* default `AIRFLOW__OPERATORS__DEFAULT_QUEUE`
   to `"celery"` — Airflow's own built-in default queue name is literally
   `"default"`, and the Celery worker only ever subscribes to `"celery"`.
   Every task here (`@task`, `@task.branch`, `@task.virtualenv`, the
   `KubernetesPodOperator`, even the `EmptyOperator`) passes `queue="celery"`
   explicitly for exactly this reason — omit it on a new task and it will
   queue forever with no error, just `base_executor.py` logging
   `could not queue task ... (still running after N attempts)`. This matches
   the convention already used by every other DAG in this repo
   (`etf_pipeline_dag.py`, `econometrics_dag.py`, etc.) — it just wasn't
   obvious *why* until it broke.
2. **`Pool.create_or_update_pool()` needs `include_deferred=False`** on this
   Airflow version (2.9.3) — it's a required positional argument here, not
   optional. Omitting it raises `TypeError` at task *execution* time (not at
   DAG-parse time, so it doesn't show up as an Import Error — it only
   surfaces once the queue issue above is fixed and the task actually runs).
3. **The claudebox entrypoint can abort on a UID/GID collision.** The base
   `aicodebox` entrypoint tries to realign its `aicode` user's UID/GID to
   match whatever owns the mounted workspace (`stat`-based, so the agent's
   files look right if you went and inspected them from the host side) — but
   `groupmod`/`usermod` refuse by default to assign an ID already claimed by
   a *different* account. This cluster's NFS export leaves new directories
   owned by GID 100, which collides with Ubuntu's stock `users` group at that
   same GID — a near-guaranteed collision for *any* NFS/NAS setup using that
   common convention. The entrypoint treats the resulting `groupmod` failure
   as fatal (`set -e` + an `ERR` trap that just logs and dies), so the pod
   never starts, and `is_delete_operator_pod=True` means it also disappears
   before you can inspect it unless you catch it fast with
   `kubectl get pods -w`. Two things worth noting if this resurfaces:
   - A plain `chown` workaround from an init container **does not work**
     here — this NFS export has `root_squash` enabled, so `chown` as root
     from inside any pod is silently rejected server-side.
   - The real fix (`-o`/`--non-unique` on the `groupmod`/`usermod` calls) is
     baked into `wilkobets/claudebox-k8s` (see above) and filed upstream at
     [psyb0t/docker-aicodebox#1](https://github.com/psyb0t/docker-aicodebox/issues/1).
