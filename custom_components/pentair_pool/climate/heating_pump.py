"""Run a pump program for the heater, and stop it once the heater is done.

The IntelliConnect heater only fires while a pump provides flow, and the
controller does not start the pump for it (verified live 2026-10-25: heater on,
water below setpoint, IntelliFlo enabled but stopped, so the pump stayed off).
With the `heating_pump_program` option set, the heater entity therefore:

  - before turning the heater on or starting a heater timer, runs that program
    (`c1` = program number) if the pump on the same controller is stopped
    (`ifs2` = 0);
  - once the heater is off (`htd1` = 0) and its cooldown has finished
    (`htd14` = 0), stops the pump (`c1` = 6) and re-enables its schedules
    (`c1` = 5), as the app's pump toggle does.

It only stops a pump it started itself. That is remembered in memory only, so
after a Home Assistant restart a pump started earlier is left running. Heater
fields arrive only with the REST poll, so the stop also waits until the heater
has read off for `_STOP_GRACE_SECONDS`, long enough for a cooldown to show up.
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING

from custom_components.pentair_pool.api import PentairPoolApiClientError
from custom_components.pentair_pool.const import (
    C1_RESUME_SCHEDULES,
    C1_STOP,
    DOMAIN,
    FIELD_C1,
    FIELD_HTD1,
    FIELD_HTD14,
    FIELD_IFS2,
    HTD1_OFF,
    IFS2_OFF,
    LOGGER,
)
from custom_components.pentair_pool.entity_utils.pump_commands import check_pump_command
from homeassistant.exceptions import HomeAssistantError

if TYPE_CHECKING:
    from custom_components.pentair_pool.entity import PentairPoolEntity

# How long the heater must read off before its pump is stopped.
_STOP_GRACE_SECONDS = 120
# Pause between Stop and Resume schedules; the app waits one poll interval.
_RESUME_DELAY_SECONDS = 10


class PentairPoolHeatingPump:
    """Start/stop logic for the pump program that gives the heater flow."""

    def __init__(self, entity: PentairPoolEntity, device_id: str, program: int | None) -> None:
        """Bind to the heater entity; `program` None disables the feature."""
        self._entity = entity
        self._device_id = device_id
        self._program = program
        self._started = False
        self._off_since: float | None = None
        self._stopping = False

    @property
    def started(self) -> bool:
        """True while a pump program started for heating may still be running."""
        return self._started

    async def async_ensure_running(self) -> None:
        """Run the heating program if the controller's pump is stopped."""
        entity = self._entity
        if self._program is None or entity.field_value(FIELD_IFS2) != IFS2_OFF:
            return
        check_pump_command(entity, self._program)
        await self._async_command(str(self._program))
        LOGGER.debug("Started pump program %s for heating on %s", self._program, entity.unique_id)
        self._started = True
        self._off_since = None

    async def async_check_stop(self) -> None:
        """Stop a pump started for heating once the heater and its cooldown are done."""
        entity = self._entity
        if not self._started or self._stopping:
            return
        if entity.field_value(FIELD_HTD1) != HTD1_OFF:
            self._off_since = None
            return
        now = time.monotonic()
        if self._off_since is None:
            self._off_since = now
        if entity.field_value(FIELD_HTD14) not in (None, "0") or now - self._off_since < _STOP_GRACE_SECONDS:
            return
        self._started = False
        if entity.field_value(FIELD_IFS2) == IFS2_OFF:
            # The program already ended on its own (e.g. its egg timer ran out).
            return
        self._stopping = True
        try:
            check_pump_command(entity)
            await self._async_command(C1_STOP)
            await asyncio.sleep(_RESUME_DELAY_SECONDS)
            await self._async_command(C1_RESUME_SCHEDULES)
            LOGGER.debug("Stopped heating pump program on %s", entity.unique_id)
        except HomeAssistantError as err:
            LOGGER.warning("Could not stop the pump after heating on %s: %s", entity.unique_id, err)
        finally:
            self._stopping = False

    async def _async_command(self, command: str) -> None:
        entity = self._entity
        try:
            await entity.coordinator.async_set_fields(self._device_id, {FIELD_C1: command})
        except PentairPoolApiClientError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="command_failed",
            ) from err
