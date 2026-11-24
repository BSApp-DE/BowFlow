# 5 · Ablauf eines Wettkampftags

Beispiel mit Liga App (L), Scoring App (S) und Spotter App (P). Jeder Pfeil zwischen Apps läuft über die Liga.

## Vorbereitung

```mermaid
sequenceDiagram
    autonumber
    actor VA as Veranstalter
    participant L as Liga App
    participant S as Scoring App
    participant P as Spotter App

    VA->>L: Wettkampftag anlegen, Spielplan pflegen
    VA->>S: Beitrittscode eingeben
    S->>L: POST /join (Webhook-URL, URL-Vorlage für QR-Codes)
    L-->>S: Token, Webhook-Geheimnis
    VA->>P: Beitrittscode eingeben
    P->>L: POST /join (Webhook-URL)
    L-->>P: Token, Webhook-Geheimnis
    S->>L: GET /snapshot
    P->>L: GET /snapshot
    L->>L: QR-Codes aus der URL-Vorlage auf Schusszettel drucken
    Note over S,P: Alle Matches stehen auf LOCKED
```

## Freigabe und Meldung

```mermaid
sequenceDiagram
    autonumber
    actor KR as Kampfrichter
    actor SC as Scorer
    participant S as Scoring App
    participant L as Liga App
    participant P as Spotter App

    SC->>S: QR-Code des Schusszettels scannen
    KR->>S: Match 1 freigeben
    S->>L: PUT /state (Match 1 ACTIVE)
    L--)P: event_state.updated
    SC->>S: 3 Schützen melden und bestätigen
    S->>L: PUT /scoresheets/ss_101/lineup
    L--)P: lineup.updated
    Note over P: Display zeigt die gemeldeten Schützen
    opt Meldung falsch
        KR->>S: Meldung zurücksetzen
        S->>L: DELETE /scoresheets/ss_101/lineup
        L--)P: lineup.deleted
    end
```

## Ein Satz

```mermaid
sequenceDiagram
    autonumber
    actor SP as Spotter
    actor SC as Scorer
    participant S as Scoring App
    participant L as Liga App
    participant P as Spotter App

    loop jeder Pfeil
        SP->>P: Pfeilwert eintippen
        P->>L: PUT /provisional-sets/2 (arrows wächst)
        L--)S: provisional_set.updated
        Note over P: Display zeigt den Pfeil sofort
    end
    SP->>P: Satzende bestätigen (closed = true)
    Note over SC: Pfeile an der Scheibe werten
    SC->>S: Pfeile schützenbezogen eintragen und speichern
    S->>L: PUT /official-sets/2
    L--)P: official_set.updated
    Note over L: Wartet, bis beide Mannschaften der Begegnung gespeichert haben
    L->>L: Ringsummen, Satzpunkte, Matchstand, Tabelle berechnen
    L--)S: results.updated
    L--)P: results.updated
    L--)S: standings.updated
    L--)P: standings.updated
    Note over S,P: Handys und Displays zeigen Satzsumme und Satzpunkte
```

Strafpunkte trägt der Kampfrichter in der Scoring App ein. Sie gehen als `penalty_points` mit dem offiziellen Satz an die Liga.

## Nächstes Match und Tagesende

```mermaid
sequenceDiagram
    autonumber
    actor KR as Kampfrichter
    participant S as Scoring App
    participant L as Liga App
    participant P as Spotter App

    Note over S: Alle Begegnungen des Matches entschieden
    S->>L: PUT /state (Match 1 COMPLETED)
    KR->>S: Match 2 freigeben
    S->>L: PUT /state (Match 2 ACTIVE)
    L--)P: event_state.updated
    Note over KR,P: Wiederholt, bis alle Matches des Spielplans geschossen sind
    KR->>S: Wettkampftag abschließen
    S->>L: PUT /state (FINISHED)
    L--)P: event_state.updated
    L->>L: Tag abschließen
    P->>P: Displays auf Tabelle
```

## Stechen (nur Modus `KNOCKOUT`)

```mermaid
sequenceDiagram
    autonumber
    actor KR as Kampfrichter
    participant S as Scoring App
    participant L as Liga App
    participant P as Spotter App

    L--)S: results.updated (shoot_off_pending = true)
    L--)P: results.updated (shoot_off_pending = true)
    Note over KR: Stechen wird geschossen
    KR->>S: Sieger des Stechens eintragen
    S->>L: PUT /scoresheets/ss_101/shoot-off { won: true }
    L--)P: shoot_off.updated
    L->>L: Match entscheiden, Tabelle berechnen
    L--)S: results.updated (decided = true)
    L--)P: results.updated (decided = true)
    Note over S: Match darf jetzt COMPLETED werden
```

Im Modus `LEAGUE` entfällt das Stechen: Bei 5:5 nach allen Sätzen ist das Match unentschieden und sofort entschieden.

## Korrektur

```mermaid
sequenceDiagram
    autonumber
    actor WB as Wettkampfbüro
    participant L as Liga App
    participant S as Scoring App
    participant P as Spotter App

    WB->>L: Schusszettel korrigieren
    L->>L: Satz speichern, neu berechnen
    L--)S: official_set.updated
    L--)P: official_set.updated
    L--)S: results.updated
    L--)P: results.updated
    L--)S: standings.updated
    L--)P: standings.updated
```

Eine App, die keine Webhooks bekommt, sieht die Korrektur spätestens beim nächsten Snapshot.
