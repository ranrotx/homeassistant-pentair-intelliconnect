"""Base class for controllable aux relays (Blower, Pentair Color Light, ...).

The installed accessory and its name come from the listdevices manifest, so
one relay becomes a `light` (manifest type ``lighting``) and the other a
`switch`. Relay fields refresh over REST only (no WebSocket push), so after a
press the state comes from the written ``RelayN_Manual_Schedule`` value until
the next poll confirms it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.pentair_pool.api import PentairPoolApiClientError
from custom_components.pentair_pool.const import DOMAIN
from custom_components.pentair_pool.entity_utils.capabilities import manifest_entry
from custom_components.pentair_pool.entity_utils.relay import (
    RelayFields,
    relay_is_on,
    relay_payload,
    timer_default_minutes,
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

from .base import PentairPoolEntity

if TYPE_CHECKING:
    from custom_components.pentair_pool.coordinator import PentairPoolDataUpdateCoordinator
    from custom_components.pentair_pool.entity_utils.relay import FieldValues
    from homeassistant.helpers.entity import EntityDescription


class PentairPoolRelayEntity(PentairPoolEntity):
    """One aux relay on one device, named from the manifest."""

    def __init__(
        self,
        coordinator: PentairPoolDataUpdateCoordinator,
        entity_description: EntityDescription,
        device_id: str,
        relay: RelayFields,
    ) -> None:
        """Bind to one relay; fall back to the relay label if there's no manifest."""
        super().__init__(coordinator, entity_description, device_id)
        self._relay = relay
        entry = manifest_entry(self.device_state, relay.manifest_key)
        self._attr_name = (entry.get("nickName") or relay.manifest_key).strip()

    def _values(self) -> FieldValues:
        return {code: self.field_value(code) for code in self._relay.codes}

    def _relay_is_on(self) -> bool | None:
        """On/off from the relay state machine and schedule window.

        Platform classes expose this as `is_on` themselves: they list the HA
        platform class first, so its `ToggleEntity.is_on` would shadow a
        property defined here.
        """
        return relay_is_on(self._relay, self._values(), dt_util.utcnow())

    @property
    def extra_state_attributes(self) -> dict[str, str | None]:
        """Raw relay fields, for checking the derived on/off against the app."""
        return {
            "state_machine": self.field_value(self._relay.state),
            "power_watts": self.field_value(self._relay.power),
        }

    @property
    def _timer_key(self) -> str:
        """Key of this relay's HA-side timer duration (the timer number's unique ID)."""
        return f"{self._device_id}_{self._relay.key}_timer"

    def _timer_minutes(self) -> int:
        """Timer duration chosen in HA, else the controller's last one."""
        chosen = self.coordinator.config_entry.runtime_data.relay_timer_minutes.get(self._timer_key)
        return chosen if chosen is not None else timer_default_minutes(self._relay, self._values())

    async def _async_set_relay(self, *, turn_on: bool) -> None:
        payload = relay_payload(self._relay, self._values(), turn_on=turn_on, now=dt_util.utcnow())
        await self._async_write(payload)

    async def _async_write(self, payload: dict[str, str]) -> None:
        try:
            await self.coordinator.async_set_fields(self._device_id, payload)
        except PentairPoolApiClientError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="command_failed",
            ) from err
