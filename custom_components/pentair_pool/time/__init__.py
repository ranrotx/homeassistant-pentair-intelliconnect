"""Time platform: editable Daily Schedule start / end."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.pentair_pool.const import FIELD_RA1, FIELD_RA2, PARALLEL_UPDATES as PARALLEL_UPDATES
from custom_components.pentair_pool.entity_utils.capabilities import CAP_RELAY1, capability_present

from .schedule import PentairPoolScheduleEnd, PentairPoolScheduleStart

if TYPE_CHECKING:
    from custom_components.pentair_pool.data import PentairPoolConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PentairPoolConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """One pair of schedule time entities per device with a Relay 1 installed.

    Gated on the `Relay 1` manifest capability: a controller with no relay still
    reports default ra1/ra2 schedule fields, which would create phantom entities.
    """
    coordinator = entry.runtime_data.coordinator
    entities = []
    for device_id, dev in (coordinator.data or {}).items():
        fields = dev.get("fields") or {}
        if not capability_present(dev, CAP_RELAY1):
            continue
        if FIELD_RA1 in fields:
            entities.append(PentairPoolScheduleStart(coordinator, device_id))
        if FIELD_RA2 in fields:
            entities.append(PentairPoolScheduleEnd(coordinator, device_id))
    async_add_entities(entities)
