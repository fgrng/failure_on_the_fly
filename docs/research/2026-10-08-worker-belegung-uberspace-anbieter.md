# Worker-Belegung: Grenzen von Uberspace und Anbietern für 150 gleichzeitige Sitzungen

Erfüllt den Rechercheteil von [#203](https://github.com/fgrng/failure_on_the_fly/issues/203). Die Lastannahme (fünf Seminargruppen à ~30 Studierende, also 150 gleichzeitige Sitzungen) und die Entscheidung für Thread-Worker stehen in ADR-0050. Hier steht, was die Auslegung von außen begrenzt, und was davon belegt ist.

Stand: 2026-10-08. Alle Quellen am 2026-10-08 abgerufen. Lokal gemessen mit gunicorn 26.2.0 (`uv.lock`), CPython 3.14, Django 6.0.7 und litellm aus `uv.lock`, unter Linux (WSL2).

## Gist

- **Uberspace trägt 3 × 60 Threads.** 1536 MB Arbeitsspeicher, 1024 Prozesse/Threads, drei Minuten Leerlauf bis zum Verbindungsabbruch im Frontend. Gebraucht werden rund 720 MB und etwa 190 Threads; die längste Haltezeit (120 s) bleibt unter drei Minuten.
- **OpenRouter setzt für bezahlte Modelle keine Plattformgrenze**, wohl aber die Upstream-Anbieter, ohne Zahl. Die Transkription über OpenRouter bricht beim Upstream nach **60 s** ab, vor dem eigenen Budget von 120 s.
- **Für Infomaniak ist die Grenze der KI-Routen unbelegt.** Die allgemeine API-Grenze von 60 Anfragen/min ist belegt, ihre Geltung für AI Tools nicht. Gälte sie, läge sie weit unter dem Bedarf (Abschnitt 3).

## 1. Uberspace 7

| Grenze | Wert | Beleg |
| --- | --- | --- |
| Arbeitsspeicher | 1536 MB | »You can use up to 1536 MB (1.5 GB) of RAM. If you try to use more than this limit, your process will be killed.« ([basics-resources](https://manual.uberspace.de/basics-resources/)) |
| CPU | keine feste Zahl | »Every Uberspace gets a fair slice of CPU time. If the CPU is idle, you can use more than that. Processes that try to use too much CPU resources will be throttled.« (ebd.) |
| Prozesse/Threads | 1024 | »Increased the process limit to `1024` (up from `400`).« ([Changelog 7.6.1, 2020-04-23](https://github.com/Uberspace/manual/blob/main/source/changelog/2020-04-23_7.6.1.rst)); dass die Grenze Threads mitzählt: »The maximum number of processes/threads is now 400 instead of 300« ([Changelog 7.0.22, 2017-12-20](https://github.com/Uberspace/manual/blob/main/source/changelog/2017-12-20_7.0.22.rst)) |
| Leerlauf einer Verbindung im Frontend | 3 min | »Idle HTTP connections are shut down after three minutes.« ([web-backends](https://manual.uberspace.de/web-backends/)) |
| Weg der Anfrage | Frontend → Backend direkt | »Using web backends you can connect your applications directly to our frontend […] Traffic is proxied transparently to your application« (ebd.) |

Die beiden Changelog-Einträge stehen im offiziellen Manual-Repository, nicht mehr auf der Live-Seite des Changelogs.

### 1.1 Speicherbedarf, gemessen

Ein gunicorn-Worker mit geladenem `config.wsgi`, litellm, openai und httpx belegt **~225–230 MB RSS**. 40 bzw. 60 Threads, die in einer wartenden Anfrage schlafen, erhöhen das um 1–2 MB. Der Master-Prozess belegt ~28 MB.

| Aufteilung | Gleichzeitig | RSS gunicorn | Rest bis 1536 MB |
| --- | --- | --- | --- |
| 3 × 60 | 180 | ~720 MB | ~810 MB |
| 4 × 40 | 160 | ~950 MB | ~590 MB |

Vom Rest gehen ein Evallauf-Prozess nach ADR-0047 (ein weiterer Django-Prozess, geschätzt wie ein Worker ~230 MB), SSH-Sitzungen, das Backup und Spitzen je Anfrage ab. Die größte Spitze ist eine Aufnahme: bis zu 15 MB (`TRANSKRIPTION_MAX_AUFNAHME_BYTES`), im Prozess mehrfach kopiert. Ein Redebeitrag von unter einer Minute liegt in Opus/WebM bei wenigen Hundert KB; die Obergrenze ist der seltene Fall. Daraus folgen **drei** Prozesse.

**Unbelegt:** ob Uberspace das Limit an RSS oder am virtuellen Speicher misst. Ein Worker mit 60 Threads reserviert ~4,6 GB virtuell (Thread-Stacks), belegt davon aber nur ~230 MB. Das Handbuch spricht von »RAM«; bei einem OOM-Kill trotz niedriger RSS wäre das die erste Vermutung.

### 1.2 Threads

3 × (60 Threads + Hauptthread und gunicorn-Hilfsthread) + Master ≈ 190 Threads; mit Evallauf-Prozess und Shell etwa 200 von 1024.

### 1.3 Haltezeit gegen Frontend

Gesprächsschritt 90 s und Transkription 120 s bleiben unter den drei Minuten, nach denen das Frontend eine Verbindung ohne Daten schließt. Diese Grenze ersetzt, was bisher `--timeout 180` versprach: Beim Thread-Worker bricht gunicorn keine einzelne Anfrage ab (Abschnitt 4).

**Unbelegt:** ein eigener Lese-Timeout des Frontend-Proxys neben dem Leerlauf. Gesucht im Manual-Repository, im Uberlab-Repository und im Web nach »timeout«, »proxy« und »504«; dokumentiert ist nur der Leerlauf.

**Unbelegt:** Grenzen für supervisord-Dienste (Zahl, Speicher, Threads). Die Handbuchseite zu supervisord und die Changelogs nennen keine.

## 2. OpenRouter

| Grenze | Wert | Beleg |
| --- | --- | --- |
| Kostenlose Modelle | 20 Anfragen/min; 50 bzw. 1000 Anfragen/Tag | Tabelle in [Limits](https://openrouter.ai/docs/api-reference/limits) |
| Bezahlte Modelle | keine Plattformgrenze | »switch to the paid variant of the model, which has no platform-level request cap.« (ebd.) |
| DDoS-Schutz | ohne Zahl | »Cloudflare's DDoS protection will block requests that dramatically exceed reasonable usage.« (ebd.) |
| Upstream-Anbieter | ohne Zahl | »**The upstream provider**, when the provider serving your request is rate limiting or at capacity.« (ebd.) |
| Gleichzeitig gebundenes Guthaben | Anteil des Guthabens, Obergrenze ohne Zahl | »The total that can be held at once is your in-flight spending budget: a fraction of your current credit balance, up to a fixed ceiling. A request whose estimated cost does not fit alongside your running and recently completed requests is rejected with 402 before it reaches a provider« — gilt nur für Konten unter einer Guthabenschwelle und neue Konten ohne Ausgabenhistorie (ebd.) |
| Transkription, Upstream-Timeout | 60 s | »The upstream provider timeout is 60 seconds, so very large files may time out« ([Speech-to-Text](https://openrouter.ai/docs/guides/overview/multimodal/stt.md)); Fehlercodes 504 und 524 in der [Endpunktbeschreibung](https://openrouter.ai/docs/api/api-reference/stt/create-transcription.md) |
| Transkription, Uploadgröße | 25 MB | »Multipart uploads are limited to 25 MB, the same cap OpenAI enforces.« (Speech-to-Text) |

Für 150 Sitzungen heißt das: Bezahlte Modelle verwenden, Guthaben so bemessen, dass das In-flight-Budget nicht greift. Die 60 s Upstream-Timeout liegen unter `TRANSKRIPTION_BUDGET_SEKUNDEN` (120 s); eine Transkription über OpenRouter scheitert also früher, als das Budget es vorsieht, mit einem Anbieterfehler. Für Redebeiträge unter einer Minute Audio ist das kein Engpass.

**Unbelegt:** eine Nebenläufigkeits- oder Sekundengrenze für bezahlte Konten; Schwelle und Obergrenze des In-flight-Budgets.

## 3. Infomaniak AI Tools

| Grenze | Wert | Beleg |
| --- | --- | --- |
| Chat-Completion, Route v1 (als veraltet markiert) | ohne Zahl | »By default, the number of requests per minute is rate limited. If you wish to know the rate limite or increase this limit, please contact our support team for assistance.« ([v1 chat/completions](https://developer.infomaniak.com/docs/api/post/1/ai/%7Bproduct_id%7D/openai/chat/completions)) |
| Chat-Completion, Route v2 (genutzt) | keine Angabe | [v2 chat/completions](https://developer.infomaniak.com/docs/api/post/2/ai/%7Bproduct_id%7D/openai/v1/chat/completions) |
| Infomaniak-API allgemein | 60 Anfragen/min, nicht erhöhbar | »There is a limit of 60 requests per minute with the Infomaniak API. This limit cannot be increased.« ([FAQ 2581](https://www.infomaniak.com/en/support/faq/2581/discover-the-infomaniak-api)) |
| Transkription | asynchron, Abholen per Polling | »This route is asynchronous, use GET `/1/ai/{product_id}/results/{batch_id}` to get the result« ([audio/transcriptions](https://developer.infomaniak.com/docs/api/post/1/ai/%7Bproduct_id%7D/openai/audio/transcriptions)) |

Die beiden Aussagen widersprechen sich: Die allgemeine FAQ nennt 60/min als nicht erhöhbar, die KI-Route verweist zum Erhöhen an den Support. Ob die 60/min für AI Tools gelten, steht nirgends.

**Was 150 Sitzungen bräuchten.** Bei einem Gesprächsschritt je Person alle 25–70 s sind das 130–360 Chat-Aufrufe pro Minute. Jede Transkription kommt mit einem Absenden und bei `INFOMANIAK_INTERVALL_SEKUNDEN = 2` mit einer Abfrage alle zwei Sekunden dazu. Gälte die allgemeine Grenze, läge sie um mindestens den Faktor 2 unter dem Bedarf, mit Transkription deutlich mehr. Die Worker-Auslegung ändert daran nichts: Jede Auslegung, die 150 Personen bedient, stellt diese Aufrufe; drei synchrone Worker drosselten sie nur, indem sie alle übrigen Personen warten ließen.

**Unbelegt:** die tatsächliche Minutengrenze der KI-Chat-Route; Grenzen für Transkription und Polling (Rate, Nebenläufigkeit, Stapel); die Geltung der 60/min für AI Tools. Geprüft: Endpunktbeschreibungen im Developer-Portal, Preis- und FAQ-Seite der AI Services, FAQ 2845 (Einstieg), FAQ 2828 (Ressourcengrenzen), Nutzungsbedingungen der AI Tools. Vor einem Einsatz mit fünf Seminargruppen über Infomaniak ist die Grenze beim Support zu erfragen.

## 4. gunicorn: was `gthread` an den Parametern ändert

- **`--timeout`** — »Workers silent for more than this many seconds are killed and restarted. […] For the non sync workers it just means that the worker process is still communicating and is not tied to the length of time required to handle a single request.« (gunicorn 26.2.0, `gunicorn/config.py`, Einstellung `timeout`; [Settings](https://gunicorn.org/reference/settings/)). Die Hauptschleife des Thread-Workers meldet sich jede Sekunde beim Master (`gunicorn/workers/gthread.py`, `run()`), auch wenn alle Threads warten.
- **`--worker-connections`** (Default 1000) — der Thread-Worker nimmt Verbindungen an, solange `nr_conns < worker_connections` (`gthread.py`, `run()`), und reiht, was über `--threads` hinausgeht, in seinen `ThreadPoolExecutor` ein. Ein voller Prozess staut dann Anfragen, während ein anderer freie Threads hat. Gemessen mit 3 × 60 Threads, 180 gleichzeitigen Anfragen à 20 s Schlaf, je zweimal: ohne die Option **41 bzw. 40 s** bis zur letzten Antwort (belegte Threads je Prozess 53/60/54 bzw. 60/41/58, der Rest gestaut), mit `--worker-connections 60` **20 bzw. 21 s**, alle drei Prozesse mit 60 belegten Threads. Gleich der Threadzahl gesetzt, bleiben überzählige Verbindungen im Listen-Backlog, wo jeder Prozess mit freiem Thread sie abholt. Keep-alive zum Frontend entfällt damit (`max_keepalived = worker_connections - threads = 0`); hinter dem Frontend-Proxy kostet das einen lokalen Verbindungsaufbau je Anfrage.

## Folgen für das Repo

- `docs/DEPLOYMENT.md`: Dienstdefinition auf `--worker-class gthread --workers 3 --threads 60 --worker-connections 60 --timeout 180`, Fehlertabelle angepasst.
- ADR-0050 hält Lastannahme und Entscheidung fest.
- Eigenes Issue vorschlagen: Infomaniak-Grenze der KI-Routen beim Support erfragen; je nach Antwort das Polling-Intervall oder Rückfragen bei 429 bedenken.
