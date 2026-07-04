"""Per-device capability gating from the Pentair ``listdevices`` manifest.

Each controller's ``listdevices`` payload carries a ``devices`` manifest that
enumerates the physically installed accessories -- e.g. on a Main Control
controller::

    {"Water Temperature": {...}, "Air Temperature": {...},
     "IntelliFlo pumps": {...}, "sanitizers": {...}, "heaters": {...},
     "Relay 1": {"nickName": "Pentair Color Light", ...},
     "Relay 2": {"nickName": "Blower", ...}}

whereas a Feature Control controller that only drives a fountain reports just::

    {"Air Temperature": {...}, "IntelliFlo pumps": {"nickName": "Fountain "}}

The firmware still reports *config/status fields* for hardware that isn't
installed (a heater setpoint, a ``1000`` water-temp sentinel, relay schedule
fields), so gating entity creation on field presence alone produces phantom
entities on controllers that lack that hardware. Gating on this manifest
instead matches exactly what the Pentair app renders.
"""

from __future__ import annotations

from typing import Any

# Manifest keys, verbatim from the listdevices ``devices`` object.
CAP_HEATER = "heaters"
CAP_WATER_TEMP = "Water Temperature"
CAP_AIR_TEMP = "Air Temperature"
CAP_SANITIZER = "sanitizers"
CAP_PUMP = "IntelliFlo pumps"
CAP_RELAY1 = "Relay 1"
CAP_RELAY2 = "Relay 2"


def device_manifest(dev: dict[str, Any]) -> dict[str, Any]:
    """Return the installed-accessory manifest for a coordinator device entry."""
    return ((dev or {}).get("device_info") or {}).get("devices") or {}


def capability_present(dev: dict[str, Any], *keys: str) -> bool:
    """True if the device's manifest lists any of ``keys``.

    Falls back to ``True`` when the device reports no manifest at all (older
    firmware), so we degrade to field-presence gating and never hide real
    hardware on a controller that simply doesn't publish a manifest.
    """
    manifest = device_manifest(dev)
    if not manifest:
        return True
    return any(k in manifest for k in keys)


def manifest_entry(dev: dict[str, Any], key: str) -> dict[str, Any]:
    """Return the manifest entry for ``key`` (e.g. the ``Relay 1`` accessory).

    Each entry carries the installed accessory's ``nickName`` (Blower, Pentair
    Color Light, ...), ``model`` and ``type`` (``lighting``, a pump type, ...),
    so entities can name and classify themselves from cloud metadata instead of
    hard-coding ``Relay 1``.
    """
    entry = device_manifest(dev).get(key)
    return entry if isinstance(entry, dict) else {}
