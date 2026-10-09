---
status: accepted
---

# Wartende Anfragen halten einen Thread, keine Warteschlange

Zwei Pfade halten ihre Anfrage, bis ein Anbieter antwortet: der
**Gesprächsschritt** (höchstens 90 s über alle Versuche, legitim 20–60 s bei
Reasoning-Modellen) und die **Transkription** (höchstens 120 s, bei Infomaniak
durch Polling). Mit drei synchronen gunicorn-Workern staute sich ab der vierten
gleichzeitig wartenden Anfrage alles Weitere (#203).

**Lastannahme:** Das Werkzeug läuft in Seminaren von etwa 30 Studierenden;
vorbereitet sein muss es auf fünf Seminargruppen gleichzeitig, also **150
gleichzeitige Sitzungen**. Eine Person steckt etwa 40–60 % ihrer Zeit in einer
wartenden Anfrage; im Mittel sind das 60–90 gehaltene Anfragen, bei
gleichzeitigem Seminarstart bis zu 150.

**Entscheidung:** gunicorn läuft mit dem Thread-Worker `gthread`, **3 Prozesse ×
60 Threads = 180** gleichzeitige Anfragen, und `--worker-connections 60`. Der
Arbeitsspeicher hängt am Prozess, nicht am Thread: Ein Worker mit Django und
litellm belegt gemessen rund 230 MB, 60 wartende Threads kommen auf wenige MB
dazu. Drei Prozesse lassen vom Uberspace-Limit (1,5 GB) Platz für den
Evallauf-Prozess aus ADR-0047 und für Spitzen durch Audio-Uploads; vier
Prozesse würden ihn halbieren. Die 30 Threads über 150 bleiben für
Seitenaufrufe von Studierenden, deren Anfrage gerade nicht wartet, und für
Lehrende. `--worker-connections` gleich der Threadzahl verhindert, dass ein voll
belegter Prozess weitere Verbindungen annimmt und hinter seinen Threads staut,
während andere frei sind. Zahlen und Quellen stehen in
`docs/research/2026-10-08-worker-belegung-uberspace-anbieter.md`.

## Considered Options

- **Mehr synchrone Worker** — verworfen. 150 Prozesse à 230 MB sprengen das
  Speicherlimit um eine Größenordnung.
- **Aufgabenwarteschlange für Gesprächsschritt und Transkription** (Celery, RQ
  oder die Datenbank-Warteschlange aus ADR-0047) — verworfen. Die
  Teilnehmer:in wartet ohnehin auf Antwort bzw. Transkript; eine Warteschlange
  verlagerte das Warten nur vom Worker in ein Browser-Polling und senkte die
  Zahl gleichzeitiger Anbieteraufrufe nicht. Ein wartender Thread ist billig.
  Die Warteschlange aus ADR-0047 bleibt den Evalläufen vorbehalten.
- **ASGI mit async Views** — verworfen. Das trüge dieselbe Last, verlangte aber
  async-Nähte zu beiden Anbietern und zur Datenbank.

## Consequences

- **`--timeout` begrenzt keine einzelne Anfrage mehr.** Beim Thread-Worker
  meldet sich der Prozess weiter, solange seine Threads warten; gunicorn tötet
  nur einen hängenden Prozess. Die Haltezeit begrenzen allein die beiden Nähte
  selbst (`SPRACHMODELL_FRIST_SEKUNDEN`, `TRANSKRIPTION_BUDGET_SEKUNDEN`), von
  außen das Uberspace-Frontend, das eine Verbindung nach drei Minuten ohne Daten
  schließt.
- **Der Produktivcode läuft unter mehreren Threads je Prozess.** Geprüft wurde
  er am 2026-10-08 auf veränderlichen Zustand auf Modulebene, geteilte
  HTTP-Clients, Caches und Singletons, vor allem an den Nähten
  (`simulation/__init__.py`, `simulation/sprachmodell/`,
  `simulation/transkription/`, `simulation/modellverzeichnis.py`) und am
  Markdown-Renderer (`texte/markdown.py`). Gefunden wurde nichts, was einen
  Eingriff braucht: Sprachmodell-Adapter, Transkriptions-Adapter samt
  HTTP-Client und Modellverzeichnis werden je Anfrage neu gebildet, die
  Konstanten auf Modulebene werden nur gelesen, die geteilten
  `MarkdownIt`-Parser halten ihren Zustand je Aufruf. Einzig
  `FakeSprachmodell.letzte_anfragen` ist eine geteilte Liste; sie dient den
  Tests, `append` ist atomar, und produktiv antwortet kein Fake.
- **Bis zu 180 Anbieteraufrufe gleichzeitig.** OpenRouter setzt für bezahlte
  Modelle keine Plattformgrenze; für Infomaniak ist die Grenze der KI-Routen
  nicht belegt. Vor einem Einsatz mit fünf Seminargruppen über Infomaniak ist
  sie beim Anbieter zu erfragen (Rechercheeintrag, Abschnitt 3).
- **SQLite trägt die Nebenläufigkeit**, mit kleinerem Abstand als bei zehn
  Teilnehmenden: Nachtrag vom 2026-10-08 in
  `docs/research/2026-09-21-sqlite-nebenlaeufigkeit-wal.md`.
