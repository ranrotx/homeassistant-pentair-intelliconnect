"""Binary-sensor platform for pentair_pool."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.pentair_pool.const import (
    FIELD_IFS1,
    FIELD_IFS3,
    FIELD_IFS4,
    FIELD_RA0,
    FIELD_RA4,
    FIELD_RB0,
    FIELD_RB4,
    PARALLEL_UPDATES as PARALLEL_UPDATES,
)
from custom_components.pentair_pool.entity_utils.capabilities import CAP_RELAY1, CAP_RELAY2, capability_present

from .pump_enabled import PentairPoolPumpEnabledBinarySensor
from .pump_running import PentairPoolPumpRunningBinarySensor
from .relay import PentairPoolRelayBinarySensor
from .status import PentairPoolAlarmBinarySensor, PentairPoolOnlineBinarySensor

# Any of these reporting means the device has a pump whose running-state we can
# derive (ifs4/ifs3 for VSF pumps, ra4 for relay pumps).
_PUMP_FIELDS = (FIELD_IFS4, FIELD_IFS3, FIELD_RA4)

# Aux relays: (entity key, manifest capability, state-machine field, power field).
# The installed accessory (Blower, Color Light, ...) and its name come from the
# manifest at entity construction.
_RELAYS = (
    ("relay_1", CAP_RELAY1, FIELD_RA0, FIELD_RA4),
    ("relay_2", CAP_RELAY2, FIELD_RB0, FIELD_RB4),
)

if TYPE_CHECKING:
    from custom_components.pentair_pool.data import PentairPoolConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PentairPoolConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add per-device binary sensors."""
    coordinator = entry.runtime_data.coordinator
    entities = []
    for device_id, dev in (coordinator.data or {}).items():
        fields = dev.get("fields") or {}
        entities.append(PentairPoolOnlineBinarySensor(coordinator, device_id))
        entities.append(PentairPoolAlarmBinarySensor(coordinator, device_id))
        if any(f in fields for f in _PUMP_FIELDS):
            entities.append(PentairPoolPumpRunningBinarySensor(coordinator, device_id))
        if FIELD_IFS1 in fields:
            entities.append(PentairPoolPumpEnabledBinarySensor(coordinator, device_id))
        for key, cap, state_field, power_field in _RELAYS:
            if state_field in fields and capability_present(dev, cap):
                entities.append(
                    PentairPoolRelayBinarySensor(
                        coordinator,
                        device_id,
                        key=key,
                        manifest_key=cap,
                        state_field=state_field,
                        power_field=power_field,
                    ),
                )
    async_add_entities(entities)
