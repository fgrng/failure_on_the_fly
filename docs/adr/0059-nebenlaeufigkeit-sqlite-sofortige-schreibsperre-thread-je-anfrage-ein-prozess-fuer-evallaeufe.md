---
status: accepted
---

# Nebenläufigkeit: SQLite mit sofortiger Schreibsperre, ein Thread je wartender Anfrage, ein Prozess für Evalläufe

Dieses ADR fasst den Stand von ADR-0047 (samt Nachführung durch ADR-0050) und
ADR-0050 zusammen und ersetzt beide. Es zieht außerdem die
Nebenläufigkeitsaussagen aus ADR-0016 (SQLite) und ADR-0037 (`atomic()` statt
`select_for_update()`) an einen Ort. Die Betriebszahlen (Prozesse, Threads,
Speicher, Hoster-Limits) stehen in `docs/DEPLOYMENT.md` und der Recherche
`docs/research/2026-10-08-worker-belegung-uberspace-anbieter.md`; hier stehen
die Regeln.

## Lastannahme

Das Werkzeug läuft in Seminaren von etwa 30 Studierenden; vorbereitet sein
muss es auf fünf Seminargruppen gleichzeitig, also **150 gleichzeitige
Sitzungen**. Zwei Pfade halten ihre Anfrage, bis ein Anbieter antwortet: der
**Gesprächsschritt** (bis zu `SPRACHMODELL_FRIST_SEKUNDEN` über alle Versuche,
legitim 20 bis 60 s bei Reasoning-Modellen) und die **Transkription** (bis zu
`TRANSKRIPTION_BUDGET_SEKUNDEN`). Eine Person steckt etwa 40 bis 60 % ihrer
Zeit in einer wartenden Anfrage.

## Eine wartende Anfrage hält einen Thread, keine Warteschlange

gunicorn läuft mit dem **Thread-Worker** (`gthread`): wenige Prozesse mit
vielen Threads. Der Arbeitsspeicher hängt am Prozess, ein wartender Thread
kostet wenige Kilobyte. Die Teilnehmer:in wartet ohnehin auf Antwort oder
Transkript; eine Aufgabenwarteschlange verlagerte das Warten nur vom Worker in
ein Browser-Polling und senkte die Zahl gleichzeitiger Anbieteraufrufe nicht.

Daraus folgt, was die Haltezeit begrenzt: **nicht `--timeout`**. Beim
Thread-Worker meldet sich der Prozess weiter, solange seine Threads warten;
gunicorn tötet nur einen hängenden Prozess. Die Haltezeit begrenzen allein die
Fristen der Nähte (`SPRACHMODELL_FRIST_SEKUNDEN`,
`TRANSKRIPTION_BUDGET_SEKUNDEN`) und von außen das Frontend des Hosters, das
eine Verbindung ohne Daten nach einigen Minuten schließt. `--worker-connections`
ist gleich der Threadzahl, damit ein voll belegter Prozess keine Verbindungen
annimmt und hinter seinen Threads staut, während andere frei sind.

**Der Produktivcode läuft unter mehreren Threads je Prozess** und muss
dafür frei von veränderlichem Zustand auf Modulebene sein: Sprachmodell-Adapter,
Transkriptions-Adapter samt HTTP-Client und Modellverzeichnis werden je Anfrage
neu gebildet; Konstanten auf Modulebene werden nur gelesen; die geteilten
`MarkdownIt`-Parser halten ihren Zustand je Aufruf. Der Fake-Sprachmodell-
Adapter hält keine geteilte Liste; Tests zeichnen ihre Anfragen je Test über
`config.tests.sprachmodell.anfragen_aufzeichnen` auf (#379). Wer einen Cache,
ein Singleton oder einen geteilten Client einführt, begründet dessen
Threadsicherheit.

## SQLite trägt die Nebenläufigkeit, mit sofortiger Schreibsperre

Das Projekt läuft auf **SQLite**, nicht auf Postgres. Der Wechsel ist billig,
solange keine Forschungsdaten existieren; die Datenbank ist eine Datei im Home
der Instanz. Sie läuft im **WAL-Modus** mit `transaction_mode: IMMEDIATE`
(`config/settings.py`): Jedes `atomic()` öffnet mit `BEGIN IMMEDIATE` und nimmt
die Schreibsperre sofort, statt sie beim ersten Schreibbefehl zu erwerben und
dann an einem konkurrierenden Schreiber zu scheitern. Leser blockieren Schreiber
nicht und umgekehrt. Die Nachträge in
`docs/research/2026-09-21-sqlite-nebenlaeufigkeit-wal.md` belegen den Abstand
unter der Lastannahme.

Daraus folgen drei Regeln:

- **Serialisiert wird über `atomic()`.** Djangos SQLite-Backend meldet
  `has_select_for_update = False`; `select_for_update()` erzeugt hier kein SQL
  und keinen Fehler, es tut schlicht nichts. Die tragende Sicherung ist die
  sofortige Schreibsperre der Transaktion. Wo `select_for_update()` im Code
  steht (Ablauf, Trainingsstart), dokumentiert es die Zeilensperre, die ein
  Backend mit Sperrunterstützung nähme; es darf nicht als tragende Sicherung
  gelesen werden, und der Eigentümer-Kreis verzichtet ausdrücklich darauf
  (ADR-0037). Mit einem Backend-Wechsel wird `select_for_update()` wieder das
  richtige Mittel.
- **Kein Modellaufruf hält eine Schreibsperre.** Gespräche und Urteile werden
  in kurzen Einzelschritten geschrieben; ein Anbieteraufruf findet außerhalb
  jeder Transaktion statt.
- **Kein Rendern in einer Transaktion.** Schreibaktionen leiten nach dem Commit
  weiter und rendern erst danach (ADR-0040); GET-Ansichten lesen außerhalb
  einer Schreibtransaktion, auch bei finalen und überholten Fassungen (#249,
  #409). Mehr Threads halten die globale Schreibsperre sonst öfter.

## Evalläufe laufen in einem eigenen Prozess, die Datenbank ist die Warteschlange

Ein Evallauf (ADR-0046) sprengt jede Anfrage: Bei einer Handvoll Evals mit je
zwei Evalinputs, *k* = 3 und drei Inputschritten kommen gut zweihundert
Modellaufrufe zusammen, nacheinander zwanzig bis vierzig Minuten. Er wird
deshalb von einem **eigenen Prozess** abgearbeitet: dem Management-Command
`evallaeufe_abarbeiten`, das als zweiter supervisord-Dienst neben gunicorn
läuft. Der Zustand des Evallaufs ist die Warteschlange; eine eigene
Queue-Infrastruktur gibt es nicht, und diese Warteschlange bleibt den
Evalläufen vorbehalten.

Der Prozess arbeitet **einen Evallauf nach dem anderen** ab, instanzweit; das
ist zugleich die Kostenbremse und hält die Anbieterlimits ein. Je
Vignettenfassung wartet oder läuft höchstens einer. Er hält eine exklusive
Sperre, damit nie zwei Hintergrundprozesse arbeiten, und erklärt beim Start
alles, was noch „läuft", zu Waisen eines abgebrochenen Vorgängers. Bricht der
Prozess mitten in einem Lauf ab, bleibt der Evallauf **abgebrochen** stehen;
was fertig war, bleibt sichtbar. Fortgesetzt wird nicht, er wird neu
ausgelöst. SIGTERM von supervisord beendet einen laufenden Lauf als
abgebrochen, statt ihn als laufend liegen zu lassen.

Der Hintergrundprozess schreibt in dieselbe SQLite-Datei wie gunicorn und liest
dieselbe Umgebung. Bei einem Lauf nach dem anderen ist das eine zusätzliche
Schreiberin, keine Last. Er ist das Fundament für eine spätere Regressionsreihe
über viele Vignetten.

## Erwogene Optionen

- **Mehr synchrone Worker** — verworfen. 150 Prozesse sprengen das
  Speicherlimit der Instanz um eine Größenordnung.
- **Aufgabenwarteschlange für Gesprächsschritt und Transkription** (Celery,
  RQ oder die Datenbank-Warteschlange der Evalläufe) — verworfen. Sie
  verlagerte das Warten in ein Browser-Polling und senkte die Zahl
  gleichzeitiger Anbieteraufrufe nicht.
- **ASGI mit async Views** — verworfen. Trüge dieselbe Last, verlangte aber
  async-Nähte zu beiden Anbietern und zur Datenbank.
- **Evallauf synchron in der Anfrage** — unmöglich; das Frontend schließt die
  Verbindung lange vorher.
- **Der Browser treibt den Evallauf** per HTMX, Evalgespräch für Evalgespräch
  — verworfen. Jede Anfrage belegte einen Thread und konkurrierte mit
  laufenden Erhebungen; ein geschlossener Tab bräche den Lauf ab.
- **Evallauf nur als Management-Command für Administrator:innen** —
  verworfen. Der Evallauf ist ein Werkzeug der Autor:in.
- **Eine Worker-Bibliothek mit eigenem Broker** — verworfen. Ein Dienst, eine
  Abhängigkeit und ein Betriebsrisiko mehr für einen Anwendungsfall, dessen
  Durchsatz ein Lauf nach dem anderen ist.
- **Postgres von Anfang an** — verworfen. Die Schlussfolgerung „kein
  Repository-Interface" (ADR-0055) hängt daran, dass *eine* Datenbank fest
  verdrahtet ist, nicht daran, welche; SQLite reicht für die Lastannahme und
  ist auf der Zielinstanz das einfachste Deployment.

## Folgen

- Die Instanz betreibt zwei Prozesse; `docs/DEPLOYMENT.md` beschreibt beide
  samt der Zahlen, die sich mit dem Hoster ändern dürfen, ohne dass dieses ADR
  nachgeführt wird.
- Bis zu so viele Anbieteraufrufe gleichzeitig, wie Threads bereitstehen.
  OpenRouter setzt für bezahlte Modelle keine Plattformgrenze; für Infomaniak
  ist die Grenze der KI-Routen vor einem Einsatz mit fünf Seminargruppen beim
  Anbieter zu erfragen.
- Ein Backend-Wechsel nimmt die Regel „`atomic()` statt `select_for_update()`"
  zurück; die Stellen sind benannt und klein.
- Wer Hintergrundarbeit jenseits der Evalläufe braucht, argumentiert gegen
  dieses ADR, nicht mit der vorhandenen Warteschlange.
