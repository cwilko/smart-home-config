# Agent Ideas

Brainstorm of activities for agents run through the
[agent orchestration framework](README.md). This assumes a future where a wide
library of MCP tools is available; tools that don't exist in the cluster yet are
marked ➕ in the [tool table](#mcp-tool-catalogue).

Status of every idea below: **not implemented** (only `data_collector` exists).

## Design principles

- **Draft, never send.** Anything touching the outside world (email, social,
  purchases, supplier switches) only creates drafts, carts or PRs. A human
  approves via [WhatsApp](#human-approval-via-whatsapp).
- **Read-only first.** Banking, broker, kubectl and cameras start read-only.
  Most of the value is analysis, not action.
- **No-op is a valid outcome.** Like `data_collector`, an agent that finds
  nothing new should do nothing and say nothing. Otherwise scheduled agents
  become noise.
- **One pending proposal at a time** for anything that changes a repo (the
  `data_collector` PR gate), so review queues never back up.
- **Agents never merge their own work.**
- **Agents can trigger agents.** Everything flows over MQTT, so chains such as
  anomaly → security sentinel → cluster doctor come almost free via the router.
- **Shared memory.** A common vector store / notes MCP lets agents build on each
  other's findings rather than starting cold.

## Human approval via WhatsApp

WhatsApp is the primary channel for the agents that need a human in the loop.
It serves two roles:

1. **Notify** — a summary, alert or briefing pushed to you.
2. **Approve** — an agent proposes an action and waits for a reply before
   acting.

Suggested shape (to be designed):

- Agent sends a message: what it wants to do, why, and a short reply code
  (e.g. `Reply 1 to approve, 2 to reject, or send edits`).
- Pods are one-shot, so the agent **does not wait in-pod**. It records the
  pending action (PR, draft, cart link) and exits. Your reply arrives as an
  inbound event: WhatsApp bridge → MQTT → `agent_router_dag` → the owning agent,
  which executes or discards the action. This reuses the router already
  designed, and needs the same not-yet-built MQTT-to-Airflow bridge.
- Outbound-only messages (briefings, alerts) need just the WhatsApp send tool.
- Open questions: WhatsApp Business API vs. a self-hosted bridge; message
  templates and the 24-hour customer-service window; allow-listing your own
  number only; how approval codes are bound to a specific pending action so a
  stale or spoofed reply can't trigger anything.

## Ideas

### Personal and family

#### 1. Chief-of-staff briefing
- **Trigger:** weekday cron.
- **What:** merges email, calendar and Slack into one morning brief. Flags
  clashes, drafts replies, adds travel time to meetings.
- **Output:** WhatsApp briefing; reply-to-approve for any drafted response.
- **Tools:** Gmail ➕, Google Calendar ➕, Slack ➕, Drive ➕, Weather ➕,
  Maps ➕, WhatsApp ➕.

#### 2. Per-family-member agents
- **Trigger:** one cron entry per person, each with its own `--continue` memory
  and PVC subPath. Needs the parameterised design the README defers.
- **What:** term dates, permission slips, meal plans based on what is in the
  fridge, shopping baskets prepared but not checked out.
- **Output:** WhatsApp to the individual (or the family group); basket links for
  approval.
- **Tools:** school-portal / email parser ➕, shared calendar ➕, grocery
  APIs ➕, recipe DB ➕, Todoist / Notion ➕, WhatsApp ➕.

#### 3. Life-admin watcher
- **Trigger:** weekly cron.
- **What:** tracks renewals (insurance, MOT, passport, broadband
  end-of-contract), finds cheaper alternatives, drafts the switch.
- **Output:** WhatsApp heads-up with the saving; approve to proceed.
- **Tools:** Gmail ➕, Open Banking read-only ➕, document OCR ➕, Drive ➕,
  price comparison ➕, WhatsApp ➕.

#### 4. Travel planner
- **Trigger:** event-driven ("thinking of going to X", via WhatsApp message).
- **What:** builds an itinerary against everyone's calendars and budget.
- **Output:** draft itinerary doc; WhatsApp summary and options.
- **Tools:** Flights ➕, Hotels ➕, Maps ➕, Weather ➕, Google Calendar ➕,
  visa-rules API ➕, WhatsApp ➕.

### Homelab and smart home

#### 5. Cluster doctor
- **Trigger:** scheduled, plus event-driven from alerts.
- **What:** diagnoses crash loops, near-full PVCs and failed DAG runs; finds the
  root cause across metrics and logs; opens a fix PR to `smart-home-config`.
  Would have caught the three silent failures documented in the README.
- **Output:** PR; WhatsApp alert for anything urgent.
- **Tools:** kubectl read-only ➕, Prometheus / Loki ➕, Alertmanager ➕,
  GitHub, Argo CD / Flux diff ➕, Airflow API ➕, WhatsApp ➕.

#### 6. Home-automation optimiser
- **Trigger:** weekly cron, plus event-driven.
- **What:** learns usage patterns and proposes automations (e.g. pre-heat when
  tariff drops); finds dead or flapping devices.
- **Output:** PRs to the Home Assistant config; weekly WhatsApp summary.
- **Tools:** Home Assistant ➕, MQTT, energy tariff ➕ (Octopus Agile), solar
  forecast ➕, GitHub, WhatsApp ➕.

#### 7. Security sentinel
- **Trigger:** event-driven (router) plus daily scan.
- **What:** correlates new devices, odd DNS, camera events and image CVEs into
  one ranked alert instead of raw noise.
- **Output:** WhatsApp alert with severity; approve to block a device or
  quarantine.
- **Tools:** UniFi / router ➕, Pi-hole / AdGuard ➕, Frigate ➕, CVE feeds ➕,
  Trivy ➕, MQTT, WhatsApp ➕.

#### 8. Backup verifier
- **Trigger:** weekly cron.
- **What:** checks TrueNAS snapshots and backups exist and are fresh, and
  test-restores a small sample.
- **Output:** WhatsApp only on failure (silent on success).
- **Tools:** TrueNAS API ➕, kubectl read-only ➕, WhatsApp ➕.

### Data and finance

#### 9. Market-insights analyst
- **Trigger:** weekly cron.
- **What:** writes a "what changed and why" note with charts from the
  `marketinsights-collector` data; backtests hypotheses it generates. Pairs with
  `data_collector` so new sources get used immediately.
- **Output:** report in the repo / Drive; WhatsApp digest.
- **Tools:** Postgres ➕, Python sandbox ➕, chart renderer ➕, FRED / SEC
  EDGAR / news ➕, GitHub, WhatsApp ➕.

#### 10. Portfolio and finance auditor
- **Trigger:** monthly cron.
- **What:** drift from target allocation, fee leakage, ISA / pension allowance
  use, subscription creep. Read-only by design.
- **Output:** WhatsApp monthly summary.
- **Tools:** Broker API read-only ➕, Open Banking read-only ➕, tax-rules
  lookup ➕, spreadsheet ➕, WhatsApp ➕.

#### 11. Business lead and market scout
- **Trigger:** weekly cron.
- **What:** finds and enriches target companies, scores them, drafts
  personalised outreach.
- **Output:** drafts queued in the CRM; WhatsApp approval before anything is
  sent.
- **Tools:** Web search / browser ➕, Companies House ➕, LinkedIn / job
  boards ➕, CRM ➕, Gmail drafts ➕, WhatsApp ➕.

### Content and knowledge

#### 12. Social media studio
- **Trigger:** weekly cron.
- **What:** turns the week's commits and projects into post drafts; reviews what
  performed well and adjusts.
- **Output:** drafts to a review queue; WhatsApp approve-to-publish.
- **Tools:** GitHub, image generator ➕, Buffer / X ➕, LinkedIn draft-only ➕,
  analytics ➕, WhatsApp ➕.

#### 13. Research and reading digest
- **Trigger:** daily cron.
- **What:** filters RSS, arXiv and Hacker News by your interests, summarises,
  links each item to existing notes.
- **Output:** notes written to the knowledge base; short WhatsApp digest.
- **Tools:** RSS ➕, arXiv ➕, Hacker News ➕, vector store ➕, Obsidian /
  Readwise ➕, WhatsApp ➕.

#### 14. Knowledge-base gardener
- **Trigger:** nightly cron.
- **What:** dedupes and links notes, turns meeting notes into tasks, resurfaces
  forgotten projects.
- **Output:** edits to the notes store; occasional WhatsApp nudge.
- **Tools:** Obsidian / Notion ➕, vector store ➕, Drive ➕, WhatsApp ➕.

### Engineering and meta

#### 15. Repo maintainer
- **Trigger:** weekly cron plus event-driven on new issues.
- **What:** triages issues, fixes flaky tests, bumps dependencies and images
  behind green CI, one PR open at a time.
- **Output:** PRs; WhatsApp ping when one needs review.
- **Tools:** GitHub, test runner / sandbox ➕, package registries ➕,
  WhatsApp ➕.

#### 16. Agent overseer
- **Trigger:** weekly cron.
- **What:** reviews every agent's runs for noise, cost, stuck sessions and
  suspect output; proposes `SKILL.md` edits; recommends retiring agents that
  don't earn their keep.
- **Output:** PR with skill edits; WhatsApp weekly report.
- **Tools:** Airflow API ➕, MQTT history, GitHub, usage / cost tracker ➕,
  WhatsApp ➕.

## MCP tool catalogue

✅ = already used in this repo, ➕ = new.

**How this was researched (2026-10-27):** web searches against MCP directories
(Glama, mcpservers.org, PulseMCP, vendor docs). Entries marked **✔** had their
GitHub README opened and the transport/safety claims confirmed. Everything else
comes from directory listings and is **unverified**, so check the repo
(licence, last commit, open security issues) before depending on it. Treat every
third-party server as supply-chain surface: pin versions and read the source.

**Transport key:**
- 🟢 streamable HTTP (preferred: can run as a shared in-cluster service or be
  hosted by the vendor)
- 🟡 HTTP of unspecified flavour, or SSE (SSE is deprecated in the MCP spec)
- 🔴 stdio only (fits the one-shot pod model, like the current `github` and
  `mqtt` tools, but each pod pays the install cost)
- ❔ not stated in what I found

"Hosted" means the vendor runs the server and you connect to a URL; these need
an OAuth flow, so check how a headless pod would obtain and refresh a token.

| Tool | Existing MCP server(s) | Transport | Notes (access scope to grant) | Ideas |
|---|---|---|---|---|
| GitHub ✅ | [github/github-mcp-server](https://github.com/github/github-mcp-server) | 🔴 as used today (it also offers a remote mode) | Fine-grained PAT per repo | 5, 6, 9, 12, 15, 16 |
| MQTT ✅ | [eduard256/mqtt-mcp-server](https://github.com/eduard256/mqtt-mcp-server) | 🔴 | Publish to agent topics | 6, 7, 16 |
| **WhatsApp** ➕ | [Sealjay/mcp-whatsapp](https://github.com/Sealjay/mcp-whatsapp) ✔ (personal account via whatsmeow, MIT, 42 tools); [lharries/whatsapp-mcp](https://github.com/lharries/whatsapp-mcp) (most popular, Go bridge + stdio); [YCloud](https://enterprisedna.co/directories/mcp/ycloud-developers-ycloud-whatsapp-mcp-server) and GreenAPI servers for the Business API (unverified) | 🟡 Sealjay: HTTP at `/mcp`, stateless; lharries: 🔴 | See WhatsApp notes below this table | all |
| Gmail / Google Calendar / Drive ➕ | [taylorwilsdon/google_workspace_mcp](https://github.com/taylorwilsdon/google_workspace_mcp) ✔ (Gmail, Drive, Calendar, Docs, Sheets and more; OAuth 2.1) | 🟢 (also stdio) | Has a `--read-only` option and per-service/tool-tier limits. It includes *send*, so restrict tiers to draft-only for Gmail | 1, 3, 4, 11 |
| Slack ➕ | Hosted: `https://mcp.slack.com/mcp` (vendor-run, OAuth); [korotovsky/slack-mcp-server](https://github.com/korotovsky/slack-mcp-server) ✔ | 🟢 hosted; korotovsky: stdio, SSE, HTTP | korotovsky disables posting by default (`SLACK_MCP_ADD_MESSAGE_TOOL`). Can use `xoxc`/`xoxd` browser tokens, which sidestep Slack app approval but are against the spirit of workspace policy | 1 |
| Notion ➕ | Hosted: `https://mcp.notion.com/mcp` (official, OAuth); [makenotion/notion-mcp-server](https://github.com/makenotion/notion-mcp-server) (local, integration token; maintainers say it may be sunset) | 🟢 hosted; local: stdio | Prefer an integration token for headless pods, since the hosted one needs interactive OAuth | 2, 14 |
| Todoist ➕ | [Doist/todoist-mcp](https://github.com/doist/todoist-mcp) (official, 40+ tools) | 🔴 default, HTTP wrapper available | Needs Node 24+ | 2 |
| Obsidian ➕ | [MarkusPfundstein/mcp-obsidian](https://github.com/MarkusPfundstein/mcp-obsidian) | 🔴 | Needs Obsidian running with the Local REST API plugin, which doesn't suit a pod. Simpler: keep the vault as markdown on the NFS and use a filesystem MCP | 13, 14 |
| Readwise ➕ | [readwiseio/readwise-mcp](https://github.com/readwiseio/readwise-mcp) | 🔴 | Access token only | 13 |
| Vector store ➕ | [qdrant/mcp-server-qdrant](https://github.com/qdrant/mcp-server-qdrant) (official, Apache-2.0; `qdrant-store` / `qdrant-find`) | 🟢 (`--transport streamable-http`) | Needs a Qdrant instance in the cluster. Good fit as the shared agent memory | 1, 13, 14 |
| Web search ➕ | Brave Search reference server in [modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers) (check whether it has been moved or archived) | 🔴 | Needs `BRAVE_API_KEY` | 4, 11 |
| Browser ➕ | [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp) | 🟢 (`--port`, endpoint `/mcp`) | Heavy image; headless Chromium in the pod | 4, 11 |
| Web fetch ➕ | `fetch` server in [modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers/tree/main/src/fetch) | 🔴 | Read-only | 4, 13 |
| RSS ➕ | Several community servers (see [Glama listing](https://glama.ai/mcp/tools?query=RSS)); none stands out | ❔ | Alternative: have a collector DAG ingest feeds and let the agent read from a store | 13 |
| arXiv ➕ | [blazickjp/arxiv-mcp-server](https://github.com/blazickjp/arxiv-mcp-server) (~2.7k stars per listings) | 🔴 + HTTP (per listings) | Stores downloaded papers on disk, so point it at the PVC | 13 |
| Hacker News ➕ | [Malayke/hackernews-mcp](https://glama.ai/mcp/servers/@Malayke/hackernews-mcp) | ❔ | Needs a Firecrawl API key. An Algolia-based server also exists | 13 |
| Weather ➕ | Google Maps [Grounding Lite](https://developers.google.com/maps/ai/grounding-lite) (hosted, official; places, routes and weather); community Open-Meteo servers such as [langepas/open-meteo-mcp](https://glama.ai/mcp/servers/BilelSelmiAi2026/open-meteo-mcp) | 🟢 hosted (per Google docs, unverified) | Open-Meteo needs no API key, which suits a homelab | 1, 4 |
| Maps / travel time ➕ | Google Maps [Grounding Lite](https://developers.google.com/maps/ai/grounding-lite/reference/mcp) (`mapstools.googleapis.com`) | 🟢 hosted | Needs a Google Cloud project and API key | 1, 4 |
| Flights / hotels ➕ | Duffel: [FortripEngineering/duffel-mcp](https://glama.ai/mcp/servers/@FortripEngineering/duffel-mcp) (search **and booking**), [kidehen/mcp-travel-server](https://github.com/kidehen/mcp-travel-server); Amadeus: `travel-amadeus-mcp` on npm | 🔴 | Some of these can book. Disable the booking tools or use a search-only token. No Airbnb server found | 4 |
| Grocery ➕ | Instacart ([official MCP](https://docs.instacart.com/mcp_servers/), US-focused); Tesco: [Basketeer](https://mcpservers.org/zh-CN/servers/tobyandrews1985/basketeer) (unofficial; Tesco blocks sign-in from datacentre IPs). **Ocado: none found** | ❔ | UK grocers are poorly served, so idea 2's basket step may need a custom server | 2 |
| Recipes ➕ | Mealie: [mdlopresti/mealie-mcp](https://glama.ai/mcp/servers/@mdlopresti/mealie-mcp) (also a 43-tool `mealie-mcp-server` on npm) | 🔴 | Mealie is self-hostable, which fits the homelab well | 2 |
| School portal / email parser ➕ | **None found** | n/a | Custom: Gmail MCP plus an agent prompt that parses school emails | 2 |
| Open Banking ➕ | TrueLayer: [pimvanoerle/open-banking-mcp](https://glama.ai/mcp/servers/bzjbd2mqx3) (read-only, UK banks, "single-user, personal-scale"); [tkom04/openbankingMCP](https://images.glama.ai/mcp/servers/tkom04/openbankingMCP). **Plaid and GoCardless: none found** | 🔴 | Data-API scopes only. This is the most sensitive credential on the list, so keep it out of every pod except 3 and 10 | 3, 10 |
| Broker ➕ | Alpaca [official MCP server](https://alpaca.markets/mcp-server) (trading API, can place trades); Interactive Brokers: community servers only. **Trading 212: none found** | 🔴 (Alpaca, per docs) | Alpaca is a US broker, so check it is relevant to your accounts. Use read-only keys and keep trading tools off | 10 |
| Price comparison ➕ | **None found** (not searched specifically) | n/a | Could be a browser-driven agent task instead | 3 |
| Document OCR ➕ | [lemopian/mistral-ocr-mcp](https://glama.ai/mcp/servers/lemopian/mistral-ocr-mcp) (Mistral OCR API); [Swih/mistral-mcp](https://mcpservers.org/servers/swih/mistral-mcp) | 🔴 | Sends documents to Mistral's API. Claude can read PDFs and images itself, so this may be unnecessary | 3 |
| Tax-rules lookup ➕ | **None found** (not searched specifically) | n/a | Probably a skill file with the allowance figures, refreshed yearly | 10 |
| Spreadsheet ➕ | [haris-musa/excel-mcp-server](https://github.com/haris-musa/excel-mcp-server) | 🟢 (`streamable-http`; docs recommend it for remote use) | Port default is inconsistent across docs (8000 vs 8017); set `EXCEL_FILES_PATH` | 10 |
| Postgres ➕ | [crystaldba/postgres-mcp](https://github.com/crystaldba/postgres-mcp) (`--access-mode restricted`) | 🔴 + SSE (per listings) | Default mode may be unrestricted. Use a read-only DB role as the real control | 9 |
| Python sandbox ➕ | [chrishayuk/mcp-code-sandbox](https://github.com/chrishayuk/mcp-code-sandbox) (backed by the E2B service); [E2B MCP server](https://hub.docker.com/mcp/server/e2b) | 🔴 | Sends code to a third-party sandbox. **The claudebox pod is already a sandbox** (Bash with bypassPermissions), so you may not need this | 9, 15 |
| Chart renderer ➕ | [antvis/mcp-server-chart](https://github.com/antvis/mcp-server-chart) (25+ chart types) | 🟢 (stdio, SSE, streamable HTTP) | Check whether chart rendering calls a hosted AntV service, which would send your data out of the cluster. Alternative: matplotlib in the pod | 9 |
| FRED ➕ | [stefanoamorelli/fred-mcp-server](https://github.com/stefanoamorelli/fred-mcp-server) (AGPL-3.0) | 🔴 | Free FRED API key | 9 |
| SEC EDGAR ➕ | **Not verified.** Search did not cover it | ❔ | Search again before relying on it | 9 |
| News ➕ | `mcp-newsapi` on [npm](https://npmjs.com/package/mcp-newsapi); GNews and NewsAPI.ai servers via [Glama](https://glama.ai/mcp/servers/krij4otgrj). **GDELT: no dedicated server found** | 🔴 | Free tiers are rate-limited | 9 |
| kubectl ➕ | [containers/kubernetes-mcp-server](https://github.com/containers/kubernetes-mcp-server) ✔ (Apache-2.0, active) | 🟡 HTTP mode exists; transports not confirmed | `read_only = true` in TOML config. Pair with a ServiceAccount bound to the built-in `view` ClusterRole, and note `view` excludes Secrets | 5, 8 |
| Prometheus / Loki / alerting ➕ | [grafana/mcp-grafana](https://github.com/grafana/mcp-grafana) ✔ (official; PromQL, LogQL, alert rules, silences); standalone [ntk148v/alertmanager-mcp-server](https://github.com/ntk148v/alertmanager-mcp-server) | 🟢 (stdio, SSE, streamable-http) | `--disable-write` gives read-only. It reaches Prometheus and Loki through your Grafana, which the repo already deploys | 5, 7 |
| Argo CD / Flux ➕ | [argoproj-labs/mcp-for-argocd](https://github.com/argoproj-labs/mcp-for-argocd) (read-only mode); Flux: [controlplaneio-fluxcd/flux-operator](https://github.com/controlplaneio-fluxcd/flux-operator) (`cmd/mcp`) | 🟢 Argo CD: stdio + HTTP stream; Flux: stdio, SSE, HTTP | Only relevant if you use one of them | 5 |
| Airflow API ➕ | [fastmcp-me/mcp-server-apache-airflow](https://github.com/fastmcp-me/mcp-server-apache-airflow) (a fork wrapping the REST API); [ponderedw/airflow-mcp](https://github.com/ponderedw) (natural-language, ownership transferred) | ❔ | Has a read-only mode. Find the upstream repo of that fork before depending on it | 5, 16 |
| TrueNAS ➕ | [vespo92/TrueNasCoreMCP](https://github.com/vespo92/TrueNasCoreMCP) (Core and SCALE, PyPI, `uvx`) | 🔴 | Needs a TrueNAS API key. Use a read-only key and exclude user and share management | 8 |
| Home Assistant ➕ | [homeassistant-ai/ha-mcp](https://github.com/homeassistant-ai/ha-mcp); community [AHA MCP](https://glama.ai/mcp/servers/slhad/aha-mcp) | 🟢 (OIDC auth available) | Long-lived HA token. Keep service calls behind approval | 6 |
| Energy tariff ➕ | [DanielChicot/octopus-mcp](https://glama.ai/mcp/servers/DanielChicot/octopus-mcp) (usage, costs, tariff comparison); [darronz/octopus-mcp-server](https://github.com/darronz/octopus-mcp-server) (consumption) | 🔴 | Unofficial. Neither obviously covers live Agile half-hourly prices, so verify | 6 |
| Solar forecast ➕ | **None found** (a US-only `solar-data-mcp` exists on PyPI) | n/a | Forecast.Solar is a simple HTTP API; a tiny custom server or a skill that calls it with curl would do | 6 |
| UniFi / router ➕ | **No verified server found** (one sibling project is mentioned in the [chris2ao listing](https://glama.ai/mcp/servers/nzbax8dzi2)) | ❔ | Search by exact repo name before relying on it | 7 |
| Pi-hole / AdGuard ➕ | Pi-hole: [sbarbett/pihole-mcp-server](https://github.com/sbarbett/pihole-mcp-server) (Docker, SSE), [chris2ao/pihole-mcp](https://github.com/chris2ao/pihole-mcp) (v6, 28 tools); AdGuard: [listing](https://ai.g2.com/marketplace/tools/adguard-home-mcp-server) says remote HTTP with read-only tier | 🟡 | Pi-hole v6 API differs from v5, so match the version | 7 |
| Frigate ➕ | [jakekeeys/frigate-mcp](https://github.com/jakekeeys/frigate-mcp) (59 tools, Frigate v0.17 HTTP API) | 🔴 | No PTZ (that is MQTT-only in Frigate). Read-only is by your choice of tools | 7 |
| CVE feeds / Trivy ➕ | [aquasecurity/trivy-mcp](https://github.com/aquasecurity/trivy-mcp) (official Trivy plugin). **NVD: no dedicated server found** | 🟢 (stdio, streamable HTTP, SSE) | Trivy's GitHub Action had a supply-chain compromise in March 2026 (CVE-2026-33634), so pin the version | 5, 7 |
| Companies House ➕ | [aicayzer/companies-house-mcp](https://github.com/aicayzer/companies-house-mcp) (MIT, unofficial) | 🔴 (`npx`) | Free API key | 11 |
| LinkedIn / job boards ➕ | [stickerdaniel/linkedin-mcp-server](https://github.com/stickerdaniel/linkedin-mcp-server) (drives a logged-in browser session) | 🔴 | Scraping goes against LinkedIn's terms and risks your account, so prefer a paid data API for anything routine | 11 |
| CRM ➕ | HubSpot: hosted `https://mcp.hubspot.com` ([docs](https://developers.hubspot.com/docs/build-with-ai/remote-mcp-server), official, OAuth 2.1) | 🟢 hosted | Needs a HubSpot account. For Notion as CRM, see the Notion row | 11 |
| Image generator ➕ | No official server found. Community: [gmkr/mcp-imagegen](https://github.com/gmkr/mcp-imagegen) (Replicate/Together), [gerred/mcp-server-replicate](https://github.com/gerred/mcp-server-replicate), `image-mcp` (OpenAI + Replicate) | 🔴 | Needs an image-model API key | 12 |
| Social scheduling ➕ | X: [DataWhisker/x-mcp-server](https://mcpservers.org/servers/DataWhisker/x-mcp-server), [Dishant27/twitter-mcp](https://github.com/Dishant27/twitter-mcp) (community; need X developer credentials). **Buffer and LinkedIn posting: none found** | 🔴 | Create the post as a draft in a scheduler where possible, not a live post | 12 |
| Social analytics ➕ | **None found** (not searched specifically) | n/a | | 12 |
| Test runner ➕ | **Probably not needed**: the pod runs Claude Code with Bash, so it can run tests directly | n/a | Needs the repo cloned into the workspace | 15 |
| Package registries ➕ | [Artmann/package-registry-mcp](https://github.com/Artmann/package-registry-mcp) (npm, PyPI, crates.io, NuGet, Go, GitHub advisories); [Nekzus/npm-sentinel-mcp](https://github.com/Nekzus/npm-sentinel-mcp) | 🔴 | Read-only public data | 15 |
| Usage / cost tracker ➕ | [ryoppippi/ccusage](https://github.com/ryoppippi/ccusage) (`@ccusage/mcp`: daily, monthly, session reports) | 🔴 | Reads Claude Code's local logs, which here live on `claudebox-state-pvc`, so one pod mounting it could report on all agents | 16 |

### WhatsApp notes

The WhatsApp row is the one that decides whether the approval flow works, so it
deserves more than a table cell.

- **Two kinds of server exist.** The popular ones (`Sealjay/mcp-whatsapp`,
  `lharries/whatsapp-mcp`) log in as **your personal account** through the
  unofficial whatsmeow library. The others (YCloud, GreenAPI) use the **WhatsApp
  Business API**, which is the sanctioned route.
- **The personal-account route has real risks.** It is unofficial (Sealjay's own
  README says it is unaffiliated with Meta), so Meta could ban the number. The
  session is invalidated about every 20 days and needs a QR re-scan, which is
  awkward for an unattended pod. A dedicated second SIM would limit the damage.
- **Inbound messages are not pushed.** Sealjay's server stores incoming messages
  in a local SQLite file while its daemon runs and exposes them through query
  tools. There is no webhook, so it can't directly trigger `agent_router_dag`.
  The approval flow therefore needs either a small always-on bridge that watches
  that store and publishes to MQTT, or the Business API, which does support
  webhooks.
- **It must run as a long-lived service.** A one-shot pod can't hold the
  WhatsApp session, so the server belongs in its own Deployment (with a PVC for
  the session store) and pods connect to it over HTTP. This is another reason to
  prefer streamable HTTP for it.
- **Safety gaps.** Sealjay has no recipient allow-list and no send confirmation.
  The README itself warns that prompt injection in an incoming message could
  lead to data exfiltration. Anything an agent reads from WhatsApp is untrusted
  input, so approval replies should be matched against a stored pending-action
  code rather than interpreted by the model.

### Findings from the research

- **Where a ready-made server exists:** most of the homelab and data tools
  (Grafana/Prometheus/Loki, Kubernetes, Argo CD, Home Assistant, Frigate,
  Pi-hole, Trivy, TrueNAS, Qdrant, Postgres, Excel) and the big SaaS ones
  (Google Workspace, Slack, Notion, HubSpot, Todoist, Google Maps).
- **Streamable HTTP is common for infra tools and vendor-hosted servers**
  (`mcp-grafana`, Google Workspace, Qdrant, Excel, Trivy, `ha-mcp`, Slack,
  Notion, HubSpot, Google Maps). Most community servers are still stdio-first,
  which suits the current one-shot pod model but not shared services.
- **Biggest gaps:** UK grocery (Ocado), Plaid/GoCardless, Trading 212, solar
  forecasting, price comparison, UniFi, school portals, social scheduling
  (Buffer, LinkedIn posting) and SEC EDGAR (not verified). These need a custom
  server, an agent using a browser, or a skill that calls the HTTP API directly.
- **Several tools may not need an MCP server at all:** the pod already has Bash,
  so the Python sandbox, test runner and likely OCR (Claude reads PDFs and
  images) can be handled in-pod.
- **Hosted OAuth servers (Slack, Notion, HubSpot, Google Maps) are the awkward
  case for a headless pod.** Where there is a token-based alternative (Notion
  integration token, Slack bot token, HubSpot private app token), use that.
- **A hybrid deployment will probably be needed.** Keep stdio servers installed
  per pod for cheap, stateless tools, and run the stateful or heavy ones
  (WhatsApp, Qdrant, Grafana, Playwright) as shared Deployments reached over
  streamable HTTP. A stdio-to-HTTP gateway could front the stdio-only ones, but I
  haven't researched which gateway to use.

## Suggested starting set

1. **Cluster doctor (5)**: no new third-party credentials; proves the
   event-driven path.
2. **Market-insights analyst (9)**: builds on data you already collect.
3. **Chief-of-staff briefing (1)**: the best first test of the WhatsApp
   notify-and-approve loop.
4. **Agent overseer (16)**: add once there are three or more agents.

## Prerequisites to build first

- WhatsApp MCP tool and the approval/reply flow described above. Per the
  [WhatsApp notes](#whatsapp-notes), this means a long-lived WhatsApp service
  (not a one-shot pod), a decision between a personal-account bridge and the
  Business API, and a small bridge that turns inbound messages into MQTT events.
- The MQTT-to-Airflow bridge (already noted as not built in the README), since
  inbound WhatsApp replies and all event-driven agents depend on it.
- Per-agent credential scoping: today `GITHUB_PERSONAL_ACCESS_TOKEN` is shared
  across the worker; each new tool brings its own secret that should only reach
  the agents that need it.
- The parameterised "one agent per person" design for idea 2.
