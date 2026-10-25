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
from custom_components.pentair_pool.const import DOMAIN, FIELD_C1
from custom_components.pentair_pool.entity import PentairPoolEntity
from custom_components.pentair_pool.entity_utils.pump_commands import check_pump_command, program_name
from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.exceptions import HomeAssistantError

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
            self._attr_translation_placeholders = {"program": program_name(self, description.program)}

    async def async_press(self) -> None:
        """Check the pump can take the command, then send it."""
        check_pump_command(self, self.entity_description.program)
        try:
            await self.coordinator.async_set_fields(self._device_id, {FIELD_C1: self.entity_description.command})
        except PentairPoolApiClientError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="command_failed",
            ) from err
