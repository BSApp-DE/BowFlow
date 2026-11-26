# Liga 5 · Glossar

| Begriff | Bedeutung | Schnittstellen-Name |
|---|---|---|
| Wettkampftag | Ein Tag mit allen Matches. In der Schnittstelle heißt er `event`. | `event` |
| Liga | Wettbewerb mit Mannschaften über eine Saison | `league_name` |
| Veranstaltung, Saison | In der Liga App die Saison, zu der mehrere Wettkampftage gehören (z. B. „Runde 2026") | `season_name` |
| Match | Zeitslot mit 2 bis 4 gleichzeitigen Begegnungen (4, 6 oder 8 Scheiben); wird vom Kampfrichter freigegeben | `match` (`number`) |
| Begegnung | Zwei Mannschaften gegeneinander: Scheibe 1 gegen 2, 3 gegen 4 usw. | (nicht modelliert) |
| Schusszettel | Eine Mannschaft an einer Scheibe in einem Match, mit eigener ID und QR-Code | `scoresheet` |
| Scheibe | Physische Scheibe | `target_number` |
| Schütze | Teilnehmer einer Mannschaft. Englisch bewusst `athlete`, weil „shooter" im Englischen oft an Militär oder Jagd erinnert. | `athlete` (Listen: `athletes`) |
| Satz | 3 Schützen mit je 2 Pfeilen | `set_number` |
| Startnummer | Nummer des Schützen in der Mannschaft, ab 1 ohne Lücken | `start_number` |
| Schützenliste | Alle Schützen einer Mannschaft mit Startnummer und Name; Grundlage für die Meldung | `roster` |
| Meldung | Die 3 Schützen eines Schusszettels | `lineup` |
| Strafpunkte | Abzug von der Ringsumme, pro Mannschaft und Satz | `penalty_points` |
| Satzpunkte | 2 für Sieg, 1 für Unentschieden, 0 für Niederlage | `set_points` |
| Stechen | Entscheidung bei Satzgleichstand im KO-Modus; erfasst wird nur der Sieger | `shoot_off` |
| Modus | `LEAGUE` (Liga-System, 5:5 ist unentschieden) oder `KNOCKOUT` (KO-System, Stechen) | `rules.mode` |
| Pfeilwert | Ganze Zahl 0 bis 10. `0` = Fehlschuss, `null` = noch nicht geschossen | `ArrowValue` |
| Verbundene App | Jede App außer der Liga App | – |

Hinweis zu „Veranstaltung": In der Liga App ist die Veranstaltung die Saison mit mehreren Wettkampftagen, in der Spotter App heißt der Wettkampftag „Veranstaltung". In dieser Spezifikation ist ein Wettkampftag immer ein `event`, die Saison heißt `season_name`.

Hinweis: In der Spotter App Fawkes heißt der Zeitslot teils „Match", in der Liga App meint „Match" intern die Mannschaftsseite einer Begegnung. In dieser Spezifikation gelten ausschließlich die Begriffe der Tabelle.
