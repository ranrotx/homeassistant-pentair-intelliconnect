"""Egg-timer duration for an aux relay (e.g. "Blower timer").

The duration lives in Home Assistant, not on the controller: setting it only
chooses how long the matching "Start <accessory> timer" button runs the relay.
It is restored across restarts; until it has been set it starts from the
controller's last timer duration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.pentair_pool.const import RELAY_TIMER_MAX_MINUTES, RELAY_TIMER_MIN_MINUTES
from custom_components.pentair_pool.entity.relay import PentairPoolRelayEntity
from homeassistant.components.number import NumberEntityDescription, NumberMode, RestoreNumber
from homeassistant.const import UnitOfTime

if TYPE_CHECKING:
    from custom_components.pentair_pool.coordinator import PentairPoolDataUpdateCoordinator
    from custom_components.pentair_pool.entity_utils.relay import RelayFields


class PentairPoolRelayTimerDuration(RestoreNumber, PentairPoolRelayEntity):
    """Minutes the Start timer button runs the relay for."""

    _attr_native_min_value = RELAY_TIMER_MIN_MINUTES
    _attr_native_max_value = RELAY_TIMER_MAX_MINUTES
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: PentairPoolDataUpdateCoordinator,
        device_id: str,
        relay: RelayFields,
    ) -> None:
        """Bind to one relay; named after its accessory."""
        super().__init__(
            coordinator,
            NumberEntityDescription(
                key=f"{relay.key}_timer",
                icon="mdi:timer-cog-outline",
                has_entity_name=True,
            ),
            device_id,
            relay,
        )
        self._attr_name = f"{self._attr_name} timer"

    async def async_added_to_hass(self) -> None:
        """Restore the last chosen duration and share it with the Start button."""
        await super().async_added_to_hass()
        last = await self.async_get_last_number_data()
        minutes = int(last.native_value) if last and last.native_value is not None else self._timer_minutes()
        self._store(minutes)

    @property
    def native_value(self) -> float:
        """Chosen duration in minutes."""
        return self._timer_minutes()

    async def async_set_native_value(self, value: float) -> None:
        """Remember the new duration; the controller isn't written until Start."""
        self._store(int(value))
        self.async_write_ha_state()

    def _store(self, minutes: int) -> None:
        self.coordinator.config_entry.runtime_data.relay_timer_minutes[self._timer_key] = minutes
