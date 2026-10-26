"""Aux-relay (Relay 1 / Relay 2) state and on/off command logic.

Both relays share one field layout (``ra*`` / ``rb*``). The on/off state lives
in the ``RelayN_Manual_Schedule`` field, whose values depend on whether the
relay has a schedule (see ``RELAY_*`` in ``const.py``). This module mirrors the
Pentair Android app (v4.2.21): ``getRunningStatus`` decides whether a schedule
window is running, and ``getPayloadOnRelay`` builds the write for an on/off
press. Times are compared as UTC seconds-of-day, which matches the app's
comparison in the controller's time zone because a fixed offset doesn't change
whether a time falls inside a (possibly overnight) window.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from custom_components.pentair_pool.const import (
    FIELD_P1,
    FIELD_P2,
    FIELD_RA0,
    FIELD_RA1,
    FIELD_RA2,
    FIELD_RA3,
    FIELD_RA4,
    FIELD_RA5,
    FIELD_RA8,
    FIELD_RA9,
    FIELD_RA10,
    FIELD_RAS0,
    FIELD_RB0,
    FIELD_RB1,
    FIELD_RB2,
    FIELD_RB3,
    FIELD_RB4,
    FIELD_RB5,
    FIELD_RB8,
    FIELD_RB9,
    FIELD_RB10,
    FIELD_RBS0,
    RELAY_COLOR_LIGHT_PRODUCTS,
    RELAY_FOLLOW_SCHEDULE,
    RELAY_OFF,
    RELAY_OFF_OVERRIDE,
    RELAY_ON,
    RELAY_ON_OVERRIDE,
    RELAY_SCHEDULE_MAX,
    RELAY_TIMER_DEFAULT_MINUTES,
    RELAY_TIMER_MAX_MINUTES,
    RELAY_TIMER_MIN_MINUTES,
)
from custom_components.pentair_pool.entity_utils.capabilities import (
    CAP_RELAY1,
    CAP_RELAY2,
    capability_present,
    manifest_entry,
)

FieldValues = dict[str, str | None]


@dataclass(frozen=True, kw_only=True)
class RelayFields:
    """Field codes for one aux relay."""

    key: str  # entity description key
    manifest_key: str  # listdevices manifest entry naming the accessory
    state: str
    schedules: tuple[tuple[str, str], ...]  # (start, stop) pairs
    timer: str  # RelayN_Timer (seconds)
    egg_timer: str  # RelayN_Egg_Timer, written with `timer` to start a timed run
    timer_status: str  # seconds left in a timed run
    power: str
    product_id: str
    color_mode: str

    @property
    def codes(self) -> tuple[str, ...]:
        """Every field this module reads."""
        flat = [code for pair in self.schedules for code in pair]
        return (self.state, *flat, self.timer, self.timer_status, self.power, self.product_id, self.color_mode)


RELAYS = (
    RelayFields(
        key="relay_1",
        manifest_key=CAP_RELAY1,
        state=FIELD_RA0,
        schedules=((FIELD_RA1, FIELD_RA2), (FIELD_RA9, FIELD_RA10)),
        timer=FIELD_RA3,
        egg_timer=FIELD_P1,
        timer_status=FIELD_RAS0,
        power=FIELD_RA4,
        product_id=FIELD_RA5,
        color_mode=FIELD_RA8,
    ),
    RelayFields(
        key="relay_2",
        manifest_key=CAP_RELAY2,
        state=FIELD_RB0,
        schedules=((FIELD_RB1, FIELD_RB2), (FIELD_RB9, FIELD_RB10)),
        timer=FIELD_RB3,
        egg_timer=FIELD_P2,
        timer_status=FIELD_RBS0,
        power=FIELD_RB4,
        product_id=FIELD_RB5,
        color_mode=FIELD_RB8,
    ),
)


def installed_relays(dev: dict[str, Any], *, lighting: bool) -> list[RelayFields]:
    """Relays the device reports and lists as installed, lights or non-lights.

    A light is a manifest entry of type ``lighting``. Without a manifest,
    every reported relay counts as a non-light.
    """
    fields = dev.get("fields") or {}
    return [
        relay
        for relay in RELAYS
        if relay.state in fields
        and capability_present(dev, relay.manifest_key)
        and (manifest_entry(dev, relay.manifest_key).get("type") == "lighting") == lighting
    ]


def _int(value: str | None) -> int | None:
    try:
        return int(value) if value is not None else None
    except ValueError:
        return None


def _schedule_enabled(start: int | None) -> bool:
    return start is not None and start <= RELAY_SCHEDULE_MAX


def has_schedule(relay: RelayFields, values: FieldValues) -> bool:
    """True if the relay is in schedule mode (a schedule is set and state > 1)."""
    if not any(_schedule_enabled(_int(values.get(start))) for start, _ in relay.schedules):
        return False
    state = _int(values.get(relay.state))
    return state is not None and state > 1


def _in_window(start: int, stop: int, now: int) -> bool:
    """Whether `now` falls in [start, stop], all UTC seconds-of-day.

    Like the app, start and stop are compared at minute resolution, and a stop
    before the start is an overnight window.
    """
    start -= start % 60
    stop -= stop % 60
    if stop > start:
        return start <= now <= stop
    if stop < start:
        return now >= start or now <= stop
    return True


def in_schedule_window(relay: RelayFields, values: FieldValues, now: datetime) -> bool:
    """True if `now` falls inside one of the relay's schedule windows.

    Unlike the app, a start or stop of 0 is midnight UTC (e.g. 7 PM CDT), not
    an unset time; the controller runs such a window. Only 0-0 counts as unset.
    """
    seconds = now.hour * 3600 + now.minute * 60 + now.second
    for start_code, stop_code in relay.schedules:
        start, stop = _int(values.get(start_code)), _int(values.get(stop_code))
        if start is None or stop is None or not _schedule_enabled(start) or not (start or stop):
            continue
        if _in_window(start, stop, seconds):
            return True
    return False


def running_by_schedule(relay: RelayFields, values: FieldValues, now: datetime) -> bool:
    """True if the relay follows its schedule and a window is running (app: getRunningStatus)."""
    if values.get(relay.state) != RELAY_FOLLOW_SCHEDULE:
        return False
    if (_int(values.get(relay.timer_status)) or 0) > 0:
        return False
    return in_schedule_window(relay, values, now)


def relay_is_on(relay: RelayFields, values: FieldValues, now: datetime) -> bool | None:
    """Derived on/off; falls back to power draw for an unknown state value."""
    state = values.get(relay.state)
    if (_int(values.get(relay.timer_status)) or 0) > 0:
        return True
    if state in (RELAY_ON, RELAY_ON_OVERRIDE):
        return True
    if state in (RELAY_OFF, RELAY_OFF_OVERRIDE):
        return False
    if state == RELAY_FOLLOW_SCHEDULE:
        return running_by_schedule(relay, values, now)
    power = _int(values.get(relay.power))
    return None if power is None else power > 0


def relay_payload(relay: RelayFields, values: FieldValues, *, turn_on: bool, now: datetime) -> dict[str, str]:
    """Fields to write for an on/off press (app: getPayloadOnRelay)."""
    scheduled = has_schedule(relay, values)
    payload: dict[str, str] = {}
    if turn_on:
        # The app re-sends a color light's mode when it is 0.
        if values.get(relay.product_id) in RELAY_COLOR_LIGHT_PRODUCTS and values.get(relay.color_mode) == "0":
            payload[relay.color_mode] = "0"
        if not scheduled:
            payload[relay.state] = RELAY_ON
        elif values.get(relay.state) == RELAY_OFF_OVERRIDE:
            payload[relay.state] = RELAY_FOLLOW_SCHEDULE
        else:
            payload[relay.state] = RELAY_ON_OVERRIDE
        return payload
    # The app holds the relay off only when it is in state 2 inside a window,
    # so from an on override (3) it writes 2 and the running window keeps the
    # relay on. Hold it off whenever a window is running instead.
    if not scheduled:
        payload[relay.state] = RELAY_OFF
    elif in_schedule_window(relay, values, now):
        payload[relay.state] = RELAY_OFF_OVERRIDE
    else:
        payload[relay.state] = RELAY_FOLLOW_SCHEDULE
    # Turning off also cancels a running relay timer.
    if (_int(values.get(relay.timer_status)) or 0) > 0:
        payload[relay.timer] = "0"
    return payload


def timer_default_minutes(relay: RelayFields, values: FieldValues) -> int:
    """Last timer duration the controller ran (`RelayN_Timer`), else the default."""
    seconds = _int(values.get(relay.timer)) or 0
    minutes = round(seconds / 60)
    if RELAY_TIMER_MIN_MINUTES <= minutes <= RELAY_TIMER_MAX_MINUTES:
        return minutes
    return RELAY_TIMER_DEFAULT_MINUTES


def timer_payload(relay: RelayFields, values: FieldValues, minutes: int) -> dict[str, str]:
    """Fields that start a timed run (app: saveTimer).

    Writing the duration to both timer fields starts the relay. The app adds
    one second when the duration equals the stored one, so the write is a
    change the controller acts on.
    """
    seconds = minutes * 60
    if _int(values.get(relay.timer)) == seconds:
        seconds += 1
    return {relay.timer: str(seconds), relay.egg_timer: str(seconds)}
