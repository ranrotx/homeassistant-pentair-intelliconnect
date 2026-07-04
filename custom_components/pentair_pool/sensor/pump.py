"""IntelliFlo VSF pump sensors (power, speed, egg-timer remaining).

A variable-speed IntelliFlo pump reports its live state through the `ifs*`
field family, captured from a two-controller account on 2026-07-03 (see
`docs/intelliconnect-phase1-capture.md`):

  - `ifs4` = pump speed (RPM):   0 stopped, ~900 steady run, ~1800 priming
  - `ifs3` = pump power (watts):  scales ~cubically with RPM
  - `ifs27` = egg-timer remaining (seconds): counts down while a timed run is
              active; the pump stops the moment it reaches 0

Unlike the relay fields (`ra*`), these push over the WebSocket in real time,
so they are the authoritative source for both the Feature Control fountain and
the Main Control pump. The power sensor keeps the historical
`filter_pump_power` key and falls back to the relay power `ra4` so relay-only
pumps (and the entity's history) keep working.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.pentair_pool.const import FIELD_IFS3, FIELD_IFS4, FIELD_IFS27, FIELD_RA4
from custom_components.pentair_pool.entity import PentairPoolEntity
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.const import REVOLUTIONS_PER_MINUTE, EntityCategory, UnitOfPower, UnitOfTime

if TYPE_CHECKING:
    from custom_components.pentair_pool.coordinator import PentairPoolDataUpdateCoordinator

# Power source preference: real-time IntelliFlo watts first, relay power last.
_POWER_FIELDS = (FIELD_IFS3, FIELD_RA4)


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


class PentairPoolPumpTimerRemainingSensor(SensorEntity, PentairPoolEntity):
    """Egg-timer remaining seconds (`ifs27`) while a timed run is active.

    `ifs27` only carries a meaningful countdown while the pump is running; at
    rest the field holds an unrelated rolling value, so this reports 0 whenever
    the pump is stopped (`ifs4` == 0). Marked diagnostic pending final
    confirmation of the field's exact semantics.
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
                native_unit_of_measurement=UnitOfTime.SECONDS,
                entity_category=EntityCategory.DIAGNOSTIC,
                has_entity_name=True,
            ),
            device_id,
        )
        self._attr_name = "Pump timer remaining"

    @property
    def native_value(self) -> int | None:
        """Seconds remaining while running, else 0."""
        rpm = _first_int(self, (FIELD_IFS4,))
        if not rpm:  # stopped or unknown -> no meaningful countdown
            return 0
        remaining = _first_int(self, (FIELD_IFS27,))
        return remaining if remaining is not None else 0
