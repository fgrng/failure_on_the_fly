# Prototype #287 (Punkt 3): Namensfeld beim Anlegen einer Erhebung

Wegwerfbarer, datenbankfreier Prototyp. Frage: **Wie soll das Namensfeld der Erhebung sich verhalten?** Heute steht `<input name="name" required>` von Hand in `erhebungen/anlegen.html`, und `views.anlegen` übernimmt `request.POST["name"]` ohne Formular. Die Folgen: kein Hilfetext, keine Fehlermeldung, reine Leerzeichen gehen durch, und ein zu langer Name endet (auf PostgreSQL) im Serverfehler. Nach dem Anlegen lässt sich der Name nicht mehr ändern, obwohl er in der Liste, im Dateinamen der Datenspur und in den Abschriften erscheint.

Starten mit `SECRET_KEY=test DEBUG=True uv run python manage.py runserver` und öffnen:

`http://127.0.0.1:8000/erhebungen/prototype/namensfeld/?variant=a` (auch `b`, `c`)

| Variante | Besser | Schlechter |
| --- | --- | --- |
| A · heute | nichts zu tun | siehe oben |
| B · Django-Formular | Meldungen am Feld, Eingabe bleibt stehen, Hilfetext; kleinster Eingriff | Name bleibt nach dem Anlegen unveränderlich |
| C · Ohne Anlegen-Seite | ein Klick weniger; Umbenennen jederzeit im Entwurf | eine neue Aktion »Umbenennen«; offen, ob Umbenennen nach dem Finalisieren erlaubt ist (Abschriften haben den alten Namen kopiert) |

## Entscheidung

**Variante B · Django-Formular** (Sichtung durch den Maintainer, 2026-09-24). Das Namensfeld kommt aus einem Formular, mit Hilfetext, Meldungen am Feld (leer, über 255 Zeichen) und stehen bleibender Eingabe. Die eigene Anlegen-Seite bleibt, ein Umbenennen gibt es nicht.

Festgehalten in #287 (Kommentar vom 2026-09-24). _Danach_ Route in `erhebungen/urls.py`, View-Teil in `erhebungen/views.py`, `erhebungen/templates/erhebungen/prototype_namensfeld.html` und diese Notiz löschen._
