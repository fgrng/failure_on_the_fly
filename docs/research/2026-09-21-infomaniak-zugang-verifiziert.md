# Infomaniak-Zugang am echten Konto verifiziert

Erfüllt [#193](https://github.com/fgrng/failure_on_the_fly/issues/193). Die Recherche zu [#166](https://github.com/fgrng/failure_on_the_fly/issues/166) konnte Infomaniak ausschließlich **ohne Token** prüfen; alles, was dort über diesen Anbieter steht, stammte aus der Anbieterdokumentation. Dieser Text hält fest, was am **2026-09-21** an einem echten Konto **beobachtet** wurde.

Stand: 2026-09-21. Geprüfte Codebasis: `simulation/transkription/__init__.py`, `simulation/sprachmodell/__init__.py`, `simulation/models.py`. Zugangsdaten stehen nicht in diesem Text; die Produktkennung ist als `<product_id>` maskiert.

## Gist

Beide Nähte tragen. Die Chat-Route liefert Structured Output mit unserem echten `AUSGABE_SCHEMA` — **ADR-0005 trägt bei diesem Anbieter nachweislich**. Die Transkriptions-Route durchläuft ihren asynchronen Ablauf wie erwartet, mit den Statusnamen `pending` und `success`.

Der wichtigste Befund ist ein **Fehler**: Der produktive Transkriptions-Adapter scheitert an jeder echten Antwort. Er ist als [#232](https://github.com/fgrng/failure_on_the_fly/issues/232) festgehalten. Genau das ist der Schaden, den #193 verhindern sollte — der Testbestand bildete die aus der Dokumentation *abgeleitete* Antwortform nach und bestätigte damit die falsche Annahme.

Ein Kriterium aus #193 ist **gegenstandslos**: die Frage nach einer nativen Reasoning-Spur als Text. Mit [#174](https://github.com/fgrng/failure_on_the_fly/issues/174) ist die native Spur gestrichen.

## 1. Produkt und Zugang

`GET /1/ai` beantwortet mit gültigem Token die Produktkennung:

```json
{"result":"success","data":[{"product_name":"Ai-Tools","product_id":<product_id>,"account_name":"…","status":"ok"}]}
```

Drei Dinge folgen daraus:

- **`data` ist ein Array.** Mehrere AI-Produkte an einem Konto sind vorgesehen; das geprüfte Konto führt eines. Wer aus dieser Antwort die Endpunktwurzel ableitet, muss den Mehrfachfall behandeln.
- **Die Antwort trägt `account_name`**, also einen Klarnamen. Er darf keine Oberfläche erreichen.
- Aus der Kennung bilden sich die beiden Wurzeln: Sprachmodell `…/2/ai/<product_id>/openai/v1`, Transkription `…/1/ai/<product_id>/openai`.

Fehlerbild: Ohne oder mit falschem Token antwortet die v1-API mit `401` und der Nutzlast `{"result":"error","error":{"code":"not_authorized",…}}`; die OpenAI-kompatible v2-Route antwortet ebenfalls mit `401`, aber im OpenAI-Stil (`{"error":{"message":"Invalid Authentication",…}}`).

## 2. Modellliste

`GET /1/ai/models` ist die maßgebliche Liste. Sie braucht **keine** `product_id` — der Abruf hängt allein am Token. 16 Einträge, Antwortzeit rund 120 ms.

Jeder Eintrag trägt `id`, `name`, `type`, `documentation_link`, `description`, `info_status`, `logo_url`, `last_updated_at`, `max_token_input`, `version` und `meta` (mit `is_beta`, `is_coder`). **Der Modellstring steht in `name`; `id` ist eine bedeutungslose Ganzzahl.**

Verteilung nach `type`: 8 `llm`, 1 `stt`, 3 `embedding`, 2 `reranker`, 2 `image`.

Die acht Sprachmodelle:

| `name` | `max_token_input` | Beta | `info_status` |
|---|---|---|---|
| `Qwen/Qwen3.5-122B-A10B-FP8` | 200000 | nein | `coming_soon` |
| `Qwen/Qwen3.5-397B-A17B-FP8` | 200000 | ja | `coming_soon` |
| `google/gemma-4-31B-it` | 100000 | nein | `coming_soon` |
| `mistralai/Ministral-3-14B-Instruct-2512` | 100000 | nein | `ready` |
| `mistralai/Mistral-Small-4-119B-2603` | 256000 | nein | `coming_soon` |
| `moonshotai/Kimi-K2.6` | 256000 | ja | `coming_soon` |
| `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8` | 1000000 | ja | `coming_soon` |
| `swiss-ai/Apertus-v1.5-70B` | 100000 | ja | `coming_soon` |

Das Transkriptionsmodell ist `whisper` (`ready`, `version: "3.0"`, `description: "Whisper V3"`) — der einzige Eintrag, dessen `description` sich vom `name` unterscheidet.

**Der Verfügbarkeitsstatus trügt.** Sieben der acht Sprachmodelle stehen auf `coming_soon` und antworten trotzdem; eines davon beherrscht nachweislich auch Structured Output (Abschnitt 3). `info_status` taugt deshalb **nicht** als Filterkriterium — wer danach filtert, bietet genau ein Modell an.

Die OpenAI-kompatible Liste `GET /2/ai/<product_id>/openai/v1/models` ist der kontoweiten unterlegen: 11 Einträge mit nur `id`, `object`, `created`, `owned_by`, ohne Typ und ohne Beta-Kennung, Sprachmodelle und Embeddings in einem Topf — und **ohne** `whisper`. Sie verlangt zudem die `product_id`.

Ein Gegenstück zu OpenRouters `supported_parameters` gibt es nicht: Nach Structured Output lässt sich bei Infomaniak nicht filtern.

## 3. Sprachmodell-Naht: Structured Output

`POST /2/ai/<product_id>/openai/v1/chat/completions`, OpenAI-kompatibel. **Die API erwartet den rohen Modellnamen**; das Präfix `openai/` ist ausschließlich LiteLLM-Routing und gehört nicht in die Anfrage.

Geprüft mit dem echten `AUSGABE_SCHEMA` der Anwendung — `denkspur` und `aeusserung`, beide `required`, `additionalProperties: false` — als `response_format` vom Typ `json_schema` mit `strict: true`:

| Modell | `finish_reason` | Ergebnis |
|---|---|---|
| `mistralai/Ministral-3-14B-Instruct-2512` | `stop` | valides JSON, exakt die zwei Schemafelder |
| `swiss-ai/Apertus-v1.5-70B` (Beta, `coming_soon`) | `stop` | valides JSON, exakt die zwei Schemafelder |

**ADR-0005 trägt damit bei diesem Anbieter.** Die strict-Teilmenge unseres Schemas wird angenommen, und das zweite Modell zeigt, dass `info_status` auch über den Funktionsumfang nichts aussagt.

Die Antwort trägt ein `reasoning`-Feld in `choices[].message` (bei diesen Aufrufen `null`). Für uns ohne Belang: Die native Spur ist mit #174 gestrichen, die Denkspur kommt aus dem Schema.

## 4. Transkriptions-Naht: der asynchrone Ablauf

`POST /1/ai/<product_id>/openai/audio/transcriptions`, Modell `whisper`, multipart. Die Antwort trägt nur eine Stapelkennung:

```json
{"batch_id": "…"}
```

Das Ergebnis wird an einer Route **neben** der OpenAI-kompatiblen Wurzel abgeholt, nicht unter ihr: `GET /1/ai/<product_id>/results/<batch_id>` — wie im Code bereits angenommen.

### 4.1 Statusnamen

- **`pending`** — laufend. Verifiziert.
- **`success`** — fertig. Verifiziert.
- **Der gescheiterte Zustand bleibt unverifiziert.** Ein Stapel, der startet und dann scheitert, ließ sich nicht provozieren: Eine unbrauchbare Datei wird bereits beim Absenden mit `422` und der Fehlermenge `validation_rule_mimes` abgewiesen und wird nie ein Stapel. Die im Code geführten Namen für den Fehlschlag bleiben damit Vermutung. Folge: Ein tatsächlich gescheiterter Stapel liefe ins volle Budget, statt sofort zu scheitern — gutartig, aber eine bekannte Lücke.

Eine unbekannte Stapelkennung antwortet mit `403 access_result_forbidden`, nicht mit `404`.

### 4.2 Die Gestalt des Ergebnisses hängt an `response_format`

Das ist der Befund, der am leichtesten übersehen wird. Dieselbe Route antwortet in zwei Gestalten, und die Dateiendung in `file_name` verrät welche.

Mit `response_format=text` — **so sendet der Adapter**:

```json
{
  "status": "success",
  "url": "…/results/<batch_id>/download",
  "file_name": "transcription_<batch_id>.txt",
  "file_size": 39,
  "data": "Vielen Dank.\nVielen Dank.\nVielen Dank.\n"
}
```

Ohne `response_format`:

```json
{
  "status": "success",
  "file_name": "transcription_<batch_id>.json",
  "file_size": 51,
  "data": "{\"text\": \" Vielen Dank. Vielen Dank. Vielen Dank.\"}"
}
```

`data` ist in **beiden** Fällen eine Zeichenkette, nie eine Abbildung. Das Stapelobjekt trägt **keinen** `{"result", "data"}`-Umschlag — anders als die übrigen v1-Routen.

Wer die Gestalt rät statt sie an den gesendeten Parameter zu binden, baut eine stille Falle: Ein bedingungsloses Parsen scheitert an der Textform, ein bedingungsloses Durchreichen liefert bei der JSON-Form ein Transkript samt Klammern und Feldnamen.

### 4.3 Formate und Dauer

Angenommene Dateitypen, vom Anbieter in der Fehlermeldung namentlich genannt: `mp3, mp4, aac, wav, flac, ogg, opus, wma, m4a, webm`. Unser Aufnahmeformat ist dabei.

Durchgespielt wurde mit `wav` und mit einer echten `webm`/Opus-Datei (48 kHz, mono), wie sie die Aufnahme im Browser erzeugt — kein Unterschied im Ablauf.

**Dauer:** Fünf Minuten Audio waren in rund **zwei Sekunden** transkribiert, mit drei Abfragen im Zustand `pending` dazwischen. Das Budget von 120 s ist reichlich bemessen. Bei dieser Geschwindigkeit dominiert das Abfrageintervall von 2 s die Wartezeit — wer die Sitzung flüssiger machen will, setzt dort an, nicht am Budget.

## 5. Der Befund, der gegen die Spec steht

**Die Transkription über Infomaniak funktioniert heute nicht.** Der produktive Adapter wurde unverändert gegen die echte API ausgeführt und endet ausnahmslos mit `TranskriptionsAnbieterfehler: Infomaniak antwortete nicht mit einem Stapelergebnis.`

Ursache ist die Umschlag-Heuristik: Sie erkennt den v1-Umschlag am Vorhandensein eines `data`-Feldes allein. Das Stapelobjekt der Ergebnisroute trägt selbst ein solches Feld, wird deshalb fälschlich geschält, und die anschließende Prüfung findet keine Abbildung mehr.

Einzelheiten, Antwortnutzlasten und Abnahmekriterien in **#232**.

## 6. Was offen bleibt

- **Der gescheiterte Statusname** (4.1). Ohne einen echten Fehlschlag nicht zu bekommen.
- **Die datenschutzrechtliche Klärung** — ob Infomaniaks beworbene Zusage in einem AVV steht. Verfolgt in #233.

## Quellen

Alle Angaben dieses Textes stammen aus eigenen Aufrufen gegen `api.infomaniak.com` am 2026-09-21 mit einem gültigen Kontotoken. Die Anbieterdokumentation ist in `docs/research/2026-09-18-zulaessige-anbieter-und-modelle.md` verzeichnet; wo dieser Text ihr widerspricht, gilt dieser Text.
