---
status: accepted
---

# Historische Migrationen sind unveränderlich

Eine ausgelieferte Migration wird nicht mehr angefasst: weder ihre
`dependencies` noch die Feldnamen in ihrem Modellzustand. Was sich am Modell
ändert, bekommt eine neue Migration. Ausgeliefert ist eine Migration, sobald
sie mit ihrem PR nach `main` geht; der Auslöser ist der PR und nicht die
Produktivinstanz, denn was dort gelaufen ist, fließt nicht verlässlich ins
Repo zurück.

## Warum

Die Entscheidung fällt nach zwei Brüchen beim Nachziehen von PRD #137. Beide
schlugen auf jeder bestehenden Entwicklungsdatenbank zu, während die Testsuite
grün blieb: Test-Datenbanken werden immer frisch migriert und sehen so etwas
nie.

- **Verschobene `dependencies`.** `training.0001` und `erhebungen.0005`
  wurden auf eine spätere `vignetten`-Migration vorwärts gezogen.
  `django_migrations` speichert keine Abhängigkeiten, nur welche Migration
  wann lief; `check_consistent_history` vergleicht die neue Kante gegen alte
  Zeitstempel und bricht mit `InconsistentMigrationHistory` jeden
  `manage.py`-Aufruf ab. Eine nachträglich verschobene Abhängigkeit lässt sich
  prinzipiell nicht mit der Historie versöhnen.
- **Umbenannte Felder im Modellzustand.** Die Umbenennungen aus #138 wurden
  direkt in `vignetten.0001_initial` geschrieben statt als
  `RenameField`-Migration. Auf einer bestehenden Datenbank hießen die Spalten
  weiter alt, und der nächste Tabellen-Remake füllte die neuen Spalten still
  mit ihrem eigenen Namen als Literal. Kein Fehler, keine Warnung,
  Datenverlust.

Die Freiheit eines harten Schnitts, wie ADR-0030 sie für den
Platzhaltervertrag genommen hat, ist deshalb auf Anwendungsdaten begrenzt und
deckt Migrationen nicht ab.

## Folgerungen

- **Braucht eine spätere Migration eine frühere Fremd-App, zeigt die Kante
  vorwärts.** Der Anlass des ersten Bruchs war echt: Ein Trigger in `training`
  referenziert `vignetten_vignette`, und der Tabellen-Remake, den SQLite für
  einen neuen Constraint braucht, droppt diese Tabelle zwischenzeitlich. Die
  Lösung ist die umgekehrte Kante: Die `vignetten`-Migration hängt von
  `training.0001` ab und klammert den Remake in `DROP TRIGGER` /
  `CREATE TRIGGER`. Jeder Trigger, der `vignetten_vignette` referenziert,
  gehört in die Trigger-Klammer jeder Migration, die diese Tabelle umbaut.
- **Kein mechanischer Guard.** Ein Test kann die Invariante nicht prüfen:
  Welche Abhängigkeit galt, als eine Migration lief, steht in keiner Datei
  und in keiner Tabelle. Dieses ADR ist der Guard.
- **Migrationstests enden mit der Auslieferung.** Ein Test, der eine
  ausgelieferte Migration vor- und zurückmigriert, kann nichts mehr fangen; er
  ist ein Werkzeug der Entwicklung, kein Bestand der Suite. Die Abschlussphase
  einer Spec streicht deshalb die Tests der Migrationen, die die Spec selbst
  neu anlegt (`docs/agents/issue-tracker.md`); Migrationen aus Tickets ohne
  Spec räumt die Maintainerin von Hand ab.

## Folgen

- Eine fehlerhafte Migration wird durch eine weitere korrigiert, nie durch
  Bearbeiten.
- Verweise aus Migrationen auf inzwischen ersetzte ADRs bleiben stehen
  (`docs/adr/README.md`).
- Eine Entwicklungsdatenbank aus der Zeit vor #138 repariert man von Hand:
  die beiden Spalten umbenennen, dann normal weitermigrieren. Kein `flush`,
  kein `--fake`.
