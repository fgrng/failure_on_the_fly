# Zulässige Anbieter und Modelle: OpenRouter und Infomaniak

Recherche zu [#166](https://github.com/fgrng/failure_on_the_fly/issues/166) (`docs/open-questions.md` Frage 2).
Stand: 2026-09-18. Geprüfte Codebasis: `simulation/sprachmodell/__init__.py`, `simulation/transkription/__init__.py`, `simulation/models.py`, `erhebungen/export.py`, `config/settings.py`, `litellm==1.80.10`.

Vorgabe aus dem Gespräch mit dem Dev: **genau zwei Anbieter** werden unterstützt — **OpenRouter** (Router auf die großen Anbieter) und **Infomaniak** (Schweizer Anbieter, souveräne Open-Source-Modelle). Zweite Vorgabe: **Zugangsdaten wandern aus den Umgebungsvariablen in die Modell-Konfiguration**, in eine benannte Feldgruppe, mit dem Anbieter als Auswahl aus einer festen Liste.

Die Recherche prüft, ob beide Anbieter die Anforderungen aus ADR-0005 (Denkspur immer aus dem Structured Output), ADR-0016 (LiteLLM als einziger echter Adapter) und ADR-0026 (Transkription nur unter Zero-Retention) tragen.

## Gist

Beide Anbieter tragen **beide Nähte** — Sprachmodell und Transkription. OpenRouter hat entgegen der ersten Annahme einen eigenen, OpenAI-kompatiblen Speech-to-Text-Endpunkt (`openai/whisper-large-v3` u. a.); Infomaniak hat Whisper ebenfalls, dort aber **asynchron** mit `batch_id` und Polling.

Auf der Sprachmodell-Naht ist **kein Codeänderungsbedarf**: der bestehende `LiteLLMSprachmodell`-Adapter greift bei beiden, auch für die native Reasoning-Spur. Die Zulässigkeit hängt an Konfiguration — bei OpenRouter am erzwungenen Provider-Filter, bei Infomaniak an `api_base`.

Die **Zugangsdaten wandern in die Konfiguration**, in eine benannte Feldgruppe `anbieter`, `anbieter_basis_url`, `anbieter_token` mit fester Anbieterauswahl — und zwar in **zwei getrennte Objekte**, eines je Naht (Abschnitt 3). Damit lässt sich das Sprachmodell über OpenRouter und die Transkription über Infomaniak fahren; nebenbei lösen sich Infomaniaks zwei verschiedene Endpunktwurzeln und die Frage der Schlüsselrotation.

Beide Anbieter liefern ihre Modellliste per API — OpenRouter **öffentlich und nach Structured Output filterbar**, Infomaniak nur mit Token. Das trägt eine Autovervollständigung im Formular, aber keine harte Prüfung (Abschnitt 4).

Zur eigentlichen Frage 2: **keine erzwungene Modellliste** (bestätigt #165), stattdessen zwei Betriebs-Tore und ein Rauchtest über den Probelauf.

## 1. Sprachmodell-Naht

### 1.1 OpenRouter

- **LiteLLM-Routing:** nativer Provider (`openrouter` ist in `LlmProviders` von `litellm==1.80.10`). Model-String `openrouter/<anbieter>/<modell>`. Keine Codeänderung.
- **Structured Output:** `response_format` mit `{"type": "json_schema", ...}` wird unterstützt, **aber die Unterstützung hängt am Endpunkt, nicht am Modell**. Dasselbe Modell wird von mehreren Providern bedient, und nur manche davon können json_schema. Läuft eine Anfrage auf einen Provider ohne Unterstützung, schlägt sie fehl oder liefert freien Text — bei uns also **Anbieterfehler oder Formatbruch**, und nach `MAX_VERSUCHE = 3` ein sichtbarer Fehler.
- **Konsequenz:** Der Provider-Filter ist **nicht optional**. Die Konfiguration muss das Routing einschränken, z. B.

  ```json
  {
    "extra_body": {
      "provider": {
        "require_parameters": true,
        "data_collection": "deny",
        "zdr": true
      }
    }
  }
  ```

  `require_parameters: true` schließt Endpunkte aus, die `response_format`/json_schema nicht können; `data_collection: "deny"` schließt Provider aus, die Eingaben nicht-transient speichern oder darauf trainieren; `zdr: true` verlangt Zero Data Retention. Die beiden letzteren sind der Hebel, mit dem sich auf dieser Naht überhaupt eine datenschutzrechtlich vertretbare Aussage treffen lässt — Teilnehmer:innen-Eingaben reisen hier mit.
- **Native Reasoning-Spur:** über den `reasoning`-Parameter steuerbar; die Antwort trägt sie in `choices[].message.reasoning` bzw. `reasoning_details`. Hinweis aus einer Sekundärquelle (nicht verifiziert): etliche Modelle lassen die Reasoning-Felder im json_schema-Modus fallen. Für uns unkritisch — ADR-0005 macht die Denkspur zum Schema-Feld; die native Spur ist ausdrücklich optional.
- **Offen (HITL):** OpenRouter ist ein US-Unternehmen. Ob ein AVV vorliegt und wo verarbeitet wird, ist eine vertragliche, keine technische Frage. Für die Erhebung mit pseudonymen Teilnahmen (ADR-0006) ist das zu klären, bevor OpenRouter dort aktiviert wird.

### 1.2 Infomaniak

- **Endpunkt:** `POST https://api.infomaniak.com/2/ai/{product_id}/openai/v1/chat/completions`, OpenAI-kompatibel. Die `product_id` stammt aus `GET /1/ai`, die Modellliste aus `GET /2/ai/{product_id}/openai/v1/models` bzw. `GET /1/ai/models` (letzteres markiert Beta-Modelle).
- **LiteLLM-Routing:** **kein** eigener LiteLLM-Provider. Der Weg führt über den OpenAI-kompatiblen Pfad: Model-String `openai/<modell>` (z. B. `openai/qwen3`) mit `api_base: https://api.infomaniak.com/2/ai/<product_id>/openai/v1`. Keine Codeänderung an der Naht.
- **Structured Output:** unterstützt und die **einzige** noch unterstützte Form. Die API-Doku zu `response_format.type` sagt: nur `json_schema` wird derzeit unterstützt, `text` ist das Standardverhalten, `json_object` ist obsolet. `strict: true` wird geführt und verweist auf den OpenAI-Structured-Outputs-Leitfaden. Unser `AUSGABE_SCHEMA` (`denkspur` vor `aeusserung`, `additionalProperties: false`, beide `required`) erfüllt die strict-Teilmenge.
- **Native Reasoning-Spur:** über `reasoning_effort` steuerbar, laut Doku aber nur als An/Aus (`"none"` schaltet das Denken ab, jeder andere Wert an). Bei den meisten Modellen ist es per Vorgabe an. **Nicht** unterstützt u. a. von `apertus-ai/Apertus-v1.5-70B` und `mistral3`. Das Antwortschema führt `usage.completion_tokens_details.reasoning_tokens`; ob zusätzlich ein Textfeld mit der Spur zurückkommt, geht aus der Doku nicht hervor und ist empirisch zu prüfen.
- **Modelle:** Die API-Doku nennt als Beispiele `qwen3`, `swiss-ai/Apertus-70B-Instruct-2509`, `Qwen/Qwen3-VL-235B-A22B-Instruct`. Eine Drittquelle listet zehn Modelle, darunter `Qwen/Qwen3.5-122B-A10B-FP8`, `Qwen/Qwen3.5-397B-A17B-FP8`, `swiss-ai/Apertus-v1.5-70B`, `moonshotai/Kimi-K2.6`, `mistral-ai/Mistral-Small-4-119B-2603`, `google/gemma-4-31B-it`, `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8` sowie zwei Embedding-Modelle. **Verbindlich ist allein `GET /1/ai/models`** mit gültigem Token — das steht aus, weil kein Infomaniak-Konto vorliegt.
- **Datenschutz:** Infomaniak wirbt für die AI Services mit Betrieb in eigenen Schweizer Rechenzentren, „Es werden keine Anfragen gespeichert", „Ihre Prompts werden weder gespeichert noch dazu verwendet, die Modelle zu trainieren oder unsere Dienstleistungen zu verbessern" und voller DSG-/DSGVO-Konformität. Inhaltlich ist das genau die Zusage, die ADR-0026 verlangt. Ob sie **vertraglich** in einem AVV steht, ist HITL zu klären.

### 1.3 Was der bestehende Code schon trägt

`LiteLLMSprachmodell.antworten` liest die native Spur aus `message.reasoning_content`, ersatzweise `message.thinking`. LiteLLM normalisiert im Nicht-Streaming-Pfad sowohl `reasoning_content` als auch `reasoning` auf `Message.reasoning_content` (`litellm_core_utils/prompt_templates/common_utils.py:1051-1054`). Damit greift der Adapter bei **beiden** Anbietern ohne Anpassung — OpenRouters `reasoning`-Feld eingeschlossen.

## 2. Transkriptions-Naht (ADR-0026)

Beide Anbieter bieten Whisper an, aber in **unterschiedlicher Bauform**.

### 2.1 OpenRouter — synchron, OpenAI-kompatibel

- **Endpunkt:** `POST https://openrouter.ai/api/v1/audio/transcriptions` (Existenz verifiziert: ein POST ohne Schlüssel antwortet mit `401`, nicht `404`). Zwei Eingabeformen: JSON mit base64 in `input_audio` oder **`multipart/form-data` im OpenAI-Stil** (`file`, `model`).
- **Modelle:** `openai/whisper-large-v3` (Modalität `audio->transcription`, bedient von DeepInfra, Together und Groq), daneben `openai/whisper-1`, `openai/whisper-large-v3-turbo` u. a. Auffindbar über `GET /api/v1/models?output_modalities=transcription` — in der ungefilterten Modellliste tauchen sie **nicht** auf.
- **Passt zu uns:** `webm` ist ein unterstütztes Format (unser Aufnahmeformat), `language` und `response_format` gibt es, die multipart-Form ist OpenAI-kompatibel. Damit bedient der **bestehende** `OpenAITranskription`-Adapter OpenRouter, indem ihm ein `OpenAI(base_url="https://openrouter.ai/api/v1", api_key=...)`-Client injiziert wird — der Konstruktor nimmt bereits einen Client entgegen. `litellm.transcription()` hilft hier nicht: es kennt nur `azure` und `openai`.
- **Grenzen:** multipart max. 25 MB, Verarbeitungs-Timeout 60 Sekunden pro Anfrage. Beides ist beim Aufnahme-Limit zu berücksichtigen.
- **Offen (wichtig für ADR-0026):** Die STT-Doku hält fest, dass die Routing-Präferenzen `order`, `only` und `ignore` auf Transkriptionsanfragen **nicht** angewendet werden. Ob die Datenschutz-Filter `zdr` und `data_collection` dort greifen, sagt sie nicht. Solange das ungeklärt ist, lässt sich für die Transkription über OpenRouter **keine** Zero-Retention-Zusage erzwingen — und damit greift das Tor aus ADR-0026 nicht. Das ist bei OpenRouter zu erfragen.

### 2.2 Infomaniak — asynchron

- **Endpunkt:** `POST https://api.infomaniak.com/1/ai/{product_id}/openai/audio/transcriptions`, Modell `whisper`.
- **Passt:** erlaubte Dateitypen umfassen `webm`, `language` kennt `de`, `response_format` kennt `text`, `prompt` zum Stilanstoß ist vorhanden.
- **Passt nicht ohne Umbau:** Die Route ist **asynchron**. Sie antwortet mit `{"batch_id": "..."}`; das Ergebnis wird über `GET /1/ai/{product_id}/results/{batch_id}` geholt bzw. über `.../download` heruntergeladen. Der heutige synchrone SDK-Aufruf kann das nicht bedienen. Ein zweiter Adapter hinter dem bestehenden `Transkription`-Protokoll (Abschicken + Polling mit Timeout) hält die Naht intakt: die Signatur `transkribieren(audio) -> str` bleibt synchron, das Polling liegt im Adapter.
- Der Größenbegrenzung des `file`-Parameters ist beim Aufnahme-Limit Rechnung zu tragen.

In beiden Fällen bleibt `TRANSKRIPTION_ZERO_RETENTION` die Stelle, an der die vertragliche Zusage technisch wirksam wird.

## 3. Anbieter in der Konfiguration

**Entschieden:** Die Anbieterangaben liegen in der Konfiguration, in einer eigenen, am Namen erkennbaren Feldgruppe. Der Anbieter wird aus einer **festen Liste** gewählt; welche der übrigen Felder gefüllt sein müssen, hängt an dieser Wahl. Sprachmodell und Transkription werden dabei **getrennt** konfiguriert und dürfen an verschiedenen Anbietern hängen.

### 3.1 Zwei getrennte Konfigurationen

Die beiden Nähte werden **unabhängig** konfiguriert. Das Sprachmodell darf bei OpenRouter liegen und die Transkription bei Infomaniak — oder umgekehrt. Dieselbe Feldgruppe, zwei Objekte:

**`simulation.ModellKonfiguration`** (bestehend, erweitert):

| Feld | Typ | Zweck |
|---|---|---|
| `sprachmodell` | `CharField(255)` | Model-String (unverändert) |
| `parameter` | `JSONField` | Aufrufparameter (unverändert) |
| `anbieter` | `CharField(choices)` | `fake`, `openrouter`, `infomaniak` |
| `anbieter_basis_url` | `URLField(blank=True)` | Chat-Endpunktwurzel |
| `anbieter_token` | `CharField(blank=True)` | Zugangsschlüssel |

**`simulation.TranskriptionsKonfiguration`** (neu):

| Feld | Typ | Zweck |
|---|---|---|
| `transkriptionsmodell` | `CharField` | `openai/whisper-large-v3` bzw. `whisper` |
| `anbieter` | `CharField(choices)` | `fake`, `openrouter`, `infomaniak` |
| `anbieter_basis_url` | `URLField(blank=True)` | Transkriptions-Endpunktwurzel |
| `anbieter_token` | `CharField(blank=True)` | Zugangsschlüssel |

`fake` gehört in beide Listen, weil es die deterministischen Adapter gibt — beim Sprachmodell wandert damit die heutige Erkennung über den magischen Namen `sprachmodell == "fake"` (`simulation/__init__.py:101`, `seeds/.../entwicklungsdaten_anlegen.py:234-240`) auf ein echtes Auswahlfeld.

**Geheimnisse gehören nicht nach `parameter`** — dafür gibt es `anbieter_token`.

### 3.2 Was die Trennung löst

Drei Dinge fallen damit weg, die sich an einem gemeinsamen Objekt gerieben hätten:

1. **Die zwei Basis-URLs bei Infomaniak.** Der Chat liegt unter `/2/ai/{product_id}/openai/v1`, die Transkription unter `/1/ai/{product_id}/openai` — andere API-Version, kein `v1`-Suffix. Mit getrennten Objekten trägt jede Naht schlicht ihre eigene URL; es braucht weder ein Zusatzfeld noch eine Ableitungsregel.
2. **Die unterschiedlichen Lebensdauern.** `ModellKonfiguration` ist append-only und wird von Sitzung und Erhebung gepinnt (ADR-0013), weil das Sprachmodell die Antworten *erzeugt* und damit zur Nachvollziehbarkeit der Daten gehört. Für die Transkription gilt das ausdrücklich **nicht**: ADR-0026 hält fest, dass die Wahl des Auftragsverarbeiters „Teil der datenschutzrechtlichen Dokumentation, nicht der Datenspur" ist. `TranskriptionsKonfiguration` darf deshalb **veränderlich** sein — womit die Rotationsklemme aus 3.5 für diese Naht gar nicht erst entsteht.
3. **Die Kopplung im Betrieb.** Ein Anbieterwechsel bei der Transkription zwingt keine neue Modell-Konfiguration und damit keine Erhebung in die Knie.

Konkret heißt das auch: Die naheliegende Betriebsvariante — Sprachmodell über OpenRouter wegen der Modellauswahl, Audio über Infomaniak wegen der Schweizer Verarbeitung — ist ohne Verrenkung konfigurierbar. Sie ist sogar die datenschutzrechtlich attraktivste, weil die Stimme das biometrische Datum ist (ADR-0007) und bei OpenRouter derzeit offen ist, ob sich für Audio überhaupt Zero Retention erzwingen lässt (2.1).

### 3.3 Welche Felder je Anbieter gebraucht werden

Prüfung in `clean()`, für beide Objekte nach demselben Muster:

| Anbieter | Modellname | `anbieter_basis_url` | `anbieter_token` |
|---|---|---|---|
| `fake` | `fake` | leer | leer |
| `openrouter` | Sprachmodell: Präfix `openrouter/`; Transkription: z. B. `openai/whisper-large-v3` | optional (Vorgabe `https://openrouter.ai/api/v1`) | **Pflicht** |
| `infomaniak` | Sprachmodell: Präfix `openai/`; Transkription: `whisper` | **Pflicht** | **Pflicht** |

Bei Infomaniak lautet die Wurzel für das Sprachmodell `https://api.infomaniak.com/2/ai/<product_id>/openai/v1`, für die Transkription `https://api.infomaniak.com/1/ai/<product_id>/openai`.

Damit ist die Präfixprüfung aus Abschnitt 5 nebenbei erledigt: Nicht der Modellname wird gegen eine Liste geprüft, aber seine Anbieterbindung.

### 3.4 Wie die Felder am Aufruf ankommen

`_sprachmodell_aus()` (`simulation/__init__.py:100-107`) reicht `parameter` heute roh an LiteLLM durch. Künftig ergänzt es die Anbieterfelder:

```python
LiteLLMSprachmodell(
    konfiguration.sprachmodell,
    {
        **konfiguration.parameter,
        "api_key": konfiguration.anbieter_token,
        **({"api_base": konfiguration.anbieter_basis_url}
           if konfiguration.anbieter_basis_url else {}),
    },
)
```

Auf der Transkriptionsseite entsteht die Entsprechung: eine Funktion, die aus der `TranskriptionsKonfiguration` den passenden Adapter bildet — für `openrouter` den bestehenden `OpenAITranskription` mit injiziertem Client (2.1), für `infomaniak` den neuen asynchronen Adapter (2.2). Damit entfällt die heutige Bindung an `OPENAI_API_KEY` in der Umgebung.

### 3.5 Was aus den Transkriptions-Settings wird

`TRANSKRIPTION_ANBIETER` und `TRANSKRIPTION_MODELL` (`config/settings.py:181-182`) werden von der neuen Konfiguration abgelöst.

`TRANSKRIPTION_ZERO_RETENTION` bleibt **Instanz-Einstellung** und wandert *nicht* mit. Es bezeugt eine vertragliche Zusage der Betreiber:in, keine Aufrufangabe — ein Tor, das eine Administrator:in im selben Formular anklicken kann, in dem sie den Anbieter wählt, ist keins mehr. Es gehört in die Deployment-Hoheit, so wie ADR-0026 es meint.

### 3.6 Sichtbarkeit und Geheimhaltung

Das Token darf an keiner dieser Stellen austreten:

1. **Export** — `erhebungen/export.py:331-336` schreibt heute `id`, `sprachmodell`, `parameter` nach `modellkonfigurationen.csv`. Aufzunehmen ist **`anbieter`**, nicht Token und nicht Basis-URL (letztere trägt bei Infomaniak die `product_id`). ADR-0029 ist entsprechend zu ergänzen. Die `TranskriptionsKonfiguration` gehört **gar nicht** in den Export — siehe ADR-0026 und 3.2.
2. **Kern-Seite** — `simulation/templates/simulation/kern.html:68-69` zeigt Sprachmodell und Parameter. Anbieter ja, Basis-URL ja, Token nur maskiert.
3. **Erhebungsdetail** — `erhebungen/templates/erhebungen/detail.html:174-175` zeigt dieselben zwei Felder, gleiche Regel.

In beiden Formularen ist `anbieter_token` write-only: leer anzeigen, gesetzten Wert nie zurückrendern.

### 3.7 Konsequenz: Schlüsselrotation beim Sprachmodell legt eine neue Fassung an

`ModellKonfiguration` ist append-only (`simulation/models.py:383-388`). Liegt das Token am Datensatz, ist eine Rotation kein Feldupdate, sondern eine **neue Fassung plus Aktivierung**. Für neue Sitzungen greift sie sofort. Laufende Erhebungen pinnen weiterhin die alte Fassung (ADR-0013) und liefen damit gegen ein ungültiges Token — sie müssen bei einer Rotation ausdrücklich nachgezogen werden.

Das ist die bewusst in Kauf genommene Konsequenz der Ablage am Artefakt. Sie gehört in die Betriebsdoku. Für die **Transkription** gilt sie nicht: Deren Konfiguration ist veränderlich (3.2), das Token dort also im Feld rotierbar.

## 4. Modellnamen aus den Anbieter-APIs

Beide Anbieter liefern ihre Modellliste über die API — mit einem entscheidenden Unterschied im Zugang.

### 4.1 OpenRouter: öffentlich und filterbar

`GET https://openrouter.ai/api/v1/models` antwortet **ohne Authentifizierung** (verifiziert, 445 Modelle). Jeder Eintrag trägt u. a. `id`, `name`, `context_length`, `architecture`, `supported_parameters`, `pricing`. Zwei Filter sind für uns unmittelbar brauchbar, beide verifiziert:

| Abfrage | Treffer | Nutzen |
|---|---|---|
| `?supported_parameters=structured_outputs` | 340 | Kandidaten für die Sprachmodell-Naht (ADR-0005) |
| `?supported_parameters=structured_outputs,reasoning` | 239 | beides zugleich — beantwortet open-questions Frage 6 für OpenRouter |
| `?output_modalities=transcription` | 21 | Kandidaten für die Transkriptions-Naht |

Der kombinierte Filter wirkt als UND (alle 239 Treffer führen beide Parameter). Die Transkriptionsmodelle tauchen in der ungefilterten Liste **nicht** auf; sie sind nur über den Modalitätsfilter erreichbar.

**Wichtiger Vorbehalt gegen eine harte Prüfung:** `supported_parameters` auf Modellebene ist die Vereinigung über alle Provider-Endpunkte. Verifiziertes Gegenbeispiel: `deepseek/deepseek-v4.1-flash` steht in der `structured_outputs`-Liste, aber drei seiner acht Endpunkte (Relace, DeepSeek, StreamLake) können es nicht. Eine Prüfung gegen diese Liste sagt also nur „mindestens ein Endpunkt kann es" — das Routing kann trotzdem auf einem anderen landen. **`require_parameters: true` bleibt deshalb zwingend**, auch bei geprüftem Modellnamen.

### 4.2 Infomaniak: nur mit Token

`GET https://api.infomaniak.com/1/ai/models` verlangt Authentifizierung (verifiziert: `401 not_authorized` ohne Schlüssel); dasselbe gilt für `GET /2/ai/{product_id}/openai/v1/models`. Eine Liste ohne Zugangsdaten gibt es nicht. Da das Token künftig an der Modell-Konfiguration liegt (Abschnitt 3), ist das lösbar — aber mit einer Henne-Ei-Ordnung: erst Anbieter, Basis-URL und Token eintragen, dann die Modellliste abrufen.

### 4.3 Empfehlung: Autovervollständigung ja, harte Prüfung nein

- **Autovervollständigung**: sinnvoll und billig. Bei OpenRouter direkt beim Tippen gegen die öffentliche, gefilterte Liste; bei Infomaniak erst nach dem Speichern von Token und Basis-URL, also im Bearbeiten-Schritt. Beides mit kurzem Cache, damit das Formular nicht bei jedem Tastendruck über das Netz geht.
- **Harte Prüfung**: nicht empfohlen. Sie macht das Anlegen einer Konfiguration von der Erreichbarkeit einer fremden API abhängig — und schlägt genau dann fehl, wenn man sie am dringendsten braucht: bei einer Störung. Dazu der Vorbehalt aus 4.1, der ihr bei OpenRouter ohnehin die Schärfe nimmt. Wird ein Modellname falsch geschrieben, meldet der Probelauf das beim ersten Aufruf.
- **Kompromiss, falls doch gewünscht**: eine **Warnung** im Formular („dieses Modell steht bei OpenRouter nicht in der Liste der Modelle mit Structured Output"), die das Speichern nicht blockiert. Das gibt den Hinweis, ohne den Betrieb an eine fremde API zu koppeln.

## 5. Wird die Modellliste erzwungen?

**Empfehlung: nein — Betriebsdokumentation statt Validierung.** Begründung:

- Die Entscheidung aus #165 (`sprachmodell` bleibt freier `CharField`) bleibt tragfähig. Eine Modellliste veraltet schneller als eine Migration; Infomaniak markiert Modelle ausdrücklich als Beta und behält sich Änderungen vor.
- Die eigentliche Zulässigkeitsprüfung ist bei OpenRouter ohnehin **nicht** am Modellnamen zu treffen, sondern am Endpunkt — genau das leistet `require_parameters`. Eine Namens-Whitelist würde Sicherheit vortäuschen, die sie nicht hat.
- Das System hat bereits ein hartes Tor: Ein Modell ohne Structured Output erzeugt Formatbruch, nach `MAX_VERSUCHE = 3` einen sichtbaren Fehler. Eine untaugliche Konfiguration fällt beim **Probelauf** auf, bevor sie eine Erhebung erreicht — genau die Rolle, die ADR-0014 dem Probelauf gibt.
- Eine Prüfung gegen die Anbieterliste wäre zudem nur scheinbar scharf (4.1) und würde das Anlegen einer Konfiguration von der Erreichbarkeit einer fremden API abhängig machen.

Konkret vorgeschlagen:

1. Eine Betriebsdoku mit den zwei Anbietern, ihren Model-Strings, den Pflicht-`parameter`-Blöcken, der Anbieter-Einrichtung und der Rotationsregel aus 3.5.
2. Ein **Rauchtest über den Probelauf** als Pflichtschritt beim Aktivieren einer neuen Modell-Konfiguration, in der Betriebsdoku festgeschrieben.
3. Kein `clean()`-Vergleich gegen eine **Modell**-Liste.

Das Anbieterfeld aus Abschnitt 3 ist dagegen sehr wohl eine feste Liste — geprüft wird also die Anbieterbindung samt Präfix des Model-Strings, nicht der Modellname. Das ist die kleinste sinnvolle Härtung und bereits Teil des Entwurfs.

## 6. Offene Punkte

### 6.1 Entschieden (2026-09-18)

- **`openai/gpt-4o` wird abgelöst.** Seeds (`seeds/.../entwicklungsdaten_anlegen.py:51`, `seeds/.../workshopdaten_anlegen.py:28`), README (`:266`) und die Bestandsdatensätze stellen auf **OpenRouter** um. Die Anbieterliste bleibt damit bei `fake`, `openrouter`, `infomaniak`; OpenAI-direkt wird nicht aufgenommen.
- **`openrouter` darf als Transkriptionsanbieter gewählt werden.** `clean()` verbietet die Kombination nicht. Für die Zero-Retention-Zusage ist die **Administrator:in verantwortlich, die die Konfiguration anlegt** — dieselbe Verantwortung, die `TRANSKRIPTION_ZERO_RETENTION` schon heute bezeugt (3.5). Die offene Frage aus 6.2 bleibt damit eine Betriebsfrage, keine Sperre im Code.
- **Die Repo-Abhängigkeiten werden umprogrammiert.** Sie sind in [#169](https://github.com/fgrng/failure_on_the_fly/issues/169) skizziert und werden dort genauer geplant; der Editor entsteht ebenfalls dort.

### 6.2 Vertragliche Klärungen (HITL)

Keine Sperre im Code — sie liegen in der Verantwortung der Betreiber:in (6.1).

- **Greifen `zdr`/`data_collection` auf OpenRouters Transkriptionsroute?** Ohne Antwort ist die Transkription über OpenRouter nach ADR-0026 nicht freizugeben. Bei OpenRouter zu erfragen.
- **AVV und Verarbeitungsort bei OpenRouter.** Ohne Klärung bleibt OpenRouter auf Training und Probelauf beschränkt.
- **AVV bei Infomaniak.** Die öffentliche Zusage deckt ADR-0026 inhaltlich; das Papier fehlt.
- **Verbindliche Modellliste von Infomaniak** über `GET /1/ai/models` mit Token — samt der Frage, welche Modelle Structured Output *und* Reasoning zugleich liefern. Für OpenRouter ist das mit 4.1 beantwortet (239 Modelle können beides).
- **Empirische Prüfung**, ob Infomaniak eine native Reasoning-Spur als Text zurückgibt oder nur `reasoning_tokens` zählt.
- **Verschlüsselung von `anbieter_token` at rest** — eigene Entscheidung, nicht Teil dieser Frage.

### 6.3 Ungeprüft geblieben

- **Native Reasoning-Spur bei Infomaniak** — ob ein Textfeld zurückkommt oder nur `reasoning_tokens` gezählt werden, ließ sich ohne Konto nicht feststellen.
- **Infomaniaks Transkriptions-Polling** — Antwortform und Zeitverhalten von `GET /1/ai/{product_id}/results/{batch_id}` sind nur aus der Doku bekannt, nicht erprobt. Der Timeout des Adapters lässt sich erst danach sinnvoll wählen.
- **Dateigrößengrenze** des Infomaniak-`file`-Parameters (»Max length« in Kilobyte) — anbieter- bzw. produktabhängig, nicht dokumentiert.

### 6.4 Abhängigkeiten im Repo

Drei Stellen müssen existieren oder umgebaut werden, bevor der Entwurf aus Abschnitt 3 greifen kann:

- **Es gibt kein Anlegeformular.** `simulation/forms.py` fehlt, `admin.py` gibt es im ganzen Projekt nicht; Modell-Konfigurationen entstehen heute nur aus der Shell oder den Seeds. Der Editor entsteht in [#169](https://github.com/fgrng/failure_on_the_fly/issues/169); die Feldgruppe aus Abschnitt 3 ist dort einzuplanen. #169 hält bisher fest, `sprachmodell` bleibe frei und `parameter` werde nur auf gültiges JSON geprüft — das gilt weiterhin für den **Modellnamen**, wird aber um die Anbieter-Feldgruppe und deren `clean()`-Regeln ergänzt.
- **Der Transkriptionsadapter ist fest verdrahtet.** `sitzungen/urls.py:34` instanziiert `OpenAITranskription()` zur Importzeit in der URL-Konfiguration. Es gibt heute keine Stelle, die eine Konfiguration lesen könnte; dieser Aufbau muss auf eine Adapterbildung zur Anfragezeit umgestellt werden. Nebenbei: `FakeTranskription` hat produktiv gar keinen Pfad — der `fake`-Anbieter der Transkription wird also neu gebaut, nicht nur verdrahtet.
- **Die Migration für Bestandsdatensätze** ist unter append-only zu schreiben (`ModellKonfigurationQuerySet.update()` wirft, `save()` ebenso) und fällt danach unter ADR-0031. Altdatensätze mit `openai/gpt-4o` werden auf OpenRouter umgestellt (6.1).

## 7. Angedacht: native Reasoning-Spur fallen lassen, Schema vereinheitlichen

**Stand: Überlegung, nicht entschieden.** Der Gedanke: Die native Reasoning-Spur wird nicht weiter aufgenommen. Stattdessen wird für **alle** Modelle — gewöhnliche wie Reasoning-Modelle — dasselbe Structured Output verlangt, mit der Denkspur als aktiv eingefordertem Feld.

Das passt zur Stoßrichtung von ADR-0005, der die native Spur ohnehin nur als optionale Beigabe führt und sie ausdrücklich „neben der Denkspur, nie als sie" verortet. Drei der dort genannten Gründe sprechen sogar direkt fürs Streichen: Sie ist bei mehreren Anbietern nur zusammengefasst abrufbar, sie ist nicht steuerbar, und ihre Herkunft hängt an der Modell-Konfiguration. Die Recherche stützt das zusätzlich: Bei OpenRouter lassen etliche Modelle die Reasoning-Felder im json_schema-Modus fallen (1.1), bei Infomaniak ist unklar, ob überhaupt ein Textfeld zurückkommt (1.2). Ein Feld, das bei einem Anbieterwechsel stillschweigend leer bleibt, trägt wenig.

### 7.1 Was daran hängt

Die native Spur ist durchgereicht bis in die Datenspur. Ein Streichen berührt:

| Stelle | Art |
|---|---|
| `sitzungen/models.py:109` | Feld `native_reasoning_spur` am Gesprächsschritt (Migration nötig) |
| `sitzungen/orchestrierung.py:53`, `sitzungen/sink.py:39` | Durchreichung |
| `sitzungen/templates/.../sitzung_gespraech.html:36-37` | Anzeige im Probelauf |
| `erhebungen/export.py:183,194` | Spalte im Export — **ADR-0029 ist ein Kontrakt** und wäre zu ändern |
| `simulation/__init__.py:40` | Feld am `Antwortversuch` |
| `simulation/sprachmodell/__init__.py:202-207` | Auslesen aus der Modellantwort; das Protokoll gäbe dann keine `tuple[Antwort, str \| None]` mehr zurück, sondern nur die Antwort |
| ADR-0005, ADR-0016, #27 | Begründungen und Spec wären nachzuführen |

Die Naht würde dadurch **schmaler**: Das Protokoll verlöre seinen zweiten Rückgabewert, und die Sonderbehandlung „reist am Schema vorbei" entfiele ersatzlos.

### 7.2 Offene Frage: die drei Felder

Vorgeschlagen ist ein dreiteiliges Schema:

1. simulierte Denkspur des Schülers
2. simulierte Äußerung
3. daraus resultierende Äußerung des Schülers

Zwischen (2) und (3) ist die Unterscheidung noch nicht scharf — beide heißen »Äußerung«. Das ist zu klären, **bevor** ein ADR entsteht, weil ADR-0005 die **Reihenfolge im Schema für normativ** erklärt: Sie ist es, die das Reasoning vor der Äußerung entstehen lässt. Ein drittes Feld wirkt nur dann, wenn klar ist, was es gegenüber dem zweiten hinzufügt.

Mögliche Lesarten, die zu prüfen wären:

- **Absicht vor Wortlaut:** (2) ist, was die simulierte Schüler:in sagen *will*, (3) der tatsächlich ausgesprochene Text — der Zwischenschritt zwänge das Modell, Inhalt und Formulierung zu trennen.
- **Fachliches vor Sprachlichem:** (2) trägt das fachliche Ergebnis aus dem Fehlermuster, (3) kleidet es in die Sprache der Klassenstufe.
- **Ein Feld zu viel:** (2) ist eine Umschreibung von (3) und fällt weg — dann bleibt es beim heutigen Zweierschema, nur ohne native Spur.

Erst danach lässt sich sagen, welches Feld in die Datenspur gehört, welches die Autor:in im Probelauf sieht und welches die Teilnehmer:in nie sehen darf (die Sichtbarkeitsstaffel aus ADR-0005 kennt heute nur *eine* verborgene Schicht).

## Folgen für das Repo

Bei positiver Entscheidung:

- ADR zu den zwei zulässigen Anbietern und der Nicht-Erzwingung der Modellliste.
- ADR zur Anbieter-Feldgruppe, zur Trennung der beiden Konfigurationen und zu ihren unterschiedlichen Lebensdauern (append-only vs. veränderlich).
- `docs/open-questions.md` Frage 2 streichen.
- Ticket: Anbieter-Feldgruppe an `ModellKonfiguration` samt Migration, `clean()`-Prüfung je Anbieter, write-only-Token, Maskierung an beiden Anzeigestellen, `anbieter` im Export (ADR-0029 ergänzen).
- Ticket: `TranskriptionsKonfiguration` als eigenes, veränderliches Objekt; löst `TRANSKRIPTION_ANBIETER`/`TRANSKRIPTION_MODELL` ab, nicht im Export.
- Ticket: Autovervollständigung der Modellnamen im Anlegeformular aus den Anbieter-APIs (Abschnitt 4).
- Ticket: zweiter Transkriptionsadapter für Infomaniak (asynchron mit Polling); OpenRouter-Transkription über den bestehenden Adapter mit injiziertem Client.
- README: Anbieter-Abschnitt; `OPENAI_API_KEY` und `openai/gpt-4o` entfallen (`README.md:144-160`, `:266`).
- Seeds auf OpenRouter umstellen (`entwicklungsdaten_anlegen.py:51`, `workshopdaten_anlegen.py:28`).
- Bei positiver Entscheidung zu Abschnitt 7: ADR-0005 und ADR-0029 nachführen, Feld und Exportspalte entfernen.

## Quellen

- Infomaniak, [Create chat completion (`POST /2/ai/{product_id}/openai/v1/chat/completions`)](https://developer.infomaniak.com/docs/api/post/2/ai/%7Bproduct_id%7D/openai/v1/chat/completions) — `response_format`, `reasoning_effort`, `model`, Antwortschema.
- Infomaniak, [Create transcription (`POST /1/ai/{product_id}/openai/audio/transcriptions`)](https://developer.infomaniak.com/docs/api/post/1/ai/%7Bproduct_id%7D/openai/audio/transcriptions) — asynchrones Verhalten, `batch_id`, Formate, Sprachen.
- Infomaniak, [List models (`GET /1/ai/models`)](https://developer.infomaniak.com/docs/api/get/1/ai/models).
- Infomaniak, [AI Tools – Produktseite](https://www.infomaniak.com/de/hosting/ai-tools) — Schweizer Rechenzentren, keine Speicherung von Anfragen, kein Training auf Prompts, DSG/DSGVO.
- OpenRouter, [Structured Outputs](https://openrouter.ai/docs/guides/features/structured-outputs) — Unterstützung je Endpunkt, `require_parameters`.
- OpenRouter, [Speech-to-Text](https://openrouter.ai/docs/guides/overview/multimodal/stt) — `/api/v1/audio/transcriptions`, Formate, 25-MB-/60-s-Grenzen, Hinweis zu nicht angewandten Routing-Präferenzen.
- OpenRouter, [Whisper Large V3](https://openrouter.ai/openai/whisper-large-v3) und `GET /api/v1/models/openai/whisper-large-v3/endpoints` — Modalität `audio->transcription`, Provider DeepInfra/Together/Groq.
- OpenRouter, `GET /api/v1/models` mit `supported_parameters=structured_outputs[,reasoning]` und `output_modalities=transcription` — ohne Authentifizierung abgefragt und verifiziert; Endpunkt-Varianz an `deepseek/deepseek-v4.1-flash` geprüft.
- OpenRouter, [Zero Data Retention](https://openrouter.ai/docs/guides/features/zdr) und [Reasoning Tokens](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens) — `zdr`, `data_collection`, `reasoning_details`.
- [Mastra: Infomaniak-Modellliste](https://mastra.ai/models/providers/infomaniak) — Drittquelle für Modell-IDs und Base-URL.
- LiteLLM 1.80.10, lokal geprüft: `LlmProviders`, `litellm.main.transcription` (nur `azure`/`openai`), `litellm_core_utils/prompt_templates/common_utils.py:1040-1057`.
