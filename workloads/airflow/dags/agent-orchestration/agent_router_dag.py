import pendulum
from airflow.decorators import dag, task
from airflow.operators.empty import EmptyOperator

import agent_lib

# Agents are discovered from a config file, not hardcoded — see README.md.
# Shared plumbing (pod template, PVCs, pool/launch-task construction) lives
# in agent_lib.py, alongside scheduled_agents_dag.py's cron-triggered path.
NONE_AGENT_TYPE = "none"
_NONE_DESCRIPTION = "The event doesn't match any currently-implemented agent's scope."

_routed_agents = agent_lib.discover_routed_agents()
AGENT_TYPES = list(_routed_agents)
AGENT_DESCRIPTIONS = {**_routed_agents, NONE_AGENT_TYPE: _NONE_DESCRIPTION}
NO_MATCH_TASK_ID = "no_agent_matched"


@dag(
    schedule=None,
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    max_active_runs=10,
    tags=["agent-orchestration"],
)
def agent_router():
    """
    ### Agent Orchestration Router

    One DAG run per incoming event — this DAG does not listen for MQTT
    itself. A separate, external MQTT-to-Airflow bridge (not built yet)
    subscribes to the relevant topic(s) and calls
    `POST /api/v1/dags/agent_router/dagRuns` with the raw MQTT payload as
    `conf` for each message.

    Flow: an LLM classifies the event into one of the agent types below,
    then that agent's claudebox container
    (https://github.com/psyb0t/docker-claudebox, image psyb0t/claudebox:latest)
    is launched as a one-shot Kubernetes pod. The pod's own ENTRYPOINT
    (claudebox-entrypoint) must run unmodified — it installs the Claude Code
    CLI on first boot (not baked into the image, since Anthropic's CLI is
    proprietary) and dispatches `-p "<task>" --output-format json` to
    `claudebox-agent`, which adds --continue (resume this agent's last
    session) and --permission-mode bypassPermissions. Do not override `cmds`.

    For agents that run on a schedule instead of reacting to an event (no
    incoming payload to classify), see scheduled_agents_dag.py — it skips
    this DAG's classifier entirely and launches with a fixed prompt instead.
    """

    @task
    def ensure_agent_pools():
        """
        Idempotently (re)create the per-agent pools this DAG relies on to
        serialize invocations against each agent's session-state subdirectory.
        Runs once per DAG run (i.e. per event) — cheap no-op after the first
        time, self-healing if a pool is ever deleted. Must run before the
        branch below: a task queued against a pool that doesn't exist yet
        just sits stuck, it doesn't error.
        """
        agent_lib.ensure_pools(AGENT_TYPES)

    @task
    def ensure_agent_storage():
        """
        Idempotently create the two shared NFS-backed PVCs every agent's
        launch task mounts (via subPathExpr, not a dedicated PVC each).
        Runs once per DAG run; a 409 means it already exists, which is the
        expected steady state. Must run before the branch below, same
        reasoning as ensure_agent_pools.
        """
        agent_lib.ensure_storage()

    @task.virtualenv(
        task_id="route_event",
        requirements=["langchain-google-genai"],
        system_site_packages=False,
    )
    def route_event(agent_descriptions: dict[str, str], **context) -> dict:
        """Classify the incoming event and decide which agent should handle it, if any."""
        from typing import Literal, Optional

        from langchain_core.messages import HumanMessage
        from langchain_google_genai import ChatGoogleGenerativeAI
        from pydantic import BaseModel, Field

        # Uses Google's Gemini API free tier (Flash/Flash-Lite, no credit
        # card, ~1500 req/day via AI Studio) rather than a paid Anthropic
        # key — classification is a single small call per event, a good fit
        # for the free quota. Separate credential from the claudebox agents'
        # CLAUDE_CODE_OAUTH_TOKEN below, though both now live in the same
        # `ai-secrets` SealedSecret (workloads/airflow/secrets/ai-sealed-secrets.yaml).
        # ChatGoogleGenerativeAI picks up GEMINI_API_KEY from the environment
        # automatically (its documented fallback for GOOGLE_API_KEY) — set via
        # ai-secrets, envFrom'd into the Airflow worker in airflow-worker.yaml.
        class RoutingDecision(BaseModel):
            agent_type: Literal[tuple(agent_descriptions)]
            refined_task: Optional[str] = Field(
                default=None,
                description=(
                    "A clear, self-contained task description for the chosen agent to execute. "
                    "Omit when agent_type is 'none'."
                ),
            )

        raw_payload = context["dag_run"].conf
        descriptions_block = "\n".join(f"- {name}: {desc}" for name, desc in agent_descriptions.items())

        model = ChatGoogleGenerativeAI(model="gemini-2.5-flash").with_structured_output(
            RoutingDecision, method="json_schema"
        )
        decision = model.invoke(
            [
                HumanMessage(
                    content=(
                        "Analyze this incoming smart-home automation event and decide which "
                        f"agent should handle it, if any: {raw_payload}\n\n"
                        f"Available agent types:\n{descriptions_block}"
                    )
                )
            ]
        )

        return decision.model_dump()

    @task.branch
    def choose_agent(routing_decision: dict) -> str:
        if routing_decision["agent_type"] == NONE_AGENT_TYPE:
            return NO_MATCH_TASK_ID
        return agent_lib.launch_task_id(routing_decision["agent_type"])

    pools_ready = ensure_agent_pools()
    storage_ready = ensure_agent_storage()
    routing_decision = route_event(agent_descriptions=AGENT_DESCRIPTIONS)
    branch = choose_agent(routing_decision)
    [pools_ready, storage_ready] >> branch

    no_agent_matched = EmptyOperator(task_id=NO_MATCH_TASK_ID)
    branch >> no_agent_matched

    for agent_type in AGENT_TYPES:
        launch_agent = agent_lib.build_launch_task(
            agent_type,
            arguments=[
                "-p",
                "{{ ti.xcom_pull(task_ids='route_event')['refined_task'] }}",
                "--output-format",
                "json",
            ],
        )
        branch >> launch_agent


agent_router()
