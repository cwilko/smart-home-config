# agent_router

Two DAGs share this folder's agent config and plumbing (`agent_lib.py`):

- **`agent_router_dag.py`** — event-driven. Triggered externally per incoming event
  (not built yet — see a future MQTT-to-Airflow bridge), classifies it with an LLM,
  launches the matching agent.
- **`scheduled_agents_dag.py`** — cron-driven, one Airflow DAG per agent that has a
  `schedule` in `agents.json`. No event to classify, so it launches with a fixed
  `scheduled_task` prompt instead. Not every agent needs one of these.

## Agent config

All agents are defined in `agents.json`, under exactly one of two sections — an
agent is event-reachable or cron-driven, not both, until there's an actual case for
needing either path:

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
  audience ("what kinds of incoming events does this agent handle"), not for the
  agent itself. That's what each agent's own `skills/<agent_type>/SKILL.md` is for.
- **`scheduled`**: handled by `scheduled_agents_dag.py`, one Airflow DAG per entry
  here. `scheduled_task` is the fixed `-p` prompt used for those runs — there's no
  incoming event to derive one from.

**Adding a new agent** is adding a new entry to the right section — no DAG code
change needed. Both DAGs discover their own section from `agents.json` at
DAG-parse time (see `agent_lib.discover_routed_agents()` /
`discover_scheduled_agents()`); `agent_router_dag.py` builds one Pool and one
launch task per `routed` entry, `scheduled_agents_dag.py` builds one DAG per
`scheduled` entry.

**Removing/disabling an agent** is deleting its entry. **Moving an agent between
the two models** is moving its entry from one section to the other, swapping
`description` for `schedule`/`scheduled_task` (or vice versa).

## Why only `data_collector` exists today

Several other agent concepts were scoped during this project's design conversation
but aren't implemented yet:

- **Social media / Work assistant**: need new external credentials (social platform
  APIs, Slack/email/calendar) not yet wired up.
- **Family assistant**: a structurally different shape — "one agent per family
  member," not a single named bucket like the others — deferred pending that design.
- **Business leads/marketing**: no blocker, just not prioritized yet for this
  prototype.

See conversation/commit history for the full reasoning; not reproduced here since
it'll go stale.
