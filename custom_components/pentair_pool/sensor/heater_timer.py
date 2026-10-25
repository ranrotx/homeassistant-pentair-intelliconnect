"""Heater timer remaining sensor.

`hts2` (HeaterEggTimerStatus) is the seconds left on a heater timer started
with the `pentair_pool.start_heater_timer` action or from the Pentair app.
The app only treats the timer as running while `htd13` (the commanded run
length) is also non-zero, so this sensor reads 0 otherwise.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.pentair_pool.const import FIELD_HTD13, FIELD_HTS2
from custom_components.pentair_pool.entity import PentairPoolEntity
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.const import UnitOfTime

if TYPE_CHECKING:
    from custom_components.pentair_pool.coordinator import PentairPoolDataUpdateCoordinator

DESCRIPTION = SensorEntityDescription(
    key="heater_timer_remaining",
    translation_key="heater_timer_remaining",
    icon="mdi:timer-outline",
    device_class=SensorDeviceClass.DURATION,
    state_class=SensorStateClass.MEASUREMENT,
    native_unit_of_measurement=UnitOfTime.SECONDS,
    suggested_unit_of_measurement=UnitOfTime.MINUTES,
    has_entity_name=True,
)


def _as_int(v: str | None) -> int | None:
    if v is None:
        return None
    try:
        return int(v)
    except ValueError:
        return None


class PentairPoolHeaterTimerRemainingSensor(SensorEntity, PentairPoolEntity):
    """Seconds left on the heater timer (`hts2`), 0 when no timer runs."""

    def __init__(
        self,
        coordinator: PentairPoolDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Bind to one device."""
        super().__init__(coordinator, DESCRIPTION, device_id)

    @property
    def native_value(self) -> int | None:
        """Remaining seconds while a timer is commanded (`htd13` > 0), else 0."""
        remaining = _as_int(self.field_value(FIELD_HTS2))
        if remaining is None:
            return None
        commanded = _as_int(self.field_value(FIELD_HTD13)) or 0
        return max(remaining, 0) if commanded > 0 else 0
