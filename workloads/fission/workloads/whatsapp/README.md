# WhatsApp MCP server

[Sealjay/mcp-whatsapp](https://github.com/Sealjay/mcp-whatsapp) (MIT): a Go server (whatsmeow) that logs in to WhatsApp as a linked device and exposes it as MCP tools over HTTP. It runs here as a plain Deployment in `services`, not as a Fission function: the session is a long-lived websocket with state on disk, so it cannot scale to zero and must never run twice.

| File | What |
|---|---|
| `whatsapp-data.yaml` | Static PV and PVC, 5Gi on `truenas-nvmeof`: the session (`whatsapp.db`), message history (`messages.db`) and uploads. `pvc.yaml.old` is the dynamic claim it was pinned from |
| `deployment.yaml` | ServiceAccount and the Deployment (1 replica, `Recreate`) |
| `service.yaml` | ClusterIP `whatsapp-mcp:8765` |
| `ingressroute.yaml` | Traefik route `https://api.squirrelhome.co.uk/whatsapp-mcp/` (prefix stripped) |

Not in the repo: the sealed secret `whatsapp-mcp-secret` (step 2). Nothing in it is committed in plaintext.

## Deploy

### 1. Build and push the image

There is no published image. Build the upstream Dockerfile at a pinned release tag. The cluster nodes are amd64, so build for that platform when building on an Apple Silicon Mac.

**With GitHub Actions (preferred):** run the `Build WhatsApp MCP image` workflow (`.github/workflows/whatsapp-mcp-image.yml` at the repo root; GitHub only reads workflows from there, not from this directory) from the Actions tab, with the upstream tag as the `ref` input (default `v0.6.0`). It builds `linux/amd64`, logs the image's user and home in the "Show the image's user and home" step, then pushes `wilkobets/whatsapp-mcp:<ref>`. It needs the `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` repository secrets. Use the logged `id` and `HOME` for the checks below. After bumping `ref`, update the image tag in `deployment.yaml` to match.

**Locally, instead:**

```bash
git clone --branch v0.6.0 --depth 1 https://github.com/Sealjay/mcp-whatsapp.git
cd mcp-whatsapp
docker buildx build --platform linux/amd64 \
  --build-arg VERSION=v0.6.0 \
  -t wilkobets/whatsapp-mcp:v0.6.0 --push .
```

Then check the user the image runs as, and make `runAsUser`, `runAsGroup` and `fsGroup` in `deployment.yaml` match it (they are set to 1000, which is a guess):

```bash
docker run --rm --entrypoint id wilkobets/whatsapp-mcp:v0.6.0
```

Also confirm the image's home directory is `/home/app` (the volume is mounted at `/home/app/store`, the store's default location relative to the working directory). A mismatch shows up as the server creating a fresh, empty store instead of using the volume.

### 2. Create the sealed secret

The token is the bearer credential for `/mcp` and `/pair/*`. Generate it, seal it into `services`, and keep the plaintext out of the repo:

```bash
kubectl create secret generic whatsapp-mcp-secret --namespace services \
  --from-literal=WHATSAPP_MCP_TOKEN="$(openssl rand -hex 32)" --dry-run=client -o yaml \
  | kubeseal --format yaml > secrets/whatsapp-mcp-sealed-secret.yaml
```

(You need the token itself for the clients below, so generate it in a variable first if you want to keep a copy in a password manager.)

### 3. Apply

```bash
kubectl apply -f secrets/whatsapp-mcp-sealed-secret.yaml
kubectl apply -f whatsapp-data.yaml -f deployment.yaml -f service.yaml -f ingressroute.yaml
kubectl -n services rollout status deploy/whatsapp-mcp
```

### 4. Pair the phone

`/pair` and `/pair/qr.png` are behind the bearer token, and the server reads it only from an `Authorization: Bearer` header. It does not accept a query parameter, cookie or login form, so typing the URL into a browser returns 401. The token is enforced whenever the server runs with `-allow-remote` (as here), so port-forwarding does not bypass it either.

Add the header from the browser with a header-injecting extension (for example ModHeader): set a request header `Authorization: Bearer <token>` limited to `api.squirrelhome.co.uk`, then open `https://api.squirrelhome.co.uk/whatsapp-mcp/pair`. The page loads its QR image (`/pair/qr.png`) as a separate request, which the extension covers too. Turn the rule off afterwards, because the extension holds the token.

Then either scan the QR code (Settings → Linked Devices → Link a Device) or use the "Link with phone number instead" form. The QR rotates, so scan it soon after it appears. The page reloads itself every 5 seconds and each reload issues a new form token, so a phone number typed slowly into the form may be lost or rejected; if so, use the QR. The first history sync can take several minutes.

The session rotates roughly every 20 days; `/pair` then shows a fresh QR. Re-pair when `get_status` returns `paired: false` (`connected: false` alone can be a dropped connection).

Alternative without a browser: the binary's `login` subcommand shows a terminal QR (`login -phone +<number>` gives a pairing code). It needs the store volume, and the server allows one instance per store, so the Deployment would have to be scaled to 0 first. Not tested here.

### 5. Connect clients

```bash
claude mcp add --transport http whatsapp https://api.squirrelhome.co.uk/whatsapp-mcp/mcp \
  --header "Authorization: Bearer $WHATSAPP_MCP_TOKEN"
```

Automated agents use the same URL and `Authorization` header. The endpoint is stateless (no `Mcp-Session-Id`).

## Behaviour to know about

- **Messages are stored, not pushed.** Incoming events go to SQLite while the server runs; an agent reads them with `list_messages` / `list_chats`. Anything that arrives while the pod is down is recovered only through WhatsApp's own history sync, within its retention window (`request_sync` backfills one chat).
- **Rate limits** (from the v0.4.0 release notes): a 45 second floor between sends, 30 an hour, stricter for first-contact sends. This is deliberate: it protects the number from being banned. Recipients should have the account saved as a contact.
- **No recipient allowlist.** Any chat the account can see is reachable by anyone holding the token. Prompt injection from an incoming message is the main risk (the upstream README calls out the "lethal trifecta"); keep the contact list to family.
- **Health:** the server has no health route. The probes only check that port 8765 accepts connections. The MCP tool `get_status` reports whether WhatsApp is connected and which account is paired.
- **One instance per store.** Do not scale this above 1 and do not change the strategy from `Recreate`.

## If something goes wrong

- **Pod in `CreateContainerConfigError`:** the secret `whatsapp-mcp-secret` is missing (step 2).
- **Crash loop, "permission denied" on the store:** the pod's user and `fsGroup` do not match the image (step 1).
- **PVC stuck `Pending`, or the pod can't mount the volume:** the volume is a pinned static PV (`whatsapp-data.yaml`) onto the zvol `SSD_pool/k8s/block/pvc-whatsapp-mcp-data`, exported as the NVMe-oF subsystem `k8s-services-whatsapp-mcp-data` (namespace `nsid` 2). Check the PV's `nqn` and `nsid` against TrueNAS (`nvmet.subsys.query` and `nvmet.namespace.query`). How it was made, and how to grow or move it, is in `smart-home-docs/storage/PERSISTENT-VOLUMES.md`. To expand it, raise the PVC's request only.
- **403 through the ingress, but `/mcp` works through a port-forward when you send the bearer header:** the server's DNS-rebinding protection (from the mcp-go library) rejects a non-loopback `Host` header. The upstream README does not document a way to allow a hostname. Check the project's issues and `serve -h`; the fallback is a Caddy sidecar that rewrites `Host`, as `../github-mcp` does for a different reason.
- **Probe passes but nothing works:** the process is up but WhatsApp is disconnected. Call `get_status`; if it returns `paired: false`, re-pair at `/pair` (step 4).

## Idea, not implemented: automated re-pair alerts

When the session expires (roughly every 20 days), a scheduled check could detect it and send the QR code to a private channel (Slack DM or email), instead of someone noticing and opening `/pair` by hand. Nothing here is built; this records what was learned from the upstream source (Sealjay/mcp-whatsapp, read at its `main` branch, not run against a live server) so it can be picked up later.

### Calling the tools

`/mcp` is stateless MCP over HTTP, so a tool is one JSON-RPC `tools/call` POST with the bearer header, no session setup. Both tools below take no arguments and return indented JSON as text.

### `get_status`

| Field | Meaning |
|---|---|
| `connected` | Live WhatsApp websocket state |
| `paired` | True only if the device store holds a paired account ID |
| `own_jid`, `own_phone` | Only when paired |
| `hint` | Only when not paired (says to open `/pair`) |

- Paired and healthy: `{"connected": true, "paired": true, "own_jid": "...", "own_phone": "..."}`
- Not paired: `{"connected": false, "paired": false, "hint": "Not paired. Open /pair ..."}`
- `connected: false` with `paired: true` is a dropped connection, not a re-pair case. Test `paired`, not `connected` alone.
- There is no "logged out" value. Whether whatsmeow clears the stored account ID on a remote logout (so `paired` flips to false) was not verified.

### `pairing_status`

Returns `type: "setup_state"` and a `state`:

- `ready`: paired and connected (adds `own_jid`, `own_phone`).
- `awaiting_qr`: adds `qr_payload` (the raw QR string) once a code exists, otherwise `detail: "Generating pairing code…"`.
- `error`: pairing cache unavailable (seen only in test setups).

Quirk (from reading the code): a paired device with a dropped socket is also reported as `awaiting_qr` / "Generating pairing code…". Do not treat `awaiting_qr` alone as "needs pairing".

A reliable trigger is therefore `get_status` with `paired: false` **and** `pairing_status` with `state: awaiting_qr` and a `qr_payload`.

### Getting the QR

- `GET /pair/qr.png` (bearer header required) returns a 256x256 PNG of the current code with `Cache-Control: no-store`. It returns 404 when there is no QR cached, which covers both "already paired" and "not emitted yet", so a 404 alone is ambiguous.
- `qr_payload` from `pairing_status` is the raw string behind that image, so a script could render its own QR instead of fetching the PNG.
- The `/pair` page refreshes every 5 seconds to keep up with QR rotation.

### Recovery after a logout

On a remote logout the daemon clears its pairing cache and starts pairing again by itself, so fresh QR codes appear without a restart. The same pairing path runs at startup when the device is not logged in. Not verified: whether the "Force re-pair" button in `/pair` triggers pairing again (its handler logs out and redirects), and whether repeated logout cycles register the logout handler more than once.

### Cautions for a real implementation

- **QR codes expire quickly.** A PNG sent by Slack or email may be stale when opened (code rotation is from whatsmeow; the timing was not checked). Prefer an alert that points at a page serving a fresh QR, or a bot that sends a new one on request.
- **A QR is a credential.** Whoever scans it in time can link a device to the account. Send it to a private DM or your own mailbox, never to a shared channel.
- **Avoid repeat alerts.** If the check runs on a schedule and the phone stays unpaired, rate-limit the message (for example at most once an hour).
- Slack file uploads need a bot token with `files:write` (incoming webhooks cannot upload files); email needs SMTP credentials. Either is a new sealed secret in `services`.
- Where it could run: Node-RED (Slack and email nodes already available), a Fission function on the timer trigger (`optional/timer.yaml`, not checked whether enabled), or a Kubernetes CronJob.

## Idea, not implemented: acting on incoming messages

To trigger something when a WhatsApp message arrives. Nothing here is built; this records what was learned from the upstream source (Sealjay/mcp-whatsapp, `main` branch, read but not run) so it can be picked up later.

### The server has no push

There is no webhook URL option, no "run a command on new message" option, and no MCP notification or subscription (`/mcp` is stateless, so it cannot send server-initiated events). Incoming messages are written to SQLite by a goroutine, only while `serve` is running. The `docs/hooks/` directory upstream is about Claude Code session hooks (start the daemon, open `/pair`), not message events. Something has to poll, unless the server is patched.

### Options

| Option | How | Trade-offs |
|---|---|---|
| **Poll `list_messages`** over MCP | A non-agent scheduled job (Node-RED, Airflow, Fission timer, CronJob) calls the tool with `after=<marker>`, then hands any matching message to an action or an agent | Supported interface, same bearer token, no extra mounts. Output is plain text and has no message ID for text messages, so the job needs a regex and a weak dedup key. Latency is the poll interval |
| **Sidecar reading `messages.db`** | A second container in the same pod mounts the same volume (read-only) and queries SQLite | Clean data: real `id`, `chat_jid`, `sender`, `is_from_me`. The volume is ReadWriteOnce, so the reader has to be in the same pod. The schema is internal and may change between releases. Still a poll (or a file watch), not a push |
| **Fork the server and add a webhook** | Patch the incoming-message handler to POST each message to a URL | Real push, no polling, no parsing. Costs maintaining a fork and rebuilding the image on upstream changes. Only worth it if poll latency matters |

Preference at the time of writing: poll `list_messages` first (a 30 to 60 second delay is fine for personal use). Move to the sidecar if the text parsing or the missing IDs become a problem, and to a fork only if polling is not good enough. The polling job should not be an agent: it only calls the agent once there is a new message that passes the checks below.

### `list_messages` details

Input (all optional): `after`, `before` (ISO-8601 UTC), `chat_jid`, `sender_phone_number`, `query` (case-insensitive substring), `limit` (default 20, capped at 100), `page` (zero-based offset), `include_context` (default true), `context_before` and `context_after` (default 1, capped at 20). Results are newest first, with offset paging only (no cursor) and no tiebreaker on equal timestamps.

For a polling job: call with `after=<marker>`, `limit=100` and `include_context=false` (otherwise each match brings neighbouring messages that look like new ones).

- `after` and `before` are exclusive in the SQL (`>` and `<`) although the tool description says inclusive. A message with exactly the marker's timestamp is not returned again, but a second message in the same second as the marker can be missed if the marker is only a timestamp.
- Output is plain text, one line per message: `[2026-01-02 15:04:05] Chat: <chat name> From: <sender name>: <content>`. No timezone marker. Empty result is `No messages to display.`
- The message ID and chat JID appear only for media messages, in a bracketed prefix. Text lines show the chat name, not the JID, so telling chats apart means matching names or calling once per `chat_jid`.
- The account's own messages appear as `From: Me` and there is no filter to exclude them, so the job has to drop them itself (otherwise an automated reply can trigger itself).
- `sender_phone_number` is an exact match on the stored sender (the bare user part). How JIDs are normalised was not verified, so a full JID or a newer LID-style sender may not match.
- `query` does not escape `%` or `_`.
- More than 100 new messages between polls need paging.

### `messages.db` schema (for the sidecar option)

```sql
CREATE TABLE chats (jid TEXT PRIMARY KEY, name TEXT, last_message_time TIMESTAMP);
CREATE TABLE messages (
  id TEXT, chat_jid TEXT, sender TEXT, content TEXT, timestamp TIMESTAMP, is_from_me BOOLEAN,
  media_type TEXT, filename TEXT, url TEXT, direct_path TEXT,
  media_key BLOB, file_sha256 BLOB, file_enc_sha256 BLOB, file_length INTEGER, poll_options_json TEXT,
  PRIMARY KEY (id, chat_jid),
  FOREIGN KEY (chat_jid) REFERENCES chats(jid)
);
```

There is also a `poll_votes` table. The connection uses WAL mode with a 5 second busy timeout, which allows a second reader alongside the server. There are no indexes beyond the primary keys (nothing on `timestamp`, `chat_jid` or `sender`), which does not matter at family-level volume. Schema from `internal/store/store.go`; not documented upstream as a stable interface.

### Cautions

- **Downtime gaps.** Messages that arrive while the pod is down are recovered only through WhatsApp's own history sync, within its retention window (`request_sync` backfills one chat).
- **Untrusted input.** A message that triggers an action is untrusted text, and more so when it goes into an agent. Check the sender against a short allowlist before acting.
- **Rate limits on replies.** The 45 second floor between sends (30 an hour) applies to automated replies too.
- **Groups.** Group messages arrive from every member of the group, so the allowlist matters more there.
