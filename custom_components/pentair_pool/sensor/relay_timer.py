"""Time left in an aux relay's egg-timed run (e.g. "Blower timer remaining").

Reads `RelayN_Timer_Status`, the controller's countdown in seconds; 0 when no
timed run is active. Relay fields refresh over REST only, so the value steps
once per poll.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.pentair_pool.entity.relay import PentairPoolRelayEntity
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription
from homeassistant.const import UnitOfTime

if TYPE_CHECKING:
    from custom_components.pentair_pool.coordinator import PentairPoolDataUpdateCoordinator
    from custom_components.pentair_pool.entity_utils.relay import RelayFields


class PentairPoolRelayTimerRemainingSensor(SensorEntity, PentairPoolRelayEntity):
    """Seconds left in the relay's timed run."""

    def __init__(
        self,
        coordinator: PentairPoolDataUpdateCoordinator,
        device_id: str,
        relay: RelayFields,
    ) -> None:
        """Bind to one relay; named after its accessory."""
        super().__init__(
            coordinator,
            SensorEntityDescription(
                key=f"{relay.key}_timer_remaining",
                icon="mdi:timer-sand",
                device_class=SensorDeviceClass.DURATION,
                native_unit_of_measurement=UnitOfTime.SECONDS,
                suggested_unit_of_measurement=UnitOfTime.MINUTES,
                suggested_display_precision=1,
                has_entity_name=True,
            ),
            device_id,
            relay,
        )
        self._attr_name = f"{self._attr_name} timer remaining"

    @property
    def native_value(self) -> int | None:
        """Seconds remaining, 0 when no timed run is active."""
        value = self.field_value(self._relay.timer_status)
        try:
            return max(int(value), 0) if value is not None else None
        except ValueError:
            return None
