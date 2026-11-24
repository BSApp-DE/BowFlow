"""Prüft eine verbundene App (z. B. Scoring App, Spotter App): Das Tool spielt die Verwaltungs-App."""
from __future__ import annotations

import copy
import random
import time

import yaml

from .common import API, Profile, Report, Schemas, sign, wait_until
from .mock import MockManagement, serve

CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def new_code() -> str:
    return "".join(random.choice(CODE_CHARS) for _ in range(6))


class ClientChecker:
    def __init__(self, a, schemas: Schemas, report: Report) -> None:
        self.a, self.schemas, self.r = a, schemas, report

    def run(self) -> None:
        r, a = self.r, self.a
        profile = Profile(a.profile)
        code = a.code or new_code()
        mgmt = MockManagement(profile, self.schemas, codes=[code], retry=[1, 1, 1], deliver=False)
        host, _, port = a.listen.rpartition(":")
        srv = serve(mgmt, host or "0.0.0.0", int(port))  # noqa: S104
        public = (a.public_url or f"http://localhost:{port}").rstrip("/")
        print(f"\nMock-Verwaltungs-App läuft (Profil {profile.name}, Wettkampf {mgmt.event_id}).")
        print("Trage in der zu prüfenden App ein:")
        print(f"    Adresse der Verwaltungs-App: {public}")
        print(f"    Beitrittscode:               {code}")
        print(f"    (Basis-Pfad der API: {public}{API})")
        print(f"Warte bis zu {a.wait_join} s auf den Beitritt ...", flush=True)
        try:
            if not mgmt.joined.wait(a.wait_join):
                r.section("Beitritt")
                r.fail("Die App ist beigetreten", f"innerhalb von {a.wait_join} s kein POST /join angekommen")
                return
            self.run_checks(mgmt, profile)
        finally:
            mgmt.stop()
            srv.shutdown()
            srv.server_close()

    def run_checks(self, mgmt: MockManagement, profile: Profile) -> None:
        r, a = self.r, self.a
        app = next(iter(mgmt.apps.values()))
        r.section("Beitritt")
        errs = self.schemas.errors("core", "join.schema.json", app.request, "JoinRequest")
        r.check(not errs, "POST /join entspricht JoinRequest", "; ".join(errs))
        lt = app.request.get("link_templates")
        if lt is not None:
            meta = yaml.safe_load((profile.dir / "profile.yaml").read_text()).get("link_templates", {})
            for key, tpl in lt.items():
                if key not in meta:
                    r.warn(f"link_templates['{key}']", f"das Profil {profile.name} kennt diesen Schlüssel nicht (bekannt: {sorted(meta)})")
                else:
                    missing = [p for p in meta[key] if "{" + p + "}" not in tpl]
                    r.check(not missing, f"link_templates['{key}'] enthält die Platzhalter {meta[key]}", f"fehlt: {missing}")
        else:
            r.info("link_templates", "nicht angegeben (optional)")

        r.section("Snapshot")
        got = wait_until(lambda: mgmt.count("snapshot") > 0, 15)
        r.check(bool(got), "Die App ruft nach dem Beitritt den Snapshot ab", "innerhalb von 15 s kein GET /snapshot")
        r.check(not any(e["status"] == 401 for e in mgmt.log if e["kind"] != "join"),
                "Jeder Aufruf trägt das Token (Authorization: Bearer)", "mindestens ein Aufruf wurde mit 401 abgewiesen")

        r.section("Webhooks empfangen")
        state = copy.deepcopy(mgmt.data["event_state"])
        base = {"sent_at": "2026-11-29T10:14:07+00:00", "event_id": mgmt.event_id}

        def note(seq, ntype="event_state.updated", obj=None, **extra):
            return dict(base, sequence=seq, type=ntype, object=state if obj is None else obj, **extra)

        def post(n, **kw):
            app.seq = max(app.seq, n["sequence"])
            return mgmt.send_status(app, n, **kw)

        st = post(note(1))
        r.check(200 <= st < 300, "Gültige signierte Benachrichtigung (sequence 1) wird mit 2xx quittiert", f"Status {st or 'keine Verbindung'}")
        puts_before = sum(1 for e in mgmt.log if e["method"] == "PUT")
        st = mgmt.send_status(app, note(2), signature="sha256=" + "0" * 64)
        if 200 <= st < 300:
            r.warn("Ungültige Signatur wird mit 2xx beantwortet", "die Spezifikation verlangt, solche Webhooks zu verwerfen; ob die App es tut, ist von außen nicht prüfbar. Besser mit 401 abweisen.")
        else:
            r.ok(f"Ungültige Signatur wird abgewiesen (Status {st or 'keine Verbindung'})")
        st = mgmt.send_status(app, note(2), signature="")
        r.check(not (200 <= st < 300), "Fehlende Signatur wird abgewiesen", f"Status {st}")
        st = post(note(1))
        r.check(200 <= st < 300, "Doppelte Zustellung (sequence 1 nochmal) wird mit 2xx quittiert", f"Status {st}")
        st = post(note(2, "unbekannt_xyz.updated", {"x": 1}))
        r.check(200 <= st < 300, "Unbekannter Benachrichtigungs-Typ wird ignoriert und mit 2xx quittiert", f"Status {st}")
        st = post(dict(note(3), zusatzfeld="egal"))
        r.check(200 <= st < 300, "Unbekannte Felder im Body werden ignoriert (2xx)", f"Status {st}")

        before = mgmt.count("snapshot")
        st = post(note(9))
        r.info(f"Lücke: sequence 9 statt 4 gesendet, Status {st}")
        r.check(bool(wait_until(lambda: mgmt.count("snapshot") > before, 15)),
                "Bei einer Lücke in der sequence ruft die App den Snapshot ab", "innerhalb von 15 s kein GET /snapshot")
        looped = [e for e in mgmt.log if e["method"] == "PUT"][puts_before:]
        r.check(not looped, "Empfangene Objekte werden nicht zurückgeschrieben (Regel gegen Schleifen)",
                f"{len(looped)} PUT nach den Webhooks: {[e['path'] for e in looped][:3]}")

        r.section("Sicherheitsnetz")
        if a.slow:
            before = mgmt.count("snapshot")
            r.info(f"Warte bis zu {a.safety_net} s auf den Snapshot-Abruf des Sicherheitsnetzes ...")
            r.check(bool(wait_until(lambda: mgmt.count("snapshot") > before, a.safety_net, 0.5)),
                    f"Die App ruft den Snapshot spätestens alle 60 s ab (gewartet {a.safety_net} s)", "kein Abruf")
        else:
            r.skip("Snapshot alle 60 Sekunden", "nur mit --slow (wartet bis zu 65 s)")

        r.section("Beobachtung")
        if a.observe > 0:
            print(f"  Beobachte {a.observe} s lang Aufrufe der App. Löse jetzt Aktionen in der App aus (z. B. eine Meldung speichern) ...", flush=True)
            start = len(mgmt.log)
            time.sleep(a.observe)
            for e in mgmt.log[start:]:
                if e["method"] in ("PUT", "DELETE"):
                    ok = e["status"] in (200, 204)
                    (r.ok if ok else r.fail)(f"{e['method']} {e['path'].replace(API, '')} -> {e['status']}",
                                              "" if ok else "von der Mock-Verwaltungs-App abgelehnt (Schema, Pfad oder Schlüsselfelder)")
        else:
            r.skip("Schreibzugriffe der App", "mit --observe SEKUNDEN kannst du in der App Aktionen auslösen, die das Tool prüft")
        writes = [e for e in mgmt.log if e["method"] in ("PUT", "DELETE")]
        if not writes and a.observe > 0:
            r.info("Schreibzugriffe", "die App hat in dieser Zeit nichts geschrieben")
