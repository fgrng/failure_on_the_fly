# Testreview: Simulation

Bereich aus #329 (Spec #321). Geprüft sind alle zehn Dateien, die zu #329 in `simulation/tests/` lagen; die beiden späteren bewertet der Nachtrag unten. Für Tests auf die Zeit und auf Migrationen gelten die Entscheidungen aus #324 und #325:

- Die vier Migrationstests in `test_modell_konfiguration.py` sind totes Gewicht (ADR-0031) und werden gestrichen.
- Kein Test hier patcht `timezone.now` oder eine andere Wanduhr. Zwei Dateien ersetzen `time.monotonic`, `test_transkription.py` zusätzlich `time.sleep`. Das sind Uhren an der Grenze zum Anbieter, die `time-machine` nicht steuert; #324 betrifft sie nicht.

**Nachtrag Evalkatalog (#395, Spec #391):** `test_evalkatalog.py` und `test_evalkatalog_view.py` kamen mit #298 und sind nachträglich nach denselben Kriterien bewertet. Dazu gehören die Schnittstellen-Abschnitte Evalkatalog, Katalogteile, Evallauf und Urteil, Evalkatalog-Views, Formulare und Standardkern sowie die beiden Befundtabellen am Ende der Befunde. Umgesetzt wird der Nachtrag in #403. Keine der beiden Dateien patcht die Zeit, keine testet eine Migration.

## Schnittstelle

### Antwortversuch (`simulation/__init__.py`)

- **Aufrufe:**
  - `antwort_versuchen(vignette, kern, modell_konfiguration, verlauf, eingabe) -> Antwortversuch`. Einziger Aufrufer ist `sitzungen.durchlauf`.
  - `vorlage_rendern(vorlage, platzhalter)` setzt die benutzten Platzhalter einer Vorlage ein. Aufrufer sind `antwort_versuchen` und `sitzungen.durchlauf`.
- **Invarianten:**
  - Schreibfrei (ADR-0016): `antwort_versuchen` berührt die Datenbank nicht.
  - Höchstens drei Modellaufrufe je Schritt. Jeder verworfene Aufruf wird ein `Fehlversuch` mit Grund (`Formatbruch`, `Anbieterfehler`, `Content-Filter`) und Rohantwort.
  - Alle Versuche teilen sich eine Frist von 90 s. Jeder Aufruf bekommt die Restzeit als `timeout`, mindestens 1 s. Ist die Frist vor einem Versuch erschöpft, wird ohne Aufruf ein `Anbieterfehler` notiert und abgebrochen.
  - Die Adapterwahl hängt am Feld `anbieter`, nicht am Modellnamen. Echte Anbieter bekommen `api_key` aus dem Token und `api_base` aus der Basis-URL. OpenRouter bekommt immer den Provider-Filter (`require_parameters`, `data_collection: deny`, `zdr`), den keine Konfiguration abschalten kann (ADR-0026).
- **Fehlerfälle:**
  - Scheitern alle Versuche, ist `antwort` gleich `None`; es gibt keine Ausnahme.
  - Fehlt einem benutzten Platzhalter der Wert, wirft `vorlage_rendern` einen `KeyError`.
- **Konfiguration:** keine Umgebung; alles kommt aus der `ModellKonfiguration`.
- **Kante:** `antwort_versuchen` importiert `vignetten.models` funktionslokal. Das ist eine Rückkante gegen ADR-0016 (#378).

### Sprachmodell-Naht (`simulation/sprachmodell/`)

- **Aufrufe:**
  - Protokoll `Sprachmodell.antworten(system_prompt, user_prompt, verlauf, eingabe, ausgabe_schema, timeout) -> Antwort`.
  - Zwei Adapter: `LiteLLMSprachmodell(modell, parameter, completion=None)` und `FakeSprachmodell(skript)`.
  - `AUSGABE_SCHEMA` nennt `denkspur` vor `aeusserung` (ADR-0005).
- **Invarianten:**
  - Der Verlauf reist als native Rollen: System, Arbeitskontext als `user`, danach abwechselnd `user` und `assistant`, zuletzt die Eingabe.
  - Strukturierte Ausgabe mit `strict: True`. Nur genau die beiden Felder gelten als Antwort; eine native Reasoning-Spur des Anbieters wird nicht durchgereicht.
  - `timeout` überschreibt einen gleichnamigen Parameter.
- **Fehlerfälle:** `ContentFilter` (Ausnahme von LiteLLM oder `finish_reason`), `Formatbruch` (Hülle fehlt, kein JSON, falsche Felder), `Anbieterfehler` (jede andere Ausnahme). Alle tragen `rohantwort`.
- **Fake:** verbraucht je Aufruf einen Skripteintrag und spielt `fehler: formatbruch | anbieterfehler | content_filter` ab. Er zeichnet keine Aufrufe auf; Tests lesen die Nachrichten über `config.tests.sprachmodell.anfragen_aufzeichnen` (#379).

### Transkription (`simulation/transkription/`)

- **Aufrufe:**
  - Protokoll `Transkription.transkribieren(audio) -> str`.
  - Drei Adapter: `FakeTranskription(skript)`, `OpenAITranskription(client, modell, sprache)` und `InfomaniakTranskription(client, basis_url, modell, sprache)`.
  - `transkriptions_anbieter()` bildet den Adapter je Aufruf neu aus der `TranskriptionsKonfiguration`.
- **Invarianten:**
  - Anbieter `fake`: ein Platzhaltertext, kein Netz.
  - OpenRouter läuft über den OpenAI-Client. Ohne eigene Basis-URL gilt `https://openrouter.ai/api/v1`, nie die Vorgabe des Clients. Das Token kommt nur aus der Konfiguration, nie aus `OPENAI_API_KEY`.
  - Infomaniak: Absenden an `<basis>/audio/transcriptions` mit `response_format: text`. Abholen an `<basis ohne /openai>/results/<batch_id>` alle 2 s.
  - Gesamtbudget 120 s. Jede Einzelanfrage bekommt die Restzeit, mindestens 1 s.
  - Der v1-Umschlag `{"result", "data"}` wird nur am Paar erkannt.
- **Fehlerfälle:**
  - `AnbieterNichtErreichbar` bei Transportfehlern.
  - `LeeresTranskript` bei leerem oder nur aus Leerraum bestehendem Text.
  - `TranskriptionsAnbieterfehler` für alles andere: Fehlerstatus, gescheiterter Stapel, fehlende Kennung, unlesbares Ergebnis, Budget erschöpft.
  - Ein unbekannter Stapelstand läuft ins Budget.

### Modellverzeichnis (`simulation/modellverzeichnis.py`)

- **Aufrufe:**
  - `modellverzeichnis(anbieter, token) -> Modellverzeichnis`.
  - Am Verzeichnis: `vorschlaege(naht) -> list[Modellvorschlag]` und `basis_url(naht) -> str`.
  - Nähte: `sprachmodell` und `transkription`.
- **Invarianten:**
  - OpenRouter fragt die öffentliche Liste ohne Token. Filter: `supported_parameters=structured_outputs` bzw. `output_modalities=transcription`. Infomaniak fragt `/1/ai/models` mit `Bearer`-Token und filtert nach `type` (`llm` bzw. `stt`).
  - Den Präfix des Anbieters trägt der Wert nur an der Sprachmodell-Naht.
  - Sortiert wird nach der Anzeige, ohne Groß- und Kleinschreibung.
  - `basis_url`: Nur Infomaniak leitet ab, und nur bei genau einem Produkt im Konto. Sprachmodell: `/2/ai/<id>/openai/v1`, Transkription: `/1/ai/<id>/openai`. Der Kontoklarname wird nicht gelesen.
- **Fehlerfälle:** `KeineModellliste` (Anbieter `fake`, unbekannte Naht; vor jedem Netzaufruf), `AnbieterNichtErreichbar`, `AnbieterLehntAb` (bei Infomaniak mit Hinweis auf das Token), `AnbieterAntwortetFormwidrig`.
- **Konfiguration:** Frist 10 s je Abfrage.

### Modelle (`simulation/models.py`)

- **Simulationskern:**
  - Aufrufe: `objects.anlegen(**vorlagen)`, `bearbeiten()`, `finalisieren()`, `delete()`, `clean()`.
  - Invarianten: eine Historie, höchstens ein Entwurf, höchstens eine finale Fassung. `finalisiert_am` passt zum Zustand. Nur Entwürfe sind veränderlich und löschbar. `create`, `update`, `bulk_create` und `bulk_update` sind gesperrt (`RuntimeError`).
  - Fehlerfälle: `ValueError` bei zweiter Anlage, zweitem Entwurf oder falschem Zustand. `ValidationError`, wenn eine Vorlage Platzhalter außerhalb ihres Vertrags (`VERTRAG_PROMPT`, `VERTRAG_RAHMEN`) oder ungültige Syntax hat.
- **ModellKonfiguration:**
  - Append-only: Speichern einer bestehenden Zeile und `update()` werfen `RuntimeError`. `save()` ruft `full_clean()`, also auch aus Shell und Seeds.
  - Anbieterbindung (ADR-0036): `fake` nur mit Modell `fake`, ohne URL und ohne Token. Echte Anbieter brauchen Präfix und Token, Infomaniak zusätzlich die Basis-URL.
  - Die Parameter sind ein Objekt mit Schlüsseln aus der Allowlist des Anbieters; bei `fake` nur `skript`.
- **Verwendungen:**
  - `aktive(verwendung)` liefert `None`, solange unbelegt; `belegte(verwendung)` wirft dann `DoesNotExist`.
  - `aktivieren(konfiguration, verwendung)` setzt den Zeiger; `aktive_je_verwendung()` liefert die belegten Zeiger.
  - Je Verwendung ein Zeiger. Die Verwendung hat bewusst keinen Default. Eine aktive Konfiguration ist vor dem Löschen geschützt (`ProtectedError`).
- **TranskriptionsKonfiguration:**
  - `objects.aktuelle()` liefert die eine Zeile und legt sie beim ersten Zugriff an; Vorgabe `fake` und `de`.
  - Veränderlich. Echte Anbieter brauchen Modellnamen und Token, Infomaniak zusätzlich die Basis-URL.
- **Token-Maske (beide Konfigurationen):** leer ohne Token; acht Punkte unter zwölf Zeichen, sonst acht Punkte und die letzten vier Zeichen.

### Views (`simulation/views.py`, Routen unter `/system/`)

- **Kern:**
  - `kern` (Autor:in, nur lesen) zeigt die finale Fassung, die Platzhalterverträge und die aktive Konfiguration der Schüler:in.
  - `kern_verwalten` (Administration) zeigt Entwurf, finale und archivierte Fassungen. Anlegegesten erscheinen nur, solange es gar keine Fassung gibt.
  - Die POST-Routen `kern_anlegen` (leer oder Standardkern), `neue_fassung`, `finalisieren` und `verwerfen` leiten auf `kern_verwalten` und melden Modellfehler dort.
  - `kern_bearbeiten` liefert 404 für alles außer dem Entwurf und zeigt Vertragsfehler am Feld.
- **Modell-Konfiguration** (Administration):
  - Die Liste wählt die Detailzeile über `?konfiguration=`, sonst die der Schüler:in, sonst die neueste. Das Token erscheint nur maskiert.
  - `modell_konfiguration_neu` legt an, optional aus `?vorlage=`. Die Vorlage füllt alles außer dem Token vor; aktiviert wird dabei nichts.
  - `modell_konfiguration_aktivieren` nimmt nur POST an; unbekannte Verwendung oder Konfiguration ergibt 404.
- **Modellvorschläge** (POST, Administration): liefern ein Fragment mit der Liste und dem Zielfeld der Naht. Ist die Basis-URL leer und lässt sie sich ableiten, setzt das Fragment sie ein; scheitert nur die Ableitung, bleibt die Liste stehen. Das Token erscheint nie in der Antwort.
- **Transkriptions-Konfiguration** (Administration): bearbeitet die eine Zeile. Ein leeres Tokenfeld behält das gespeicherte Token. Nach dem Speichern folgt eine Umleitung, damit das Token nicht im Antwortkörper steht.

### Management-Command `kern_initialisieren`

Legt auf einer leeren Instanz den Standardkern an und finalisiert ihn über die Lebenszyklus-Naht. Läuft die Instanz schon mit einem Kern, tut der Command nichts.

### Standardkern (`simulation/standardkern.py`, Nachtrag #395)

- **Aufrufe:** `STANDARDKERN_VORLAGEN` ist die kanonische Erstfassung der Kern-Inhaltsfelder (GLOSSARY.md, „Standardkern“). Aufrufer sind `kern_anlegen` mit Standardkern, der Command `kern_initialisieren` und die Seeds `workshopdaten_anlegen` und `entwicklungsdaten_anlegen`.
- **Invarianten:** Die Schlüssel sind genau die fünf Inhaltsfelder `system_prompt_vorlage`, `user_prompt_vorlage`, `rahmenhandlung_einleitung`, `rahmenhandlung_gespraechseinleitung` und `rahmenhandlung_debrief`. Jede Vorlage hält ihren Vertrag (`VERTRAG_PROMPT` bzw. `VERTRAG_RAHMEN`); ein Kern aus ihnen lässt sich ohne Änderung finalisieren.
- **Wortlaut:** Der Text ist Inhalt, keine Schnittstelle. Tests prüfen ihn nicht, sondern vergleichen die Felder eines angelegten Kerns mit ihrem Eintrag (siehe `test_legt_einen_entwurf_aus_den_standardvorlagen_an` und `test_kern_initialisieren_legt_eine_finale_platzhalter_fassung_an`).

### Formulare (`simulation/forms.py`, Nachtrag #395)

Die Formulare haben keine eigene Testdatei. Ihre Zusagen zeigen sich im gerenderten Formular und in der Antwort auf POST, also prüfen die View-Tests sie.

- **`SimulationskernForm`** (`kern_bearbeiten`): die fünf Inhaltsfelder eines Kern-Entwurfs, beschriftet wie in der Leseansicht. Der Hilfetext jedes Felds nennt die erlaubten Platzhalter seines Vertrags. Bei den Prompt-Vorlagen nennt er zusätzlich die Platzhalter, die eine benannte Umgebung erzeugen. Die Vertragsprüfung selbst macht das Modell (`clean()`, `finalisieren()`).
- **`EvalkatalogDurchlaufForm`** (Knoten Durchlauf und Vorlagen, dazu jede Geste des Editors): `k`, `lehrperson_vorlage`, `bewerter_vorlage`. Es prüft nur die Feldtypen: `k` ist eine ganze Zahl ab 0, die Vorlagen dürfen leer sein. Vertrag, leere Vorlagen und `k ≥ 1` prüft erst `finalisieren()`.
- **`ModellKonfigurationForm`** (`modell_konfiguration_neu`): einzige Schreibgeste an einer append-only Konfiguration. Die Eingabefolge ist `bezeichnung`, `anbieter`, `anbieter_token`, `anbieter_basis_url`, `sprachmodell`, `parameter`. Das Token ist write-only und wird nie zurückgerendert, auch nicht bei einem Formfehler. Ein leeres Parameterfeld gilt als `{}`, ungültiges JSON meldet „Bitte gültiges JSON eintragen.“. Der Hilfetext am Parameterfeld nennt die Allowlist je Anbieter.
- **`TranskriptionsKonfigurationForm`** (`transkriptions_konfiguration`): die eine Zeile, Eingabefolge `anbieter`, `anbieter_token`, `anbieter_basis_url`, `transkriptionsmodell`, `sprache`. Das Token ist write-only; ein leeres Tokenfeld behält das gespeicherte.
- **Gemeinsam:** Die Anbieterbindung prüft das Modell über `full_clean()`; ihre Fehler erscheinen am Feld.

### Evalkatalog (`simulation/models.py`, Lebenszyklus aus `simulation/lebenszyklus.py`, Nachtrag #395)

- **Aufrufe:**
  - `Evalkatalog.objects.anlegen()` legt die erste Fassung als leeren Entwurf an: `k = 3`, beide Vorlagen leer. Einen Standardkatalog gibt es nicht (ADR-0046).
  - Lebenszyklus aus derselben Basis `VersionierteFassung` wie der Kern: `bearbeiten()` zieht aus der finalen Fassung einen Entwurf, `finalisieren()`, `delete()` nur am Entwurf.
  - `objects.finale_fassung()` liefert die finale Fassung oder `None`. Das ist die Abfrage für andere Apps, künftig für den Evallauf.
  - `maengel() -> list[str]` liefert je Lücke eine Meldung, bei einem vollständigen Entwurf `[]`. Einziger Aufrufer ist `finalisieren()`.
  - `kriterium_anlegen(text)` und `eval_anlegen(name)` hängen Teile ans Ende.
  - `zustandsbezeichnung` nennt den Zustand wie der Editor: archiviert heißt „Überholt“.
- **Invarianten:**
  - Eine namenlose Linie (`EvalkatalogHistorie`, eine Zeile) mit höchstens einem Entwurf und höchstens einer finalen Fassung. `finalisiert_am` passt zum Zustand (`lebenszyklus_constraints`).
  - Finalisieren überholt die bisherige finale Fassung im selben Schritt; überholt ist nicht umkehrbar. Ungespeicherte Werte von `k` und den Vorlagen gehen mit dem Zustandswechsel in die Fassung.
  - `bearbeiten()` kopiert `k`, beide Vorlagen, die übergreifenden Kriterien und den Baum aus Evals, Evalkriterien, Evalinputs und Inputschritten (mit Art und Text) in gleicher Reihenfolge. Der Entwurf verweist auf die Vorgängerin; Änderungen an ihm berühren sie nicht.
  - Ein Entwurf darf unvollständig gespeichert werden. Finalisieren verlangt ohne Modellaufruf: beide Vorlagen nichtleer, gültig und nur mit Platzhaltern ihres Vertrags; `k ≥ 1`; mindestens ein Eval; je Eval mindestens ein Evalkriterium und einen Evalinput; je Evalinput mindestens einen Inputschritt; kein leerer Inputschritt, kein leeres Evalkriterium, kein leeres übergreifendes Kriterium. Übergreifende Kriterien dürfen fehlen.
- **Platzhalterverträge (ADR-0010):** `VERTRAG_LEHRPERSON` ist der Promptvertrag plus `inputstrategie` und `verlauf`, `VERTRAG_BEWERTER` der Promptvertrag plus `kriterium` und `verlauf`. `VERTRAG_EVAL` ist ihre Vereinigung. Er hat im Produktionscode noch keinen Aufrufer; der Evallauf aus #299 rendert aus ihm.
- **Fehlerfälle:**
  - `RuntimeError` (Regel A, ADR-0021): `objects.create()`, `update()`, `bulk_create`, `bulk_update`.
  - `ValidationError` beim Finalisieren eines unvollständigen Entwurfs, mit allen Lücken auf einmal in fester Reihenfolge: Vorlagen, `k`, übergreifende Kriterien, Evals. Ein namenloses Eval heißt in der Meldung „Unbenanntes Eval“.
  - `ValidationError` mit Meldung bei zweitem `anlegen()` („Der Evalkatalog wurde bereits angelegt.“), bei `bearbeiten()` mit bestehendem Entwurf („Ein Evalkatalog-Entwurf existiert bereits.“) oder an einer inzwischen geänderten Fassung, bei `finalisieren()` einer inzwischen finalisierten Fassung („Nur Entwürfe können finalisiert werden.“) und bei `save()` oder `delete()` außerhalb des Entwurfs.

### Katalogteile: übergreifendes Kriterium, Eval, Evalkriterium, Evalinput, Inputschritt (Nachtrag #395)

- **Aufrufe:**
  - Anlegen hängt ans Ende der Geschwister: `Evalkatalog.kriterium_anlegen(text)`, `Evalkatalog.eval_anlegen(name)`, `Eval.kriterium_anlegen(text)`, `Eval.input_anlegen()`, `Evalinput.schritt_anlegen(art=FEST, text="")`.
  - Lesen über die Relationen in Positionsreihenfolge: `katalog.uebergreifende_kriterien`, `katalog.evals`, `eval.kriterien`, `eval.inputs`, `evalinput.schritte`.
  - `verschieben(-1 | +1)` tauscht mit dem Nachbarn; am Rand bleibt alles, wie es ist. Dazu `save()` und `delete()`.
  - `Evalinput.kuerzel` gibt die Schrittfolge als F (fest) und G (gelenkt) wieder, etwa „FFG“. `Inputschritt.gelenkt` sagt, ob die Lehrperson nach Strategie formuliert.
- **Invarianten:**
  - Kriterien und Inputschritte sind reiner Text ohne Platzhalter. „Kern-neutral“ bei übergreifenden Kriterien ist eine Pflegeregel, keine Prüfung (ADR-0046).
  - Ein neuer Evalinput startet mit drei leeren, festen Inputschritten.
  - Ein Eval nimmt beim Löschen seine Evalkriterien, Evalinputs und Inputschritte mit, ein Evalinput seine Schritte.
  - Die Position ist je Elternteil eindeutig (DB). `Eval.name` hat höchstens 200 Zeichen.
  - Jeder Teil teilt die Schreibsperre seiner Fassung: Er ändert sich nur an einem Entwurf, auch gesammelt und auch beim Umhängen aus einer finalen Fassung in einen Entwurf.
- **Fehlerfälle:** `ValidationError` („Der Evalkatalog ändert sich nur an einem Entwurf.“) für `save()`, `delete()`, `verschieben()`, Anlegen und `QuerySet.delete()` an Teilen einer finalen oder überholten Fassung. `RuntimeError` für `update()`, `bulk_create` und `bulk_update` auf Teilen, unabhängig vom Zustand.

### Evallauf und Urteil (Nachtrag #395)

Beide gibt es noch nicht. Sie entstehen mit Spec #299 in einer eigenen App `evals`; keine Datei testet sie. Was der Evalkatalog ihnen heute zusagt, steht in seiner Schnittstelle oben:

- Die einzige Abfrage ist `Evalkatalog.objects.finale_fassung()`. Nichts pinnt den Katalog (ADR-0046).
- `k` ist die Zahl der Evalgespräche je Evalinput, die Zahl seiner Inputschritte die Länge jedes Evalgesprächs. Bei `fest` ist der Text die Inputäußerung, bei `gelenkt` die Inputstrategie (`$inputstrategie`).
- Ein Urteil fällt je Evalgespräch für jedes Evalkriterium seines Evals und für jedes übergreifende Kriterium (`$kriterium`).
- Die Vorlagen rendern aus `VERTRAG_LEHRPERSON` bzw. `VERTRAG_BEWERTER`; `$verlauf` rendert der Evallauf je Empfänger (ADR-0010).

### Evalkatalog-Views (`simulation/views.py`, Routen unter `/system/evalkatalog/`, Nachtrag #395)

- **Zugriff:** nur Administration. Alle anderen Rollen bekommen 403, lesend wie schreibend. Schreibende Routen nehmen nur POST an (405).
- **Übersicht** `evalkatalog`:
  - Ohne Katalog bietet sie „Evalkatalog anlegen“ an, mit Entwurf „Entwurf bearbeiten“ und „Entwurf verwerfen“.
  - Mit finaler Fassung zeigt sie „Finale Fassung lesen“ und, solange kein Entwurf besteht, „Neue Fassung“.
  - Überholte Fassungen stehen als Liste darunter, die zuletzt gültige zuerst.
- **Lebenszyklus** (POST):
  - `evalkatalog_anlegen` öffnet den Editor. Ein zweites Anlegen führt mit Meldung auf die Übersicht.
  - `evalkatalog_neue_fassung` erreicht nur die finale Fassung (sonst 404) und öffnet den Editor des neuen Entwurfs. Bei bestehendem Entwurf führt sie mit Meldung auf die Übersicht.
  - `evalkatalog_verwerfen` erreicht nur den Entwurf.
  - `evalkatalog_finalisieren` übernimmt zuerst alle getippten Werte. Danach landet die Administrator:in auf der Übersicht mit „Der Evalkatalog ist final. Jeder Evallauf prüft ab jetzt gegen ihn.“ oder im Editor mit je einer Meldung pro Lücke.
- **Editor:**
  - Vier Knotenarten: Durchlauf und Vorlagen, Übergreifende Kriterien, Eval, Evalinput. Links steht der Baum, rechts der Knoten.
  - Lesen erreicht jede Fassung, ein POST nur Entwürfe (sonst 404).
  - Ein Teil muss zur genannten Fassung bzw. zum genannten Eval oder Evalinput gehören, sonst 404; ebenso jede Richtung außer `hoch` und `runter`.
- **Gesten:**
  - Jede Geste sendet das ganze Formular und übernimmt zuerst alle getippten Werte: Hinzufügen, Löschen, Verschieben, Speichern, Finalisieren. Die Felder heißen `k`, `lehrperson_vorlage`, `bewerter_vorlage`, `kriterium-<pk>`, `eval-<pk>`, `evalkriterium-<pk>`, `inputschritt-<pk>` und `inputschritt-art-<pk>`.
  - Ein ungültiger Wert des Durchlaufs bleibt ungespeichert und wird gemeldet; gültige Vorlagen gelten trotzdem.
  - Ungültige Teilwerte (Name über 200 Zeichen, unbekannte Art) bleiben ohne Meldung ungespeichert. Fremde Schlüssel bleiben folgenlos.
  - Nach jeder Geste leitet die View auf einen Knoten weiter.
- **Platzhalterknöpfe:** je Vorlage die Namen ihres Vertrags als `data-platzhalter` mit `data-ziel`. Der vorlageneigene steht vorn, die übrigen alphabetisch.
- **Gesperrte Fassungen:** Ein Hinweisband nennt Zustand und Datum. Alle Felder sind `disabled`. Es gibt keine Gesten, keine Platzhalterknöpfe und keine Warnung vor ungespeicherten Änderungen. „Neue Fassung“ steht nur an der finalen Fassung, solange kein Entwurf besteht.
- **Sidebar:** Der Link „Evalkatalog“ trägt auf jedem Knoten `aria-current`.
- **Transaktion:** Die Knoten Kriterien, Eval und Evalinput rendern auch auf GET innerhalb von `transaction.atomic`, also unter der Schreibsperre (#409).

## Befunde

### `simulation/tests/test_antworten.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_antwort_versuchen_liefert_denkspur_und_aeusserung_des_fakes`, `…_haelt_formatbruch_neben_der_antwort_fest`, `…_haelt_anbieterfehler_neben_der_antwort_fest` | behalten | Schnittstelle, Literale. Sie laufen ohne `django_db` und belegen damit nebenbei, dass `antwort_versuchen` die Datenbank nicht berührt. | – |
| `test_antwort_versuchen_kennzeichnet_drei_verworfene_versuche` | umschreiben | Tautologisch: Skriptlänge und Erwartung kommen aus `MAX_VERSUCHE`. Mit `MAX_VERSUCHE = 1` bestünde der Test weiter. | Skript mit vier Anbieterfehlern; Erwartung: `antwort is None` und genau drei Fehlversuche (Literal 3). ADR-0011 lässt die Zahl offen; der Test hält damit die Entscheidung fest. |
| `test_antwort_versuchen_gibt_dem_fake_nur_sichtbaren_verlauf` | streichen | Tautologisch: Der Test baut den Verlauf selbst aus der Äußerung. Dass die Denkspur nicht im Ergebnis steht, folgt aus seiner Eingabe, nicht aus `antwort_versuchen`. Zudem liest er `letzte_anfragen[1]` und hängt an geteiltem Zustand (#379). | `sitzungen/tests/test_probelauf.py::…::test_modellverlauf_traegt_beide_gespraechsseiten`: Dort baut `sitzungen` den Verlauf aus gespeicherten Schritten, deren Fake-Antwort eine Denkspur trägt, und die `assistant`-Nachricht ist genau die Äußerung. Die Rollenfolge prüft `test_litellm_adapter_uebergibt_den_verlauf_als_konversationsnachrichten`. |
| `test_ausgabe_schema_fuehrt_denkspur_vor_aeusserung` | umschreiben | Prüft eine Modulkonstante, nicht, was den Anbieter erreicht. | In `test_litellm_sprachmodell.py`: `antwort_versuchen` mit gemocktem `litellm.completion`. Die Schlüssel von `response_format["json_schema"]["schema"]["properties"]` im Aufruf sind in dieser Reihenfolge `["denkspur", "aeusserung"]`. |
| `test_antwort_versuchen_persistiert_nichts` | streichen | Schwach: `ModellKonfiguration` ist append-only, die Zahl kann sich gar nicht ändern. Andere Tabellen prüft der Test nicht. | Die Tests oben laufen ohne `django_db`. pytest-django lässt jeden Datenbankzugriff dort scheitern. Damit ist „schreibfrei“ stärker belegt als hier. |

### `simulation/tests/test_litellm_sprachmodell.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_litellm_adapter_reicht_konfiguration_und_schema_durch`, `…_uebergibt_den_verlauf_als_konversationsnachrichten`, `…_reicht_native_reasoning_felder_nicht_durch`, `…_kennzeichnet_content_filter`, `…_kennzeichnet_content_policy_exception_als_filter`, `…_kennzeichnet_fehlende_antworthuelle_als_formatbruch`, `…_kennzeichnet_zusaetzliches_feld_als_formatbruch` | behalten | Startbefund bestätigt: Die Aufruf-Assertions betreffen nur den Payload an `completion` (Modell, Nachrichten, `response_format`, Parameter, `timeout`). `AUSGABE_SCHEMA` und die Frist sind dort Eingaben, keine berechneten Erwartungen. | – |
| `test_antwort_versuchen_bildet_litellm_adapter_aus_modell_konfiguration`, `…_reicht_token_und_basis_url_an_den_aufruf_durch`, `…_setzt_den_provider_filter_bei_openrouter`, `…_waehlt_den_fake_adapter_ueber_das_anbieterfeld` | behalten | Payload an der LiteLLM-Grenze, Erwartungen als Literale. Der Provider-Filter steht als Literal im Test, nicht als importierte Konstante. | – |
| `test_antwort_versuchen_teilt_eine_frist_ueber_alle_versuche` | umschreiben | Die Testuhr ersetzt `time.monotonic` und bleibt (siehe Einleitung). Die Erwartung `[SPRACHMODELL_FRIST_SEKUNDEN, SPRACHMODELL_FRIST_SEKUNDEN * 0.4]` ist aus der Modulkonstante berechnet. | Gleicher Ablauf; der Anbieter verbraucht je Aufruf 54 s. Erwartung als Literal: `timeout`-Werte `[90.0, 36.0]`, zwei Aufrufe, drei Fehlversuche. Die 90 s nennt `docs/DEPLOYMENT.md`. |
| `test_timeout_steht_nicht_in_der_allowlist_der_stellschrauben` | umschreiben | Abwesenheit in einer Modulkonstante. | In `test_modell_konfiguration.py` neben `test_lehnt_api_key_ab`: `_openrouter(parameter={"timeout": 5})` wirft `ValidationError` mit `timeout`. |
| `test_ein_aufruf_mit_aufgebrauchter_frist_bekommt_die_mindestfrist` | umschreiben | Erwartung aus `SPRACHMODELL_MINDEST_ANFRAGEFRIST_SEKUNDEN`. | Uhr mit Schritt `89.5`; Erwartung `timeout == 1.0`. |

### `simulation/tests/test_models.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_render_substituiert_alle_vereinbarten_platzhalter`, `test_render_lehnt_fehlende_platzhalter_ab` | umschreiben | Sie prüfen `render`, dessen einziger Aufrufer `vorlage_rendern` ist (#380). | Dieselben Fälle über `vorlage_rendern`: Werte werden eingesetzt; ein benutzter Platzhalter ohne Wert ergibt `KeyError`. |
| `test_render_lehnt_ueberzaehlige_platzhalter_ab` | umschreiben | Prüft einen Zweig, den kein Produktionspfad erreicht (#380). | `vorlage_rendern("$name", {"name": "Mia", "thema": "Brüche"}) == "Mia"`: Übrige Werte werden ignoriert. Das ist das Verhalten, auf das sich `antwort_versuchen` verlässt. |
| `test_anlegen_legt_entwurf_mit_eifriger_historie_an`, `test_anlegen_laesst_keine_lebenszyklusfelder_ueberschreiben`, `test_direktes_anlegen_…`, `test_direktes_aktualisieren_…`, `test_finale_fassung_kann_nicht_gesammelt_geloescht_werden` | behalten | Lebenszyklus-Naht und gesperrte Schreibrouten über die öffentliche API. | – |
| `test_finalisieren_lehnt_vertragsfremde_platzhalter_je_feld_ab`, `test_finalisieren_speichert_den_geprueften_entwurf`, `test_bearbeiten_einer_finalen_fassung_erzeugt_einen_neuen_entwurf`, `test_bearbeiten_lehnt_zweiten_entwurf_ab`, `test_finalisieren_laesst_genau_eine_finale_fassung_zurueck`, `test_finale_fassung_ist_ausserhalb_des_lebenszyklus_unveraenderlich` | behalten | – | – |
| `test_anlegen_lehnt_eine_zweite_erste_fassung_ab`, `test_finalisieren_lehnt_eine_finale_fassung_ab`, `test_finalisieren_in_zweitem_tab_lehnt_den_uebergang_ab`, `test_bearbeiten_lehnt_eine_inzwischen_geaenderte_fassung_ab`, `test_zustandswechsel_ueber_save_wird_abgelehnt` | behalten | Nachtrag (#400): Fehlerfälle des Lebenszyklus über die öffentliche API, Meldungen als Literale. Der zweite Tab (veraltete Instanz im Zustand Entwurf) ist ein anderer Pfad als das erneute Finalisieren derselben Instanz. | – |
| `test_entwurf_kann_physisch_geloescht_werden`, `test_anlegen_ist_nach_loeschen_des_einzigen_entwurfs_wieder_moeglich`, `test_finale_fassung_kann_nicht_physisch_geloescht_werden`, `test_archivierte_fassung_kann_nicht_physisch_geloescht_werden` | behalten | – | – |
| `test_vertragsfremder_prompt_platzhalter_wird_abgelehnt` | streichen | Doppelung in derselben Datei: derselbe Fall (`system_prompt_vorlage`, `$lehrperson_name`) über `full_clean` statt über `finalisieren`. | `test_finalisieren_lehnt_vertragsfremde_platzhalter_je_feld_ab[system_prompt_vorlage-$lehrperson_name]` |
| `test_ungueltige_vorlagen_syntax_wird_abgelehnt`, `test_vertragstreue_teilmengen_und_leere_vorlagen_werden_akzeptiert` | behalten | `clean()` ist Schnittstelle; es gibt keinen anderen Test zur Syntax. | – |
| `test_kern_historie_ist_ein_singleton`, `test_historie_hat_hoechstens_einen_entwurf`, `test_historie_hat_hoechstens_eine_finale_fassung`, `test_finalisiert_am_muss_genau_dem_zustand_entsprechen` | behalten | Constraint-Tests über eine interne Naht (`models.QuerySet(...).bulk_create`), von #321 ausdrücklich erlaubt. | – |
| `test_aktivieren_bewegt_den_zeiger_ohne_zweite_aktive_konfiguration` | streichen | Doppelung zwischen Dateien. | `test_modell_konfiguration.py::test_nach_dem_aktivieren_liefert_die_verwendung_genau_diese` (prüft zusätzlich, dass es nur einen Zeiger gibt) |
| `test_modell_konfiguration_ist_nach_dem_anlegen_unveraenderlich`, `test_modell_konfiguration_kann_nicht_per_queryset_mutiert_werden`, `test_aktive_modell_konfiguration_kann_nicht_geloescht_werden` | behalten | Append-only und Löschschutz an der Schnittstelle. | Die beiden ersten sind zugleich Ersatz für mehrere View-Tests unten. |
| `test_transkriptions_konfiguration_beginnt_bei_fake_auf_deutsch` | behalten | Vorgabe der einen Zeile, Literale. | – |
| `test_transkriptions_konfiguration_ueberschreibt_ihre_eine_zeile` | streichen | Doppelung mit dem View-Test, der denselben Weg über HTTP geht und dieselbe Zusage prüft. | `test_transkriptions_konfiguration.py::TranskriptionsKonfigurationSeiteTests::test_zweimaliges_speichern_erzeugt_keine_zweite_konfiguration` |
| `test_transkriptions_konfiguration_traegt_keinen_rohen_parameterbeutel` | streichen | Startbefund bestätigt: Abwesenheit eines Feldes über `_meta.get_fields()`. | Keiner nötig (CODING_STANDARDS, „Never the absence of fields“). |

### `simulation/tests/test_modell_konfiguration.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_fake_laeuft_ohne_endpunkt_und_ohne_token`, `test_openrouter_verlangt_praefix_und_token_und_kommt_ohne_url_aus`, `test_infomaniak_verlangt_praefix_url_und_token`, `test_der_modellname_wird_nicht_gegen_eine_liste_geprueft` | behalten | Anbieterbindung über `create` (also `save` und `full_clean`). | – |
| `test_lehnt_fremdes_praefix_beim_anbieter_ab`, `test_lehnt_echten_anbieter_ohne_token_ab`, `test_lehnt_infomaniak_ohne_basis_url_ab`, `test_lehnt_fake_mit_zugangsdaten_ab`, `test_lehnt_fake_mit_fremdem_modellnamen_ab` | behalten | – | – |
| `test_nimmt_mikro_stellschrauben_an`, `test_lehnt_schluessel_ausserhalb_der_allowlist_ab`, `test_lehnt_mock_response_ab`, `test_lehnt_api_key_ab`, `test_lehnt_extra_body_ab`, `test_erlaubt_skript_nur_beim_anbieter_fake`, `test_lehnt_skript_bei_echtem_anbieter_ab`, `test_lehnt_ungueltiges_json_ab`, `test_lehnt_parameter_ohne_schluesselraum_ab` | behalten | Allowlist über die Schnittstelle, Literale. Dazu kommt der `timeout`-Fall aus `test_litellm_sprachmodell.py`. | – |
| `test_maskiert_das_token_bis_auf_die_letzten_vier_zeichen`, `test_maskiert_kurze_token_vollstaendig`, `test_maskiert_das_fehlende_token_als_leeren_wert` | behalten | Literale Erwartungen. Sie decken die gemeinsame Basis `AnbieterFeldgruppe` auch für die Transkription. | – |
| `test_verlangt_eine_bezeichnung` | behalten | – | – |
| `test_die_bezeichnung_ist_nach_dem_anlegen_unveraenderlich` | streichen | Doppelung: derselbe Mechanismus wie für jedes andere Feld. | `test_models.py::test_modell_konfiguration_ist_nach_dem_anlegen_unveraenderlich` |
| `test_migration_benennt_den_bestand_nach_sprachmodell_und_nummer` | streichen | Totes Gewicht: `simulation.0007` liegt auf `main` (ADR-0031, #325). | Keiner nötig. |
| `test_migration_macht_die_aktive_zur_schuelerin` | streichen | Totes Gewicht: `simulation.0008` (ADR-0031, #325). | Keiner nötig. |
| `test_migration_laesst_das_anlagedatum_des_bestands_leer` | streichen | Totes Gewicht: `simulation.0009`/`0010` (ADR-0031, #325). | Keiner nötig. |
| `test_migration_datiert_den_bestand_auf_seine_frueheste_sitzung` | streichen | Totes Gewicht: `simulation.0009`/`0010` (ADR-0031, #325). | Keiner nötig. |
| `test_nach_dem_aktivieren_liefert_die_verwendung_genau_diese`, `test_unbelegte_verwendung_liefert_keine`, `test_dieselbe_konfiguration_dient_mehreren_verwendungen`, `test_umschalten_einer_verwendung_laesst_die_anderen_unberuehrt`, `test_aktive_je_verwendung_nennt_nur_belegte_verwendungen` | behalten | Manager-Schnittstelle der Verwendungen. Ersatz für zwei View-Tests unten. | – |
| `test_haelt_den_anlagezeitpunkt_fest` | behalten | Patcht keine Uhr (#324 greift nicht). Mit `time-machine` aus #349 ließe sich das Datum exakt prüfen. | – |
| `test_die_verwendung_hat_keinen_default` | umschreiben | Startbefund geprüft: `inspect.signature` liest die Struktur der Signatur, nicht das Verhalten. Als Typ- oder Lint-Regel ist es aber nicht besser aufgehoben: `ty` prüft nur Aufrufstellen gegen die Signatur und kann einen neu eingeführten Default nicht verbieten; ruff hat keine Regel dafür. Startbefund daher **verworfen**, das Urteil aber nicht „behalten“. | Über die Schnittstelle, wie schon `test_anlegen_laesst_keine_lebenszyklusfelder_ueberschreiben`: `aktive()`, `belegte()` und `aktivieren(konfiguration)` ohne Verwendung werfen je `TypeError`. |

### `simulation/tests/test_kern_view.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `SimulationskernAnsichtLeereRahmenhandlungTests::test_leere_abschnitte_zeigen_einen_strich` | behalten | Der Container wird gezählt, weil der Strich sonst nicht zuzuordnen ist. | – |
| `SimulationskernAnsichtMitKernTests::test_zeigt_den_system_prompt_…`, `test_zeigt_den_user_prompt_…`, `test_zeigt_keinen_aelteren_system_prompt`, `test_zeigt_die_aktive_modellkonfiguration` | behalten | HTTP, Literale. | – |
| `…::test_zeigt_die_einleitung_der_neuesten_finalen_fassung`, `…::test_zeigt_den_debrief_…`, `…::test_zeigt_die_gespraechseinleitung_…` | streichen | Doppelung in derselben Klasse. | `test_rendert_die_rahmenhandlung_mit_woertlichen_platzhaltern` prüft alle drei Abschnitte: `<h3>Aktuelle Einleitung</h3>`, `<li><em>erster Schritt</em></li>` aus der Gesprächseinleitung und `Aktueller Debrief<br>…`. |
| `…::test_rendert_die_rahmenhandlung_mit_woertlichen_platzhaltern`, `…::test_zeigt_die_erlaubten_platzhalter_beider_vertraege`, `…::test_benennt_die_gemeinsamen_abschnitte_fuer_hilfstechnologien` | behalten | Literale; die `aria-label` sind eine Zusage an Hilfstechnologien. | – |
| `…::test_zeigt_keine_verwaltungsgesten` | umschreiben | Abwesenheit von drei Wörtern auf der ganzen Seite. | `submit_knoepfe(response)` liefert nur den Abmelden-Knopf der Sidebar: Die Leseansicht hat keine eigene Absendegeste. |
| `SimulationskernLeereAnsichtTests::test_stellt_den_leeren_kern_nur_fest`, `…::test_zeigt_fehlende_aktive_modellkonfiguration`, `…::test_erfordert_anmeldung` | behalten | – | – |
| `…::test_verweist_autorinnen_nicht_auf_die_verwaltung` | umschreiben | `assertNotContains("manage.py")` prüft die Abwesenheit eines früheren Hinweises (totes Gewicht). | Nur die Zusicherung auf die URL von `kern_anlegen` behalten. |
| `ModellKonfigurationAnzeigeTests` (2 Tests) | behalten | Eigene Seite (`kern_verwalten`), Maske als Literal. | – |
| `SimulationskernRollenTests` | behalten | – | – |
| `SimulationskernAnlegenTests` (6 übrige Tests) | behalten | – | – |
| `SimulationskernAnlegenTests::test_legt_einen_entwurf_aus_den_standardvorlagen_an` | umschreiben | Tautologisch: Die Schleife läuft über `STANDARDKERN_VORLAGEN.items()`. Wäre die Konstante leer oder fehlte ein Feld, bestünde der Test weiter. Die Werte selbst sind keine berechnete Erwartung: Der Standardkern ist laut GLOSSARY.md genau dieser Text, eine Abschrift im Test wäre die schlechtere Quelle. | Die fünf Feldnamen als Literal (`system_prompt_vorlage`, `user_prompt_vorlage`, `rahmenhandlung_einleitung`, `rahmenhandlung_gespraechseinleitung`, `rahmenhandlung_debrief`); je Feld ist der Wert des Entwurfs gleich dem Eintrag in `STANDARDKERN_VORLAGEN`. |
| `SimulationskernVerwaltungTests::test_traegt_die_entwicklungs_farbfläche` | streichen | Doppelung, dazu ein Klassenstring. | `konten/tests/test_navigation.py::BereichszuordnungTests` führt `simulation:kern_verwalten` und `simulation:kern_bearbeiten` mit `authoring`. |
| `…::test_zeigt_den_entwurf`, `…::test_verlinkt_den_entwurf_zur_eigenen_bearbeitungsseite`, `…::test_bearbeitungsseite_zeigt_felder_und_platzhaltervertraege`, `…::test_bearbeitungsseite_benennt_die_felder_wie_die_ansicht` | behalten | – | – |
| `…::test_rahmenhandlung_bietet_hinweis_und_umschalter_im_szenentext` | umschreiben | `assertNotContains("[Linktext](https://…)")` prüft die Abwesenheit eines entfernten Hinweises. | Diese eine Zusicherung streichen, den Rest (Vorschau-Knöpfe, IDs, `aria-describedby`, fünf Vertragshinweise) behalten. |
| `…::test_kern_vorschau_laesst_platzhalter_woertlich_stehen` | umschreiben | Prüft die Route `texte:vorschau` einer anderen App. `texte/tests/test_vorschau.py` prüft keine `$`-Platzhalter, eine Doppelung ist es also nicht. | Unverändert nach `texte/tests/test_vorschau.py` verschieben (Hinweis für #331). |
| `…::test_platzhalteranzeige_folgt_dem_prompt_vertrag` | streichen | Tautologisch: Die Erwartung iteriert über `VERTRAG_PROMPT`. Fehlt ein Name in der Konstante, besteht der Test weiter. | `SimulationskernAnsichtMitKernTests::test_zeigt_die_erlaubten_platzhalter_beider_vertraege` prüft Literale am selben Include (`prompt_platzhalter.html`). `test_bearbeitungsseite_zeigt_felder_und_platzhaltervertraege` belegt, dass die Bearbeitungsseite es einbindet. |
| `…::test_ungueltiger_platzhalter_erscheint_am_verursachenden_feld`, `…::test_speichert_aenderungen_und_zeigt_sie_nach_finalisierung_an`, `…::test_bearbeiten_weist_finale_und_archivierte_fassungen_ab`, `…::test_bearbeiten_weist_autorin_ohne_administrationsrolle_ab`, `…::test_zieht_aus_finaler_fassung_einen_entwurf`, `…::test_verwirft_den_entwurf` | behalten | – | – |
| `…::test_finalisiert_den_entwurf` | streichen | Tautologisch: `<h2>Finale Fassung</h2>` steht wegen `setUp` schon vor dem POST auf der Seite. Der Test bestünde auch, wenn `finalisieren` nichts täte. | `test_speichert_aenderungen_und_zeigt_sie_nach_finalisierung_an` finalisiert über HTTP und findet den geänderten Prompt in der Leseansicht. |
| `…::test_verwerfen_weist_finale_und_archivierte_fassungen_ab` | umschreiben | Belegt das Ausbleiben des Löschens über `objects.filter(...).exists()` statt über die Seite. | Nach dem POST zeigt die Übersicht weiter „Aktueller Prompt“ und „Archivierter Prompt“; die Meldung bleibt. |
| `…::test_gesten_sind_post_und_administratorinnen_vorbehalten`, `…::test_zeigt_modellfehler_als_meldung`, `…::test_zeigt_unvollstaendigen_entwurf_als_meldung` | behalten | – | – |
| `…::test_zeigt_alle_meldungen_einer_ablehnung` | behalten | Nachtrag (#400): HTTP, die verbundene Meldung als Literal. Kein anderer Test prüft mehrere Fehler in einer Meldung. | – |
| `…::test_ueberschreibt_die_finale_fassung_ohne_verwendungs_markierung` | streichen | Totes Gewicht: Abwesenheit einer früheren Beschriftung. Die Überschrift steht schon in `setUp`. | `…::test_zeigt_die_finale_fassung` |
| `…::test_zeigt_die_finale_fassung`, `…::test_zeigt_die_archivierte_fassung`, `…::test_klappt_archivierte_fassungen_ein` | behalten | – | – |
| `…::test_zeigt_archivierte_fassungen_ohne_aktionsbereich` | umschreiben | Schneidet die Seite an `<details>` und sucht den Klassennamen `page-actions`. | Über die Routen: Die Seite nennt keine URL von `neue_fassung`, `finalisieren` oder `verwerfen` mit dem `pk` der archivierten Fassung. „Archivierter Prompt“ bleibt sichtbar. |
| `…::test_weist_autorin_ab`, `…::test_weist_konto_ohne_rolle_ab`, `…::test_weist_nicht_angemeldetes_konto_ab` | behalten | – | – |
| `SimulationskernLangeTexteTests::test_texte_erscheinen_gerendert_mit_bearbeiten_oder_text_schreiben` | umschreiben | Zählt den Klassenstring `page-field--wide markdown-lesefeld"`. | Den Klassenzähler streichen. Gerenderter Markdown, wörtlicher Prompt, „Noch kein Text“ (3) und „Text schreiben“ (3) bleiben. |
| `…::test_jeder_speichern_knopf_speichert_den_ganzen_kern`, `…::test_seite_warnt_vor_dem_verlassen_mit_ungespeicherten_aenderungen` | behalten | `submit_knoepfe` und das Opt-in-Attribut des gemeinsamen Skripts. | – |
| `…::test_text_mit_fehler_startet_offen` | behalten | `bearbeiten: true` ist Alpine-Startzustand, aber vom Server je Feld berechnet: nur das fehlerhafte Feld startet offen. Das ist View-Ausgabe, kein abgeschriebener Quelltext. | – |
| `SimulationskernSeitennavigationTests::test_markiert_die_autorinnen_ansicht_gelb` | umschreiben | Doppelung mit der Bereichszuordnung, dazu Klassenstrings. | `simulation:kern` mit `authoring` als Zeile in `BereichszuordnungTests`. Die Badge-Zusicherung entfällt. |
| `…::test_markiert_in_der_sidebar_nur_den_verwaltungslink`, `…::test_markiert_in_der_sidebar_nur_den_ansichtslink` | behalten | Eigenes Verhalten: Zwei Routen teilen den Namensraum, aber nicht den aktiven Link. Kein Test in `konten` prüft `aria-current`. | – |
| `SimulationsschichtImportgraphTests::test_kern_verwaltung_importiert_die_vignetten_schicht_nicht` | umschreiben | Startbefund bestätigt: Er dupliziert die Hilfsfunktionen aus `sitzungen/tests/test_importgraph.py` und prüft nur `views.py`. Ein Wächter über die ganze App schlüge heute fehl, weil `antwort_versuchen` `vignetten.models` importiert (#378). | In `sitzungen/tests/test_importgraph.py` aufnehmen: `_verstoesse(_quellen("simulation", mit_tests=False), "vignetten")` ist leer. Voraussetzung ist #378. Bis dahin bleibt der Test hier. **Umsetzung (#378):** Aufgegangen in `config/tests/test_importgraph.py::test_app_zeigt_nur_entlang_der_kantentabelle[simulation]`; `simulation` darf nur auf `konten` zeigen. |

### `simulation/tests/test_modell_konfiguration_view.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `ModellKonfigurationRollenTests` (6 Tests) | behalten | – | – |
| `ModellKonfigurationListeTests::test_traegt_die_system_farbflaeche` | umschreiben | Klassenstring; die Bereichszuordnung hat eine gemeinsame Tabelle. | `simulation:modell_konfiguration` mit `system` als Zeile in `BereichszuordnungTests`. |
| `…::test_listet_alle_je_angelegten_konfigurationen`, `…::test_zeigt_die_bezeichnung_jeder_konfiguration`, `…::test_nennt_den_anbieter_je_zeile`, `…::test_nennt_das_anlagedatum`, `…::test_zeigt_fuer_den_bestand_ohne_anlagedatum_einen_strich` | behalten | Ein Bestand ohne Anlagedatum existiert in echten Daten, auch wenn die Migration selbst nicht mehr getestet wird. | – |
| `…::test_nennt_die_kuerzel_der_verwendungen_je_zeile` | umschreiben | Implementation-coupled: liest `response.context["konfigurationen"]`, eine Liste der privaten Dataclass `_Konfigurationszeile`. | Über den gerenderten Inhalt: In der Zeile von `aeltere` stehen die Kürzel S und B, in der von `neuere` L. Prüfbar über die `abbr`-Elemente je Tabellenzeile. |
| `ModellKonfigurationDetailTests::test_zeigt_ohne_wahl_die_konfiguration_der_schuelerin`, `…::test_zeigt_die_gewaehlte_zeile`, `…::test_faellt_bei_unbekannter_wahl_auf_die_schuelerin_zurueck`, `…::test_zeigt_ohne_aktive_schuelerin_die_neueste`, `…::test_zeigt_einen_leerhinweis_ohne_konfiguration`, `ModellKonfigurationEditorTests::test_meldet_das_anlegen_auf_der_liste` | umschreiben | Implementation-coupled: `response.context["gewaehlt"]` ist die private Dataclass. | Das Detail über die Seite erkennen: Überschrift `Nr. <pk>` der erwarteten Zeile, wie `test_zeigt_die_gewaehlte_zeile` es schon zusätzlich tut. Beim Leerhinweis genügt der Satz. |
| `…::test_bietet_je_verwendung_einen_knopf`, `…::test_zeigt_eine_schon_aktive_verwendung_als_deaktivierten_knopf`, `…::test_zeigt_das_token_nur_maskiert`, `…::test_zeigt_einen_leerhinweis_ohne_token` | behalten | – | – |
| `…::test_bietet_weder_bearbeiten_noch_loeschen_an` | umschreiben | Abwesenheit zweier Wörter auf der ganzen Seite, Sidebar und Hilfetexte eingeschlossen. | `submit_knoepfe(response)`: Außer „Abmelden“ beginnen alle Absendeknöpfe mit „Für … aktivieren“. |
| `…::test_gibt_den_klartext_nicht_in_den_kontext` | streichen | Implementation-coupled: `str()` über Kontextobjekte. Was den Server verlässt, ist der Antwortkörper. | `…::test_zeigt_das_token_nur_maskiert` |
| `…::test_benennt_die_betriebsfolgen` | streichen | Tautologisch: Prosa aus dem statischen Template. | Keiner in diesem Bereich. Dass laufende Erhebungen ihre Konfiguration behalten, prüft `erhebungen/tests/test_models.py::test_finalisieren_pinnt_die_aktive_modell_konfiguration`. |
| `ModellKonfigurationAnlegenTests` (8 Tests) | behalten | Formfehler am Feld, Token kommt nie zurück. Nach dem Anlegen lässt sich das gespeicherte Token nur über das Modell prüfen. | – |
| `ModellKonfigurationEditorTests::test_die_liste_traegt_kein_anlegeformular_mehr` | umschreiben | Abwesenheit des früheren Formulars (totes Gewicht). | Nur den Link auf `modell_konfiguration_neu` und „Neue Konfiguration“ prüfen. |
| `…::test_das_detail_bietet_die_gewaehlte_als_vorlage_an`, `…::test_startet_ohne_vorlage_leer`, `…::test_fuellt_aus_der_vorlage_alles_ausser_dem_token_vor`, `…::test_das_token_der_vorlage_steht_nirgends_im_html`, `…::test_lehnt_eine_unbekannte_vorlage_ab`, `…::test_anlegen_aktiviert_nichts`, `…::test_markiert_den_sidebar_eintrag` | behalten | – | – |
| `…::test_stellt_die_bezeichnung_zuerst`, `ModellvorschlaegeSeitenTests::test_stellt_das_token_vor_das_sprachmodell`, `ModellKonfigurationFormularTests::test_nennt_jedes_feld_des_formulars`, `…::test_haelt_die_reihenfolge_des_formulars` | umschreiben | Vier Tests auf eine Zusage, die Eingabefolge. Zwei nehmen die Erwartung aus `ModellKonfigurationForm().fields`, sie bestehen also bei jeder Reihenfolge, die das Formular selbst hat. | Ein Test: Die Stellen von `name="…"` folgen dem Literal `["bezeichnung", "anbieter", "anbieter_token", "anbieter_basis_url", "sprachmodell", "parameter"]`. Der Helfer `_formularfelder` entfällt. |
| `…::test_anlegen_aus_der_vorlage_laesst_die_vorlage_unveraendert` | streichen | Belegt über `values()` aus der Datenbank. Eine Änderung der Vorlage ist am Modell ausgeschlossen: `save()` auf einer bestehenden Zeile wirft. | `test_models.py::test_modell_konfiguration_ist_nach_dem_anlegen_unveraenderlich`, `…::test_modell_konfiguration_kann_nicht_per_queryset_mutiert_werden` |
| `…::test_bietet_kein_gleich_aktivieren_an` | umschreiben | Abwesenheit eines Wortteils auf der ganzen Seite. | `submit_knoepfe(response)`: außer „Abmelden“ genau „Konfiguration anlegen“. |
| `ModellKonfigurationAktivierenTests::test_aktiviert_fuer_die_genannte_verwendung`, `…::test_lehnt_eine_unbekannte_verwendung_ab`, `…::test_lehnt_eine_unbekannte_konfiguration_ab`, `…::test_aktivieren_ist_der_post_route_vorbehalten` | behalten | Route → Manager, Umleitung, 404, 405. | – |
| `…::test_laesst_die_anderen_verwendungen_unberuehrt` | streichen | Doppelung: Die View reicht nur an `aktivieren` weiter. | `test_modell_konfiguration.py::test_umschalten_einer_verwendung_laesst_die_anderen_unberuehrt` |
| `…::test_dieselbe_konfiguration_fuer_mehrere_verwendungen` | streichen | Doppelung wie oben. | `test_modell_konfiguration.py::test_dieselbe_konfiguration_dient_mehreren_verwendungen` |
| `…::test_verschiebt_nur_den_zeiger_ohne_zeile_zu_mutieren` | streichen | Belegt über `values_list()` und die Zahl der Zeiger, also über die Datenbank. Mutation ist am Modell ausgeschlossen. | Die Append-only-Tests in `test_models.py`; dass ein Zeiger gesetzt wird, prüft `test_aktiviert_fuer_die_genannte_verwendung`. |
| `ModellKonfigurationNavigationTests::test_verlinkt_die_seite_in_der_gruppe_system` | umschreiben | `assertNotContains("… <small>geplant</small>")` prüft einen entfernten Platzhalter. | Nur den aktiven Link behalten. |
| `ModellKonfigurationFakeTests` | behalten | – | – |
| `ModellvorschlaegeEndpunktTests::test_weist_autorin_ohne_administrationsrolle_ab`, `…::test_ist_der_post_route_vorbehalten`, `…::test_meldet_den_anbieter_fake_ohne_netzaufruf`, `…::test_traegt_den_kontoklarnamen_der_produktabfrage_nicht` | behalten | Patchen an der echten Grenze (`httpx.Client`). | – |
| `…::test_liefert_die_vorschlaege_des_verzeichnisses`, `…::test_gibt_das_getippte_token_nicht_zurueck`, `…::test_meldet_einen_gescheiterten_abruf_verstaendlich`, `…::test_haelt_die_vorschlaege_wenn_allein_die_produktabfrage_scheitert` | umschreiben | Startbefund bestätigt: Sie patchen das eigene Modul `simulation.views.modellverzeichnis`, und der erste prüft dessen Aufrufe (`assert_called_once_with`). | `httpx.Client` patchen wie in `test_meldet_den_anbieter_fake_ohne_netzaufruf`. Die Antwortnutzlast als Literal (`{"data": [{"id": "anthropic/claude-opus-4.8", "name": "Anthropic: Claude Opus"}]}`), und die Seite zeigt Anzeige und Wert. Fehlerfall: `get.side_effect = httpx.ConnectError(...)`, die Seite meldet „OpenRouter ist nicht erreichbar.“. Produktabfrage: `get.side_effect` je URL; nur die Abfrage auf `https://api.infomaniak.com/1/ai` wirft. |
| `…::test_setzt_den_vorschlag_in_das_feld_des_formulars`, `…::test_setzt_den_vorschlag_der_transkription_in_ihr_eigenes_feld` | umschreiben | Patchen das eigene Modul und prüfen einen JS-Ausdruck wörtlich (`getElementById('…')`). | Mit `httpx.Client` an der Grenze. Die Antwort nennt `id_sprachmodell` und nicht `id_transkriptionsmodell`, an der anderen Naht umgekehrt. Das Zielfeld berechnet der Server je Naht; nur das ist Verhalten, nicht die JS-Formulierung. |
| `…::test_fuellt_bei_infomaniak_die_leere_basis_url_in_derselben_geste` | umschreiben | Eigenes Modul gepatcht, Aufrufe geprüft, JS wörtlich. | `httpx.Client` liefert je URL Modellliste und genau ein Produkt (`product_id: 314159`). Die Antwort enthält `https://api.infomaniak.com/2/ai/314159/openai/v1` und den Vorschlag. |
| `…::test_ueberschreibt_eine_getippte_basis_url_nicht` | umschreiben | Eigenes Modul gepatcht, `basis_url.assert_not_called()`. | `httpx.Client` an der Grenze: Bei getippter Basis-URL geht kein Aufruf an `https://api.infomaniak.com/1/ai`, und die Antwort enthält keine abgeleitete Wurzel. Der Aufruf-Payload ist hier die Schnittstelle. |
| `…::test_holt_infomaniaks_liste_allein_mit_dem_getippten_token` | umschreiben | Die erwartete URL ist die Modulkonstante `INFOMANIAK_MODELLE_URL`. Das Token prüft der Test trotz seines Namens nicht. | Literal `https://api.infomaniak.com/1/ai/models`, dazu `httpx.Client` mit `headers={"Authorization": "Bearer <getipptes Token>"}` gebildet. Die URL ist die Spec des Anbieters. |
| `…::test_fragt_bei_openrouter_kein_produkt_ab` | umschreiben | Erwartung aus `OPENROUTER_MODELLE_URL`. | Literal `https://openrouter.ai/api/v1/models`. |
| `ModellvorschlaegeSeitenTests::test_traegt_den_knopf_neben_dem_sprachmodell`, `…::test_schickt_die_getippte_basis_url_mit` | behalten | `hx-post` und `hx-include` sind deklarierte HTML-Attribute: Sie legen fest, was die Seite an den Endpunkt schickt. Sie sind kein JS-Ausdruck. | – |
| `…::test_verbirgt_den_knopf_beim_anbieter_fake` | streichen | Quelltext: der Alpine-Ausdruck `anbieter !== 'fake'` aus einem statischen Template. | Serverseitig: `ModellvorschlaegeEndpunktTests::test_meldet_den_anbieter_fake_ohne_netzaufruf`. Das Verbergen selbst beobachtet nur ein Browsertest. |
| `…::test_holt_beim_rendern_keine_modellliste` | umschreiben | Patcht das eigene Modul. | `httpx.Client` patchen; nach dem GET `assert_not_called()`. |
| `…::test_leert_die_liste_beim_anbieterwechsel` | streichen | Startbefund bestätigt: JS-Ausdruck wörtlich aus dem statischen Template. | Keiner; ohne Browsertest nicht beobachtbar. |

Alle Patches auf `simulation.views.modellverzeichnis` gehen an die Grenze `httpx.Client`. Die Datei tut das an vier Stellen schon. Danach prüft kein Test mehr Aufrufe des eigenen Verzeichnisses; Aufruf-Assertions bleiben nur auf `httpx.Client` und betreffen URL, Parameter und Kopfzeilen.

### `simulation/tests/test_modellverzeichnis.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_openrouter_fragt_die_oeffentliche_liste_nach_structured_output`, `test_openrouter_fragt_die_transkriptionsmodelle_ueber_die_modalitaet`, `test_infomaniak_fragt_die_kontoweite_liste_ohne_produktkennung`, `test_infomaniak_bildet_die_sprachmodell_wurzel_aus_der_produktkennung` | umschreiben | Die erwartete URL ist die Modulkonstante (`OPENROUTER_MODELLE_URL`, `INFOMANIAK_MODELLE_URL`, `INFOMANIAK_PRODUKT_URL`). Ein Tippfehler in der Konstante bliebe unbemerkt. | Literale aus der Anbieter-API: `https://openrouter.ai/api/v1/models`, `https://api.infomaniak.com/1/ai/models`, `https://api.infomaniak.com/1/ai`. Parameter und Wurzel sind schon Literale. |
| `test_openrouter_bildet_den_vorschlag_aus_id_und_klarnamen`, `…_zeigt_die_id_wenn_ein_klarname_fehlt`, `…_sortiert_alphabetisch_nach_der_anzeige`, `…_setzt_an_der_transkription_kein_praefix`, `…_meldet_einen_nicht_erreichbaren_anbieter`, `…_meldet_einen_ablehnenden_anbieter`, `…_meldet_eine_formwidrige_antwort`, `…_meldet_eine_naht_ohne_liste`, `test_openrouter_leitet_keine_wurzel_ab` | behalten | Der Client wird eingesetzt; die Nutzlast ist Eingabe, die Erwartung ein Literal. | – |
| `test_fabrik_bildet_das_openrouter_verzeichnis_ohne_token`, `test_fabrik_meldet_einen_anbieter_ohne_liste`, `test_fabrik_bildet_das_infomaniak_verzeichnis_mit_dem_getippten_token` | behalten | Die Kopfzeilen des echten `httpx.Client` sind der Payload an der Grenze. | – |
| `test_infomaniak_bildet_den_vorschlag_aus_dem_modellnamen`, `…_zeigt_nur_die_sprachmodelle`, `…_nimmt_noch_nicht_verfuegbare_modelle_auf`, `…_nimmt_beta_modelle_ungekennzeichnet_auf`, `…_sortiert_alphabetisch_nach_der_anzeige`, `…_zeigt_an_der_transkription_nur_das_stt_modell`, `…_meldet_ein_abgelehntes_token_verstaendlich`, `…_meldet_einen_nicht_erreichbaren_anbieter`, `…_meldet_eine_formwidrige_antwort`, `…_meldet_eine_naht_ohne_liste` | behalten | – | – |
| `test_infomaniak_traegt_die_numerische_kennung_in_keinem_feld` | streichen | Abwesenheitsprüfung, die schon aus einem Gleichheitsvergleich folgt. | `test_infomaniak_bildet_den_vorschlag_aus_dem_modellnamen`: Der Eintrag trägt `id: 4711`, und der Vorschlag ist gleich dem Literal ohne diese Zahl. |
| `test_infomaniak_bildet_die_transkriptions_wurzel_unter_eigener_gestalt`, `…_leitet_bei_mehreren_produkten_keine_wurzel_ab`, `…_leitet_ohne_produkt_keine_wurzel_ab`, `…_leitet_ohne_kennung_keine_wurzel_ab`, `…_meldet_eine_abgelehnte_produktabfrage`, `…_leitet_fuer_eine_naht_ohne_gestalt_nichts_ab` | behalten | – | – |
| `test_infomaniak_traegt_den_kontoklarnamen_nicht_in_die_wurzel` | streichen | Die Wurzel entsteht aus einem Format mit der Kennung; der Test besteht per Konstruktion. | `test_modell_konfiguration_view.py::ModellvorschlaegeEndpunktTests::test_traegt_den_kontoklarnamen_der_produktabfrage_nicht` prüft die Zusage dort, wo sie gilt: an der Oberfläche. |

### `simulation/tests/test_transkription.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_fake_transkription_liefert_das_naechste_skript_transkript`, `test_fake_transkription_spielt_jeden_fehlerzustand_ab` | behalten | Der Fake ist produktiver Adapter (Anbieter `fake`) und Testdoppel für die Endpunkte in `sitzungen` und `erhebungen`. | – |
| `test_openai_transkription_reicht_audio_an_konfiguriertes_modell_und_sprache`, `…_unterscheidet_anbieterfehler_und_nichterreichbarkeit`, `…_kennzeichnet_leere_antwort`, `…_kennzeichnet_ungueltige_antwort_als_anbieterfehler` | behalten | Mock des OpenAI-Clients; die Aufruf-Assertion betrifft nur den Payload (`model`, `language`, `file`). | – |
| `test_anbieterfunktion_bildet_fuer_fake_einen_platzhalter_ohne_netz` | umschreiben | Erwartung aus `PLATZHALTER_TRANSKRIPT`. | Literal „Dies ist ein Platzhalter-Transkript.“; `OpenAI` nicht aufgerufen bleibt. |
| `test_anbieterfunktion_haelt_keinen_adapter_ueber_anfragen_hinweg` | umschreiben | `zweiter is not erster` prüft Objektidentität, also das Wie. Erwartung aus `PLATZHALTER_TRANSKRIPT`. | Nur das Verhalten: Nach einer verbrauchten Transkription liefert ein zweiter Aufruf von `transkriptions_anbieter()` wieder das Literal. |
| `test_anbieterfunktion_bildet_fuer_openrouter_den_client_aus_der_konfiguration` | umschreiben | Erwartung `timeout=TRANSKRIPTION_BUDGET_SEKUNDEN` aus dem Modul. Liest die Attribute `client`, `modell` und `sprache` des Adapters statt seines Aufrufs. | `OpenAI` mit `base_url`, `api_key` und `timeout=120.0` (Literal, `docs/DEPLOYMENT.md`) gebildet. Danach `transkribieren(b"…")`: `audio.transcriptions.create` bekommt `model="whisper-large-v3"` und `language="fr"`. |
| `test_anbieterfunktion_gibt_openrouter_ohne_eigene_wurzel_die_vorgabe` | behalten | Literal; die Zusage aus ADR-0026 an der Grenze. | – |
| `test_infomaniak_transkription_holt_das_ergebnis_nach_dem_absenden` | behalten | Payload an `httpx` als Literal, einschließlich `response_format: "text"`. | – |
| `test_infomaniak_transkription_sendet_das_vereinbarte_antwortformat` | streichen | Startbefund bestätigt: Der Aufruf wird gegen die Konstante geprüft und dann die Konstante gegen `"text"`. | `test_infomaniak_transkription_holt_das_ergebnis_nach_dem_absenden` prüft `"response_format": "text"` als Literal im Payload. |
| `test_infomaniak_transkription_fragt_nach_einem_laufenden_stapel_erneut` | umschreiben | Erwartung `2 * INFOMANIAK_INTERVALL_SEKUNDEN`. | `uhr.jetzt == 4.0` (zwei Pausen zu 2 s). |
| `test_infomaniak_transkription_endet_nach_dem_budget_statt_endlos_zu_fragen` | umschreiben | Startbefund bestätigt: Die Zahl der Abfragen wird wie im Code berechnet (`Budget / Intervall + 1`). | Durchgerechnetes Beispiel als Literal: 61 Abfragen (sofort, dann alle 2 s bis 120 s), `uhr.jetzt == 120.0`. |
| `test_infomaniak_transkription_begrenzt_jede_anfrage_auf_die_restzeit` | umschreiben | Erwartungen aus `TRANSKRIPTION_BUDGET_SEKUNDEN` und `MINDEST_ANFRAGEFRIST_SEKUNDEN`. | Literale `120.0` (Absenden, erste Abfrage) und `1.0` (letzte Abfrage); die fallende Folge bleibt. |
| `…_reicht_einen_gemeldeten_fehlschlag_weiter`, `…_kennzeichnet_ein_leeres_ergebnis`, `…_meldet_ein_unlesbares_ergebnis`, `…_wartet_bei_einem_unlesbaren_stand_weiter`, `…_meldet_eine_unbekannte_stapelkennung`, `…_meldet_eine_unerreichbare_route`, `…_meldet_eine_antwort_ohne_kennung` | behalten | Nutzlasten wie am echten Konto beobachtet (#232). `time.sleep` und `time.monotonic` bleiben ersetzt, siehe Einleitung. | – |
| `test_anbieterfunktion_bildet_fuer_infomaniak_den_asynchronen_adapter` | umschreiben | Erwartung `timeout=TRANSKRIPTION_BUDGET_SEKUNDEN`; liest Adapterattribute. | `httpx.Client` mit Bearer-Kopf und `timeout=120.0` gebildet. Dann `transkribieren` mit gemocktem Client: Der POST geht an `https://api.infomaniak.com/1/ai/4711/openai/audio/transcriptions` mit `model="whisper"` und `language="fr"`. |

### `simulation/tests/test_transkriptions_konfiguration.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_fake_braucht_weder_modell_noch_zugangsdaten`, `test_openrouter_verlangt_modell_und_token`, `test_infomaniak_verlangt_zusaetzlich_die_endpunktwurzel` | behalten | `full_clean()` mit genauer Fehlerfeldmenge. | – |
| `test_maskierung_zeigt_die_letzten_vier_zeichen`, `test_maskierung_eines_sehr_kurzen_tokens_zeigt_nur_punkte`, `test_maskierung_ohne_token_bleibt_leer` | streichen | Doppelung: Die Maske ist eine Eigenschaft der gemeinsamen Basis `AnbieterFeldgruppe`. Die Tests der Modell-Konfiguration prüfen sie mit genaueren Literalen. | `test_modell_konfiguration.py::test_maskiert_das_token_bis_auf_die_letzten_vier_zeichen`, `…::test_maskiert_kurze_token_vollstaendig`, `…::test_maskiert_das_fehlende_token_als_leeren_wert`. Die Maske auf dieser Seite prüft `test_zeigt_das_hinterlegte_token_maskiert`. |
| `TranskriptionsKonfigurationRollenTests` (3 Tests) | behalten | – | – |
| `TranskriptionsKonfigurationSeiteTests::test_zeigt_alle_fuenf_felder`, `TranskriptionsKonfigurationVorschlaegeTests::test_stellt_das_token_vor_das_transkriptionsmodell` | umschreiben | Zwei Tests auf eine Zusage, die Eingabefolge. | Ein Test: Die Stellen von `name="…"` folgen dem Literal `["anbieter", "anbieter_token", "anbieter_basis_url", "transkriptionsmodell", "sprache"]`. |
| `…::test_zeigt_die_sprache_mit_der_vorgabe_deutsch` | streichen | `value="de"` kann überall stehen; die Vorgabe ist eine Modelleigenschaft, die das ModelForm nur rendert. | `test_models.py::test_transkriptions_konfiguration_beginnt_bei_fake_auf_deutsch` |
| `…::test_speichert_die_eingetragene_konfiguration`, `…::test_zweimaliges_speichern_erzeugt_keine_zweite_konfiguration`, `…::test_meldet_die_verletzte_anbieterbindung_am_feld`, `…::test_gibt_das_token_nach_dem_speichern_nicht_zurueck`, `…::test_zeigt_das_hinterlegte_token_maskiert`, `…::test_behaelt_das_token_wenn_das_feld_leer_bleibt` | behalten | – | – |
| `…::test_bietet_weder_anlegen_noch_aktivieren_noch_eine_liste_an` | umschreiben | Abwesenheit von vier Wörtern auf der ganzen Seite. | `submit_knoepfe(response)`: außer „Abmelden“ genau „Änderungen speichern“. |
| `…::test_benennt_die_zero_retention_zusicherung_als_instanz_einstellung` | streichen | Tautologisch: Prosa aus dem statischen Template. | Das Tor selbst prüft `sitzungen/tests/test_transkription.py::…::test_zero_retention_bleibt_auch_im_probelauf_das_tor`. |
| `…::test_liegt_blau_unter_system` | umschreiben | Klassenstring; dazu der Pfad `/system/transkription/`, den niemand zusagt. | `simulation:transkriptions_konfiguration` mit `system` als Zeile in `BereichszuordnungTests`. Die Pfad-Zusicherung entfällt. |
| `…::test_traegt_einen_eigenen_sidebar_eintrag` | behalten | – | – |
| `TranskriptionsKonfigurationVorschlaegeTests::test_traegt_den_knopf_neben_dem_transkriptionsmodell` | behalten | `hx-post` und `hx-vals` (Naht) sind die deklarierte Anfrage. | – |
| `…::test_verbirgt_den_knopf_beim_anbieter_fake` | streichen | Alpine-Ausdruck aus statischem Template. | wie bei der Modell-Konfiguration |
| `…::test_holt_beim_rendern_keine_modellliste` | umschreiben | Patcht das eigene Modul. | `httpx.Client` patchen, `assert_not_called()`. |
| `…::test_leert_die_liste_beim_anbieterwechsel` | streichen | JS-Ausdruck aus statischem Template. | Keiner. |
| `TranskriptionsKonfigurationWirkungTests::test_wirkt_bei_der_naechsten_anfrage` | umschreiben | Verbindet Seite und Fabrik: gespeichert über HTTP, wirksam beim nächsten `transkriptions_anbieter()`. Keine andere Datei geht diesen Weg. Liest aber das Adapterattribut `modell` statt des Aufrufs, wie die Fabrik-Tests oben. | Gleicher Weg; nach dem POST `transkriptions_anbieter().transkribieren(b"audio")` mit gemocktem `OpenAI`: `audio.transcriptions.create` bekommt `model="whisper-large-v3"`. |

### `simulation/tests/test_commands.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_kern_initialisieren_legt_eine_finale_platzhalter_fassung_an` | umschreiben | Wortlaut des Prompts („kannst ihn im Gespräch nicht herleiten“, „Arbeitsphase“). Dazu die Abwesenheit früherer Formate (`<fehlermuster_beschreibung>`, `<lernauftrag_text>`, `<arbeitsheft>`), also totes Gewicht. | Die eine Fassung ist final, und ihre fünf Felder, als Literal benannt, sind gleich ihrem Eintrag in `STANDARDKERN_VORLAGEN`, wie im umgeschriebenen View-Test `test_legt_einen_entwurf_aus_den_standardvorlagen_an`. Dass der Standardkern seine Verträge hält, belegt das erfolgreiche `finalisieren()` selbst. |
| `test_kern_initialisieren_ist_idempotent` | behalten | – | – |

### Nachtrag Evalkatalog (#395)

Für beide Dateien gilt eine Lesart. Der Editor zeigt einen Entwurf nur als Werte von Formularfeldern. Liest ein View-Test nach einer Geste Texte und Reihenfolge der Teile über die Relationen (`katalog.evals`, `eval.kriterien` …) oder `refresh_from_db()`, ist das die öffentliche Modell-API. Auch der Evallauf aus #299 liest sie so. Das zählt nicht als „DB-Abfrage statt Schnittstelle“ (wie in `vignetten.md`). Umgeschrieben wird nur, wenn die Prüfung Modellverhalten wiederholt (Schichtdoppelung) oder wenn eine Seite den Zustand als Text zeigt. Das tun die Übersicht (finale und überholte Fassungen, Anlegen) und der Baum (Namen, Kürzel).

`simulation/tests/evalkatalog_bau.py` ist kein Test. Der Helfer baut finalisierbare Kataloge nur über die öffentliche API und bleibt in der App, weil keine zweite App ihn braucht (#392 nimmt nur Helfer aus mindestens zwei Apps auf). Keine der beiden Dateien steht auf der SLF001-Übergangsliste. Umgesetzt (#403): Die View-Tests melden ihre Konten über `config.tests.aufbau.konto_mit_rollen` an statt über eine eigene Kopie.

### `simulation/tests/test_evalkatalog.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_vertrag_eval_erweitert_den_promptvertrag_um_die_drei_evalwerte` | streichen | Tautologisch: Die Erwartung ist die Definition von `VERTRAG_EVAL`, abgeschrieben aus dem Modul. Dazu hat die Konstante noch keinen Aufrufer (siehe Schnittstelle). | Keiner nötig. Die Zusage entsteht mit dem Evallauf (#299); dessen Tests prüfen sie über das Rendern der Vorlagen. |
| `test_jede_vorlage_erlaubt_nur_ihren_eigenen_evalwert` | streichen | Tautologisch: vergleicht zwei Modulkonstanten mit ihrer abgeschriebenen Definition. | Das Verhalten beim Finalisieren: `test_vorlage_ausserhalb_ihres_vertrags_wird_nicht_final` (der fremde Evalwert wird abgelehnt) und `test_promptvertrag_und_verlauf_sind_in_beiden_vorlagen_erlaubt` (gemeinsame Werte gehen durch, umgeschrieben). |
| `test_anlegen_legt_einen_leeren_entwurf_mit_k_drei_an`, `test_anlegen_lehnt_einen_zweiten_entwurf_ab`, `test_anlegen_ist_nach_dem_verwerfen_wieder_moeglich`, `test_direktes_anlegen_wird_abgelehnt` | behalten | Anlege-Naht und gesperrte Schreibroute über die öffentliche API, Literale. | – |
| `test_entwurf_uebernimmt_gespeicherte_werte` | streichen | Schichtdoppelung: prüft nur das `save()` eines Entwurfs. Sein einziger Produktionsaufrufer ist das Formular des Editors, und der View-Test geht genau diesen Weg. | `test_evalkatalog_view.py::EvalkatalogEditorTests::test_speichern_uebernimmt_die_werte` |
| `test_linie_hat_hoechstens_einen_entwurf` | behalten | Constraint-Test über eine interne Naht (`models.QuerySet(...).bulk_create`), von #321 ausdrücklich erlaubt. | – |
| `test_kriterien_stehen_in_der_reihenfolge_des_anlegens`, `test_verschieben_tauscht_mit_der_nachbarin_und_bleibt_gespeichert`, `test_evals_stehen_in_der_reihenfolge_des_anlegens_und_lassen_sich_umordnen`, `test_evalkriterien_haengen_am_eval_und_lassen_sich_umordnen`, `test_inputschritte_lassen_sich_umordnen_und_tragen_ihre_art` | behalten | Anlegen und `verschieben` über die Instanzmethoden; Reihenfolge und Kürzel („FFGF“) als Literal. | – |
| `test_neuer_evalinput_startet_mit_drei_leeren_festen_inputschritten`, `test_geloeschtes_eval_nimmt_seine_kriterien_mit`, `test_geloeschtes_eval_nimmt_seine_evalinputs_mit` | behalten | Zusagen der Manager- und Instanzmethoden. Sie sind zugleich Ersatz für Zusicherungen, die in den View-Tests unten entfallen. | – |
| `test_kriterien_einer_finalen_fassung_sind_unveraenderlich`, `test_kriterien_einer_finalen_fassung_widerstehen_massenaenderungen`, `test_evals_und_evalkriterien_einer_finalen_fassung_sind_unveraenderlich`, `test_evalinputs_und_inputschritte_einer_finalen_fassung_sind_unveraenderlich` | behalten | Schreibsperre der Teile über `save`, `delete`, Anlegen, `verschieben` und die gesperrten Queryset-Routen; Fehlerart nach Regel A/B. | – |
| `test_kriterium_wechselt_nicht_aus_einer_finalen_fassung_in_einen_entwurf`, `test_evalkriterium_wechselt_nicht_aus_einer_finalen_fassung_in_einen_entwurf`, `test_inputschritt_wechselt_nicht_aus_einer_finalen_fassung_in_einen_entwurf` | behalten | Umhängen über die öffentliche Instanz-API; je Ebene ein eigener Weg zur Fassung. | – |
| `test_neuer_entwurf_uebernimmt_die_kriterien_ohne_die_vorgaengerin_zu_beruehren`, `test_neuer_entwurf_uebernimmt_evals_und_evalkriterien`, `test_neuer_entwurf_uebernimmt_evalinputs_samt_inputschritten` | behalten | Tiefenkopie je Teilart, Literale. `FUELLTEXT` stammt aus dem Bauhelfer, nicht aus dem geprüften Modul. Ersatz für zwei View-Tests unten. | – |
| `test_vollstaendiger_entwurf_wird_final_und_ueberholt_die_vorgaengerin`, `test_finalisieren_in_zweitem_tab_lehnt_den_uebergang_ab`, `test_finalisieren_schreibt_den_geprueften_inhalt_mit`, `test_finale_fassung_fehlt_ohne_finalisierten_katalog` | behalten | Lebenszyklus und die Abfrage für andere Apps. Zustände als Choice-Mitglieder (CODING_STANDARDS). | – |
| `test_uebergreifende_kriterien_duerfen_fehlen` | behalten | Benennt die Regel ausdrücklich. Der Test oben deckt sie nur nebenbei, weil der Bauhelfer keine übergreifenden Kriterien anlegt. | – |
| `test_unvollstaendiger_entwurf_wird_nicht_final` (10 Fälle), `test_vorlage_ausserhalb_ihres_vertrags_wird_nicht_final` (4 Fälle), `test_meldung_nennt_ein_namenloses_eval_unbenannt`, `test_meldungen_nennen_alle_luecken_auf_einmal` | behalten | Je Strukturregel eine Lücke; die Meldungen sind Literale. | – |
| `test_promptvertrag_und_verlauf_sind_in_beiden_vorlagen_erlaubt` | umschreiben | Erwartung aus der Modulkonstante: Der Test baut die Vorlagen aus `VERTRAG_PROMPT`. Fehlte ein Name im Promptvertrag, bestünde er weiter. | Die zehn Namen der Prompt-Spalte aus ADR-0010 als Literal (`fehlermuster_beschreibung`, `lernauftrag`, `arbeitsheft`, `lernauftrag_simulationshinweise`, `arbeitsheft_simulationshinweise`, `schuelerin_name`, `schuelerin_geschlecht`, `fach`, `thema`, `klassenstufe`), dazu `$verlauf`. Beide Vorlagen mit allen elf und ihrem eigenen Evalwert lassen sich finalisieren. |

### `simulation/tests/test_evalkatalog_view.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `EvalkatalogUebersichtTests::test_ohne_katalog_bietet_die_seite_das_anlegen_an`, `…::test_anlegen_oeffnet_den_editor_des_neuen_entwurfs`, `…::test_mit_entwurf_fuehrt_die_seite_zum_editor_statt_anzulegen` | behalten | HTTP, Knöpfe über `submit_knoepfe`. | – |
| `…::test_zweites_anlegen_wird_mit_meldung_abgelehnt` | umschreiben | Die Zählung `Evalkatalog.objects.count() == 1` wiederholt `test_evalkatalog.py::test_anlegen_lehnt_einen_zweiten_entwurf_ab`. | Ohne Zählung. Die Meldung bleibt; dazu bietet die Übersicht weiter „Entwurf verwerfen“ an. |
| `…::test_verwerfen_nimmt_die_kriterien_des_entwurfs_mit`, `…::test_verwerfen_nimmt_die_evals_samt_evalkriterien_mit` | streichen | Sie belegen über `objects.exists()` statt über die Seite. Die Kaskade ist Modellverhalten. Eigenes Verhalten der View ist nur, dass das Verwerfen eines Entwurfs mit Teilen gelingt. | Der umgeschriebene `…::test_verwerfen_loescht_den_entwurf`. |
| `…::test_verwerfen_loescht_den_entwurf` | umschreiben | Belegt die leere Linie zusätzlich über `objects.exists()`. Die Übersicht zeigt das selbst: „Evalkatalog anlegen“ erscheint nur ohne Katalog. | Setup: ein Entwurf mit übergreifendem Kriterium und einem Eval samt Evalkriterium und Evalinput (Ersatz für die beiden gestrichenen Tests). POST mit `follow=True`; die Übersicht bietet „Evalkatalog anlegen“ an. Die Zusicherung über `exists()` entfällt. |
| `EvalkatalogEditorTests::test_zeigt_den_baum_mit_dem_knoten_durchlauf_und_vorlagen` | umschreiben | Klassenstring `class="evalkatalog-baum"`. „Durchlauf und Vorlagen“ steht als Text an mehreren Stellen. | Der Baum verlinkt den Knoten: `<a href="<Editor-URL>" aria-current="page">Durchlauf und Vorlagen</a>` (`html=True`). |
| `…::test_zeigt_k_und_beide_vorlagen`, `…::test_speichern_uebernimmt_die_werte`, `…::test_ungueltige_eingabe_bleibt_im_editor_ohne_zu_speichern`, `…::test_verworfener_entwurf_hat_keinen_editor` | behalten | Formularfelder als Schnittstelle; `refresh_from_db()` nach Lesart oben. `test_speichern_uebernimmt_die_werte` ist Ersatz für den gestrichenen Modelltest. | – |
| `…::test_platzhalterknoepfe_heben_die_vorlageneigenen_hervor`, `…::test_der_vorlageneigene_platzhalter_steht_vorn` | umschreiben | Zwei Tests auf eine Zusage, die Knöpfe je Vorlage. Der erste iteriert über `VERTRAG_PROMPT` (Erwartung aus dem Modul) und prüft Klassenstrings sowie den Pfad `js/platzhalter.js`. Der zweite berechnet die erwartete Ordnung mit `sorted()` aus dem Ergebnis selbst. Die Hervorhebung ist Gestaltung. | Ein Test: Je `data-ziel` folgen die Namen aus `data-platzhalter` einem Literal. Lehrperson: `inputstrategie`, `arbeitsheft`, `arbeitsheft_simulationshinweise`, `fach`, `fehlermuster_beschreibung`, `klassenstufe`, `lernauftrag`, `lernauftrag_simulationshinweise`, `schuelerin_geschlecht`, `schuelerin_name`, `thema`, `verlauf`. Bewerter: dieselbe Liste mit `kriterium` vorn. Klassen und Skriptpfad entfallen. Umgesetzt als `…::test_platzhalterknoepfe_folgen_dem_vertrag_jeder_vorlage`; die Knöpfe liest ein `HTMLParser` statt eines Regex auf die Attributfolge. |
| `…::test_aktionszeile_steht_am_formularende_und_klebt` | umschreiben | Quelltext und Gestaltung: Stylesheet-Pfad, Klassenname `vignette-form-actions`, Position im Markup. Das Kleben selbst ist CSS. | Nur `("Änderungen speichern", "evalkatalog-formular")` in `submit_knoepfe(response)`. Der Rest entfällt (ohne Browsertest nicht beobachtbar). Umgesetzt als `…::test_speichern_schickt_das_editorformular`. |
| `EvalkatalogKriterienTests::test_baum_zeigt_den_knoten_mit_der_zahl_seiner_kriterien`, `…::test_hinzufuegen_haengt_ein_leeres_kriterium_an`, `…::test_speichern_uebernimmt_die_texte`, `…::test_loeschen_entfernt_das_kriterium`, `…::test_hoch_und_runter_ordnen_um`, `…::test_unbekannte_richtung_ist_nicht_erreichbar`, `…::test_kriterium_eines_anderen_katalogs_ist_nicht_erreichbar` | behalten | Route → Instanzmethode, Übernahme der getippten Werte, 404 für fremde Teile. Lesart oben. | – |
| `…::test_hoch_an_der_ersten_zeile_aendert_nichts` | behalten | Das Randverhalten prüft auch `test_verschieben_tauscht_mit_der_nachbarin_und_bleibt_gespeichert`. Eigenes Verhalten der View ist die Weiterleitung der Verschieberoute; kein anderer Kriterientest prüft sie. | – |
| `…::test_hoch_an_der_ersten_runter_an_der_letzten_zeile_deaktiviert` | behalten | `disabled` berechnet der Server je Zeile; das ist View-Ausgabe, kein Quelltext. | – |
| `…::test_knoten_zeigt_den_hinweis_zur_kern_neutralitaet` | umschreiben | Tautologisch: „kern-neutral“ ist Prosa aus dem statischen Template. | Nur die Geste prüfen: `("Kriterium hinzufügen", "evalkatalog-formular")` in `submit_knoepfe(response)`; Name etwa `test_knoten_bietet_das_hinzufuegen_an`. |
| `EvalkatalogEvalTests::test_hinzufuegen_legt_ein_eval_an_und_oeffnet_seinen_knoten`, `…::test_hinzufuegen_uebernimmt_die_getippten_eingaben`, `…::test_ungueltiger_durchlauf_wird_bei_jeder_geste_gemeldet`, `…::test_speichern_benennt_das_eval_um_und_uebernimmt_die_kriterien`, `…::test_hoch_und_runter_ordnen_die_evals_um`, `…::test_evalkriterien_lassen_sich_anlegen_loeschen_und_umordnen`, `…::test_knoten_zeigt_die_evalkriterien_mit_gesten`, `…::test_eval_und_kriterium_eines_anderen_katalogs_sind_nicht_erreichbar`, `…::test_kriterium_eines_anderen_evals_ist_nicht_erreichbar`, `…::test_zu_langer_name_wird_nicht_gespeichert` | behalten | HTTP-Gesten, 404 für fremde Teile, Feldlänge 200 aus `docs/verhalten.md` als Literal. Lesart oben. | – |
| `…::test_baum_zeigt_jedes_eval_in_seiner_reihenfolge` | behalten | Der Klassenname dient nur als Anker, um den Baum vom Rest der Seite zu trennen; er wird nicht als Gestaltung geprüft. | – |
| `…::test_loeschen_nimmt_die_evalkriterien_mit` | umschreiben | `Evalkriterium.objects.exists()` wiederholt `test_evalkatalog.py::test_geloeschtes_eval_nimmt_seine_kriterien_mit`. | Ohne diese Zusicherung. Weiterleitung auf den Editor und `_namen() == ["Rolle"]` bleiben. Umgesetzt als `…::test_loeschen_fuehrt_zum_editor`, weil der alte Name nichts mehr belegt. |
| `EvalkatalogEvalinputTests::test_hinzufuegen_legt_einen_evalinput_mit_drei_schritten_an` | umschreiben | Die Prüfung der drei leeren, festen Schritte wiederholt `test_evalkatalog.py::test_neuer_evalinput_startet_mit_drei_leeren_festen_inputschritten`. | Knopf, Weiterleitung auf den Knoten des zweiten Evalinputs und Zahl 2 bleiben. Die Schrittprüfung entfällt; Name etwa `test_hinzufuegen_legt_einen_weiteren_evalinput_an_und_oeffnet_ihn`. |
| `…::test_loeschen_entfernt_den_evalinput_und_fuehrt_zum_eval` | umschreiben | Belegt die Kaskade auf die Schritte über `Inputschritt.objects.exists()`, eine Abfrage am Manager statt über die Relation (Lesart oben). Die Kaskade ist Modellverhalten wie beim Verwerfen, und kein Modelltest prüft sie für den Evalinput allein. | Ohne diese Zusicherung; Weiterleitung auf das Eval und `self.eval_.inputs.exists()` bleiben. Die Kaskade belegt ein neuer Modelltest `test_evalkatalog.py::test_geloeschter_evalinput_nimmt_seine_schritte_mit` nach dem Muster von `test_geloeschtes_eval_nimmt_seine_evalinputs_mit`. |
| `…::test_speichern_uebernimmt_texte_und_arten`, `…::test_unbekannte_art_bleibt_ungespeichert`, `…::test_schritte_lassen_sich_anlegen_loeschen_und_umordnen`, `…::test_hoch_am_ersten_runter_am_letzten_schritt_deaktiviert`, `…::test_knoten_zeigt_die_evalkriterien_seines_evals`, `…::test_fremde_evalinputs_und_schritte_sind_nicht_erreichbar` | behalten | HTTP-Gesten und Ausgabe des Knotens. | – |
| `…::test_eval_knoten_listet_seine_evalinputs_mit_kuerzeln`, `…::test_baum_zeigt_die_evalinputs_je_eval_mit_kuerzeln` | behalten | Kürzel als Literal („FFFG“). Die Klassennamen dienen nur als Anker. Auf dem Eval-Knoten zeigen Liste und Baum dieselben Links mit Kürzel, der Anker trennt sie. | – |
| `…::test_drehbuch_zeigt_schritte_antworten_und_gelenkte_blasen` | umschreiben | Zählt Klassenstrings (`<p class="drehbuch__antwort">`, `drehbuch__blase--gelenkt`). Die gestrichelte, kursive Blase ist Gestaltung. | „Schüler:in antwortet“ dreimal als Text (umgesetzt mit `html=True`: als Teilstring stünde er viermal da, weil der Hinweis am Knoten ihn in seiner Prosa enthält); die Beschriftungen „sagt wörtlich“ und „formuliert nach Strategie“; `value="gelenkt" checked` am zweiten Schritt; der Knopf „Inputschritt hinzufügen“. Die Klassenzähler entfallen. |
| `EvalkatalogFinaleFassungTests::test_finale_fassung_nimmt_keine_eingaben_an`, `…::test_kriterienrouten_erreichen_nur_entwuerfe`, `…::test_evalrouten_erreichen_nur_entwuerfe`, `…::test_evalrouten_erreichen_keine_ueberholte_fassung` | behalten | 404 je Route mit `subTest`, so nennt ein Fehlschlag die Route. Die überholte Fassung ist ein eigener Weg: Die Übersicht verlinkt sie. | – |
| `…::test_finale_fassung_laesst_sich_nicht_verwerfen` | umschreiben | Belegt das Ausbleiben des Löschens über `objects.filter(...).exists()` und prüft die Antwort der Route nicht. | POST ergibt 404. Danach zeigt die Übersicht weiter „Finale Fassung lesen“ mit dem Link auf diese Fassung. Links liest ein kleiner `HTMLParser` im Testmodul (`_links`). |
| `EvalkatalogLeseansichtTests::test_jeder_knoten_zeigt_seine_werte_mit_gesperrten_feldern` | behalten | `disabled` je Feld; `formaction`, `data-platzhalter` und `data-ungespeichert-warnen` sind deklarierte Attribute, die Gesten, Knöpfe und das gemeinsame Skript einschalten. Ihr Fehlen ist die Zusage „gesperrt“, keine Abwesenheit von Code. | – |
| `…::test_finale_fassung_traegt_ein_hinweisband` | umschreiben | Klassenstring `class="evalkatalog-band"`. | Nur die Texte „Diese Fassung ist final“ und „Finale Fassung lesen“. |
| `…::test_ueberholte_fassung_traegt_ein_hinweisband_ohne_neue_fassung`, `…::test_ueberholte_fassung_heisst_im_zustand_ueberholt` | behalten | Texte und Knöpfe. Das Badge belegt, dass der Zustand im Kopf „Überholt“ heißt und nicht „Archiviert“; das Band allein belegt das nicht. | – |
| `…::test_entwurf_bleibt_bearbeitbar` | umschreiben | Klassenstring `class="evalkatalog-band"` als Beleg, dass kein Band erscheint. | Statt des Klassennamens: Die Seite enthält „Diese Fassung ist“ nicht. Offene Felder und `formaction=` bleiben. |
| `…::test_baum_der_lese_ansicht_fuehrt_zu_den_knoten_der_fassung`, `…::test_uebersicht_verlinkt_die_finale_fassung`, `…::test_uebersicht_listet_die_ueberholten_fassungen_neueste_zuerst`, `…::test_ohne_ueberholte_fassung_fehlt_die_liste` | behalten | Links und Reihenfolge auf der Seite. Die fehlende Liste ist ein Seitenzustand, kein entferntes Feld. | – |
| `EvalkatalogNeueFassungTests::test_neue_fassung_oeffnet_den_editor_einer_tiefenkopie` | umschreiben | Der Baumvergleich wiederholt die drei Tiefenkopie-Tests des Modells. Er vergleicht zudem zwei Datenbankzustände miteinander statt mit einem Literal. Eigenes Verhalten der View ist die Weiterleitung. Kein Modelltest prüft, dass `k` und die Vorlagen mitkopiert werden. | Das Setup setzt vor dem Finalisieren `k = 5`, damit sich die Kopie vom Startwert unterscheidet. Weiterleitung auf den Editor des Entwurfs. Der Editor zeigt `name="k" value="5"` und die Lehrperson-Vorlage `Sprich mit $schuelerin_name nach $inputstrategie.`. `entwurf.vorgaengerin == self.katalog` bleibt (keine Seite zeigt sie). Der Baumvergleich und die Kriterienliste entfallen. |
| `…::test_aenderungen_am_entwurf_beruehren_die_vorgaengerin_nicht` | streichen | Schichtdoppelung: Die View trägt nichts bei; das Umbenennen über HTTP prüft schon der Eval-Test. | `test_evalkatalog.py::test_neuer_entwurf_uebernimmt_evals_und_evalkriterien` (Änderung am Entwurf, Vorgängerin unverändert); `EvalkatalogEvalTests::test_speichern_benennt_das_eval_um_und_uebernimmt_die_kriterien` |
| `…::test_bei_bestehendem_entwurf_wird_keine_neue_fassung_abgeleitet`, `…::test_bei_bestehendem_entwurf_bieten_die_seiten_keine_neue_fassung_an`, `…::test_uebersicht_bietet_die_neue_fassung_an`, `…::test_neue_fassung_entsteht_nur_aus_der_finalen` | behalten | Meldung statt 500, 404 außerhalb der finalen Fassung, Knöpfe über `submit_knoepfe`. Für den Evalkatalog prüft kein Modelltest den zweiten Entwurf aus `bearbeiten()`; der erste dieser Tests ist der Beleg. | – |
| `EvalkatalogFinalisierenTests::test_editor_bietet_das_finalisieren_im_formular_an`, `…::test_unvollstaendiger_entwurf_bleibt_mit_meldungen_im_editor`, `…::test_finalisieren_uebernimmt_zuerst_die_getippten_eingaben`, `…::test_unerlaubter_platzhalter_wird_abgelehnt`, `…::test_ungueltiges_k_wird_abgelehnt_statt_uebergangen`, `…::test_finale_fassung_wird_nicht_erneut_finalisiert`, `…::test_uebersicht_nennt_die_finale_fassung` | behalten | Eigenes Verhalten der View: getippte Werte vor dem Finalisieren, Meldungen im Editor, 404. Die Meldungstexte sind auch im Modell geprüft, hier aber auf der Seite. | – |
| `…::test_vollstaendiger_entwurf_wird_final_und_ueberholt_die_vorgaengerin` | umschreiben | `finale_fassung()` und `refresh_from_db()` wiederholen den gleichnamigen Modelltest. Die Übersicht, auf der der Test landet, zeigt beides selbst. | Weiterleitung und Meldung bleiben. Auf derselben Übersicht verlinkt „Finale Fassung lesen“ den Editor von `entwurf`, und unter „Überholte Fassungen“ steht der Link auf `self.katalog`. |
| `…::test_zwischenzeitlich_geaenderter_entwurf_wird_gemeldet` | streichen | Implementation-coupled: patcht die eigene Klasse (`mock.patch.object(VersionierteFassung, "finalisieren")`). Über HTTP ist der Fall nicht herbeizuführen: Die View läuft in `transaction.atomic`, unter `IMMEDIATE` also mit Schreibsperre ab dem Laden des Entwurfs. | Der `except`-Zweig der View ist derselbe wie für Lücken: `…::test_unvollstaendiger_entwurf_bleibt_mit_meldungen_im_editor`. Den abgelehnten Übergang selbst prüft `test_evalkatalog.py::test_finalisieren_in_zweitem_tab_lehnt_den_uebergang_ab`. |
| `…::test_uebersicht_ohne_finale_fassung_nennt_keine` | umschreiben | Abwesenheit zweier Wörter auf der ganzen Seite. | `submit_knoepfe(response)`: außer „Abmelden“ genau „Entwurf verwerfen“, also weder „Neue Fassung“ noch „Evalkatalog anlegen“. Dazu fehlt der Link „Finale Fassung lesen“. |
| `EvalkatalogZugriffTests::test_autorinnen_erhalten_auf_keiner_route_zugriff`, `…::test_aenderungsrouten_nehmen_nur_post_an` | behalten | 403 und 405 je Route mit `subTest`. | – |
| `…::test_sidebar_markiert_den_evalkatalog_auf_jedem_knoten` | behalten | `aria-current` auf den Knoten; kein Test in `konten` prüft das für den Evalkatalog. | – |
| `…::test_sidebar_fuehrt_administratorinnen_zum_evalkatalog` | streichen | Schwach: Auf der Übersicht selbst bestünde der Test mit jedem Link auf sie. Der Test darüber prüft den Sidebar-Link genauer. | `…::test_sidebar_markiert_den_evalkatalog_auf_jedem_knoten` |

## Startbefunde

| Startbefund | Ergebnis |
|---|---|
| View-Tests patchen `simulation.views.modellverzeichnis` | bestätigt; zehn Tests werden umgeschrieben, auf `httpx.Client`. |
| JS-Ausdruck beim Anbieterwechsel | bestätigt, an beiden Seiten; gestrichen, dazu `anbieter !== 'fake'`. |
| Transkription: Abfragezahl wie im Code, `INFOMANIAK_ANTWORTFORMAT == "text"` | bestätigt; Literal 61 bzw. Streichen. Weitere Erwartungen aus Modulkonstanten in derselben Datei und in `test_litellm_sprachmodell.py`. |
| Modelltest auf fehlendes Feld über `_meta` | bestätigt; gestrichen. |
| `inspect.signature` für den fehlenden Default | als Typ- oder Lint-Regel verworfen (`ty` und ruff können einen Default nicht verbieten); umgeschrieben auf `TypeError` beim Aufruf ohne Verwendung. |
| Migrationstests der Modell-Konfiguration | bestätigt; alle vier gestrichen (#325). Das spart die langsamen `MigrationExecutor`-Läufe mit `transaction=True`. |
| Importgraph-Wächter doppelt | bestätigt; mit #378 zu `config/tests/test_importgraph.py` zusammengelegt. |
| Mocks von litellm, OpenAI-SDK, httpx | bestätigt in Ordnung. Die Aufruf-Assertions betreffen nur den Payload nach außen. Ausnahme sind Objektattribute der Transkriptions-Adapter (`client`, `modell`, `sprache`) und die erwarteten URLs aus Modulkonstanten; beides wird umgeschrieben. |

## Folge-Issues

- #378 Zyklische Kante: `simulation.antwort_versuchen` importiert `vignetten.models` (ADR-0016). Aus #330 schon angelegt; Voraussetzung für einen Importgraph-Wächter über die ganze App.
- #379 `FakeSprachmodell.letzte_anfragen` wächst prozessweit und ist geteilter Testzustand: ein Testhaken im Produktionscode, den die Tests in drei Apps über Indizes lesen.
- #380 `simulation.render` ist neben `vorlage_rendern` überflüssig; sein Fehlerfall für überzählige Werte ist über den einzigen Aufrufer unerreichbar.
- #409 Evalkatalog-Knoten (Kriterien, Eval, Evalinput) rendern auch auf GET innerhalb von `transaction.atomic`, unter `IMMEDIATE` also unter der globalen Schreibsperre; dasselbe Muster wie #249. Aus dem Nachtrag #395.
