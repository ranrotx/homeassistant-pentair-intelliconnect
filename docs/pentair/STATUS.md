# Pentair IntelliConnect integration — project status

Snapshot of where things are so any session in the future can pick up cleanly. Last updated 2026-10-25 (fork branch `feat/vsf-pump-and-capability-gating`).

## 1. What this is

A Home Assistant custom integration that talks to Pentair Cloud (the service behind the _Pentair Home_ mobile app). Reverse-engineered from `com.pentair.pentairhome v4.2.18`. Originally tested against one IntelliConnect (`deviceType=PIF0`) with a single-speed filter pump, a heater, and an IntelliChlor salt cell. Since 2026-07 it has also been tested on a two-controller account: Main Control (IntelliFlo VSF pump, heater, IntelliChlor, Color Light on Relay 1, Blower on Relay 2) and Feature Control (an IntelliFlo VSF fountain pump only).

Reverse-engineering artifacts (mitmproxy captures, Frida hooks, decompiled APK, the full Pentair Cloud API reference) live in a separate research workspace outside this integration's repo, and are not required to build or run this integration. This document focuses on the integration's state, not the API itself.

## 2. Current state

### Working

Confirmed end-to-end on a live HA instance:

| Entity                                     | Source field(s)               | Read                           | Write                                                            |
| ------------------------------------------ | ----------------------------- | ------------------------------ | ---------------------------------------------------------------- |
| `climate.<dev>_heater`                     | `htd1`, `htd2`, `htd13`       | ✅                             | ✅ HVAC OFF/HEAT + setpoint (tenths of °F) + heater timer action |
| `sensor.<dev>_heater_timer_remaining`      | `hts2`                        | ✅ s                           | —                                                                |
| `sensor.<dev>_filter_pump_power`           | `ifs3`, fallback `ra4`        | ✅ W (real time on VSF)        | —                                                                |
| `sensor.<dev>_pump_speed`                  | `ifs4`                        | ✅ RPM                         | —                                                                |
| `sensor.<dev>_pump_program`                | `ifs2`, names `p5`–`p8`       | ✅ Off / Priming / program     | —                                                                |
| `sensor.<dev>_pump_timer_remaining`        | `ifs27`                       | ✅ min (diagnostic)            | —                                                                |
| `sensor.<dev>_chlorine_output_actual`      | `ics1`                        | ✅ %                           | —                                                                |
| `sensor.<dev>_salt_level`                  | `ics2`                        | ✅ ppm                         | —                                                                |
| `sensor.<dev>_salt_cell_water_temperature` | `ics9`                        | ✅ °F                          | —                                                                |
| `sensor.<dev>_boost_remaining`             | `ics13`                       | ✅ s                           | —                                                                |
| `sensor.<dev>_salt_cell_lifetime_hours`    | `ics15`                       | ✅ h                           | —                                                                |
| `sensor.<dev>_heater_cooldown`             | `htd14`                       | ✅ s (likely config, not live) | —                                                                |
| `sensor.<dev>_salt_cell_firmware`          | `ics11`                       | ✅ string                      | —                                                                |
| `sensor.<dev>_salt_cell_model`             | `ics12`                       | ✅ string                      | —                                                                |
| `binary_sensor.<dev>_online`               | top-level `online`            | ✅                             | —                                                                |
| `binary_sensor.<dev>_alarm`                | top-level `alarm`             | ✅                             | —                                                                |
| `binary_sensor.<dev>_filter_pump_running`  | `ifs4`/`ifs3`, fallback `ra4` | ✅                             | —                                                                |
| `binary_sensor.<dev>_pump_enabled`         | `ifs1` (10 = enabled)         | ✅                             | —                                                                |
| `binary_sensor.<dev>_<relay nickname>`     | `ra0`/`ra4`, `rb0`/`rb4`      | ✅ on/off (60 s REST lag)      | —                                                                |

Round-trip write verified for heater HVAC mode + setpoint. The filter pump switch, Daily Schedule switch, schedule start/end times, and chlorine slider have been removed: on VSF accounts Relay 1 is not the pump (it drives the Color Light here), and schedules, programs and chlorine output are now managed only in the Pentair app. Entities are gated on the `listdevices` accessory manifest (`entity_utils/capabilities.py`).

### Known issues / pending

1. **Cooldown indicator not yet identified.** When the heater shuts down it keeps the pump running for `htd14` seconds. The pump switch already correctly stays ON during cooldown (because `is_on` reads `ra4`, the physical power draw). What's missing is a _why_ indicator — a separate `binary_sensor.cooldown_active` or attribute on the pump switch — telling the user "pump is locked due to cooldown."
   - The cooldown capture script (`script/_cooldown_capture.py`) ran but didn't isolate the live-countdown field because the test conditions weren't right (heater wasn't actively heating at start; Daily Schedule was masking the cooldown effect anyway).
   - **Next try:** set climate mode to OFF while heater is actively heating (`htd1 == "1"`), watch the WS feed for a field whose value ticks down. Likely an `hts*` (heater status) field we haven't surfaced.

2. **IntelliChlor boost mode** isn't exposed as a control yet. We know the protocol (`icd2`/`icd3` write-and-forget, `ics13` countdown read) but haven't built UI for it. Candidate shapes:
   - `button.<dev>_start_boost` + `number.<dev>_boost_duration` (or similar pair)
   - A custom service `pentair_pool.start_boost {duration_seconds}`
   - The boost-remaining sensor already exists; just needs the trigger.

3. **IntelliFlo program start/stop** not exposed. On VSF pumps the app's Program 1–4 cards map to the `ifd*` SpeedN fields, and the running program is `ifs2`. Starting or stopping a program changes no stored field, and test writes to `ifs1`/`ifs2`/`dr0` didn't start the pump. Next step is a mitmproxy capture of the app; see [`../intelliconnect-program-control.md`](../intelliconnect-program-control.md).

4. **Heater timer** is exposed as the `pentair_pool.start_heater_timer` action plus `sensor.<dev>_heater_timer_remaining`. Decoded from the Android app (v4.2.21, `IC1_HeaterTimer`) and verified live on 2026-10-25: PUT `htd13` (Heater_EggTimer) in seconds, with `htd1=1` only if the heater is off. `hts2` (HeaterEggTimerStatus) then counts down in seconds, and at 0 the firmware sets `htd1=0` itself; `htd13` keeps its old value. Neither the timer nor heater-on starts a pump (verified live: heater on, water below setpoint, IntelliFlo enabled but stopped, pump stayed off), so the heater stays in Auto idle without flow. The `heating_pump_program` option covers this: the climate entity runs that program (`c1`) when HA turns the heater on or starts a timer while `ifs2` = 0, and after `htd1` = 0, `htd14` = 0 and a 120 s grace (heater fields only arrive with the REST poll) it sends `c1=6` then `c1=5` (`climate/heating_pump.py`). Pump start/stop for heating is not yet verified live. Heater schedules (`htd4`–`htd12`, UTC `YY MM DD HH mm` strings) are deliberately not exposed; they stay in the app. `htd1` values from the app: 2 = timer/schedule idle, 4 = timer/schedule heating. The app blocks heater writes while `ecs1` ≠ 0; the integration does the same.

5. **Token refresh** is implemented but unverified live. The test session has been < 1 hour each run so the refresh path (`REFRESH_TOKEN_AUTH`) hasn't been exercised. Leave HA running > 1 h to validate.

6. **Multiple devices per account** works: confirmed live with two IntelliConnect controllers on one account (2026-07).

7. **Non-PIF0 device types** (`IF31` IntelliFlo, `ICT1` IntelliCenter, `WQM1` ChemCheck, etc.) — field codes unknown. The auth/REST/WS plumbing should work for them, but no entities will spawn because the platform gating checks for PIF0-specific fields.

8. **`binary_sensor.intelliconnect_alarm`** has been reading `on` throughout the session. Worth checking what alarm code is being raised (likely in `ics3` for the salt cell). Not yet decoded.

9. **Water/air temperature sensors** — done: `t0` (water, gated on the "Water Temperature" accessory) and `t1` (air).

10. **Blueprint's options flow** still has stale demo fields (`update_interval_hours`, `enable_debugging`, `custom_icon`). Imports were stubbed to satisfy `from ...const import DEFAULT_*`; the actual options dialog isn't wired to anything functional. Either remove it or wire the poll interval to real config.

## 3. How to develop on this

### One-command workflow (host → devcontainer)

`script/pentair_test` is a host-side wrapper that auto-execs into the running VS Code devcontainer via `docker exec`, so VS Code's port-forwarding doesn't matter. All HTTP traffic with HA happens over loopback inside the container.

```bash
# Inspect
./script/pentair_test entries          # list config entries
./script/pentair_test states           # list every Pentair entity + value
./script/pentair_test logs             # recent pentair_pool log lines
./script/pentair_test errors           # errors + tracebacks only

# Mutate
./script/pentair_test call SVC k=v ... # arbitrary HA service call
                                       # e.g.  call switch.turn_on entity_id=switch.x
                                       # e.g.  call climate.set_temperature entity_id=climate.x temperature=88
./script/pentair_test remove           # delete every pentair_pool entry
./script/pentair_test flow EMAIL PW    # add the integration via config flow
./script/pentair_test restart          # POST homeassistant.restart + wait

# Combined
./script/pentair_test loop EMAIL PW    # restart -> remove -> add -> errors
```

The driver reads the user's stored refresh token from `config/.storage/auth` and mints short-lived access tokens automatically — no manual HA token setup needed.

### Code-change debugging cycle

1. Edit `custom_components/pentair_pool/*.py` on the host.
2. `./script/pentair_test restart` — HA picks up the change.
3. `./script/pentair_test states` + `errors` — verify.

When the integration's entity definitions change (`description.key`, `_attr_name`, new entities), HA caches some attributes (`original_name`) in `config/.storage/core.entity_registry` from first registration. To force a fresh registration after a rename, either:

- Bump the `description.key` (creates new entity with new unique_id; old becomes orphaned),
- Or patch the registry directly: `python3 -c "..."` editing `original_name` in `core.entity_registry` then restart (see `docs/pentair/CHANGELOG.md` for the exact pattern used to flip "end" → "stop").

### Reverse-engineering more behavior

The captured-traffic archives (mitmproxy `.mitm` files, WS-frame JSONL) and Frida-hook + emulator setup live in a separate research workspace outside this repo. When you need to capture new behavior, the workflow is:

1. Re-arm the Pentair Android app on a rooted emulator with the SSL-pinning bypass.
2. Run Frida bypass + mitmproxy intercept.
3. Drive the UI to trigger the behavior of interest.
4. Diff WS deltas to identify the new field code.

`script/_cooldown_capture.py` is a reusable template for driving HA + polling the diagnostics endpoint to find which field changes during a specific user action.

## 4. Architecture (this integration)

### Three-layer flow

```text
   HA UI / automation
        │
        ▼
   Entities (climate/sensor/binary_sensor)
        │  read coordinator.data
        │  write via coordinator.async_set_fields()
        ▼
   PentairPoolDataUpdateCoordinator
        │  REST poll fallback (60 s)
        │  WS push merge (real-time)
        │  optimistic local updates
        ▼
   PentairPoolApiClient + PentairPoolWebSocket
        │  Cognito SRP login (pycognito)
        │  GetId + GetCredentialsForIdentity → STS
        │  hand-rolled SigV4 (non-standard signed-headers list)
        │  long-lived WS with exp-backoff reconnect
        ▼
   Pentair Cloud
```

Entities **never** call the client directly — always through `coordinator.async_set_fields()`. The coordinator handles auth-expired retries, optimistic local state updates, and routing the resulting WS push back into per-entity updates.

### Data layout in `coordinator.data`

```python
{
    "<device_id>": {
        "device_info": {                       # top-level keys from listdevices
            "pname": "IntelliConnect",
            "deviceType": "PIF0",
            "arn": "arn:aws:iot:us-west-2:...",
            "devices": {                       # component map (heaters/sanitizers/Relay 1/etc.)
                ...
            },
            ...
        },
        "fields": {                            # field code → record
            "ra0": {"name": "Relay1_Manual_Schedule", "value": "2", "min": "0", "max": "4", ...},
            "ra4": {"name": "Relay1_Power", "value": "1392", ...},
            ...
        },
        "online":    True,
        "alarm":     False,
        "fwVersion": "1.0",
    }
}
```

WebSocket `device_data` pushes carry _deltas_ — only fields whose value changed are included. The coordinator merges these into `fields[code]` and calls `async_set_updated_data()`, which fans out to every listening entity.

### Pump on/off semantics — why is_on reads ra4

The pump's state machine uses a single `ra0` field that combines "Daily Schedule enabled" with "manual override on/off":

| `ra0` | Schedule | Override             | What the pump actually does                               |
| ----- | -------- | -------------------- | --------------------------------------------------------- |
| `"0"` | disabled | off                  | pump off                                                  |
| `"1"` | disabled | on                   | pump on (manual)                                          |
| `"2"` | enabled  | off                  | pump on **if currently inside schedule window**, else off |
| `"3"` | enabled  | on                   | pump on (manual override)                                 |
| `"4"` | enabled  | (timer just expired) | pump off (post-schedule)                                  |

So `ra0` is the user's _intent_, not physical state. A common real-world state is `ra0="2"` with the pump running because the Daily Schedule is firing. If the switch's `is_on` is computed from `ra0` alone, the switch shows OFF while the pump is on — confusing, and toggling it sends `ra0="2"` (a no-op) while the pump keeps running.

**Fix shipped:** `switch.filter_pump.is_on = (ra4 > 0)`. Reads physical truth. Writing still goes to `ra0` (intent). This also handles the heater-cooldown case transparently: during cooldown the firmware refuses to stop the pump, `ra4` stays > 0, switch stays ON — accurate.

Trade-off: when the user taps OFF while the schedule is firing, the switch doesn't immediately flip OFF (because the pump keeps running until the schedule ends). That's the truth, but it can confuse users who expect "switch toggle = pump command success." The fix for that UX confusion is the cooldown-active-style indicator described in pending item §2.1.

### UTC ↔ local time conversion

The schedule time entities (`time.daily_schedule_start`, `time.daily_schedule_end`) convert between Pentair's UTC-seconds-of-day storage and HA's local-time display using `hass.config.time_zone`. Today's date is used as the carrier so DST is applied correctly. Schedules repeat every day, so the choice of date doesn't matter as long as it's "today."

For one user with HA + the Pentair-side TZ matching (which is the normal case — the controller is at the user's home and they run HA there), display and behavior are consistent. If the two diverge, the schedule still fires at the right UTC instant but display may be off by the TZ delta.

### SigV4 quirk

Pentair's API Gateway expects a non-standard signed-headers list:

```text
SignedHeaders=host;iseuropeanuser;x-amz-date;x-amz-id-token;x-amz-security-token;x-pha-apptype
```

`iseuropeanuser` and `x-pha-apptype` are inside the signed set; `content-type` is **not**. boto3's `SigV4Auth` doesn't easily produce this exact set, so we hand-roll SigV4 in `api/client.py:_sigv4_headers()` — short enough (~50 lines) and gives full control.

### Cognito Identity response Content-Type

`cognito-identity.us-west-2.amazonaws.com` returns `Content-Type: application/x-amz-json-1.1`, which aiohttp rejects in `.json()` by default. Every `.json()` call on a Cognito Identity response uses `content_type=None` to bypass the MIME guard.

### get_device body shape

`POST /device2/device2-service/user/device` requires the body `{"deviceIds": [<id>]}` (plural key, list value). A singular `{"deviceId": id}` returns `200 OK` with `response.data: []` — the API silently swallows the wrong shape. Spent 30 minutes on this; doc'd loud here so we don't repeat.

## 5. File map

```text
homeassistant-pentair-intelliconnect/
├── custom_components/pentair_pool/
│   ├── __init__.py                            entry setup/unload
│   ├── manifest.json                          requires pycognito>=2024.5.1
│   ├── const.py                               domain, Cognito IDs, field codes, ra0/htd1 values
│   ├── data.py                                PentairPoolConfigEntry type alias
│   ├── diagnostics.py                         per-entry diagnostic dump
│   ├── repairs.py                             (unchanged blueprint stub; not wired)
│   ├── services.yaml                          reload_data service definition
│   │
│   ├── api/
│   │   ├── __init__.py                        public exports
│   │   └── client.py                          PentairPoolApiClient + PentairPoolWebSocket
│   │
│   ├── coordinator/
│   │   ├── __init__.py
│   │   └── base.py                            REST poll + WS merge + optimistic writes
│   │
│   ├── entity/
│   │   ├── __init__.py
│   │   └── base.py                            per-device DeviceInfo, field helpers
│   │
│   ├── config_flow.py                         (blueprint backwards-compat shim)
│   ├── config_flow_handler/                   (blueprint config flow — works as-is)
│   │
│   ├── climate/
│   │   ├── __init__.py
│   │   └── heater.py                          OFF/HEAT + tenths-of-°F setpoint
│   │
│   ├── sensor/
│   │   ├── __init__.py
│   │   ├── cooldown.py                        heater cooldown countdown (1 Hz local tick)
│   │   ├── pump.py                            VSF power/speed/program/timer (ifs*)
│   │   └── telemetry.py                       read-only field-backed sensors
│   │
│   ├── binary_sensor/
│   │   ├── __init__.py
│   │   ├── pump_enabled.py                    ifs1 enable state
│   │   ├── pump_running.py                    ifs4/ifs3 (fallback ra4)
│   │   ├── relay.py                           aux relays named from the manifest
│   │   └── status.py                          online + alarm
│   │
│   ├── service_actions/
│   │   └── __init__.py                        reload_data service handler
│   │
│   ├── translations/
│   │   └── en.json                            entity + config-flow strings
│   │
│   └── entity_utils/, utils/, config_flow_handler/options_flow.py
│       (blueprint extras, not load-bearing)
│
├── script/
│   ├── pentair_test                           HOST-SIDE bash wrapper (docker-exec dispatch)
│   ├── _pentair_test.py                       in-container Python driver
│   ├── _probe.py                              direct API client probe (uses HA venv)
│   ├── _cooldown_capture.py                   polling diff capture template
│   ├── _field_diff.py                         read-only REST field-diff capture
│   ├── _mitm_pentair_log.py                   mitmproxy addon for app-traffic capture
│   ├── develop, setup/, check, lint, test...  blueprint scripts
│   │
└── docs/
    ├── development/   blueprint general guidance (kept as-is)
    ├── user/          blueprint general guidance (kept as-is)
    └── pentair/       THIS PROJECT'S NOTES (you are reading STATUS.md)
```

## 6. Captured artifacts (for resuming the reverse-engineering)

Lives in the sibling `work/` directory:

```text
work/
├── docs/
│   ├── REPRODUCE.md                end-to-end: stock APK → live mitmproxy capture
│   ├── SECRETS.md                  Cognito IDs, API keys, pool IDs (low-value, in-APK anyway)
│   └── ENDPOINTS.md                ⭐ full API reference + field-code spec + verified command catalogue
├── capture-2-full-email.log        clean detectUser capture (userExists:true)
├── capture-3-authenticated.log     post-sign-in: tokens, STS, device list, WS URL
├── flows-dashboard-idle.mitm       (5.7 MB) 61 idle WS messages
├── flows-pump-on-off.mitm          pump tile ON → OFF
├── flows-pump-schedule.mitm        schedule enable/disable + edit
├── flows-pump-schedule-heater.mitm heater on/off + setpoint
├── flows-salt-cell.mitm            chlorine % + boost set/cancel
└── ws-frames-*.jsonl               live-streamed WS frames per session
```

If you need to verify a captured PUT body / WS field schema while debugging:

```bash
# Replay a .mitm file interactively
mitmweb --rfile work/flows-pump-on-off.mitm

# Or grep the ws-frames JSONL
jq -c 'select(.from_client==false) | .content | fromjson | .data.fields' \
   work/ws-frames-pump.jsonl | less
```

## 7. Where to pick up

Most impactful next things, in rough priority order:

0. **Capture the IntelliFlo program start/stop command** with mitmproxy while the Mac and iPhone share Wi-Fi, then add per-program start buttons and a stop button. Procedure and findings: [`../intelliconnect-program-control.md`](../intelliconnect-program-control.md).
1. **Re-run the cooldown capture under correct conditions.** The current `script/_cooldown_capture.py` template polls diagnostics every 1.5 s and diffs field-by-field. Just needs to be invoked when the heater is actually heating (htd1==1) and the schedule isn't masking the effect. Goal: identify the live cooldown field, then add `binary_sensor.cooldown_active` and `cooldown_remaining` (in seconds).
2. **Expose the salt-cell boost as a control.** Either button+number pair, or service `pentair_pool.start_boost`. Field codes already known (icd2 + icd3).
3. ~~**Water/Air temperature sensors.**~~ Done (`t0`, `t1`).
4. **Test token refresh.** Leave HA running for 90 minutes (past the 1-hour token expiry) and confirm the WS reconnect + REST calls keep working.
5. **Decode `ics3` alarm code.** The `binary_sensor.intelliconnect_alarm` keeps reading ON; need to find the lookup table (probably in the JS bundle's `IC1.Errors.*` translation keys).
6. **`htd1` mode values 2 and 4.** We've only observed 0/1/3. The bundle's `HeaterModes` map names them (`AutoHeating`, `ScheduleRunning`, `Timer`, etc.) but the numeric mapping isn't pinned. Could surface via a longer real-world capture.
7. **Generalize beyond PIF0.** Add a per-deviceType platform gating layer so IntelliCenter (`ICT1`), IntelliFlo (`IF31`), ChemCheck (`WQM1`), etc. can plug in their own field-code sets without breaking existing PIF0 users.
