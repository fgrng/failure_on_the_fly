# Prototyp: Willkommensseite statt Startseite

Bewusst wegwerfbarer, datenbankfreier Gestaltungsprototyp. Er beantwortet nur die
Frage, wie eine kurze Willkommensseite die Features von FailureOnTheFly vorstellen
kann. Die echte Startseite unter `/` (`templates/start.html`) bleibt unangetastet.

Starten mit `SECRET_KEY=test DEBUG=True uv run python manage.py runserver` und dann
öffnen:

`http://127.0.0.1:8000/prototype/start/?variant=a`

Die Leiste unten oder die Pfeiltasten wechselt zwischen `a`, `b` und `c`; die URL
bleibt teilbar. Der Prototyp läuft in der echten Seitenhülle (Sidebar, Tokens,
Schriften), damit die Dichte realistisch beurteilbar ist.

| Variante | Idee | Besser | Schlechter |
| --- | --- | --- | --- |
| A · Ablaufband | Die Plattform als eine Sequenz: Vignette → Hospitation → Diagnosegespräch → Debrief → Training/Erhebung, nummeriert und untereinander. | Erklärt in einem Durchgang, *was hier passiert*; Schritt 03 ist sichtbar das Herz des Produkts. | Rollenblind — wer nur kuratieren oder auswerten will, muss die ganze Erzählung lesen. |
| B · Rolleneinstieg | Aussage und Anmeldung links, drei Rollenspalten rechts (Autor:in, Lehrperson in Ausbildung, Ausbildung & Forschung) mit je vier Features. | Jede Person findet ihre Spalte sofort; die Bereichsfarben aus ADR-0024 tragen die Orientierung. | Breiteste Variante; auf kleinen Bildschirmen wird aus dem Nebeneinander eine lange Liste. |
| C · Texttafel | Wortmarke, ein Satz, danach sieben Features als dichte Begriffsliste mit Haarlinien. Keine Farbflächen, keine Karten. | Kürzeste Lesezeit, wirkt sachlich und passt zum wissenschaftlichen Kontext; nennt auch Datenschutz. | Wenig einladend, keine sichtbare Hierarchie zwischen den Features, kein visueller Anker. |

Noch nicht entschieden: welche Variante (oder welche Teile davon) die Startseite
wird. Erfahrungsgemäss ist die Antwort eine Mischung — z. B. der Kopf aus C mit dem
Ablaufband aus A. Nach der Sichtung werden Route, View, Template, Assets und diese
Notiz gelöscht und der gewählte Entwurf sauber in `templates/start.html`
implementiert.

Beteiligte Wegwerf-Dateien:
`config/prototype_views.py`, die Route `prototype/start/` in `config/urls.py`,
`templates/prototype_start.html`, `static/css/start-prototype.css`,
`static/js/start-prototype.js`.
