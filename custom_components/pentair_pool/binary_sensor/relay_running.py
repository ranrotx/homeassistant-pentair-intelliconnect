"""Whether an aux-relay accessory (e.g. the Blower) is actually running.

The relay switch turns on the moment it is pressed, but the controller first
primes the pump and brings it up to the accessory's speed, so a blower only
starts about 2 minutes later. This sensor follows the relay's power draw
instead: on once it exceeds ``RELAY_RUNNING_MIN_WATTS``. Relay power refreshes
over REST only, so it lags the real start by up to one poll.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.pentair_pool.const import RELAY_RUNNING_MIN_WATTS
from custom_components.pentair_pool.entity.relay import PentairPoolRelayEntity
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)

if TYPE_CHECKING:
    from custom_components.pentair_pool.coordinator import PentairPoolDataUpdateCoordinator
    from custom_components.pentair_pool.entity_utils.relay import RelayFields


class PentairPoolRelayRunningBinarySensor(BinarySensorEntity, PentairPoolRelayEntity):
    """`<accessory> running`: relay power above the running threshold."""

    def __init__(
        self,
        coordinator: PentairPoolDataUpdateCoordinator,
        device_id: str,
        relay: RelayFields,
    ) -> None:
        """Bind to one relay; named after its accessory."""
        super().__init__(
            coordinator,
            BinarySensorEntityDescription(
                key=f"{relay.key}_running",
                device_class=BinarySensorDeviceClass.RUNNING,
                has_entity_name=True,
            ),
            device_id,
            relay,
        )
        self._attr_name = f"{self._attr_name} running"

    @property
    def is_on(self) -> bool | None:
        """True while the relay draws more than the running threshold."""
        value = self.field_value(self._relay.power)
        try:
            return int(value) > RELAY_RUNNING_MIN_WATTS if value is not None else None
        except ValueError:
            return None
