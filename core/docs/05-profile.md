# Kern 5 · Profile

Ein Profil beschreibt eine Wettkampfart: welche Objekte es gibt, wer sie schreiben darf und wie ein Wettkampf abläuft. Der Kern (Beitritt, Token, Webhooks, Snapshot) bleibt für alle Profile gleich.

| Profil | Wettkampfart | Status |
|---|---|---|
| [`league`](../../profiles/league/README.md) | Liga-Wettkämpfe (Satzsystem, Mannschaften, Tabelle) | Entwurf |
| `championship` | Meisterschaften | geplant |

## Wie ein Profil festgelegt wird

Jedes Profil liegt unter `profiles/<name>/` und hat denselben Aufbau:

```
profiles/<name>/
├── README.md        Überblick und Einstieg
├── profile.yaml     maschinenlesbare Beschreibung (Objekte, Pfade, Zugriffsarten)
├── docs/            Konzept, Objekte, Abläufe, Glossar, Entscheidungen
├── schemas/         JSON Schemas der Objekte
├── api/openapi.yaml Pfade der Objekte
└── examples/        Beispielobjekte
```

Ein Profil legt fest:

1. **Objekte** mit Pfad (unter `/events/{event_id}`), Schema und Zugriffsart: `read` (verbundene Apps nur lesen) oder `read_write` (lesen und schreiben), optional mit `deletable`.
2. **Benachrichtigungs-Typen**: je Objekt `<objekt>.updated`, bei löschbaren Objekten zusätzlich `<objekt>.deleted`.
3. **Snapshot:** ein Objekt, das alle geteilten Objekte des Wettkampfs enthält.
4. **Link-Vorlagen:** welche Schlüssel und Platzhalter eine App beim Beitritt in `link_templates` melden kann.
5. **Begriffe und Abläufe** der Wettkampfart.

`python tools/validate.py` prüft, dass `profile.yaml`, Schemas, OpenAPI und Doku zusammenpassen.

## Überschneidungen zwischen Profilen

Objekte, die in mehreren Wettkampfarten gleich sind (zum Beispiel Pfeilwerte oder die Meldung der Schützen), werden zunächst im Profil definiert, in dem sie zuerst gebraucht wurden. Sobald ein zweites Profil sie braucht, wird das Objekt in den gemeinsamen Teil verschoben oder verwiesen. Das ist ein Vorschlag nach [GOVERNANCE.md](../../GOVERNANCE.md).

## Das Profil kommt vom Wettkampf

Der Beitritt kennt das Profil nicht im Voraus: Die Antwort auf `POST /join` enthält `profile`. Eine App, die das Profil nicht unterstützt, beendet die Verbindung.
