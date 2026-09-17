from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from typing import Optional

from flask import Flask, Response, abort, make_response, request


app = Flask(__name__)


def _flag(room_id: str) -> str:
    # Stable, deterministic flags for repeatable demos.
    return f"FLAG{{ZEROPATH_{room_id.upper()}_LOCAL_DEMO}}"


@dataclass(frozen=True)
class BasicCreds:
    user: str
    password: str


ROOM03_CREDS = BasicCreds(user="analyst", password="s3cur3-d3m0")


@app.get("/")
def index() -> Response:
    return make_response(
        {
            "service": "zeropath-lab",
            "rooms": [
                "room01_robots",
                "room02_dirbust",
                "room03_basic_auth",
                "room04_cookie_gate",
                "room05_header_key",
                "room06_query_puzzle",
            ],
            "note": "Local training lab only.",
        }
    )


# ---- Room 01: robots.txt reveals hidden path ----
@app.get("/room01/robots.txt")
def room01_robots() -> Response:
    body = "User-agent: *\nDisallow: /room01/hidden/\n"
    return Response(body, mimetype="text/plain")


@app.get("/room01/hidden/flag")
def room01_flag() -> Response:
    return Response(_flag("room01_robots"), mimetype="text/plain")


# ---- Room 02: basic dirbust (admin not linked) ----
@app.get("/room02/")
def room02_root() -> Response:
    return Response("<h1>Room02</h1><p>Nothing interesting here.</p>", mimetype="text/html")


@app.get("/room02/admin/flag")
def room02_admin_flag() -> Response:
    return Response(_flag("room02_dirbust"), mimetype="text/plain")


# ---- Room 03: sitemap.xml reveals debug endpoint containing creds; flag behind basic auth ----
@app.get("/room03/sitemap.xml")
def room03_sitemap() -> Response:
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>/room03/</loc></url>
  <url><loc>/room03/debug</loc></url>
</urlset>
"""
    return Response(xml, mimetype="application/xml")


@app.get("/room03/debug")
def room03_debug() -> Response:
    # Intentionally exposed in the lab.
    return make_response(
        {
            "service_user": ROOM03_CREDS.user,
            "service_pass": ROOM03_CREDS.password,
            "hint": "Use HTTP basic auth to access /room03/flag",
        }
    )


def _parse_basic_auth() -> Optional[BasicCreds]:
    h = request.headers.get("Authorization", "")
    if not h.startswith("Basic "):
        return None
    try:
        raw = base64.b64decode(h.split(" ", 1)[1]).decode("utf-8", errors="strict")
        if ":" not in raw:
            return None
        u, p = raw.split(":", 1)
        return BasicCreds(user=u, password=p)
    except Exception:
        return None


@app.get("/room03/flag")
def room03_flag() -> Response:
    creds = _parse_basic_auth()
    if not creds or creds.user != ROOM03_CREDS.user or creds.password != ROOM03_CREDS.password:
        r = Response("Unauthorized", status=401, mimetype="text/plain")
        r.headers["WWW-Authenticate"] = 'Basic realm="ZeroPath Lab"'
        return r
    return Response(_flag("room03_basic_auth"), mimetype="text/plain")


# ---- Room 04: cookie gate ----
@app.get("/room04/")
def room04_root() -> Response:
    html = """
<html><body>
  <h1>Room04</h1>
  <!-- hint: creds dev/devpass -->
  <p>Login at <code>/room04/login</code> then access <code>/room04/flag</code>.</p>
</body></html>
"""
    return Response(html, mimetype="text/html")


@app.post("/room04/login")
def room04_login() -> Response:
    data = request.get_json(silent=True) or {}
    user = str(data.get("user", ""))
    password = str(data.get("password", ""))
    if user == "dev" and password == "devpass":
        resp = Response("OK", mimetype="text/plain")
        resp.set_cookie("zp_session", "ok", httponly=True, samesite="Lax")
        return resp
    return Response("Invalid", status=403, mimetype="text/plain")


@app.get("/room04/flag")
def room04_flag() -> Response:
    if request.cookies.get("zp_session") != "ok":
        return Response("Forbidden", status=403, mimetype="text/plain")
    return Response(_flag("room04_cookie_gate"), mimetype="text/plain")


# ---- Room 05: header key (key hinted in HTML comment) ----
@app.get("/room05/")
def room05_root() -> Response:
    key = os.getenv("ZP_ROOM05_KEY", "local-demo-key")
    html = f"""
<html><body>
  <h1>Room05</h1>
  <!-- hint: X-ZP-Key = {key} -->
  <p>Keyed endpoint: /room05/flag</p>
</body></html>
"""
    return Response(html, mimetype="text/html")


@app.get("/room05/flag")
def room05_flag() -> Response:
    key = os.getenv("ZP_ROOM05_KEY", "local-demo-key")
    if request.headers.get("X-ZP-Key") != key:
        return Response("Forbidden", status=403, mimetype="text/plain")
    return Response(_flag("room05_header_key"), mimetype="text/plain")


# ---- Room 06: query puzzle (discover via content and retry) ----
@app.get("/room06/")
def room06_root() -> Response:
    return Response(
        "<h1>Room06</h1><p>Flag is at /room06/flag?answer=...</p><p>Hint: answer is 6*7.</p>",
        mimetype="text/html",
    )


@app.get("/room06/flag")
def room06_flag() -> Response:
    ans = request.args.get("answer", "")
    if ans != "42":
        abort(404)
    return Response(_flag("room06_query_puzzle"), mimetype="text/plain")


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5000"))
    app.run(host=host, port=port)

