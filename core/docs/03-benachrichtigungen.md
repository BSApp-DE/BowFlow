# Kern 3 · Benachrichtigungen (Webhooks) und Fallback

## Prinzip

1. Eine verbundene App schreibt ein Objekt an die Verwaltungs-App (`PUT`).
2. Die Verwaltungs-App speichert es und schickt es per Webhook an **alle anderen** verbundenen Apps. Nicht an die App, die geschrieben hat.
3. Der Empfänger ersetzt seinen Stand durch das Objekt aus dem Webhook.
4. Apps ignorieren Typen, die sie nicht brauchen.

Ändert die Verwaltungs-App selbst etwas (berechnete Ergebnisse, Korrekturen), geht der Webhook an alle verbundenen Apps.

**Regel gegen Schleifen:** Eine App schreibt einen empfangenen Stand nie zurück. Sie sendet nur, wenn ein Mensch oder ihre eigene Logik etwas ändert.

## Aufbau

```json
{
  "sequence": 118,
  "sent_at": "2026-11-29T10:14:07+01:00",
  "event_id": "ev_42",
  "type": "official_set.updated",
  "object": { "scoresheet_id": "ss_101", "set_number": 2, "...": "..." }
}
```

- `type`: `<objekt>.updated` oder `<objekt>.deleted`. Die erlaubten Typen legt das [Profil](05-profile.md) fest.
- `sequence`: fortlaufend **je Empfänger**, beginnt bei 1. Wiederholungen derselben Benachrichtigung tragen dieselbe Nummer.
- `object`: das vollständige geänderte Objekt. Bei `*.deleted` nur die Schlüsselfelder.
- Header `X-BowFlow-Signature`, siehe [Beitritt](02-beitritt.md).

## Zustellung

- Die App antwortet mit `2xx`. Alles andere zählt als Fehler.
- Die Verwaltungs-App wiederholt nach 5 s, 30 s, 2 min, 10 min, 30 min und 1 h.
- Die Reihenfolge je Empfänger bleibt erhalten: Eine neue Benachrichtigung wartet hinter einer fehlgeschlagenen.
- Ausnahme: Ruft die App einen [Snapshot](#fallback-snapshot) ab, verwirft die Verwaltungs-App alle wartenden Benachrichtigungen dieser App mit `sequence` ≤ der `sequence` des Snapshots, auch laufende Wiederholungen. Sie sind im Snapshot enthalten.
- Doppelte Zustellung ist möglich. Empfänger erkennen sie an der `sequence` (bereits gesehen) und ignorieren sie.

## Fallback: Snapshot

`GET /events/{event_id}/snapshot` liefert alle geteilten Objekte des Wettkampfs auf einmal plus die aktuelle `sequence`. Das Schema des Snapshots legt das Profil fest. Eine App ruft ihn ab,

1. beim Start,
2. nach jedem Verbindungsabriss,
3. wenn sie eine Lücke in der `sequence` bemerkt,
4. als Sicherheitsnetz **alle 60 Sekunden**.

Sie ersetzt danach ihren gesamten Stand und setzt ihre erwartete Laufnummer auf `sequence + 1`.

- Die `sequence` im Snapshot ist die höchste Nummer, die für diese App vergeben wurde, auch wenn die Benachrichtigung noch wartet. Der Snapshot enthält mindestens den Stand aller Benachrichtigungen bis zu dieser Nummer.
- Die Verwaltungs-App erkennt die App am Token. Sobald sie den Snapshot ausliefert, verwirft sie die wartenden Benachrichtigungen mit `sequence` ≤ der `sequence` des Snapshots (siehe [Zustellung](#zustellung)). Es müssen also nicht erst alle verpassten Benachrichtigungen nacheinander zugestellt werden.
- Kommt eine bereits verworfene Benachrichtigung trotzdem an (sie war schon unterwegs), ist sie ein Duplikat und wird mit `2xx` quittiert und ignoriert.

### Ohne Änderung: `since` und `304`

Die App kann ihre zuletzt verarbeitete Nummer mitschicken: `GET /events/{event_id}/snapshot?since=130`. Ist `130` genau die aktuelle `sequence` dieser App, hat sich nichts geändert, und die Verwaltungs-App antwortet mit `304 Not Modified` ohne Body. Bei jeder anderen Nummer (höher oder niedriger) liefert sie den vollständigen Snapshot mit `200`. Das Sicherheitsnetz alle 60 Sekunden kostet so im Normalfall fast keine Daten.

```mermaid
sequenceDiagram
    autonumber
    participant V as Verwaltungs-App
    participant P as Verbundene App

    V--)P: sequence 117 (angenommen)
    V--xP: sequence 118 (Timeout)
    V--xP: sequence 119 (wartet hinter 118)
    Note over P: nach 60 s Sicherheitsnetz
    P->>V: GET /snapshot?since=117
    V-->>P: alle Objekte, sequence 119
    Note over V: wartende 118 und 119 verworfen
    V--)P: sequence 120
    P->>V: GET /snapshot?since=120
    V-->>P: 304 Not Modified
```
