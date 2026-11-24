# Kern 4 · Konventionen

## Namen und Formate

- Feldnamen `snake_case`, Enum-Werte `UPPER_SNAKE_CASE`, Pfade `kebab-case`, alles Englisch.
- Benachrichtigungs-Typen: `<objekt>.updated` oder `<objekt>.deleted` mit dem Objektnamen in `snake_case`.
- IDs sind opake Zeichenketten der Verwaltungs-App (höchstens 64 Zeichen). Nie parsen, nie annehmen, dass sie Zahlen sind.
- Natürliche Schlüssel (zum Beispiel Scheibennummer, Satznummer) sind Ganzzahlen und gehören zum Profil.
- Zeitstempel: ISO 8601 mit Zeitzone. Datum: `YYYY-MM-DD`.
- Unbekannte Felder und unbekannte Benachrichtigungs-Typen ignorieren Empfänger.
- Basis-Pfad: `{base_url}/bowflow/v1`. `{base_url}` ist die Adresse der Verwaltungs-App, also `https://<host>`. Der Wettkampf steckt im Pfad: `/events/{event_id}/...`.

## Schlüsselfelder im Pfad und im Objekt

Ein Objekt trägt seine Schlüsselfelder (zum Beispiel `scoresheet_id`, `set_number`) auch im Inhalt, weil es in Webhooks und im Snapshot ohne Pfad vorkommt. Beim Schreiben (`PUT`) müssen diese Felder im Inhalt **gleich den Werten im Pfad** sein. Weichen sie ab, lehnt die Verwaltungs-App mit `422 VALIDATION_FAILED` ab und speichert nichts.

## Fehler

HTTP-Status plus Körper `{ "code": "...", "message": "..." }` ([Schema](../schemas/problem.schema.json)).

| Status | Code | Bedeutung |
|---|---|---|
| 401 | `JOIN_CODE_INVALID` | Beitrittscode ungültig, abgelaufen oder benutzt (nur beim Beitritt) |
| 401 | `UNAUTHORIZED` | Token fehlt, ist ungültig, abgelaufen oder wurde von der Verwaltungs-App getrennt |
| 403 | `FORBIDDEN` | Objekt ist für verbundene Apps nur lesbar |
| 403 | `OUTSIDE_TIME_WINDOW` | Aktion ist jetzt nicht erlaubt, zum Beispiel Schreiben außerhalb des Wettkampfdatums; die Verwaltungs-App darf das verlangen |
| 404 | `NOT_FOUND` | Wettkampf oder Objekt unbekannt |
| 422 | `VALIDATION_FAILED` | Objekt entspricht nicht dem Schema oder seine Schlüsselfelder weichen vom Pfad ab |
| 429 | `RATE_LIMITED` | Zu viele Anfragen oder Fehlversuche, später erneut versuchen |

Eine App, die mitten im Wettkampf `UNAUTHORIZED` erhält, wurde getrennt oder das Token ist abgelaufen. Sie braucht einen neuen Beitrittscode.

## Versionierung

Die Version steht im Pfad (`/bowflow/v1`). Innerhalb einer Hauptversion sind nur additive Änderungen erlaubt, siehe [GOVERNANCE.md](../../GOVERNANCE.md).
