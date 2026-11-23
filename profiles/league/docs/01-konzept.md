# Liga 1 · Konzept

## Teilnehmer

| Teilnehmer | Aufgabe im Liga-Profil |
|---|---|
| **Liga App** | Gibt es bei jedem Liga-Wettkampf. Hält den Spielplan, rechnet Ergebnisse und Tabelle, speichert alle geteilten Objekte. Beispiel: Bennu. |
| **Verbundene App** | Zum Beispiel die Scoring App (digitaler Schusszettel, Kampfrichter) oder die Spotter App (Pfeile live, Displays). Beispiele: SiaScore, Fawkes. Kombi-Apps sind möglich. |

## Zugriffsarten

| Objekt | Verbundene App | Liga App |
|---|---|---|
| Spielplan, Schützenliste | lesen | schreibt |
| Ergebnisse, Tabelle | lesen | schreibt (berechnet) |
| Freigabe-Stand | lesen, schreiben | schreibt bei Korrektur |
| Meldung der Schützen | lesen, schreiben | schreibt bei Korrektur |
| Stechen (nur KO-Modus) | lesen, schreiben | schreibt bei Korrektur |
| Vorläufige Sätze | lesen, schreiben | – |
| Offizielle Sätze | lesen, schreiben | schreibt bei Korrektur |

Schreiben zwei Apps dasselbe Objekt, gilt der **letzte Schreibzugriff**.

## Wer rechnet

Nur die Liga App rechnet: Ringsumme nach Strafpunkten, Satzpunkte, Matchpunkte, Tabelle. Verbundene Apps zeigen die Ergebnisse der Liga an.

## Zwei Wahrheitsstufen bei Pfeilen

- **Vorläufig:** Der Spotter trägt Pfeil für Pfeil ein, damit Zuschauer sofort etwas sehen.
- **Offiziell:** Wird erst durch das Speichern des Satzes gültig. Mit Scoring App speichern die Schützen, ohne Scoring App bestätigt der Spotter.

Die Liga rechnet nur aus offiziellen Sätzen.

## Rahmen eines Liga-Wettkampfs

- Ein **Match** ist ein Zeitslot, in dem 2 bis 4 Begegnungen gleichzeitig laufen, also 4, 6 oder 8 Scheiben. Match 1, dann Match 2 usw.
- Eine **Begegnung** ergibt sich aus den Scheiben: Scheibe 1 gegen 2, 3 gegen 4, 5 gegen 6, 7 gegen 8.
- Ein **Schusszettel** (`scoresheet`) gehört einer Mannschaft an einer Scheibe in einem Match und hat eine eigene ID.
- Ein Satz: 3 Schützen mit je 2 Pfeilen, 6 Pfeile pro Mannschaft. Ein Match geht über bis zu 5 Sätze.

Die Spielregeln (Anzahl Sätze, Schützen, Pfeile, Punkte zum Sieg) stehen als Parameter im Spielplan.

## Link-Vorlagen

Schlüssel `scoresheet` mit dem Platzhalter `{scoresheet_id}`. Die Liga App druckt daraus den QR-Code auf den Schusszettel.
