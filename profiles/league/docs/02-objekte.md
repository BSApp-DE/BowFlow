# 4 · Geteilte Objekte

Nur Objekte, die zwischen Apps ausgetauscht werden. Was eine App intern speichert (Anzeigezustände, Tokens der Handys, Kampfrichterbericht), steht hier nicht. Schemas: [`schemas/`](../schemas/), Beispiele: [`examples/`](../examples/).

Pfade relativ zu `{base_url}/bowflow/v1/events/{event_id}`.

Beim Schreiben müssen `scoresheet_id` und `set_number` im Objekt gleich den Werten im Pfad sein, siehe [Kern](../../../core/docs/04-konventionen.md).

| Objekt | Pfad | Verbundene App | Schema |
|---|---|---|---|
| Spielplan | `/competition-plan` | lesen | [competition-plan](../schemas/competition-plan.schema.json) |
| Schützenliste | `/teams/{team_id}/roster` | lesen | [roster](../schemas/roster.schema.json) |
| Freigabe-Stand | `/state` | lesen, schreiben | [event-state](../schemas/event-state.schema.json) |
| Meldung | `/scoresheets/{id}/lineup` | lesen, schreiben, löschen | [lineup](../schemas/lineup.schema.json) |
| Vorläufiger Satz | `/scoresheets/{id}/provisional-sets/{n}` | lesen, schreiben | [provisional-set](../schemas/provisional-set.schema.json) |
| Offizieller Satz | `/scoresheets/{id}/official-sets/{n}` | lesen, schreiben | [official-set](../schemas/official-set.schema.json) |
| Stechen | `/scoresheets/{id}/shoot-off` | lesen, schreiben, löschen | [shoot-off](../schemas/shoot-off.schema.json) |
| Ergebnisse | `/scoresheets/{id}/results` | lesen | [results](../schemas/results.schema.json) |
| Tabelle | `/standings` | lesen | [standings](../schemas/standings.schema.json) |
| Snapshot | `/snapshot` | lesen | [snapshot](../schemas/snapshot.schema.json) |

## Benachrichtigungen

Jede Änderung an einem Objekt löst eine Benachrichtigung aus (Aufbau und Zustellung im [Kern](../../../core/docs/03-benachrichtigungen.md)).

| Typ | Objekt | Wer löst aus |
|---|---|---|
| `competition_plan.updated` | Spielplan | Liga |
| `roster.updated` | Schützenliste einer Mannschaft | Liga |
| `event_state.updated` | Freigabe-Stand | verbundene App oder Liga |
| `lineup.updated` | Meldung | verbundene App oder Liga |
| `lineup.deleted` | Meldung zurückgesetzt | verbundene App oder Liga |
| `provisional_set.updated` | Vorläufiger Satz | verbundene App |
| `official_set.updated` | Offizieller Satz | verbundene App oder Liga (Korrektur) |
| `shoot_off.updated` | Ergebnis des Stechens | verbundene App oder Liga |
| `shoot_off.deleted` | Ergebnis des Stechens zurückgenommen | verbundene App oder Liga |
| `results.updated` | Ergebnisse eines Schusszettels | Liga |
| `standings.updated` | Tabelle | Liga |

## Spielplan

Objekt `competition_plan`. Wettkampftag (`id`, `name`, `date`; optional `league_name`, `season_name` und `location` mit `name`, `street`, `postal_code`, `city`, `info`), Spielregeln (`rules`) und die Matches mit ihren Schusszettel-Einträgen: `id` des Schusszettels, `target_number`, `team` (`id`, `name`).

- Ort und Namen sind für Berichte gedacht, zum Beispiel für den Kampfrichterbericht der Scoring App (Ort, Liga, Veranstaltung, Datum).
- Begegnungen sind nicht eigens modelliert: Scheibe 1 gegen 2, 3 gegen 4 usw. innerhalb eines Matches.
- Ein Match hat 4, 6 oder 8 Schusszettel. Wie viele Matches es gibt, steht im Spielplan.
- `rules`: `mode`, `sets_per_match`, `athletes_per_team`, `arrows_per_athlete_per_set`, `points_to_win`.
- `mode`: `LEAGUE` (bei 5:5 nach allen Sätzen unentschieden) oder `KNOCKOUT` (bei Satzgleichstand wird gestochen).
- Heim und Gast gibt es nicht, die Scheibennummer genügt.

## Schützenliste

`team` (`id`, `name`) und `members` mit `start_number`, `first_name` und `last_name`.

- Die Liste enthält alle Schützen, die für die Mannschaft gemeldet werden können. Die Scoring App wählt daraus beim Melden die 3 Schützen aus.
- Ein Schütze ist über Mannschaft und `start_number` eindeutig. Es gibt keine Mitglieds-IDs.
- Vor- und Nachname sind getrennte Felder, damit jede App die Anzeige nach Region wählen kann („Vorname Nachname“ oder „Nachname, Vorname“). Beide sind Pflicht.
- Nur die Liga schreibt die Liste, verbundene App lesen sie. Ändert die Liga sie, schickt sie `roster.updated`.
- Die Spotter App braucht die Liste nicht: Sie bekommt Namen und Startnummern mit der [Meldung](#meldung).

## Freigabe-Stand

`state` (`PLANNED`, `RUNNING`, `FINISHED`) und `match_states`, eine Liste mit `number` (Match-Nummer) und `state` (`LOCKED`, `ACTIVE`, `COMPLETED`) je Match.

- Jede Match-Nummer kommt höchstens einmal vor. Es ist immer höchstens ein Match `ACTIVE`. Das freigegebene Match ist das mit diesem Wert; ist keines `ACTIVE`, ist keines freigegeben.
- `FINISHED` setzt der Kampfrichter bzw. Veranstalter ausdrücklich. Die Liga braucht aktuell nur diesen Wert, die übrigen Felder dienen z. B. einer Liveanzeige.
- Prüfungen wie „nur am Wettkampftag freigeben" sind Sache der schreibenden App.

## Meldung

`scoresheet_id` und `athletes` mit `position` (Schussreihenfolge), `start_number`, `first_name` und `last_name`.

- Ein Schütze ist über Mannschaft (steckt im Schusszettel) und `start_number` eindeutig. Startnummern laufen immer ab 1 ohne Lücken.
- Zurücksetzen (`DELETE`) ist nur sinnvoll, solange noch keine Pfeile erfasst sind. Das prüft die schreibende App.
- **Ohne Meldung** gelten die Startnummern 1, 2, 3 (so viele wie `athletes_per_team`). Das gilt auch für abwesende Mannschaften.

## Vorläufiger Satz

`scoresheet_id`, `set_number`, `arrows` und `closed`.

- `arrows` wächst mit jedem Pfeil: Wert 0 bis 10, `0` = Fehlschuss, `null` = noch nicht geschossen.
- Reihenfolge: Pfeil 1 und 2 gehören dem Schützen auf Position 1, Pfeil 3 und 4 Position 2 usw.
- `closed = true`, wenn der Spotter das Satzende bestätigt hat.
- Nie Grundlage für Ergebnisse. Die Liga rechnet nur aus offiziellen Sätzen.
- Ob die Scoring App die vorläufigen Werte zum Vorbefüllen nutzt, entscheidet sie selbst (Einstellung der App).

## Offizieller Satz

`scoresheet_id`, `set_number`, `athletes` (je `start_number` und `arrows`) und `penalty_points`.

- Mit dem Speichern ist der Satz fixiert, und die Liga rechnet neu.
- `penalty_points` gelten für die Mannschaft im Satz und werden von der Ringsumme abgezogen.
- Ohne Scoring App schreibt die Spotter App den Satz mit den Startnummern 1, 2, 3. Die richtige Zuordnung der Pfeile zu den Schützen korrigiert das Wettkampfbüro nachträglich in der Liga.
- Korrekturen macht die Liga selbst und schickt `official_set.updated` an alle Apps.

## Stechen

`scoresheet_id` und `won`. Nur im Modus `KNOCKOUT`. Erfasst wird ausschließlich der **Sieger**, keine Pfeile.

- Ein Stechen ist fällig, wenn nach allen Sätzen Satzgleichstand herrscht. Das erkennen die Apps an `shoot_off_pending = true` in den Ergebnissen.
- Die App meldet den Sieger für einen der beiden Schusszettel der Begegnung (`won: true`). Die Liga leitet daraus den Verlierer ab.
- Solange das Stechen aussteht, ist das Match nicht entschieden (`decided = false`) und darf nicht `COMPLETED` werden.
- Eingetragen wird das Stechen in der Scoring App (durch den Kampfrichter). Die Liga App hat die Hoheit und kann es korrigieren, auch zurücknehmen (`DELETE`); sie schickt dann `shoot_off.updated` bzw. `shoot_off.deleted` an alle Apps.

## Ergebnisse (je Schusszettel)

`sets` mit `ring_sum` (nach Abzug der Strafpunkte) und `set_points`, dazu `set_points_total`, `match_points` (`null`, bis entschieden), `decided` und `shoot_off_pending`.

## Tabelle

Liste mit `rank`, `team`, `match_points_won`, `match_points_lost`, `set_points_won`, `set_points_lost` und `rank_change` (positiv = Plätze gewonnen seit Tagesbeginn).

## Hinweise für die Liga App: Berechnung

Nur zur Orientierung, die Berechnung gehört der Liga.

- Ringsumme eines Satzes = Summe aller Pfeile der Mannschaft minus `penalty_points`.
- Satzpunkte: Mehr Ringe = 2, gleich = 1 für beide, weniger = 0.
- Ein Match ist entschieden (`decided`), sobald eine Mannschaft `points_to_win` Satzpunkte erreicht hat oder alle Sätze geschossen sind.
- Bei Satzgleichstand nach allen Sätzen: Im Modus `LEAGUE` ist das Match unentschieden. Im Modus `KNOCKOUT` gilt `shoot_off_pending = true`, bis der Sieger des Stechens gemeldet ist. Danach ist das Match entschieden.
- Ein Satz wird erst gewertet, wenn **beide** Mannschaften der Begegnung ihren offiziellen Satz gespeichert haben.
