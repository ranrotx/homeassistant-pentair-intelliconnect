"""Climate platform for pentair_pool (pool heater)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.pentair_pool.const import FIELD_HTD1, PARALLEL_UPDATES as PARALLEL_UPDATES
from custom_components.pentair_pool.entity_utils.capabilities import CAP_HEATER, capability_present

from .heater import PentairPoolHeater

if TYPE_CHECKING:
    from custom_components.pentair_pool.data import PentairPoolConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PentairPoolConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up one heater per device that has a heater installed.

    Gated on the `heaters` capability from the listdevices manifest, not just
    `htd1` presence -- controllers without a heater still report a default
    `htd1`/`htd2`, which would otherwise create a phantom heater entity.
    """
    coordinator = entry.runtime_data.coordinator
    entities = [
        PentairPoolHeater(coordinator, device_id)
        for device_id, dev in (coordinator.data or {}).items()
        if FIELD_HTD1 in (dev.get("fields") or {}) and capability_present(dev, CAP_HEATER)
    ]
    async_add_entities(entities)
