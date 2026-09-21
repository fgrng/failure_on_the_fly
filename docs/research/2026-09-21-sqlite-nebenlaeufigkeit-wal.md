# SQLite unter WAL: Trägt die bestehende Konfiguration mehr Schreib-Nebenläufigkeit?

Recherche zu [#203](https://github.com/fgrng/failure_on_the_fly/issues/203). Beantwortet die zweite der dort offenen Fragen:

> Trägt SQLite mit WAL die erhöhte Schreib-Nebenläufigkeit, oder häufen sich Sperrkonflikte?

Die Frage steht vor der eigentlichen Entscheidung aus #203 (Thread-Worker in der README-Empfehlung oder Aufgabenwarteschlange). Sie ist hier **aus Primärquellen und aus dem Code** beantwortet, damit dafür **kein Lastgenerator gebaut werden muss**. Was diese Notiz ausdrücklich *nicht* beantwortet: ob die Worker-Blockade selbst tragbar ist — das ist eine Frage an die Zahl der Worker, nicht an die Datenbank.

Stand: 2026-09-21. Geprüfte Codebasis: `config/settings.py`, `sitzungen/sink.py`, `sitzungen/durchlauf.py`, `sitzungen/views.py`, `erhebungen/ablauf.py`, `erhebungen/views.py`, `erhebungen/models.py`, `training/views.py`, `simulation/__init__.py`, `simulation/transkription/__init__.py`, `README.md`; `django==6.0.7` (`django/db/backends/sqlite3/base.py`), CPython 3.14.3, SQLite-Bibliothek 3.45.1, `gunicorn` laut README-Dienstdefinition.

## Gist

**Die bestehende Konfiguration trägt die erhöhte Schreib-Nebenläufigkeit — mit mindestens einer, realistisch zwei Größenordnungen Abstand.** Die Annahme aus dem Ticket bestätigt sich; die Datenbank ist hier nicht der Engpass, und ein Lastgenerator wäre Aufwand ohne Erkenntnisgewinn.

Der Grund ist nicht, dass SQLite besonders viel Nebenläufigkeit könnte — es serialisiert unter WAL **genau einen Schreiber** (Abschnitt 1) —, sondern dass die serialisierte Strecke hier **sehr kurz** ist. Die Schreibtransaktionen des Repos enthalten ausschließlich DB-Operationen: wenige `INSERT`/`UPDATE` und ein `fsync`, zusammen im Bereich von Millisekunden. Der teure Teil eines Gesprächsschritts — der Modellaufruf, drei Versuche à mehreren Sekunden — liegt **vollständig außerhalb jeder Transaktion** (Abschnitt 6), ebenso das 120-s-Polling der Infomaniak-Transkription, das überhaupt nichts in die Datenbank schreibt (Abschnitt 7). Das ist der eine Befund, der die Entscheidung hätte kippen können; er ist für das ganze Repo systematisch geprüft und negativ.

Die Kombination `journal_mode=WAL` + `transaction_mode="IMMEDIATE"` + `timeout=20` ist genau die, die sqlite.org und die Django-Doku empfehlen: `BEGIN IMMEDIATE` nimmt die Schreibsperre am Transaktionsanfang, wo der Busy-Handler wartet, statt sie mittendrin hochzustufen, wo SQLite **ohne** Busy-Handler sofort `SQLITE_BUSY` zurückgäbe (Abschnitt 2). Der Preis ist, dass `atomic()` hier **immer** global serialisiert, auch wenn der Block nur liest.

Zur Größenordnung (Abschnitt 8): Erwartet werden bei ~10 gleichzeitig Teilnehmenden **1–3 Schreibtransaktionen/s**, im unrealistisch dichten Fall ~15/s. Dem steht die einzige belastbare Untergrenze von sqlite.org gegenüber: **etwa 60 Transaktionen/s auf einer rotierenden 7200er-Platte**, wo jedes Commit auf die Plattenumdrehung wartet. Selbst dieser schlechteste dokumentierte Fall liegt über der Last; auf SSD liegen Faktoren von 10–100 dazwischen. Der Sicherheitsabstand beträgt also **mindestens eine, realistisch zwei Größenordnungen**.

Der Ausfallmodus, der SQLite unter WAL wirklich umbringt, ist kein Sperrkonflikt, sondern das Netzdateisystem: WAL braucht geteilten Speicher (`-shm`) und funktioniert dort schlicht nicht (Abschnitt 4). Das ist hier bereits empirisch ausgeschlossen — die Datenbank steht nachweislich in WAL.

Zwei kleine, ehrlich zu nennende Kanten: Die Sitzungen liegen im DB-Backend, jeder Gesprächsschritt erzeugt daher **zwei** Schreibtransaktionen statt einer (Abschnitt 6.3). Und `erhebungen/views.py:629/638` hält die Schreibsperre über das Rendern einer ganzen Seite (Abschnitt 6.4) — irrelevant für den Workshop, weil Forschenden-Pfad, aber der einzige Ort im Repo, an dem eine Transaktion länger offen ist als nötig.

## 1. WAL-Writer-Semantik: was genau serialisiert

### 1.1 Ein Schreiber, beliebig viele Leser

sqlite.org, [Write-Ahead Logging](https://www.sqlite.org/wal.html), Abschnitt 1 (Overview):

> WAL provides more concurrency as readers do not block writers and a writer does not block readers. Reading and writing can proceed concurrently.

Und Abschnitt 2.2 (Concurrency), unmissverständlich:

> However, since there is only one WAL file, there can only be one writer at a time.

Das ist die ganze Semantik: **Leser sind gratis, Schreiber sind eine Warteschlange der Länge 1.** Es gibt unter WAL keine Aufteilung nach Tabelle oder Zeile — die Sperre gilt für die Datenbankdatei als Ganzes. Was in den älteren Journal-Modi über die Sperrzustände `SHARED` → `RESERVED` → `PENDING` → `EXCLUSIVE` läuft ([File Locking And Concurrency In SQLite Version 3](https://www.sqlite.org/lockingv3.html): »Only a single RESERVED lock may be active at one time«), ist unter WAL zu einer einzigen Schreibsperre zusammengezogen.

### 1.2 Ab wann serialisiert es

Das ist der Teil, auf den es für die Auslegung ankommt: **nicht ab dem ersten Lesen, sondern ab dem Moment, in dem die Schreibsperre genommen wird.** Wann das ist, entscheidet der Transaktionsmodus — siehe Abschnitt 2. Die serialisierte Strecke ist also nicht die Dauer einer HTTP-Anfrage, sondern die Dauer zwischen `BEGIN IMMEDIATE` und `COMMIT`.

Daraus folgt die einzige Auslegungsregel, die hier zählt: **Die Frage ist nicht, wie viele Anfragen gleichzeitig laufen, sondern wie lange jede einzelne die Schreibsperre hält.** Zehn Teilnehmende, deren Schreibtransaktionen je 2 ms dauern, belegen die Sperre zusammen 20 ms — sie kollidieren praktisch nie. Zehn Teilnehmende, deren Transaktionen je einen Modellaufruf von 5 s umschließen, wären dagegen bei jedem Schritt in einer 50-Sekunden-Schlange. Abschnitt 6 zeigt, dass das Repo im ersten Fall ist.

### 1.3 Wie viele Schreiber es überhaupt geben kann

Begrenzt ist das nicht durch die Zahl der Teilnehmenden, sondern durch die Zahl gleichzeitiger Anfragebearbeiter. Die README-Dienstdefinition (`README.md:322`) fährt `--workers 3`; `worker_class` bleibt beim gunicorn-Standard `sync` mit `threads` = 1 ([gunicorn, Settings](https://gunicorn.org/reference/settings/): »threads — Default: 1 … only affects the Gthread worker type«; »If you try to use the `sync` worker type and set the `threads` setting to more than 1, the `gthread` worker type will be used instead«). Heute gibt es also **höchstens drei** Verbindungen, die gleichzeitig schreiben wollen. Der in #203 erwogene Wechsel auf `--worker-class gthread --threads N` hebt diese Zahl auf `3 × N`. Selbst bei `--threads 8` sind das 24 potenzielle Schreiber — die Warteschlange vor einer Millisekunden-Transaktion bleibt trivial (Abschnitt 8.4).

## 2. `busy_timeout` und `BEGIN IMMEDIATE`: was die Kombination bewirkt

### 2.1 Was `busy_timeout` tut — und was nicht

`PRAGMA busy_timeout` setzt den Busy-Handler der Verbindung ([PRAGMA busy_timeout](https://www.sqlite.org/pragma.html#pragma_busy_timeout): »Query or change the setting of the busy timeout. This pragma is an alternative to the `sqlite3_busy_timeout()` C-language interface«). Der Handler lässt eine blockierte Anfrage warten, statt sofort `SQLITE_BUSY` zu melden.

Entscheidend ist die Ausnahme. sqlite.org, [`sqlite3_busy_handler`](https://www.sqlite.org/c3ref/busy_handler.html):

> The presence of a busy handler does not guarantee that it will be invoked when there is lock contention. If SQLite determines that invoking the busy handler could result in a deadlock, it will go ahead and return SQLITE_BUSY to the application instead of invoking the busy handler.

Die dort beschriebene Szene ist genau der klassische Upgrade-Deadlock: zwei Verbindungen, jede hält eine niedrigere Sperre und will hochstufen, keine kommt voran. SQLite bricht das auf, indem es einer von beiden `SQLITE_BUSY` gibt — **ohne zu warten**. Ein `busy_timeout` von 20 s hilft in diesem Fall nichts: Er wird nicht konsultiert.

Das WAL-Gegenstück dazu ist [`SQLITE_BUSY_SNAPSHOT` (517)](https://www.sqlite.org/rescode.html#busy_snapshot):

> The SQLITE_BUSY_SNAPSHOT error code is an extended error code for SQLITE_BUSY that occurs on WAL mode databases when a database connection tries to promote a read transaction into a write transaction but finds that another database connection has already written to the database and thus invalidated prior reads.

Der Lesestand der wartenden Verbindung ist veraltet; Warten kann ihn nicht auffrischen. Die Transaktion **muss** zurückgerollt werden. Das ist der Fehlermodus, der in Django-Anwendungen als sporadisches `OperationalError: database is locked` auftritt und sich durch Erhöhen von `timeout` nicht wegkonfigurieren lässt.

### 2.2 Was `BEGIN IMMEDIATE` daran ändert

sqlite.org, [`BEGIN`](https://www.sqlite.org/lang_transaction.html) — erst der Standardfall:

> DEFERRED means that the transaction does not actually start until the database is first accessed. […] If the first statement after BEGIN DEFERRED is a SELECT, then a read transaction is started. Subsequent write statements will upgrade the transaction to a write transaction if possible, **or return SQLITE_BUSY**.

Genau dieses Hochstufen ist der Ort, an dem der Busy-Handler ausfällt. `IMMEDIATE` schneidet ihn weg:

> IMMEDIATE causes the database connection to start a new write immediately, without waiting for a write statement. The BEGIN IMMEDIATE might fail with SQLITE_BUSY if another write transaction is already active on another database connection.

Und (für WAL relevant): »EXCLUSIVE and IMMEDIATE are the same in WAL mode.«

Der Unterschied ist subtil, aber genau der gesuchte: `BEGIN IMMEDIATE` kann ebenfalls `SQLITE_BUSY` liefern — aber **am Anfang der Transaktion**, wo noch keine Sperre gehalten wird, wo kein Deadlock droht und wo der Busy-Handler deshalb sehr wohl gerufen wird und bis zu 20 s wartet. Die Garantie steht ausdrücklich in der Beschreibung von [`SQLITE_BUSY` (5)](https://www.sqlite.org/rescode.html#busy):

> An SQLITE_BUSY error can occur at any point in a transaction: when the transaction is first started, during any write or update operations, or when the transaction commits. To avoid encountering SQLITE_BUSY errors in the middle of a transaction, the application can use BEGIN IMMEDIATE instead of just BEGIN to start a transaction. The BEGIN IMMEDIATE command might itself return SQLITE_BUSY, but **if it succeeds, then SQLite guarantees that no subsequent operations on the same database through the next COMMIT will return SQLITE_BUSY**.

**Antwort auf die Frage aus dem Ticket: Ja.** `transaction_mode="IMMEDIATE"` verhindert die Upgrade-`SQLITE_BUSY`-Fälle, die `busy_timeout` nicht auflösen kann — belegt an `rescode.html#busy` (Garantie) und `c3ref/busy_handler.html` (warum der Timeout im Upgrade-Fall nicht greift). Die Kombination verwandelt einen unauflösbaren Fehler mitten in der Transaktion in ein auflösbares Warten am Transaktionsanfang.

### 2.3 Dieselbe Aussage in der Django-Doku

Django sagt es kürzer, [Databases — SQLite notes](https://docs.djangoproject.com/en/6.0/ref/databases/):

> To make sure your transactions wait until `timeout` before raising "Database is Locked", change the transaction mode to `IMMEDIATE`.

Und zum `timeout` allein, ohne `IMMEDIATE`, sehr ehrlich:

> This will make SQLite wait a bit longer before throwing "database is locked" errors; **it won't really do anything to solve them.**

Das ist genau die Lücke, die `IMMEDIATE` schließt. Beide Optionen zusammen sind mehr als die Summe ihrer Teile: `timeout` allein verschiebt das Problem, `IMMEDIATE` allein hätte keinen Warteraum.

### 2.4 Der Preis: `atomic()` serialisiert immer

Es gibt eine Kehrseite, die zu benennen ist. Mit `IMMEDIATE` nimmt **jeder** `transaction.atomic()`-Block die globale Schreibsperre, auch wenn er nur liest. Der Beleg steht in Djangos Quellcode, `django/db/backends/sqlite3/base.py:321-331`:

```python
def _start_transaction_under_autocommit(self):
    if self.transaction_mode is None:
        self.cursor().execute("BEGIN")
    else:
        self.cursor().execute(f"BEGIN {self.transaction_mode}")
```

Konkret heißt das: `_trainingsbindung_laden_oder_anlegen` (`training/views.py:418`) nimmt die Schreibsperre auch dann, wenn die Bindung längst existiert und der Block nichts schreibt. Das ist für die Auslegung hier unerheblich (der Block dauert Mikrosekunden), gehört aber in die Rechnung: Die Zahl der serialisierten Abschnitte ist die Zahl der `atomic()`-Blöcke, nicht die Zahl der tatsächlichen Schreibvorgänge.

Django selbst zieht daraus genau eine Konsequenz, und das Repo folgt ihr bereits:

> For the best performance with `IMMEDIATE` and `EXCLUSIVE`, transactions should be as short as possible. This might be hard to guarantee for all of your views so **the usage of `ATOMIC_REQUESTS` is discouraged in this case.**

Siehe Abschnitt 6.2.

Ein zweiter Nebeneffekt, im Repo schon dokumentiert (ADR-0037, `docs/adr/0037-eigentuemer-kreis-als-gemeinsame-basis.md:118-134`): Djangos SQLite-Backend führt `has_select_for_update = False` — am laufenden Prozess nachgeprüft —, die Klausel erzeugt also kein SQL. Alle `select_for_update()`-Aufrufe im Repo (`erhebungen/ablauf.py:294`, `erhebungen/views.py:972`, `training/views.py:562`, `vignetten/models.py:460` u. a.) sind unter SQLite **wirkungslos**; die Serialisierung leistet ausschließlich das `BEGIN IMMEDIATE` des umschließenden `atomic()`. Das ist korrekt so, aber es verschiebt die ganze Nebenläufigkeitsfrage auf die Länge der `atomic()`-Blöcke — worauf Abschnitt 6 antwortet.

## 3. Größenordnung des Schreibdurchsatzes

Hier ist Vorsicht geboten, weil die gängig zitierten Zahlen gerne die falsche Größe messen. Die gesuchte Größe ist **Commits pro Sekunde**, nicht INSERTs pro Sekunde.

### 3.1 Die eine belastbare Zahl von sqlite.org

sqlite.org, [FAQ (19)](https://www.sqlite.org/faq.html) — »INSERT is really slow – I can only do few dozen INSERTs per second«:

> Actually, SQLite will easily do 50,000 or more INSERT statements per second on an average desktop computer. **But it will only do a few dozen transactions per second.** Transaction speed is limited by the rotational speed of your disk drive. A transaction normally requires two complete rotations of the disk platter, which on a 7200RPM disk drive limits you to about 60 transactions per second.

> Transaction speed is limited by disk drive speed because (by default) SQLite actually waits until the data really is safely stored on the disk surface before the transaction is complete.

Die 50.000 INSERTs/s sind INSERTs **innerhalb einer** Transaktion und für unsere Frage wertlos. Die relevante Zahl ist **~60 Transaktionen/s**, und sie ist der schlechteste dokumentierte Fall: rotierende Platte, ein voller `fsync` pro Commit.

Das SQLite-Projekt hat die Antwort selbst nachgetragen:

> **Update 2024-11-19:** The text above is a really old answer. SQLite will do far more than 50K inserts/second now, and everybody uses SSD nowadays, making the performance faster still. But the gist of the answer above remains correct: Putting multiple operations inside a single transaction can improve performance dramatically.

Auch der Nachtrag nennt keine Commit-Rate für SSD. **sqlite.org veröffentlicht keine Commits-pro-Sekunde-Zahl für moderne Hardware.** Das ist ehrlich so festzuhalten: Der einzige harte Wert der Primärquelle ist die Untergrenze von ~60/s. Alles darüber ist Ableitung aus der `fsync`-Latenz des Speichers (Abschnitt 3.3), nicht Zitat.

### 3.2 Wovon es abhängt: `synchronous`

Der Durchsatz hängt fast ausschließlich daran, ob pro Commit ein `fsync` fällig wird. sqlite.org, [wal.html](https://www.sqlite.org/wal.html), Abschnitt 2.3 (Performance Considerations):

> Write transactions are very fast since they only involve writing the content once (versus twice for rollback-journal transactions) and because the writes are all sequential. Further, syncing the content to the disk is not required, as long as the application is willing to sacrifice durability following a power loss or hard reboot. (Writers sync the WAL on every transaction commit if PRAGMA synchronous is set to FULL but omit this sync if PRAGMA synchronous is set to NORMAL.)

Und [PRAGMA synchronous](https://www.sqlite.org/pragma.html#pragma_synchronous):

> In WAL mode when synchronous is NORMAL (1), the WAL file is synchronized before each checkpoint and the database file is synchronized after each completed checkpoint … but **no sync operations occur during most transactions**. With synchronous=FULL in WAL mode, an additional sync operation of the WAL file happens after each transaction commit.

> WAL mode is safe from corruption with synchronous=NORMAL … but WAL mode does lose durability. A transaction committed in WAL mode with synchronous=NORMAL might roll back following a power loss or system crash. **Transactions are still atomic, consistent, and isolated.** … Transactions are durable across application crashes regardless of the synchronous setting or journal mode.

**Befund am laufenden Prozess:** Das Repo setzt `synchronous` **nicht**; die Abfrage über Djangos Verbindung liefert `synchronous = 2`, also **FULL**. Es fällt hier also ein WAL-`fsync` pro Commit an. Das ist die langsamere, dafür voll dauerhafte Einstellung — und die Rechnung in Abschnitt 8 rechnet mit ihr. `synchronous=NORMAL` bliebe als Reserve, falls es je eng würde; für eine Forschungserhebung ist der Verzicht auf Dauerhaftigkeit bei Stromausfall allerdings nichts, was man ohne Not eingeht, und nach der Rechnung besteht keine Not.

### 3.3 Der Rest: Dateisystem und Speichermedium

Die Commit-Rate ist damit im Wesentlichen `1 / fsync-Latenz`. Die Bandbreite, ehrlich benannt:

| Fall | `fsync`-Latenz | Commits/s (abgeleitet) | Beleg |
| --- | --- | --- | --- |
| Rotierende 7200er-Platte | ~16 ms (Umdrehung) | **~60** | sqlite.org FAQ (19), zitiert |
| SATA-SSD / NVMe | Bruchteile einer Millisekunde | **mehrere Hundert bis Tausende** | abgeleitet, **keine sqlite.org-Zahl** |
| `synchronous=NORMAL` | kein `fsync` im Commit | nochmals deutlich höher | `pragma.html#pragma_synchronous` |
| Netzdateisystem | — | **WAL funktioniert gar nicht** | Abschnitt 4 |

Die Untergrenze der Tabelle — 60/s — ist der Wert, mit dem Abschnitt 8 rechnet. Sie ist für einen Uberspace-Host sicher pessimistisch, aber sie ist die einzige, die eine Primärquelle hergibt, und sie genügt.

### 3.4 Kleine Transaktionen sind der Fall, für den WAL gebaut ist

[wal.html](https://www.sqlite.org/wal.html), Abschnitt 1:

> WAL works best with smaller transactions. WAL does not work well for very large transactions.

Das Schreibprofil des Repos — pro Gesprächsschritt ein `INSERT` plus ein `bulk_create` weniger Fehlversuche — ist genau das günstige Profil. Die einzige große Transaktion im Repo ist das Seeding (`seeds/management/commands/workshopdaten_anlegen.py:68`, `entwicklungsdaten_anlegen.py:160`), das eine ganze Einrichtung in einen `atomic()`-Block legt. Das läuft vor dem Workshop, einmal, ohne Nebenläufigkeit.

## 4. Der Ausfallmodus, der wirklich zählt: `-shm` und Netzdateisysteme

Der Sperrkonflikt ist nicht das Risiko. Das Risiko ist, dass WAL auf dem Zielsystem überhaupt nicht läuft. sqlite.org, [wal.html](https://www.sqlite.org/wal.html), Abschnitt 1 (Disadvantages):

> All processes using a database must be on the same host computer; **WAL does not work over a network filesystem.** This is because WAL requires all processes to share a small amount of memory and processes on separate host machines obviously cannot share memory with each other.

Der Mechanismus dahinter, Abschnitt 2.2:

> a data structure called the "wal-index" is maintained in shared memory which helps readers locate pages in the WAL quickly and with a minimum of I/O. The wal-index greatly improves the performance of readers, but **the use of shared memory means that all readers must exist on the same machine**. This is why the write-ahead log implementation will not work on a network filesystem.

Das ist die `-shm`-Datei neben `db.sqlite3` und `db.sqlite3-wal`.

**Hier bereits empirisch ausgeschlossen.** Der Wechsel nach WAL ist kein Wunsch, sondern ein Zustand der Datei: [PRAGMA journal_mode](https://www.sqlite.org/pragma.html#pragma_journal_mode) sagt, »The WAL journaling mode is persistent; after being set it stays in effect across multiple database connections and after closing and reopening the database«, und die zweite Form des Pragmas gibt zurück, was tatsächlich gilt — »If the journal mode could not be changed, the original journal mode is returned«. Eine Datenbank auf einem Netzdateisystem stünde also schlicht nicht in WAL.

Nachgeprüft: `PRAGMA journal_mode` liefert an der Datenbank des Repos `wal`. `config/settings.py` setzt das über `init_command` bei jedem Verbindungsaufbau erneut; Djangos Backend zerlegt die Zeichenkette an `;` und führt sie aus (`django/db/backends/sqlite3/base.py:195-197`, `self.init_commands = init_command.split(";")` → `['PRAGMA journal_mode=WAL', '']`). **Die Produktivinstanz läuft damit nachweislich unter WAL.** Wäre der Ablageort ein Netzdateisystem, wäre das bereits heute sichtbar — es wäre nicht ein Problem der erhöhten Nebenläufigkeit, sondern eines des laufenden Betriebs.

Ein Rest bleibt anzumerken: `DATABASE_PFAD` ist über die Umgebung konfigurierbar (`config/settings.py`, `os.environ.get("DATABASE_PFAD", BASE_DIR / "db.sqlite3")`). Wer die Datei auf eine Netzfreigabe legt, verlässt den geprüften Boden. Das ist eine Betriebs-, keine Auslegungsfrage.

## 5. WAL-Checkpointing über einen mehrstündigen Workshop

### 5.1 Blockiert ein Checkpoint Schreiber?

Nein — jedenfalls nicht der automatische. [wal.html](https://www.sqlite.org/wal.html), 2.2:

> A checkpoint operation takes content from the WAL file and transfers it back into the original database file. A checkpoint can run concurrently with readers, however the checkpoint must stop when it reaches a page in the WAL that is past the end mark of any current reader.

Und dass Schreiber dabei weiterlaufen:

> Whenever a write operation occurs, the writer checks how much progress the checkpointer has made, and if the entire WAL has been transferred into the database and synced and if no readers are making use of the WAL, then the writer will rewind the WAL back to the beginning and start putting new transactions at the beginning of the WAL.

Wichtig für uns: [PRAGMA wal_autocheckpoint](https://www.sqlite.org/pragma.html#pragma_wal_autocheckpoint) — »**All automatic checkpoints are PASSIVE.**« Nur die manuellen Varianten blockieren:

> In applications with many concurrent readers, one might also consider running manual checkpoints with the SQLITE_CHECKPOINT_RESTART or SQLITE_CHECKPOINT_TRUNCATE option … The disadvantage of using SQLITE_CHECKPOINT_RESTART and SQLITE_CHECKPOINT_TRUNCATE is that **readers might block while the checkpoint is running.**

Das Repo ruft keine manuellen Checkpoints; `rg 'wal_checkpoint'` findet nichts. Es bleibt bei PASSIVE.

### 5.2 Wächst die WAL-Datei unter Dauerlast?

Sie wächst bis zur Schwelle und wird dann wiederverwendet. [wal.html](https://www.sqlite.org/wal.html), 2.1 und 2.3:

> By default, SQLite does a checkpoint automatically when the WAL file reaches a threshold size of 1000 pages.

> The default strategy is to allow successive write transactions to grow the WAL until the WAL becomes about 1000 pages in size, then to run a checkpoint operation for each subsequent COMMIT until the WAL is reset to be smaller than 1000 pages.

> The checkpoint does not normally truncate the WAL file (unless the journal_size_limit pragma is set). Instead, it merely causes SQLite to start overwriting the WAL file from the beginning.

Nachgeprüft: `PRAGMA wal_autocheckpoint` = 1000 (Standard), `PRAGMA page_size` = 4096. Die WAL-Datei pendelt damit um **~4 MB**. Das ist kein Problem für einen mehrstündigen Workshop.

### 5.3 Der eine Fall, in dem sie doch wächst

[wal.html](https://www.sqlite.org/wal.html), Abschnitt 6 (Avoiding Excessively Large WAL Files):

> However, if a database has many concurrent overlapping readers and there is always at least one active reader, then no checkpoints will be able to complete and hence **the WAL file will grow without bound.**

Das ist Checkpoint-Starvation: Ein Dauerleser, der seine Lesetransaktion offen hält, hindert jeden Checkpoint am Abschluss.

**Kann das hier passieren?** Nein, und zwar aus einem strukturellen Grund: `CONN_MAX_AGE` ist nicht gesetzt, also 0 — »A value of 0 closes database connections at the end of each request« ([Django, Settings](https://docs.djangoproject.com/en/6.0/ref/settings/)). Jede Anfrage baut ihre Verbindung neu auf und schließt sie am Ende; es gibt keine langlebige Verbindung, die eine Lesetransaktion über Stunden offen hielte. Selbst der längste Vorgang im Repo — die 120 s Transkriptions-Polling — hält gar keine DB-Transaktion (Abschnitt 7). Die von wal.html geforderten »reader gaps« entstehen hier nach jeder einzelnen Anfrage.

## 6. Codebefunde

Alle Angaben am Stand 2026-09-21 nachgeprüft.

### 6.1 Die Konfiguration

`config/settings.py:115-128` (nachgeprüft, Kommentar im Original):

```python
# WAL und ein wartender Writer: Sitzungen mehrerer gleichzeitig angemeldeter
# Browser schreiben parallel in dieselbe SQLite-Datei.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("DATABASE_PFAD", BASE_DIR / "db.sqlite3"),
        "OPTIONS": {
            "init_command": "PRAGMA journal_mode=WAL;",
            "transaction_mode": "IMMEDIATE",
            "timeout": 20,
        },
    }
}
```

Am laufenden Django-Prozess abgefragt, was davon tatsächlich ankommt:

| Größe | Wert | Herkunft |
| --- | --- | --- |
| `PRAGMA journal_mode` | `wal` | `init_command`, persistent in der Datei |
| `connection.transaction_mode` | `IMMEDIATE` | `OPTIONS["transaction_mode"]` |
| `PRAGMA busy_timeout` | `20000` (ms) | `OPTIONS["timeout"] = 20` → `sqlite3.connect(timeout=20)` |
| `PRAGMA synchronous` | `2` (FULL) | **nicht gesetzt**, SQLite-Standard |
| `PRAGMA wal_autocheckpoint` | `1000` | nicht gesetzt, SQLite-Standard |
| `PRAGMA page_size` | `4096` | nicht gesetzt, SQLite-Standard |
| `features.has_select_for_update` | `False` | Djangos SQLite-Backend |

Der Weg von `OPTIONS` zum `BEGIN` ist im Django-Quellcode nachlesbar: `get_connection_params` nimmt `transaction_mode` aus den `OPTIONS`, prüft ihn gegen `frozenset(["DEFERRED", "EXCLUSIVE", "IMMEDIATE"])` und legt ihn auf der Verbindung ab (`base.py:143`, `:181-194`); `_start_transaction_under_autocommit` setzt ihn in das `BEGIN` ein (`base.py:321-331`, oben in 2.4 zitiert). `timeout` bleibt in `kwargs` und wandert unverändert an `sqlite3.connect()` (`base.py:161-165`) — daher die 20.000 ms Busy-Timeout.

### 6.2 `ATOMIC_REQUESTS` und `CONN_MAX_AGE` — bestätigt nicht gesetzt

`rg 'ATOMIC_REQUESTS|CONN_MAX_AGE'` findet im ganzen Repo keine Fundstelle; am laufenden Prozess liefert `settings.DATABASES["default"]` beide Schlüssel gar nicht, Django setzt seine Vorgaben ein: `ATOMIC_REQUESTS = False`, `CONN_MAX_AGE = 0` ([Django, Settings](https://docs.djangoproject.com/en/6.0/ref/settings/)).

Die Folge ist die im Auftrag genannte, und sie ist für die ganze Frage zentral: **Keine Anfrage hält allein dadurch eine Schreibtransaktion, dass sie lange läuft.** Wäre `ATOMIC_REQUESTS = True`, hätte unter `transaction_mode="IMMEDIATE"` *jede* Anfrage die globale Schreibsperre von der ersten bis zur letzten Zeile des View genommen — und die synchrone Transkription mit ihren bis zu 120 s hätte die Datenbank für alle anderen zwei Minuten lang zugenagelt. Das ist genau das Szenario, vor dem Djangos Doku warnt (»the usage of ATOMIC_REQUESTS is discouraged in this case«, oben in 2.4 zitiert), und es ist hier ausgeschlossen.

Daraus folgt umgekehrt eine **harte Betriebsregel für #203**: Wer je `ATOMIC_REQUESTS = True` setzt, kippt diese Recherche. Die beiden Einstellungen sind gekoppelt.

`CONN_MAX_AGE = 0` schließt zusätzlich die Checkpoint-Starvation aus (Abschnitt 5.3).

### 6.3 Die `atomic()`-Blöcke: systematisch geprüft, nichts Langsames darin

Die im Auftrag genannten Blöcke sind bestätigt: `sitzungen/sink.py:149` (`Gespraechsschritt.objects.create` + `Fehlversuch.objects.bulk_create`), `:169` (`answerless_anlegen` + `status_setzen`), `:183` (`Diagnose.objects.create` + `status_setzen`); `erhebungen/ablauf.py:187, 200, 252, 271` — und ein vierter, im Auftrag nicht genannter: `:282` (`bindung_abschliessen`). Alle enthalten ausschließlich ORM-Aufrufe.

Die Prüfung ist über das **ganze** Repo gezogen worden, nicht nur über diese Dateien. Methode: `rg` auf alle `atomic`-Fundstellen (ergibt 43 Blöcke in Produktivcode, ohne Tests, Migrationen und Worktrees) und zusätzlich ein AST-Durchlauf über alle `.py`-Dateien, der jeden `with transaction.atomic()`-Block und jede mit `@transaction.atomic` dekorierte Funktion aufspannt und im gesamten Teilbaum nach Aufrufen sucht, deren Name auf etwas Langsames deutet (`sleep`, `post`, `get`, `request`, `completion`, `antworten`, `transkribieren`, `send`, `urlopen`, `run`, `render`, `read`, `modellverzeichnis`).

Die einzigen Treffer sind harmlos und namensgleich: `objects.get()`, `objects.select_for_update().get()`, `request.POST.get()`. **Kein einziger `atomic()`-Block im Repo umschließt einen Anbieteraufruf, ein `time.sleep`, einen HTTP-Aufruf oder sonst etwas Netzgebundenes.**

Gegenprobe von der anderen Seite, über die Aufrufstellen statt über die Blöcke. Alles Netzgebundene im Produktivcode sitzt an drei Stellen:

- `simulation/sprachmodell/__init__.py:156` (`litellm.completion`) — gerufen aus `simulation/__init__.py:93` (`antwort_versuchen`, bis zu `MAX_VERSUCHE = 3` Durchläufe), gerufen aus `sitzungen/durchlauf.py:72` (`gespraechsschritt_ausfuehren`), gerufen aus `sitzungen/views.py:270` und `:488`. **Auf dieser ganzen Kette gibt es kein `atomic()`.** Der Ablauf ist ausdrücklich so gebaut: Erst `antwort_versuchen` — komplett transaktionsfrei —, dann greift eine der Sink-Methoden, und *die* öffnet ihre kurze Transaktion (`durchlauf.py:85` bzw. `:91`). Der Modellaufruf steht also **vor** dem `BEGIN IMMEDIATE`, nicht darin.
- `simulation/transkription/__init__.py` — siehe Abschnitt 7.
- `simulation/modellverzeichnis.py:298/304` (`httpx.Client`), gerufen aus `simulation/views.py:279`. Auch hier kein umschließendes `atomic()`; außerdem ein reiner Formular-Hilfspfad der Administration, nicht des Workshops.

### 6.4 Die eine Kante: Schreibsperre über ein Template-Rendering

`erhebungen/views.py:629` (`item_hoch`) und `:638` (`item_runter`) tragen `@transaction.atomic` als Dekorator und geben `_itemreihenfolge_aendern(...)` zurück, das mit `return detail(request, pk)` endet (`:623`). `detail` (`:286-387`) führt mehrere Abfragen aus und endet mit einem `render(...)` der vollständigen Detailseite. **Die Schreibsperre wird hier also über das Rendern einer ganzen HTML-Seite gehalten** — Größenordnung einige Millisekunden bis wenige Zehntelsekunden, je nach Zahl der Vignetten und Items.

Ähnlich, wenn auch harmloser: `konfiguration_speichern` (`:672`) trägt den Dekorator ebenfalls und liest `request.POST` innerhalb der Transaktion (`:681-690`) — das ist bereits geparst, also kein I/O.

Beides kippt die Entscheidung nicht: Es sind Forschenden-Pfade der Erhebungsverwaltung, keine Teilnehmenden-Pfade; sie laufen nicht während eines Workshops und nicht zu zehnt gleichzeitig. Es ist aber der einzige Ort im Repo, an dem eine Transaktion länger offen steht, als sie müsste, und damit der erste Kandidat, falls je doch Sperrkonflikte auftauchen.

### 6.5 Die versteckte zweite Schreibtransaktion: das Sitzungs-Backend

`SESSION_ENGINE` ist in `config/settings.py` nicht gesetzt; Django verwendet damit `django.contrib.sessions.backends.db`, und `SessionMiddleware` steht in `MIDDLEWARE` (`config/settings.py:82`). **Jede Anfrage, die die Session verändert, schreibt eine Zeile in `django_session`** — als eigene, autocommittete Schreibtransaktion.

Das ist im Gesprächspfad der Regelfall, nicht die Ausnahme: `sitzungen/sink.py:240-262` (`zeitbudget_fortsetzen` / `zeitbudget_anhalten`) schreibt in `self.session`, und `gespraechsschritt_ausfuehren` ruft beide bei jedem Schritt (`durchlauf.py:76`, `:96`). Pro Gesprächsschritt fällt also **eine** Transaktion für den Schritt selbst und **eine** für die Session an.

Der Befund aus dem Auftrag — »eine Schreibtransaktion je Gesprächsschritt« — ist damit um den Faktor 2 zu korrigieren. Abschnitt 8 rechnet mit dem korrigierten Wert.

## 7. Die Transkription: 120 s außerhalb jeder Transaktion

Bestätigt. `simulation/transkription/__init__.py` führt `TRANSKRIPTION_BUDGET_SEKUNDEN = 120.0` (`:19`) und pollt bei Infomaniak in einer Schleife mit `time.sleep(INFOMANIAK_INTERVALL_SEKUNDEN)` bei 2,0 s Abstand (`:147`, `:26`).

Der Endpunkt, der das ruft, ist `sitzungen/views.py:345-371`. Er

- prüft Methode, Sitzung, Einwilligung, das Zero-Retention-Tor und die Aufnahmegrenze aus #196 (`settings.TRANSKRIPTION_MAX_AUFNAHME_BYTES`),
- ruft `anbieter_bilden().transkribieren(audio)` (`:364`),
- und gibt eine `JsonResponse` mit dem Text zurück.

**Er öffnet kein `atomic()` und schreibt überhaupt nichts in die Datenbank** — das Transkript geht als JSON an den Browser zurück und wird erst persistiert, wenn die Person es als Eingabe eines Gesprächsschritts abschickt. Die 120 s liegen damit vollständig außerhalb jeder Transaktion.

Das ist die Pointe für #203: **Das Polling verlängert die Worker-Haltezeit, aber es verlängert die Schreibsperre um exakt null.** Die im Ticket beschriebene Verschärfung ist real — sie ist aber eine Worker-Frage, keine Datenbankfrage. Die beiden Hälften der Beobachtung aus #203 sind voneinander unabhängig; diese Notiz beantwortet nur die zweite.

Nebenbei ist der Zusammenhang im Code bereits so kommentiert (`:15-18`): Die 120 s lassen »60 s Luft zum Worker-Timeout des Deployments (180 s, README)« — `--timeout 180` in `README.md:322`, gegenüber gunicorns Vorgabe von 30 s.

## 8. Die Rechnung

### 8.1 Woher die Schreibvorgänge kommen

Aus Abschnitt 6 abgeleitet, pro Gesprächsschritt einer teilnehmenden Person:

| Schreibtransaktion | Fundstelle | Inhalt |
| --- | --- | --- |
| Gesprächsschritt + Fehlversuche | `sitzungen/sink.py:149` | 1 `INSERT` + 0–2 `INSERT` |
| Sitzung (Zeitbudget) | `SessionMiddleware`, aus `sink.py:262` | 1 `UPDATE` |

= **2 Schreibtransaktionen je Gesprächsschritt.** Dazu kommen seltene Einzelereignisse: Sitzung anlegen, Statuswechsel, Diagnose, Itemblöcke (`erhebungen/ablauf.py:252`, `:271`), Bindung abschließen. Über eine Vignette gerechnet sind das eine Handvoll gegenüber Dutzenden Gesprächsschritten; als Aufschlag reicht **Faktor 1,5**. Rechengröße: **3 Schreibtransaktionen je Gesprächsschritt.**

### 8.2 Wie schnell Gesprächsschritte entstehen

Der Takt ist durch den Modellaufruf und den Menschen gesetzt, nicht durch die Datenbank. Ein Schritt braucht:

- **Modellaufruf:** ein `litellm.completion` mit strukturierter Ausgabe, realistisch 3–10 s; bei Formatbruch bis zu drei Versuche (`MAX_VERSUCHE = 3`, `simulation/__init__.py:91`).
- **Mensch:** Antwort lesen und eine Eingabe verfassen — im Workshop eher 20–60 s, mit Spracheingabe zuzüglich Aufnahme und Transkription.

Pro Person also ein Gesprächsschritt alle **25–70 s**. Für die Rechnung wird der günstige Rand genommen: **ein Schritt alle 25 s**.

### 8.3 Erwartete Schreibrate bei zehn gleichzeitig Teilnehmenden

$$\frac{10 \text{ Personen}}{25 \text{ s/Schritt}} \times 3 \frac{\text{Transaktionen}}{\text{Schritt}} = 1{,}2 \frac{\text{Transaktionen}}{\text{s}}$$

Dagegen ein bewusst absurder Deckel: Angenommen, niemand liest und niemand tippt, und das Modell antwortet in 2 s — zehn Personen im Dauerfeuer:

$$\frac{10}{2\,\text{s}} \times 3 = 15 \frac{\text{Transaktionen}}{\text{s}}$$

Dieser Fall kann nicht eintreten, solange die Anzahl der Worker die Nebenläufigkeit deckelt (Abschnitt 1.3), aber er taugt als Obergrenze.

### 8.4 Gegenüberstellung

| | Schreibrate | Verhältnis zur Kapazität |
| --- | --- | --- |
| **Erwartet** (10 Personen, 25-s-Takt) | ~1,2/s | |
| **Absurde Obergrenze** (Dauerfeuer) | ~15/s | |
| **Kapazität, schlechtester dokumentierter Fall** (rotierende Platte, `synchronous=FULL`, FAQ 19) | ~60/s | **50-facher** Abstand zur Erwartung, 4-facher zur Obergrenze |
| **Kapazität, realistischer Fall** (SSD, `synchronous=FULL`, abgeleitet) | einige Hundert bis Tausend/s | **100- bis 1000-facher** Abstand |

**Sicherheitsabstand in Größenordnungen: mindestens 1,5, realistisch 2 bis 3.** Selbst der ungünstigste Fall, den sqlite.org überhaupt beschreibt — eine rotierende Platte, auf der jedes Commit auf eine Plattenumdrehung wartet —, trägt die erwartete Last fünfzigfach.

### 8.5 Wie lange wartet ein blockierter Schreiber?

Die andere Hälfte der Frage: nicht der Durchsatz, sondern die Wartezeit. Eine Schreibtransaktion dauert hier `n × INSERT` + ein `fsync`. Der `fsync` dominiert. Im schlechtesten Fall (16 ms, rotierende Platte) und bei `--workers 3`, also höchstens drei gleichzeitigen Schreibern, wartet der letzte höchstens `2 × 16 ms = 32 ms`. Bei einem Wechsel auf `gthread` mit `--threads 8`, also 24 potenziellen Schreibern, wären es höchstens `23 × 16 ms ≈ 370 ms`.

Dem steht `busy_timeout = 20 000 ms` gegenüber. Der Abstand beträgt **rund zwei Größenordnungen selbst im gethreadeten Fall auf rotierender Platte**; auf SSD sind es vier. Und weil `transaction_mode="IMMEDIATE"` dafür sorgt, dass dieses Warten überhaupt am Busy-Handler ankommt (Abschnitt 2), ist es tatsächlich ein Warten und kein Fehler.

### 8.6 Was die Rechnung kippen würde

Ehrlichkeitshalber die Bedingungen, unter denen das Ergebnis nicht mehr gilt:

1. **`ATOMIC_REQUESTS = True`.** Dann hält jede Anfrage die globale Schreibsperre über ihre ganze Laufzeit — bei der Transkription also bis zu 120 s. Ein einziger Teilnehmer legte damit alle anderen lahm. Djangos Doku rät davon unter `IMMEDIATE` ausdrücklich ab (2.4).
2. **Ein Anbieteraufruf wandert in ein `atomic()`.** Heute nirgends der Fall (6.3), aber es ist die eine Änderung, die aus einer Millisekunden-Transaktion eine Sekunden-Transaktion machte. Die Rechnung in 8.3 skalierte dann mit der Modelllatenz statt mit der `fsync`-Latenz — bei 5 s Modellaufruf und 10 Personen wäre die Sperre dauerhaft belegt.
3. **Die Datenbankdatei auf einem Netzdateisystem.** Dann läuft WAL gar nicht (Abschnitt 4).
4. **Ein Größensprung um zwei Zehnerpotenzen** — also 1000 statt 10 gleichzeitig Teilnehmende. Das ist kein Workshop mehr.

Punkt 1 und 2 sind als Vertragstest oder als Zeile in einem ADR sicherbar; Punkt 3 fällt im Betrieb sofort auf.

## 9. Was daraus für #203 folgt

- **Die Datenbankfrage ist entschieden, und zwar zugunsten der bestehenden Konfiguration.** Ein Lastgenerator ist nicht nötig; er würde die Zahlen aus 8.4 bestätigen und nichts hinzufügen, was nicht aus `fsync`-Latenz und Transaktionslänge folgte.
- **Die Worker-Frage bleibt offen.** Sie ist von der Datenbankfrage unabhängig (Abschnitt 7): Das Polling hält einen Worker, aber keine Sperre. Ob `--worker-class gthread --threads N` genügt oder eine Aufgabenwarteschlange nötig ist, entscheidet sich an der Haltezeit und am Speicherbedarf, nicht an SQLite. Aus Sicht der Datenbank spricht gegen den Thread-Worker nichts: Auch `3 × 8 = 24` potenzielle Schreiber bleiben zwei Größenordnungen unter der Kapazität (8.5).
- **`synchronous=NORMAL` bleibt als Reserve**, ist aber nicht nötig und kostet Dauerhaftigkeit bei Stromausfall (3.2). Nicht ohne Not anfassen.

## Folgen für das Repo

Bei positiver Entscheidung:

- Ticket oder ADR-Notiz: `ATOMIC_REQUESTS` bleibt aus und `CONN_MAX_AGE` bleibt 0 — beides ist unter `transaction_mode="IMMEDIATE"` tragende Auslegung, nicht Zufall (6.2, 8.6). Der bestehende Kommentar in `config/settings.py:115-116` erklärt nur WAL; die IMMEDIATE-Begründung fehlt dort.
- Ticket: `erhebungen/views.py:629/638` — `@transaction.atomic` vom View auf `_item_verschieben` zusammenziehen, damit die Schreibsperre nicht über `detail()` samt Rendering steht (6.4).
- In #203 festhalten, dass die Frage »Trägt SQLite mit WAL die erhöhte Schreib-Nebenläufigkeit?« beantwortet ist, und das Ticket auf die verbleibende Worker-Frage verengen.
- Kein Bedarf an: Lastgenerator, `synchronous`-Änderung, `journal_size_limit`, manuellen Checkpoints, Wechsel des Datenbank-Backends.

## Quellen

- sqlite.org, [Write-Ahead Logging (`wal.html`)](https://www.sqlite.org/wal.html) — ein Schreiber zur Zeit (2.2), Leser blockieren nicht (1), wal-index im geteilten Speicher und Scheitern auf Netzdateisystemen (1, 2.2), Checkpoint nebenläufig zu Lesern (2.2), Auto-Checkpoint bei 1000 Seiten (2.1, 2.3), `synchronous`-Verhalten beim Commit (2.3), Checkpoint-Starvation und `journal_size_limit` (6), »WAL works best with smaller transactions« (1).
- sqlite.org, [`BEGIN TRANSACTION` (`lang_transaction.html`)](https://www.sqlite.org/lang_transaction.html) — DEFERRED stuft hoch »or return SQLITE_BUSY«; IMMEDIATE nimmt die Schreibsperre sofort; EXCLUSIVE und IMMEDIATE sind unter WAL gleich.
- sqlite.org, [Result and Error Codes (`rescode.html`)](https://www.sqlite.org/rescode.html) — `SQLITE_BUSY` (5) mit der ausdrücklichen Empfehlung zu `BEGIN IMMEDIATE` und der Garantie »no subsequent operations … will return SQLITE_BUSY«; `SQLITE_BUSY_SNAPSHOT` (517) als WAL-Upgrade-Fehler.
- sqlite.org, [`sqlite3_busy_handler()`](https://www.sqlite.org/c3ref/busy_handler.html) — der Busy-Handler wird **nicht** gerufen, wenn SQLite einen Deadlock erkennt; `busy_timeout` ist über diesen Handler implementiert.
- sqlite.org, [PRAGMA-Referenz (`pragma.html`)](https://www.sqlite.org/pragma.html) — `busy_timeout`, `journal_mode` (WAL ist persistent; die zweite Form gibt den tatsächlichen Modus zurück), `synchronous` (FULL/NORMAL im WAL-Modus, Dauerhaftigkeitsmatrix), `wal_autocheckpoint` (Standard 1000, »All automatic checkpoints are PASSIVE«).
- sqlite.org, [FAQ (`faq.html`)](https://www.sqlite.org/faq.html) — Frage 19: »it will only do a few dozen transactions per second … about 60 transactions per second« auf 7200 RPM, `synchronous=OFF` als Hebel, Nachtrag 2024-11-19; Frage 5: nur ein schreibender Prozess, `SQLITE_BUSY` als Standardverhalten.
- sqlite.org, [File Locking And Concurrency In SQLite Version 3 (`lockingv3.html`)](https://www.sqlite.org/lockingv3.html) — Sperrzustände, »Only a single RESERVED lock may be active at one time«, `SQLITE_BUSY` beim gescheiterten RESERVED-Erwerb.
- Django 6.0, [Databases — SQLite notes](https://docs.djangoproject.com/en/6.0/ref/databases/) — »database is locked«, `timeout` (»it won't really do anything to solve them«), `transaction_mode` und die Empfehlung zu `IMMEDIATE`, Abraten von `ATOMIC_REQUESTS` unter IMMEDIATE.
- Django 6.0, [Settings-Referenz](https://docs.djangoproject.com/en/6.0/ref/settings/) — `ATOMIC_REQUESTS` (Default `False`), `CONN_MAX_AGE` (Default `0`, Verbindung wird am Anfrageende geschlossen).
- Django 6.0.7, lokal geprüft: `django/db/backends/sqlite3/base.py:143` (`transaction_modes`), `:161-165` (`timeout` geht an `sqlite3.connect`), `:181-197` (`transaction_mode` und `init_command`), `:321-331` (`BEGIN {mode}`); `django/db/backends/sqlite3/features.py` bzw. `connection.features.has_select_for_update = False`.
- gunicorn, [Settings](https://gunicorn.org/reference/settings/) — `workers` (Default 1, »2-4 x $(NUM_CORES)«), `worker_class` (Default `sync`, u. a. `gthread`), `threads` (Default 1, »only affects the Gthread worker type«; `sync` mit `threads > 1` wird zu `gthread`), `timeout` (Default 30).
- Repo, am 2026-09-21 nachgeprüft: `config/settings.py:115-128`; Abfrage der effektiven Pragmas über Djangos Verbindung (`journal_mode=wal`, `synchronous=2`, `busy_timeout=20000`, `wal_autocheckpoint=1000`, `page_size=4096`, `transaction_mode='IMMEDIATE'`, SQLite-Bibliothek 3.45.1); `rg`- und AST-Durchlauf über alle `atomic()`-Blöcke des Produktivcodes; `sitzungen/sink.py:149,169,183,240-262`; `sitzungen/durchlauf.py:63-107`; `sitzungen/views.py:270,345-371,488`; `simulation/__init__.py:74-108`; `simulation/transkription/__init__.py:19,26,132-147`; `erhebungen/ablauf.py:187,200,252,271,282,294`; `erhebungen/views.py:286-387,613-642,672-702,971,1080,1171`; `training/views.py:418,428,485,561`; `README.md:322`.
