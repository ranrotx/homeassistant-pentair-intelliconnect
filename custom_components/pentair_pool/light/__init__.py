"""Light platform for pentair_pool (lights on aux relays)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.pentair_pool.const import PARALLEL_UPDATES as PARALLEL_UPDATES
from custom_components.pentair_pool.entity_utils.relay import installed_relays
from homeassistant.components.light import LightEntityDescription

from .relay import PentairPoolRelayLight

if TYPE_CHECKING:
    from custom_components.pentair_pool.data import PentairPoolConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PentairPoolConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add one light per installed aux relay whose manifest type is ``lighting``."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        PentairPoolRelayLight(
            coordinator,
            LightEntityDescription(key=relay.key, icon="mdi:lightbulb", has_entity_name=True),
            device_id,
            relay,
        )
        for device_id, dev in (coordinator.data or {}).items()
        for relay in installed_relays(dev, lighting=True)
    )
