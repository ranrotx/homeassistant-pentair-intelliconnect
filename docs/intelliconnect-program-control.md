# IntelliFlo Program Control — Findings

**Status (2026-10-25):** done. The start/stop command is the write-only field `c1` (§4), verified live on the fountain. The integration exposes it as pump buttons.

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

## 4. The command: `c1`

A mitmproxy capture of the iPhone app failed: the phone trusted the proxy (Safari loaded `api.pentair.cloud` through it), but the app aborts the TLS handshake, so it pins certificates. The command came instead from the Android app (`com.pentair.pentairhome` 4.2.21). Its React Native bundle is Hermes bytecode v96, which [hermes-dec](https://github.com/P1sec/hermes-dec) decompiles. The IntelliFlo screen's `startStopProgram` writes the field the app calls `selectSpeed`, which is `c1`:

| `c1` | App action                                        | Effect                                                 |
| ---- | ------------------------------------------------- | ------------------------------------------------------ |
| 1–4  | Run Now on Program N                              | primes, then runs Program N with its app settings      |
| `6`  | Stop, and the pump on/off toggle's off            | stops; `ifs1` → 4, pump stays disabled, schedules idle |
| `5`  | the pump on/off toggle's on (`activateSchedules`) | re-enables the pump so its schedules run again         |

It goes through the same `PUT /device/device-service/user/device/<id>` with `{"payload": {"c1": "<value>"}}` as any other write. `c1` never appears in the REST snapshot, which is why §2 saw no field change. The app also:

- sends no Run for a program whose mode is schedule (`ifd*` = 2); it sends `6`, then `5` after one polling interval;
- refuses every command while `ifs18` (`Alarm`) is 16384, 128, 16512, 8192 or −1.

Live test on the fountain controller (Program 1: egg timer, 900 RPM, 61 min), 2026-10-25:

```text
18:15:12 PUT c1=1 -> set_device_success
18:15:16 ifs2=17 (priming)
18:15:25 ifs2=1  ifs4=900 ifs3=62 ifs27=61
18:15:44 PUT c1=6 -> set_device_success
18:15:48 ifs1=4  ifs2=0  ifs4=0  ifs27=0
```

## 5. In the integration

`button/pump_command.py` adds, for each device reporting `ifs2`: **Run _program name_** for each program slot (`ifd0`–`ifd3`), **Stop pump** (`6`) and **Resume pump schedules** (`5`). Presses follow the app's alarm and schedule-mode rules. Program settings stay in the Pentair app.
