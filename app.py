from flask import Flask, request
import json
import os
import requests
import time
from datetime import datetime

app = Flask(__name__)
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

# Read ntfy config from environment (provide defaults if needed)
FILE_LOGS = os.getenv("FILE_LOGS", "false").lower() in ("1", "true", "yes")
NTFY_SERVER = os.getenv("NTFY_SERVER", "https://ntfy.freilinger.ws").rstrip("/")
NTFY_TOPIC  = os.getenv("NTFY_TOPIC", "media")
NTFY_USER   = os.getenv("NTFY_USER")      # no default for safety
NTFY_PASS   = os.getenv("NTFY_PASS")      # no default for safety
NTFY_ENABLED = os.getenv("NTFY_ENABLED", "true").lower() in ("1", "true", "yes")
NTFY_ICON   = os.getenv("NTFY_ICON", "https://freilinger.ws/jellyfin.png")


def try_parse_json_from_raw(raw_bytes):
    """Attempt to parse UTF-8 JSON regardless of Content-Type."""
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return None, None
    stripped = text.lstrip()
    if not stripped or stripped[0] not in "{[":
        return None, text
    try:
        return json.loads(text), text
    except Exception:
        return None, text

def send_ntfy(title: str, message: str, icon: str = None):
    """Send a notification to ntfy. Returns (ok: bool, status_code: int|None, error: str|None)."""
    if not NTFY_ENABLED:
        return (False, None, "disabled")

    icon_url = (icon or NTFY_ICON)

    url = f"{NTFY_SERVER}/{NTFY_TOPIC}"
    headers = {
        "Title": title,
        "Icon": icon_url,
        "X-Icon": icon_url
    }
    try:
        # ntfy expects the message as the request body
        auth = (NTFY_USER, NTFY_PASS) if (NTFY_USER and NTFY_PASS) else None
        r = requests.post(url, data=message.encode("utf-8"), headers=headers, auth=auth, timeout=5)
        return (200 <= r.status_code < 300, r.status_code, None)
    except Exception as e:
        return (False, None, str(e))

@app.route("/", methods=["POST"])
def log_post():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    base = os.path.join(log_dir, f"request_{ts}")

    raw_bytes = request.get_data(cache=False, as_text=False)

    if FILE_LOGS:
        # Persist raw bytes
        body_bin_path = f"{base}.body.bin"
        with open(body_bin_path, "wb") as bf:
            bf.write(raw_bytes)

    # Parse JSON (fallback regardless of Content-Type)
    parsed_json = request.get_json(force=False, silent=True)
    raw_text = None
    if parsed_json is None:
        parsed_json, raw_text = try_parse_json_from_raw(raw_bytes)

    # Also keep a text preview if possible
    if raw_text is None:
        try:
            raw_text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            raw_text = None

    if FILE_LOGS:
        # Pretty JSON output if parsing worked
        pretty_json_path = None
        if isinstance(parsed_json, (dict, list)):
            # Optional: nicer base name if notification fields exist
            if isinstance(parsed_json, dict):
                notif = str(parsed_json.get("NotificationType", "Event")).replace("/", "_")
                item  = str(parsed_json.get("ItemId", "noid")).replace("/", "_")
                base  = os.path.join(log_dir, f"{ts}_{notif}_{item}")
                body_bin_path = f"{base}.body.bin"  # path updated for meta naming consistency (file already written with old name)

            pretty_json_path = f"{base}.json"
            with open(pretty_json_path, "w", encoding="utf-8") as jf:
                json.dump(parsed_json, jf, indent=2, ensure_ascii=False)

    # ntfy hook: only for ItemAdded
    ntfy_result = {
        "attempted": False,
        "ok": False,
        "status_code": None,
        "error": None
    }

    if isinstance(parsed_json, dict) and parsed_json.get("NotificationType") == "ItemAdded":
        item_type = parsed_json.get("ItemType", "Item")
        title = f"New {item_type}"

        if item_type.lower() == "episode":
            icon="https://freilinger.ws/jf_tv.png"
            series = parsed_json.get("SeriesName", "")
            name = parsed_json.get("Name", "")
            season = parsed_json.get("SeasonNumber00")
            episode = parsed_json.get("EpisodeNumber00")
            message = f"{series}\n{name}\nS{season}E{episode}".strip()
        elif item_type.lower() == "movie":
            icon="https://freilinger.ws/jf_movie.png"
            name = parsed_json.get("Name", "")
            year = parsed_json.get("Year", "")
            tagline = parsed_json.get("Tagline", "")
            message = f"{name} ({year})\n{tagline}".strip()
        else:
            message = parsed_json.get("Name", "(no name)")

        ntfy_result["attempted"] = True
        ok, code, err = send_ntfy(title, message, icon=icon)
        ntfy_result.update({"ok": ok, "status_code": code, "error": err})

    if FILE_LOGS:
        # Build meta
        meta = {
            "timestamp": ts,
            "remote_addr": request.remote_addr,
            "method": request.method,
            "path": request.path,
            "query_params": request.args.to_dict(flat=False),
            "content_type": request.headers.get("Content-Type"),
            "content_length": request.content_length,
            "headers": dict(request.headers),
            "json_parsed": isinstance(parsed_json, (dict, list)),
            "raw_body_file": os.path.basename(body_bin_path),
            "pretty_json_file": os.path.basename(pretty_json_path) if pretty_json_path else None,
            "ntfy": {
                "attempted": ntfy_result["attempted"],
                "ok": ntfy_result["ok"],
                "status_code": ntfy_result["status_code"],
                "server": NTFY_SERVER,
                "topic": NTFY_TOPIC,
                "error": ntfy_result["error"],
            }
        }
        if raw_text is not None:
            meta["raw_body_preview_utf8"] = raw_text[:4000]  # limit preview

        meta_path = f"{base}.meta.json"
        with open(meta_path, "w", encoding="utf-8") as mf:
            json.dump(meta, mf, indent=2, ensure_ascii=False)

    if FILE_LOGS:
        return {"status": "ok", "meta_file": os.path.basename(meta_path)}, 200
    else:
        return {"status": "ok"}, 200


if __name__ == "__main__":
    # Bind on all interfaces, default port 8080
    app.run(host="0.0.0.0", port=8080)
