"""Aux-relay on/off binary sensor (Blower, Pentair Color Light, ...).

Relay 1 and Relay 2 are generic auxiliary relays; the installed accessory is
read from the listdevices ``devices`` manifest (on the captured account Relay 1
is a Pentair Color Light and Relay 2 is a Blower). Both relays expose the same
field layout, so one class drives either, parameterised by its state/power
fields and manifest key.

On/off is derived from the ``RelayN_Manual_Schedule`` state machine (the same
values as the pump: 0=off, 1=on, 2=off/scheduled, 3=on/scheduled, 4=timer-done)
OR a non-zero power draw. The relay fields refresh over REST (not the WebSocket),
so this reflects a change from the panel/app within the 60 s poll interval.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.pentair_pool.entity import PentairPoolEntity
from custom_components.pentair_pool.entity_utils.capabilities import manifest_entry
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)

if TYPE_CHECKING:
    from custom_components.pentair_pool.coordinator import PentairPoolDataUpdateCoordinator

# RelayN_Manual_Schedule values that mean the relay is energised.
_ON_STATES = {"1", "3"}


class PentairPoolRelayBinarySensor(BinarySensorEntity, PentairPoolEntity):
    """On/off indicator for one aux relay, named from the device manifest."""

    def __init__(
        self,
        coordinator: PentairPoolDataUpdateCoordinator,
        device_id: str,
        *,
        key: str,
        manifest_key: str,
        state_field: str,
        power_field: str,
    ) -> None:
        """Bind to one relay on one device."""
        entry = manifest_entry((coordinator.data or {}).get(device_id) or {}, manifest_key)
        is_light = entry.get("type") == "lighting"
        # A light is plain on/off: BinarySensorDeviceClass.LIGHT means "light
        # DETECTED" (an illuminance sensor), which would mislabel the state.
        # Leave lights with no device_class (On/Off) and a lightbulb icon;
        # classify other relays (pumps/blowers) as RUNNING.
        super().__init__(
            coordinator,
            BinarySensorEntityDescription(
                key=key,
                device_class=None if is_light else BinarySensorDeviceClass.RUNNING,
                icon="mdi:lightbulb" if is_light else None,
                has_entity_name=True,
            ),
            device_id,
        )
        # Name from cloud metadata ("Blower", "Pentair Color Light"); fall back
        # to the relay label if the manifest is unavailable.
        self._attr_name = (entry.get("nickName") or manifest_key).strip()
        self._state_field = state_field
        self._power_field = power_field

    def _power(self) -> int | None:
        v = self.field_value(self._power_field)
        if v is None:
            return None
        try:
            return int(v)
        except ValueError:
            return None

    @property
    def is_on(self) -> bool | None:
        """On when the relay state machine says on, or it's drawing power."""
        state = self.field_value(self._state_field)
        power = self._power()
        if state is None and power is None:
            return None
        return (state in _ON_STATES) or bool(power)

    @property
    def extra_state_attributes(self) -> dict[str, str | int | None]:
        """Raw relay fields, for verifying the derived on/off against reality."""
        return {
            "state_machine": self.field_value(self._state_field),
            "power_watts": self._power(),
        }
