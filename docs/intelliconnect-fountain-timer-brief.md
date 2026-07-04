# Build Brief: Fountain Egg-Timer + Multi-Controller Support for the Pentair IntelliConnect Integration

**Target repo:** `tikotzky/homeassistant-pentair-intelliconnect` (fork it)
**Component domain:** `pentair_pool`
**Component path:** `custom_components/pentair_pool/`
**Primary goal:** Let Home Assistant start and monitor the **fountain egg timer** (run-for-N-minutes then auto-off) and control the fountain on/off, matching the Pentair Home app.
**Secondary goal:** Surface the other relays that aren't modeled yet (Blower, Pentair Color Light).

---

## 0. Correction from an earlier draft — read this first

An earlier version of this brief assumed the fountain was an auxiliary relay (`rb*`/`p2`) on a single controller. **That is wrong.** The verified topology is:

- The account has **two IntelliConnect controllers** (two cloud devices).
- The **fountain is a pump** — specifically the **primary pump (Relay 1) on the second controller**, not an aux relay.
- The fountain is driven by an **egg timer (one-shot countdown), with no recurring schedule**.

This means the fountain almost certainly reuses the **same `ra*` + `p1` egg-timer field family already implemented for the Main Pump**, just under a different device ID. The core work is therefore **(a) multi-controller enumeration** and **(b) an egg-timer entity** — not reverse-engineering a new relay family.

---

## 1. Verified hardware topology (from the Pentair Home app)

Two controllers appear under **Pools → Pool Devices**, each a separate IntelliConnect cloud device:

### Controller A — "Feature Control"

| App device      | Type                                  | Notes                                               |
| --------------- | ------------------------------------- | --------------------------------------------------- |
| Fountain        | **Pump (Relay 1 of this controller)** | The target. Started via egg timer; **no schedule**. |
| Air Temperature | Sensor                                | `t*`                                                |

### Controller B — "Main Control"

| App device              | Type                    | Notes                                                               |
| ----------------------- | ----------------------- | ------------------------------------------------------------------- |
| Main Pump               | Pump (Relay 1)          | Already modeled as the "filter pump" today.                         |
| Blower                  | Aux relay               | Not modeled yet (P1).                                               |
| Pentair Color Light     | Aux relay (color light) | Not modeled yet (P1); may support color/theme via power sequencing. |
| Heater                  | `htd*`                  | Modeled.                                                            |
| iChlor Salt Chlorine    | `icd*` / `ics*`         | Modeled.                                                            |
| Air / Water Temperature | Sensors                 | `t0` / `t1`.                                                        |

**Key implication:** each controller has its **own field namespace**. "Relay 1" on Feature Control (the fountain) and "Relay 1" on Main Control (the main pump) both use `ra0/ra1/ra2/ra3/ra4/ras0/p1`, but scoped to different device IDs. Entities must be keyed per device, and the friendly names ("Fountain", "Blower", "Pentair Color Light", "Main Pump") should be pulled from each device's cloud metadata rather than hard-coded as "Relay 1".

---

## 2. Current integration state and the gap

The integration talks to the Pentair Cloud (AWS Cognito auth + real-time WebSocket, 60 s REST fallback). Today it models the Main Pump (Relay 1), heater, salt cell, and a single daily schedule.

Gaps to close:

1. **Multi-controller enumeration.** The README claims "one HA device per IntelliConnect controller on that account," but this must be **verified against a two-controller account**. If only the first/primary device is surfaced, the Feature Control controller (and thus the fountain) never appears. This is the most likely root cause of "can't run my fountain timer."
2. **No egg-timer entity.** `p1` (Relay1_Egg_Timer), `ra3` (Relay1_Timer duration), and `ras0` (Relay1_Timer_Status, live countdown) are defined in `const.py` but exposed by **no entity**. Even for the Main Pump you can't start a timed run today.
3. **Blower and Color Light relays are unmodeled** (secondary).

---

## 3. Objectives, prioritized

- **P0 — Multi-controller support:** enumerate every IntelliConnect device on the account; create one HA device each; name entities from cloud friendly-names.
- **P0 — Fountain egg timer:** on/off + start-timed-run + remaining-time for the Feature Control pump.
- **P1 — Blower:** expose the Blower aux relay on Main Control as a `switch`.
- **P1 — Pentair Color Light:** expose the color light on Main Control as a `light` (on/off first; color/theme as a stretch).
- **P2 — Main Pump egg timer:** apply the same egg-timer entity to the Main Control pump (same mechanism, free once P0 is done).

---

## 4. How the fountain is controlled (egg timer, no schedule)

Confirmed field family for a Relay-1 pump (ground truth from `const.py`, applies per device):

| Field  | Meaning                                                       | Relevant to fountain?                    |
| ------ | ------------------------------------------------------------- | ---------------------------------------- |
| `ra0`  | Relay1_Manual_Schedule — on/off + schedule-mode state machine | Yes (on/off)                             |
| `ra1`  | Relay1_Start_Time (UTC sec-of-day)                            | **No** (fountain has no schedule)        |
| `ra2`  | Relay1_End_Time (UTC sec-of-day)                              | **No**                                   |
| `ra3`  | Relay1_Timer — configured timer duration, seconds             | **Yes** (egg-timer duration)             |
| `ra4`  | Relay1_Power (watts, RO)                                      | Yes (feedback)                           |
| `ras0` | Relay1_Timer_Status — live stop countdown, RO seconds         | **Yes** (remaining)                      |
| `p1`   | Relay1_Egg_Timer                                              | **Yes** (likely the on-demand egg timer) |

`ra0` state machine: `0`=off/no-sched, `1`=on/no-sched, `2`=off/scheduled, `3`=on/scheduled, `4`=timer-done/scheduled.

**To confirm in discovery (Phase 1):** exactly which field(s) the app writes when the user "starts an egg timer" — the relationship between `p1`, `ra3`, and `ras0`, and whether starting a timed run is one write (set duration + turn on) or two. The user reports "starting one of the egg timers," so also confirm whether multiple egg-timer presets/slots exist or it's a single per-relay egg timer.

---

## 5. Entity-design options for the egg timer (pick one; ranked)

1. **Switch + Number (duration) + Sensor (remaining) — recommended.** Switch on starts the native egg timer for the Number's value; Sensor shows remaining; firmware auto-offs. _Pros:_ familiar, reuses the existing pump-switch code, automatable. _Cons:_ two-step; must define "switch off = cancel."
2. **Button (start) + Number (duration) + Sensor (remaining).** _Pros:_ cleanest match to the app's one-shot egg timer. _Cons:_ buttons are stateless in the UI; early-stop needs a separate control.
3. **Custom service (`pentair_pool.start_egg_timer`, duration) + Sensor.** Mirrors the existing `reload_data` service. _Pros:_ maximum automation flexibility. _Cons:_ not a tappable dashboard control by itself.
4. **`fan`/speed entity.** Only if the fountain pump is variable-speed (confirm in discovery). _Pros:_ maps speed. _Cons:_ overkill for single-speed; egg timer maps poorly.
5. **HA `timer` helper + plain switch — not recommended.** _Pros:_ no firmware timer. _Cons:_ state lives in HA, so starting the fountain from the wall panel/app desyncs it and bypasses the native egg timer the user relies on.

Default to **#1** (or #2). Mirror the heater-cooldown sensor's 1 Hz local tick (re-anchored on each WS push) for a smooth remaining-time countdown.

---

## 6. Implementation plan (phased)

### Phase 0 — Orientation

1. Fork/clone; symlink the component into a dev HA instance.
2. Read `const.py`, `__init__.py`, `coordinator.py`, then the existing `switch.py` / `time.py` / `number.py` / `climate.py`. Note how a Relay-1 entity reads its field, writes via the cloud client, and reconciles optimistic state against the WS push.
3. Read the dev-notes `ENDPOINTS.md` (referenced in `const.py`) for the capture methodology.

### Phase 1 — Multi-controller + fountain discovery (do before writing entities)

1. Enable debug logging:

   ```yaml
   logger:
     default: warning
     logs:
       custom_components.pentair_pool: debug
   ```

2. Inspect how the integration lists account devices. **Confirm both controllers (Feature Control + Main Control) are returned and iterated.** If only one device is handled, fix enumeration first — this alone may surface the fountain.
3. With logging on, in the Pentair Home app: (a) start the fountain egg timer for a known duration, (b) let it run, (c) stop early once. Capture the payloads and **diff** to identify the exact write(s) and the `ra3`/`ras0`/`p1` behavior for the Feature Control device.
4. Capture the Blower and Color Light relays on Main Control by toggling each and diffing, to identify their aux-relay field families (`rb*`/`rc*` etc.) and any color/theme fields for the light.

**Deliverables:** confirmed per-device field tables added to `const.py` with comments; a note appended to the dev-notes doc.

### Phase 2 — Multi-controller correctness

1. Ensure one HA device is created per controller with a stable `unique_id` derived from the cloud device ID.
2. Pull each device's **friendly name** from cloud metadata so entities read "Fountain", "Blower", etc., not "Relay 1".
3. Ensure entities are created **only when the underlying field is reported**, so neither controller produces orphan entities.

### Phase 3 — Fountain entities

1. `switch` for fountain on/off (mirror the filter-pump switch: `is_on` follows reality/power, optimistic until the WS push confirms, preserve any co-encoded bits).
2. Egg-timer per the chosen design (#1): `number` (duration, minutes), `sensor` (remaining, 1 Hz local tick), and wire "switch on" (or a button) to start the native egg timer.

### Phase 4 — Blower & Color Light (P1)

1. `switch` for the Blower relay.
2. `light` for the Pentair Color Light — on/off first; color/theme (IntelliBrite-style) only if the captured fields make it safe.

### Phase 5 — Hardening & PR

1. Edge cases: controller offline, WS reconnect mid-countdown, timer=0, double-tap ordering (keep `PARALLEL_UPDATES=1`), device present on account but currently unreachable.
2. Update `README.md` entity tables and any `strings.json`/translations.
3. Pass hassfest/HACS validation; add tests for the new field parsing and write payloads.
4. Open a PR upstream (maintainer is active) and keep the fork installable via HACS custom repo meanwhile.

---

## 7. Known-good facts from `const.py` (don't re-derive)

- Cognito (US): region `us-west-2`, user pool `us-west-2_lbiduhSwD`, client `3de110o697faq7avdchtf07h4v`, identity pool `us-west-2:6f950f85-af44-43d9-b690-a431f753e9aa`. (EU pool exists, unused.)
- API host `https://api.pentair.cloud`; WebSocket `wss://g44t970cbi.execute-api.us-west-2.amazonaws.com/prod`.
- `PARALLEL_UPDATES = 1` — writes are serialized on purpose; keep it.
- Schedule times are **UTC seconds-of-day**, converted using HA's timezone (relevant only to scheduled relays, not the fountain).
- Device model tag is **PIF0**; field codes reverse-engineered from `com.pentair.pentairhome v4.2.18`.

> The exact filenames/classes for the existing platforms could not be re-enumerated at write time (GitHub API rate limit). **Read the actual repo files before coding** and mirror their patterns.

---

## 8. Constraints & gotchas

- **Per-device namespacing.** "Relay 1" exists on both controllers; never mix device contexts. Key everything by cloud device ID.
- **Cloud-only.** All control via Pentair Cloud WS/REST; fail gracefully on token expiry (refresh margin already handled).
- **Don't clobber sibling bits.** Read-modify-write only the target bit (mirror the filter-pump switch).
- **Optimistic state must reconcile** against the WS push.
- **Conditional entity creation** on reported fields to avoid orphans across two dissimilar controllers.
- **Friendly names from metadata**, so the fountain reads "Fountain," not "Relay 1."

---

## 9. Acceptance criteria

1. Both controllers (Feature Control, Main Control) appear as separate HA devices with correctly named entities.
2. A fountain **switch** reflects real state and toggles the pump, verified against the app.
3. Setting a duration and starting a **timed run** makes the fountain auto-stop after that duration (native egg timer), with a smooth remaining-time sensor that snaps to 0 on stop.
4. State stays correct when the fountain is started/stopped from the wall panel or app (no desync).
5. Blower switch and Color Light entity function on Main Control (P1).
6. Installs without a given device/relay see no orphan entities.
7. Passes hassfest/HACS validation; README updated.

---

## 10. Open questions to resolve in Phase 1

- Does the integration currently enumerate **both** controllers, or only the primary? (Root-cause check.)
- Which field(s) does "start egg timer" write for the fountain — `p1` vs `ra3` — and is it one write or two? Is there more than one egg-timer preset/slot?
- Is the fountain pump single- or variable-speed (does it expose RPM/speed fields)?
- Aux-relay field families for Blower and Color Light on Main Control (`rb*`/`rc*`?), and does the Color Light expose color/theme control or only on/off?
- Firmware-accepted egg-timer duration range and units (seconds vs minutes).
