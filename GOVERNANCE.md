# Governance

Die Spezifikation wird von einem kleinen Gremium betreut, möglichst einfach und ohne Bürokratie.

- **Gremium:** je eine Person pro beteiligter App-Art (Liga, Scoring, Spotter) plus eine maintainende Person.
- **Änderungen:** Als Vorschlag (Issue oder Merge Request) mit Begründung und Beispiel. Gibt es innerhalb von 7 Tagen keinen Einspruch aus dem Gremium, wird er übernommen.
- **Kompatibilität:** Innerhalb von `v1` nur additive Änderungen (neue optionale Felder, neue Objekte, neue Benachrichtigungs-Typen). Empfänger ignorieren unbekannte Felder und Typen. Brechende Änderungen gibt es nur in einer neuen Hauptversion (`v2`), die alte Version läuft mindestens eine Saison weiter.
- **Neue Profile:** Ein neues Profil (Wettkampfart) wird als Vorschlag mit `profile.yaml`, Schemas, OpenAPI, Beispielen und Doku eingebracht, die Struktur steht in [core/docs/05-profile.md](core/docs/05-profile.md). Das Gremium ergänzt für das Profil eine Person aus der betroffenen Wettkampfart.
- **Neue Funktionen:** Ein Vorschlag, der ein neues geteiltes Objekt einführt, enthält Schema, Beispiel und einen Eintrag in `docs/04-objekte.md`. `python tools/validate.py` muss grün sein.
- **Datenschutz:** Nur das Nötigste teilen (Name und Startnummer von Schützen, keine weiteren Personendaten).
