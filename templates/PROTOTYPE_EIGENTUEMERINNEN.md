# Prototype #289: Eigentümer:innen-Abschnitt

Wegwerfbarer, datenbankfreier Gestaltungsprototyp. Frage: **Wie lassen sich der Eigentümer:innen-Kreis und das Hinzufügen neuer Personen übersichtlich darstellen?**

Starten mit `SECRET_KEY=test DEBUG=True uv run python manage.py runserver` und öffnen:

`http://127.0.0.1:8000/prototype/eigentuemerinnen/?variant=a` (auch `b`, `c`, `d`)

Nachgebaut ist der Schluss der Vignetten-Detailseite (Abschnitt 06 als Attrappe). Abschnitt 07 steht dreimal untereinander, einmal je Zustand: mehrere Eigentümer:innen mit Auswahl, nur noch die eigene Person, niemand mehr hinzuzufügen. Die Knöpfe tun nichts. Ohne `DEBUG` antwortet die Route mit 404.

| Variante | Kreis | Hinzufügen | Eigene Person entfernen |
| --- | --- | --- | --- |
| A · heute | Chips mit × | Auswahl direkt darunter, nicht getrennt; leeres Auswahlfeld | ohne Hinweis |
| B · Tabelle | Name, Rolle, roter Textlink »Entfernen« | eigene Unterüberschrift nach einer Linie; leer: ein Satz statt Feld | »Mich entfernen« mit Erklärung darunter |
| C · Liste mit Klappzeile | gerahmte Zeilen mit Rolle | letzte Zeile »+ Eigentümer:in hinzufügen« klappt auf | fragt aufklappend nach, erst dann roter Knopf |
| D · Zwei Spalten | schlichte Liste, eigene Person ohne Aktion | Karte rechts daneben | eigener Fuß »Kreis verlassen« (rot, bei letzter Person gesperrt) |

Offen für alle Varianten mit Rolle: Das Include kennt heute nur `username`; die Rolle müsste aus der Gruppe kommen. Bei der Erhebung heißt die Unterzeile nicht »diese Vignette«.

## Entscheidung

**Variante B · Tabelle** (Sichtung durch den Maintainer, 2026-09-24): Tabelle mit Name, Rolle und rotem Textlink »Entfernen«; in der eigenen Zeile »Mich entfernen« mit Erklärung zur Übergabe; bei der letzten Person »Letzte Eigentümer:in« statt Aktion. Hinzufügen unter eigener Unterüberschrift nach einer Trennlinie; ohne mögliche Ergänzungen ein Satz statt leerem Auswahlfeld.

Für die Umsetzung:

- **Rolle:** Ein Konto kann mehrere Rollen haben (Gruppen, dazu `is_superuser`). Die Spalte zeigt alle, z. B. »Autorin, Administratorin«.
- **Gegenstand:** Unterzeile und Erklärungen nennen das jeweilige Artefakt (Vignette, Fragebogen-Item, Erhebung, Training) statt fest »Vignette«; das Include bekommt die Bezeichnung als Parameter.

Festgehalten in #289. _Danach_ Route in `config/urls.py`, View-Teil in `config/prototype.py`, `templates/prototype_eigentuemerinnen.html` und diese Notiz löschen.
