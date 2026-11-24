"""Gemeinsame Bausteine der Konformitätsprüfung: Schemas, Profil, HTTP, Signatur, Bericht, Webhook-Empfänger."""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import ssl
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[2]
API = "/bowflow/v1"
SIGNATURE_HEADER = "X-BowFlow-Signature"


# --- Schemas und Profil -----------------------------------------------------------------------
class Schemas:
    """Alle Schemas des Repos (Kern und Profile) in einer Registry."""

    def __init__(self) -> None:
        resources = []
        self.ids: dict[tuple[str, str], str] = {}
        for unit in [ROOT / "core"] + sorted((ROOT / "profiles").glob("*/")):
            for f in sorted((unit / "schemas").glob("*.schema.json")):
                s = json.loads(f.read_text())
                resources.append((s["$id"], Resource.from_contents(s)))
                self.ids[(unit.name, f.name)] = s["$id"]
        self.registry = Registry().with_resources(resources)

    def errors(self, unit: str, filename: str, instance, defname: str | None = None) -> list[str]:
        uri = self.ids[(unit, filename)] + (f"#/$defs/{defname}" if defname else "")
        validator = Draft202012Validator({"$ref": uri}, registry=self.registry)
        out = []
        for e in validator.iter_errors(instance):
            where = "/".join(str(p) for p in e.absolute_path) or "(Wurzel)"
            out.append(f"{where}: {e.message[:160]}")
        return out[:5]


def _template_regex(template: str) -> re.Pattern:
    parts = re.split(r"(\{[a-z_]+\})", template)
    rx = "".join(f"(?P<{p[1:-1]}>[^/]+)" if p.startswith("{") else re.escape(p) for p in parts)
    return re.compile(rx + r"\Z")


class Profile:
    """Liest profiles/<name>/profile.yaml."""

    def __init__(self, name: str) -> None:
        path = ROOT / "profiles" / name / "profile.yaml"
        if not path.exists():
            raise SystemExit(f"Profil '{name}' ist in diesem Repo nicht vorhanden ({path.parent})")
        self.name = name
        self.dir = path.parent
        meta = yaml.safe_load(path.read_text())
        self.objects: list[dict] = meta["objects"]
        self.snapshot: dict = meta["snapshot"]
        self._rx = [(o, _template_regex(o["path"])) for o in self.objects]

    def match(self, rest: str):
        """Pfad unterhalb von /events/{event_id} -> (Objekt, Parameter) oder None."""
        for obj, rx in self._rx:
            m = rx.match(rest)
            if m:
                return obj, m.groupdict()
        return None

    def notification_types(self) -> set[str]:
        types = set()
        for o in self.objects:
            types.add(f"{o['name']}.updated")
            if o.get("deletable"):
                types.add(f"{o['name']}.deleted")
        return types

    def example(self, filename: str):
        return json.loads((self.dir / "examples" / filename).read_text())


def snapshot_key(snapshot: dict, name: str) -> str:
    return name if name in snapshot else name + "s"


def item_matches(item: dict, params: dict) -> bool:
    for p, v in params.items():
        if p == "scoresheet_id" and item.get("scoresheet_id") != v:
            return False
        if p == "set_number" and str(item.get("set_number")) != v:
            return False
        if p == "team_id" and item.get("team", {}).get("id") != v:
            return False
    return True


def key_object(params: dict) -> dict:
    return {k: (int(v) if k == "set_number" else v) for k, v in params.items()}


def find_object(data: dict, name: str, params: dict):
    value = data.get(snapshot_key(data, name))
    if isinstance(value, list):
        return next((i for i in value if item_matches(i, params)), None)
    return value


# --- HTTP -------------------------------------------------------------------------------------
class Resp:
    def __init__(self, status: int, headers: dict, body: bytes, error: str = "") -> None:
        self.status, self.headers, self.body, self.error = status, headers, body, error

    @property
    def json(self):
        try:
            return json.loads(self.body)
        except Exception:  # noqa: BLE001
            return None

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", "replace")


def http(method: str, url: str, *, token: str | None = None, body=None, raw: bytes | None = None,
         headers: dict | None = None, timeout: float = 10, insecure: bool = False) -> Resp:
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    ctx = ssl._create_unverified_context() if insecure else None  # noqa: S323
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return Resp(r.status, dict(r.headers), r.read())
    except urllib.error.HTTPError as e:
        return Resp(e.code, dict(e.headers), e.read())
    except Exception as e:  # noqa: BLE001
        return Resp(0, {}, b"", error=str(e))


def sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def problem(code: str, message: str) -> dict:
    return {"code": code, "message": message}


# --- Bericht ----------------------------------------------------------------------------------
class Report:
    COLORS = {"OK": "32", "FEHLER": "31", "WARNUNG": "33", "ÜBERSPRUNGEN": "90", "INFO": "36"}

    def __init__(self) -> None:
        self.rows: list[tuple[str, str, str]] = []

    def _add(self, status: str, name: str, detail: str = "") -> None:
        self.rows.append((status, name, detail))
        tag = f"{status:<13}"
        if sys.stdout.isatty():
            tag = f"\033[{self.COLORS[status]}m{tag}\033[0m"
        print(f"  {tag} {name}" + (f"\n{'':15}{detail}" if detail else ""), flush=True)

    def ok(self, name, detail=""): self._add("OK", name, detail)
    def fail(self, name, detail=""): self._add("FEHLER", name, detail)
    def warn(self, name, detail=""): self._add("WARNUNG", name, detail)
    def skip(self, name, detail=""): self._add("ÜBERSPRUNGEN", name, detail)
    def info(self, name, detail=""): self._add("INFO", name, detail)

    def check(self, cond: bool, name: str, detail_on_fail: str = "") -> bool:
        (self.ok(name) if cond else self.fail(name, detail_on_fail))
        return cond

    def section(self, title: str) -> None:
        print(f"\n== {title}", flush=True)

    def summary(self) -> int:
        counts = {k: sum(1 for r in self.rows if r[0] == k) for k in self.COLORS}
        print("\n" + ", ".join(f"{v} {k}" for k, v in counts.items() if v))
        return 1 if counts["FEHLER"] else 0


# --- Webhook-Empfänger (für Prüfung der Verwaltungs-App und als Referenz-App) -----------------
class WebhookReceiver:
    """Kleiner HTTP-Server, der Webhooks unter /hook/<label> annimmt, die Signatur prüft und alles aufzeichnet."""

    def __init__(self, host: str, port: int) -> None:
        self.secrets: dict[str, str] = {}
        self.modes: dict[str, str] = {}  # label -> "ok" | "fail"
        self.deliveries: list[dict] = []
        self.on_delivery = None
        self._lock = threading.Lock()
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a): pass

            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b""
                label = self.path.rstrip("/").rsplit("/", 1)[-1]
                secret = outer.secrets.get(label)
                got = self.headers.get(SIGNATURE_HEADER, "")
                sig_ok = bool(secret) and hmac.compare_digest(got, sign(secret, raw))
                try:
                    parsed = json.loads(raw)
                except Exception:  # noqa: BLE001
                    parsed = None
                rec = {"label": label, "time": time.time(), "sig_header": got, "sig_ok": sig_ok, "raw": raw, "json": parsed}
                status = 401 if not sig_ok else (500 if outer.modes.get(label) == "fail" else 200)
                rec["status"] = status
                with outer._lock:
                    outer.deliveries.append(rec)
                if outer.on_delivery:
                    try:
                        status = outer.on_delivery(label, rec) or status
                    except Exception:  # noqa: BLE001
                        pass
                self.send_response(status)
                self.send_header("Content-Length", "0")
                self.end_headers()

        self.server = ThreadingHTTPServer((host, port), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def start(self): self.thread.start(); return self
    def stop(self): self.server.shutdown(); self.server.server_close()

    def for_label(self, label: str) -> list[dict]:
        with self._lock:
            return [d for d in self.deliveries if d["label"] == label]

    def wait_for(self, label: str, pred, timeout: float, start: int = 0):
        end = time.time() + timeout
        while time.time() < end:
            for d in self.for_label(label)[start:]:
                if pred(d):
                    return d
            time.sleep(0.1)
        return None


def wait_until(pred, timeout: float, step: float = 0.1):
    end = time.time() + timeout
    while time.time() < end:
        v = pred()
        if v:
            return v
        time.sleep(step)
    return None
