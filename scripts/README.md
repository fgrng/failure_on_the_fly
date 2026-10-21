# Skripte ohne App

`simulieren.py` spielt einen Gesprächsschritt (docs/agents/simulieren.md),
`evalgespraech.py`, `bewerter_prompt.py` und `urteile_zaehlen.py` spielen
Evalgespräche durch (docs/evals/README.md, Abschnitt «Durchspielen ohne App»).
Alle lesen das Modell aus den `SIMULIEREN_*`-Variablen in `.env`. Diese Datei
hält fest, was der Anbieter dahinter kann.

## Modelle bei Infomaniak, Stand 2026-10-20

Geprüft mit Minimalanfragen gegen
`https://api.infomaniak.com/2/ai/<produkt>/openai/v1` und mit der
OpenAPI-Beschreibung des Anbieters (`docs/infomaniak_api_1792487006.json`, nur
eingeloggt abrufbar). Modellliste über `GET …/models`; Beta-Status und
Kontextlänge über `GET https://api.infomaniak.com/1/ai/models`.

| Modell (`SIMULIEREN_MODELL` ohne `openai/`) | Beta | Kontext | Thinking Standard    | Thinking aus                 | JSON-Schema |
| ------------------------------------------- | ---- | ------- | -------------------- | ---------------------------- | ----------- |
| `swiss-ai/Apertus-v1.5-70B`                 | ja   | 100k    | aus                  | `reasoning_effort: none`     | ja          |
| `Qwen/Qwen3.5-397B-A17B-FP8`                | ja   | 200k    | an, Feld `reasoning` | `reasoning_effort: none`     | ja          |
| `Qwen/Qwen3.5-122B-A10B-FP8`                | nein | 200k    | an, Feld `reasoning` | `reasoning_effort: none`     | ja          |
| `moonshotai/Kimi-K2.6`                      | ja   | 256k    | an, Feld `reasoning` | nur `reasoning_effort: none` | ja          |

Weitere Sprachmodelle im Angebot, ungeprüft: `google/gemma-4-31B-it`,
`mistralai/Mistral-Small-4-119B-2603`,
`mistralai/Ministral-3-14B-Instruct-2512`. Die übrigen Einträge sind Embedding-,
Reranker- und Bildmodelle.

## Parameter

- **Temperatur**: Standard 1, Bereich 0 bis 2 (Doku). Alle vier Modelle nehmen
  Werte von 0 bis 1.9 an; bei Kimi erzeugt 1.9 Zeichensalat. Bei Temperatur 0
  liefert Apertus identische Antworten, Qwen3.5-122B nicht (Mixture of Experts).
  `top_p` Standard 1.
- **Thinking**: Einziger Schalter ist `reasoning_effort`. `none` schaltet aus,
  jeder andere Wert ein; die Stufe selbst wird ignoriert. Die Doku nennt Apertus
  und Mistral 3 als Modelle ohne Thinking.
  `chat_template_kwargs: {"enable_thinking": …}` wird durchgereicht, aber ohne
  Parser: Bei Kimi landen die Überlegungen dann im sichtbaren Inhalt, bei
  Apertus erscheint der Denkblock roh mit `<|inner_prefix|>` im Inhalt. Mit
  JSON-Schema erzwingt die Grammatik bei Apertus sofort das JSON, der Denkblock
  fällt weg. Bei Qwen und Kimi zählen Denktokens zu `max_tokens`; mit Thinking
  an und JSON-Schema bleibt für das JSON nichts übrig, wenn `max_tokens` knapp
  ist.
- **JSON-Schema**: `response_format` mit `json_schema` (so erzwingen App und
  Skripte Denkspur und Äusserung) funktioniert bei allen vier Modellen, bei Qwen
  und Kimi nur sinnvoll mit `reasoning_effort: none`. Kimi stellt dem JSON ein
  Leerzeichen voran, das `json.loads` verträgt.
- **Rate-Limit**: Sechs parallele Anfragen auf dem Konto lösten
  `Rate limit exceeded` aus. `evalgespraech.py` spielt die k Wiederholungen
  parallel; bei k = 3 reicht das, grössere Schleifen über Evals und Vignetten
  laufen besser sequenziell.

## Konfiguration für einen Vergleichslauf

```sh
SIMULIEREN_MODELL=openai/moonshotai/Kimi-K2.6
SIMULIEREN_PARAMETER={"reasoning_effort": "none", "temperature": 1}
```

`reasoning_effort: none` ist bei Qwen und Kimi Pflicht. LiteLLM lehnt
`reasoning_effort` für unbekannte Modelle hinter `openai/` sonst schon vor der
Anfrage mit `UnsupportedParamsError` ab; der Adapter setzt deshalb selbst
`allowed_openai_params` mit allen gesetzten Parametern. Die Temperatur
ausdrücklich setzen, damit sie in den Probelauf-Einträgen steht und ein Lauf mit
anderer Temperatur davon unterscheidbar bleibt. Seit dem 2026-10-20 steht `.env`
auf Kimi-K2.6 mit genau diesen Parametern (docs/evals/README.md, «Stand»).
Apertus lief bis dahin ohne Parameter, also mit Temperatur 1 und ohne Thinking;
ein Thinking-Modus steht für Apertus über diese API nicht zur Verfügung, es
denkt nur in der Denkspur.
