# Kern 1 · Konzept

Der Kern beschreibt, **wie** Apps bei einem Wettkampf Daten austauschen. **Was** ausgetauscht wird, legt ein [Profil](05-profile.md) für die jeweilige Wettkampfart fest.

## Teilnehmer

| Teilnehmer | Aufgabe |
|---|---|
| **Verwaltungs-App** | Gibt es bei jedem Wettkampf genau einmal. Sie ist die Wahrheit für Planung und Ergebnisse, speichert alle geteilten Objekte und verteilt Änderungen. Im Profil `league` ist das die Liga App (Beispiel: Bennu). |
| **Verbundene App** | Jede andere App, die an einem Wettkampf teilnimmt, zum Beispiel eine Scoring App (SiaScore) oder eine Spotter App (Fawkes). Eine App kann mehrere Aufgaben vereinen. |

Es gibt keine festen Rollen für verbundene Apps. Das Protokoll unterscheidet nur zwischen Verwaltungs-App und verbundener App.

## Grundregeln

1. **Alles läuft über die Verwaltungs-App.** Verbundene Apps reden nie direkt miteinander.
2. **Objekte statt Befehle.** Apps tauschen Objekte aus (zum Beispiel einen Satz oder eine Meldung). Jede Änderung ist ein neuer Stand des Objekts.
3. **Zugriffsarten pro Objekt.** Das Profil legt fest, ob verbundene Apps ein Objekt nur lesen oder auch schreiben dürfen. Es gibt keine Anmeldung von Fähigkeiten.
4. **Letzter Schreibzugriff gilt.** Es gibt keine Versionsnummern. Die Verwaltungs-App speichert den zuletzt geschriebenen Stand.
5. **Nur die Verwaltungs-App rechnet.** Verbundene Apps erfassen und zeigen an. Das vermeidet doppelte Logik.
6. **Änderungen kommen per Webhook, der Snapshot ist der Fallback.** Siehe [Benachrichtigungen](03-benachrichtigungen.md).

## Wettkampf (`event`)

Der Wettkampf (ein Wettkampftag, eine Veranstaltung) ist die Klammer für alles: Beitritt, Token, Objekte und Benachrichtigungen gelten immer für genau einen `event`. Jeder `event` gehört zu einem **Profil**.

## Mehrere Wettkämpfe

Eine verbundene App kann gleichzeitig an mehreren Wettkämpfen teilnehmen, auch bei verschiedenen Verwaltungs-Apps und mit verschiedenen Profilen, zum Beispiel einer Scoring App, die einmal einen Ligawettkampf und einmal eine Meisterschaft erfasst. Sie tritt jedem Wettkampf einzeln bei (eigener Code, eigenes Token) und hält die Verbindungen getrennt.
