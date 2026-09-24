# Prototype #290: Lange Erhebungstexte platzsparend bearbeiten

Wegwerfbarer, datenbankfreier Gestaltungsprototyp. Frage: **Wie nehmen Instruktion, Einwilligung und Abschluss weniger Platz ein, ohne schwer bearbeitbar zu werden?**

Starten mit `SECRET_KEY=test DEBUG=True uv run python manage.py runserver` und öffnen:

`http://127.0.0.1:8000/erhebungen/prototype/lange-texte/?variant=a` (auch `b`, `c`, `d`, `heute`)

Nachgebaut ist Abschnitt 01 der Erhebungs-Detailseite, darunter stehen 02 und 03 als Attrappen. Beispieldaten: eine lange Instruktion, eine leere Einwilligung (benötigt) und ein kurzer Abschluss. Die Zustandsleiste oben zeigt je Text den Status und misst, wie weit unten Abschnitt 02 beginnt. Speichern schreibt nichts; die Leiste meldet, was gesendet würde. Die Markdown-Vorschau ist ein grober Nachbau im Browser, weil der Server-Renderer aus `texte/` bisher nur auf `main` liegt. Ohne `DEBUG` antwortet die Route mit 404.

| Variante | Leerer Pflichttext | Speichern / ungespeichert |
| --- | --- | --- |
| A · `<details>` je Text, geschlossen mit Status und erster Zeile | rot umrandet, startet offen | ein Knopf für alle; »Ungespeichert« steht auch am geschlossenen Kopf |
| B · Zweizeilige Felder, die beim Fokus wachsen | rote Kante am Feld und Status am Label | ein Knopf für alle; nichts ist versteckt |
| C · Gerenderter Text, gekürzt, »Bearbeiten« je Text | »Noch kein Text …« und »Text schreiben« | Speichern/Abbrechen je Text, also drei Formulare statt einem |
| D · Ein Feld, drei Reiter | »!« am Reiter | ein Knopf für alle; »●« am Reiter |
| Heute | – | Messlatte |

Zu entscheiden, auch wenn eine Variante gewählt ist: Soll die Lösung nur hier gelten oder in `texte/includes/markdown_feld.html` (Vignette, Simulationskern) wandern? A und B ließen sich ins geteilte Feld einbauen, C und D sind Seitenlayouts. Gemessen wird hier ohne das Seitenraster aus #286.

## Entscheidung

**Variante C · Lesen, je Text »Bearbeiten«** (Sichtung durch den Maintainer, 2026-09-24).

- Gespeichert wird je Text (Speichern/Abbrechen am Text).
- »Finalisieren« speichert vorher alle offenen Texte.
- Beim Verlassen der Seite mit ungespeicherten Änderungen wird gewarnt.
- Gilt für **alle großen Texteingaben**, also auch im Vignettenformular und im Simulationskern, jeweils mit Markdown-Vorschau, wo der Text Markdown ist.
- An den Pflichteingaben ändert sich nichts: Die drei Erhebungstexte bleiben optional, das Finalisieren wird nicht gesperrt. Die Marke »wird benötigt« aus dem Prototyp entfällt; ein leerer Text zeigt nur »Leer« bzw. »Noch kein Text«.

Festgehalten in #290 (Kommentar vom 2026-09-24). _Danach__ Route in `erhebungen/urls.py`, View-Teil in `erhebungen/views.py`, `erhebungen/templates/erhebungen/prototype_lange_texte*`, `static/css/lange-texte-prototype.css`, `static/js/lange-texte-prototype.js` und diese Notiz löschen. Wenn auch die Prototypen zu #287 weg sind, zusätzlich `config/prototype.py`, `templates/includes/prototype_switcher.html`, `static/css/prototype-switcher.css` und `static/js/prototype-switcher.js` löschen._
