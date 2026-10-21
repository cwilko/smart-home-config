# MQTT Topics

Reference for every MQTT topic convention in use across this homelab. Keep this file
current whenever a new topic or pattern is introduced, or an existing one changes.

Broker: `mqtt.automation.svc.cluster.local:1883` (eclipse-mosquitto, unauthenticated).

## Events and alerts

```
events/<domain>/<entity-type>/<entity-id>/<attribute>/priority/<level>
```

The standard convention for any event, regardless of payload type — scalar/text or
JSON both belong here. `<domain>`: what the event is *about*, not who raised it. In
use: `home`, `system`, `agents` (meta-findings about the agent squad with no better
fit). `<entity-type>`: `device`, `sensor`, `pod`, `net`, `agent`. `<level>`: `OK`,
`INFO`, `WARNING`, `CRITICAL`. Consumed in Node-RED via a `change` node.

**In use:**
- Kapacitor alerting (`smart-home-config/scripts/tasks/*.tick`): e.g.
  `events/home/device/<device>/health/priority/<level>`,
  `events/system/device/<host>/mem/priority/<level>`.
- `arlo2mqtt`: `events/home/sensor/arlo/<cam>/motion/priority/OK` (text payload).
- `data_collector` Airflow agent
  (`smart-home-config/workloads/airflow/dags/agent-orchestration/skills/data_collector/SKILL.md`):
  `events/system/agent/data_collector/<attribute>/priority/<level>`, JSON payload
  with at least a `summary` field.

`events-json/#` is a separate, one-off topic used only by `arlo2mqtt` for its own
snapshot events (`events-json/system/sensor/arlo/<cam>/snapshot/priority/OK`, JSON:
`{"msg": ..., "url": ...}`), consumed in Node-RED via a `json` parser node. It's not a
general "JSON payload" convention — `events/#` already carries JSON fine when a
publisher needs it. Don't use `events-json` for anything new; it's Arlo-specific.

## Device bridges

Command + state + availability, for things with real device semantics:

```
<device>/connected          # retained availability, LWT
<device>/set/#              # commands in
<device>/status/<property>  # state out, retained
```

**In use:** `lgtv2mqtt` — `lgtv/connected`, `lgtv/set/#` (e.g. `lgtv/set/open_max`,
`lgtv/set/toast`), `lgtv/status/volume`, `lgtv/status/mute`,
`lgtv/status/foregroundApp`, `lgtv/status/currentChannel`. Simpler devices skip
straight to `<namespace>/<device>/<command>` — e.g. `home/chromecast/start`.

## Raw sensor / metrics data

```
sensors/<device>/<metric-type>/...   # plural
sensor/#                              # singular — telegraf.conf's subscription only
telegraf/<category>/<name>            # direct metrics ingestion target
```

`telegraf.conf` subscribes to `sensor/#` and `telegraf/#`, feeding
`[[outputs.influxdb]]`. Telegraf only ever consumes here — no `[[outputs.mqtt]]`
exists.

`telegraf/<category>/<name>` is published directly by `googlefit2mqtt`
(`telegraf/health/heart`, `telegraf/health/steps`) and `hive2mqtt`
(`telegraf/hive/<device-name>`), and relayed there by Node-RED for Arlo data
(`telegraf/sensors/arlo`).

`sensor/#` (singular) and `sensors/...` (plural, used by `arlo2mqtt` and Node-RED) are
different topics, not variants of one convention.

## Manual alerts / notification fan-out

```
alerts/#
```

Consumed in Node-RED (node "Manual alerts"), feeding a `FormatForSlack` function, a
Pushover API call, an `mqtt out` to LGTV, and an HTTP call to a LogDNA ingest
endpoint. `FormatForSlack` sets `msg.topic = "chat.meMessage"` and
`msg.payload = {channel, text}` — not a standard Slack Web API call, so whether this
leg currently delivers to Slack is unconfirmed; check directly in Node-RED before
relying on it.

## Other

```
tele/tasmota/SENSOR   # Tasmota's own default convention, unrelated to the schemes above
```

## Future direction: a more consistent convention

Not current state — a proposal for if/when this is worth consolidating. Nothing below
is implemented.

**The core structural issue**: the top level currently mixes two different kinds of
thing as peers — *message category* (`events`, `alerts`, `sensors`, `telegraf`) and
*device identity* (`lgtv`, `home`). That's why there's no single wildcard that
cleanly answers "everything about my home" or "everything that just happened" —
those two axes are tangled together depending on which bridge was written first.

**Target shape**, with domain/entity consistent under every intent rather than just
under events:

```
<intent>/<domain>/<entity-type>/<entity-id>/<attribute>[/priority/<level>]
```

`[/priority/<level>]` isn't free-choice-optional — it's intent-dependent: always
present for `event/` (severity is a property of an event), always absent for
`state/`, `command/`, and `availability/` (none of those have a meaningful severity
level).

- `event/` — something happened. Carries any payload type; no reason to split by
  payload type the way `arlo2mqtt`'s one-off `events-json` topic does — a subscriber
  to a given topic already knows its schema, and that distinction doesn't need
  encoding in the path itself.
- `state/` — current value of something. Unifies `sensors/`, the inconsistent
  `sensor/#`, and device `.../status/...`.
- `command/` — do something. Unifies device `.../set/#` and ad hoc direct commands
  like `home/chromecast/start`.
- `availability/` — online/offline, pulled out on its own rather than bundled into
  `state/` — a lifecycle concern, not a sensor value.

`domain` (`home`/`system`/`agents`, extensible) sits at the same second level under
every intent, so `state/home/device/lgtv/volume` and
`event/home/sensor/arlo/motion/priority/OK` share one shape, and `+/home/#` means
"everything about my home" — not "everything about my home that happens to be an
alert."

**On staying flexible**: that's mostly not a property of the string format — it's
`domain` and `entity-type` staying open vocabularies (documented here, not a hardcoded
enum) and keeping the hierarchy shallow enough that wildcards stay useful as new
sources get added. This document being the thing someone checks *before* a new bridge
invents its own shape does more work than any clever naming scheme would.

**Migration cost, if this is ever pursued**: this spans independently-maintained
repos (Kapacitor `.tick` scripts, several `*2mqtt` bridges, Node-RED flows,
`telegraf.conf`) that each publish/subscribe to the current shapes directly. Not a
single change — would need an overlap period (dual-publish old and new shapes) per
source, retired one at a time, not a flag-day cutover. `telegraf/<category>/<name>`
should stay as-is regardless — it's a Telegraf-specific ingestion target, not a
general convention competing with the others.
