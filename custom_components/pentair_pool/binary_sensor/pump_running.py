"""Physical-pump-state binary sensor.

Reports whether Relay 1 is actually drawing power. This is the "truth"
companion to `switch.<device>_filter_pump` (which represents user intent).
When they disagree, the firmware is either:
  - running the pump via Daily Schedule despite the intent being off, or
  - holding the pump on for heater cooldown despite the intent being off, or
  - the command hasn't propagated yet (typical lag is 1-3 s).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.pentair_pool.const import FIELD_IFS3, FIELD_IFS4, FIELD_RA4
from custom_components.pentair_pool.entity import PentairPoolEntity
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)

# Real-time speed/power first (VSF pumps only push ifs*), relay power last
# (relay-only pumps, and the REST-seeded fallback). First field that reports a
# parseable value wins.
_RUNNING_FIELDS = (FIELD_IFS4, FIELD_IFS3, FIELD_RA4)

if TYPE_CHECKING:
    from custom_components.pentair_pool.coordinator import PentairPoolDataUpdateCoordinator

DESCRIPTION = BinarySensorEntityDescription(
    key="filter_pump_running",
    translation_key="filter_pump_running",
    device_class=BinarySensorDeviceClass.RUNNING,
    has_entity_name=True,
)


class PentairPoolPumpRunningBinarySensor(BinarySensorEntity, PentairPoolEntity):
    """Pump-circulating indicator (speed or power > 0).

    Prefers the real-time IntelliFlo fields (`ifs4` RPM, `ifs3` W) that a VSF
    pump pushes over the WebSocket; falls back to the relay power `ra4` for
    relay-only pumps. This keeps the sensor live for the fountain and the main
    VSF pump, which never push `ra4` over the WebSocket.
    """

    def __init__(
        self,
        coordinator: PentairPoolDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Bind to one device."""
        super().__init__(coordinator, DESCRIPTION, device_id)
        self._attr_name = "Filter pump running"

    @property
    def is_on(self) -> bool | None:
        """True when the pump is circulating (first parseable source > 0)."""
        for code in _RUNNING_FIELDS:
            v = self.field_value(code)
            if v is None:
                continue
            try:
                return int(v) > 0
            except ValueError:
                continue
        return None
