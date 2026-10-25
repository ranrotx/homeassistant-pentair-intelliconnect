"""Constants for pentair_pool.

Values reverse-engineered from com.pentair.pentairhome v4.2.18; see
the ENDPOINTS.md document in the development notes for the source
captures and rationale for each constant.
"""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

# Integration metadata
DOMAIN = "pentair_pool"
ATTRIBUTION = "Data provided by Pentair Cloud"

# Platform parallel updates - applied to all platforms.
# Writes are serialized so a rapid double-tap of a switch can't reorder.
PARALLEL_UPDATES = 1

# Default polling cadence (seconds). The WebSocket pushes carry most state
# changes within a second; this is the fallback for missed pushes.
DEFAULT_POLL_INTERVAL_SECONDS = 60

# Option: pump program (1-4) the heater starts when it needs flow and the pump
# on its controller is stopped. "0" (the default) leaves the pump alone.
CONF_HEATING_PUMP_PROGRAM = "heating_pump_program"
HEATING_PUMP_PROGRAM_NONE = "0"

# Legacy options-flow defaults (kept so the blueprint's options_flow imports
# still resolve). Not yet wired to anything functional.
DEFAULT_UPDATE_INTERVAL_HOURS = 1
DEFAULT_ENABLE_DEBUGGING = False

# --- Cognito (US pool) --------------------------------------------------------
COGNITO_REGION = "us-west-2"
COGNITO_USER_POOL_ID = "us-west-2_lbiduhSwD"
COGNITO_CLIENT_ID = "3de110o697faq7avdchtf07h4v"
IDENTITY_POOL_ID = "us-west-2:6f950f85-af44-43d9-b690-a431f753e9aa"

# EU pool (discovered in decompile; not yet exercised).
COGNITO_REGION_EU = "eu-west-1"
COGNITO_USER_POOL_ID_EU = "eu-west-1_rsBGJFuRd"

# --- Pentair Cloud API --------------------------------------------------------
API_HOST = "api.pentair.cloud"
API_BASE = f"https://{API_HOST}"
API_KEY_UNAUTH = "p4u60la7xH7q4aat3Tzrq9BfspTOslIs6oXzIhuS"
DETECT_USER_URL = f"{API_BASE}/user2/user2-service/unauth/detectUser"

# --- Real-time WebSocket ------------------------------------------------------
WS_URL = "wss://g44t970cbi.execute-api.us-west-2.amazonaws.com/prod"

# --- Token refresh safety margin (seconds) -----------------------------------
TOKEN_REFRESH_MARGIN_SECONDS = 60

# --- IntelliConnect (PIF0) field codes ---------------------------------------
# Relay 1 and Relay 2 are generic aux relays; the installed accessory varies by
# controller (on the captured account Relay 1 = Pentair Color Light, Relay 2 =
# Blower -- see the listdevices `devices` manifest). Both relays share the same
# field layout: raN/rbN. Relay state/power push only over REST (not the WS), so
# relay entities refresh on the REST poll.
FIELD_RA0 = "ra0"  # Relay1_Manual_Schedule (on/off + schedule mode)
FIELD_RA1 = "ra1"  # Relay1_Start_Time (UTC seconds-of-day)
FIELD_RA2 = "ra2"  # Relay1_End_Time
FIELD_RA3 = "ra3"  # Relay1_Timer (configured timer duration, seconds)
FIELD_RA4 = "ra4"  # Relay1_Power (watts, RO)
FIELD_RA5 = "ra5"  # Relay1_Product_ID (7-9 = color lights)
FIELD_RA8 = "ra8"  # Relay1_ColorLight_Mode (0-18; color/theme index when a light)
FIELD_RA9 = "ra9"  # second schedule start (read by the app; not reported by all firmware)
FIELD_RA10 = "ra10"  # second schedule stop
FIELD_RAS0 = "ras0"  # Relay1_Timer_Status (live pump-stop countdown, RO seconds)
FIELD_RB0 = "rb0"  # Relay2_Manual_Schedule (on/off + schedule mode)
FIELD_RB1 = "rb1"  # Relay2_Start_Time (UTC seconds-of-day)
FIELD_RB2 = "rb2"  # Relay2_Stop_Time
FIELD_RB3 = "rb3"  # Relay2_Timer
FIELD_RB4 = "rb4"  # Relay2_Power (watts, RO)
FIELD_RB5 = "rb5"  # Relay2_Product_ID
FIELD_RB8 = "rb8"  # Relay2_ColorLight_Mode (0-18; color/theme index when a light)
FIELD_RB9 = "rb9"  # second schedule start
FIELD_RB10 = "rb10"  # second schedule stop
FIELD_RBS0 = "rbs0"  # Relay2_Timer_Status (live stop countdown, RO seconds)
FIELD_P1 = "p1"  # Relay1_Egg_Timer (seconds; the app writes it together with ra3)
FIELD_P2 = "p2"  # Relay2_Egg_Timer (seconds; written together with rb3)
FIELD_HTD1 = "htd1"  # Heater_Mode
FIELD_HTD2 = "htd2"  # Heater_SetPoint (tenths of degF)
FIELD_HTD13 = "htd13"  # Heater_EggTimer (run duration, seconds; 0 clears it)
FIELD_HTD14 = "htd14"  # Heater_Cooldown (seconds, RO)
FIELD_HTS2 = "hts2"  # HeaterEggTimerStatus (seconds remaining, RO)
FIELD_ECS1 = "ecs1"  # Device service mode (0 = normal; the app blocks heater writes otherwise)
FIELD_ICD1 = "icd1"  # Chlor_Set_Percentage (set in the Pentair app; not written by this integration)
FIELD_ICD2 = "icd2"  # Boost_Mode_RPM (one-shot)
FIELD_ICD3 = "icd3"  # Boost_Mode_Timer (one-shot, seconds)
FIELD_ICS1 = "ics1"  # Chlor_Percentage (actual, RO)
FIELD_ICS2 = "ics2"  # Chlor_Salt_Value_PPM (RO)
FIELD_ICS3 = "ics3"  # Chlor_Error_Message (RO)
FIELD_ICS9 = "ics9"  # Chlor_Status_Call_Temp (RO)
FIELD_ICS11 = "ics11"  # Chlor_Status_Call_VerNum (RO)
FIELD_ICS12 = "ics12"  # Chlor_Device_Name (RO)
FIELD_ICS13 = "ics13"  # Chlor_BoostTimer_Status (countdown, RO)
FIELD_ICS15 = "ics15"  # Chlor_Operation_Hours (RO)

# --- IntelliFlo VSF pump status (ifs*) ---------------------------------------
# Reverse-engineered from a live two-controller capture on 2026-07-03 (see
# docs/intelliconnect-phase1-capture.md). A variable-speed IntelliFlo (VSF)
# pump -- the Feature Control fountain AND the Main Control pump -- reports its
# real-time speed/power/timer through these fields, NOT through ra*/ras0. The
# ra* relay fields are present in the REST snapshot but NEVER push over the
# WebSocket for a VSF pump, so ifs* is the only real-time source.
FIELD_IFS1 = "ifs1"  # Running_Stopped -> pump enable state (10=enabled, 4=disabled)
FIELD_IFS2 = "ifs2"  # Active_Menu (0=off, N=program N running, 17=priming)
FIELD_IFS3 = "ifs3"  # Actual_Power (watts, RO)
FIELD_IFS4 = "ifs4"  # Actual_Speed_Status (RPM, RO)
FIELD_IFS18 = "ifs18"  # Alarm (0 = none)
FIELD_IFS27 = "ifs27"  # Duration -> egg-timer remaining (minutes, RO while a timed run is active)

# ifs1 (Running_Stopped) values. Confirmed live 2026-07-04 by enabling/disabling
# the fountain: the field holds 10 in every enabled state (idle, priming, or
# running) and 4 when the pump feature is disabled at the controller. The app's
# Stop button disables the pump this way too (c1 = C1_STOP, verified 2026-10-25).
IFS1_ENABLED = "10"
IFS1_DISABLED = "4"

# ifs18 (Alarm) values the Pentair app refuses to send pump commands in.
IFS18_COMMAND_BLOCKED = frozenset({"16384", "128", "16512", "8192", "-1"})

# --- IntelliFlo pump commands (c1) --------------------------------------------
# `c1` (the app's "selectSpeed") is a write-only command field: it never appears
# in the REST snapshot. Decoded from the Android app (v4.2.21, startStopProgram)
# and verified live on 2026-10-25: "1"-"4" run that program, "6" stops the pump
# (ifs1 -> 4), "5" re-enables it so its schedules run again (the app's pump
# on/off toggle sends "6" and "5").
FIELD_C1 = "c1"
C1_STOP = "6"
C1_RESUME_SCHEDULES = "5"

# Per-program Operation_Mode fields (ifd0-ifd3, one per app "Program 1-4").
# The app never sends a Run command for a SCHEDULE program; it hands control
# back to the schedules instead.
FIELD_PROGRAM_MODES = ("ifd0", "ifd1", "ifd2", "ifd3")
PROGRAM_MODE_SCHEDULE = "2"

# ifs2 (Active_Menu) values. Confirmed live 2026-10-25 by starting/stopping
# programs from the app: 0 while stopped, 17 while priming, then the number of
# the running program (Program 2 -> 2, Program 3 -> 3).
IFS2_OFF = "0"
IFS2_PRIMING = "17"

# Program display names (cloud fields), one per app "Program 1-4" slot. Each
# program's settings live in the ifd* SpeedN_* config fields (mode, RPM, egg-timer
# minutes); those are edited in the Pentair app, not by this integration.
FIELD_PROGRAM_NAMES = ("p5", "p6", "p7", "p8")

# Temperature sensors (whole degrees F, NOT tenths like htd2)
FIELD_T0 = "t0"  # Current_Water_Temp (RO, degF integer)
FIELD_T1 = "t1"  # FP_Outside_Temp (RO, degF integer, S16 so signed)

# --- RelayN_Manual_Schedule (ra0/rb0) values ---------------------------------
# Decoded from the Android app's getPayloadOnRelay (v4.2.21). With no schedule
# the relay is plainly off (0) or on (1). With a schedule it follows it (2),
# is held on (3), or is held off during a running schedule window (4).
RELAY_OFF = "0"
RELAY_ON = "1"
RELAY_FOLLOW_SCHEDULE = "2"
RELAY_ON_OVERRIDE = "3"
RELAY_OFF_OVERRIDE = "4"

# Schedule start/stop fields hold UTC seconds-of-day; any larger value (the app
# writes 100000) means that schedule is disabled.
RELAY_SCHEDULE_MAX = 86399

# Relay product IDs the app treats as color lights.
RELAY_COLOR_LIGHT_PRODUCTS = frozenset({"7", "8", "9"})

# Relay power (W) above which the accessory itself is running. A blower relay
# reads about 10 W while the controller ramps the pump up before starting the
# blower, and about 720 W once the blower runs (measured 2026-10-25).
RELAY_RUNNING_MIN_WATTS = 50

# Relay egg-timer durations offered in HA (minutes), and the default when
# neither HA nor the controller has one yet.
RELAY_TIMER_MIN_MINUTES = 1
RELAY_TIMER_MAX_MINUTES = 1440
RELAY_TIMER_DEFAULT_MINUTES = 10

# --- htd1 values --------------------------------------------------------------
# Empirically confirmed by cross-referencing the Pentair Home app's UI:
#   htd1=1 -> app shows "Auto Idle"  (heater enabled, monitoring, NOT firing)
#   htd1=3 -> app shows "Heating"    (heater actively firing)
# Earlier code had these swapped. Mode 1 is also what we WRITE to turn the
# heater on, because that puts it in auto monitoring; the firmware itself
# transitions 1->3 when it decides to fire (water below setpoint AND pump
# flow available). The Android app (v4.2.21, getHeaterData) treats 2 like 1
# and 4 like 3: 2 = on under a timer or schedule but not firing, 4 = firing
# under a timer or schedule. Both are firmware-managed.
HTD1_OFF = "0"
HTD1_AUTO_IDLE = "1"
HTD1_TIMER_IDLE = "2"
HTD1_HEATING = "3"
HTD1_TIMER_HEATING = "4"
HTD1_HEATING_MODES = frozenset({HTD1_HEATING, HTD1_TIMER_HEATING})

HTD1_LABELS = {
    "0": "Off",
    "1": "Auto idle",
    "2": "Timer or schedule idle",
    "3": "Heating",
    "4": "Timer or schedule heating",
}

# --- Heater egg timer ---------------------------------------------------------
# Decoded from the Android app (IC1_HeaterTimer addTimer): the app writes the
# run length to htd13 in seconds and, only if the heater is off, htd1=1 in the
# same PUT. hts2 then reports the seconds left. Turning the heater off writes
# htd13=0, which also cancels the timer. 2592000 s (30 days) is the field's max.
HEATER_TIMER_MIN_SECONDS = 60
HEATER_TIMER_MAX_SECONDS = 2592000

# --- Salt cell boost ---------------------------------------------------------
BOOST_RPM = "450"
