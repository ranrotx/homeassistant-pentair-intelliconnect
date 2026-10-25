# IntelliFlo Program Control — Findings and Capture Plan

**Status (2026-10-25):** read side done, start/stop command not yet found. Next step is a capture of the Pentair Pool iPhone app's traffic with mitmproxy, done while the Mac and the iPhone are on the same Wi-Fi network.

**Goal:** Home Assistant "presses" the start and stop buttons of the pump's four programs (the app's Program 1–4 cards). Program settings (speed, mode, egg-timer duration, schedule) stay in the Pentair app. The integration does not edit them.

## 1. Where the programs live

Captured on the Main Control controller (IntelliFlo VSF) through the REST `device` snapshot. The cloud names every field. The app's **Program N** is the firmware's **SpeedN**, and N−1 is the index in the table below.

| Field                    | Name                       | Meaning                                                         |
| ------------------------ | -------------------------- | --------------------------------------------------------------- |
| `ifd0`–`ifd3`            | `SpeedN_Operation_Mode`    | 0 = manual, 1 = egg timer, 2 = schedule                         |
| `ifd4`–`ifd7`            | `SpeedN_Set_Speed`         | RPM (450–3450)                                                  |
| `ifd8`–`ifd11`           | `SpeedN_Start_Time`        | minute of day (0–1439)                                          |
| `ifd12`–`ifd15`          | `SpeedN_Stop_Time`         | minute of day (0–1439)                                          |
| `ifd16`–`ifd19`          | `SpeedN_EggTimer_Duration` | minutes (−1–600)                                                |
| `ifd22`–`ifd25`          | `SpeedN_Set_Type`          | 0–1 (all 1 here; meaning unknown)                               |
| `p5`–`p8`                | `Program 1`–`Program 4`    | program display names (cloud fields)                            |
| `ifd29`–`ifd32`          | `Program1-4_Set_Speed`     | do **not** match the speeds the app shows; ignore               |
| `ifd20`, `ifd21`         | —                          | missing from the snapshot (gap in the numbering)                |
| `ifs2`                   | `Active_Menu`              | 0 = stopped, 17 = priming, N = program N running                |
| `ifs27`                  | `Duration`                 | egg-timer minutes remaining while a program runs (0 for manual) |
| `ifs1`                   | `Running_Stopped`          | 10 = enabled, 4 = stopped/disabled (the app's stop sets 4)      |
| `ifs4` / `ifs3` / `ifs6` | speed / power / flow       | live RPM, W, flow                                               |

The mode meanings match the pump's own behavior: programs 1–4 run as manual, egg timer, or schedule, and programs 5–8 are schedule-only. They were confirmed against the app: Program 2 is set to manual (0), and the user started it as a manual run.

The integration now exposes the read side as `sensor.<device>_pump_program` and `sensor.<device>_pump_timer_remaining`, in minutes.

## 2. What a start and a stop look like

From a 4-second REST diff (`script/_field_diff.py`) while the user drove the app:

```text
16:09:06 ifs1  '10' -> '4'     # Stop pressed
16:09:06 ifs2  '2'  -> '0'
16:09:37 ifs1  '4'  -> '10'    # Program 2 started
16:09:37 ifs2  '0'  -> '17'    # priming, ~35 s at 1800-2600 RPM
16:10:12 ifs2  '17' -> '2'     # Program 2 running at its 1200 RPM
16:13:39 ifs2  '17' -> '3'     # Program 3 (egg timer) running
16:13:39 ifs27 '11' -> '60'    # 60-minute egg timer
```

**No config or cloud field changes on start or stop.** The app's command is transient. It is either written to a field the snapshot doesn't list, or sent to a different endpoint or over a different channel. Editing a program's duration in the app, by contrast, shows up at once (`ifd19` 120 → 90 → 120).

## 3. Write probes already tried (user-approved, all reverted)

Every probe was a `PUT /device/device-service/user/device/<id>` with `{"payload": {...}}`.

| Payload              | Cloud response                                 | Pump                   |
| -------------------- | ---------------------------------------------- | ---------------------- |
| `ifd19=120`, `=90`   | `set_device_success`, visible in REST in ~10 s | settings write works   |
| `ifs2=4`             | `set_device_error_no_attribute_to_update`      | nothing                |
| `ifs1=10, ifs2=4`    | `set_device_error_no_attribute_to_update`      | nothing                |
| `ifd3=1` (unchanged) | `set_device_success`                           | did not start          |
| `dr0=60`             | `set_device_success`, stored and kept          | did not start; reset 0 |

The cloud checks field codes: it rejects status fields and codes it doesn't know. `dr0`–`dr2` (`Type1_DR`–`Type3_DR`, −2–43200) behave like a stored setting, probably demand response, not a run command.

## 4. Capture procedure (same Wi-Fi network)

An attempt over the iPhone's Personal Hotspot failed. The Mac only gets a T-Mobile IPv6 address there, and packets from the iPhone to that address never arrive. A WireGuard tunnel showed bytes sent and none received. The app is also not installable on Apple Silicon Macs.

1. On the Mac, from the repo root:

   ```bash
   uvx --from mitmproxy mitmdump -s script/_mitm_pentair_log.py \
       --allow-hosts 'pentair|execute-api|\.iot\.|mitm\.it'
   ```

   Only Pentair and AWS API hosts are decrypted. Tokens, passwords and auth headers are redacted in `script/_mitm_pentair_log.log`, which git ignores.

2. Find the Mac's Wi-Fi address: `ipconfig getifaddr en0`.
3. On the iPhone, go to Settings › Wi-Fi › (network) › Configure Proxy › Manual. Enter the Mac's address, port `8080`.
4. In Safari, open `http://mitm.it`, download the iOS certificate, and install it under Settings › General › VPN & Device Management. Then turn on full trust under Settings › General › About › Certificate Trust Settings.
5. Start `script/_field_diff.py <device_id>` in the devcontainer as a cross-check.
6. Force-quit and reopen the Pentair Pool app. Press **start** on one program, wait about 30 s, then press **stop**. Note the times.
7. Read the log for the request sent at the moment of each press: method, URL, body, and any WebSocket frame.

If the log shows `TLS-FAIL` for Pentair hosts, the app is rejecting the certificate, either because it isn't trusted or because the app pins certificates. Fallbacks are an Android emulator with a system CA, or asking the upstream maintainer. Upstream `docs/pentair/STATUS.md` describes an `ENDPOINTS.md` "verified command catalogue" kept in a separate research workspace.

**Cleanup afterwards:** turn off the iPhone's Wi-Fi proxy, remove the mitmproxy profile (Settings › General › VPN & Device Management), and stop mitmdump. Anyone holding the mitmproxy CA key in `~/.mitmproxy` can read the phone's encrypted traffic while that profile stays trusted.

## 5. After the capture

- Add one `button` per program ("Start _program name_", named from `p5`–`p8`), plus a "Stop pump" button. Gate them on the IntelliFlo manifest entry and on the `ifs2` field.
- Keep writes serialized (`PARALLEL_UPDATES = 1`). Verify each press through `ifs2` (priming, then N) and `ifs1`.
- Remove the temporary WebSocket debug logging in `api/client.py` (`_handle_text`) once no more field captures are needed.
