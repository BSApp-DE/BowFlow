# Kern 6 · Entscheidungen

Stand: 2026-11-23. Die Entscheidungen zum Liga-Profil stehen in [profiles/league/docs/06-entscheidungen.md](../../profiles/league/docs/06-entscheidungen.md).

| Nr. | Entscheidung | Begründung |
|---|---|---|
| K1 | Alle Kommunikation läuft über die Verwaltungs-App. Keine direkte Verbindung zwischen verbundenen Apps. | Eine Vertrauensbeziehung pro App, einfache Absicherung, bessere Liveanzeige für Zuhause. Der Ausfall der Verwaltungs-App wird in Kauf genommen. |
| K2 | Nur zwei Arten von Teilnehmern: Verwaltungs-App und verbundene App. Keine festen Rollen. | Flexibel für Kombi-Apps und neue App-Typen. |
| K3 | Pro Objekt ist festgelegt, ob verbundene Apps nur lesen oder auch schreiben. Es gibt keine Anmeldung von Fähigkeiten. | Einfach. |
| K4 | Letzter Schreibzugriff gilt, keine Versionsnummern. | Einfach, passt zu „Stand ersetzen". |
| K5 | Webhook mit vollständigem Objekt, nie an den Absender, Laufnummer je Empfänger. | Kein Abruf nötig, keine Schleifen, Lücken erkennbar. |
| K6 | Fallback: Snapshot beim Start, nach Ausfall, bei Lücke und alle 60 Sekunden. | Webhooks können unbemerkt ausfallen. |
| K7 | Beitritt per 6-stelligem Code, Token für den Wettkampftag, signierte Webhooks. Kein Widerruf in der Spezifikation. | Entspricht der bestehenden Anbindung der Scoring App. |
| K8 | Die URL-Vorlage für QR-Codes (und ähnliche Links) wird beim Beitritt gemeldet, die Verwaltungs-App druckt sie. | So heute schon bei der Scoring App. |
| K9 | Wettkampfarten sind **Profile** auf einem gemeinsamen Kern. Das Profil steht in der Antwort auf den Beitritt. | Start mit der Liga, andere Wettkampfarten kommen dazu. Eine App kann Wettkämpfe verschiedener Profile bedienen. |
| K10 | Lizenz: MIT für alles im Repo. | Einfach, offen, bekannt. |

## Offene Punkte

- Wie Objekte, die mehrere Profile nutzen, in einen gemeinsamen Teil wandern (siehe [Profile](05-profile.md)).
- Name des Repos.
