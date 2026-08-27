---
status: accepted
---

# Historische Migrationen sind unveränderlich

Eine ausgelieferte Migration wird nicht mehr angefasst. Weder ihre
`dependencies` noch die Feldnamen in ihrem Modellzustand. Was sich am Modell
ändert, bekommt eine neue Migration.

Die Entscheidung fällt nach zwei Brüchen, die beide beim Nachziehen von PRD #137
entstanden sind und beide auf jeder bestehenden Entwicklungsdatenbank zuschlugen,
während die Testsuite grün blieb. Test-Datenbanken werden immer frisch migriert;
sie sehen keinen der beiden Fehler.

## 1. `dependencies` bleiben unangetastet

`training/migrations/0001_initial.py` und
`erhebungen/migrations/0005_erhebungsvignette_erhebung_vignetten_and_more.py`
wurden auf `vignetten.0005_vignette_lernauftrag_bild_and_more` vorwärts gezogen.
Auf einer Datenbank, die `training.0001` längst angewandt hatte, bricht danach
jeder `manage.py`-Aufruf:

```
django.db.migrations.exceptions.InconsistentMigrationHistory: Migration
training.0001_initial is applied before its dependency
vignetten.0005_vignette_lernauftrag_bild_and_more on database 'default'.
```

`django_migrations` speichert keine Abhängigkeiten, sondern nur, welche
Migration wann lief. Eine nachträglich verschobene Abhängigkeit lässt sich
deshalb prinzipiell nicht mit der Historie versöhnen —
`check_consistent_history` vergleicht die neue Kante gegen alte Zeitstempel und
muss scheitern. Beide Abhängigkeiten stehen wieder auf
`vignetten.0002_alter_vignette_arbeitsheft_bild`.

**Braucht eine spätere Migration eine frühere Fremd-App, zeigt die Kante
vorwärts.** Die Vorwärtsverschiebung war der Versuch, ein echtes Problem zu
lösen: Der Trigger `training_nur_finale_vignetten_einbinden` referenziert
`vignetten_vignette`, und der Tabellen-Remake, den SQLite für den neuen
`CheckConstraint` in `vignetten.0005` braucht, droppt diese Tabelle
zwischenzeitlich:

```
django.db.utils.OperationalError: error in trigger
training_nur_finale_vignetten_einbinden: no such table: main.vignetten_vignette
```

Die Lösung ist die umgekehrte Kante: `vignetten.0005` hängt von
`training.0001` ab und klammert den Remake in `DROP TRIGGER` / `CREATE TRIGGER`
— genauso, wie es die beiden `erhebungen`-Trigger dort schon wurden. Damit
gilt: **jeder Trigger, der `vignetten_vignette` referenziert, gehört in die
Trigger-Klammer jeder Migration, die diese Tabelle umbaut.**

## 2. Feldnamen im Modellzustand bleiben unangetastet

Die Umbenennungen aus #138 (`lernauftrag` → `lernauftrag_text`,
`arbeitsheft_beschreibung` → `arbeitsheft_bildbeschreibung`) wurden direkt in
`vignetten/migrations/0001_initial.py` geschrieben, statt eine `RenameField`-
Migration zu erzeugen. Auf einer frischen Datenbank fällt das nicht auf. Auf
einer bestehenden heißen die Spalten weiter alt, und der nächste Tabellen-Remake
füllt die neuen Spalten **still mit ihrem eigenen Namen als Literal**:

```
sqlite> select id, lernauftrag_text from vignetten_vignette limit 1;
1|lernauftrag_text
```

Kein Fehler, keine Warnung, Datenverlust. Genau deshalb ist die in ADR-0030 §3
beschriebene Freiheit des harten Schnitts auf den *Platzhaltervertrag* begrenzt
und deckt Migrationen nicht mit ab.

## Kein mechanischer Guard

Ein Test kann die verletzte Invariante nicht prüfen: Die nötige Information —
welche Abhängigkeit galt, als eine Migration lief — steht in keiner Datei und
in keiner Tabelle. Diese ADR ist der Guard.

## Reparatur einer betroffenen Entwicklungsdatenbank

Wer eine Datenbank aus der Zeit vor #138 hat, benennt die beiden Spalten von
Hand um und migriert dann normal weiter. Kein `flush`, kein `--fake`:

```sql
ALTER TABLE vignetten_vignette RENAME COLUMN lernauftrag TO lernauftrag_text;
ALTER TABLE vignetten_vignette
    RENAME COLUMN arbeitsheft_beschreibung TO arbeitsheft_bildbeschreibung;
```
