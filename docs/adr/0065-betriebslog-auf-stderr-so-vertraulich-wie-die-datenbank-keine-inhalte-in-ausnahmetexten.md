---
status: accepted
---

# Das Betriebslog geht nach stderr, ist so vertraulich wie die Datenbank, und Ausnahmetexte tragen keine Inhalte

Mit `DEBUG=False` fiel der Traceback einer unbehandelten Ausnahme bisher
nirgends an: Djangos Standard schickt `django.request` an einen Handler, der
nur mit `DEBUG=True` schreibt, und an `mail_admins`, das ohne `ADMINS` nichts
tut (#469). Dieses ADR legt fest, was ins Betriebslog geht und was nie.

## Was ins Log geht

Ein Handler am Root-Logger schreibt ab **WARNING** nach stderr; dort sammelt
supervisord das Log der Instanz. Damit fällt keine Meldung still weg:
`django.security` (etwa unzulässige Hosts, CSRF-Fehler), eigene Logger und
Warnungen aus Bibliotheken erscheinen. `django.request` schreibt erst ab
**ERROR**, also für Serverfehler samt Traceback, nicht für jedes 404 und 403.
Der Logger `evals` bleibt bei INFO.

litellm schreibt bei Anbieterfehlern Hilfe-Banner nach stdout. Sie tragen
keinen Inhalt, verdecken aber die Fehlermeldungen; sie werden abgeschaltet.

## Das Log ist so vertraulich wie die Datenbank

Wer das Log lesen kann, liest auf dem Host auch die SQLite-Datei. Das Log
bekommt deshalb keinen eigenen Schutz, der über den der Datenbank hinausgeht.
Insbesondere wird das **Teilnahme-Token** in protokollierten Pfaden nicht
maskiert: Ein Filter schützte nichts, was die Datenbank nicht ohnehin
preisgibt, und müsste jeder URL-Änderung folgen. Steht das Token einmal nicht
mehr im Pfad, entfällt die Frage.

Daraus folgt auch: Tracebacks verlassen den Host nicht. `ADMINS` bleibt leer;
`AdminEmailHandler` verschickte Tracebacks mit lokalen Variablen über einen
Mailanbieter.

Wie lange Logdateien liegen bleiben, regelt die Rotation von supervisord; die
Deploy-Doku nennt Ort und Rotation. Eine eigene Aufbewahrungsfrist gehört zur
offenen Frage nach der Aufbewahrung der Datenbank.

## Ausnahmetexte tragen keine Inhalte

Das Log nimmt volle Tracebacks auf, denn ohne Ausnahmetext ist ein
Serverfehler oft nicht zu diagnostizieren. Der Preis: Was im Ausnahmetext
steht, landet auf der Platte. Für die flüchtige Teilnahme wäre das die erste
Stelle, an der ihre Inhalte persistiert werden (ADR-0045).

Deshalb gilt: Code, der Inhalte verarbeitet, wirft keine Ausnahmen, deren
Text Inhalte trägt. Inhalte sind Eingaben der Teilnehmenden, Prompts,
Antworten und Denkspuren des Sprachmodells, Transkripte. Betroffen sind der
Gesprächsschritt, die Naht zum Sprachmodell, die Naht zur Transkription und
die flüchtige Sitzung. Die `Anbieterfehler` halten das schon: Sie tragen
keinen Ausnahmetext des Anbieters. **Audio** und **Zugangstoken der
Anbieter** gelangen nie in ein Log, auch nicht über einen Ausnahmetext
(ADR-0007, ADR-0026, ADR-0056).

Ein Test lässt einen Gesprächsschritt mit einem markanten Inhalt an der Naht
zum Sprachmodell scheitern und prüft, dass der Inhalt weder im Log noch in der
Fehlerantwort steht.

## Erwogene Optionen

- **Nur `django.request` ab ERROR.** Schließt die Lücke aus #469, lässt aber
  `django.security` und Warnungen anderer Logger weiter still.
- **Root-Logger ab WARNING ohne Ausnahme.** Schriebe jedes 404 und 403 samt
  Pfad, auf Teilnahme-URLs also samt Token, und verdeckte Serverfehler.
- **Nur Ausnahmetyp und Ort loggen.** Sicher gegen Inhalte, nimmt aber oft die
  Diagnose; die Regel an den Nähten erreicht dasselbe mit weniger Verlust.
- **Mail an `ADMINS`.** Bequem, schickt aber lokale Variablen aus dem Haus.

## Folgen

- Serverfehler sind in Produktion über das supervisord-Log nachvollziehbar.
- Wer an einer inhaltsverarbeitenden Naht eine Ausnahme mit Text wirft, prüft
  den Text gegen diese Regel.
- Ein Inhalt, der trotz der Regel in einen Ausnahmetext gerät, liegt bis zur
  Rotation im Log. Das ist der in Kauf genommene Rest.
