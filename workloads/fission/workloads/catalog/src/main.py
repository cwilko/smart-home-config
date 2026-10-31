# Deployed as a literal Package in catalog.yaml: after editing this file, replace that `literal` value with the output of
#   base64 -i src/main.py | tr -d '\n'
# (run from the directory that holds catalog.yaml)
import datetime
import json
import os
import ssl
import urllib.request

# Public host that Traefik routes to the Fission router. A deployment fact, so it lives here and not in the triggers.
BASE_URL = "https://api.squirrelhome.co.uk"
ANNOTATION_PREFIX = "catalog.squirrelhome.co.uk/"
KINDS = ("rest", "mcp", "webhook", "other")

# Fission does not mount the pod's ServiceAccount token into the runtime container (only into its fetcher sidecar), so
# the credential comes from the token Secret listed under secrets: in function.yaml, which Fission mounts at
# /secrets/<namespace>/<name>/<key>
SECRET_DIR = "/secrets/services/fission-catalog-token"

ABOUT = (
    "Catalog of the HTTP endpoints that Fission fronts: one entry per HTTPTrigger, joined with its Function. "
    "'url' is the full public URL ('match' says whether 'path' is an exact path or a prefix). "
    "'description', 'kind', 'openapi' and 'usage' come from the trigger's catalog.squirrelhome.co.uk/ annotations "
    "(null when absent); for kind 'rest', 'openapi' is the URL of an OpenAPI document, for the other kinds 'usage' is "
    "a markdown note on how to call the endpoint. 'problems' lists anything missing or inconsistent for that entry. "
    "Convention: workloads/fission/README.md, section 'Endpoint metadata'."
)


def _read_secret(name):
    with open(os.path.join(SECRET_DIR, name)) as f:
        return f.read().strip()


def _list_fission(plural, namespace, token, context):
    host = os.environ["KUBERNETES_SERVICE_HOST"]
    port = os.environ["KUBERNETES_SERVICE_PORT"]
    url = "https://%s:%s/apis/fission.io/v1/namespaces/%s/%s" % (host, port, namespace, plural)
    request = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
    with urllib.request.urlopen(request, context=context, timeout=10) as response:
        return json.load(response)["items"]


def _annotation(trigger, key):
    return (trigger["metadata"].get("annotations") or {}).get(ANNOTATION_PREFIX + key)


def _problems(kind, description, openapi, usage):
    problems = []
    if description is None:
        problems.append("missing annotation: description")
    if kind is None:
        problems.append("missing annotation: kind")
    elif kind not in KINDS:
        problems.append("kind '%s' is not one of: %s" % (kind, ", ".join(KINDS)))
    elif kind == "rest" and openapi is None:
        problems.append("missing annotation: openapi (required for kind rest)")
    elif kind != "rest" and usage is None:
        problems.append("missing annotation: usage (required for kind %s)" % kind)
    return problems


def _endpoint(trigger, functions):
    spec = trigger["spec"]
    if spec.get("prefix"):
        match, path = "prefix", spec["prefix"]
    else:
        match, path = "exact", spec["relativeurl"]
    # Triggers carry either a single 'method' or a 'methods' list
    methods = spec.get("methods") or ([spec["method"]] if spec.get("method") else [])

    kind = _annotation(trigger, "kind")
    description = _annotation(trigger, "description")
    openapi = _annotation(trigger, "openapi")
    usage = _annotation(trigger, "usage")
    problems = _problems(kind, description, openapi, usage)

    function = None
    functionref = spec["functionref"]
    if functionref["type"] != "name":
        problems.append("functionref type '%s' is not supported by the catalog" % functionref["type"])
    elif functionref["name"] not in functions:
        problems.append("function '%s' not found" % functionref["name"])
    else:
        function_spec = functions[functionref["name"]]["spec"]
        execution = function_spec["InvokeStrategy"]["ExecutionStrategy"]
        function = {
            "name": functionref["name"],
            "executor": execution["ExecutorType"],
            "min_scale": execution.get("MinScale"),
            "max_scale": execution.get("MaxScale"),
            "streaming": "streaming" in function_spec,
        }

    return {
        "name": trigger["metadata"]["name"],
        "namespace": trigger["metadata"]["namespace"],
        "url": BASE_URL + path,
        "path": path,
        "match": match,
        "methods": methods,
        "kind": kind,
        "description": description,
        "openapi": openapi,
        "usage": usage,
        "function": function,
        "problems": problems,
    }


def build_catalog(triggers, functions, now):
    by_name = {f["metadata"]["name"]: f for f in functions}
    endpoints = sorted((_endpoint(t, by_name) for t in triggers), key=lambda e: e["path"])
    return {
        "about": ABOUT,
        "generated_at": now.isoformat(timespec="seconds"),
        "base_url": BASE_URL,
        "endpoints": endpoints,
    }


def main():
    from flask import Response

    namespace = _read_secret("namespace")
    token = _read_secret("token")
    context = ssl.create_default_context(cafile=os.path.join(SECRET_DIR, "ca.crt"))
    catalog = build_catalog(
        _list_fission("httptriggers", namespace, token, context),
        _list_fission("functions", namespace, token, context),
        datetime.datetime.now(datetime.timezone.utc),
    )
    return Response(json.dumps(catalog, indent=2) + "\n", mimetype="application/json")
