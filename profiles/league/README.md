# Profil `league` · Liga-Wettkämpfe

Satzsystem mit Mannschaften: 3 Schützen mit je 2 Pfeilen pro Satz, Matches mit mehreren gleichzeitigen Begegnungen, Tabelle. Die Verwaltungs-App ist die **Liga App** (Beispiele: Bennu, BuLiBowApp). Verbundene Apps sind zum Beispiel eine Scoring App (SiaScore) und eine Spotter App (Fawkes).

Der Beitritt, die Webhooks und der Snapshot kommen aus dem [Kern](../../README.md). Dieses Profil legt die Objekte und den Ablauf fest.

| Datei | Inhalt |
|---|---|
| [docs/01-konzept.md](docs/01-konzept.md) | Teilnehmer, Zugriffsarten, Rahmen eines Liga-Wettkampfs |
| [docs/02-objekte.md](docs/02-objekte.md) | Alle geteilten Objekte mit Feldern und Regeln |
| [docs/03-wettkampftag.md](docs/03-wettkampftag.md) | Ablauf eines Wettkampftags in Diagrammen |
| [docs/04-varianten.md](docs/04-varianten.md) | Mit und ohne Scoring App oder Spotter App |
| [docs/05-glossar.md](docs/05-glossar.md) | Begriffe |
| [docs/06-entscheidungen.md](docs/06-entscheidungen.md) | Entscheidungen und offene Punkte |
| [profile.yaml](profile.yaml) | Objekte, Pfade und Zugriffsarten, maschinenlesbar |
| [schemas/](schemas/) | JSON Schemas |
| [api/openapi.yaml](api/openapi.yaml) | OpenAPI der Objekte |
| [examples/](examples/) | Beispielobjekte, gegen die Schemas geprüft |
