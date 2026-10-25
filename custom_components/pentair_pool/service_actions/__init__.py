"""Service actions package for pentair_pool."""

from __future__ import annotations

from typing import TYPE_CHECKING

import voluptuous as vol

from custom_components.pentair_pool.const import DOMAIN, LOGGER
from homeassistant.components.climate.const import DOMAIN as CLIMATE_DOMAIN
from homeassistant.helpers import config_validation as cv, service

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, ServiceCall


SERVICE_RELOAD_DATA = "reload_data"
SERVICE_START_HEATER_TIMER = "start_heater_timer"

ATTR_DURATION = "duration"


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register integration-level services.

    `pentair_pool.reload_data` forces a coordinator refresh for every
    configured account, which is useful after manually changing settings
    on a controller.

    `pentair_pool.start_heater_timer` targets a heater climate entity and
    runs it for a duration (handled by `PentairPoolHeater.async_start_timer`).
    """

    async def handle_reload_data(_call: ServiceCall) -> None:
        for entry in hass.config_entries.async_entries(DOMAIN):
            coordinator = entry.runtime_data.coordinator if hasattr(entry, "runtime_data") else None
            if coordinator is not None:
                await coordinator.async_request_refresh()

    if not hass.services.has_service(DOMAIN, SERVICE_RELOAD_DATA):
        hass.services.async_register(DOMAIN, SERVICE_RELOAD_DATA, handle_reload_data)

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_START_HEATER_TIMER,
        entity_domain=CLIMATE_DOMAIN,
        schema={vol.Required(ATTR_DURATION): cv.positive_time_period},
        func="async_start_timer",
    )
    LOGGER.debug("pentair_pool services registered")
