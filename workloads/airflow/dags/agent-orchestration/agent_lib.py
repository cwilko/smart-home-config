"""
Shared plumbing for this folder's DAGs — agent_router_dag.py (event-driven,
classifies an incoming payload) and scheduled_agents_dag.py (cron-triggered,
no incoming event to classify, launches with a fixed prompt instead).

Not a DAG itself — Airflow's parser finds no DAG objects here and skips it.
Lives alongside the DAG files that import it (not a package), relying on
Airflow inserting each DAG file's own directory onto sys.path at parse time.
"""

import json
import os

from airflow.models import Pool
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from kubernetes.client import models as k8s

_DAG_DIR = os.path.dirname(os.path.abspath(__file__))

# Image is psyb0t/claudebox:latest (Docker Hub, multi-arch) — pinned in
# pod_templates/claudebox_pod_template.yaml, not here.
#
# All agents share two NFS-backed PVCs (a workspace volume and a Claude
# session-state volume) rather than getting one PVC each — each agent gets
# its own subdirectory within them via subPathExpr on the launch tasks
# below. Adding a new agent needs no new Kubernetes object.
POD_TEMPLATE_FILE = os.path.normpath(os.path.join(_DAG_DIR, "..", "..", "pod_templates", "claudebox_pod_template.yaml"))
AGENT_NAMESPACE = "automation"
WORKSPACES_PVC = "claudebox-workspaces-pvc"
STATE_PVC = "claudebox-state-pvc"

# Agents are discovered from a config file, not hardcoded — see README.md.
AGENTS_CONFIG_FILE = os.path.join(_DAG_DIR, "agents.json")

# Public repo — each agent's SKILL.md/.mcp.json are fetched fresh from here into
# its workspace on every launch (see build_launch_task's init container). Both
# files are pure static config now (the one piece of agent-grown content,
# data_collector's source catalog, moved to a GitHub PR flow instead), so
# always-overwrite is safe — there's nothing agent-accumulated left to protect.
SKILLS_GIT_REPO = "https://github.com/cwilko/smart-home-config.git"
SKILLS_GIT_PATH = "workloads/airflow/dags/agent-orchestration/skills"


def _load_agents_config() -> dict:
    """
    Parse agents.json: two top-level sections, each with consistent fields
    within it — {"routed": {"<agent_type>": {"description": ...}, ...},
    "scheduled": {"<agent_type>": {"schedule": ..., "scheduled_task": ...}, ...}}.
    An agent belongs to exactly one section: event-reachable (routed, no
    incoming-event trigger exists for it otherwise) or cron-driven
    (scheduled) — not both, until there's an actual case for an agent
    needing either path.

    Runs at DAG-parse time in both consumer DAGs, not task-run time, unlike
    every other config read in this repo — the number of Pools/launch tasks
    (and, for scheduled_agents_dag.py, the number of DAGs) is structurally
    needed at parse time and can't be deferred into a task.

    A missing file is treated as a config/deploy error and raises (surfaces
    loudly as an Airflow Import Error, in whichever DAG parses it first). A
    missing "routed" or "scheduled" key, or either being empty ({}), is
    tolerated — zero agents in a given category is a legitimate state, not
    an error. Malformed JSON, or a missing required key within an entry
    (e.g. "description", or "scheduled_task" when "schedule" is set), is
    left to raise naturally — same as elsewhere in this repo (see
    options_dag.py's unguarded json.load) — callers index into entries
    themselves.
    """
    if not os.path.isfile(AGENTS_CONFIG_FILE):
        raise FileNotFoundError(
            f"Agent config file not found: {AGENTS_CONFIG_FILE}. "
            'Expected {"routed": {...}, "scheduled": {...}}.'
        )
    with open(AGENTS_CONFIG_FILE) as f:
        return json.load(f)


def discover_routed_agents() -> dict[str, str]:
    """{agent_type: description} for agents reachable via agent_router_dag.py's
    event-driven classifier. Zero is a valid, honest state — not every agent
    needs an event-driven path."""
    routed = _load_agents_config().get("routed", {})
    return {agent_type: entry["description"] for agent_type, entry in routed.items()}


def discover_scheduled_agents() -> dict[str, dict]:
    """{agent_type: {"schedule": ..., "scheduled_task": ...}} for agents
    launched on a cron via scheduled_agents_dag.py."""
    return _load_agents_config().get("scheduled", {})


def launch_task_id(agent_type: str) -> str:
    return f"launch_agent_{agent_type}"


def pool_name(agent_type: str) -> str:
    return f"agent_{agent_type}"


def ensure_pools(agent_types) -> None:
    """Idempotently (re)create one 1-slot pool per given agent type —
    serializes invocations against that agent's session-state subdirectory,
    self-healing if a pool is ever deleted."""
    for agent_type in agent_types:
        Pool.create_or_update_pool(
            name=pool_name(agent_type),
            slots=1,
            description=f"Serializes claudebox {agent_type} agent invocations (shared session-state subdirectory)",
            include_deferred=False,
        )


def ensure_storage() -> None:
    """Idempotently create the two shared NFS-backed PVCs every agent's
    launch task mounts (via subPathExpr, not a dedicated PVC each)."""
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException

    config.load_incluster_config()
    v1 = client.CoreV1Api()

    sizes = {WORKSPACES_PVC: "5Gi", STATE_PVC: "2Gi"}
    for pvc_name, size in sizes.items():
        pvc = client.V1PersistentVolumeClaim(
            metadata=client.V1ObjectMeta(name=pvc_name, namespace=AGENT_NAMESPACE),
            spec=client.V1PersistentVolumeClaimSpec(
                access_modes=["ReadWriteMany"],
                storage_class_name="managed-nfs-storage",
                resources=client.V1ResourceRequirements(requests={"storage": size}),
            ),
        )
        try:
            v1.create_namespaced_persistent_volume_claim(namespace=AGENT_NAMESPACE, body=pvc)
        except ApiException as e:
            if e.status != 409:  # already exists — expected after first run
                raise


def build_launch_task(agent_type: str, arguments: list) -> KubernetesPodOperator:
    """
    Build the KubernetesPodOperator that launches `agent_type`'s claudebox
    container. `arguments` is the full one-shot CLI arg list — this is the
    one thing that differs between callers (agent_router_dag.py pulls the
    prompt from an upstream classifier's XCom via Jinja; scheduled_agents_dag.py
    uses a fixed `scheduled_task` string from agents.json). Everything else
    about the pod (image via POD_TEMPLATE_FILE, volumes, pool, OAuth token)
    is identical regardless of how the launch was triggered.
    """
    return KubernetesPodOperator(
        task_id=launch_task_id(agent_type),
        name=f"claudebox-{agent_type.replace('_', '-')}",
        namespace=AGENT_NAMESPACE,
        pod_template_file=POD_TEMPLATE_FILE,
        # Fetches this agent's SKILL.md/.mcp.json fresh from the public
        # SKILLS_GIT_REPO on every launch — always-overwrite, not seed-once,
        # since both files are pure git-authored config with nothing
        # agent-grown left to protect. A shallow clone into a scratch dir,
        # not the official git-sync image: that's built for continuous
        # syncing in a long-lived pod, overkill for a one-shot fetch-and-exit
        # init container.
        init_containers=[
            k8s.V1Container(
                name="fetch-skill-config",
                image="alpine/git:latest",
                command=["sh", "-c"],
                args=[
                    f"git clone --depth 1 {SKILLS_GIT_REPO} /tmp/repo && "
                    f"cp /tmp/repo/{SKILLS_GIT_PATH}/{agent_type}/SKILL.md /workspace/ && "
                    f"cp /tmp/repo/{SKILLS_GIT_PATH}/{agent_type}/.mcp.json /workspace/"
                ],
                env=[k8s.V1EnvVar(name="AGENT_TYPE", value=agent_type)],
                volume_mounts=[
                    k8s.V1VolumeMount(name="workspace", mount_path="/workspace", sub_path_expr="$(AGENT_TYPE)"),
                ],
            ),
        ],
        # No `cmds=` override — the image's own ENTRYPOINT must run as-is.
        arguments=arguments,
        env_vars=[
            # Plain value, not a secret — selects this agent's subdirectory
            # within the shared PVCs below via subPathExpr.
            k8s.V1EnvVar(name="AGENT_TYPE", value=agent_type),
            # Subscription-backed OAuth token (sk-ant-oat01-..., from
            # `claude setup-token` / `claudebox setup-token`), NOT an API
            # key — this is what the real `claude` CLI inside the container
            # reads. Scoped only to Claude Code inference.
            k8s.V1EnvVar(
                name="CLAUDE_CODE_OAUTH_TOKEN",
                value_from=k8s.V1EnvVarSource(
                    secret_key_ref=k8s.V1SecretKeySelector(
                        name="ai-secrets",
                        key="CLAUDE_CODE_OAUTH_TOKEN",
                    )
                ),
            ),
            # Fine-grained PAT, scoped to a single repo (cwilko/marketinsights-collector
            # for data_collector today). Not referenced directly in any .mcp.json —
            # present here so Claude's own process environment has it, and the
            # ${GITHUB_PERSONAL_ACCESS_TOKEN} substitution in a skill's .mcp.json
            # resolves to it rather than needing the literal value committed to git.
            # Harmless for agents whose .mcp.json doesn't reference it.
            k8s.V1EnvVar(
                name="GITHUB_PERSONAL_ACCESS_TOKEN",
                value_from=k8s.V1EnvVarSource(
                    secret_key_ref=k8s.V1SecretKeySelector(
                        name="ai-secrets",
                        key="GITHUB_PERSONAL_ACCESS_TOKEN",
                    )
                ),
            ),
        ],
        volumes=[
            k8s.V1Volume(
                name="workspace",
                persistent_volume_claim=k8s.V1PersistentVolumeClaimVolumeSource(claim_name=WORKSPACES_PVC),
            ),
            k8s.V1Volume(
                name="claude-state",
                persistent_volume_claim=k8s.V1PersistentVolumeClaimVolumeSource(claim_name=STATE_PVC),
            ),
        ],
        volume_mounts=[
            k8s.V1VolumeMount(name="workspace", mount_path="/workspace", sub_path_expr="$(AGENT_TYPE)"),
            k8s.V1VolumeMount(name="claude-state", mount_path="/home/aicode/.claude", sub_path_expr="$(AGENT_TYPE)"),
        ],
        # One slot per agent: --continue reads/writes this agent's live
        # session files under its claude-state subdirectory, so two
        # concurrent pods for the SAME agent would race (different agents
        # run freely in parallel — separate subdirectories, separate pools).
        pool=pool_name(agent_type),
        queue="celery",
        get_logs=True,
        is_delete_operator_pod=True,
    )
