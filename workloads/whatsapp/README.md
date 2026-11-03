# WhatsApp MCP server

[Sealjay/mcp-whatsapp](https://github.com/Sealjay/mcp-whatsapp) (MIT): a Go server (whatsmeow) that logs in to WhatsApp as a linked device and exposes it as MCP tools over HTTP. It runs here as a plain Deployment in `services`, not as a Fission function: the session is a long-lived websocket with state on disk, so it cannot scale to zero and must never run twice.

| File | What |
|---|---|
| `whatsapp-data.yaml` | Static PV and PVC, 5Gi on `truenas-nvmeof`: the session (`whatsapp.db`), message history (`messages.db`) and uploads. `whatsapp-data.yaml.old` is the earlier version it replaced |
| `deployment.yaml` | ServiceAccount and the Deployment (1 replica, `Recreate`) |
| `service.yaml` | ClusterIP `whatsapp-mcp:8765` |
| *(other repo)* | The `mqtt-sidecar` container in `deployment.yaml` publishes incoming messages to MQTT. Its source, and the workflows that build both images, are in the separate repository `whatsapp-server` (see "Chosen: the MQTT sidecar") |
| *(none here)* | The Traefik route `https://api.squirrelhome.co.uk/whatsapp/mcp` (`/whatsapp` stripped) is not in this directory: it is a rule in `api-squirrelhome` in `../traefik/ingress/ingressroute-api.yaml`, with the middleware `whatsapp-mcp-stripprefix` (namespace `services`) next to it |
| `../fission/workloads/whatsapp-pair/` | Separate directory under the Fission workloads, because it is a Fission function: container function (Caddy) that injects the token so the pairing QR image opens in a plain browser at `https://api.squirrelhome.co.uk/whatsapp/pair`. `config/Caddyfile` is the source of `configmap.yaml` |

Not in this directory: the shared secret `squirrel-api-secret` (key `SQUIRREL_API_TOKEN`, namespace `services`), see step 2.

## Deploy

### 1. Build and push the image

There is no published image. Build the upstream Dockerfile at a pinned release tag. The cluster nodes are amd64, so build for that platform when building on an Apple Silicon Mac.

**With GitHub Actions (preferred):** run the `Build WhatsApp MCP image` workflow (`.github/workflows/whatsapp-mcp-image.yml` in the separate `whatsapp-server` repository, which also holds the sidecar source) from that repository's Actions tab, with the upstream tag as the `ref` input (default `v0.6.0`). It builds `linux/amd64`, logs the image's user and home in the "Show the image's user and home" step, then pushes `wilkobets/whatsapp-mcp:<ref>`. It needs the `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` repository secrets. Use the logged `id` and `HOME` for the checks below. After bumping `ref`, update the image tag in `deployment.yaml` to match.

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

### 2. The API token

The bearer credential for `/mcp` and `/pair/*` is the shared `SQUIRREL_API_TOKEN`, not a WhatsApp-specific token. The Deployment reads it from the key `SQUIRREL_API_TOKEN` of the secret `squirrel-api-secret` in `services` and passes it to the server as `WHATSAPP_MCP_TOKEN` (the only name the server reads). That secret is managed outside this directory (see `secrets/squirrel_api_secret.yaml.example` at the repo root for how it is created); it must exist before the pod will start. Anything holding the token can send as the WhatsApp account, so treat it accordingly.

### 3. Apply

```bash
kubectl apply -f whatsapp-data.yaml -f deployment.yaml -f service.yaml
kubectl apply -f ../traefik/ingress/ingressroute-api.yaml
kubectl -n services rollout status deploy/whatsapp-mcp
kubectl apply -f ../fission/workloads/whatsapp-pair/configmap.yaml -f ../fission/workloads/whatsapp-pair/function.yaml
```

The second `apply` is the pairing proxy (step 4); it needs the Fission install and the `services` namespace, like `../fission/workloads/github-mcp`. After editing `../fission/workloads/whatsapp-pair/config/Caddyfile`, regenerate `configmap.yaml` with the command in the Caddyfile header before applying.

### 4. Pair the phone

`/pair` and `/pair/qr.png` are behind the bearer token, and the server reads it only from an `Authorization: Bearer` header. It does not accept a query parameter, cookie or login form, so a browser opening the server's `/pair` directly gets 401 (the ingress does not route `/pair` to the server at all, only `/whatsapp/mcp`). The token is enforced whenever the server runs with `-allow-remote` (as here), so port-forwarding does not bypass it either.

Use the pairing proxy instead: open **`https://api.squirrelhome.co.uk/whatsapp/pair`**. It is a Fission function (`../fission/workloads/whatsapp-pair/`) that adds the token itself and returns the server's current pairing QR (`/pair/qr.png`) as a PNG for a plain GET of that URL; everything else (including `/mcp`, the server's pairing page, the pairing-code form and the "Force re-pair" button, `/pair/reset`) is a 403. It scales to zero, so the first load after a quiet period takes a few seconds.

**A QR is only good for about 2.5 minutes after the pod starts, and reloading does not renew it.** Verified against the live server: the server makes its QR at startup; when that pairing window times out (about 160 seconds, the websocket closes with an EOF warning) it keeps serving the same dead code, and the phone answers "Couldn't link device. Try again later". So:

1. Restart the pod: `kubectl -n services rollout restart deploy/whatsapp-mcp` (wait for the rollout; the log ends `unpaired: open ... to scan QR`).
2. Open `/whatsapp/pair` straight away, zoom the browser to about 200% (the PNG is only 256x256 and blurs when scaled), and scan from Settings → Linked Devices → Link a Device within a couple of minutes.
3. If you miss the window, restart again.

After you unlink the device from the phone, restart the pod before pairing again: the server drops its session (`Device logged out`) but does not start a fresh QR on its own.

The server's own pairing page is not used, because it links to absolute `/pair/...` URLs that would not reach this proxy. If the account is already paired, or no QR is ready yet, the server answers 404 and so does the proxy. There is no pairing-code (phone number) option through the proxy.

The proxy has no caller authentication, so anyone who can reach the API host can see the pairing QR. That only matters while the account is unpaired: when paired, there is no QR and the URL returns a 404. Someone who scanned the QR with their own phone would link their account to the server, so do the pairing yourself and, if the LAN is not fully trusted, delete the function and trigger when you are done (`kubectl delete -f ../fission/workloads/whatsapp-pair/function.yaml`) and apply them again at the next re-pair.

Fallback without the proxy: `kubectl -n services port-forward deploy/whatsapp-mcp 8765:8765`, a header-injecting browser extension (for example ModHeader) adding `Authorization: Bearer <SQUIRREL_API_TOKEN value>` for `127.0.0.1`, then open `http://127.0.0.1:8765/pair`. Turn the rule off afterwards, because the extension holds the token.

Then scan the QR code (Settings → Linked Devices → Link a Device), within the window described above. The first history sync can take several minutes. (Pairing by phone number works only through the port-forward fallback below, where the form is not blocked.)

The linked-device session needs the primary phone to stay online: leave it plugged in, on Wi-Fi, with WhatsApp installed and exempt from battery optimisation (WhatsApp unlinks companion devices when the primary has been offline for about two weeks). The session also rotates roughly every 20 days; restart the pod to get a fresh QR (see above). Re-pair when `get_status` returns `paired: false` (`connected: false` alone can be a dropped connection).

Alternative without a browser: the binary's `login` subcommand shows a terminal QR (`login -phone +<number>` gives a pairing code). It needs the store volume, and the server allows one instance per store, so the Deployment would have to be scaled to 0 first. Not tested here.

### 5. Connect clients

```bash
claude mcp add --transport http whatsapp https://api.squirrelhome.co.uk/whatsapp/mcp \
  --header "Authorization: Bearer $SQUIRREL_API_TOKEN"
```

Automated agents use the same URL and `Authorization` header. The endpoint is stateless (no `Mcp-Session-Id`).

## Behaviour to know about

- **Messages are stored, not pushed.** Incoming events go to SQLite while the server runs; an agent reads them with `list_messages` / `list_chats` (pass `include_context=false` to `list_messages`, or neighbouring messages are repeated in the output; see the `list_messages` details below). Anything that arrives while the pod is down is recovered only through WhatsApp's own history sync, within its retention window (`request_sync` backfills one chat).
- **Rate limits** (from the v0.4.0 release notes): a 45 second floor between sends, 30 an hour, stricter for first-contact sends. This is deliberate: it protects the number from being banned. Recipients should have the account saved as a contact.
- **No recipient allowlist.** Any chat the account can see is reachable by anyone holding the token. Prompt injection from an incoming message is the main risk (the upstream README calls out the "lethal trifecta"); keep the contact list to family.
- **Health:** the server has no health route. The probes only check that port 8765 accepts connections. The MCP tool `get_status` reports whether WhatsApp is connected and which account is paired.
- **One instance per store.** Do not scale this above 1 and do not change the strategy from `Recreate`.

## If something goes wrong

- **Pod in `CreateContainerConfigError`:** the secret `squirrel-api-secret` (key `SQUIRREL_API_TOKEN`) is missing from `services` (step 2).
- **Crash loop, "permission denied" on the store:** the pod's user and `fsGroup` do not match the image (step 1).
- **PVC stuck `Pending`, or the pod can't mount the volume:** the volume is a pinned static PV (`whatsapp-data.yaml`) onto the zvol `SSD_pool/k8s/block/pvc-whatsapp-mcp-data`, exported as the NVMe-oF subsystem `k8s-services-whatsapp-mcp-data` (namespace `nsid` 2). Check the PV's `nqn` and `nsid` against TrueNAS (`nvmet.subsys.query` and `nvmet.namespace.query`). How it was made, and how to grow or move it, is in `smart-home-docs/storage/PERSISTENT-VOLUMES.md`. To expand it, raise the PVC's request only.
- **403 through the ingress, but `/mcp` works through a port-forward when you send the bearer header:** the server's DNS-rebinding protection (from the mcp-go library) rejects a non-loopback `Host` header. The upstream README does not document a way to allow a hostname. Check the project's issues and `serve -h`; the fallback is a Caddy sidecar that rewrites `Host`, as `../fission/workloads/github-mcp` does for a different reason.
- **Phone says "Couldn't link device. Try again later":** the QR is stale (see step 4). Restart the pod and scan the new code within a couple of minutes. This happened on a years-old account too, so it is not a new-number restriction. The server log shows no pairing attempt when it is a stale code.
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

On a remote logout the daemon drops its session (`Device logged out`), but observed on the live server it did not produce a fresh QR afterwards; a pod restart did. Treat the restart as part of any re-pair, so an automated alert would need to restart the pod (or call the reset endpoint) before fetching the QR. The same pairing path runs at startup when the device is not logged in. Not verified: whether the "Force re-pair" button in `/pair` triggers pairing again (its handler logs out and redirects), and whether repeated logout cycles register the logout handler more than once.

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
| **Sidecar reading `messages.db`** | A second container in the same pod mounts the same volume and queries SQLite. The mount has to be read-write (the database is in WAL mode, so even a reader updates the `-shm` file); the program opens the database read-only itself | Clean data: real `id`, `chat_jid`, `sender`, `is_from_me`. The volume is ReadWriteOnce, so the reader has to be in the same pod. The schema is internal and may change between releases. Still a poll (or a file watch), not a push |
| **Fork the server and add a webhook** | Patch the incoming-message handler to POST each message to a URL | Real push, no polling, no parsing. Costs maintaining a fork and rebuilding the image on upstream changes. Only worth it if poll latency matters |

Preference at the time of writing: poll `list_messages` first (a 30 to 60 second delay is fine for personal use). Move to the sidecar if the text parsing or the missing IDs become a problem, and to a fork only if polling is not good enough. The polling job should not be an agent: it only calls the agent once there is a new message that passes the checks below.

### Chosen: the MQTT sidecar (written, not yet built or deployed)

The sidecar is the container `mqtt-sidecar` in `deployment.yaml`. Its source (a small Go program, `sidecar/main.go`, commented as a Go tutorial) and `Dockerfile` live in the separate repository `whatsapp-server`, which also holds both image workflows. The image is built by that repository's `.github/workflows/whatsapp-sidecar-image.yml` (manual, input `tag`, default `v0.1.0`; pushes `wilkobets/whatsapp-sidecar:<tag>`; needs the `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` secrets there). After a new build, update the image tag in `deployment.yaml`. **Build the image before applying `deployment.yaml`**: until it exists, the pod is not ready and the MCP endpoint is down. Nothing in the sidecar has been compiled or run yet (no Go or Docker on the machine it was written on), so the first build may need fixes.

What it does: every `POLL_INTERVAL` (1s) it reads rows of `messages` with a `rowid` above the last one it saw and `is_from_me = 0`, and publishes each as JSON to the single topic in its `TOPIC` environment variable (`events/home/device/whatsapp/message-received/priority/INFO`, following `smart-home-docs/reference/MQTT_TOPICS.md`) on the broker `mqtt.automation.svc.cluster.local:1883` (QoS 1, not retained). The program has no topic logic of its own, so the naming convention lives in `deployment.yaml`. Payload: `id`, `chat_jid`, `sender`, `content`, `media_type`, `timestamp` (Unix seconds), `is_group`. There is one topic for every chat: a subscriber that wants a single chat filters on `chat_jid` in the payload.

Limits to know about:
- **It starts from "now".** The position is kept in memory and seeded from the newest row at start-up, so a message that arrives while the sidecar is restarting (or the pod is down) is never published. It is still in `messages.db` and `list_messages`.
- **Old rows are skipped.** A history sync (for example after a re-pair) inserts old messages as new rows. Anything older than `MAX_AGE` (10m) is skipped and logged, not published.
- **No message text in the logs** (logs are less private than the chat).
- **A failed publish is retried every tick** without moving the position on, and logged as `ERROR`. A broker outage therefore shows in `kubectl -n services logs deploy/whatsapp-mcp -c mqtt-sidecar`.
- **The broker has no authentication**, so anything on the LAN can read these messages and publish to the same topics. Do not treat a message on this topic as proof the sender is who they say.
- **Dependency versions are not pinned** (see the comment in the `Dockerfile`).
- A webhook instead of (or as well as) MQTT would be a small change to `publish` in `main.go`.

### `list_messages` details

Input (all optional): `after`, `before` (ISO-8601 UTC), `chat_jid`, `sender_phone_number`, `query` (case-insensitive substring), `limit` (default 20, capped at 100), `page` (zero-based offset), `include_context` (default true), `context_before` and `context_after` (default 1, capped at 20). Results are newest first, with offset paging only (no cursor) and no tiebreaker on equal timestamps.

For a polling job: call with `after=<marker>`, `limit=100` and `include_context=false`.

**Always pass `include_context=false` when reading messages programmatically.** With the default (true), the server runs a separate context query per match and appends the message before it, the match and the message after it (`ListMessages` in `internal/store/queries.go`), with no de-duplication. Checked live: `limit=5` on a short chat returned 13 lines, with the middle messages repeated up to three times, and the same call with `include_context=false` returned the 5 unique messages. The extra lines are older neighbours as well as repeats, so a poller that does not set the flag can treat an already-seen message as new. It is a read-time effect only: each message is stored once. `limit` counts matches, not output lines, so the response can hold more lines than `limit`. Use `context_before` and `context_after` only when surrounding messages are wanted, for example to give an agent a conversation snippet.

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
