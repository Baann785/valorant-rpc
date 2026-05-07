import logging
import re
import secrets
from html import escape
from urllib.parse import quote, urlencode, urlparse

from flask import Flask, jsonify, make_response, request
from werkzeug.serving import make_server

from ..utilities.logging import Logger


app = Flask(__name__)
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

client = None
config = None
action_token = None
http_server = None
SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def configure(client_obj, config_obj, token=None):
    global client, config, action_token
    client = client_obj
    config = config_obj
    action_token = token or secrets.token_urlsafe(32)
    return action_token


def configured_port(config_obj=None):
    config_source = config_obj if isinstance(config_obj, dict) else config
    if isinstance(config_source, dict):
        return int(config_source.get("webserver", {}).get("port", 4100))
    return 4100


def build_confirm_url(action, party_id, region, config_obj=None, friend_id=None):
    if action not in {"join", "request"} or not is_safe_identifier(party_id):
        return None

    query = urlencode({"region": region or ""})
    party = quote(str(party_id), safe="")
    base = f"http://127.0.0.1:{configured_port(config_obj)}"

    if action == "join":
        return f"{base}/valorant/confirm/join/{party}?{query}"

    if not is_safe_identifier(friend_id):
        return None

    friend = quote(str(friend_id), safe="")
    return f"{base}/valorant/confirm/request/{party}/{friend}?{query}"


def is_safe_identifier(value):
    return isinstance(value, str) and bool(SAFE_IDENTIFIER.fullmatch(value))


@app.after_request
def add_security_headers(response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'"
    return response


def get_request_value(name):
    if name in request.args:
        return request.args.get(name)

    payload = request.get_json(silent=True)
    if isinstance(payload, dict) and name in payload:
        return payload.get(name)

    if name in request.form:
        return request.form.get(name)

    return None


def token_is_valid():
    supplied_token = request.headers.get("X-Valorant-Rpc-Token") or get_request_value("token")
    return bool(action_token and supplied_token == action_token)


def same_origin_is_valid():
    for header in ("Origin", "Referer"):
        value = request.headers.get(header)
        if not value:
            continue

        parsed = urlparse(value)
        if parsed.netloc and parsed.netloc != request.host:
            return False

    return True


def require_ready():
    if client is None:
        return jsonify({"error": "client_not_ready"}), 503

    if not token_is_valid():
        return jsonify({"error": "invalid_token"}), 403

    if request.method == "POST" and not same_origin_is_valid():
        return jsonify({"error": "invalid_origin"}), 403

    return None


def require_region():
    region = get_request_value("region")
    if region != client.region:
        return jsonify({
            "error": "wrong_region",
            "their_region": region,
            "your_region": client.region,
        }), 409

    return None


def require_identifier(name, value):
    if not is_safe_identifier(value):
        return jsonify({"error": "invalid_identifier", "field": name}), 400
    return None


def html_page(title, body, status=200):
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    body {{ background: #111; color: #f5f5f5; font-family: Segoe UI, Arial, sans-serif; margin: 0; min-height: 100vh; display: grid; place-items: center; }}
    main {{ width: min(560px, calc(100vw - 32px)); border: 1px solid #333; border-radius: 8px; padding: 24px; background: #181818; }}
    h1 {{ font-size: 22px; margin: 0 0 12px; }}
    p {{ color: #cfcfcf; line-height: 1.45; }}
    code {{ color: #fff; word-break: break-all; }}
    button, a {{ display: inline-block; margin-top: 12px; border: 0; border-radius: 6px; padding: 10px 14px; background: #ff4655; color: white; text-decoration: none; font-weight: 600; cursor: pointer; }}
  </style>
</head>
<body>
  <main>{body}</main>
</body>
</html>"""
    return make_response(html, status)


def error_page(title, message, status):
    return html_page(
        title,
        f"<h1>{escape(title)}</h1><p>{escape(message)}</p>",
        status,
    )


def confirm_page(action, party_id, friend_id=None):
    if client is None or action_token is None:
        return error_page("VALORANT RPC not ready", "The local RPC server is not ready yet.", 503)

    error = require_identifier("party_id", party_id) or require_region()
    if error:
        return error

    if action == "request":
        friend_error = require_identifier("friend_id", friend_id)
        if friend_error:
            return friend_error
        action_path = f"/valorant/request/{quote(party_id, safe='')}/{quote(friend_id, safe='')}"
        heading = "Request to join this VALORANT party?"
        description = "This will send a join request from your Riot account after you confirm."
        button = "Send request"
    else:
        action_path = f"/valorant/join/{quote(party_id, safe='')}"
        heading = "Join this VALORANT party?"
        description = "This will join the party from your Riot account after you confirm."
        button = "Join party"

    region = get_request_value("region") or ""
    body = f"""
<h1>{escape(heading)}</h1>
<p>{escape(description)}</p>
<p>Party: <code>{escape(party_id)}</code><br>Region: <code>{escape(region)}</code></p>
<form method="post" action="{escape(action_path)}">
  <input type="hidden" name="token" value="{escape(action_token)}">
  <input type="hidden" name="region" value="{escape(region)}">
  <button type="submit">{escape(button)}</button>
</form>"""
    return html_page("Confirm VALORANT party action", body)


@app.route('/')
def home():
    return jsonify({"status": "ok"})


@app.route('/valorant/confirm/join/<party_id>', methods=["GET"])
def confirm_join_party(party_id):
    return confirm_page("join", party_id)


@app.route('/valorant/confirm/request/<party_id>/<friend_id>', methods=["GET"])
def confirm_request_party(party_id, friend_id):
    return confirm_page("request", party_id, friend_id)


@app.route('/valorant/request/<party_id>/<friend_id>', methods=["POST"])
def request_party(party_id, friend_id):
    error = require_ready() or require_identifier("party_id", party_id) or require_identifier("friend_id", friend_id) or require_region()
    if error:
        return error

    try:
        data = client.party_request_to_join(party_id, friend_id)
        for player in data.get("Requests", []):
            if client.puuid == player.get("RequestedBySubject"):
                return jsonify({"status": "ok"})
        return jsonify(data)
    except Exception:
        Logger.exception("Unable to request party join")
        return jsonify({"error": "request_failed"}), 500


@app.route('/valorant/join/<party_id>', methods=["POST"])
def join_party(party_id):
    error = require_ready() or require_identifier("party_id", party_id) or require_region()
    if error:
        return error

    try:
        data = client.party_join(party_id)
        if "CurrentPartyID" in data:
            return jsonify({"status": "ok"})
        return jsonify(data)
    except Exception:
        Logger.exception("Unable to join party")
        return jsonify({"error": "join_failed"}), 500


def start(host="127.0.0.1", port=4100):
    global http_server
    http_server = make_server(host, port, app)
    try:
        http_server.serve_forever()
    finally:
        http_server = None


def stop():
    if http_server is not None:
        http_server.shutdown()
