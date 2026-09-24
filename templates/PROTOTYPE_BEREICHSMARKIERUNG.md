# Prototype #287: Bereichsmarkierung in Navigation und Formularseiten

Wegwerfbarer, datenbankfreier Gestaltungsprototyp. Frage: **Wie markieren Navigation und Formularseiten ihren Funktionsbereich einheitlich?**

Starten mit `SECRET_KEY=test DEBUG=True uv run python manage.py runserver`, anmelden (Admin sieht alle vier Gruppen) und öffnen:

`http://127.0.0.1:8000/prototype/bereichsmarkierung/?variant=a` (auch `b`, `c`, `d`)

Die Seite setzt das Sitzungscookie `prototype_nav`. Solange es besteht, trägt die **echte Sidebar auf allen Seiten** die gewählte Variante (`templates/base.html` lädt dann `static/css/bereichsmarkierung-prototype.css`). So lässt sich die Markierung neben echten Formularseiten beurteilen. `?aus=1` löscht das Cookie. Ohne `DEBUG` antwortet die Route mit 404.

| Variante | Aktiv | Hover | ADR-0024 |
| --- | --- | --- | --- |
| A · heute | weiss, grüne Schrift, grüner Balken | weiss, grüne Schrift | bleibt |
| B · Balken in Bereichsfarbe | weiss, grüne Schrift, Balken `--color-area-*-solid` | wie heute | Nachtrag: Der Balken der aktiven Navigation trägt die Bereichsfarbe |
| C · Balken und Fläche | Fläche `-tint`, Balken `-solid`, dunkle Schrift | halbe Tint-Fläche | Nachtrag: »aktive Navigation« fällt aus den grünen Akzenten |
| D · Gruppe als Fläche | ganze Gruppe `-tint`, Eintrag weiss mit Punkt | weiss, dunkle Schrift | wie C |

Kontraste (gerechnet, nicht geschätzt): Gelb-Dark #967231 auf Weiss **4,42:1** (das Ticket nennt ~3:1). Für den Balken genügt das (WCAG 1.4.11 verlangt 3:1), für normalen Text fehlt knapp 4,5:1. Mint 4,71, Violett 8,79, Blau 7,44. Dunkle Schrift auf allen Tints ≥ 8,3:1, Grün-Dark #009b56 auf Tints nur 2,5–3,4:1. In C und D darf die Schrift darum nicht grün bleiben.

Die Tabellen auf der Seite (Seite → Bereich → Überzeile → Titel → Knopf, Feldbeschriftungen) sind der Vorschlag für Punkt 2 und 3 des Tickets.

## Entscheidung

**Variante C · Balken und Fläche im Bereichston** (Sichtung durch den Maintainer, 2026-09-24). Die Vorschlagstabelle und die Feldbeschriftungen gelten, mit drei Änderungen:

- `vignetten/anlegen` und `bearbeiten`: »Schritt für Schritt zur Trainingssituation« entfällt ganz, auch nicht als Untertitel.
- `simulation/kern`: Titel »Aktueller Kern«.
- `simulation/kern_verwalten`: Titel »Kern verwalten«.

Hover: halbe Tönung und dunkle Schrift wie in C, dazu ein aufgehellter Balken in Bereichsfarbe, **keine Unterstreichung**. Bestätigt: »Simulationskern verwalten« wandert nach Entwicklung, die Sidebar-Einträge werden wie vorgeschlagen umbenannt. ADR-0024 ist nachgetragen. Das Namensfeld der Erhebung kommt aus einem Django-Formular (Variante B, siehe `erhebungen/PROTOTYPE_NAMENSFELD.md`).

Festgehalten in #287 (Kommentar vom 2026-09-24). _Danach__ Route in `config/urls.py`, View in `config/prototype.py`, die zwei Zeilen in `templates/base.html`, `templates/prototype_bereichsmarkierung.html`, `static/css/bereichsmarkierung-prototype.css` und diese Notiz löschen._
