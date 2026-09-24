# Prototype #288: Bildfeld im Vignettenformular

Wegwerfbarer, datenbankfreier Gestaltungsprototyp. Frage: **Wie sieht ein Bild-Upload aus, der zum Rest des Formulars passt?**

Starten mit `SECRET_KEY=test DEBUG=True uv run python manage.py runserver` und öffnen:

`http://127.0.0.1:8000/vignetten/prototype/bildfeld/?variant=a` (auch `b`, `c`, `vergleich`)

Oben steht ein bedienbarer Abschnitt »03 Lernauftrag«. Dort kann man wählen, ablegen, ersetzen und entfernen. »Vignette speichern« täuscht einen Formularfehler vor, danach steht das Feld im Zustand »Auswahl verloren«. Unten stehen alle sechs Zustände nebeneinander, jede Kachel ist ein eigenes Feld. `←`/`→` wechseln die Variante. Ohne `DEBUG` antwortet die Route mit 404.

Allen Varianten gemeinsam: Das echte `<input type="file" accept="image/*">` bleibt unsichtbar, aber fokussierbar (Tab → Leertaste öffnet den Dialog). Entfernen setzt die Django-Checkbox `<name>-clear`. Ablegen per Drag & Drop schreibt `input.files`. Statusmeldungen laufen über `role="status"`.

| Variante | Besser | Schlechter |
| --- | --- | --- |
| A · Ablagezone | Klarste Einladung zum Ablegen; das vorhandene Bild ist groß sichtbar. | Nimmt viel Höhe ein, auch wenn nichts zu tun ist; die Bildbeschreibung bleibt ein getrenntes Feld. |
| B · Anhangzeile | So dicht wie die übrigen Felder; der Status ist auf einen Blick lesbar. | Das Vorschaubild ist zu klein, um den Inhalt zu prüfen; Ablegen ist kaum auffindbar; im schmalen Zustand »gewählt« wird es eng. |
| C · Bildkarte mit Beschreibung | Bild, Alt-Text und Position (`[bild]`-Marker live aus dem Text) bilden eine Einheit; weist auf eine fehlende Beschreibung hin. | Größter Umbau: Die Bildbeschreibung wandert ins Widget, das Formularlayout ändert sich, und das Widget ist nicht mehr nur ein reines Datei-Widget. |

## Entscheidung

**Variante C · Bildkarte mit Beschreibung** (Sichtung durch den Maintainer, 2026-09-24). Festgehalten als Kommentar in #288. Danach Route, View-Teil, Templates unter `vignetten/templates/vignetten/prototype_bildfeld*`, `static/css/bildfeld-prototype.css`, `static/js/bildfeld-prototype.js`, `static/images/prototype-bildfeld/` und diese Notiz löschen.
