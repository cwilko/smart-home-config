import os
import sys

import pendulum
from airflow.decorators import dag, task

# Airflow doesn't reliably put a DAG file's own directory on sys.path, so a
# plain `import agent_lib` isn't guaranteed to resolve even though the file
# sits right next to this one — add it explicitly rather than rely on that.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agent_lib  # noqa: E402

# One Airflow DAG per agent that has a "schedule" entry in agents.json —
# for agents with nothing external to react to (e.g. "periodically look for
# new data sources"), not every agent needs one. Unlike agent_router_dag.py
# (event-driven, classifies an incoming payload), there's no event here to
# classify, so this skips route_event/choose_agent entirely and launches
# with the fixed "scheduled_task" prompt from agents.json instead.
_scheduled_agents = agent_lib.discover_scheduled_agents()


def _build_scheduled_agent_dag(agent_type: str, schedule: str, scheduled_task: str):
    @dag(
        dag_id=f"scheduled_agent_{agent_type}",
        schedule=schedule,
        start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
        catchup=False,
        max_active_runs=1,
        tags=["agent-orchestration", "scheduled"],
    )
    def scheduled_agent():
        f"""
        ### Scheduled launch — {agent_type}

        Cron-triggered launch of the `{agent_type}` claudebox container with
        a fixed prompt (agents.json's "scheduled_task" for this agent) —
        see agent_router_dag.py for the event-driven path this skips.
        """

        @task
        def ensure_agent_pools():
            agent_lib.ensure_pools([agent_type])

        @task
        def ensure_agent_storage():
            agent_lib.ensure_storage()

        pools_ready = ensure_agent_pools()
        storage_ready = ensure_agent_storage()

        launch_agent = agent_lib.build_launch_task(
            agent_type,
            arguments=["-p", scheduled_task, "--output-format", "json"],
        )

        [pools_ready, storage_ready] >> launch_agent

    return scheduled_agent()


for _agent_type, _entry in _scheduled_agents.items():
    globals()[f"scheduled_agent_{_agent_type}"] = _build_scheduled_agent_dag(
        agent_type=_agent_type,
        schedule=_entry["schedule"],
        scheduled_task=_entry["scheduled_task"],
    )
