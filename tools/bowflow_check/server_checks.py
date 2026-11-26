"""Prüft eine Verwaltungs-App (z. B. Liga App) gegen Kern und Profil."""
from __future__ import annotations

import itertools
import re

from .common import (API, Profile, Report, Schemas, WebhookReceiver, find_object, http, key_object, wait_until)

PROBLEM = ("core", "problem.schema.json")


class ServerChecker:
    def __init__(self, a, schemas: Schemas, report: Report) -> None:
        self.a, self.schemas, self.r = a, schemas, report
        self.base = a.url.rstrip("/")
        if not self.base.endswith(API):
            self.base += API
        self.receiver: WebhookReceiver | None = None

    # -- Hilfen
    def req(self, method, path, token=None, **kw):
        return http(method, self.base + path, token=token, insecure=self.a.insecure, **kw)

    def problem_ok(self, resp, status: int, code: str, name: str) -> bool:
        errs = self.schemas.errors(*PROBLEM, resp.json) if resp.json is not None else ["kein JSON-Körper"]
        good = resp.status == status and not errs and resp.json.get("code") == code
        detail = f"erwartet {status} {code}, bekommen {resp.status or resp.error} {resp.text[:120]}" + (f" ({errs[0]})" if errs else "")
        return self.r.check(good, name, detail)

    def join(self, code: str, label: str):
        webhook = f"{self.a.webhook_url.rstrip('/')}/hook/{label}"
        body = {"code": code, "app": {"name": "bowflow-check", "version": "1"}, "device_name": f"Prüfung {label}",
                "webhook_url": webhook}
        return self.req("POST", "/join", body=body)

    # -- Ablauf
    def run(self) -> None:
        r = self.r
        host, _, port = self.a.webhook_listen.rpartition(":")
        self.receiver = WebhookReceiver(host or "0.0.0.0", int(port)).start()  # noqa: S104
        try:
            self.run_checks()
        finally:
            self.receiver.stop()

    def run_checks(self) -> None:
        r = self.r
        r.section("Beitritt")
        resp = self.join(self.a.code, "A")
        if resp.status != 201:
            r.fail("POST /join mit gültigem Code ergibt 201", f"bekommen {resp.status or resp.error} {resp.text[:160]}")
            r.info("Abbruch", "ohne Beitritt sind keine weiteren Prüfungen möglich (Code abgelaufen oder schon benutzt?)")
            return
        j = resp.json or {}
        errs = self.schemas.errors("core", "join.schema.json", j, "JoinResponse")
        r.check(not errs, "Antwort entspricht JoinResponse", "; ".join(errs))
        if errs:
            return
        token, event, secret = j["token"], j["event_id"], j["webhook_secret"]
        self.receiver.secrets["A"] = secret
        try:
            profile = Profile(j["profile"])
        except SystemExit as e:
            r.fail("Profil ist in diesem Repo bekannt", str(e))
            return
        r.ok(f"Profil '{profile.name}' gefunden")
        ev = f"/events/{event}"

        self.problem_ok(self.join(self.a.code, "A2"), 401, "JOIN_CODE_INVALID", "Code ist nur einmal benutzbar (zweiter Beitritt: 401 JOIN_CODE_INVALID)")
        self.problem_ok(self.join("ZZZZZZ", "A3"), 401, "JOIN_CODE_INVALID", "Unbekannter Code ergibt 401 JOIN_CODE_INVALID (zählt als Fehlversuch)")

        r.section("Absicherung")
        self.problem_ok(self.req("GET", ev + profile.snapshot["path"]), 401, "UNAUTHORIZED", "Aufruf ohne Token ergibt 401 UNAUTHORIZED")
        self.problem_ok(self.req("GET", ev + profile.snapshot["path"], token="falsch"), 401, "UNAUTHORIZED", "Aufruf mit falschem Token ergibt 401 UNAUTHORIZED")
        self.problem_ok(self.req("GET", "/events/gibt-es-nicht" + profile.snapshot["path"], token=token), 404, "NOT_FOUND", "Unbekannter Wettkampf ergibt 404 NOT_FOUND")

        r.section("Snapshot")
        snap = self.req("GET", ev + profile.snapshot["path"], token=token)
        if snap.status != 200:
            r.fail("GET /snapshot ergibt 200", f"bekommen {snap.status or snap.error}")
            return
        snapshot = snap.json
        errs = self.schemas.errors(profile.name, profile.snapshot["schema"], snapshot)
        r.check(not errs, "Snapshot entspricht dem Schema", "; ".join(errs))
        if not isinstance(snapshot, dict) or not isinstance(snapshot.get("sequence"), int):
            return
        seq = snapshot["sequence"]
        s304 = self.req("GET", f"{ev}{profile.snapshot['path']}?since={seq}", token=token)
        r.check(s304.status == 304 and not s304.body, f"?since={seq} (aktuelle sequence) ergibt 304 ohne Body",
                f"bekommen {s304.status} mit {len(s304.body)} Bytes")
        other = seq + 1000
        s200 = self.req("GET", f"{ev}{profile.snapshot['path']}?since={other}", token=token)
        r.check(s200.status == 200 and not self.schemas.errors(profile.name, profile.snapshot["schema"], s200.json),
                f"?since={other} (andere Nummer) ergibt den vollständigen Snapshot", f"bekommen {s200.status}")

        r.section("Objekte lesen")
        self.read_objects(profile, ev, token, snapshot)

        r.section("Schreibschutz")
        ro = next((o for o in profile.objects if o["access"] == "read" and "{" not in o["path"]), None)
        if ro:
            if self.a.write:
                self.problem_ok(self.req("PUT", ev + ro["path"], token=token, body={}), 403, "FORBIDDEN", f"PUT auf das nur lesbare Objekt {ro['name']} ergibt 403 FORBIDDEN")
            else:
                r.skip(f"PUT auf nur lesbares Objekt {ro['name']} ergibt 403", "nur mit --write (ein fehlerhafter Server könnte das Objekt überschreiben)")

        if not self.a.write:
            r.section("Schreiben und Benachrichtigungen")
            r.skip("PUT, DELETE und Webhooks", "nur mit --write (ändert Daten der Anwendung; nur gegen eine Entwicklungs- oder Testinstanz verwenden)")
            return
        self.write_checks(profile, ev, token, snapshot)

    # -- Lesen
    def candidates(self, snapshot: dict, params: list[str]):
        plan = snapshot.get("competition_plan") or {}
        scoresheets = [s for m in plan.get("matches", []) for s in m.get("scoresheets", [])]
        pools = {"scoresheet_id": [s["id"] for s in scoresheets[:1]],
                 "team_id": sorted({s["team"]["id"] for s in scoresheets})[:1],
                 "set_number": ["1"]}
        lists = [pools.get(p, []) for p in params]
        return [dict(zip(params, combo)) for combo in itertools.product(*lists)]

    def read_objects(self, profile: Profile, ev: str, token: str, snapshot: dict) -> None:
        r = self.r
        for obj in profile.objects:
            names = re.findall(r"\{([a-z_]+)\}", obj["path"])
            combos = self.candidates(snapshot, names) if names else [{}]
            if not combos:
                r.skip(f"GET {obj['path']}", "keine passenden IDs im Snapshot")
                continue
            for params in combos[:1]:
                path = obj["path"]
                for k, v in params.items():
                    path = path.replace("{" + k + "}", v)
                resp = self.req("GET", ev + path, token=token)
                label = f"GET {path} ({obj['name']})"
                if resp.status == 200:
                    errs = self.schemas.errors(profile.name, obj["schema"], resp.json)
                    r.check(not errs, label + " entspricht dem Schema", "; ".join(errs))
                    for k, v in params.items():
                        if isinstance(resp.json, dict) and k in resp.json and str(resp.json[k]) != v:
                            r.fail(label + f": {k} im Objekt weicht vom Pfad ab")
                elif resp.status == 404:
                    self.problem_ok(resp, 404, "NOT_FOUND", label + " (noch nicht vorhanden): 404 NOT_FOUND")
                else:
                    r.fail(label, f"erwartet 200 oder 404, bekommen {resp.status or resp.error}")

    # -- Schreiben
    def write_checks(self, profile: Profile, ev: str, token: str, snapshot: dict) -> None:
        r = self.r
        r.section("Schreiben")
        lineup = next((o for o in profile.objects if o["name"] == "lineup"), None)
        state = next((o for o in profile.objects if o["name"] == "event_state"), None)
        plan = snapshot.get("competition_plan") or {}
        scoresheets = [s["id"] for m in plan.get("matches", []) for s in m.get("scoresheets", [])]
        if state:
            cur = self.req("GET", ev + state["path"], token=token).json
            if cur is not None:
                put = self.req("PUT", ev + state["path"], token=token, body=cur)
                r.check(put.status == 200 and put.json == cur, "PUT /state mit dem unveränderten Objekt ergibt 200 und liefert es zurück",
                        f"bekommen {put.status or put.error}")
                bad = self.req("PUT", ev + state["path"], token=token, body={"state": "UNGUELTIG"})
                self.problem_ok(bad, 422, "VALIDATION_FAILED", "PUT /state mit ungültigem Objekt ergibt 422 VALIDATION_FAILED")
        if not (lineup and scoresheets):
            r.skip("Meldung schreiben", "Objekt lineup oder Schusszettel fehlt")
            return
        sid = next((i for i in scoresheets if self.req("GET", ev + lineup["path"].replace("{scoresheet_id}", i), token=token).status == 404), None)
        if sid is None:
            r.skip("Meldung anlegen und löschen", "für alle Schusszettel ist schon eine Meldung vorhanden, sie bleiben unangetastet")
            return
        path = ev + lineup["path"].replace("{scoresheet_id}", sid)
        body = profile.example("lineup.json")
        body["scoresheet_id"] = sid
        wrong = dict(body, scoresheet_id=sid + "-x")
        self.problem_ok(self.req("PUT", path, token=token, body=wrong), 422, "VALIDATION_FAILED", "PUT mit abweichender scoresheet_id im Objekt ergibt 422 VALIDATION_FAILED")
        self.problem_ok(self.req("PUT", path, token=token, body={"athletes": []}), 422, "VALIDATION_FAILED", "PUT mit ungültiger Meldung ergibt 422 VALIDATION_FAILED")

        observer = None
        if self.a.code2:
            observer = self.join_observer(profile, ev)

        put = self.req("PUT", path, token=token, body=body)
        r.check(put.status == 200 and put.json == body, "PUT Meldung ergibt 200 und liefert das Objekt zurück", f"bekommen {put.status or put.error} {put.text[:120]}")
        got = self.req("GET", path, token=token)
        r.check(got.status == 200 and got.json == body, "GET liefert danach die geschriebene Meldung")
        if observer:
            self.observe(observer, "lineup.updated", body, "Webhook nach PUT")
        dele = self.req("DELETE", path, token=token)
        r.check(dele.status == 204, "DELETE Meldung ergibt 204", f"bekommen {dele.status or dele.error}")
        self.problem_ok(self.req("GET", path, token=token), 404, "NOT_FOUND", "GET nach DELETE ergibt 404 NOT_FOUND")
        if observer:
            self.observe(observer, "lineup.deleted", key_object({"scoresheet_id": sid}), "Webhook nach DELETE")
            self.observer_checks(observer, profile, ev, token, path, body)

    # -- Zweite App: Webhooks beobachten
    def join_observer(self, profile: Profile, ev: str):
        r = self.r
        r.section("Zweite App (Webhooks)")
        resp = self.join(self.a.code2, "B")
        if resp.status != 201:
            r.fail("Beitritt der zweiten App", f"bekommen {resp.status or resp.error} {resp.text[:120]}")
            return None
        j = resp.json
        self.receiver.secrets["B"] = j["webhook_secret"]
        snap = self.req("GET", ev + profile.snapshot["path"], token=j["token"]).json or {}
        return {"token": j["token"], "last": snap.get("sequence", 0), "n": 0}

    def observe(self, obs: dict, ntype: str, obj, label: str) -> None:
        r = self.r
        d = self.receiver.wait_for("B", lambda d: True, 10, start=obs["n"])
        if not d:
            r.fail(f"{label}: zweite App bekommt eine Benachrichtigung ({ntype})", "innerhalb von 10 s nichts angekommen")
            return
        obs["n"] = len(self.receiver.for_label("B"))
        r.check(d["sig_ok"], f"{label}: Signatur X-BowFlow-Signature gültig", f"Header: {d['sig_header'][:40]!r}")
        note = d["json"]
        errs = self.schemas.errors("core", "notification.schema.json", note) if note is not None else ["kein JSON"]
        r.check(not errs, f"{label}: Benachrichtigung entspricht dem Schema", "; ".join(errs))
        if errs or not note:
            return
        r.check(note["type"] == ntype, f"{label}: type ist {ntype}", f"bekommen {note['type']}")
        r.check(note["object"] == obj, f"{label}: object entspricht dem geschriebenen Objekt", f"bekommen {str(note['object'])[:120]}")
        r.check(note["sequence"] == obs["last"] + 1, f"{label}: sequence ist lückenlos (erwartet {obs['last'] + 1})", f"bekommen {note['sequence']}")
        obs["last"] = note["sequence"]

    def observer_checks(self, obs: dict, profile: Profile, ev: str, token: str, path: str, body) -> None:
        r = self.r
        a_hooks = self.receiver.for_label("A")
        r.check(not a_hooks, "Die schreibende App bekommt keine eigene Benachrichtigung", f"{len(a_hooks)} Webhooks an die Schreiberin")
        snap = self.req("GET", f"{ev}{profile.snapshot['path']}?since={obs['last']}", token=obs["token"])
        r.check(snap.status == 304, f"Snapshot ?since={obs['last']} ergibt 304, wenn alles zugestellt ist", f"bekommen {snap.status}")
        if self.a.slow:
            self.queue_discard_check(obs, profile, ev, token, path, body)
        else:
            r.skip("Warteschlange nach Snapshot verwerfen", "nur mit --slow (wartet auf Wiederholungen, dauert etwa 15 s)")

    def queue_discard_check(self, obs, profile, ev, token, path, body) -> None:
        """B nimmt Webhooks nicht an, A schreibt dreimal, B holt den Snapshot -> wartende Webhooks müssen entfallen."""
        r = self.r
        self.receiver.modes["B"] = "fail"
        start = len(self.receiver.for_label("B"))
        for _ in range(3):
            self.req("PUT", path, token=token, body=body)
            self.req("DELETE", path, token=token)
        snap = self.req("GET", ev + profile.snapshot["path"], token=obs["token"])
        seq = (snap.json or {}).get("sequence")
        if snap.status != 200 or not isinstance(seq, int):
            r.fail("Snapshot der zweiten App", f"bekommen {snap.status}")
            return
        self.receiver.modes["B"] = "ok"
        marker = len(self.receiver.for_label("B"))
        wait_until(lambda: False, 9)  # erste Wiederholung nach 5 s abwarten
        late = [d["json"]["sequence"] for d in self.receiver.for_label("B")[marker:] if isinstance(d["json"], dict)
                and isinstance(d["json"].get("sequence"), int) and d["json"]["sequence"] <= seq]
        r.check(not late, f"Nach dem Snapshot (sequence {seq}) werden wartende Benachrichtigungen ≤ {seq} nicht mehr zugestellt",
                f"trotzdem zugestellt: {late}")
