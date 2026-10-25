"""Number platform for pentair_pool (aux-relay egg-timer durations)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.pentair_pool.const import PARALLEL_UPDATES as PARALLEL_UPDATES
from custom_components.pentair_pool.entity_utils.relay import installed_relays

from .relay_timer import PentairPoolRelayTimerDuration

if TYPE_CHECKING:
    from custom_components.pentair_pool.data import PentairPoolConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PentairPoolConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add a timer duration for each installed aux relay that isn't a light."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        PentairPoolRelayTimerDuration(coordinator, device_id, relay)
        for device_id, dev in (coordinator.data or {}).items()
        for relay in installed_relays(dev, lighting=False)
    )
