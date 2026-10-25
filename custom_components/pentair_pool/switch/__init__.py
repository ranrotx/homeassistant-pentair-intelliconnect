"""Switch platform for pentair_pool (aux relays other than lights)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.pentair_pool.const import PARALLEL_UPDATES as PARALLEL_UPDATES
from custom_components.pentair_pool.entity_utils.relay import installed_relays
from homeassistant.components.switch import SwitchDeviceClass, SwitchEntityDescription

from .relay import PentairPoolRelaySwitch

if TYPE_CHECKING:
    from custom_components.pentair_pool.data import PentairPoolConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PentairPoolConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add one switch per installed aux relay whose accessory isn't a light."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        PentairPoolRelaySwitch(
            coordinator,
            SwitchEntityDescription(key=relay.key, device_class=SwitchDeviceClass.SWITCH, has_entity_name=True),
            device_id,
            relay,
        )
        for device_id, dev in (coordinator.data or {}).items()
        for relay in installed_relays(dev, lighting=False)
    )
