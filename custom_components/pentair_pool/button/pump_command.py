"""IntelliFlo pump command buttons (run a program, stop, resume schedules).

Each press writes the pump's `c1` command field, exactly as the Pentair app's
program play/stop buttons and pump on/off toggle do (decoded from the Android
app and verified live on the fountain on 2026-10-25):

  - "1"-"4": run Program N with the speed and egg timer set in the app
  - "6": stop the pump; it stays disabled (`ifs1` = 4) and its schedules
         don't run until it is re-enabled
  - "5": re-enable the pump so its schedules run again

Program settings stay in the Pentair app; these buttons only press start/stop.
Like the app, a press is refused while the pump reports a blocking alarm, and
a program set to run on a schedule has no Run button action.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from custom_components.pentair_pool.api import PentairPoolApiClientError
from custom_components.pentair_pool.const import (
    DOMAIN,
    FIELD_C1,
    FIELD_IFS18,
    FIELD_PROGRAM_MODES,
    FIELD_PROGRAM_NAMES,
    IFS18_COMMAND_BLOCKED,
    PROGRAM_MODE_SCHEDULE,
)
from custom_components.pentair_pool.entity import PentairPoolEntity
from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

if TYPE_CHECKING:
    from custom_components.pentair_pool.coordinator import PentairPoolDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class PentairPoolPumpButtonDescription(ButtonEntityDescription):
    """A pump command button: the `c1` value it sends, and its program if any."""

    command: str
    program: int | None = None


class PentairPoolPumpCommandButton(ButtonEntity, PentairPoolEntity):
    """Send one `c1` command to an IntelliFlo pump."""

    entity_description: PentairPoolPumpButtonDescription

    def __init__(
        self,
        coordinator: PentairPoolDataUpdateCoordinator,
        description: PentairPoolPumpButtonDescription,
        device_id: str,
    ) -> None:
        """Bind to one device; program buttons are named after the program."""
        super().__init__(coordinator, description, device_id)
        if description.program is not None:
            self._attr_translation_placeholders = {"program": self._program_name()}

    def _program_name(self) -> str:
        """Program's name from the app (`p5`-`p8`), else "Program N"."""
        program = self.entity_description.program
        name = (self.field_value(FIELD_PROGRAM_NAMES[program - 1]) or "").strip() if program else ""
        return name or f"Program {program}"

    async def async_press(self) -> None:
        """Check the pump can take the command, then send it."""
        alarm = self.field_value(FIELD_IFS18)
        if alarm in IFS18_COMMAND_BLOCKED:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="pump_alarm",
                translation_placeholders={"alarm": str(alarm)},
            )
        program = self.entity_description.program
        if program is not None and self.field_value(FIELD_PROGRAM_MODES[program - 1]) == PROGRAM_MODE_SCHEDULE:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="program_runs_on_schedule",
                translation_placeholders={"program": self._program_name()},
            )
        try:
            await self.coordinator.async_set_fields(self._device_id, {FIELD_C1: self.entity_description.command})
        except PentairPoolApiClientError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="command_failed",
            ) from err
