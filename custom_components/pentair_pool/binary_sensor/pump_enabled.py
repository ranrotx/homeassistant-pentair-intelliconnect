"""Pump-enabled binary sensor.

Reports whether the pump *feature* is enabled at the controller, which is
distinct from whether it is physically circulating water (see
`sensor.*_pump_speed` / `binary_sensor.*_filter_pump_running`). An IntelliFlo
VSF pump can be enabled but idle (armed, waiting for a schedule/egg timer) or
enabled and running; when disabled it will not run at all.

Derived from `ifs1` (Running_Stopped), confirmed live by toggling the fountain:
the field holds `10` in every enabled state (idle, priming, running) and `4`
when disabled. The app's Stop button (and `button.*_stop_pump`) disables the
pump this way; Run or Resume pump schedules enables it again.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.pentair_pool.const import FIELD_IFS1, IFS1_DISABLED, IFS1_ENABLED
from custom_components.pentair_pool.entity import PentairPoolEntity
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorEntityDescription

if TYPE_CHECKING:
    from custom_components.pentair_pool.coordinator import PentairPoolDataUpdateCoordinator

DESCRIPTION = BinarySensorEntityDescription(
    key="pump_enabled",
    translation_key="pump_enabled",
    icon="mdi:pump",
    has_entity_name=True,
)


class PentairPoolPumpEnabledBinarySensor(BinarySensorEntity, PentairPoolEntity):
    """`ifs1 == 10` -> pump feature enabled."""

    def __init__(
        self,
        coordinator: PentairPoolDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Bind to one device."""
        super().__init__(coordinator, DESCRIPTION, device_id)
        self._attr_name = "Pump enabled"

    @property
    def is_on(self) -> bool | None:
        """True when the pump feature is enabled (ifs1 == 10)."""
        v = self.field_value(FIELD_IFS1)
        if v is None:
            return None
        return v == IFS1_ENABLED

    @property
    def extra_state_attributes(self) -> dict[str, str | None]:
        """Raw ifs1 plus a decoded label for the known values."""
        v = self.field_value(FIELD_IFS1)
        labels = {IFS1_ENABLED: "enabled", IFS1_DISABLED: "disabled"}
        return {
            "ifs1_raw": v,
            "ifs1_state": labels.get(v, f"unknown ({v})") if v is not None else None,
        }
