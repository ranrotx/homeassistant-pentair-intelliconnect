"""Aux-relay light for lighting accessories (e.g. the Pentair Color Light on Relay 1).

On/off only; the color theme (`RelayN_ColorLight_Mode`) stays in the Pentair app.
"""

from __future__ import annotations

from typing import Any

from custom_components.pentair_pool.entity.relay import PentairPoolRelayEntity
from homeassistant.components.light import LightEntity
from homeassistant.components.light.const import ColorMode


class PentairPoolRelayLight(LightEntity, PentairPoolRelayEntity):
    """On/off for a light on an aux relay, like the app's relay toggle."""

    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}

    @property
    def is_on(self) -> bool | None:
        """Whether the light is on."""
        return self._relay_is_on()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        await self._async_set_relay(turn_on=True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        await self._async_set_relay(turn_on=False)
