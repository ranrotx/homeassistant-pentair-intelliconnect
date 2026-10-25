"""Read-only field-diff capture: poll one device's REST snapshot and print every change.

Logs in with the credentials of the dev instance's pentair_pool config entry
(``config/.storage/core.config_entries``) and never writes to the controller.
Run it inside the devcontainer while you drive the Pentair app, then read the
diff to see which stored fields an app action touches::

    source /home/vscode/ha-venv/bin/activate
    python script/_field_diff.py <device_id> [interval_s=4] [duration_s=1500]

An app action that changes nothing here (e.g. starting/stopping a pump program)
is a transient command rather than a stored field; capture the app's own
traffic instead (see ``script/_mitm_pentair_log.py``).
"""

from __future__ import annotations

import asyncio
import datetime
import json
from pathlib import Path
import sys

import aiohttp

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from custom_components.pentair_pool.api.client import PentairPoolApiClient  # noqa: E402

# Fields that churn constantly and drown out the signal.
NOISE = {"appuse", "ecs2"}


def _now() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%H:%M:%S")


def _credentials() -> dict[str, str]:
    entries = json.loads((REPO / "config/.storage/core.config_entries").read_text())
    return next(e for e in entries["data"]["entries"] if e["domain"] == "pentair_pool")["data"]


async def _snapshot(client: PentairPoolApiClient, device_id: str) -> dict[str, tuple[str, str]]:
    full = await client.async_get_device(device_id)
    resp = full.get("response") or {}
    data = resp.get("data") if isinstance(resp, dict) else resp
    fields = data[0].get("fields", {}) if data else {}
    return {code: (str(f.get("value")), str(f.get("name"))) for code, f in fields.items()}


async def main(device_id: str, interval: float, duration: float) -> None:
    """Print a baseline, then one line per field value change."""
    creds = _credentials()
    async with aiohttp.ClientSession() as session:
        client = PentairPoolApiClient(creds["username"], creds["password"], session)
        await client.async_login()
        prev = await _snapshot(client, device_id)
        print(_now(), "baseline", json.dumps({k: v[0] for k, v in sorted(prev.items())}), flush=True)
        loop = asyncio.get_running_loop()
        end = loop.time() + duration
        while loop.time() < end:
            await asyncio.sleep(interval)
            try:
                cur = await _snapshot(client, device_id)
            except Exception as err:  # noqa: BLE001
                print(_now(), "ERR", err, flush=True)
                continue
            for code in sorted(set(cur) | set(prev)):
                if code in NOISE:
                    continue
                old = prev.get(code, ("<none>", ""))[0]
                new = cur.get(code, ("<none>", ""))[0]
                if old != new:
                    name = (cur.get(code) or prev[code])[1]
                    print(f"{_now()} {code:6} {name:32} {old!r} -> {new!r}", flush=True)
            prev = cur


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    asyncio.run(
        main(
            args[0],
            float(args[1]) if len(args) > 1 else 4,
            float(args[2]) if len(args) > 2 else 1500,
        )
    )
