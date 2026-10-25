"""Aux-relay switch for non-light accessories (e.g. the Blower on Relay 2)."""

from __future__ import annotations

from typing import Any

from custom_components.pentair_pool.entity.relay import PentairPoolRelayEntity
from homeassistant.components.switch import SwitchEntity


class PentairPoolRelaySwitch(SwitchEntity, PentairPoolRelayEntity):
    """On/off for one aux relay, like the app's relay toggle."""

    @property
    def is_on(self) -> bool | None:
        """Whether the relay is on."""
        return self._relay_is_on()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the relay on."""
        await self._async_set_relay(turn_on=True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the relay off."""
        await self._async_set_relay(turn_on=False)
