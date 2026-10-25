"""Shared checks before sending an IntelliFlo `c1` pump command.

Used by the pump buttons and by the heater when it starts a pump program for
heating. Mirrors the Pentair app: a command is refused while the pump reports
a blocking alarm, and a program set to run on a schedule is never run directly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.pentair_pool.const import (
    DOMAIN,
    FIELD_IFS18,
    FIELD_PROGRAM_MODES,
    FIELD_PROGRAM_NAMES,
    IFS18_COMMAND_BLOCKED,
    PROGRAM_MODE_SCHEDULE,
)
from homeassistant.exceptions import ServiceValidationError

if TYPE_CHECKING:
    from custom_components.pentair_pool.entity import PentairPoolEntity


def program_name(entity: PentairPoolEntity, program: int) -> str:
    """Program's name from the app (`p5`-`p8`), else "Program N"."""
    name = (entity.field_value(FIELD_PROGRAM_NAMES[program - 1]) or "").strip()
    return name or f"Program {program}"


def check_pump_command(entity: PentairPoolEntity, program: int | None = None) -> None:
    """Raise ServiceValidationError if the pump can't take a command now.

    `program` is the program a Run command would start, or None for Stop and
    Resume schedules.
    """
    alarm = entity.field_value(FIELD_IFS18)
    if alarm in IFS18_COMMAND_BLOCKED:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="pump_alarm",
            translation_placeholders={"alarm": str(alarm)},
        )
    if program is not None and entity.field_value(FIELD_PROGRAM_MODES[program - 1]) == PROGRAM_MODE_SCHEDULE:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="program_runs_on_schedule",
            translation_placeholders={"program": program_name(entity, program)},
        )
