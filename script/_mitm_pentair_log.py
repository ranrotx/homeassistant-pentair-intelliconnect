r"""mitmproxy addon: log the Pentair app's API traffic, with auth material redacted.

Used to capture commands the cloud does not store as fields (e.g. starting or
stopping an IntelliFlo program). Writes ``_mitm_pentair_log.log`` next to this
file. Pass ``--allow-hosts`` so only Pentair/AWS API hosts are decrypted; every
other host is tunnelled untouched, and its hostname is only noted if it looks
Pentair/AWS-related, so an unexpected command endpoint still shows up::

    uvx --from mitmproxy mitmdump -s script/_mitm_pentair_log.py \
        --allow-hosts 'pentair|execute-api|\.iot\.|mitm\.it'

See ``docs/intelliconnect-program-control.md`` for the full capture procedure.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
import re
from typing import Any

from mitmproxy import http, tls

LOG = Path(__file__).with_suffix(".log")
RELEVANT = re.compile(r"pentair|amazonaws|aws|iot", re.IGNORECASE)
REDACT_HEADERS = {"authorization", "x-amz-security-token", "cookie", "set-cookie", "x-amz-date"}
REDACT_KEYS = re.compile(r"token|password|secret|srp|session|credential|accesskey", re.IGNORECASE)


def _ts() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%H:%M:%S.%f")[:-3]


def _write(line: str) -> None:
    with LOG.open("a") as f:
        f.write(line + "\n")


def _redact(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: ("<redacted>" if REDACT_KEYS.search(k) else _redact(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_redact(v) for v in obj]
    return obj


def _scrub(text: str, limit: int) -> str:
    try:
        return json.dumps(_redact(json.loads(text)))[:limit]
    except ValueError:
        return text[:limit]


def tls_clienthello(data: tls.ClientHelloData) -> None:
    """Note relevant hostnames, including ones that are only tunnelled."""
    sni = data.client_hello.sni or ""
    if RELEVANT.search(sni):
        _write(f"{_ts()} TLS  {sni}")


def tls_failed_client(data: tls.TlsData) -> None:
    """Flag a rejected certificate (CA not trusted, or the app pins certificates)."""
    sni = data.conn.sni or ""
    if RELEVANT.search(sni):
        _write(f"{_ts()} TLS-FAIL {sni}: {data.conn.error}")


def request(flow: http.HTTPFlow) -> None:
    """Log method, URL, redacted headers and body."""
    r = flow.request
    headers = {k: ("<redacted>" if k.lower() in REDACT_HEADERS else v) for k, v in r.headers.items()}
    _write(f"{_ts()} >>> {r.method} {r.pretty_url}")
    _write(f"         headers={json.dumps(headers)}")
    if body := _scrub(r.get_text(strict=False) or "", 4000):
        _write(f"         body={body}")


def response(flow: http.HTTPFlow) -> None:
    """Log status and redacted body."""
    if flow.response is None:
        return
    _write(f"{_ts()} <<< {flow.response.status_code} {flow.request.method} {flow.request.pretty_url}")
    if body := _scrub(flow.response.get_text(strict=False) or "", 1500):
        _write(f"         body={body}")


def websocket_message(flow: http.HTTPFlow) -> None:
    """Log each WebSocket frame in either direction."""
    if flow.websocket is None:
        return
    msg = flow.websocket.messages[-1]
    direction = "WS>>" if msg.from_client else "WS<<"
    text = msg.text if msg.is_text else f"<binary {len(msg.content)}B> {msg.content[:200]!r}"
    _write(f"{_ts()} {direction} {flow.request.pretty_host} {_scrub(text, 3000)}")
