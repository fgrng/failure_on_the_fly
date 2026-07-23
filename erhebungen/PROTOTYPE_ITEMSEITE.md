# Prototype #135: Itemseite für Teilnehmende

Dies ist ein bewusst wegwerfbarer, datenbankfreier Gestaltungsprototyp. Er beantwortet nur die Frage, wie freiwillige Freitext- und Likert-Items an beiden Andockpunkten aussehen und ihren Zustand vermitteln können. Die bestehende Ablauf- und Speicherlogik bleibt unangetastet.

Starten mit `SECRET_KEY=test DEBUG=True uv run python manage.py runserver` und dann öffnen:

`http://127.0.0.1:8000/erhebungen/prototype/itemseite/?variant=vergleich`

Die Vergleichsansicht zeigt alle drei Varianten nebeneinander. Die Leiste unten oder die Pfeiltasten wechselt zwischen `a`, `b` und `c`; die URL bleibt teilbar.

| Variante | Besser | Schlechter |
| --- | --- | --- |
| A · Skalenband | Sehr kompakt; die Pole und alle sechs Stufen sind auf einen Blick lesbar. | Die vielen gleichförmigen Felder können wie eine technische Skala wirken. |
| B · Entscheidungsleiter | Betont sechs bewusste Entscheidungen; die erzwungene Tendenz wirkt nicht wie eine vergessene Mitte. | Braucht deutlich mehr Höhe und unterbricht bei mehreren Items den Lesefluss. |
| C · Antwortkarten | Die Antwortflächen sind auf Touch-Geräten deutlich und der freiwillige Charakter wird einladend kommuniziert. | Die Karten geben der kurzen Befragung mehr visuelles Gewicht als dem vorausgehenden Sitzungsverlauf. |

Noch nicht entschieden: welche Variante (oder welche Teile davon) in die echte Item-Darstellung übernommen werden. Nach der Sichtung werden Route, Assets und diese Notiz gelöscht oder der gewählte Entwurf sauber neu implementiert.
