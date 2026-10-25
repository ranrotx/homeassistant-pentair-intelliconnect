# Phase 1 Capture Protocol — Egg Timer + Unmodeled Relays

**Status (2026-10-25):** finished, and the temporary `WS device_data` debug logging this protocol relies on has been removed from `api/client.py`. Kept for reference; to repeat a capture, re-add a debug log of the frame in `_handle_text`.

Goal: capture the **exact field changes** the IntelliConnect pushes when you
start/stop the fountain egg timer and toggle the Blower / Color Light in the
Pentair Home app, so the HA entities can be built against confirmed ground
truth instead of guesses.

A temporary debug log line was added in `api/client.py` (`_handle_text`). With
`debug` logging on, **every** real-time WebSocket `device_data` frame is printed
as a compact `{field_code: value}` map, tagged with the device ID and screen.
When you change something in the app, the controller pushes a delta over the
same WebSocket HA is subscribed to — that delta is your ground truth.

## 1. Enable debug logging

Add to `configuration.yaml` (or the dev `config/configuration.yaml`):

```yaml
logger:
  default: warning
  logs:
    custom_components.pentair_pool: debug
```

Restart HA (dev: `./script/develop`). Confirm both controllers loaded — you
should see `WS device_data ...` lines for **two** different `device=` IDs. Note
which device ID is **Feature Control** (fountain) vs **Main Control** (main
pump); the friendly name isn't in the frame, but the fountain device is the one
whose `ra*`/`ras0` fields move when you drive the fountain.

## 2. Capture each action (one at a time, ~15 s apart)

For each step, **note the wall-clock time you tap** so we can line it up with
the log timestamps. Do them individually — don't batch.

| #   | Action in the Pentair app                                              | What we learn                                                                             |
| --- | ---------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| A   | Let it sit idle ~15 s (baseline)                                       | resting values of `ra0/ra3/ras0/p1` on the fountain device                                |
| B   | Start the fountain egg timer for a **known** duration (e.g. 10 min)    | which field(s) the start writes — `p1` vs `ra3`, one write or two; how `ra0`/`ras0` react |
| C   | Wait ~30–60 s while it runs                                            | `ras0` counting down; `ra4` power                                                         |
| D   | Stop the fountain **early**                                            | the cancel write; how `ras0`/`ra0` reset                                                  |
| E   | Toggle **Blower** on, wait, off                                        | the Blower relay's field family (look for new codes: `rb*`, `p2`, …)                      |
| F   | Toggle **Color Light** on, wait, off; if it has color/theme, change it | the light's field family (`rc*`?) and any color/theme fields                              |

## 3. Pull the relevant log lines

Home Assistant log location varies (`config/home-assistant.log`, or the
`./script/develop` console). Filter to just the capture lines:

```bash
grep "WS device_data" config/home-assistant.log > /tmp/pentair-capture.log
# or, if watching the dev console, copy the WS device_data lines directly
```

## 4. Paste back

Paste the `WS device_data` lines (with timestamps) plus your notes of when you
did A–F. Even a rough "started timer ~14:03:10, stopped ~14:04:20" is enough to
correlate. From that I can:

- confirm the fountain **start** write (fields + count) and the **cancel** write,
- confirm `ras0` is the live remaining countdown for the timed run,
- identify the **Blower** and **Color Light** field families and add named
  constants for them,
- then build the entities against real fields.

## Fields already known (fountain / Relay-1 pump), for reference

| Field  | Meaning                                                                                      |
| ------ | -------------------------------------------------------------------------------------------- |
| `ra0`  | Relay1 on/off + schedule state machine (`0`off `1`on `2`off-sched `3`on-sched `4`timer-done) |
| `ra3`  | Relay1 configured timer duration (seconds)                                                   |
| `ras0` | Relay1 live stop-countdown (seconds, RO)                                                     |
| `p1`   | Relay1 egg timer                                                                             |
| `ra4`  | Relay1 power (watts, RO)                                                                     |

## Cleanup

Done: the temporary debug log line was removed from `api/client.py` on 2026-10-25.
