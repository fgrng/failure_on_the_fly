---
status: accepted
---

# Die Sitzung wächst auf einer Seite

Eine Sitzung wird als eine durchgehende, zentrierte Seite dargeboten. Die
Rahmenhandlung besteht aus einer erzählenden Einleitung und einer kurzen
Gesprächseinleitung, die zur simulierten Schüler:in überleitet; beide bleiben
sichtbar. Darunter stehen von Beginn an das Diagnosegespräch und sein
Eingabefeld. Nach dem Gespräch erscheint der Debrief als weiterer Abschnitt
darunter. Einen eigenen Schritt „Gespräch beginnen“ gibt es nicht.

HTMX ersetzt ausschließlich die Fortsetzung unter der Rahmenhandlung. Dadurch
aktualisieren neue Gesprächsschritte das Diagnosegespräch, und der Debrief
ergänzt anschließend das bestehende Transkript, ohne die vorherigen Abschnitte
zu entfernen. Formulare und Views bleiben auch ohne HTMX als normale
HTTP-Endpunkte nutzbar.

Probelauf und persistierte Trainingssitzung verwenden dieselbe Darstellung. Der
Probelauf ergänzt darin lediglich die live sichtbare Denkspur; Persistierung und
Ablauforchestrierung bleiben getrennt.

## Gestaltungsentscheidung

- Rahmenhandlung und Debrief verwenden eine ruhige, lineare Abschnittshierarchie
  mit Trennlinien.
- Das Diagnosegespräch verwendet unterscheidbare Sprechblasen für die Eingabe
  der Teilnehmer:in und die Antwort der simulierten Schüler:in.
- Die Lesespalte bleibt schmal und zentriert, damit längere Gesprächsverläufe
  mit kurzen Augenbewegungen lesbar bleiben. Auf breiten Ansichten belegt sie
  die mittleren vier der acht Hauptspalten; unterhalb von 1050 px nutzt sie die
  volle Breite.
