#!/usr/bin/env python3
"""Prüft, ob eine Implementierung der BowFlow-Spezifikation entspricht.

Verwaltungs-App (z. B. Liga App) prüfen:
    python tools/check.py server --url https://liga.example.org --code AB3K7M

    Das Tool tritt mit dem Code bei und prüft Beitritt, Absicherung, Snapshot (since/304), alle lesbaren
    Objekte gegen die Schemas und die Fehlercodes. Mit --write werden zusätzlich PUT/DELETE und
    Webhooks geprüft (nur gegen eine Entwicklungs- oder Testinstanz!). Für die Webhook-Prüfung startet
    das Tool einen kleinen Empfänger (--webhook-listen) und braucht einen zweiten Code (--code2).

Verbundene App (z. B. Scoring App, Spotter App) prüfen:
    python tools/check.py client --public-url http://192.168.1.20:8080

    Das Tool spielt die Verwaltungs-App, gibt Adresse und Beitrittscode aus und prüft, wie die App
    Beitritt, Snapshot und Webhooks (Signatur, Duplikate, Lücken, unbekannte Typen) behandelt.

Selbsttest (Prüfer gegen eingebaute Referenz, ohne eigene Anwendung):
    python tools/check.py selftest

Abhängigkeiten: jsonschema, pyyaml (wie tools/validate.py).
"""
from __future__ import annotations

import argparse
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.bowflow_check.client_checks import ClientChecker  # noqa: E402
from tools.bowflow_check.common import Profile, Report, Schemas  # noqa: E402
from tools.bowflow_check.mock import MockManagement, ReferenceApp, serve  # noqa: E402
from tools.bowflow_check.server_checks import ServerChecker  # noqa: E402


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="BowFlow-Konformitätsprüfung", formatter_class=argparse.RawDescriptionHelpFormatter,
                                epilog=__doc__)
    sub = p.add_subparsers(dest="mode", required=True)

    s = sub.add_parser("server", help="Verwaltungs-App prüfen")
    s.add_argument("--url", required=True, help="Adresse der Verwaltungs-App, z. B. https://liga.example.org (ohne /bowflow/v1)")
    s.add_argument("--code", required=True, help="Beitrittscode (einmalig, 30 Minuten gültig)")
    s.add_argument("--code2", help="zweiter Beitrittscode: für die Prüfung der Webhooks (nur mit --write)")
    s.add_argument("--write", action="store_true", help="auch PUT/DELETE und Webhooks prüfen (ändert Daten!)")
    s.add_argument("--slow", action="store_true", help="auch Wiederholungen und das Verwerfen der Warteschlange prüfen (ca. 15 s länger)")
    s.add_argument("--webhook-listen", default="0.0.0.0:8099", help="Adresse des Webhook-Empfängers (Standard 0.0.0.0:8099)")
    s.add_argument("--webhook-url", default="http://127.0.0.1:8099",
                   help="Adresse, unter der die Verwaltungs-App den Empfänger erreicht (Standard http://127.0.0.1:8099)")
    s.add_argument("--insecure", action="store_true", help="TLS-Zertifikat nicht prüfen (Entwicklung)")

    c = sub.add_parser("client", help="verbundene App prüfen")
    c.add_argument("--profile", default="league", help="Profil des Wettkampfs (Standard league)")
    c.add_argument("--listen", default="0.0.0.0:8080", help="Adresse der Mock-Verwaltungs-App (Standard 0.0.0.0:8080)")
    c.add_argument("--public-url", help="Adresse, unter der die App die Mock-Verwaltungs-App erreicht (Standard http://localhost:<Port>)")
    c.add_argument("--code", help="Beitrittscode (Standard: zufällig)")
    c.add_argument("--wait-join", type=int, default=120, help="Sekunden, die auf den Beitritt gewartet wird (Standard 120)")
    c.add_argument("--slow", action="store_true", help="auch das 60-Sekunden-Sicherheitsnetz prüfen (wartet bis zu 65 s)")
    c.add_argument("--safety-net", type=int, default=65, help=argparse.SUPPRESS)
    c.add_argument("--observe", type=int, default=0, help="Sekunden, in denen Aktionen der App beobachtet werden (PUT/DELETE werden geprüft)")

    sub.add_parser("selftest", help="Prüfer gegen die eingebaute Referenz laufen lassen")
    return p


def main() -> int:
    args = parser().parse_args()
    schemas, report = Schemas(), Report()
    if args.mode == "server":
        ServerChecker(args, schemas, report).run()
    elif args.mode == "client":
        ClientChecker(args, schemas, report).run()
    else:
        return selftest(schemas)
    return report.summary()


def selftest(schemas: Schemas) -> int:
    rc = 0
    mgmt = MockManagement(Profile("league"), schemas, codes=["AAAAA2", "BBBBB3"], retry=[1, 1, 1])
    srv = serve(mgmt, "127.0.0.1", 18080)
    ns = argparse.Namespace(url="http://127.0.0.1:18080", code="AAAAA2", code2="BBBBB3", write=True, slow=True,
                            webhook_listen="127.0.0.1:18099", webhook_url="http://127.0.0.1:18099", insecure=False)
    print("### Selbsttest 1/2: Prüfung der Verwaltungs-App gegen die Mock-Verwaltungs-App")
    rep = Report()
    ServerChecker(ns, schemas, rep).run()
    rc |= rep.summary()
    mgmt.stop(); srv.shutdown(); srv.server_close()

    print("\n### Selbsttest 2/2: Prüfung einer verbundenen App (Referenz-App)")
    ns = argparse.Namespace(profile="league", listen="127.0.0.1:18081", public_url="http://127.0.0.1:18081", code="CCCCC4",
                            wait_join=20, slow=True, safety_net=10, observe=0)
    holder = {}

    def start_app():
        time.sleep(1)
        holder["app"] = ReferenceApp("http://127.0.0.1:18081", "CCCCC4", "127.0.0.1", 18082, safety_net=4).start()

    threading.Thread(target=start_app, daemon=True).start()
    rep = Report()
    ClientChecker(ns, schemas, rep).run()
    rc |= rep.summary()
    if "app" in holder:
        holder["app"].close()
    return rc


if __name__ == "__main__":
    sys.exit(main())
