# Liga 6 · Entscheidungen und offene Punkte

Stand: 2026-11-23, aus dem Durchgang mit dem Maintainer anhand der Abläufe von Scoring App und Spotter App. Allgemeine Entscheidungen zum Protokoll stehen im [Kern](../../../core/docs/06-entscheidungen.md).

| Nr. | Entscheidung | Begründung |
|---|---|---|
| L1 | Die Liga App gibt es immer, sie ist Verwaltungs-App und Wahrheit für Spielplan, Ergebnisse und Tabelle. | Nur die Liga rechnet, keine doppelte Logik. |
| L2 | Schützen sind über Mannschaft und Startnummer eindeutig. Es gibt keine Mitglieds-IDs zwischen den Apps. | Keine Schützenliste für die Spotter App nötig. |
| L3 | Vorläufige Pfeile kommen vom Spotter, offizielle werden mit dem Speichern des Satzes gültig. Ohne Scoring App sind die bestätigten Spotter-Werte offiziell. | Entspricht dem tatsächlichen Ablauf. |
| L4 | Ein Satz wird erst gewertet, wenn beide Mannschaften der Begegnung gespeichert haben. | Entspricht dem tatsächlichen Ablauf. |
| L5 | Im Modus `LEAGUE` gibt es kein Stechen: Bei 5:5 ist das Match unentschieden. Im Modus `KNOCKOUT` wird bei Satzgleichstand gestochen. | Entspricht den zwei Systemen der Liga App (Liga-System und KO-System). |
| L11 | Beim Stechen wird nur der Sieger erfasst, als eigenes Objekt `shoot_off` je Schusszettel. Bis dahin gilt `shoot_off_pending`. | Bestätigt durch den Maintainer. Es braucht keine Pfeile. Die Scoring App trägt das Stechen ein, die Liga hat die Hoheit und kann korrigieren. |
| L6 | Korrekturen macht die Liga. Sie schickt sie als Webhook an alle Apps. | Der Schusszettel ist in der Liga jederzeit korrigierbar. |
| L7 | Der Wettkampftag wird ausdrücklich abgeschlossen (`FINISHED`). | Der Kampfrichter bestätigt. |
| L8 | Kampfrichterbericht und abwesende Mannschaften bleiben in der Scoring App, sie sind keine geteilten Objekte. | Verlassen die App nicht. |
| L9 | Spielregeln stehen als Parameter im Spielplan. | Erweiterbar für andere Formate. |
| L12 | Die Liga liefert die Schützenliste je Mannschaft (`roster`, nur lesen). Die Meldung wählt daraus 3 Schützen aus. | Die Scoring App braucht die Schützen zum Melden, die Spotter App nicht. |
| L10 | Begriffe: Match = Zeitslot, Begegnung = Mannschaft gegen Mannschaft, Schusszettel = Mannschaft an einer Scheibe. | Entspricht dem Sprachgebrauch des Maintainers. |

## Offene Punkte

- Anzeige von Schützennamen auf den Displays ist neu in der Spotter App (die Meldung wird dafür gelesen).
- Mehrere schreibende Apps für dieselben offiziellen Sätze: aktuell gilt der letzte Schreibzugriff, es gibt keine Warnung.
- Display-Steuerung (Modus Ergebnisse oder Tabelle, Scheibenpaar) bleibt Sache der Spotter App und ist nicht standardisiert.
- Eine Liveanzeige für Zuhause nutzt den Freigabe-Stand, ist aber nicht Teil von v1.
- Innenzehn/X und andere Disziplinen sind nicht abgedeckt.
- Ein zweiter Lieferant für vorläufige Pfeile (Kameraerkennung) nutzt dieselbe Schnittstelle wie die Tablet-Eingabe, daher keine Änderung nötig.
