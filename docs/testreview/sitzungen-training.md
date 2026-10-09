# Testreview: Sitzungen und Training

Bereich aus #330 (Spec #321). Geprüft sind alle Dateien in `sitzungen/tests/` und `training/tests/`. Die vier Dateien aus #355 (`test_beitritt.py`, `test_export.py`, `test_freigabe.py`, `test_fremdeinsicht.py`, zusammen 125 Tests) kamen erst danach; sie bewertet der Nachtrag aus #394 (Spec #391) nach denselben Kriterien. Seine Schnittstellen-Abschnitte stehen am Ende von „Schnittstelle“, seine Befunde am Ende von „Befunde“. Maßstab sind die Prüfkriterien aus #321 und der Abschnitt „What Tests Never Check“ in `CODING_STANDARDS.md`. Zwei Entscheidungen gelten für alle Einträge:

- **Zeit (#324):** Ein Test, der `sitzungen.durchlauf.jetzt` über den Modulpfad patcht, bekommt *umschreiben*. Zieltest ist derselbe Ablauf mit `time-machine` als Uhr. Umgesetzt wird das in #349.
- **Migrationen (#325, ADR-0031):** Kein Test dieses Bereichs migriert per `MigrationExecutor`. Ein Modelltest hält aber den Zustand nach `sitzungen.0007` fest; er steht unten unter `test_models.py`.

Eine Regel für Erwartungswerte gilt durchgehend: Ein Enum-Mitglied wie `Sitzung.Status.ABGESCHLOSSEN` als Erwartung ist in Ordnung. Es benennt einen Wert und berechnet ihn nicht. Tautologisch ist es, die Liste der Werte selbst abzuschreiben oder eine Meldungskonstante des geprüften Moduls als Erwartung zu nehmen.

## Schnittstelle

### Sitzungsmodelle (`sitzungen/models.py`)

- **Aufrufe:**
  - `Teilnahme` mit drei Einwilligungen (`None` heißt „nicht entschieden“). Dazu `hat_in_audioverarbeitung_eingewilligt`, `ist_fluechtig` und `Teilnahme.fluechtig_q(pfad)` für Abfragen über eine Beziehung.
  - `Sitzung` mit `Status` (laufend, abgeschlossen, abgebrochen, gescheitert), dem gepinnten Tripel und dem Budgetstand `verbrauchte_zeit`. Sie wird exportiert (ADR-0029). `offene_spanne_seit` ist interner Zustand der Uhr und wird nicht exportiert. `gespraechsschritte` liefert die Schritte in ihrer Reihenfolge.
  - `Eingabemodus.aus_formular(wert)`: Ein fehlender oder unbekannter Wert heißt „getippt“ und führt nie zu einer Ablehnung.
  - `Gespraechsschritt.objects.answerless_anlegen(...)` legt einen Abbruchschritt samt Fehlversuchen atomar an.
  - `Diagnose`, `Fehlversuch` und `Vignettenposition`.
- **Invarianten (DB):**
  - Denkspur und Äußerung sind beide gesetzt oder beide `NULL` (CheckConstraint).
  - `reihenfolge` ist je Sitzung eindeutig.
  - Ein antwortloser Schritt braucht mindestens einen Fehlversuch, beim Anlegen wie beim Löschen, und beendet die Sitzung. Das halten Trigger aus `sitzungen.0002` bis `0004` fest, nachgezogen in `0007` und `0009`.
  - Fehlversuche hängen mit `PROTECT` an ihrem Schritt.
  - Je Sitzung gibt es höchstens eine Diagnose.
  - Eine `Vignettenposition` gehört zur Teilnahme und Vignette ihrer Sitzung (`clean()` in `save()`). Ihre Position ist je Teilnahme eindeutig, die Positionen sind danach geordnet.
- **Fehlerfälle:** `IntegrityError` bei verletzten Constraints und Triggern, `ValidationError` bei einer inkonsistenten Vignettenposition.
- **Konfiguration:** keine.

### Bindungsexklusivität (`sitzungen/bindungen.py`)

- **Aufrufe:** Die abstrakte Basis `Bindung`. Unterklassen setzen `KONTO_TRAGEND` und tragen ein 1:1-Feld `teilnahme`: `Trainingsbindung` und `Abschrift` tragen ein Konto, `Erhebungsbindung` ein Token. Dazu der Manager `BindungQuerySet`.
- **Invariante (ADR-0018, ADR-0043):** Eine Teilnahme trägt nie zugleich eine konto-tragende und eine pseudonyme Bindung. Das gilt beim Anlegen, beim Ändern (Umhängen), bei `bulk_create` und bei `update()` einer Menge. Bindungen derselben Seite schließen sich nicht aus.
- **Fehlerfälle:** `ValidationError` bei `save()` und `bulk_create`. `RuntimeError` bei `update(teilnahme=…)` oder `update(teilnahme_id=…)`.

### Sink (`sitzungen/sink.py`)

- **Aufrufe:**
  - Das Protokoll `SitzungSink` mit `sitzung_starten`, `gespraechsschritte`, `gespraechsschritt_anhaengen(...) -> bool` (Budget erschöpft?), `gescheiterten_schritt_behandeln`, `diagnose_setzen`, `status_setzen`, `zug_beginnen(jetzt)` und `zug_beenden(jetzt)`.
  - Drei Adapter: `DBSink`, `FluechtigerSink` (Gerüst in der DB, Inhalte in der Session, ADR-0045) und `ScratchSink` (Probelauf, nur Session, ADR-0014).
  - Die Wahl der Senke: `sink_fuer_teilnahme` und `sink_fuer_sitzung`.
  - An `DBSink` und `FluechtigerSink` zusätzlich `fuer_sitzung(…)` zum Wiederherstellen einer bestehenden Sitzung sowie `verlauf_fehlt` und `abgegebene_diagnose`.
  - Am `ScratchSink` zusätzlich `ist_beendet`, `freie_auswahl`, `freie_auswahl_setzen()`, `vignette_pk`, `kern_pk`, `modell_konfiguration_pk` und `verwerfen()`.
  - `Budgetstand` als speicherloser Rechenkern.
  - `probelauf_laeuft(session)`.
- **Invarianten:**
  - Alle Senken liefern Gesprächsschritte in derselben Speicherform (`GespraechsschrittDaten` bzw. das gleichnamige Modell).
  - Die Uhr bucht nur offene Spannen zwischen `zug_beginnen` und `zug_beenden`. Ein erneutes `zug_beginnen` verwirft die offene Spanne. Bei einem Schrittbudget läuft keine Uhr.
  - Ein gescheiterter Schritt bleibt in DB und flüchtiger Senke stehen und setzt den Status `gescheitert`. Der Probelauf verwirft ihn und bleibt offen (ADR-0011).
  - Ein erschöpftes Budget schließt nur den Probelauf ab. Eine persistierte Sitzung bleibt `laufend` bis zur Diagnose.
  - Die Diagnose schließt in allen Senken ab.
  - Die flüchtige Senke schreibt keine Inhaltszeilen.
- **Fehlerfälle:** `RuntimeError`, wenn ein `GeruestSink` ohne gestartete Sitzung benutzt wird.
- **Konfiguration:** keine. Die Session-Schlüssel (`probelauf`, `fluechtige_sitzungen`, `verbrauchte_zeit`, `zeit_laeuft_seit`) sind privat. Kein Aufrufer außer dem Sink darf sie lesen.

### Durchlauf (`sitzungen/durchlauf.py`)

- **Aufrufe:**
  - `sitzung_starten(sink, vignette, modell_konfiguration, *, simulationskern=None)`
  - `gespraechsschritt_ausfuehren(...) -> Ausgang` mit den Ausgängen `FORTGESETZT`, `GESCHEITERT` und `BUDGET_ERSCHOEPFT`
  - `sitzung_beenden(sink)` und `sitzung_abbrechen(sink)`
  - `modellverlauf(sink)`
  - `rahmenhandlung_rendern(vorlage, vignette)`
  - `sitzung_anzeigen(request, …)` und die Datenklasse `Sitzungsnavigation`
  - `jetzt()` als Wanduhr
- **Invarianten:**
  - Vor dem Modellaufruf wird die Uhr angehalten (ADR-0012). Wieder angestoßen wird sie von der aufrufenden View, nicht vom Durchlauf.
  - Der Modellverlauf enthält nur Paare aus Eingabe und Äußerung. Die Denkspur und Schritte ohne Äußerung bleiben draußen (ADR-0005, ADR-0011). Eine leere Äußerung bleibt drin.
  - Die Rahmenhandlung ist Szenentext. Vignettenwerte werden wörtlich eingesetzt, Links des Kerns entstehen nicht.
  - Mit `HX-Request: true` rendert `sitzung_anzeigen` nur die Fortsetzung.
- **Fehlerfälle:** `RuntimeError` ohne gepinnten Kern.
- **Konfiguration:** `TRANSKRIPTION_MAX_AUFNAHME_BYTES` landet in der Seite.

### Probelauf und Sitzungsbausteine (`sitzungen/views.py`, `sitzungen/urls.py`)

- **Aufrufe (HTTP):**
  - `probelauf/`: Auswahl der eigenen Entwürfe.
  - `probelauf/<pk>/starten/` (nur POST): über jede eigene Fassung, mit der belegten Schülerinnen-Konfiguration.
  - `probelauf/administratorin/` und `…/starten/`: freies Tripel, nur für die Administration.
  - `probelauf/gespraech/` (GET/POST), `probelauf/beenden/` (POST) und `probelauf/debrief/` (POST). Der Debrief verwirft den Probelauf und führt zur Vignette zurück, beim freien Tripel zur Auswahl.
  - `transkription/`
- **Bausteine für `training` und `erhebungen`:**
  - `transkriptions_endpunkt(anbieter_bilden, sitzung_aufloesen)`
  - `persistiertes_gespraech(request, sitzung, navigation, sitzungsblock)`
  - `persistierten_debrief_anzeigen` und `persistierten_fehler_anzeigen`
  - `probelauf_sitzung_fuer_transkription`
- **Invarianten:**
  - Der Probelauf schreibt keine Domänenzeile (ADR-0014). Er lebt je Browser-Session, nicht je Konto.
  - Simulationshinweise erreichen den Prompt, nie die Seite.
  - Die Denkspur ist im Probelauf sichtbar (ADR-0005).
  - Ein endgültiger Fehlschlag zeigt eine Meldung ohne Grund. Er bietet „Erneut senden“ mit Eingabe und Eingabemodus an und lässt das Beenden zu.
  - Nach einem erschöpften Budget bleibt der Debrief stehen, auch bei weiteren Anfragen.
  - Der Transkriptions-Endpunkt nimmt nur POST an und prüft in dieser Reihenfolge: Autorisierung, Einwilligung, Zero-Retention, Größe, Anbieter. Er bildet den Anbieter je Anfrage neu und speichert keine Aufnahme.
- **Fehlerfälle:**
  - 403, wenn eine Nicht-Administratorin den freien Auswähler aufruft.
  - 404 für fremde Fassungen.
  - 405 bei falscher Methode.
  - Transkription: `PermissionDenied` ohne laufenden Probelauf. Dazu die Status 403 `einwilligung_verweigert`, 503 `zero_retention_fehlt`, 413 `aufnahme_zu_gross`, 422 `leeres_transkript`, 502 `anbieterfehler` und 503 `anbieter_nicht_erreichbar`.
- **Konfiguration:** `TRANSKRIPTION_ZERO_RETENTION`, `TRANSKRIPTION_MAX_AUFNAHME_BYTES`, die belegte `ModellKonfiguration` für `Verwendung.SCHUELERIN` und die Transkriptions-Konfiguration in der DB.

### Trainingsmodelle (`training/models.py`)

- **Aufrufe:**
  - `Training.objects` ist ein Eigentümer-Kreis (`anlegen` und `sichtbar_fuer` aus `konten.eigentuemerschaft`) und hat zusätzlich `veroeffentlicht()`.
  - `Training.veroeffentlichen()`
  - Das M2M-Feld `vignetten`
  - `Trainingsbindung` und `Abschrift`
- **Invarianten:**
  - Ein Training entsteht als Entwurf. Der Zustand wechselt nur über `veroeffentlichen()`, auch nicht über `update()`, und nur einmal.
  - Ein Training bindet nur finale Vignetten. Das gilt in beiden Richtungen und auch für eine direkte Zeile der Zwischentabelle (DB-Trigger).
  - Wird eine Vignette archiviert, verschwindet sie aus allen Trainings.
  - Die Vignettenmenge bleibt nach dem Veröffentlichen austauschbar.
  - Je Training und Konto gibt es höchstens eine Trainingsbindung, je Teilnahme höchstens eine Bindung.
  - Wird eine Abschrift gelöscht, nimmt sie ihre Teilnahme mit allem Kopierten mit, auch über die Kaskade einer Konto-Löschung (Signal).
- **Fehlerfälle:** `ValidationError` bei einem Zustandswechsel und bei einer nicht finalen Vignette. `RuntimeError` bei `update(zustand=…)`. `IntegrityError` bei doppelter Bindung.

### Abschriften (`training/abschriften.py`)

- **Aufrufe:** `abschrift_holen(konto, token) -> Abschrift`, `abschrift_loeschen(abschrift)`, `teilnahme_einer_abschrift_raeumen(teilnahme)` und die Meldung `ABLEHNUNG`.
- **Invarianten (ADR-0043, ADR-0049):**
  - Das Token wird normalisiert (Leerraum, Großschreibung).
  - Kopiert werden Sitzungen samt Schritten, Denkspur, Fehlversuchen, Diagnose, Eingabemodus, verbrauchter Zeit und Position, unter einer neuen Teilnahme. Die Zeitstempel sind Importzeit.
  - Item-Antworten werden nicht kopiert. Die Erhebungsseite bleibt unverändert.
  - Jeder Aufruf erzeugt eine eigene Abschrift.
  - Abgelehnt wird mit derselben Meldung, wenn das Token unbekannt ist, die Teilnahme nicht abgeschlossen oder flüchtig ist oder Stichprobe oder Erhebung archiviert sind.
  - Bei einer Ablehnung bleibt nichts zurück (`atomic`).
- **Fehlerfälle:** `ValidationError(ABLEHNUNG)`.

### Training-Views (`training/views.py`)

- **Katalog und Teilnahme:**
  - `katalog`: Veröffentlichte Trainings sieht jedes Konto. Ausbilder:innen sehen zusätzlich ihre sichtbaren Trainings mit „Kuratieren“.
  - `detail`: nur veröffentlichte Trainings, nur finale Vignetten, die eigenen Sitzungen nach Status.
  - `wahl` und `einwilligung`: Eine Trainingsbindung je Konto und Training. Die Einwilligung wird vor dem Start einmal festgehalten (400 bei ungültigem oder wiederholtem Wert).
  - `historie`: Fortschritt und Sitzungen nach Status je Trainingsbindung.
- **Trainingssitzung:**
  - `gespraech`, `gespraech_beenden`, `abbrechen`, `debrief`, `sitzung_ansehen` und `transkription`.
  - Die laufende Sitzung steht unter `training_sitzung_pk` in der Session und gehört dem Konto (`training_sitzung`).
  - Terminale Zustände bleiben terminal: Ein Debrief auf eine nicht laufende Sitzung führt zur Auswahl zurück.
  - Die Denkspur bleibt verborgen.
  - Ohne Einwilligung gibt es keine Spracheingabe.
- **Ausbilder-UI:**
  - `liste`, `anlegen`, `kuratieren`, `veroeffentlichen`, `vignette_hinzufuegen`, `vignette_entfernen`, `eigentuemerin_hinzufuegen` und `eigentuemerin_entfernen`.
  - Nur Ausbilder:innen und Administration (sonst 403).
  - Fremde Trainings ergeben 404. Nur eigene finale Vignetten lassen sich aufnehmen.
  - Nach dem Selbstaustritt geht es zur Liste.
- **Abschriften:**
  - `abschriften`: Token-Eingabe und Liste der eigenen Abschriften.
  - `abschrift_ansehen`: nur lesend, in gespielter Reihenfolge, ohne Denkspur.
  - `abschrift_entfernen`: nur POST.
  - Fremde Abschriften ergeben 404.

### Geschlossenes Training und Beitritt (`training/models.py`, `training/views.py`, Nachtrag #394)

- **Aufrufe:**
  - `Training.trainings_link` (UUID, je Training fest) und `Training.beitritt_gesperrt`.
  - `Training.beitreten(konto) -> bool` lädt oder legt die Trainingsbindung an und sagt, ob das Konto danach dabei ist.
  - `Training.bindung_fuer(konto)`: die eine Trainingsbindung je Konto, auch bei einem parallelen zweiten Aufruf.
  - `Training.objects.beigetreten_von(konto)` und `zugaenglich_fuer(konto)` (Trainingsbindung oder `sichtbar_fuer`).
  - HTTP: `beitreten/<trainings_link>/` (Login nötig) sowie `eigene/<pk>/beitritt/sperren/` und `…/oeffnen/` (nur POST, nur der Kreis).
- **Invarianten (ADR-0049):**
  - Teilnehmende erreichen Katalogeintrag, `detail`, `wahl` und `einwilligung` nur mit Trainingsbindung. Kreis und Administration erreichen ihre Trainings ohne Beitritt.
  - Der Beitritt ist wiederholbar und zählt jede Person einmal.
  - Ohne Login führt der Link über den Login zurück zum Beitritt.
  - Die Sperre hält nur Neue fern. Beigetretene, Kreis und Administration kommen weiter ins Training. Bei gesperrtem Link entsteht für Kreis und Administration keine Bindung; beim offenen Link entsteht eine (#410).
  - Der Link eines Entwurfs nimmt niemanden auf. Ein leeres Training lässt sich veröffentlichen und beitreten.
  - Die Trainingsseite trägt den festen Hinweis auf die Fremdeinsicht. Die Kuratierseite zeigt das Band mit dem absoluten Link, „Kopieren“, Sperren bzw. Öffnen und der Zahl der Beigetretenen in Einzahl oder Mehrzahl.
- **Fehlerfälle:** 403 mit Meldung bei gesperrtem Beitritt. 404 für den Link eines Entwurfs, für Trainings ohne eigene Bindung und für einen fremden Kreis beim Umschalten. 405 bei GET auf Sperren und Öffnen.
- **Konfiguration:** keine.

### Freigabe (`training/abschriften.py`, `training/views.py`, Nachtrag #394)

- **Aufrufe:**
  - `abschrift_freigeben(abschrift, trainings)` setzt die Freigaben genau auf die genannten Trainings. Was nicht genannt ist, ist widerrufen.
  - `Abschrift.freigegeben_fuer` bzw. rückwärts `Training.freigegebene_abschriften`.
  - HTTP: `abschriften/<pk>/freigaben/` (nur POST, Feld `training` mehrfach), danach zurück zur Abschriftseite. Die Abschriftseite zeigt die Checkbox-Liste der beigetretenen Trainings und im Kopf, für wen freigegeben ist.
- **Invarianten (ADR-0049):**
  - Freigeben lässt sich nur für beigetretene Trainings, für beliebig viele und unabhängig von ihren Vignetten.
  - Eine abgewiesene Auswahl ändert nichts.
  - Widerruf und Löschen der Abschrift beenden die Fremdeinsicht sofort.
  - Die Freigabe öffnet den Vignettenbestand nicht: Die Vignette der Abschrift bleibt für den Kreis außerhalb von Liste, Detail und Aufnahme (ADR-0015).
- **Fehlerfälle:** `ValidationError(FREIGABE_ABGEWIESEN)` am Kommando. Über HTTP 404 für ein Training ohne eigene Bindung, eine nicht lesbare Auswahl und eine fremde Abschrift, 405 bei GET.
- **Konfiguration:** keine.

### Fremdeinsicht und Selbsteinsicht (`sitzungen/models.py`, `training/views.py`, Nachtrag #394)

- **Aufrufe:**
  - `Sitzung.objects.fremd_einsehbar(trainings)`: abgeschlossene Sitzungen unter einer Trainingsbindung dieser Trainings oder unter einer für sie freigegebenen Abschrift. Wer die Trainings sieht, entscheidet der Aufrufer.
  - `Sitzung.objects.in_gespielter_folge()`
  - HTTP: `sitzung/<pk>/ansehen/` zeigt lesend die eigene Trainingssitzung in jedem Status (Selbsteinsicht). Eine fremde zeigt es nur über `fremd_einsehbar(Training.objects.sichtbar_fuer(konto))`.
  - Die Kuratierseite zeigt die Tabelle der Fremdeinsicht und die Liste „Freigegebene Abschriften“.
- **Invarianten (ADR-0049):**
  - Einsicht folgt dem Anlass, nie der Vignette: keine Sitzungen fremder Trainings, keine Einsicht für die Autorin.
  - Einsicht folgt der aktuellen Kreismitgliedschaft, auch rückwirkend; nach dem Austritt gibt es keine mehr. Die Administration folgt aus `sichtbar_fuer`.
  - Fremd sind nur abgeschlossene Sitzungen einsehbar, selbst jeder Status. Beide Ansichten zeigen keine Denkspur und keine Bedienelemente.
  - Ihre Abschriften liest die Teilnehmerin nur auf der Abschriftseite, nicht über `sitzung_ansehen`.
  - Tabelle: Zeilen sind alle Beigetretenen nach Namen, ohne Rücksicht auf Groß- und Kleinschreibung und auch ohne Sitzung. Spalten sind die Vignetten in Kuratierreihenfolge. Jede Zelle hält die abgeschlossenen Sitzungen, je Vignette ab 1 nummeriert und datiert. Ohne Beigetretene steht eine Leerzeile da, ohne Vignetten ein Hinweis statt der Tabelle.
  - Liste der freigegebenen Abschriften: nach Namen, mit Erhebungsname, Importzeitpunkt und den verlinkten abgeschlossenen Sitzungen. Ist sie leer, steht dort eine Meldung.
- **Fehlerfälle:** 404 für jede nicht einsehbare Sitzung.
- **Konfiguration:** `TIME_ZONE` für die angezeigten Daten.

### Trainingsexport (`training/export.py`, `config/downloads.py`, Nachtrag #394)

- **Aufrufe:**
  - `trainingsexport_zip(training) -> bytes` liefert dieselben Sitzungen wie `fremd_einsehbar` für genau dieses Training.
  - `zip_download(art, pk, name, inhalt)` antwortet mit `application/zip` und dem Dateinamen `<art>-<pk>-<slug>-<UTC %Y%m%dT%H%M%SZ>.zip`. Der Erhebungsexport teilt sich die Funktion.
  - HTTP: `eigene/<pk>/export/` für Kreis und Administration. Der Knopf steht in der Werkzeugleiste der Fremdeinsicht.
- **Invarianten (ADR-0049):**
  - Je Person gibt es einen Ordner `teilnehmer-<hex>`, das Kennzeichen wird je Export neu gezogen. Darin liegt `NN-<slug der Vignette>.md` je abgeschlossener Sitzung, gezählt je Ordner.
  - Freigegebene Abschriften liegen als Unterordner `<slug des Erhebungsnamens>` im Ordner der Person. Gleiche Namen bekommen `-2`, `-3`; nur Abschriften mit einsehbaren Sitzungen belegen einen Namen. Ein Erhebungsname wird nie zum Pfad.
  - Eine Datei nennt Vignette, Ausgang und Datum; das Datum fehlt bei Bestandssitzungen ohne Zeitstempel. Es folgen das Transkript als Wechsel von Eingabe und Äußerung („(keine Antwort)“ beim antwortlosen Schritt) und die Diagnose („(keine Diagnose)“).
  - Keine Kontodaten, keine Denkspur, keine Fehlversuche. Kein Exportkontrakt nach ADR-0029.
- **Fehlerfälle:** 403 ohne Ausbilder:innen-Rolle. 404 für fremde Kreise, Ausgetretene und die Autorin.
- **Konfiguration:** keine. Zeitstempel und Kennzeichen kommen aus Systemzeit und Zufall, beides Systemgrenzen.

### Formulare und Routen des Trainings (`training/forms.py`, `training/urls.py`, Nachtrag #394)

- **Aufrufe:**
  - `TrainingForm` erfasst nur `name`. `anlegen` übergibt ihn an `Training.objects.anlegen`.
  - Die Routen im Namensraum `training`:
    - Teilnahme: `katalog`, `historie`, `detail`, `beitreten`, `wahl`, `einwilligung`, die Sitzungsrouten und `transkription`.
    - Abschriften: `abschriften`, `abschrift`, `abschrift_freigaben` und `abschrift_loeschen`.
    - Ausbilder-UI: `liste`, `anlegen`, `kuratieren`, `veroeffentlichen`, `trainingsexport`, `beitritt_sperren`, `beitritt_oeffnen`, `eigentuemerin_hinzufuegen`, `eigentuemerin_entfernen`, `vignette_hinzufuegen` und `vignette_entfernen`.
  - `transkription` ist der Baustein `transkriptions_endpunkt` mit `training_sitzung` als Auflöser.
- **Invarianten:** Schreibende Routen nehmen nur POST an: `veroeffentlichen`, `beitritt_*`, `vignette_*`, `eigentuemerin_*`, `abschrift_freigaben`, `abschrift_loeschen`, `einwilligung` und die Sitzungsaktionen außer `gespraech`. Die Routen des Eigentümer-Kreises folgen dem gemeinsamen Segment `eigentuemerinnen/` (`config/tests/test_eigentuemer_kreis_routen.py`).
- **Fehlerfälle:** 405 bei falscher Methode. Ein leerer Name zeigt das Formular erneut.
- **Konfiguration:** keine.

## Befunde

### `sitzungen/tests/test_models.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| Hilfsfunktionen `_sitzung_anlegen`, `_sitzungen_anlegen` | behalten | Öffentliche Wege (`anlegen`, `finalisieren`). | – |
| `test_teilnahme_beginnt_ohne_einwilligung_zur_audioverarbeitung` | streichen | Tautologisch: Der Test prüft den Feld-Default `None` an einer ungespeicherten Instanz. Das ist die Felddefinition. | `training/tests/test_katalog.py::…::test_einwilligung_wird_an_der_teilnahme_gespeichert_bevor_die_sitzung_startet`: Eine frische Teilnahme fragt die Einwilligung ab, nach ungültiger Eingabe ist sie weiter `None`. |
| `test_teilnahme_ohne_einwilligung_erlaubt_keine_audioverarbeitung` | streichen | Prüft eine Eigenschaft (`is True`) über einen DB-Rundweg, der nichts beiträgt. | `training/tests/test_transkription.py::…::test_ohne_einwilligung_verweigert_externe_transkription` und `training/tests/test_sitzung.py::…::test_training_ohne_audioeinwilligung_zeigt_nur_tastatureingabe` prüfen dieselbe Regel dort, wo sie wirkt. |
| `test_sitzung_hat_die_vier_vorgegebenen_statuswerte` | streichen | Tautologisch, Startbefund bestätigt: Die Liste ist aus `Sitzung.Status.choices` abgeschrieben. | Jeder Status ist durch seinen Übergang belegt: `gescheitert`, `abgebrochen` und `abgeschlossen` in `test_durchlauf.py`, `laufend` als Ausgangszustand in `test_erschoepftes_budget_meldet_seinen_ausgang_und_schliesst_nur_den_probelauf_ab`. |
| `test_neuer_gespraechsschritt_traegt_entstehungszeitpunkt`, `test_gespraechsschritt_ohne_antwort_traegt_entstehungszeitpunkt`, `test_neue_diagnose_traegt_entstehungszeitpunkt` | streichen | Tautologisch: `auto_now_add` ist Django-Verhalten aus der Felddefinition. | `erhebungen/tests/test_forschenden_views.py::ErhebungsExportTests::test_exportiert_gespraechsschritte_fehlversuche_und_diagnosen` prüft den Zeitstempel im Export. Das gilt für geglückte und antwortlose Schritte und für Diagnosen. |
| `test_neue_sitzung_traegt_entstehungszeitpunkt` | streichen | wie oben | `training/tests/test_abschriften.py::test_kopierte_sitzungen_tragen_die_importzeit` vergleicht `erstellt_am` von Original und Kopie. |
| `test_bestandsdaten_duerfen_ohne_entstehungszeitpunkt_bestehen` | streichen | Totes Gewicht: Der Test hält `null=True` für Bestandszeilen von vor `sitzungen.0007` fest. Die Migration liegt auf `main` (ADR-0031, #325). | Kein Ersatz nötig, Begründung ADR-0031. |
| `test_gespraechsschritt_lehnt_aeusserung_ohne_denkspur_ab`, `…_denkspur_ohne_aeusserung_ab` | behalten | DB-Invariante (CheckConstraint) über die Schnittstelle des Modells. | – |
| `test_answerless_gespraechsschritt_ohne_fehlversuch_wird_abgelehnt`, `…_mit_fehlversuch_wird_gespeichert`, `…_beendet_das_diagnosegespraech`, `test_der_letzte_fehlversuch_eines_answerless_schritts_bleibt_gespeichert` | behalten | Trigger-Invarianten. `answerless_anlegen` ist der dafür vorgesehene öffentliche Weg. | – |
| `test_diagnose_ist_je_sitzung_eindeutig` | behalten | DB-Invariante | – |
| `test_vignettenpositionen_einer_teilnahme_sind_nach_position_geordnet`, `test_vignettenposition_lehnt_sitzung_einer_anderen_teilnahme_ab`, `…_vignette_aus_einer_anderen_sitzung_ab`, `test_position_ist_je_teilnahme_eindeutig` | behalten | DB- und Modellinvarianten. Die Meldungen werden über Literale geprüft. | – |

### `sitzungen/tests/test_importgraph.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_sitzungen_importiert_weder_training_noch_erhebungen`, `test_erhebungen_importiert_training_nicht` | behalten | Architekturwächter über den Importgraph (ADR-0016). Die Ausnahme dafür steht in den Coding Standards. | – |

**Startbefund Importgraph: bestätigt.** Der Wächter ist legitim. Den Wächter in der Simulation gibt es doppelt, aber zu eng: `simulation/tests/test_kern_view.py::SimulationsschichtImportgraphTests` liest nur `simulation/views.py` und hat einen eigenen AST-Helfer. Dabei übersieht er, dass `simulation/__init__.py` selbst `vignetten.models` importiert (#378). Empfehlung für die Umsetzung: Beide Wächter werden zu einer Datei mit einer Kantentabelle aus ADR-0016 zusammengelegt. Sie prüft je App, wohin sie nicht zeigen darf (`sitzungen` nicht auf `training`/`erhebungen`, `erhebungen` nicht auf `training`, `simulation` auf keine Domänen-App). Der Simulationswächter entfällt dann. Ob die Kante `simulation → vignetten` dabei als Ausnahme stehen bleibt, entscheidet #378. Die Simulationsdatei gehört zu #329.

### `sitzungen/tests/test_durchlauf.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| Hilfsfunktion `_verbrauchte_zeit` | umschreiben | Implementation-coupled: Für den `ScratchSink` liest sie `session["probelauf"]["verbrauchte_zeit"]`, also den privaten Session-Aufbau. Für `DBSink` und `FluechtigerSink` ist `Sitzung.verbrauchte_zeit` ein exportiertes Feld und in Ordnung. | Beim `ScratchSink` den Budgetstand über die Schnittstelle beobachten: Der Rückgabewert von `gespraechsschritt_anhaengen` bzw. der `Ausgang` meldet die Erschöpfung. Die Zeitgrenze in die Erwartung legen, z. B. „nach 3 s bei Budget 4 nicht erschöpft, bei Budget 3 erschöpft“. |
| `test_sitzung_starten_lehnt_vignette_ohne_gepinnten_kern_ab` | behalten | Fehlerfall der Schnittstelle | – |
| `test_budgetstand_bucht_nur_die_offene_spanne_und_prueft_budget` | behalten | `Budgetstand` ist öffentlich und speicherlos. Durchgerechnetes Beispiel mit Literalen. | – |
| `test_scratch_sink_haelt_erfolgreichen_schritt_mit_fehlversuchen_in_db_form` | umschreiben | Liest `session["probelauf"]["gespraechsschritte"]` statt der Schnittstelle. | Dieselbe Literal-Erwartung gegen `sink.gespraechsschritte`. Der Test ist der Literal-Anker für den Paritätstest unten. |
| `test_db_sink_persistiert_einen_erfolgreichen_gespraechsschritt`, `test_db_sink_haengt_fehlversuche_neben_den_erfolgreichen_schritt` | behalten | Beim `DBSink` ist die DB die Ausgabe; der Export liest sie. | – |
| `test_db_sink_persistiert_answerless_schritt_und_gescheiterten_status` | streichen | Schichtdoppelung mit `test_gescheiterter_schritt_meldet_denselben_ausgang_und_wird_je_sink_behandelt`: Status `gescheitert` und `aeusserung is None` prüfen beide. | `test_gescheiterter_schritt_…` nach dem Umschreiben unten (mit den drei Fehlversuchen). |
| `test_db_sink_diagnose_schliesst_die_sitzung_ab` | behalten | – | – |
| `test_scratch_und_db_sink_schliessen_mit_diagnose_gleich_ab` | umschreiben | Liest `session["probelauf"]["status"]`. Die DB-Hälfte steht schon im Test darüber. | Nur noch der Scratch-Fall über `scratch.ist_beendet`. |
| `test_db_sink_aktives_abbrechen_setzt_den_eigenen_status` | streichen | Prüft den Setter `status_setzen`, nicht den Ablauf. | `test_sitzung_abbrechen_beendet_die_offene_spanne_und_setzt_status_abgebrochen` |
| `test_scratch_und_db_sink_tragen_dieselbe_gespraechsschritt_struktur` | behalten | Invariante der gemeinsamen Speicherform. Die Erwartung kommt aus dem anderen Adapter, und `test_scratch_sink_…` hält sie als Literal fest. | – |
| `test_zeitbudget_ist_von_jeder_anderen_sitzung_getrennt` | behalten | Regressionswächter aus #245, über das exportierte Feld. | – |
| `test_scratch_und_db_sink_messen_zeit_paritaetisch` | umschreiben | Hängt über `_verbrauchte_zeit` am Session-Aufbau. Der `FluechtigerSink` fehlt in der Paritätsschleife. | Schleife über alle drei Senken. Beim Scratch-Fall belegt der Rückgabewert die Grenze, wie oben. |
| `test_schrittbudget_laesst_die_uhr_in_beiden_sinks_stehen` | umschreiben | wie oben | Beim DB- und flüchtigen Sink über `verbrauchte_zeit`. Beim Scratch-Fall ist das Verhalten ohne Session-Zugriff nicht beobachtbar; dort fällt der Fall weg. |
| `test_schrittbudget_setzt_keine_offene_spanne` | streichen | Implementation-coupled: `offene_spanne_seit` ist der interne Zustand der Uhr, nicht exportiert. | `test_schrittbudget_laesst_die_uhr_…`: Ohne gebuchte Zeit gibt es keine wirksame Spanne. |
| `test_erneutes_anzeigen_setzt_die_offene_spanne_in_beiden_sinks_neu_an` | umschreiben | Wie `messen_zeit_paritaetisch`. Zusätzlich lässt der Rückgabewert `True` bei Budget 3 ein Buchen von 13 s auch durchgehen. | Budget 4 und Erwartung „nicht erschöpft“ (3 s < 4 s). Ein fälschlich gebuchter Reload (13 s) fiele auf. |
| `test_scratch_und_db_sink_pruefen_schrittbudget_paritaetisch` | streichen | Schichtdoppelung: Dasselbe Budget (Schritte, Wert 1) prüft `test_erschoepftes_budget_…` über den Durchlauf statt über den Sink allein. | `test_erschoepftes_budget_meldet_seinen_ausgang_und_schliesst_nur_den_probelauf_ab` |
| `test_sitzung_beenden_beendet_die_offene_spanne` | umschreiben | `monkeypatch.setattr("sitzungen.durchlauf.jetzt", …)`, #324. | Mit `time-machine` die Uhr auf T setzen, `zug_beginnen(T)` aufrufen, um 7 s vorspulen, `sitzung_beenden` aufrufen. Erwartet sind 7 s. |
| `test_sitzung_abbrechen_beendet_die_offene_spanne_und_setzt_status_abgebrochen` | umschreiben | wie oben | wie oben, mit 3 s und Status `abgebrochen` |
| `test_modellverlauf_ist_fuer_beide_sinks_derselbe` | behalten | Literale Paare. Sie schließen die Denkspur schon aus. | – |
| `test_modellverlauf_laesst_die_denkspur_draussen` | streichen | Schichtdoppelung in derselben Datei: Die exakte Erwartung des Tests darüber enthält keine Denkspur. | `test_modellverlauf_ist_fuer_beide_sinks_derselbe` |
| `test_modellverlauf_laesst_schritt_ohne_aeusserung_draussen` | behalten | Grenzfall der Schnittstelle (ADR-0011) | – |
| `test_gespraechsschritt_meldet_fortgesetztes_gespraech_fuer_beide_sinks` | behalten | – | – |
| `test_gescheiterter_schritt_meldet_denselben_ausgang_und_wird_je_sink_behandelt` | umschreiben | Behalten und ergänzen, weil `test_db_sink_persistiert_answerless_…` entfällt. | Zusätzlich: Am DB-Schritt hängen drei Fehlversuche, und `denkspur` ist `None`. |
| `test_erschoepftes_budget_meldet_seinen_ausgang_und_schliesst_nur_den_probelauf_ab` | umschreiben | Der `FluechtigerSink` fehlt. | Den `FluechtigerSink` als dritte Senke aufnehmen; er bleibt `laufend`. |
| `test_fluechtiger_sink_haelt_den_verlauf_nur_in_der_session`, `test_fluechtiger_sink_haelt_den_gescheiterten_schritt_nur_in_der_session` | behalten | „Keine Inhaltszeile in der DB“ ist die Zusage aus ADR-0045, keine Abwesenheit eines Feldes. | – |
| `test_fluechtiger_sink_fuehrt_budget_uhr_an_der_sitzung` | streichen | Der Paritätstest deckt ihn ab, sobald er alle drei Senken durchläuft. `assert not modellverlauf(sink)` prüft nur, dass kein Schritt lief. | `test_scratch_und_db_sink_messen_zeit_paritaetisch` nach dem Umschreiben |
| `test_fluechtiger_sink_meldet_das_erschoepfte_schrittbudget` | streichen | wie oben | `test_erschoepftes_budget_…` nach dem Umschreiben |
| `test_rahmenhandlung_escaped_vignettenwerte_und_rendert_das_markdown_des_kerns` | behalten | Das Escaping der Werte leistet `rahmenhandlung_rendern` selbst. | – |
| `test_rahmenhandlung_link_syntax_des_kerns_bleibt_woertlich` | behalten | Ähnelt `texte/tests/test_markdown.py::…::test_link_syntax_bleibt_woertlich`. Trotzdem ist es der einzige Test, der die Wahl des Profils `szenentext` in `rahmenhandlung_rendern` festhält; mit `informationstext` bestünde der erste Test weiter. | – |

### `sitzungen/tests/test_probelauf.py`

**Strukturbefund (totes Gewicht):** `ProbelaufGespraechTests` und `GeteiltesKontoTests` erben von `ProbelaufStartTests` und damit auch dessen 11 Tests. pytest sammelt die Datei als 58 Läufe: 11 für `ProbelaufStartTests`, 33 für `ProbelaufGespraechTests`, 12 für `GeteiltesKontoTests` und 2 für die Administration. 22 davon wiederholen dieselben Starttests. **Umschreiben:** `setUp` in eine Basisklasse ohne Tests ziehen (Mixin), von der alle drei Klassen erben.

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_auswahl_zeigt_nur_eigene_entwuerfe_und_startet_rahmenhandlung` | umschreiben | Die vier `session["probelauf"][…]`-Zusicherungen lesen den privaten Session-Aufbau. | Die HTTP-Hälfte bleibt. Das gepinnte Tripel ist schon durch die gerenderte Rahmenhandlung des Kerns belegt. Die Konfiguration belegt der Zieltest der nächsten Zeile. |
| `test_start_liest_die_schuelerin_nicht_lehrperson_oder_bewerter` | umschreiben | Liest `session["probelauf"]["modell_konfiguration_pk"]`. | Schülerin- und Lehrpersonen-Konfiguration mit verschiedenen Fake-Skripten belegen. Nach einem Gesprächsschritt steht die Äußerung der Schülerinnen-Konfiguration in der Antwort. |
| `test_frischer_entwurf_startet_ohne_akteure_zu_setzen` | behalten | – | – |
| `test_rahmenhandlung_erscheint_als_szenentext_mit_woertlichen_werten` | umschreiben | Leicht implementation-coupled: `class="markdown-text rahmenhandlung__text"` hält Markup fest. Der Rest ist der eigene Beitrag der HTTP-Schicht: Alle drei Abschnitte laufen durch `rahmenhandlung_rendern`. | Die Klassen-Zusicherung entfällt, die Zusicherungen auf `<h3>`, `<strong>`, `<em>` und `<li>` bleiben. |
| `test_sitzung_waechst_per_htmx_unter_der_bleibenden_einleitung` | behalten | Die IDs `sitzung-fortsetzung`, `diagnosegespraech` und `sitzung-debrief` sind die HTMX-Ziele, also Vertrag mit dem Frontend. Die Bildnamen folgen dem Geschlecht. | – |
| `test_arbeitsheft_ordnet_text_und_bild_am_marker`, `test_lernauftrag_ordnet_text_und_bild_am_marker` | behalten | Die einzigen Tests der Bildreihenfolge auf einer gerenderten Seite. Das Include `vignetten/includes/aufgabenkontext_inhalt.html` teilen sich Sitzung, Vignettendetail und Abschrift. | – |
| `test_lernauftrag_rendert_die_teile_um_das_bild_je_als_szenentext` | behalten | Die Containerklasse im Erwartungsstring ist der Preis dafür, zwei getrennte Szenentexte überhaupt zu unterscheiden. | – |
| `test_startzustand_ueberlebt_folge_request_ohne_domaenenschreiben` | streichen | Vergleicht `session["probelauf"]` mit einem Dict (privater Aufbau). „Überlebt den Folge-Request“ belegt jeder mehrstufige Test. Domänenzeilen zählen sieben Tests der Datei: zwei inline über acht Modelle (dieser und `test_antwort_und_denkspur_…`), einer über drei Modelle (`test_beenden_…_schreibfrei`) und vier über den Helfer `_domaenenzeilen_zaehlen` (Schrittbudget und die drei Zeitbudget-Tests). | `test_beenden_zeigt_debrief_und_verwirft_diagnose_schreibfrei` nach dem Umschreiben unten |
| `test_gespraech_kann_bereits_aus_der_einleitung_beendet_werden` | behalten | – | – |
| `test_aktionszeile_im_probelauf_ohne_abbrechen` | umschreiben | Sucht den Knopf über `class="button button--neutral sitzung-aktionen__beenden"`. | „Gespräch beenden“ über `config.tests.formular.submit_knoepfe` prüfen. Erklärsatz und fehlendes „Sitzung abbrechen“ bleiben. |
| `test_bildbeschreibung_im_prompt_folgt_dem_positionsmarker` | streichen | Schichtdoppelung: Die Platzhalter-Komposition prüft `vignetten` direkt an `prompt_platzhalter`. Wie die Platzhalter in den Prompt gelangen, prüft `simulation`. | `vignetten/tests/test_vignetten_models.py::test_prompt_platzhalter_ordnet_lernauftrag_text_und_bildbeschreibung`, `…_ordnet_arbeitsheft_text_und_bildbeschreibung`, `test_positionsmarker_zaehlt_nur_allein_auf_einer_zeile` |
| `test_prompt_erhaelt_die_markdown_quelle` | umschreiben | Schichtdoppelung wie oben. Nur „Markdown bleibt roh“ (ADR-0044) steht in `vignetten` nicht ausdrücklich. | Ein Fall in `vignetten/tests/test_vignetten_models.py`: `prompt_platzhalter` reicht `**zwei**` und `[Tipp](…)` unverändert durch (Bereich #328). Danach streichen. |
| `test_simulationshinweise_erscheinen_nicht_auf_sitzungsseite_aber_im_prompt` | umschreiben | Die Prompt-Hälfte doppelt `test_prompt_platzhalter_fasst_simulationshinweise_in_umgebungen`. | Nur die Seitenhälfte behalten: Start- und Gesprächsseite enthalten die Hinweise nicht. |
| `test_spracheingabe_steht_schon_beim_ersten_schritt_bereit`, `test_spracheingabe_steht_im_gespraech_und_im_debrief_bereit` | behalten | `data-spracheingabe` ist der Haken für das Frontend. | – |
| `test_spracheingabe_traegt_dieselbe_aufnahmegrenze_wie_der_endpunkt` | umschreiben | Die Erwartung kommt aus `settings.TRANSKRIPTION_MAX_AUFNAHME_BYTES`, aus derselben Quelle wie der Code. | `@override_settings(TRANSKRIPTION_MAX_AUFNAHME_BYTES=1234)` mit der Erwartung `data-maximale-bytes="1234"`. |
| `test_antwort_und_denkspur_werden_live_angezeigt_und_in_session_behalten` | umschreiben | Sammeltest. Die Session-Liste ist privater Aufbau. Die Payload-Prüfung doppelt `test_modellverlauf_traegt_beide_gespraechsseiten` und `test_durchlauf.py`. Die acht Zeilenzählungen doppeln den Schreibfrei-Test. | Nur das Eigene behalten: Eingabe, Äußerung und Denkspur (ADR-0005, im Probelauf sichtbar) stehen in der Antwort, die zweite Antwort zeigt den Verlauf. |
| `test_schrittbudget_fuehrt_nach_letztem_schritt_unsichtbar_in_den_debrief` | umschreiben | Liest `session["probelauf"]["status"]` und `…["gespraechsschritte"]`. Die Zeilenzählung doppelt den Schreibfrei-Test. | Über HTTP: Debrief und letzte Äußerung stehen in der Antwort, „Budget“ nicht. Die Zählung über `_domaenenzeilen_zaehlen` entfällt. Erneutes GET und POST zeigen den Debrief. Nach dem POST hat der Fake keine weitere Anfrage bekommen (`FakeSprachmodell.letzte_anfragen` wächst nicht), und „Und warum?“ steht nicht im Verlauf. |
| `test_zeitbudget_pausiert_waehrend_des_modellaufrufs`, `test_zeitbudget_pausiert_waehrend_endgueltiger_fehlversuche` | umschreiben | Startbefund bestätigt: `patch("sitzungen.durchlauf.jetzt", side_effect=[…])` hängt sogar an Zahl und Reihenfolge der Aufrufe. Liest `session["probelauf"]["verbrauchte_zeit"]`. | `time-machine` und Erwartung über das Budget: Budget 5 s, 4 s Autorinnenzug, danach steht das Gespräch weiter offen („Ihre nächste Frage“). **Hinweis für #349:** Der Fake antwortet sofort, mit `time-machine` allein vergeht im Modellaufruf keine Zeit. Wer die Pause selbst belegen will, braucht einen Fake-Skripteintrag, der den aktiven Traveller vorstellt (Testadapter der Sprachmodell-Naht). Sonst prüft der Test nur, dass die Zeit nach der Antwort neu anläuft. Die Zählung über `_domaenenzeilen_zaehlen` entfällt wie beim Schrittbudget. |
| `test_zeitbudget_fuehrt_nach_laufendem_schritt_in_den_debrief` | umschreiben | `patch` auf `jetzt` und Session-Zugriff | `time-machine`: GET zu T, POST zu T+5 s. Die Antwort zeigt Debrief und Äußerung. Die Zählung über `_domaenenzeilen_zaehlen` entfällt. |
| `test_modellverlauf_traegt_beide_gespraechsseiten` | behalten | Die Fake-Aufzeichnung ist die Payload an der Sprachmodell-Naht (ADR-0016). Die Erwartung ist ein Literal. Der eigene Beitrag: Der Verlauf übersteht die Session zwischen zwei Anfragen. | – |
| `test_leere_aeusserung_bleibt_im_modellverlauf` | umschreiben | Die Regel steckt in `modellverlauf` (`is not None`). Ihr Gegenstück „Schritt ohne Äußerung bleibt draußen“ steht in `test_durchlauf.py`. | Nach `test_durchlauf.py` neben `test_modellverlauf_laesst_schritt_ohne_aeusserung_draussen` verschieben, über `modellverlauf(sink)` für alle Senken. |
| Hilfsfunktion `_endgueltigen_fehlschlag_ausloesen` | umschreiben | Schreibt den Verlauf von Hand in `session["probelauf"]["gespraechsschritte"]`, im alten Format ohne `eingabemodus`. | Den Verlauf über einen echten ersten Schritt aufbauen: Skript aus einer Antwort und drei Fehlern. |
| `test_endgueltiger_fehlschlag_zeigt_fehlermeldung`, `…_zeigt_erneutes_senden`, `…_bewahrt_eingabe_fuer_wiederholung`, `…_bewahrt_den_eingabemodus_fuer_wiederholung`, `…_zeigt_beenden_im_debrief`, `…_bewahrt_den_sichtbaren_verlauf` | behalten | HTTP-Verhalten, nach dem Umschreiben des Helfers. Zusammenlegen ist möglich, aber kein Befund. | – |
| `test_endgueltiger_fehlschlag_verbirgt_fehlergrund` | umschreiben | Besteht per Konstruktion: Der Grund heißt `Anbieterfehler`, geprüft wird das kleingeschriebene `anbieterfehler`. | `assertNotContains(response, "Anbieterfehler")`, dazu eine erkennbare `rohantwort` im Skript, die ebenfalls fehlen muss. |
| `test_beenden_zeigt_debrief_nach_endgueltigem_fehlschlag` | behalten | – | – |
| `test_beenden_zeigt_debrief_und_verwirft_diagnose_schreibfrei` | umschreiben | Wird der eine Schreibfrei-Test (ADR-0014). | Ablauf mit Start, geglücktem Schritt, gescheitertem Schritt, Beenden und Debrief. Danach unverändert: alle acht Zählungen aus `test_startzustand_…`. Der Helfer `_domaenenzeilen_zaehlen` entfällt, sobald die vier Budget-Tests ihn nicht mehr benutzen. Dazu Rücksprung zur Vignette und `probelauf_laeuft(session)` ist falsch statt `"probelauf" not in session`. |
| `AdministratorinProbelaufTests::test_administratorin_startet_freies_tripel_…` | umschreiben | Liest `session["probelauf"]["kern_pk"]`; den Kern belegt schon die gerenderte Rahmenhandlung. `assertContains(auswahl, str(pk))` trifft jede Ziffernfolge. | Session-Zugriff streichen. Die Auswahl über `<option value="…">` mit `html=True` prüfen. |
| `AdministratorinProbelaufTests::test_nicht_administratorin_erreicht_freien_auswaehler_nicht` | behalten | – | – |
| `GeteiltesKontoTests::test_zwei_anmeldungen_desselben_kontos_proben_unabhaengig` | umschreiben | Erbt die Starttests (siehe oben). Liest `session["probelauf"]["vignette_pk"]`; die getrennten Antworten belegen das schon. | Session-Zugriff streichen, von der Basisklasse ohne Tests erben. |

**Startbefund Zeit: bestätigt.** Drei Tests patchen `sitzungen.durchlauf.jetzt` mit `side_effect`-Listen und legen damit fest, wie oft und in welcher Reihenfolge die Views die Uhr lesen. In `test_durchlauf.py` tun es zwei weitere per `monkeypatch`. Alle fünf bekommen *umschreiben*, umgesetzt in #349.

### `sitzungen/tests/test_transkription.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| Aufruf über `transkriptions_endpunkt(fabrik, probelauf_sitzung_fuer_transkription)` statt über die URL | behalten | `transkriptions_endpunkt` ist öffentlich. `anbieter_bilden` ist die Naht zum Drittanbieter mit zwei Adaptern. Über die URL ließen sich Anbieterfehler nicht skripten. | – |
| `test_bildet_den_anbieter_je_anfrage_neu` | behalten | Zählt Aufrufe der übergebenen Fabrik. Das ist die dokumentierte Zusage der Schnittstelle (Docstring), kein interner Kollaborateur. | – |
| `test_laufender_probelauf_transkribiert_ohne_teilnahme`, `test_ohne_laufenden_probelauf_bleibt_der_endpunkt_verschlossen` | behalten | Autorisierung des Probelaufs | – |
| `test_reicht_anbieterfehler_als_unterscheidbare_zustaende_durch`, `test_zero_retention_bleibt_auch_im_probelauf_das_tor`, `test_persistiert_keine_aufnahme` | behalten | Allgemeines Verhalten des Endpunkts. Die Datei liegt bei der Fabrik und ist deshalb der richtige Ort dafür. | – |
| `test_lehnt_aufnahme_ueber_der_grenze_mit_eigenem_status_ab`, `test_nimmt_aufnahme_genau_auf_der_grenze_an` | umschreiben | Die Grenze kommt aus `settings.TRANSKRIPTION_MAX_AUFNAHME_BYTES`, aus derselben Quelle wie der Code. | `@override_settings(TRANSKRIPTION_MAX_AUFNAHME_BYTES=8)`, Aufnahmen mit 8 und 9 Byte. |

### `training/tests/test_transkription.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| Hilfsfunktion `_sitzung_starten` | umschreiben | Legt die Vignette über die private Naht `Vignette.objects._erstellen` an (SLF001-Übergangsliste) und setzt `session["training_sitzung_pk"]` von Hand. | Die Sitzung über HTTP starten: `wahl` und `einwilligung` mit „ja“, wie in `TrainingssitzungTests._sitzung_starten`. Die finale Vignette über den öffentlichen Weg (siehe Querschnitt). |
| `test_liefert_das_transkript_einer_aufnahme`, `test_ohne_einwilligung_verweigert_externe_transkription` | behalten | Prinzipal-spezifisch: `training_sitzung` und die Einwilligung der Teilnahme. | – |
| `test_ohne_laufende_sitzung_bleibt_der_endpunkt_verschlossen` | umschreiben | Prinzipal-spezifisch, löscht aber den Session-Schlüssel `training_sitzung_pk` von Hand. | Nach `abbrechen` ist der Endpunkt verschlossen. |
| `test_reicht_anbieterfehler_als_unterscheidbare_zustaende_durch`, `test_ohne_zero_retention_verweigert_externe_transkription`, `test_persistiert_keine_aufnahme` | streichen | Schichtdoppelung: Dasselbe Endpunktverhalten prüft die Probelauf-Datei. Der Trainingsprinzipal ändert daran nichts. | `sitzungen/tests/test_transkription.py::…::test_reicht_anbieterfehler_…`, `…::test_zero_retention_bleibt_auch_im_probelauf_das_tor` und `…::test_persistiert_keine_aufnahme`. Dieselbe Doppelung hat `erhebungen/tests/test_transkription.py` (Bereich #327). |

### `training/tests/test_models.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_veroeffentlichen_ueberfuehrt_einen_entwurf`, `…_lehnt_wiederholung_ab`, `…_lehnt_veralteten_entwurf_ab`, `test_training_muss_als_entwurf_angelegt_werden`, `test_training_verhindert_direkte_zustandswechsel_beim_speichern`, `…_massenhafte_zustandswechsel` | behalten | Lebenszyklus-Invarianten über die Schnittstelle. Die Meldungen werden über Literal-Fragmente geprüft. | – |
| `test_training_bindet_nur_finale_vignetten_und_bleibt_austauschbar` | umschreiben | Legt Vignetten über `Vignette.objects._erstellen` an. Geprüft wird die Invariante des Trainings, nicht die der Vignette; die Naht ist hier nicht gerechtfertigt. | Entwurf über `Vignette.objects.anlegen(konto)`, die finale Fassung über den öffentlichen Weg. Die Zusicherungen bleiben. |
| `test_finale_vignette_kann_rueckwaerts_eingebunden_und_archiviert_werden` | umschreiben | wie oben. Zusätzlich legt die erste Zeile eine Vignette an, die nie benutzt wird. | wie oben, ohne die tote Zeile |
| `test_trainingsbindung_haelt_training_konto_und_genau_eine_teilnahme` | umschreiben | Die erste Zusicherung ist tautologisch: Die Felder sind gleich den gesetzten. Die zweite verletzt zwei Constraints zugleich (1:1 `teilnahme` und eindeutig `training`/`konto`). Welcher greift, bleibt offen. | Zwei Fälle: dieselbe Teilnahme mit anderem Konto und Training ergibt `IntegrityError`, ebenso dasselbe Training und Konto mit neuer Teilnahme. |
| `test_sichtbar_fuer_liefert_eigene_trainings_und_alle_fuer_administration` | streichen | Schichtdoppelung mit dem Vertrag des Eigentümer-Kreises (Hinweis aus #332) | `config/tests/test_eigentuemer_kreis_contract.py::test_sichtbar_sind_die_eigenen_bestaende_und_der_administration_alle[Training]` |
| `test_geteiltes_training_ist_fuer_alle_eigentuemerinnen_sichtbar` | streichen | wie oben | derselbe Vertragstest; über HTTP `training/tests/test_views.py::TrainingKoautorschaftTests::test_hinzufuegen_gibt_koeigentuemern_listenzugriff` |
| `test_veroeffentlichtes_training_behaelt_aenderbaren_eigentuemerinnenkreis` | streichen | Schichtdoppelung mit dem HTTP-Test gleichen Inhalts. Auf Modellebene prüft er nur M2M-`add`/`remove` von Django. | `training/tests/test_views.py::TrainingKoautorschaftTests::test_veroeffentlichtes_training_kann_weiter_uebergeben_werden` |

### `training/tests/test_bindungsexklusivitaet.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_erhebungsteilnahme_nimmt_keine_trainingsbindung_an`, `…_nimmt_keine_abschrift_an`, `test_trainingsteilnahme_nimmt_keine_erhebungsbindung_an`, `test_abschriftsteilnahme_nimmt_keine_erhebungsbindung_an`, `test_bestehende_bindung_laesst_sich_nicht_umhaengen`, `test_mengen_update_haengt_keine_teilnahme_um`, `test_bulk_create_weist_die_unvertraegliche_bindung_ab` | umschreiben (nur die Erwartung) | DB-Invarianten über die Schnittstelle der Modelle, sonst einwandfrei. `match=UNVERTRAEGLICHE_BINDUNG` und `match=UMHAENGEN_FEHLERMELDUNG` nehmen aber die Meldungskonstante des geprüften Moduls als Erwartung. | `match="Bindung der anderen Art"` bzw. `match="Mengen-Update"` als Literal-Fragment. Die Fälle bleiben unverändert. |
| `test_bindungen_gleicher_art_bleiben_unberuehrt`, `test_gewoehnliches_speichern_bleibt_moeglich` | behalten | Gegenfälle der Invariante ohne Meldungserwartung | – |

### `training/tests/test_abschriften.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| Hilfsfunktionen `_finaler_kern`, `_finale_vignette_anlegen`, `_erhebung_anlegen`, `_stichprobe_anlegen`, `_gespielte_teilnahme`, `_gespielte_teilnahme_in_neuer_erhebung`, `_abschrift_mit_zwei_sitzungen`, `_gelesene_ansicht` | behalten | Öffentliche Wege. `_finale_vignette_anlegen` ist das Vorbild für den gemeinsamen Helfer (siehe Querschnitt). `Sitzung`, `Gespraechsschritt` usw. per `objects.create` herzustellen ist Testaufbau, keine Prüfung. | – |
| `test_holt_die_sitzungen_einer_abgeschlossenen_teilnahme_ins_konto` | behalten | Die Erwartungen kommen aus den Testdaten, nicht aus dem Modul. Lücke: Kopiert werden auch `verbrauchte_zeit`, `eingabemodus` des Schritts und der Diagnose; keiner dieser Werte ist geprüft. | Ergänzen: abweichende Werte im Original setzen und an der Kopie erwarten. |
| `test_laesst_die_erhebungsseite_unberuehrt`, `test_kopiert_keine_fragebogen_antworten`, `test_import_nach_dem_erhebungsfenster_gelingt`, `test_zweiter_import_erzeugt_eine_eigenstaendige_zweite_abschrift` | behalten | – | – |
| `test_kopierte_sitzungen_tragen_die_importzeit` | umschreiben | `kopie.erstellt_am > original.erstellt_am` hängt daran, dass die Wanduhr zwischen zwei Anlagen weiterläuft. | Mit `time-machine`: Original zu T1 anlegen, zu T2 importieren, an der Kopie T2 erwarten. Das ist kein Patch und gehört deshalb in die Umsetzung dieses Reviews, nicht in #349. |
| `test_weist_unbrauchbare_tokens_mit_derselben_meldung_ab` (5 Fälle) | umschreiben | `messages == [ABLEHNUNG]` nimmt die Modulkonstante als Erwartung. | Literal „Zu diesem Teilnahme-Token lässt sich keine Abschrift holen.“ |
| `test_abschrift_haelt_weder_token_noch_verweis_auf_die_erhebung` | streichen | Totes Gewicht: prüft die Abwesenheit von Feldern über `_meta.get_fields()`. Das schließen die Coding Standards ausdrücklich aus. Ein anders benanntes Feld liefe ohnehin durch. | Kein Ersatz nötig. Die Zusage aus ADR-0043 sichern `test_laesst_die_erhebungsseite_unberuehrt`, `test_loeschen_laesst_die_erhebungsdaten_unberuehrt` und der Importgraph-Wächter `test_erhebungen_importiert_training_nicht`. |
| `test_token_eingabe_ist_jedem_eingeloggten_konto_zugaenglich`, `test_eingegebenes_token_erzeugt_die_abschrift_und_listet_sie` | behalten | – | – |
| `test_abschriften_sind_ueber_den_erhebungsnamen_verlinkt` | umschreiben | Ganze Markup-Strings samt Klassen. `">Lesen</a>" not in` und `">Aktion<" not in` prüfen die Abwesenheit entfernter Elemente. | Die Seite enthält einen Link auf `reverse("training:abschrift", …)` mit dem Erhebungsnamen als Text, dazu „Lesen ›“. |
| `test_abgelehntes_token_meldet_den_grundlosen_hinweis` | umschreiben | Die Erwartung ist `ABLEHNUNG` aus dem Modul. | Literal wie oben |
| `test_token_einer_fluechtigen_teilnahme_meldet_den_grundlosen_hinweis` | streichen | Schichtdoppelung: Die View reicht die Meldung für jeden Grund gleich durch; die Gründe prüft der parametrisierte Test. | `test_weist_unbrauchbare_tokens_mit_derselben_meldung_ab[fluechtig]` und `test_abgelehntes_token_meldet_den_grundlosen_hinweis` |
| `test_abschriften_fremder_konten_bleiben_aus_der_liste`, `test_abschrift_zaehlt_nicht_zur_trainingshistorie` | behalten | – | – |
| `test_historie_ist_ueber_den_trainingsnamen_verlinkt` | umschreiben | Quelltext: Der Test sucht das Alpine-Template (`:href="r.url" x-text="r.name"`) in einer *leeren* Historie und prüft dazu Abwesenheiten. Er gehört nicht zu den Abschriften. | Nach `test_katalog.py`: Mit einer Trainingsbindung enthält die Historie den Trainingsnamen, die Detail-URL, den Fortschritt (z. B. „1 / 2“) und „Ansehen ›“. Die Historie ist sonst ungetestet (siehe Lücken). |
| `test_ansicht_zeigt_die_vignetten_in_der_gespielten_reihenfolge`, `test_ansicht_zeigt_auch_eine_sitzung_ohne_vignettenposition`, `test_ansicht_zeigt_transkript_ausgang_und_eigene_diagnose`, `test_ansicht_verschweigt_die_denkspur`, `test_ansicht_bietet_keine_eingabe_und_keine_sitzungsnavigation` | behalten | – | – |
| `test_ansicht_rendert_lernauftrag_und_arbeitsheft_als_szenentext` | umschreiben | Schichtdoppelung: Das Profil des geteilten Includes `aufgabenkontext_inhalt.html` prüft die Vignettendetailseite. | Auf einen Einbindungsbeleg kürzen: `Addiere <strong>die</strong> Brüche.` steht in der Seite. Das Profil prüft `vignetten/tests/test_views.py::…::test_rendert_lernauftrag_und_arbeitsheft_als_szenentext`. |
| `test_fremde_abschrift_ist_nicht_erreichbar`, `test_trainings_sitzungsansicht_zeigt_abschriften_nicht` | behalten | – | – |
| `test_loeschen_entfernt_abschrift_teilnahme_und_kopierte_sitzungen`, `test_loeschen_laesst_die_erhebungsdaten_unberuehrt`, `test_konto_loeschen_nimmt_die_abschrift_mit_allem_kopierten_mit`, `test_konto_loeschen_laesst_die_erhebungsdaten_unberuehrt` | behalten | Zwei Löschwege mit derselben Zusage. Die Prüfung über die DB ist hier die Zusage selbst: Nichts bleibt zurück. Die Paare ließen sich über den Löschweg parametrisieren. | – |

### `training/tests/test_katalog.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| Vignetten über `Vignette.objects._erstellen` (vier Tests und der Helfer der `TrainingsabbruchTests`) | umschreiben | SLF001-Übergangsliste, keine DB-Invariante der Vignette im Spiel | gemeinsamer Helfer (siehe Querschnitt) |
| `test_zeigt_beigetretene_trainings_im_katalog_und_in_der_navigation`, `test_versteckt_unveroeffentlichte_trainings`, `test_listet_finale_vignetten_und_bestaetigt_freie_wahl`, `test_katalog_erfordert_anmeldung`, `test_versteckt_nachtraeglich_archivierte_vignette` | behalten | – | – |
| `test_zeilen_sind_ueber_den_namen_verlinkt` | umschreiben | Quelltext: sucht das Alpine-Template als String, dazu Abwesenheiten (`button--secondary`, `>Aktion<`). | Die Zeilendaten prüfen, die die Seite ausliefert: Name, Detail-URL und `action_label` „Öffnen“, bei Ausbilder:innen „Kuratieren“. Ob sie im JSON oder im HTML stehen, zeigt `assertContains` auf die URL. |
| `test_spielt_vignette_persistiert_und_verwendet_die_trainingsbindung_wieder` | behalten | Durchgehender Ablauf über HTTP mit Wiederverwendung der Bindung. Die DB-Prüfung der Denkspur ist hier Beleg der Persistenz. | – |
| `test_einwilligung_wird_an_der_teilnahme_gespeichert_bevor_die_sitzung_startet` | behalten | – | – |
| `TrainingsabbruchTests::test_ablehnung_startet_das_training_mit_tastatureingabe` | behalten | Gehört zur Trainingssitzung und nach `test_sitzung.py`. | – |
| `TrainingsabbruchTests::test_abbrechen_beendet_die_sitzung_ohne_diagnose` | behalten | Der einzige Abbruch aus dem laufenden Diagnosegespräch. `test_sitzung.py::…::test_abbrechen_setzt_den_gewollten_status_ohne_diagnose` bricht erst nach `gespraech_beenden` ab, also aus dem Debrief. Gehört nach `test_sitzung.py`. | – |
| `TrainingsabbruchTests::test_endgueltiger_fehlschlag_bewahrt_abbruchschritt_und_fehler` | streichen | Schichtdoppelung: Meldung, Status und `aeusserung is None` prüft `test_sitzung.py`, die drei Fehlversuche prüft der Durchlauf. | `training/tests/test_sitzung.py::…::test_endgueltiger_fehlschlag_bleibt_gescheitert` und `sitzungen/tests/test_durchlauf.py::test_gescheiterter_schritt_…` nach dem Umschreiben |

### `training/tests/test_sitzung.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| Hilfsfunktion `_sitzung_starten` | umschreiben | `Vignette.objects._erstellen` | gemeinsamer Helfer (siehe Querschnitt) |
| `test_training_startet_mit_rahmenhandlung_und_eingabefeld` | behalten | – | – |
| `test_senden_ist_die_einzige_hauptaktion_der_eingabezeile` | streichen | Implementation-coupled: Der Test prüft nur Knopfklassen (`button--secondary`, `gespraechseingabe__senden`), also visuelle Gewichtung. | Keiner. Die Rangfolge der Knöpfe beobachtet pytest nicht. Die fehlende Meldung „nicht freigegeben“ prüft `test_training_ohne_audioeinwilligung_zeigt_nur_tastatureingabe` im Gegenfall. |
| `test_aktionszeile_traegt_beenden_erklaersatz_und_abbrechen` | umschreiben | Drei Klassen-Strings | „Gespräch beenden“ über `submit_knoepfe`, Erklärsatz, und ein Formular mit `action` auf `training:abbrechen`. Klassen entfallen. |
| `test_training_liest_die_schuelerin_nicht_lehrperson_oder_bewerter` | umschreiben | Die Erwartung `ModellKonfiguration.objects.belegte(SCHUELERIN)` ruft dieselbe Funktion wie die View. | Erwartet ist die im Setup aktivierte Konfiguration. Dafür gibt der Helfer sie zusätzlich zurück; heute liefert er nur das `Training`. |
| `test_training_rendert_lernauftrag_und_arbeitsheft_als_szenentext` | streichen | Schichtdoppelung: Das Profil des geteilten Includes prüft der Vignettentest mit fast denselben Eingaben. Der Probelauf deckt die Sitzungsseite ab. | `vignetten/tests/test_views.py::…::test_rendert_lernauftrag_und_arbeitsheft_als_szenentext`. Die Einbindung belegt `test_training_startet_mit_rahmenhandlung_und_eingabefeld` („Addiere zwei Brüche.“). |
| `test_training_spielt_eine_vignette_mit_ueberholtem_kern`, `test_startseite_bindet_die_spracheingabe_an_die_laufende_sitzung`, `test_training_ohne_audioeinwilligung_zeigt_nur_tastatureingabe`, `test_debrief_ohne_audioeinwilligung_zeigt_nur_tastatureingabe` | behalten | – | – |
| `test_endgueltiger_fehlschlag_bleibt_gescheitert` | behalten | Ersatz für den Katalog-Test gleichen Inhalts | – |
| `test_abbrechen_setzt_den_gewollten_status_ohne_diagnose` | behalten | Den zweiten Teil (Diagnose nach dem Abbruch) gibt es nur als Wettlauf zweier Anfragen. `session["training_sitzung_pk"]` von Hand zu setzen ist die einzige Möglichkeit, ihn ohne Nebenläufigkeit zu erzeugen. | – |
| `test_trainingssitzung_fuehrt_den_eingabemodus_mit`, `test_trainingsdiagnose_fuehrt_den_eingabemodus_mit` | behalten | – | – |
| `test_schrittbudget_zeigt_debrief_bei_laufender_sitzung`, `test_zeitbudget_zeigt_debrief_bei_laufender_sitzung` | umschreiben | `assertContains(debrief, "Debrief")` besteht auch ohne Debrief: Die Aktionszeile der Gesprächsseite sagt „Danach folgt der Debrief …“. | „Was ist Ihnen aufgefallen?“ erwarten und „Ihre nächste Frage“ ausschließen. |
| `test_debrief_nach_vorzeitigem_gespraechsende_bleibt_laufend` | behalten | – | – |
| `test_denkspur_bleibt_im_training_verborgen` | behalten | ADR-0005 für das Training | – |
| `test_vergangene_sitzung_ansehen_ist_schreibgeschuetzt` | umschreiben | `assertContains(response, "Debrief")` ist schwach, siehe oben. | Die Diagnosefrage oder den Debrief-Text des Kerns erwarten. |
| `test_vergangene_sitzung_anderer_konten_nicht_einsehbar` | behalten | – | – |

### `training/tests/test_views.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_legt_training_an_und_listet_nur_eigene_trainings`, `test_konto_ohne_ausbilderrolle_kann_kein_training_anlegen`, `test_administratorin_erreicht_alle_sichtbaren_trainings`, `test_koeigentuemerin_kann_training_kuratieren_und_veroeffentlichen` | behalten | – | – |
| `TrainingAnlegenTests::test_zeilen_sind_ueber_den_namen_verlinkt` | umschreiben | Quelltext (Alpine-Template als String), Klassen und Abwesenheiten | Die Liste enthält Name, Kuratier-URL und „Kuratieren ›“. |
| `TrainingKuratierenTests::test_zeigt_den_eigentuemer_kreis` | behalten | Prüft nur, dass der Abschnitt eingebunden ist (Hinweis aus #332). | – |
| `TrainingKuratierenTests::test_nimmt_nur_eigene_finale_vignetten_auf_und_entfernt_sie_wieder` | umschreiben | Legt die Vignetten über `_erstellen` an. Belegt wird über `training.vignetten.all()` statt über die Seite. Die letzte Zusicherung `not training.vignetten.filter(pk=fremde_finale.pk).exists()` besteht per Konstruktion, weil der Test die fremde Fassung nie aufzunehmen versucht. | Öffentlicher Helfer. Belegen über die Kuratierseite (welche Vignetten gebunden bzw. verfügbar sind). Den Fremdfall echt prüfen: `POST vignette_hinzufuegen` mit der fremden Fassung ergibt 404, ebenso mit dem Entwurf. |
| `TrainingKoautorschaftTests::test_hinzufuegen_gibt_koeigentuemern_listenzugriff` | behalten | – | – |
| `TrainingKoautorschaftTests::test_hinzufuegen_erlaubt_koeigentuemern_das_veroeffentlichen` | streichen | Schichtdoppelung: Hinzufügen und Veröffentlichen durch die Ko-Eigentümerin sind je einzeln geprüft. | `test_hinzufuegen_gibt_koeigentuemern_listenzugriff` und `TrainingAnlegenTests::test_koeigentuemerin_kann_training_kuratieren_und_veroeffentlichen` |
| übrige `TrainingKoautorschaftTests` (Selbstentfernung, letzte Eigentümerin, Rolle, Administration, veröffentlichtes Training, fremde Administration, Nicht-Eigentümerin, zweimal nur POST) | behalten | Die HTTP-Seite des Eigentümer-Kreises, Erwartungen als Literale | – |
| `TrainingSichtbarkeitTests::test_fremdes_training_gibt_auch_ueber_die_detail_url_404` | behalten | – | – |
| `VeroeffentlichteTrainingsTests::test_entwurf_erscheint_nicht_im_veroeffentlichten_queryset` | streichen | Schichtdoppelung: ein Modelltest im View-Modul, über HTTP schon gedeckt | `training/tests/test_katalog.py::…::test_versteckt_unveroeffentlichte_trainings` |

**Startbefund Schichtdoppelung: teilweise bestätigt.** Zwischen `test_durchlauf.py` und `test_probelauf.py` doppelt sich weniger als vermutet. Der Durchlauf prüft den Vertrag der Senken (Parität), der Probelauf das, was die Views darüber legen (Uhr nach der Antwort, Debrief nach Budgetende, Fehlschlag-Darstellung). Echte Doppelungen sind:

- der Ausschluss der Denkspur aus dem Modellverlauf, an drei Stellen;
- die Platzhalter-Komposition, im Probelauf und in `vignetten`;
- die Schreibfrei-Zählung, in sieben Tests des Probelaufs;
- die Starttests, die durch Vererbung dreimal laufen.

Zwischen Trainingssitzung und Training-Views liegt die Doppelung nicht in `test_views.py`, das die Ausbilder-UI prüft. Sie liegt in der Klasse `TrainingsabbruchTests` in `test_katalog.py`, deren Fehlschlag-Test `test_sitzung.py` wiederholt. Ihr Abbruch-Test startet aus dem laufenden Gespräch und trägt damit Eigenes bei. Dazu kommen die Endpunkttests der Transkription und die Darstellungstests des geteilten Includes über drei Seiten.

### Nachtrag #394: Beitritt, Freigabe, Fremdeinsicht, Trainingsexport

Die vier Dateien kamen mit #355 nach dem Review oben. Zwei Muster ziehen sich durch:

- **Negative Zusicherungen ohne Status:** Die Helfer `_kuratierseite` und `_abschriftseite` lesen `content.decode()` und prüfen den Status nicht. Ein `assertNotIn` auf so einer Seite besteht auch, wenn sie mit 403 oder 404 antwortet. Diese Helfer bekommen *umschreiben*; die Tests, die sie benutzen, bleiben danach, wie sie sind.
- **Dieselbe Einsichtsregel auf mehreren Ausgaben:** `fremd_einsehbar` speist die Sitzungsansicht, die Tabelle, die Abschriftenliste und den Export. Eine Ausgabe behält einen Fall nur, wenn sie ihn selbst entscheiden könnte. Dazu gehört eine eigene Filterung oder ein eigener Aufruf der Regel. Fälle, die schon durch den Datenzustand feststehen, entfallen.

Die Denkspur-Tests der Sitzungsansicht bleiben alle drei: Fremdeinsicht, Selbsteinsicht und freigegebene Abschrift. Jeder steht für eine Zelle der Matrix aus ADR-0049, und eine künftige Einsicht der Forschenden mit Denkspur (#356) könnte genau an Betrachter oder Anlass unterscheiden. Im Export entscheidet `_markdown` ohne Anlass; dort genügt ein Denkspur-Test.

#### `training/tests/test_beitritt.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| Hilfsfunktion `_konto` | umschreiben | Eigene Kopie des Kontos mit Rolle, wie in `test_freigabe.py` und `test_fremdeinsicht.py` | gemeinsamer Helfer aus #392 |
| Hilfsfunktion `_finale_vignette` | umschreiben | Legt die Fassung über `Vignette.objects._erstellen` an (SLF001-Übergangsliste), ohne gepinnten Kern. | finale Vignette aus #392. Danach fällt die Datei von der Übergangsliste. |
| Hilfsfunktion `_beitritt_url`; Sperre im Aufbau über `training.save(update_fields=["beitritt_gesperrt"])` | behalten | Öffentliches Feld, Testaufbau. Das Sperren über HTTP prüft `TrainingsLinkAufDerKuratierseiteTests`. | – |
| `BeitrittTests::test_jedes_training_hat_einen_eigenen_trainings_link` | streichen | Tautologisch: `default=uuid4, unique=True` ist die Felddefinition. Der Vergleich zweier Feldwerte prüft nichts, was jemand beobachtet. | `test_beitritt_legt_die_bindung_an_und_fuehrt_ins_training`: Der Link führt in sein Training. `GeschlossenesTrainingTests::test_katalog_zeigt_teilnehmenden_nur_beigetretene_trainings`: Ein Beitritt öffnet kein zweites Training. |
| `BeitrittTests::test_beitritt_legt_die_bindung_an_und_fuehrt_ins_training` | behalten | `assertRedirects` lädt die Trainingsseite mit; 200 gibt es dort nur mit Bindung. | – |
| `BeitrittTests::test_erneutes_oeffnen_fuehrt_ohne_fehler_ins_training`, `…::test_erneutes_oeffnen_zaehlt_nicht_doppelt` | behalten | Wiederholbarkeit des Beitritts, über die Seite gezählt | – |
| `BeitrittTests::test_ohne_login_fuehrt_der_link_ueber_den_login_zurueck`, `…::test_login_kehrt_zum_beitritt_zurueck_und_fuehrt_ins_training` | behalten | Zwei Hälften eines Wegs: Hinleitung zum Login und Rückkehr danach | – |
| `BeitrittTests::test_gesperrter_link_meldet_die_sperre`, `…::test_gesperrter_link_laesst_niemanden_beitreten`, `…::test_gesperrter_link_fuehrt_beigetretene_weiter_ins_training`, `…::test_gesperrter_link_fuehrt_den_kreis_ins_training`, `…::test_gesperrter_link_fuehrt_die_administration_ins_training` | behalten | Die Sperre aus Sicht jeder Rolle, Meldung als Literal | – |
| `BeitrittTests::test_gesperrter_link_bindet_den_kreis_nicht` | behalten | Den offenen Fall prüft kein Test. Dort bindet die View den Kreis heute doch; was gelten soll, entscheidet #410. | – |
| `BeitrittTests::test_link_eines_entwurfs_ist_unbekannt`, `…::test_leeres_training_laesst_sich_veroeffentlichen_und_beitreten` | behalten | – | – |
| `GeschlossenesTrainingTests::test_katalog_zeigt_teilnehmenden_nur_beigetretene_trainings` | behalten | Der Gegenfall zu `test_katalog.py::…::test_zeigt_beigetretene_trainings_im_katalog_und_in_der_navigation`: Ein veröffentlichtes fremdes Training fehlt. | – |
| `GeschlossenesTrainingTests::test_katalog_ohne_beitritt_ist_leer` | streichen | Schichtdoppelung in derselben Klasse: Dass ein veröffentlichtes Training ohne Bindung fehlt, zeigt schon „Fremdes Seminar“ im Test darüber. | `test_katalog_zeigt_teilnehmenden_nur_beigetretene_trainings` |
| `GeschlossenesTrainingTests::test_detail_wahl_und_start_ohne_bindung_liefern_404`, `…::test_beigetretene_erreichen_detail_und_wahl`, `…::test_kreis_und_administration_erreichen_das_training_ohne_beitritt` | behalten | Die Zugangsregel aus ADR-0049 über alle Einstiege | – |
| `GeschlossenesTrainingTests::test_bestehende_bindung_gilt_als_beitritt` | streichen | Besteht per Konstruktion: Eine Bindung „aus der Zeit vor dem Trainings-Link“ ist dieselbe Zeile, die der Beitritt anlegt. `zugaenglich_fuer` kann sie nicht unterscheiden. | `test_beigetretene_erreichen_detail_und_wahl` und `test_katalog_zeigt_teilnehmenden_nur_beigetretene_trainings` |
| `GeschlossenesTrainingTests::test_trainingsseite_zeigt_den_festen_hinweis_zur_fremdeinsicht` | behalten | Zusage aus ADR-0049, Text als Literal | – |
| `TrainingsLinkAufDerKuratierseiteTests::test_kuratierseite_zeigt_den_link_zum_kopieren` | behalten | „Kopieren“ belegt nur den Knopf; die Zwischenablage beobachtet pytest nicht. | – |
| `TrainingsLinkAufDerKuratierseiteTests::test_ko_eigentuemerin_sperrt_den_beitritt`, `…::test_ko_eigentuemerin_oeffnet_den_gesperrten_beitritt`, `…::test_fremde_ausbilderin_kann_den_beitritt_nicht_umschalten`, `…::test_fremder_umschaltversuch_laesst_den_beitritt_offen`, `…::test_umschalten_nur_per_post` | behalten | Der Abweisungstest mit Folgeprüfung hält fest, dass vor dem Schreiben geprüft wird. | – |
| `TrainingsLinkAufDerKuratierseiteTests::test_band_eines_entwurfs_vertroestet_auf_das_veroeffentlichen`, `…::test_band_zaehlt_die_beigetretenen`, `…::test_gesperrtes_band_nennt_eine_beigetretene_person_in_der_einzahl` | behalten | Mehrzahl im offenen Band, Einzahl im gesperrten Band, je ein Zweig des Templates | – |
| `TrainingsLinkAufDerKuratierseiteTests::test_band_nennt_eine_beigetretene_person_in_der_einzahl` | streichen | Schichtdoppelung in derselben Datei: „1 Person beigetreten“ erwartet schon `test_erneutes_oeffnen_zaehlt_nicht_doppelt`. | `BeitrittTests::test_erneutes_oeffnen_zaehlt_nicht_doppelt` |

#### `training/tests/test_freigabe.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| Hilfsfunktionen `_konto`, `_finale_vignette` | umschreiben | Öffentlicher Weg, aber Kopien derselben Helfer in `test_fremdeinsicht.py` | gemeinsame Helfer aus #392 |
| Hilfsfunktion `_abschrift` | behalten, verlegen | `Abschrift`, `Sitzung` usw. per `objects.create` sind Testaufbau. Die Freigabe hängt nicht daran, wie die Abschrift entstand; `abschrift_holen` bräuchte eine ganze Erhebung. `test_export.py` importiert den Helfer aus diesem Testmodul. | in ein gemeinsames Aufbaumodul der Trainingstests (siehe Querschnitt) |
| Hilfsfunktionen `_sitzung`, `_ansehen_url`, `FreigabeTestCase._freigeben`, `…._status_fuer` | behalten | – | – |
| `FreigabeTestCase._abschriftseite`, `…._kuratierseite` | umschreiben | Lesen `content.decode()` ohne Status. Die negativen Zusicherungen der Datei bestehen dann auch auf einer Fehlerseite. | Der Helfer prüft Status 200, bevor er den Text liefert. |
| `FreigebenTests::test_freigabe_leitet_zur_abschriftseite_zurueck`, `…::test_freigabe_fuer_ein_training_ohne_eigene_bindung_wird_abgewiesen`, `…::test_abgewiesene_freigabe_oeffnet_keine_fremdeinsicht`, `…::test_fremde_abschrift_laesst_sich_nicht_freigeben`, `…::test_abgewiesene_freigabe_laesst_die_bisherige_freigabe_stehen`, `…::test_freigeben_verlangt_post`, `…::test_abschrift_laesst_sich_fuer_mehrere_trainings_freigeben` | behalten | Kommando und Abweisungen über HTTP und die Wirkung auf die Einsicht | – |
| `FreigebenTests::test_freigabe_mit_unlesbarer_auswahl_wird_abgewiesen`, `…::test_freigabe_mit_hochgestellter_ziffer_wird_abgewiesen` | behalten | Grenzfälle der Auswahl: `"²".isdigit()` ist wahr, `int("²")` scheitert. Beide ließen sich parametrisieren, das ist aber kein Befund. | – |
| `FreigebenTests::test_freigabe_gelingt_unabhaengig_von_den_vignetten_des_trainings` | streichen | Schichtdoppelung: Das Training des `FreigabeTestCase` ist immer leer. Freigeben und Lesen prüfen mehrere Tests der Datei, mit Inhalt statt nur 200. | `FremdeinsichtInAbschriftenTests::test_kreis_liest_die_freigegebene_sitzung_samt_fremder_szene` |
| `FreigebenTests::test_abschriftseite_bietet_nur_beigetretene_trainings_an` | umschreiben | Die positive Hälfte besteht per Konstruktion: „Bruchrechnung“ steht schon im Erhebungsnamen „Studie Bruchrechnung“ im Seitenkopf. | Die Checkbox des Trainings über `assertContains(…, '<label><input type="checkbox" name="training" value="<pk>"> Bruchrechnung</label>', html=True)`. „Anderes Seminar“ fehlt weiterhin. |
| `FreigebenTests::test_abschriftseite_zeigt_die_aktuelle_freigabe_angehakt` | umschreiben | `f'value="{pk}" checked'` legt die Reihenfolge der Attribute fest. | Dasselbe Element mit `checked` über `assertContains(…, html=True)` |
| `FreigebenTests::test_abschriftseite_zeigt_ohne_freigabe_nichts_angehakt` | umschreiben | `"checked" not in` über die ganze Seite und ohne Status | Positiv: Die Checkbox steht ohne `checked` in der Seite, über `assertContains(…, html=True)`. |
| `FreigebenTests::test_abschriftseite_nennt_die_freigegebenen_trainings_im_kopf`, `…::test_private_abschrift_bleibt_im_kopf_privat` | behalten | Kopfzeile als Literal | – |
| `FreigebenTests::test_abschriftseite_ohne_beitritt_bietet_keine_freigabe_an` | umschreiben | Prüft nur eine Abwesenheit. Dafür überschreibt er `self.abschrift` und `self.teilnehmerin`, um den Helfer zu nutzen. | Positiv den Hinweis „Sie sind noch keinem Training beigetreten.“ erwarten. „Freigaben speichern“ fehlt weiterhin. Die Seite wird direkt für das zweite Konto geladen. |
| `FreigebenTests::test_abschriftseite_nennt_keinen_export` | streichen | Prüft, dass etwas nie Gebautes fehlt (Entscheidung aus #362). Jedes harmlose „Export“ auf der Seite bräche ihn. | Kein Ersatz nötig. Die Entscheidung steht in `docs/verhalten.md`. |
| `FreigebenTests::test_widerruf_beendet_die_fremdeinsicht_sofort` | behalten | – | – |
| `FreigebenTests::test_widerruf_entfernt_die_abschrift_aus_der_kuratierseite` | streichen | Besteht durch den Datenzustand: Nach dem Widerruf ist die Abschrift so privat wie nie freigegeben. Dass der Widerruf wirkt, zeigt der Test darüber. | `test_widerruf_beendet_die_fremdeinsicht_sofort` und `FremdeinsichtInAbschriftenTests::test_private_abschrift_fehlt_auf_der_kuratierseite` |
| `FreigebenTests::test_loeschen_der_abschrift_beendet_die_fremdeinsicht` | streichen | Besteht durch den Datenzustand: Nach dem Löschen gibt es die Sitzung nicht mehr, jeder Aufruf ergibt 404. | `test_abschriften.py::test_loeschen_entfernt_abschrift_teilnahme_und_kopierte_sitzungen` |
| `FremdeinsichtInAbschriftenTests::test_private_abschrift_ist_fuer_den_kreis_nicht_einsehbar`, `…::test_private_abschrift_ist_fuer_die_administration_nicht_einsehbar` | behalten | Zelle „Abschrift, Fremdeinsicht“ der Matrix | – |
| `FremdeinsichtInAbschriftenTests::test_private_abschrift_fehlt_auf_der_kuratierseite`, `…::test_kuratierseite_meldet_wenn_niemand_freigegeben_hat` | behalten | Nach dem Umschreiben von `_kuratierseite` | – |
| `FremdeinsichtInAbschriftenTests::test_freigegebene_abschrift_steht_mit_name_erhebung_und_importzeit` | umschreiben | „Grace Hopper“ steht auch als Zeile der Tabelle darüber. Das Datum rechnet `astimezone()` in der Zeitzone des Prozesses nach, nicht in `TIME_ZONE`; das Template zeigt außerdem die Uhrzeit. | Mit `time-machine` zu einem festen Zeitpunkt importieren, etwa 2026-07-02 00:30 Europe/Berlin. Erwartet sind `<th scope="row">Grace Hopper</th>`, `<td>Studie Bruchrechnung</td>` und `<td>02.07.2026 00:30</td>` über `assertContains(…, html=True)`. |
| `FremdeinsichtInAbschriftenTests::test_administration_findet_die_freigegebene_abschrift_unter_der_tabelle`, `…::test_freigegebene_abschrift_verlinkt_ihre_abgeschlossene_sitzung`, `…::test_nicht_abgeschlossene_sitzung_der_abschrift_ist_nicht_verlinkt` | behalten | Die Abschriftenliste filtert selbst über die Freigabe. Der letzte Test prüft zusätzlich die Ansicht (404). | – |
| `FremdeinsichtInAbschriftenTests::test_freigegebene_abschriften_stehen_nach_namen_sortiert` | umschreiben | Besteht per Konstruktion: Beide Personen sind beigetreten, und die Tabelle darüber sortiert dieselben Namen. `seite.index` findet zuerst die Tabelle. | Die Reihenfolge nur im Teil ab „Freigegebene Abschriften“ prüfen. |
| `FremdeinsichtInAbschriftenTests::test_kreis_liest_die_freigegebene_sitzung_samt_fremder_szene`, `…::test_freigegebene_sitzung_verschweigt_die_denkspur`, `…::test_administration_liest_die_freigegebene_sitzung`, `…::test_fremder_kreis_liest_die_freigegebene_sitzung_nicht` | behalten | Die Sitzungsansicht für den Anlass Abschrift, dritte Ausnahme von ADR-0015 | – |
| `FremdeinsichtInAbschriftenTests::test_fremde_vignette_bleibt_ausserhalb_des_vignettenbestands`, `…::test_fremde_vignette_fehlt_in_der_vignettenliste_des_kreises`, `…::test_fremde_vignette_ist_im_detail_nicht_erreichbar` | behalten | Die Freigabe öffnet den Bestand nicht. Der erste Docstring spricht von der Kuratierseite, der Test schickt aber den POST. Die Prüfung ist richtig, nur der Docstring ungenau. | – |
| `FremdeinsichtInAbschriftenTests::test_eigene_abschrift_bleibt_der_trainings_sitzungsansicht_fremd` | behalten | – | – |

#### `training/tests/test_fremdeinsicht.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| Hilfsfunktionen `_konto`, `_finale_vignette`; aktive Modell-Konfiguration in `FremdeinsichtTestCase.setUp` | umschreiben | Kopien, siehe `test_freigabe.py` | gemeinsame Helfer aus #392 |
| Hilfsfunktion `_gespielte_sitzung`, Klasse `FremdeinsichtTestCase` | behalten, verlegen | Testaufbau über `objects.create`. Ein gespielter Ablauf über HTTP bräuchte Fake-Skripte und ergäbe dieselben Zeilen. `test_export.py` importiert beide aus diesem Testmodul. | in ein gemeinsames Aufbaumodul der Trainingstests (siehe Querschnitt) |
| Hilfsfunktion `_ansehen_url`, `SitzungAnsehenTests._status_fuer` | behalten | – | – |
| `FremdeinsichtTabelleTests._kuratierseite` | umschreiben | Wie in `test_freigabe.py`: kein Status | Der Helfer prüft Status 200. |
| `SitzungAnsehenTests::test_kreismitglied_liest_eine_abgeschlossene_sitzung`, `…::test_kreismitglied_liest_die_abgegebene_diagnose` | behalten | – | – |
| `SitzungAnsehenTests::test_ko_eigentuemerin_liest_eine_abgeschlossene_sitzung` | streichen | Derselbe Datenzustand wie im Test darunter: Ein zweites Kreismitglied und eine Sitzung bestehen; nur die Reihenfolge des Aufbaus unterscheidet sich, und die Regel kennt keine Zeit. | `test_neues_kreismitglied_liest_auch_aeltere_sitzungen` |
| `SitzungAnsehenTests::test_neues_kreismitglied_liest_auch_aeltere_sitzungen`, `…::test_ausgetretenes_kreismitglied_bekommt_404`, `…::test_administration_liest_eine_abgeschlossene_sitzung`, `…::test_fremdes_konto_bekommt_404`, `…::test_autorin_der_vignette_bekommt_404`, `…::test_nicht_abgeschlossene_sitzungen_bleiben_dem_kreis_verborgen`, `…::test_sitzung_in_einem_fremden_training_bleibt_verborgen` | behalten | Die Fälle der Einsichtsregel an der Ansicht, die sie durchsetzt. Hier gilt der Fall „fremdes Training“ zu Recht für einen fremden Kreis: Gegen diese Ansicht schützt allein die Sichtbarkeit. | – |
| `SitzungAnsehenTests::test_fremdeinsicht_verschweigt_die_denkspur` | behalten | Zelle „Training, Fremdeinsicht“ (siehe oben) | – |
| `SitzungAnsehenTests::test_fremdeinsicht_ist_rein_lesend` | umschreiben | `assertNotIn` auf `content.decode()` ohne Status. Auf einer 404 bestünde er. | `assertNotContains` für jedes Bedienelement; das prüft zugleich Status 200. |
| `SelbsteinsichtTests::test_eigene_sitzung_ist_in_jedem_status_lesbar`, `…::test_selbsteinsicht_verschweigt_die_denkspur` | behalten | Die Schleife über `Sitzung.Status` benennt die Zustände, sie rechnet nichts nach. `test_sitzung.py` prüft die Selbsteinsicht nur abgeschlossen. | – |
| `FremdeinsichtTabelleTests::test_beigetretene_ohne_sitzung_erscheinen_als_zeile`, `…::test_abgeschlossene_sitzung_ist_verlinkt`, `…::test_zeilen_sind_nach_namen_sortiert`, `…::test_training_ohne_beigetretene_zeigt_eine_leerzeile`, `…::test_leeres_training_zeigt_einen_hinweis_statt_der_tabelle` | behalten | – | – |
| `FremdeinsichtTabelleTests::test_vignetten_des_trainings_sind_die_spalten`, `…::test_spalten_folgen_der_kuratierreihenfolge` | behalten | `title="…"` ist der Tooltip gekürzter Spaltenköpfe. Er ist auch der einzige Weg, den Spaltenkopf von der Vignettenliste derselben Seite zu unterscheiden. „Addition“ vor „Brüche addieren“ trennt Kuratier- von alphabetischer Reihenfolge. | – |
| `FremdeinsichtTabelleTests::test_nicht_abgeschlossene_sitzung_ist_nicht_verlinkt` | behalten | Nach dem Umschreiben von `_kuratierseite`. Die Tabelle ruft die Regel selbst auf; das ist ihr einziger Statusfall. | – |
| `FremdeinsichtTabelleTests::test_sitzung_in_einem_fremden_training_ist_nicht_verlinkt` | streichen | Besteht per Konstruktion: Die Zellen füllt die Tabelle nur über die Teilnahmen der Bindungen dieses Trainings. Die Sitzung im fremden Training hängt an einer anderen Teilnahme. | `SitzungAnsehenTests::test_sitzung_in_einem_fremden_training_bleibt_verborgen` |
| `FremdeinsichtTabelleTests::test_sitzungen_sind_je_vignette_nummeriert_und_datiert` | umschreiben | Das erwartete Datum rechnet `timezone.localtime(…).strftime` nach, wie das Template. Beide Sitzungen tragen dasselbe Datum, also bleibt offen, ob die Nummern der zeitlichen Folge folgen. | Mit `time-machine` die erste Sitzung am 01.07.2026, die zweite am 02.07.2026 um 00:30 Europe/Berlin anlegen. Erwartet sind `aria-label="Sitzung vom 01.07.2026">1</a>` und `aria-label="Sitzung vom 02.07.2026">2</a>`. |
| `FremdeinsichtTabelleTests::test_nummerierung_beginnt_je_vignette_neu` | behalten | `'">1</a>'` ist eng am Markup. Ohne Neubeginn stünde aber „3“ in der Zelle, und der Test schlüge fehl. | – |

#### `training/tests/test_export.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| Import von `_abschrift`, `FremdeinsichtTestCase`, `_gespielte_sitzung` und `_konto` aus den Testmodulen `test_freigabe` und `test_fremdeinsicht` | umschreiben | Koppelt drei Testmodule. `FremdeinsichtTestCase` landet zusätzlich im Namensraum dieses Moduls. | aus dem gemeinsamen Aufbaumodul der Trainingstests bzw. aus #392 (siehe Querschnitt) |
| Hilfsfunktionen `_export`, `_freigeben`, `_archiv`, `_ordner`; Mailadresse im `setUp` | behalten | `_archiv` prüft den Status. Der Trainingsexport ist keine Datenspur, der Export-Helfer aus #391 (ADR-0029) passt nicht. | – |
| `ZugriffTests::test_kreis_laedt_ein_zip_herunter`, `…::test_administration_laedt_den_export`, `…::test_fremde_ausbilderin_bekommt_404`, `…::test_neues_kreismitglied_laedt_auch_aeltere_sitzungen`, `…::test_ausgetretenes_kreismitglied_bekommt_404`, `…::test_autorin_der_vignette_bekommt_404`, `…::test_teilnehmerin_bekommt_403`, `…::test_kuratierseite_bietet_den_export_an` | behalten | Zugriff über `_sichtbares_training` und die Rolle, eigene Fehlerfälle der Route | – |
| `ZugriffTests::test_ko_eigentuemerin_laedt_den_export` | streichen | Wie in `test_fremdeinsicht.py`: derselbe Zustand wie beim neuen Kreismitglied, dort mit Inhalt geprüft | `test_neues_kreismitglied_laedt_auch_aeltere_sitzungen` |
| `ZugriffTests::test_dateiname_nennt_training_und_zeitpunkt` | umschreiben | Die Erwartung rechnet `slugify` nach, wie `zip_download`. Den Zeitstempel prüft nur ein Regex, ob UTC und Abrufzeit stimmen, merkt der Test nicht. | Wie beim Erhebungsexport (`erhebungen-forschung.md`): `time-machine` auf 2026-07-01 10:00 Europe/Berlin, erwartet `filename="training-<pk>-bruchrechnung-20260701T080000Z.zip"` als Literal (#349). |
| `InhaltTests::test_je_abgeschlossener_sitzung_eine_markdown_datei` | streichen | Vom Test zwei darunter mitbewiesen: Die Zählung läuft je Ordner. Lägen die Sitzungen in zwei Ordnern, hießen beide `01-…`. | `test_dateien_sind_gezaehlt_und_nach_der_vignette_benannt` |
| `InhaltTests::test_je_person_ein_eigener_ordner`, `…::test_dateien_sind_gezaehlt_und_nach_der_vignette_benannt` | behalten | Literale Dateinamen | – |
| `InhaltTests::test_ordner_heissen_nach_kennzeichen`, `…::test_zwei_exporte_ziehen_verschiedene_kennzeichen` | behalten | Das Kennzeichen ist Zufall. Die Form als Regex und die Verschiedenheit sind alles, was sich festlegen lässt. | – |
| `InhaltTests::test_datei_enthaelt_vignette_ausgang_transkript_und_diagnose` | umschreiben | Prüft nur Bruchstücke per `assertIn`. Die Zeile „Datum“ belegt kein Test positiv. | Mit `time-machine` die Sitzung am 2026-07-02 00:30 Europe/Berlin anlegen. Die ganze Datei als Literal erwarten, mit `- Datum: 02.07.2026`. Das belegt Aufbau, Reihenfolge und Ortszeit. |
| `InhaltTests::test_sitzung_ohne_zeitstempel_kommt_ohne_datum_hinaus` | behalten | Anders als `test_bestandsdaten_duerfen_ohne_entstehungszeitpunkt_bestehen` (oben gestrichen) prüft er keine Felddefinition, sondern eine Verzweigung des Exports. Bestandszeilen von vor `sitzungen.0007` sind weiter möglich. | – |
| `InhaltTests::test_schritt_ohne_aeusserung_ist_als_solcher_markiert`, `…::test_sitzung_ohne_diagnose_ist_als_solche_markiert`, `…::test_transkript_wechselt_eingabe_und_aeusserung` | behalten | Grenzfälle der Datei, Literale | – |
| `InhaltTests::test_nicht_abgeschlossene_sitzungen_fehlen`, `…::test_sitzung_in_einem_fremden_training_fehlt` | behalten | Der Export ruft die Regel selbst mit seinem Training auf. Ein falsches Argument fiele hier auf. | – |
| `InhaltTests::test_kein_kontoname_und_keine_mailadresse`, `…::test_keine_denkspur_und_keine_fehlversuche` | behalten | Zusage „pseudonym“ aus ADR-0049 | – |
| `AbschriftTests::test_freigegebene_abschrift_liegt_als_unterordner_bei_der_person`, `…::test_erhebungsname_bricht_nicht_aus_dem_ordner_aus`, `…::test_private_abschrift_fehlt`, `…::test_abschrift_ohne_einsehbare_sitzung_belegt_keinen_ordnernamen` | behalten | – | – |
| `AbschriftTests::test_abschrift_geht_ohne_denkspur_hinaus` | streichen | Schichtdoppelung: `_markdown` schreibt jede Sitzung gleich, der Anlass geht nicht ein. | `InhaltTests::test_keine_denkspur_und_keine_fehlversuche` |
| `AbschriftTests::test_widerrufene_abschrift_fehlt` | streichen | Besteht durch den Datenzustand: Widerrufen ist so privat wie nie freigegeben. | `test_private_abschrift_fehlt` und `test_freigabe.py::FreigebenTests::test_widerruf_beendet_die_fremdeinsicht_sofort` |
| `AbschriftTests::test_nicht_abgeschlossene_sitzung_der_abschrift_fehlt` | streichen | `fremd_einsehbar` filtert den Status für beide Anlässe in einem Filter. Der Export kann ihn nicht je Anlass anders anwenden. | `InhaltTests::test_nicht_abgeschlossene_sitzungen_fehlen` und `test_abschrift_ohne_einsehbare_sitzung_belegt_keinen_ordnernamen`: Dessen abgebrochene Abschrift geht nicht hinaus. |
| `AbschriftTests::test_zwei_abschriften_derselben_erhebung_bleiben_getrennt` | umschreiben | Prüft nur, dass es zwei Ordner gibt, nicht wie sie heißen | Literale Unterordner `<kennzeichen>/studie-bruchrechnung/` und `<kennzeichen>/studie-bruchrechnung-2/` |

## Querschnitt für die Umsetzung

- **Gemeinsamer Helfer für Vignetten:** 15 Stellen in `training/tests/` legen Vignetten über `Vignette.objects._erstellen` an, zwölf finale und drei Entwürfe (`test_models.py` zweimal, `test_views.py` einmal); für die Entwürfe reicht `Vignette.objects.anlegen(konto)`. Deshalb stehen `test_katalog.py`, `test_models.py`, `test_sitzung.py`, `test_transkription.py` und `test_views.py` auf der SLF001-Übergangsliste. Das öffentliche Muster steht in `training/tests/test_abschriften.py::_finale_vignette_anlegen`. Ein geteilter Helfer, wie für #332 vorgeschlagen, ersetzt alle Stellen; danach fallen die fünf Dateien von der Liste.
- **Session-Schlüssel sind privat:** Kein Test liest `session["probelauf"]`. Bei `training_sitzung_pk` bleibt eine begründete Ausnahme (Wettlauf in `test_abbrechen_setzt_den_gewollten_status_ohne_diagnose`).
- **Zeilenlink-Tabellen:** Drei der vier Tests `*_verlinkt` (Katalog, Ausbilder-Liste, Historie) prüfen dasselbe Alpine-Template als Quelltext; der Abschriften-Test prüft gerendertes Markup samt Klassen. Nach dem Umschreiben prüft jeder nur seine Zeilendaten.
- **Aufbaumodul der Trainingstests (Nachtrag #394):** `test_export.py` importiert `_abschrift` aus `test_freigabe.py` sowie `FremdeinsichtTestCase`, `_gespielte_sitzung` und `_konto` aus `test_fremdeinsicht.py`. `_abschrift`, `FremdeinsichtTestCase` und `_gespielte_sitzung` kommen nur im Training vor und gehören deshalb nicht in die app-übergreifenden Helfer aus #392. Sie ziehen in ein Modul neben den Tests, etwa `training/tests/aufbau.py`. Konto, aktive Modell-Konfiguration und finale Vignette kommen aus #392, auch für `_konto`. Danach fällt `test_beitritt.py` von der SLF001-Übergangsliste.
- **`time-machine` (Nachtrag #394):** Drei Zieltests des Nachtrags brauchen eine feste Uhr, ohne heute etwas zu patchen: Importzeit der Abschriftenliste, Datum in der Tabelle und Datum in der Exportdatei. Wie bei `test_kopierte_sitzungen_tragen_die_importzeit` gehören sie in die Umsetzung (#404), nicht in #349. Der Dateiname des Exports folgt #349 wie beim Erhebungsexport. `time-machine` ist noch keine Abhängigkeit; das Ticket, das zuerst landet, nimmt sie auf.

## Lücken (kein Anti-Pattern, für die Umsetzung)

- `training:historie`: Fortschritt („x / y“) und Sitzungen nach Status sind ungetestet. Die beiden vorhandenen Tests rufen die Seite leer bzw. ohne Trainingsbindung auf.
- `training:katalog` für Ausbilder:innen: Eigene Entwürfe mit „Kuratieren“ statt „Öffnen“ sind ungetestet.
- `abschrift_holen` kopiert `verbrauchte_zeit` und die Eingabemodi; keiner dieser Werte ist geprüft.
- `abschrift_holen` normalisiert das Token (`strip().upper()`). Alle Tests benutzen ein Token aus Ziffern und Bindestrich ohne Leerraum, die Normalisierung ist deshalb ungeprüft. Zieltest: Ein Token mit Buchstaben, in Kleinschreibung und mit Leerraum eingegeben, holt die Abschrift.
- Nachtrag #394: Die Datumszeile der Exportdatei belegt kein Test positiv; der Zieltest von `test_datei_enthaelt_vignette_ausgang_transkript_und_diagnose` schließt die Lücke.
- Nachtrag #394: Dass der offene Trainings-Link Kreis und Administration bindet, prüft kein Test. Was dort gelten soll, entscheidet #410.

## Folge-Issues

- #378 Zyklische Kante: `simulation/__init__.py` importiert `vignetten.models` entgegen ADR-0016. Blockiert das Zusammenlegen der Importgraph-Wächter.
- #410 (Nachtrag #394) Der offene Trainings-Link legt auch für Kreis und Administration eine Trainingsbindung an. Danach stehen sie als Beigetretene in Band, Tabelle und Export. Der gesperrte Link bindet sie nicht, und `docs/verhalten.md` sagt „ohne Beitritt“.

Weitere Probleme im Produktionscode haben weder das Review noch sein Nachtrag gefunden. `ScratchSink` hat keine öffentliche Lesestelle für den Budgetstand. Das ist kein Mangel: Der Budgetstand wird über den `Ausgang` beobachtet, und die Zieltests oben tun das.
