"""Switch platform for pentair_pool."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.pentair_pool.const import FIELD_RA0, PARALLEL_UPDATES as PARALLEL_UPDATES
from custom_components.pentair_pool.entity_utils.capabilities import CAP_RELAY1, capability_present

from .pump import PentairPoolPumpSwitch
from .schedule import PentairPoolDailyScheduleSwitch

if TYPE_CHECKING:
    from custom_components.pentair_pool.data import PentairPoolConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PentairPoolConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform.

    Gated on the `Relay 1` manifest capability (not just `ra0` presence): a
    controller with no relay installed still reports default relay fields, which
    would otherwise create phantom pump/schedule switches.
    """
    coordinator = entry.runtime_data.coordinator
    entities = []
    for device_id, dev in (coordinator.data or {}).items():
        if FIELD_RA0 not in (dev.get("fields") or {}):
            continue
        if not capability_present(dev, CAP_RELAY1):
            continue
        entities.append(PentairPoolPumpSwitch(coordinator, device_id))
        entities.append(PentairPoolDailyScheduleSwitch(coordinator, device_id))
    async_add_entities(entities)
