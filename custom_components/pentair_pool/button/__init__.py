"""Button platform for pentair_pool (IntelliFlo pump program start/stop, relay timers)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.pentair_pool.const import (
    C1_RESUME_SCHEDULES,
    C1_STOP,
    FIELD_IFS2,
    FIELD_PROGRAM_MODES,
    PARALLEL_UPDATES as PARALLEL_UPDATES,
)
from custom_components.pentair_pool.entity_utils.relay import installed_relays

from .pump_command import PentairPoolPumpButtonDescription, PentairPoolPumpCommandButton
from .relay_timer import PentairPoolRelayTimerButton

if TYPE_CHECKING:
    from custom_components.pentair_pool.data import PentairPoolConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

STOP = PentairPoolPumpButtonDescription(
    key="pump_stop",
    translation_key="pump_stop",
    icon="mdi:stop",
    command=C1_STOP,
)
RESUME_SCHEDULES = PentairPoolPumpButtonDescription(
    key="pump_resume_schedules",
    translation_key="pump_resume_schedules",
    icon="mdi:calendar-clock",
    command=C1_RESUME_SCHEDULES,
)


def _run_program(program: int) -> PentairPoolPumpButtonDescription:
    return PentairPoolPumpButtonDescription(
        key=f"pump_program_{program}_run",
        translation_key="pump_program_run",
        icon="mdi:play",
        command=str(program),
        program=program,
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PentairPoolConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add pump buttons for every IntelliFlo VSF pump (devices reporting `ifs2`).

    One Run button per program slot the pump reports (`ifd0`-`ifd3`), plus
    Stop and Resume schedules. Also a Start timer button for each installed
    aux relay that isn't a light.
    """
    coordinator = entry.runtime_data.coordinator
    entities = []
    for device_id, dev in (coordinator.data or {}).items():
        entities.extend(
            PentairPoolRelayTimerButton(coordinator, device_id, relay)
            for relay in installed_relays(dev, lighting=False)
        )
        fields = dev.get("fields") or {}
        if FIELD_IFS2 not in fields:
            continue
        entities.extend(
            PentairPoolPumpCommandButton(coordinator, _run_program(n), device_id)
            for n, mode_field in enumerate(FIELD_PROGRAM_MODES, start=1)
            if mode_field in fields
        )
        entities.append(PentairPoolPumpCommandButton(coordinator, STOP, device_id))
        entities.append(PentairPoolPumpCommandButton(coordinator, RESUME_SCHEDULES, device_id))
    async_add_entities(entities)
