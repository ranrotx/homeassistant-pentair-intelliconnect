"""Start an egg-timed run of an aux relay (e.g. "Start Blower timer").

Writes the duration from the matching timer number to both relay timer fields,
as the Pentair app's timer does (decoded from the Android app's saveTimer).
That write starts the relay; the controller turns it off when the countdown
(`RelayN_Timer_Status`) reaches 0. Turning the relay off sooner cancels it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.pentair_pool.entity.relay import PentairPoolRelayEntity
from custom_components.pentair_pool.entity_utils.relay import timer_payload
from homeassistant.components.button import ButtonEntity, ButtonEntityDescription

if TYPE_CHECKING:
    from custom_components.pentair_pool.coordinator import PentairPoolDataUpdateCoordinator
    from custom_components.pentair_pool.entity_utils.relay import RelayFields


class PentairPoolRelayTimerButton(ButtonEntity, PentairPoolRelayEntity):
    """Run the relay for the chosen timer duration."""

    def __init__(
        self,
        coordinator: PentairPoolDataUpdateCoordinator,
        device_id: str,
        relay: RelayFields,
    ) -> None:
        """Bind to one relay; named after its accessory."""
        super().__init__(
            coordinator,
            ButtonEntityDescription(key=f"{relay.key}_timer_start", icon="mdi:timer-play", has_entity_name=True),
            device_id,
            relay,
        )
        self._attr_name = f"Start {self._attr_name} timer"

    async def async_press(self) -> None:
        """Start the timed run."""
        await self._async_write(timer_payload(self._relay, self._values(), self._timer_minutes()))
