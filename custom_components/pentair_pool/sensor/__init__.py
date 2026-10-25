"""Sensor platform for pentair_pool."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.pentair_pool.const import (
    FIELD_HTD1,
    FIELD_IFS2,
    FIELD_IFS3,
    FIELD_IFS4,
    FIELD_IFS27,
    FIELD_RA4,
    FIELD_RAS0,
    FIELD_T0,
    PARALLEL_UPDATES as PARALLEL_UPDATES,
)
from custom_components.pentair_pool.entity_utils.capabilities import CAP_HEATER, CAP_WATER_TEMP, capability_present

from .cooldown import PentairPoolCooldownCountdown
from .pump import (
    PentairPoolPumpPowerSensor,
    PentairPoolPumpProgramSensor,
    PentairPoolPumpSpeedSensor,
    PentairPoolPumpTimerRemainingSensor,
)
from .telemetry import SENSORS, PentairPoolFieldSensor

if TYPE_CHECKING:
    from custom_components.pentair_pool.data import PentairPoolConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PentairPoolConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create one field-backed sensor per (device, field).

    Also adds the live cooldown countdown for devices that expose `ras0`
    (Relay1_Timer_Status).
    """
    coordinator = entry.runtime_data.coordinator
    entities = []
    for device_id, dev in (coordinator.data or {}).items():
        fields = dev.get("fields") or {}
        for field_code, desc in SENSORS:
            if field_code in fields and _capability_ok(dev, field_code):
                entities.append(
                    PentairPoolFieldSensor(coordinator, device_id, field_code, desc),
                )
        # Pump power: from IntelliFlo watts (ifs3) or relay power (ra4).
        if FIELD_IFS3 in fields or FIELD_RA4 in fields:
            entities.append(PentairPoolPumpPowerSensor(coordinator, device_id))
        # Speed, active program + egg-timer remaining are VSF-only (ifs*).
        if FIELD_IFS4 in fields:
            entities.append(PentairPoolPumpSpeedSensor(coordinator, device_id))
        if FIELD_IFS2 in fields:
            entities.append(PentairPoolPumpProgramSensor(coordinator, device_id))
        if FIELD_IFS27 in fields:
            entities.append(PentairPoolPumpTimerRemainingSensor(coordinator, device_id))
        # The cooldown countdown is a heater accessory; skip on controllers
        # without a heater even though the relay-timer field (ras0) exists.
        if FIELD_RAS0 in fields and capability_present(dev, CAP_HEATER):
            entities.append(PentairPoolCooldownCountdown(coordinator, device_id))
    async_add_entities(entities)


# Field-backed sensors that map to a physical accessory: skip them on
# controllers whose manifest lacks that accessory, so a firmware-reported
# default value (e.g. the 1000 water-temp sentinel, or a heater setpoint on a
# heaterless controller) doesn't create a phantom sensor.
_FIELD_CAPABILITY: dict[str, tuple[str, ...]] = {
    FIELD_T0: (CAP_WATER_TEMP,),
    FIELD_HTD1: (CAP_HEATER,),
}


def _capability_ok(dev: dict, field_code: str) -> bool:
    """True if the accessory backing `field_code` is installed (or unmapped)."""
    keys = _FIELD_CAPABILITY.get(field_code)
    return capability_present(dev, *keys) if keys else True
