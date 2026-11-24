"""Mock-Verwaltungs-App (Referenz) und Referenz-App (verbundene App).

Die Mock-Verwaltungs-App setzt die Regeln des Kerns und des Profils um und dient
  * im Modus `client` als Gegenstelle für eine verbundene App und
  * im `selftest` als Referenz, gegen die die Prüfung der Verwaltungs-App läuft.
"""
from __future__ import annotations

import copy
import json
import re
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .common import (API, Profile, Schemas, SIGNATURE_HEADER, WebhookReceiver, find_object, http, item_matches,
                     key_object, now_iso, problem, sign, snapshot_key, wait_until)

SPEC_RETRY = [5, 30, 120, 600, 1800, 3600]


class App:
    def __init__(self, app_id: str, token: str, secret: str, webhook_url: str, request: dict) -> None:
        self.app_id, self.token, self.secret, self.webhook_url, self.request = app_id, token, secret, webhook_url, request
        self.seq = 0
        self.discard_upto = 0
        self.queue: list[tuple[int, dict]] = []
        self.cv = threading.Condition()


class MockManagement:
    def __init__(self, profile: Profile, schemas: Schemas, *, event_id: str = "ev_42", codes=(), retry=None,
                 deliver: bool = True) -> None:
        self.profile, self.schemas, self.event_id = profile, schemas, event_id
        snap = profile.example("snapshot.json")
        snap.pop("sequence", None)
        self.data = snap
        self.codes = {c.upper() for c in codes}
        self.retry = retry or SPEC_RETRY
        self.deliver = deliver
        self.apps: dict[str, App] = {}
        self.log: list[dict] = []
        self.joined = threading.Event()
        self.lock = threading.RLock()
        self.stop_flag = False

    # -- Hilfen
    def add_code(self, code: str) -> None:
        self.codes.add(code.upper())

    def _log(self, **kw) -> None:
        kw["time"] = time.time()
        with self.lock:
            self.log.append(kw)

    def count(self, kind: str) -> int:
        with self.lock:
            return sum(1 for e in self.log if e.get("kind") == kind)

    # -- Anfragebearbeitung
    def handle(self, method: str, path: str, query: dict, headers, raw: bytes):
        status, body, app, kind = self._route(method, path, query, headers, raw)
        entry = dict(method=method, path=path, status=status, app=app.app_id if app else None, kind=kind,
                     authorization=bool(headers.get("Authorization")))
        if method in ("PUT", "POST"):
            try:
                entry["body"] = json.loads(raw) if raw else None
            except Exception:  # noqa: BLE001
                entry["body"] = None
        self._log(**entry)
        return status, body

    def _route(self, method, path, query, headers, raw):
        if not path.startswith(API):
            return 404, problem("NOT_FOUND", "Pfad unbekannt"), None, "other"
        p = path[len(API):]
        if method == "POST" and p == "/join":
            s, b = self._join(raw)
            return s, b, None, "join"
        app = self._auth(headers)
        if not app:
            return 401, problem("UNAUTHORIZED", "Token fehlt oder ist ungültig"), None, "other"
        m = re.fullmatch(r"/events/([^/]+)(/.*)", p)
        if not m or m.group(1) != self.event_id:
            return 404, problem("NOT_FOUND", "Wettkampf unbekannt"), app, "other"
        rest = m.group(2)
        if rest == self.profile.snapshot["path"] and method == "GET":
            s, b = self._snapshot(app, query)
            return s, b, app, "snapshot"
        hit = self.profile.match(rest)
        if not hit:
            return 404, problem("NOT_FOUND", "Objekt unbekannt"), app, "other"
        obj, params = hit
        s, b = self._object(app, method, obj, params, raw)
        return s, b, app, "object"

    def _auth(self, headers):
        h = headers.get("Authorization", "")
        tok = h[7:] if h.startswith("Bearer ") else ""
        return next((a for a in self.apps.values() if a.token == tok), None) if tok else None

    def _join(self, raw: bytes):
        try:
            req = json.loads(raw)
        except Exception:  # noqa: BLE001
            return 422, problem("VALIDATION_FAILED", "Kein JSON")
        errs = self.schemas.errors("core", "join.schema.json", req, "JoinRequest")
        if errs:
            return 422, problem("VALIDATION_FAILED", "; ".join(errs))
        with self.lock:
            code = req["code"].upper()
            if code not in self.codes:
                return 401, problem("JOIN_CODE_INVALID", "Code ungültig, abgelaufen oder benutzt")
            self.codes.discard(code)
            n = len(self.apps) + 1
            app = App(f"app_{n}", "tok_" + secrets.token_hex(8), "whs_" + secrets.token_hex(8), req["webhook_url"], req)
            self.apps[app.app_id] = app
        if self.deliver:
            threading.Thread(target=self._worker, args=(app,), daemon=True).start()
        self.joined.set()
        return 201, {"event_id": self.event_id, "profile": self.profile.name, "app_id": app.app_id, "token": app.token,
                     "expires_at": "2099-12-31T23:59:59+00:00", "webhook_secret": app.secret}

    def _snapshot(self, app: App, query: dict):
        with self.lock:
            since = (query.get("since") or [None])[0]
            if since is not None:
                try:
                    if int(since) == app.seq:
                        return 304, None
                except ValueError:
                    return 422, problem("VALIDATION_FAILED", "since ist keine Zahl")
            snap = copy.deepcopy(self.data)
            snap["sequence"] = app.seq
        with app.cv:
            app.discard_upto = max(app.discard_upto, snap["sequence"])
            app.cv.notify_all()
        return 200, snap

    def _object(self, app: App, method: str, obj: dict, params: dict, raw: bytes):
        name = obj["name"]
        with self.lock:
            current = find_object(self.data, name, params)
            if method == "GET":
                return (200, copy.deepcopy(current)) if current is not None else (404, problem("NOT_FOUND", "noch nicht vorhanden"))
            if method == "PUT":
                if obj["access"] == "read":
                    return 403, problem("FORBIDDEN", "Objekt ist nur lesbar")
                try:
                    body = json.loads(raw)
                except Exception:  # noqa: BLE001
                    return 422, problem("VALIDATION_FAILED", "Kein JSON")
                errs = self.schemas.errors(self.profile.name, obj["schema"], body)
                if errs:
                    return 422, problem("VALIDATION_FAILED", "; ".join(errs))
                for k, v in params.items():
                    if str(body.get(k)) != v:
                        return 422, problem("VALIDATION_FAILED", f"{k} im Objekt weicht vom Pfad ab")
                self._store(name, params, body)
                self._publish(app, f"{name}.updated", body)
                return 200, body
            if method == "DELETE":
                if not obj.get("deletable"):
                    return 403, problem("FORBIDDEN", "Objekt ist nicht löschbar")
                if current is None:
                    return 404, problem("NOT_FOUND", "nicht vorhanden")
                self._store(name, params, None)
                self._publish(app, f"{name}.deleted", key_object(params))
                return 204, None
        return 404, problem("NOT_FOUND", "Methode unbekannt")

    def _store(self, name: str, params: dict, body) -> None:
        key = snapshot_key(self.data, name)
        cur = self.data.get(key)
        if isinstance(cur, list):
            rest = [i for i in cur if not item_matches(i, params)]
            self.data[key] = rest + ([body] if body is not None else [])
        else:
            self.data[key] = body

    # -- Benachrichtigungen
    def _publish(self, origin: App | None, ntype: str, obj: dict) -> None:
        for app in list(self.apps.values()):
            if app is origin:
                continue
            with app.cv:
                app.seq += 1
                app.queue.append((app.seq, {"sequence": app.seq, "sent_at": now_iso(), "event_id": self.event_id,
                                             "type": ntype, "object": obj}))
                app.cv.notify_all()

    def _worker(self, app: App) -> None:
        attempt = 0
        while not self.stop_flag:
            with app.cv:
                app.queue = [q for q in app.queue if q[0] > app.discard_upto]
                while not app.queue and not self.stop_flag:
                    app.cv.wait(0.5)
                    app.queue = [q for q in app.queue if q[0] > app.discard_upto]
                if self.stop_flag:
                    return
                seq, note = app.queue[0]
            ok = self.send(app, note)
            with app.cv:
                if ok:
                    app.queue = [q for q in app.queue if q[0] != seq]
                    attempt = 0
                    continue
            delay = self.retry[min(attempt, len(self.retry) - 1)]
            attempt += 1
            end = time.time() + delay
            while time.time() < end and not self.stop_flag:
                time.sleep(0.1)

    def send(self, app: App, note: dict) -> bool:
        return 200 <= self.send_status(app, note) < 300

    def send_status(self, app: App, note: dict, *, signature: str | None = None) -> int:
        """Wie send, gibt aber den HTTP-Status zurück (0 = keine Verbindung). Für Prüfungen der verbundenen App."""
        raw = json.dumps(note).encode()
        r = http("POST", app.webhook_url, raw=raw, timeout=10,
                 headers={SIGNATURE_HEADER: signature if signature is not None else sign(app.secret, raw)})
        return r.status

    def stop(self) -> None:
        self.stop_flag = True
        for a in self.apps.values():
            with a.cv:
                a.cv.notify_all()


def serve(mgmt: MockManagement, host: str, port: int) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a): pass

        def _go(self, method):
            u = urlparse(self.path)
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b""
            status, body = mgmt.handle(method, u.path, parse_qs(u.query), self.headers, raw)
            payload = b"" if body is None else json.dumps(body).encode()
            self.send_response(status)
            if payload:
                self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            if payload and method != "HEAD":
                self.wfile.write(payload)

        def do_GET(self): self._go("GET")
        def do_PUT(self): self._go("PUT")
        def do_POST(self): self._go("POST")
        def do_DELETE(self): self._go("DELETE")

    srv = ThreadingHTTPServer((host, port), Handler)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


class ReferenceApp:
    """Kleine verbundene App, die die Regeln des Kerns einhält. Für den Selbsttest des Modus `client`."""

    def __init__(self, base_url: str, code: str, receiver_host: str, receiver_port: int, safety_net: float = 65) -> None:
        self.base, self.code, self.safety_net = base_url.rstrip("/") + API, code, safety_net
        self.receiver = WebhookReceiver(receiver_host, receiver_port)
        self.receiver.on_delivery = self._on_delivery
        self.url = f"http://127.0.0.1:{receiver_port}"
        self.last = 0
        self.token = self.event = ""
        self.stop = threading.Event()

    def start(self):
        self.receiver.start()
        r = http("POST", self.base + "/join", body={"code": self.code, "app": {"name": "Referenz-App", "version": "1"},
                                                     "webhook_url": self.url + "/hook/app"})
        j = r.json
        self.token, self.event = j["token"], j["event_id"]
        self.receiver.secrets["app"] = j["webhook_secret"]
        self._snapshot()
        threading.Thread(target=self._loop, daemon=True).start()
        return self

    def _snapshot(self) -> None:
        r = http("GET", f"{self.base}/events/{self.event}/snapshot" + (f"?since={self.last}" if self.last else ""),
                 token=self.token)
        if r.status == 200:
            self.last = r.json["sequence"]

    def _loop(self) -> None:
        while not self.stop.wait(self.safety_net):
            self._snapshot()

    def _on_delivery(self, label, rec):
        j = rec["json"] or {}
        seq = j.get("sequence")
        if not rec["sig_ok"] or not isinstance(seq, int):
            return None
        if seq <= self.last:
            return 200
        if seq > self.last + 1:
            threading.Thread(target=self._snapshot, daemon=True).start()
        else:
            self.last = seq
        return 200

    def close(self) -> None:
        self.stop.set()
        self.receiver.stop()
