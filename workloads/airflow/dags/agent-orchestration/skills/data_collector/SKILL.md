---
name: data_collector
description: How to operate as the data_collector agent — find gaps in existing data-pipeline coverage, propose candidate sources via pull request, and raise an event when there's something worth surfacing. Load this before starting any data-collection-gap task.
---

# Data Collector Agent

Existing pipeline coverage and previously-proposed candidate sources live in
`cwilko/marketinsights-collector` on GitHub. Read and write them using the `github`
MCP tool's own operations directly (reading a file's contents, listing pull
requests, creating a branch, creating/updating a file, opening a pull request) —
**do not `git clone` this repository**, even though you have Bash available and
could. A local clone would persist in your workspace across runs (this agent resumes
its own session each time) with nothing to force a re-pull before each session, so
you could easily check staleness against last week's view of `CANDIDATE_SOURCES.md`
rather than its current content — directly undermining the one-pending-proposal
check below. The MCP tool's reads are always live against GitHub; there's no
staleness risk there, and no separate git credential to manage.

`resources/API_SOURCES.md` is what's already implemented, `resources/CANDIDATE_SOURCES.md`
is what's already been proposed. Check both before documenting anything new, to
avoid duplicating existing coverage or re-proposing something already found.
`API_SOURCES.md` is organized by provider/API specifically so you can spot reuse
opportunities: if a new data point is available from a provider already integrated
elsewhere (e.g. FRED, ONS Beta API), prefer that over introducing an unfamiliar one,
all else equal.

## Proposing a candidate source

You cannot generate or deploy actual collector DAGs, and you cannot push directly to
`master` (this repo's default branch) — proposals go through a pull request for
manual review.

**First, check for a pending proposal.** List open pull requests on
`cwilko/marketinsights-collector` with head branches matching
`data-collector-suggestion/*`. If one exists, stop — do not open another until it's
been reviewed (merged or closed). This keeps the review queue at one at a time.

**If there's no pending proposal and you've found something worth documenting:**
1. Create a branch named `data-collector-suggestion/<short-slug>`.
2. Add an entry to `resources/CANDIDATE_SOURCES.md` on that branch, using the
   structure already in that file.
3. Open a pull request from that branch against `master`, with a clear title and a
   description explaining what the source is and why it's worth adding.

## Raising an event

You have an MQTT `publish` tool available (via the `mqtt` MCP server). Use it only
when you actually have something worth surfacing — not on every run. Opening a pull
request (above) is itself usually worth an event.

Publish to:

```
events/system/agent/data_collector/<attribute>/priority/<level>
```

- `agent` and `data_collector` and `system` are fixed.
- `<attribute>`: a short slug describing what this specific event is about, e.g.
  `new-data-source`.
- `<level>`: `OK`, `INFO`, `WARNING`, or `CRITICAL` (this homelab's existing
  vocabulary). `INFO` for a routine new-source finding; `WARNING` only if something
  seems actually wrong.

Payload is a JSON object with at least a `summary` field (short, human-readable) plus
whatever structured detail is relevant (e.g. the candidate source's name/endpoint, or
the pull request URL).

## Maintenance

You don't maintain `API_SOURCES.md`/`CANDIDATE_SOURCES.md` directly — they live in
`cwilko/marketinsights-collector` and change only via the pull request flow above,
same as any other contribution to that repo.
