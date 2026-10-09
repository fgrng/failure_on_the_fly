# Testreview: Simulation

Bereich aus #329 (Spec #321). Geprüft sind alle zehn Dateien in `simulation/tests/`. Für Tests auf die Zeit und auf Migrationen gelten die Entscheidungen aus #324 und #325:

- Die vier Migrationstests in `test_modell_konfiguration.py` sind totes Gewicht (ADR-0031) und werden gestrichen.
- Kein Test hier patcht `timezone.now` oder eine andere Wanduhr. Zwei Dateien ersetzen `time.monotonic`, `test_transkription.py` zusätzlich `time.sleep`. Das sind Uhren an der Grenze zum Anbieter, die `time-machine` nicht steuert; #324 betrifft sie nicht.

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
- **Fake:** verbraucht je Aufruf einen Skripteintrag und spielt `fehler: formatbruch | anbieterfehler | content_filter` ab. Er zeichnet jeden Aufruf in der klassenweiten Liste `letzte_anfragen` auf; das ist ein Testhaken im Produktionscode (#379).

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
| `…::test_ueberschreibt_die_finale_fassung_ohne_verwendungs_markierung` | streichen | Totes Gewicht: Abwesenheit einer früheren Beschriftung. Die Überschrift steht schon in `setUp`. | `…::test_zeigt_die_finale_fassung` |
| `…::test_zeigt_die_finale_fassung`, `…::test_zeigt_die_archivierte_fassung`, `…::test_klappt_archivierte_fassungen_ein` | behalten | – | – |
| `…::test_zeigt_archivierte_fassungen_ohne_aktionsbereich` | umschreiben | Schneidet die Seite an `<details>` und sucht den Klassennamen `page-actions`. | Über die Routen: Die Seite nennt keine URL von `neue_fassung`, `finalisieren` oder `verwerfen` mit dem `pk` der archivierten Fassung. „Archivierter Prompt“ bleibt sichtbar. |
| `…::test_weist_autorin_ab`, `…::test_weist_konto_ohne_rolle_ab`, `…::test_weist_nicht_angemeldetes_konto_ab` | behalten | – | – |
| `SimulationskernLangeTexteTests::test_texte_erscheinen_gerendert_mit_bearbeiten_oder_text_schreiben` | umschreiben | Zählt den Klassenstring `page-field--wide markdown-lesefeld"`. | Den Klassenzähler streichen. Gerenderter Markdown, wörtlicher Prompt, „Noch kein Text“ (3) und „Text schreiben“ (3) bleiben. |
| `…::test_jeder_speichern_knopf_speichert_den_ganzen_kern`, `…::test_seite_warnt_vor_dem_verlassen_mit_ungespeicherten_aenderungen` | behalten | `submit_knoepfe` und das Opt-in-Attribut des gemeinsamen Skripts. | – |
| `…::test_text_mit_fehler_startet_offen` | behalten | `bearbeiten: true` ist Alpine-Startzustand, aber vom Server je Feld berechnet: nur das fehlerhafte Feld startet offen. Das ist View-Ausgabe, kein abgeschriebener Quelltext. | – |
| `SimulationskernSeitennavigationTests::test_markiert_die_autorinnen_ansicht_gelb` | umschreiben | Doppelung mit der Bereichszuordnung, dazu Klassenstrings. | `simulation:kern` mit `authoring` als Zeile in `BereichszuordnungTests`. Die Badge-Zusicherung entfällt. |
| `…::test_markiert_in_der_sidebar_nur_den_verwaltungslink`, `…::test_markiert_in_der_sidebar_nur_den_ansichtslink` | behalten | Eigenes Verhalten: Zwei Routen teilen den Namensraum, aber nicht den aktiven Link. Kein Test in `konten` prüft `aria-current`. | – |
| `SimulationsschichtImportgraphTests::test_kern_verwaltung_importiert_die_vignetten_schicht_nicht` | umschreiben | Startbefund bestätigt: Er dupliziert die Hilfsfunktionen aus `sitzungen/tests/test_importgraph.py` und prüft nur `views.py`. Ein Wächter über die ganze App schlüge heute fehl, weil `antwort_versuchen` `vignetten.models` importiert (#378). | In `sitzungen/tests/test_importgraph.py` aufnehmen: `_verstoesse(_quellen("simulation", mit_tests=False), "vignetten")` ist leer. Voraussetzung ist #378. Bis dahin bleibt der Test hier. |

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

## Startbefunde

| Startbefund | Ergebnis |
|---|---|
| View-Tests patchen `simulation.views.modellverzeichnis` | bestätigt; zehn Tests werden umgeschrieben, auf `httpx.Client`. |
| JS-Ausdruck beim Anbieterwechsel | bestätigt, an beiden Seiten; gestrichen, dazu `anbieter !== 'fake'`. |
| Transkription: Abfragezahl wie im Code, `INFOMANIAK_ANTWORTFORMAT == "text"` | bestätigt; Literal 61 bzw. Streichen. Weitere Erwartungen aus Modulkonstanten in derselben Datei und in `test_litellm_sprachmodell.py`. |
| Modelltest auf fehlendes Feld über `_meta` | bestätigt; gestrichen. |
| `inspect.signature` für den fehlenden Default | als Typ- oder Lint-Regel verworfen (`ty` und ruff können einen Default nicht verbieten); umgeschrieben auf `TypeError` beim Aufruf ohne Verwendung. |
| Migrationstests der Modell-Konfiguration | bestätigt; alle vier gestrichen (#325). Das spart die langsamen `MigrationExecutor`-Läufe mit `transaction=True`. |
| Importgraph-Wächter doppelt | bestätigt; Zusammenlegen setzt #378 voraus. |
| Mocks von litellm, OpenAI-SDK, httpx | bestätigt in Ordnung. Die Aufruf-Assertions betreffen nur den Payload nach außen. Ausnahme sind Objektattribute der Transkriptions-Adapter (`client`, `modell`, `sprache`) und die erwarteten URLs aus Modulkonstanten; beides wird umgeschrieben. |

## Folge-Issues

- #378 Zyklische Kante: `simulation.antwort_versuchen` importiert `vignetten.models` (ADR-0016). Aus #330 schon angelegt; Voraussetzung für einen Importgraph-Wächter über die ganze App.
- #379 `FakeSprachmodell.letzte_anfragen` wächst prozessweit und ist geteilter Testzustand: ein Testhaken im Produktionscode, den die Tests in drei Apps über Indizes lesen.
- #380 `simulation.render` ist neben `vorlage_rendern` überflüssig; sein Fehlerfall für überzählige Werte ist über den einzigen Aufrufer unerreichbar.
