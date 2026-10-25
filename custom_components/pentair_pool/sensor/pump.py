"""IntelliFlo VSF pump sensors (power, speed, active program, egg-timer remaining).

A variable-speed IntelliFlo pump reports its live state through the `ifs*`
field family, captured from a two-controller account on 2026-07-03 (see
`docs/intelliconnect-phase1-capture.md`):

  - `ifs4` = pump speed (RPM):   0 stopped, ~900 steady run, ~1800 priming
  - `ifs3` = pump power (watts):  scales ~cubically with RPM
  - `ifs27` = egg-timer remaining (minutes): counts down once a minute while a
              timed run is active; the pump stops the moment it reaches 0
  - `ifs2`  = active program: 0 stopped, 17 priming, N while Program N runs

Unlike the relay fields (`ra*`), these push over the WebSocket in real time,
so they are the authoritative source for both the Feature Control fountain and
the Main Control pump. The power sensor keeps the historical
`filter_pump_power` key and falls back to the relay power `ra4` so relay-only
pumps (and the entity's history) keep working.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.pentair_pool.const import (
    FIELD_IFS2,
    FIELD_IFS3,
    FIELD_IFS4,
    FIELD_IFS27,
    FIELD_PROGRAM_NAMES,
    FIELD_RA4,
    IFS2_OFF,
    IFS2_PRIMING,
)
from custom_components.pentair_pool.entity import PentairPoolEntity
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.const import REVOLUTIONS_PER_MINUTE, EntityCategory, UnitOfPower, UnitOfTime

if TYPE_CHECKING:
    from custom_components.pentair_pool.coordinator import PentairPoolDataUpdateCoordinator

# Power source preference: real-time IntelliFlo watts first, relay power last.
_POWER_FIELDS = (FIELD_IFS3, FIELD_RA4)

# The pump firmware numbers its programs 1-8 (5-8 are schedule-only).
_PROGRAM_NUMBERS = range(1, 9)


def _first_int(entity: PentairPoolEntity, codes: tuple[str, ...]) -> int | None:
    """Return the first parseable int among the given field codes."""
    for code in codes:
        v = entity.field_value(code)
        if v is None:
            continue
        try:
            return int(v)
        except ValueError:
            continue
    return None


def _active_program(entity: PentairPoolEntity) -> int | None:
    """Number of the program the pump is running (`ifs2`), or None if none is."""
    menu = _first_int(entity, (FIELD_IFS2,))
    return menu if menu in _PROGRAM_NUMBERS else None


class PentairPoolPumpPowerSensor(SensorEntity, PentairPoolEntity):
    """Pump power (W). Prefers real-time `ifs3`, falls back to relay `ra4`."""

    def __init__(
        self,
        coordinator: PentairPoolDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Bind to one device."""
        super().__init__(
            coordinator,
            SensorEntityDescription(
                key="filter_pump_power",
                translation_key="filter_pump_power",
                device_class=SensorDeviceClass.POWER,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfPower.WATT,
                has_entity_name=True,
            ),
            device_id,
        )
        self._attr_name = "Filter pump power"

    @property
    def native_value(self) -> int | None:
        """Watts from the first available source."""
        return _first_int(self, _POWER_FIELDS)


class PentairPoolPumpSpeedSensor(SensorEntity, PentairPoolEntity):
    """Pump speed (RPM) from the IntelliFlo `ifs4` field."""

    def __init__(
        self,
        coordinator: PentairPoolDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Bind to one device."""
        super().__init__(
            coordinator,
            SensorEntityDescription(
                key="pump_speed",
                translation_key="pump_speed",
                icon="mdi:speedometer",
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=REVOLUTIONS_PER_MINUTE,
                has_entity_name=True,
            ),
            device_id,
        )
        self._attr_name = "Pump speed"

    @property
    def native_value(self) -> int | None:
        """Current RPM."""
        return _first_int(self, (FIELD_IFS4,))


class PentairPoolPumpProgramSensor(SensorEntity, PentairPoolEntity):
    """Which program the pump is running (`ifs2`), by its name from the app.

    Reports "Off" while stopped and "Priming" during the priming phase that
    precedes every start. Program names come from the cloud fields `p5`-`p8`
    (user-editable in the app); programs without a name fall back to
    "Program N".
    """

    def __init__(
        self,
        coordinator: PentairPoolDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Bind to one device."""
        super().__init__(
            coordinator,
            SensorEntityDescription(
                key="pump_program",
                translation_key="pump_program",
                icon="mdi:format-list-numbered",
                has_entity_name=True,
            ),
            device_id,
        )
        self._attr_name = "Pump program"

    @property
    def native_value(self) -> str | None:
        """Running program's name, "Priming", or "Off"."""
        menu = self.field_value(FIELD_IFS2)
        if menu is None:
            return None
        if menu == IFS2_OFF:
            return "Off"
        if menu == IFS2_PRIMING:
            return "Priming"
        program = _active_program(self)
        if program is None:
            return f"Menu {menu}"  # undocumented Active_Menu value
        return self._program_name(program)

    def _program_name(self, program: int) -> str:
        if program <= len(FIELD_PROGRAM_NAMES):
            name = (self.field_value(FIELD_PROGRAM_NAMES[program - 1]) or "").strip()
            if name:
                return name
        return f"Program {program}"

    @property
    def extra_state_attributes(self) -> dict[str, int | str | None]:
        """Raw Active_Menu code and the running program number."""
        return {
            "active_menu": self.field_value(FIELD_IFS2),
            "program_number": _active_program(self),
        }


class PentairPoolPumpTimerRemainingSensor(SensorEntity, PentairPoolEntity):
    """Egg-timer remaining minutes (`ifs27`) while a program is running.

    `ifs27` only carries a meaningful countdown while a program runs; at rest
    it holds an unrelated rolling value and during priming a short priming
    count, so this reports 0 unless `ifs2` names a running program. A manual
    (untimed) program reads 0 throughout. Confirmed as minutes on 2026-10-25:
    a 60-minute egg-timer program read 60 and the value drops by one per minute.
    """

    def __init__(
        self,
        coordinator: PentairPoolDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Bind to one device."""
        super().__init__(
            coordinator,
            SensorEntityDescription(
                key="pump_timer_remaining",
                translation_key="pump_timer_remaining",
                icon="mdi:timer-sand",
                device_class=SensorDeviceClass.DURATION,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfTime.MINUTES,
                entity_category=EntityCategory.DIAGNOSTIC,
                has_entity_name=True,
            ),
            device_id,
        )
        self._attr_name = "Pump timer remaining"

    @property
    def native_value(self) -> int | None:
        """Minutes remaining while a program runs, else 0."""
        if _active_program(self) is None:  # stopped/priming -> no meaningful countdown
            return 0
        remaining = _first_int(self, (FIELD_IFS27,))
        return remaining if remaining is not None else 0
