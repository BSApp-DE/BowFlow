# Kern 7 · Implementierungen prüfen

`tools/check.py` prüft, ob eine Anwendung der Spezifikation entspricht. Es gibt zwei Rollen, die unterschiedlich geprüft werden.

```bash
pip install -r tools/requirements.txt
```

## Verwaltungs-App (Liga App) prüfen

Das Tool spielt eine verbundene App. Es braucht die Adresse der Anwendung und einen Beitrittscode (einmalig, 30 Minuten gültig).

```bash
python tools/check.py server --url https://liga.example.org --code AB3K7M
```

Ohne weitere Optionen werden nur Lesezugriffe geprüft, die nichts verändern:

| Bereich | Geprüft |
|---|---|
| Beitritt | `201` mit gültiger `JoinResponse`, Code nur einmal benutzbar, unbekannter Code ergibt `401 JOIN_CODE_INVALID` |
| Absicherung | ohne oder mit falschem Token `401 UNAUTHORIZED`, unbekannter Wettkampf `404 NOT_FOUND` |
| Snapshot | entspricht dem Schema, `?since=<sequence>` ergibt `304` ohne Body, andere Nummern den vollständigen Snapshot |
| Objekte | jedes lesbare Objekt des Profils entspricht seinem Schema (oder `404 NOT_FOUND`, wenn es noch fehlt) |

Mit `--write` kommen Schreibzugriffe dazu. **Nur gegen eine Entwicklungs- oder Testinstanz verwenden**, denn das Tool legt eine Meldung an und löscht sie wieder.

- `PUT` auf ein nur lesbares Objekt ergibt `403 FORBIDDEN`.
- `PUT` mit ungültigem Objekt oder abweichender Schlüsselangabe im Pfad ergibt `422 VALIDATION_FAILED`.
- `PUT`, `GET` und `DELETE` einer Meldung verhalten sich wie beschrieben.

Mit `--code2 <zweiter Code>` tritt das Tool ein zweites Mal bei, startet einen kleinen Empfänger für Webhooks (`--webhook-listen`, Standard `0.0.0.0:8099`; `--webhook-url` ist die Adresse, unter der die Anwendung ihn erreicht) und prüft:

- Signatur, Schema, `type`, `object` und lückenlose `sequence` der Benachrichtigungen
- die schreibende App bekommt keine eigene Benachrichtigung
- `?since=<sequence>` ergibt nach vollständiger Zustellung `304`

Mit `--slow` wird zusätzlich geprüft, dass wartende Benachrichtigungen nach einem Snapshot verworfen werden (dauert etwa 15 Sekunden).

## Verbundene App (Scoring App, Spotter App) prüfen

Das Tool spielt die Verwaltungs-App. Es gibt Adresse und Beitrittscode aus, die du in der App einträgst.

```bash
python tools/check.py client --public-url http://192.168.1.20:8080
```

Die Adresse muss von der App aus erreichbar sein (bei einem Handy also nicht `localhost`). Geprüft wird:

- der Beitritt entspricht `JoinRequest`, `link_templates` passen zum Profil
- die App ruft danach den Snapshot ab und sendet das Token bei jedem Aufruf
- Webhooks: gültige Benachrichtigungen werden mit `2xx` quittiert, ungültige oder fehlende Signaturen abgewiesen, Duplikate, unbekannte Typen und unbekannte Felder ignoriert
- bei einer Lücke in der `sequence` ruft die App den Snapshot ab
- empfangene Objekte werden nicht zurückgeschrieben

Mit `--slow` wird auch das 60-Sekunden-Sicherheitsnetz geprüft (wartet bis zu 65 s). Mit `--observe 60` beobachtet das Tool 60 Sekunden lang, was die App schreibt, während du in ihr Aktionen auslöst. Jeder `PUT` und `DELETE` wird gegen Schema und Pfad geprüft.

## Selbsttest

```bash
python tools/check.py selftest
```

Das Tool prüft sich gegen eine eingebaute Mock-Verwaltungs-App und eine Referenz-App. Das hilft, wenn du das Tool selbst änderst. Die Mock-Verwaltungs-App kann als Gegenstelle zum Entwickeln einer verbundenen App dienen.

## Grenzen

- Das Tool prüft nur, was von außen sichtbar ist. Ob eine App eine ungültig signierte Benachrichtigung wirklich verwirft, sieht es nur am Status (`401` ist die empfohlene Antwort).
- Berechnungen der Liga (Ringsummen, Satzpunkte, Tabelle) werden nicht geprüft, nur die Form der Ergebnisse.
- Das Tool kennt die Profile aus diesem Repo (`profiles/<name>/profile.yaml`). Für ein neues Profil gelten dieselben Prüfungen, sobald es dort liegt. Die Zuordnung von Pfadparametern zu Objektfeldern (`scoresheet_id`, `set_number`, `team_id`) steht in `tools/bowflow_check/common.py`.
