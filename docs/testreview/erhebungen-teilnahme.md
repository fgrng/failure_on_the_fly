# Testreview: Erhebungen – Teilnahme, Ablauf und Modelle

Bereich aus #327 (Spec #321). Geprüft sind `erhebungen/tests/test_teilnahme.py`, `test_teilnahme_gestaltung.py`, `test_ablauf.py`, `test_transkription.py` und `test_models.py`. Die View-Tests der Forschenden-Sicht (`test_forschenden_views.py`) gehören zu #326. Hier sind sie nur als Ersatztests genannt.

Für die Zeit gilt #324: Wer `sitzungen.durchlauf.jetzt` oder `erhebungen.models.timezone.now` patcht, bekommt *umschreiben*, umgesetzt in #349 (siehe Startbefund 2). Für Migrationstests gilt #325: Drei Tests in `test_models.py` werden gestrichen.

Drei Lesarten gelten für das ganze Dokument:

- **Zustand nach dem Request:** Ein HTTP-Test darf den Zustand nach dem Request über die öffentliche Modell-API lesen (`refresh_from_db()`, Attribute, `objects.get()`). Bei der Erhebung ist die Datenbank die Ausgabe: Der Export liest Sitzungen, Schritte, Diagnosen, Item-Antworten und Ziehungen. Eine Zusicherung auf diese Zeilen ist deshalb keine „DB-Abfrage statt Schnittstelle“. Das Urteil fällt, wenn sie Verhalten einer anderen Schicht wiederholt oder wenn eine Seite den Zustand selbst zeigt; dann liest der Zieltest ihn dort (wie #326 und #328).
- **Choice-Mitglieder als Erwartung:** `Sitzung.Status.ABGESCHLOSSEN`, `Eingabemodus.GETIPPT` oder `Stichprobe.Phase.VOR` als Erwartung bleiben stehen, wenn der Test prüft, *welcher* Zustand entsteht. Die Schreibweise der gespeicherten Werte sichert der Export-Kontrakt (ADR-0029). Ein Literal braucht es nur, wo die Schreibweise selbst die Zusage ist. Das ist in diesem Bereich nirgends der Fall.
- **„Debrief“ ist ein schwacher Beleg:** Die Gesprächsseite trägt in der Aktionszeile den Satz „Genug gefragt? Danach folgt der Debrief mit Ihrer Diagnose.“ `assertContains(antwort, "Debrief")` besteht deshalb auch, wenn statt des Debriefs die Gesprächsseite kommt. Das hat schon #330 für das Training festgestellt. Wo diese Zusicherung der Beleg für den Debrief ist, lautet das Urteil *umschreiben*. Ziel: „Was ist Ihnen aufgefallen?“ erwarten, und wo nötig „Ihre nächste Frage“ ausschließen.

## Schnittstelle

### Modelle (`erhebungen/models.py`)

#### Erhebung

- **Aufrufe:**
  - Der Eigentümer-Kreis aus `konten/eigentuemerschaft.py` (`objects.anlegen(konto, **felder)`, `objects.sichtbar_fuer(konto)`, `austreten`, `ist_aktiv()`). Die Rollengruppe ist Forschende:r.
  - Lebenszyklus: `finalisieren()`, `zurueckziehen()`, `archivieren()`, `entarchivieren()`, `delete()`.
  - Lesende Eigenschaften: `kann_zurueckgezogen_werden`, `kann_archiviert_werden`, `kann_entarchiviert_werden`, `hat_laufende_stichprobe`.
  - Relationen: `vignettenzugehoerigkeiten`, `itemzugehoerigkeiten`, `stichprobe_set`, `vignetten`.
- **Invarianten:**
  - Eine neue Erhebung ist ein Entwurf. Zustandswechsel und das Setzen von `modell_konfiguration` laufen nur über die Lebenszyklus-Methoden, auch nicht über `QuerySet.update`.
  - Finale und archivierte Erhebungen sind eingefroren (`save()` und `update`). Der Eigentümer-Kreis bleibt änderbar.
  - `finalisieren()` pinnt die belegte Modell-Konfiguration für `Verwendung.SCHUELERIN`, nicht die für Lehrperson oder Bewerter. `zurueckziehen()` und erneutes Finalisieren pinnen neu. Archivieren und Entarchivieren lassen den Pin stehen.
  - Zurückziehen geht nur ohne nicht archivierte und ohne datentragende Stichprobe. Archivieren und Entarchivieren gehen nur ohne laufende Stichprobe. Entarchivieren braucht eine Eigentümerin.
  - Physisch gelöscht werden nur Entwürfe, einzeln wie gesammelt. Die Zuordnungen gehen mit.
- **Fehlerfälle:** Alle Verstöße werfen `ValidationError` mit lesbarer Meldung.
- **Konfiguration:** die belegte `ModellKonfiguration` für `Verwendung.SCHUELERIN`.

#### Zuordnungen: Erhebungsvignette und Erhebungsitem

- **Aufrufe:** `objects.create`, `save()`, `QuerySet.update`, `QuerySet.delete`. Positionen und Andockpunkte setzen die Forschenden-Views.
- **Invarianten:**
  - Zuordnungen ändern sich nur, solange die Erhebung ein Entwurf ist (ADR-0027). Das gilt auf jedem Schreibweg.
  - Eingebunden werden nur finale Fassungen aus einer Historie, deren Kreis sich mit dem der Erhebung schneidet. Das prüft `clean()` und, für Massen-Inserts, die Datenbank.
  - Eine Vignette steht je Erhebung einmal, jede Position einmal. Auch bei zufälliger Reihenfolge bleibt die Position gespeichert. Ein Item steht je Andockpunkt einmal, jede Position je Andockpunkt einmal.
  - Sortierung: Vignetten nach Position, Items nach Andockpunkt und Position. Eingebundene Fassungen sind gegen Löschen geschützt (`PROTECT`).
- **Fehlerfälle:** `ValidationError` aus `clean()`, `IntegrityError` aus Constraints und Triggern, `ProtectedError` beim Löschen einer eingebundenen Fassung.
- **Konfiguration:** keine.

#### Stichprobe

- **Aufrufe:** `objects.create(erhebung, beginn, ende)`, `archivieren()`, `phase`, `traegt_daten`, `teilnahme_link` (UUID, eindeutig, nicht editierbar).
- **Invarianten:** `phase` ist `vor`, `laufend` oder `nach`, gemessen an der Systemzeit. Die Grenzen `beginn` und `ende` zählen zu `laufend`. Eine Stichprobe wird nicht archiviert angelegt und nur über `archivieren()` archiviert, und nur ohne Daten.
- **Fehlerfälle:** `ValidationError` bei bereits archivierter oder datentragender Stichprobe und bei `archiviert` über `save()` (auch beim Anlegen) oder über `update`.
- **Konfiguration:** keine.

#### Erhebungsbindung

- **Aufrufe:** `objects.anlegen(stichprobe)`, `vignetten_ziehen()`, `verfallen`. Felder: `token`, `randomisierungs_seed`, `abgeschlossen_am`, `erstellt_am`.
- **Invarianten:**
  - `anlegen` legt eine frische `Teilnahme` an und vergibt ein Token im Format `XXXX-XXXX` aus `23456789ABCDEFGHJKMNPQRSTVWXYZ`. Bei einer Kollision zieht es neu.
  - Eine Teilnahme hat genau eine Bindung. Die Exklusivität gegen Trainingsbindung und Abschrift liegt in `sitzungen.bindungen` (#330).
  - `vignetten_ziehen()` schreibt die Reihenfolge genau einmal fest. Bei zufälliger Reihenfolge wird der Seed einmal gezogen und gespeichert, die Ziehung folgt `Random(seed).shuffle` über die Liste in Positionsreihenfolge. Die Positionen der Erhebung bleiben dabei unberührt.
  - `verfallen` ist wahr, wenn die Stichprobe vorbei und die Bindung nicht abgeschlossen ist. Die Eigenschaft hat keinen Aufrufer (#384).
- **Fehlerfälle:** keine eigenen.
- **Konfiguration:** keine.

#### Vignettenziehung, Itemblock, ItemAntwort

- **Aufrufe:** Geschrieben werden sie nur vom Ablauf (`erhebungen/ablauf.py`). `Itemblock.antwortzeilen()` liefert die Antwortzeilen in Item-Reihenfolge.
- **Invarianten:**
  - Je Teilnahme steht jede Position und jede Vignette einmal in der Ziehung.
  - Je Teilnahme gibt es einen Itemblock je Sitzung und einen am Ende. Die Sitzung passt zum Andockpunkt.
  - Je Itemblock gibt es eine Antwortzeile je Item. Eine Antwort trägt höchstens einen Wert, der Wert passt zum Item-Typ, eine Likert-Stufe liegt auf der Skala. Die Sitzung gehört zur selben Teilnahme und nur zu Items nach der Sitzung. Eine leere Zeile ist eine gültige Nicht-Antwort.
- **Fehlerfälle:** `ValidationError` aus `ItemAntwort.clean()` (läuft in `save()`), `IntegrityError` aus den Constraints.
- **Konfiguration:** die Skala aus `LikertSkalenpol`.

### Ablauf (`erhebungen/ablauf.py`)

- **Aufrufe:**
  - Abfragen, schreibfrei: `naechster_schritt(bindung) -> Schritt` mit den sechs Fällen `NochNichtBegonnen`, `LaufendeSitzung(sitzung)`, `OffenerSitzungsblock(sitzung)`, `NaechsteVignette(vignette)`, `OffenerAbschlussblock`, `Ende`. Dazu `laufende_sitzung`, `sitzung_am_zug` und `sitzung_mit_offenem_block`.
  - Kommandos: `ziehung_festschreiben(bindung)`, `vignette_beginnen(bindung, session) -> Sitzung | None`, `block_vorlegen(bindung, andockpunkt, sitzung=None) -> Itemblock | None`, `block_erledigen(block)`, `bindung_abschliessen(bindung)`.
- **Invarianten:**
  - Reihenfolge der Fälle: abgeschlossen, laufende Sitzung, offener Sitzungsblock, noch keine Sitzung, nächste Vignette, offener Abschlussblock, Ende.
  - Ein Itemblock ist nur offen, wenn es Items an seinem Andockpunkt gibt. Ein leer abgeschickter Itemblock ist erledigt.
  - Alle Kommandos sind wiederholbar, ohne zweite Zeilen anzulegen. Sie sperren die Bindungszeile und serialisieren so zwei Tabs.
  - `vignette_beginnen` schreibt die Ziehung fest, startet die Sitzung mit dem gepinnten Kern der Vignette und der Modell-Konfiguration der Erhebung und hält die Vignettenposition fest. Läuft schon eine Sitzung, bleibt es bei ihr. Steht nichts an, entsteht nichts.
  - Eine flüchtige Teilnahme bekommt Itemblöcke, aber keine Antwortzeilen.
- **Fehlerfälle:** `RuntimeError`, wenn die Erhebung keine Modell-Konfiguration trägt. Über `finalisieren()` ist das nicht erreichbar.
- **Konfiguration:** keine.

### Teilnahme-Views (`erhebungen/views.py`, Teil Teilnahme; `erhebungen/urls.py`)

- **Aufrufe:**
  - Über den Teilnahme-Link: `teilnehmen`, `einwilligung` (GET/POST), `abbruchseite`, `instruktion`, `spielen` (nur POST), `abschluss`.
  - Über das Token: `gespraech` (GET/POST), `gespraech_beenden`, `debrief`, `abbrechen` (je nur POST), `itemblock` (GET/POST, htmx-Fragment bei `HX-Request`).
  - `transkription` über `transkriptions_endpunkt(transkriptions_anbieter, sitzung_fuer_transkription)`. `sitzung_fuer_transkription` ist öffentlich.
- **Invarianten:**
  - Außerhalb des Fensters oder bei archivierter Stichprobe: 403 auf jedem Weg. Ein unbekanntes Token gibt 404.
  - Der erste Link-Aufruf eines Browsers legt eine neue Bindung an und bindet ihr Token an die Session. Ein Token-Aufruf bindet den Browser ebenfalls. Ein frischer Browser bekommt eine neue, leere Teilnahme.
  - Das einzige Tor ist die Einwilligung in Sprachmodelle. Unentschieden führt zur Einwilligung, abgelehnt zur Abbruchseite. Die Spracherkennung wird nur mit `TRANSKRIPTION_ZERO_RETENTION` gefragt. Jede angebotene Wahl ist Pflicht. Die Texte sind wörtlich verbindlich (#278). Nach „ja“ zu Sprachmodellen ist die Entscheidung endgültig, eine Ablehnung lässt sich überschreiben.
  - Jede Seite folgt `naechster_schritt` und leitet um, wenn der Ablauf woanders steht. `abschluss` schließt die Bindung ab. Eine flüchtige Teilnahme sieht dort statt des Abschrift-Bausteins den Hinweis, dass nichts gespeichert wurde.
  - Eine flüchtige Sitzung, deren Verlauf nicht in der Session des Browsers liegt, wird abgebrochen, bevor der Ablauf weitergeht (ADR-0045).
  - Der Sitzungsblock erscheint unter Debrief, Abbruch und Scheitern. Ein Itemblock schreibt nur, solange er laut Ablauf offen ist.
  - Die Seitenleiste zeigt während der Teilnahme nur das Token, nie ein angemeldetes Konto (`erhebungen/navigation.py`).
- **Fehlerfälle:** 400 bei unvollständiger oder schon festgehaltener Einwilligung, bei unzulässiger Item-Antwort, bei einem POST ohne offenen Block und bei einem Debrief für eine fremde oder schon beendete Sitzung. 403 und 404 wie oben. 405 bei falscher Methode. `PermissionDenied` im Transkriptions-Endpunkt ohne passendes Browser-Token oder außerhalb des Fensters.
- **Konfiguration:** `TRANSKRIPTION_ZERO_RETENTION`.

### Itemblock-Formular (`erhebungen/forms.py`, Teil Teilnahme)

- **Aufrufe:** `ItemblockFormular(block, data=None)`, `is_valid()`, `speichern()`, `speichert`.
- **Invarianten:** Ein Feld `item_<erhebungsitem_pk>` je Item, keines ist Pflicht. Ein fehlendes Feld ist eine leere Antwort. Likert-Felder bieten die Pole an und speichern die Stufe. Eine flüchtige Teilnahme verwirft die Antworten.
- **Fehlerfälle:** `is_valid()` ist falsch bei einer Stufe außerhalb der Skala.
- **Konfiguration:** `LikertSkalenpol`.

### Session und Seitenleiste (`erhebungen/teilnahme_session.py`, `erhebungen/navigation.py`)

- **Aufrufe:** `token_aus_session`, `token_in_session_speichern`, `tokens_im_browser`; der Kontextprozessor `teilnahme_token(request)`.
- **Invarianten:** Ein Browser hält je Teilnahme-Link ein Token. Schlüssel und Ablage in der Session kapselt `teilnahme_session.py` (`TEILNAHME_TOKENS_SESSION_KEY`). Der Kontextprozessor liefert das Token nur auf den Teilnahmeseiten der Positivliste und greift nicht auf die Datenbank zu.
- **Fehlerfälle und Konfiguration:** keine.

## Startbefunde

1. **`SimpleNamespace`-Kontext in den Gestaltungstests: bestätigt.** `test_teilnahme_gestaltung.py` rendert die fünf Teilnahmeseiten und die Teilvorlage mit `render_to_string` und einem nachgebauten Kontext. Der Kontext enthält `teilnahme_token`, das die Views gar nicht übergeben; es kommt aus dem Kontextprozessor. Ein falscher Kontextname in einer View bliebe unbemerkt. Geprüft werden fast nur Klassennamen. Echte Zusagen sind zwei: die `aria-labelledby`-Verknüpfung und das Rendering der Erhebungstexte über `informationstext` samt Escaping. Beide werden über HTTP umgeschrieben, der Rest gestrichen. Dazu kommen zwei kleinere Zusagen, die in bestehende HTTP-Tests wandern: die `id` des htmx-Ziels im Fragment und die Feldgruppe mit `legend` je Item.
2. **Zeitpatch über die App-Grenze: bestätigt.** Vier Tests in `test_teilnahme.py` patchen `sitzungen.durchlauf.jetzt` mit `side_effect`-Listen. Sie hängen damit am Modulpfad und an Zahl und Reihenfolge der Aufrufe. Alle vier werden nach #324 mit `time-machine` umgeschrieben (#349). Der Zieltest bleibt jeweils ein HTTP-Test der Erhebung; deckende Tests über die Schnittstelle gibt es für keinen der vier. Dazu kommen zwei Modelltests mit `erhebungen.models.timezone.now`, ebenfalls *umschreiben*.
3. **`choice`-Patch für die Token-Kollision: Kopplung bestätigt, Umbau verworfen.** `test_anlegen_wiederholt_token_nach_kollision` patcht `erhebungen.models.choice`. Der Test hängt am Importstil (`from secrets import choice`) und an acht Aufrufen je Token. Über die Schnittstelle lässt sich die Kollision aber nicht herbeiführen: `secrets` ist nicht seedbar, und der Raum hat 30⁸ Tokens. Eine Naht nur für den Test wäre ein hypothetischer Adapter. Der Patch ersetzt die Zufallsquelle, also eine Systemgrenze, die die Coding Standards ausdrücklich zum Mocken freigeben („Time/randomness“). Ändert sich der Importstil, scheitert der Test laut mit `AttributeError` und besteht nicht still. Urteil: *behalten*.
4. **`MigrationExecutor`-Tests: bestätigt.** Die drei Tests aus #325 werden gestrichen.
5. **Hilfsfunktionen mit Unterstrich: bestätigt, kein Befund.** `_vignette_anlegen`, `_laufende_sitzung_starten` usw. sind Test-Helfer. Zwei davon greifen aber selbst auf Interna zu: `_vignette_anlegen` ruft `Vignette.objects._erstellen` (siehe „Setup“), und das `setUp` der Transkriptions-Tests schreibt den Session-Schlüssel von Hand.

## Befunde

### `erhebungen/tests/test_teilnahme_gestaltung.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_jede_teilnahmeseite_nutzt_seitengeruest_und_seitenkopf` | streichen | Implementation-coupled: Klassennamen an der View vorbei. | Keiner nötig. Die Klassen tragen nur Gestaltung, und das CSS prüft `static/tests/test_design_system.py`. Wer den Seitenkopf über HTTP absichern will, nimmt die Teilnahmeseiten in `config/tests/test_seitenvokabular.py::…::test_seiten_zeigen_ueberzeile_titel_und_knopf` auf (Überzeile „Erhebung“). |
| `test_jede_teilnahmeseite_traegt_die_gruene_bereichsfarbe` | streichen | Implementation-coupled: Die Bereichsfarbe ist CSS, der Test prüft den Klassennamen `area--participant` und die Abwesenheit zweier anderer. | Keiner nötig, wie oben. |
| `test_jede_teilnahmeseite_verknuepft_abschnitt_und_ueberschrift` | umschreiben | Echte Zusage (Barrierefreiheit), aber an der View vorbei. | Neuer HTTP-Test in `test_teilnahme.py`: Einwilligung, Instruktion, Itemblock, beide Abschlussvarianten und Abbruchseite über den echten Ablauf abrufen. Jede Seite hat mindestens ein `aria-labelledby`, und jedes zeigt auf eine vorhandene `id`. |
| `test_formularseiten_verwenden_die_vorhandenen_knopfklassen` | streichen | Implementation-coupled: Klasse `button`. | Keiner nötig. Dass jede Formularseite einen Absendeknopf „Weiter“ hat, prüfen die Ablauf-Tests, die ihn auslösen. |
| `test_keine_teilnahmeseite_fuehrt_eigene_farbwerte_ein` | streichen | Abwesenheit von Quelltext in sechs ausgewählten Vorlagen. Keine Regel über alle Dateien einer Art, also nicht von der Ausnahme der Coding Standards gedeckt. | `static/tests/test_design_system.py::test_feature_styles_only_consume_semantic_color_tokens` für das CSS. Inline-Styles in Templates hat #332 als eigenes Problem gefunden (#375); eine Regel dafür gälte für alle Templates. |
| `test_erhebungstexte_erscheinen_gerendert_im_eigenen_container` | umschreiben | Echte Zusage, aber an der View vorbei. Die Profilregeln (Überschriften, Zeilenumbruch) prüft schon `texte/tests/test_markdown.py`. | HTTP-Test, parametrisiert über Einwilligung, Instruktion und Abschluss. Die Erhebung trägt `**freiwillig** [Datenschutz](https://example.org/datenschutz) <script>x</script>` als jeweiligen Text. Erwartet: `<strong>freiwillig</strong>`, `href="https://example.org/datenschutz"` mit `target="_blank"` (das unterscheidet `informationstext` von `szenentext`) und `&lt;script&gt;` statt `<script>`. |
| `test_fluechtige_abschlussseite_behaelt_das_seitengeruest` | streichen | Klassen und Abschnittszahl. Die `aria`-Prüfung übernimmt der umgeschriebene Test oben. | `test_teilnahme.py::…::test_fluechtige_abschlussseite_ersetzt_den_abschrift_baustein` (Inhalt) und der neue `aria`-Test (flüchtige Variante) |
| `test_itemblock_teilvorlage_traegt_ihre_klassen_selbst` | streichen | Klassen. Wirklich zugesagt ist nur, dass das htmx-Fragment sein eigenes Ziel mitbringt. | In `test_htmx_interaktion_schickt_den_ganzen_block` zusätzlich: Das Fragment enthält `id="itemblock-formular"`, sonst fände der nächste `outerHTML`-Tausch sein Ziel nicht. |
| `test_itemblock_behaelt_beschriftete_feldgruppen` | umschreiben | Echte Zusage (Radiogruppe mit Beschriftung), aber mit Stellvertreter-Feld statt echtem Formular. | In `test_likert_block_bietet_die_skalenpole_und_speichert_die_stufe` zusätzlich: Der Wortlaut des Items steht in einem `<legend>` innerhalb eines `<fieldset>`. |

### `erhebungen/tests/test_teilnahme.py`

#### Einwilligung, Zugang und Abbruchseite

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_teilnahme_link_legt_bindung_an_setzt_token_und_zeigt_einwilligung` | umschreiben | Implementation-coupled: liest `session["erhebung_teilnahme_tokens"]`, also das Literal des Schlüssels und das Ablageformat aus `teilnahme_session.py`. | Weiterleitung und eine Bindung wie bisher. Die Bindung an den Browser belegt ein zweiter Aufruf desselben Links: keine zweite Bindung, wieder die Einwilligung. Ohne Session-Zugriff. |
| `test_einwilligung_oeffnet_instruktion_und_bleibt_an_der_teilnahme`, `test_einwilligungsformular_fuehrt_nach_erteilter_einwilligung_in_den_ablauf`, `test_spracherkennung_wird_nur_bei_aktiver_transkription_gefragt`, `test_ohne_transkription_bleibt_die_spracherkennung_unentschieden`, `test_jede_angebotene_option_ist_eine_pflichtwahl`, `test_nach_zustimmung_zu_sprachmodellen_ist_die_entscheidung_endgueltig`, `test_rueckweg_zeigt_leeres_formular_und_ueberschreibt_die_ablehnung`, `test_abbruchseite_setzt_vor_und_nach_der_zustimmung_im_ablauf_fort` | behalten | HTTP, eigene Logik der Einwilligung. Die gespeicherten Entscheidungen sind Teil der Datenspur. | – |
| `test_formular_zeigt_die_systemtexte_ohne_vorauswahl`, `test_ablehnung_der_sprachmodelle_fuehrt_auf_die_abbruchseite` | behalten | Die Wortlaute stammen aus einer externen Spec (#278, wörtlich verbindlich), nicht aus Doku-Prosa. Das ist ein Kontrakttest im Sinn von #321. | – |
| `test_nach_ablehnung_fuehren_alle_teilnahmewege_auf_die_abbruchseite` | behalten | Alle Wege durch dasselbe Tor. | – |
| `test_ausserhalb_des_laufenden_zeitraums_ist_einstieg_und_fortsetzung_gesperrt`, `test_archivierte_stichprobe_ist_fuer_teilnahmen_gesperrt`, `test_neuer_browser_erzeugt_eine_neue_leere_teilnahme` | behalten | Die Zeit wird über die Daten der Stichprobe verschoben, nicht über einen Patch. | – |

#### Diagnosegespräch, Debrief und Abbruch

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_audioeinwilligung_aktiviert_spracheingabe_in_gespraech_und_debrief` | behalten | Eigen ist die Verdrahtung: Das Einwilligungsformular der Erhebung schaltet die Aufnahme frei. | – |
| `test_ohne_audioeinwilligung_steht_ein_stiller_hinweis_statt_des_knopfs` | streichen | Schichtdoppelung: Diagnosegespräch und Debrief rendert die geteilte `persistiertes_gespraech`. Dass „nein“ als `False` gespeichert wird, prüft schon die Einwilligung. | `training/tests/test_sitzung.py::TrainingssitzungTests::test_training_ohne_audioeinwilligung_zeigt_nur_tastatureingabe` und `…::test_debrief_ohne_audioeinwilligung_zeigt_nur_tastatureingabe`, dazu `test_spracherkennung_wird_nur_bei_aktiver_transkription_gefragt` |
| `test_gespraech_zeigt_die_abgesetzte_aktionszeile` | umschreiben | Implementation-coupled: zwei Klassen-Strings, im Debrief die Abwesenheit einer dritten Klasse. Eigen ist die Navigation der Erhebung (`_sitzungsnavigation`). | Wie in #330: „Gespräch beenden“ über `config.tests.formular.submit_knoepfe`, der Erklärsatz und ein Formular mit `action` auf `erhebungen:abbrechen`. Im Debrief fehlt der Erklärsatz. |
| `test_token_spielt_eine_vignette_mit_ueberholtem_kern` | streichen | Schichtdoppelung: Den Kern-Pin setzt `sitzung_starten` in `sitzungen`, für Training und Erhebung gleich. | `training/tests/test_sitzung.py::TrainingssitzungTests::test_training_spielt_eine_vignette_mit_ueberholtem_kern` |
| `test_sitzung_rendert_lernauftrag_und_arbeitsheft_als_szenentext` | umschreiben | Schichtdoppelung: Das Profil des geteilten Includes prüft der Vignettentest. | Wie in #330 für die Abschrift: auf einen Einbindungsbeleg kürzen, „Addiere <em>zwei</em> Brüche.“ steht auf der Gesprächsseite. Das Profil prüft `vignetten/tests/test_views.py::VignetteDetailViewTests::test_rendert_lernauftrag_und_arbeitsheft_als_szenentext`. |
| `test_token_spielt_eine_vignette_bis_zum_abschluss` | umschreiben | Durchstich mit eigenem Beitrag (Start, Wiederholung von `spielen`, Abschluss, Abschrift-Baustein). Der Debrief ist nur mit „Debrief“ belegt. | „Was ist Ihnen aufgefallen?“ statt „Debrief“. Der Rest bleibt. |
| `test_seitenleiste_zeigt_das_token_auf_jeder_teilnahmeseite` | umschreiben | Der Helfer `_seitenleiste_zeigt_nur_das_token` prüft die Abwesenheit der Klassen `sidebar-account` und `sidebar-login`. Der Test schickt außerdem das Feld `antwort`, das die View nicht liest (siehe „Setup“). | Statt der Klassen: „Ihr Teilnahme-Token“ mit dem Token steht auf der Seite; der Name des angemeldeten Kontos („grace“), „Abmelden“ und „Anmelden“ stehen nicht darauf. Die Abschlussseite trägt „Ihr Teilnahme-Token“ selbst (`abschluss.html`); dort belegen nur die Ausschlüsse etwas. |
| `test_debrief_setzt_direkt_mit_der_naechsten_vignette_fort`, `test_staler_debrief_beendet_die_folgesitzung_nicht`, `test_aktiver_abbruch_setzt_die_sitzung_auf_abgebrochen` | behalten | Eigene Views der Erhebung (`debrief`, `abbrechen`), eigene Weiterleitungen. | – |
| `test_vorzeitiges_gespraechsende_zeigt_den_debrief` | umschreiben | Eigene View `gespraech_beenden`, aber „Debrief“ als einziger Beleg. | „Was ist Ihnen aufgefallen?“ erwarten und „Ihre nächste Frage“ ausschließen; Status `laufend` wie bisher. |
| `test_abgegebene_diagnose_ist_im_debrief_gesperrt` | umschreiben | Implementation-coupled: `'name="diagnose" rows="4" required readonly'` hängt an Reihenfolge und Zahl der Attribute. | Mit einem `HTMLParser` wie in `config/tests/formular.py`: Die `textarea` `diagnose` enthält „Bruchfehler“ und trägt `readonly`, der Knopf „Diagnose abgeben“ trägt `disabled`. |
| `test_modellversagen_zeigt_den_sitzungsblock` | behalten | Erhebungseigen: der Sitzungsblock nach dem Scheitern. Die Zahl der Anfragen hält fest, dass das Vorlegen keinen weiteren Modellaufruf auslöst. | – |
| `test_endgueltiger_fehlschlag_bewahrt_gespraechsschritt_ohne_antwort` | streichen | Schichtdoppelung: Meldung, Status und Schritt ohne Äußerung prüft das Training über dieselbe geteilte View. Die drei Fehlversuche am `DBSink` prüft der Durchlauf. | `training/tests/test_sitzung.py::TrainingssitzungTests::test_endgueltiger_fehlschlag_bleibt_gescheitert` und `sitzungen/tests/test_durchlauf.py::test_gescheiterter_schritt_meldet_denselben_ausgang_und_wird_je_sink_behandelt` |
| `test_abgeschlossene_teilnahme_traegt_die_vollstaendige_datenspur` | behalten | Durchstich: Die Erhebung startet mit ihrer gepinnten Konfiguration, schreibt Schritt, Fehlversuch, Diagnose und Position. | – |

#### Gesprächsbudget

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_zeitbudget_ist_von_training_und_anderen_sitzungen_getrennt` | umschreiben | Patch auf `sitzungen.durchlauf.jetzt` mit drei Zeitpunkten in Aufrufreihenfolge (#324). | Mit `time-machine` (#349): verbrauchte Trainingssitzung wie bisher, GET zu T, POST zu T+1 s. Die Antwort zeigt „Ich addiere.“ und „Ihre nächste Frage“, nicht „Was ist Ihnen aufgefallen?“. |
| `test_zeitbudget_ueberlebt_den_browserwechsel` | umschreiben | Patch auf `sitzungen.durchlauf.jetzt` mit fünf Zeitpunkten in Aufrufreihenfolge (#324). Erhebungseigen ist der Browserwechsel, der Fall aus #245. „Debrief“ als Beleg. | Mit `time-machine` (#349): GET zu T, POST zu T+1 s im ersten Browser. Im zweiten Browser GET zu T+70 s, POST zu T+76 s. Die Antwort zeigt „Was ist Ihnen aufgefallen?“, `verbrauchte_zeit` ist 7. |
| `test_schrittbudget_laesst_die_uhr_der_sitzung_stehen` | umschreiben | Patch auf `sitzungen.durchlauf.jetzt` mit drei Zeitpunkten in Aufrufreihenfolge (#324). | Mit `time-machine` (#349): Schrittbudget 2, GET zu T, POST zu T+40 s. `verbrauchte_zeit` der Sitzung ist 0, ein Feld des Exports. |
| `test_erschoepfte_zeit_fuehrt_den_schritt_zu_ende_und_zeigt_den_debrief` | umschreiben | Patch auf `sitzungen.durchlauf.jetzt` mit drei Zeitpunkten in Aufrufreihenfolge (#324). „Debrief“ als Beleg. | Mit `time-machine` (#349): Zeitbudget 5 s, GET zu T, POST zu T+6 s. Der gespeicherte Schritt trägt Eingabe und Äußerung wie bisher; die Antwort zeigt „Ich addiere.“ und „Was ist Ihnen aufgefallen?“, nicht „Ihre nächste Frage“. |

#### Eingabemodus

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_eingabemodus_kommt_aus_dem_formular_und_faellt_tolerant_zurueck` | behalten | Der einzige Test, der den Rückfall von `Eingabemodus.aus_formular` am Gespräch prüft. Das Training verweist auf ihn („Training folgt der Erhebung“). | – |
| `test_antwortloser_schritt_traegt_den_eingabemodus` | behalten | Antwortloser Schritt am `DBSink` mit Modus. Der Probelauf prüft nur den `ScratchSink`. | – |
| `test_diagnose_traegt_den_eingabemodus_aus_dem_formular`, `test_diagnose_ohne_modusfeld_ist_getippt`, `test_diagnose_mit_unbekanntem_modus_ist_getippt` | umschreiben | Gleicher Test, nur der Formularwert wechselt. Eigen ist die Verdrahtung in `erhebungen.views.debrief`. | Ein Test, parametrisiert über `"gemischt"` → gemischt, fehlendes Feld → getippt, `"gepfiffen"` → getippt. |
| `test_diagnoseformular_traegt_das_versteckte_modusfeld` | behalten | Der einzige Test des versteckten Felds. Das Include gehört zu `sitzungen`, eine Verlegung in den Probelauf wäre möglich, ist aber kein Befund. | – |

#### Itemblöcke

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_abschluss_block_speichert_antworten_und_darf_uebersprungen_werden`, `test_offener_abschluss_block_ueberlebt_den_browserwechsel`, `test_leer_abgeschickter_abschluss_block_gilt_als_erledigt` | behalten | HTTP über den Ablauf. Die Antwortzeilen sind Forschungsdaten. | – |
| `test_abschluss_block_wird_mit_demselben_token_wiederaufgenommen` | umschreiben | Implementation-coupled: liest `session["erhebung_teilnahme_tokens"]`. | Statt des Session-Schlüssels: Der andere Browser ruft danach den Teilnahme-Link auf und landet im Itemblock, nicht bei der Einwilligung einer neuen Teilnahme. |
| `test_htmx_interaktion_schickt_den_ganzen_block` | umschreiben | `assertNotContains(block, "hx-params")` prüft die Abwesenheit eines Attributs. Zugesagt ist das Serververhalten: Ein fehlendes oder leeres Feld ist eine leere Antwort. | Ohne die `hx-params`-Zusicherung. Dazu die `id="itemblock-formular"` im Fragment (aus den Gestaltungstests). |
| `test_likert_block_bietet_die_skalenpole_und_speichert_die_stufe` | umschreiben | HTTP, Literal 6 als Stufe. Nur ergänzen. | Zusätzlich: Der Wortlaut steht im `<legend>` eines `<fieldset>` (aus den Gestaltungstests). |
| `test_likert_block_weist_eine_stufe_ausserhalb_der_skala_ab`, `test_itemantwort_bleibt_nach_zeitraumende_unangetastet`, `test_abschluss_url_ueberspringt_keine_offene_vignette` | behalten | Fehlerfälle über HTTP. | – |
| `test_token_endpunkt_sperrt_sitzungsblock_ausserhalb_seines_besuchs` | umschreiben | Ruft `block_vorlegen` aus dem Test heraus und schickt das Feld `antwort`, das die View nicht liest. Der Itemblock entsteht so neben dem Ablauf. | Während die Sitzung läuft, POST auf `itemblock` mit einem Feld `item_<pk>`: 400, und keine Antwortzeile trägt einen Wert. Ohne `block_vorlegen`. |
| `test_debrief_zeigt_fragebogen_items_unter_dem_verlauf`, `test_htmx_debrief_fuegt_den_sitzungsblock_ins_fortsetzungsfragment_ein`, `test_wiedereinstieg_fuehrt_zum_offenen_sitzungsblock`, `test_offener_sitzungsblock_ueberlebt_den_browserwechsel`, `test_abbruch_zeigt_den_sitzungsblock_statt_der_instruktion` | behalten | Sitzungsblock über HTTP, erhebungseigen. | – |
| `test_teilnahme_kommt_ueber_gewechselte_browser_zu_ende` | behalten | Durchstich über fünf Browser, beide Blockarten, Debrief und Abbruch. | – |
| `test_zwei_vignetten_fuehren_ueber_ihre_bloecke_zum_abschluss` | streichen | Doppelung in der Datei: dieselbe Folge (zwei Vignetten, Sitzungsblock, Abschlussblock, Abschluss). Je eine Antwortzeile pro Sitzung prüft der Browserwechsel-Test über `ItemAntwort.objects.get(sitzung=…)`. Die Reihenfolge der Schritte prüft `test_ablauf.py`. | `test_teilnahme_kommt_ueber_gewechselte_browser_zu_ende` und `test_ablauf.py::test_beendete_sitzung_stellt_ihren_block_vor_die_naechste_vignette` |

#### Fensterende und flüchtige Teilnahme

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_nach_fensterende_verfaellt_die_laufende_teilnahme` | umschreiben | Schichtdoppelung: `assertTrue(bindung.verfallen)` prüft eine Modelleigenschaft ohne Aufrufer (#384). | Nur die 403 auf `gespraech` und `spielen`. |
| `test_nach_fensterende_verfaellt_teilnahme_mit_offener_vignette` | streichen | Prüft nur `bindung.verfallen`, kein HTTP. Für die Views ist der Fortschritt egal; sie sperren allein nach der Phase. | Das 403 prüft `test_nach_fensterende_verfaellt_die_laufende_teilnahme`. Die Eigenschaft prüft `test_models.py::test_unfertige_teilnahme_verfaellt_nach_ende_des_erhebungszeitraums`, solange es sie gibt (#384). |
| `test_fluechtige_teilnahme_spielt_alle_vignetten_ohne_inhaltszeilen` | umschreiben | Erhebungseigen (ADR-0045). Der Debrief ist im Schleifenkörper nur mit „Debrief“ belegt. | „Was ist Ihnen aufgefallen?“ statt „Debrief“. Der Rest bleibt; „keine Inhaltszeile“ ist die Zusage aus ADR-0045. |
| `test_fluechtige_abschlussseite_ersetzt_den_abschrift_baustein`, `test_fluechtige_sitzung_zeigt_den_abgebrochenen_verlauf`, `test_token_wiedereinstieg_bricht_fluechtige_sitzung_ohne_verlauf_ab`, `test_abgebrochene_fluechtige_sitzung_fuehrt_zu_ihrem_fragebogen`, `test_letzte_abgebrochene_fluechtige_sitzung_fuehrt_zum_abschluss`, `test_debrief_ohne_verlauf_schliesst_die_fluechtige_sitzung_nicht_ab`, `test_fluechtige_sitzung_laeuft_im_selben_browser_weiter`, `test_gespeicherte_sitzung_laeuft_im_frischen_browser_weiter`, `test_fluechtige_teilnahme_verwirft_die_fragebogen_antworten` | behalten | Erhebungseigen: `_sitzung_ohne_verlauf_abbrechen` und das Formular ohne Speicherung. Der Name `…_zeigt_den_abgebrochenen_verlauf` passt nicht zum geprüften Status `gescheitert`; beim Umsetzen umbenennen. | – |

#### Setup

- **`_vignette_anlegen`** ruft `Vignette.objects._erstellen` und legt die Historie von Hand an. Deshalb steht die Datei auf der SLF001-Übergangsliste in `pyproject.toml`. Der öffentliche Weg steht schon in `test_ablauf.py::_finale_vignette_anlegen` (Kern finalisieren, `Vignette.objects.anlegen`, Felder setzen, `finalisieren()`). Den Kreis teilt die Vignette dann mit der Erhebung, weil dasselbe Konto beide anlegt. Wie in #328, #330 und #332 vorgeschlagen, ersetzt ein gemeinsamer Helfer alle Kopien. Danach fällt die Datei von der Liste.
- **`Sitzung.objects.update(status=Sitzung.Status.ABGESCHLOSSEN)`** beendet in sieben Tests die Sitzung am Lebenszyklus vorbei: `test_htmx_interaktion_…`, beide Likert-Tests, `test_itemantwort_bleibt_nach_zeitraumende_unangetastet`, `test_abschluss_url_ueberspringt_keine_offene_vignette`, `test_fluechtige_abschlussseite_…` und `test_nach_fensterende_verfaellt_teilnahme_mit_offener_vignette`. Der öffentliche Weg ist ein POST auf `debrief`, wie ihn die übrigen Tests der Datei gehen. Der Helfer `_laufende_sitzung_starten` kann dafür einen Schwesterhelfer `_sitzung_abschliessen(bindung)` bekommen.
- **Feld `antwort`:** 17 POSTs auf `itemblock` schicken `"antwort": itemantwort.pk`. Die View liest das Feld nicht mehr; das Formular arbeitet mit `item_<pk>` und `weiter`. Der tote Parameter suggeriert eine Schnittstelle, die es nicht gibt. Beim Umsetzen entfernen; wo er der einzige Inhalt war, bleibt `{"weiter": "ja"}`.

### `erhebungen/tests/test_ablauf.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_feste_reihenfolge_setzt_mit_der_naechsten_ungespielten_vignette_fort`, `test_beendete_sitzung_stellt_ihren_block_vor_die_naechste_vignette`, `test_ablauf_liefert_nach_den_vignetten_den_geordneten_abschluss_block` | behalten | Öffentliche Abfrage über die sechs Fälle. Die Anzahl der Antwortzeilen ist die Ausgabe von `block_vorlegen`. | – |
| `test_zufaellige_ziehung_ist_mit_gespeichertem_seed_reproduzierbar`, `test_ziehung_bleibt_nach_dem_ersten_festschreiben_unveraendert` | behalten | Zusage aus ADR-0029: Der Seed steht in der Datenspur und die Ziehung entsteht einmal. | – |
| `test_zufaellige_ziehung_mischt_ohne_die_positionen_zu_aendern` | umschreiben | Tautologisch: Die Erwartung entsteht mit `Random(17).shuffle`, wie im Code. | Durchgerechnetes Beispiel als Literal: Mit Seed 17 und fünf Vignetten auf den Positionen 1–5 ist die Ziehung die Folge der Vignetten 1, 3, 2, 4, 5. Das Literal hält fest, dass ein exportierter Seed auch nach einem Umbau dieselbe Reihenfolge ergibt. Der Teil „Positionen der Erhebung bleiben“ bleibt. |
| `test_kommandos_bleiben_beim_zweiten_aufruf_bei_ihrem_ergebnis`, `test_block_ohne_items_am_andockpunkt_entsteht_nicht`, `test_abfrage_nach_dem_naechsten_schritt_schreibt_keine_zeile` | behalten | Wiederholbarkeit und Schreibfreiheit sind Zusagen der Schnittstelle. Zeilenzählungen sind dafür der einzige Beleg. | – |
| `test_vignette_beginnen_schreibt_ziehung_sitzung_und_position`, `test_zwei_aufrufe_beginnen_keine_zweite_sitzung` | behalten | Öffentliches Kommando. | – |

Setup: `_bindung_anlegen` legt die Bindung mit `objects.create` und festem Token an statt über `objects.anlegen(stichprobe)`. `_sitzung_anlegen` legt Sitzungen mit gesetztem Status direkt an, und ein Test schaltet den Status per `save()` um. Für einen Unit-Test des Ablaufs ist das zulässiger Aufbau: Die Fälle hängen nur am Status der Sitzungen, und `vignette_beginnen` deckt den echten Start ab. Kein Befund.

### `erhebungen/tests/test_transkription.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| Aufruf über `transkriptions_endpunkt(lambda: anbieter, sitzung_fuer_transkription)` statt über die URL | behalten | Wie in #330: `transkriptions_endpunkt` und `sitzung_fuer_transkription` sind öffentlich, `anbieter_bilden` ist die Naht zum Drittanbieter. | – |
| `setUp` | umschreiben | `Vignette.objects._erstellen` (SLF001-Übergangsliste), `Sitzung.objects.create` und der Session-Schlüssel `erhebung_teilnahme_tokens` von Hand. | Der echte Weg über den Client: Teilnahme-Link, Einwilligung mit Spracherkennung „ja“, `spielen`. Die Sitzung und die Bindung des Browsers entstehen dabei. Die Vignette über den gemeinsamen Helfer. |
| `test_eingewilligte_teilnahme_transkribiert_ohne_konto`, `test_ohne_einwilligung_verweigert_externe_transkription`, `test_fremde_sitzung_bleibt_dem_token_verschlossen` | behalten | Erhebungseigen: Autorisierung über das Browser-Token. | – |
| `test_ohne_zero_retention_verweigert_externe_transkription` | streichen | Schichtdoppelung: Das Tor liegt in `transkriptions_endpunkt` und gilt für jeden Prinzipal. | `sitzungen/tests/test_transkription.py::ProbelaufTranskriptionTests::test_zero_retention_bleibt_auch_im_probelauf_das_tor` |

Lücke: `sitzung_fuer_transkription` sperrt außerhalb des Fensters, aber kein Test prüft das. Neuer Test: Stichprobe nach dem Start ins Vergangene verschieben (`ende` setzen), erwartet `PermissionDenied`, und der Anbieter bleibt unberührt.

### `erhebungen/tests/test_models.py`

#### Migrationen und Felder

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_migration_belaesst_bestandsdaten_ohne_entstehungszeitpunkt`, `test_eigentuemerinnen_migration_uebernimmt_bestand_und_stellt_trigger_zurueck`, `test_positionsmigration_traegt_positionen_zufaelliger_erhebungen_nach` | streichen | Totes Gewicht: Die Migrationen liegen auf `main` (#325). Der Import von `MigrationExecutor` und `connection` entfällt mit ihnen. | Keiner nötig, Begründung ADR-0031. |
| `test_neue_erhebungsbindung_traegt_entstehungszeitpunkt` | streichen | Tautologisch: `auto_now_add` ist Django-Verhalten aus der Felddefinition. | `erhebungen/tests/test_forschenden_views.py::ErhebungsExportTests::test_exportiert_erhebung_stichprobe_und_teilnahme_als_csvs` prüft `erstellt_am` im Export. |
| `test_erhebungsbindung_verbindet_stichprobe_mit_genau_einer_teilnahme` | streichen | Tautologisch: prüft, dass `objects.create` die übergebenen Fremdschlüssel speichert. „Genau eine“ prüft der Test gar nicht. | Die Exklusivität der Bindung prüft `training/tests/test_bindungsexklusivitaet.py`. Das Anlegen über die Schnittstelle prüft `test_anlegen_vergibt_lesbare_eindeutige_teilnahme_tokens`. |

#### Sichtbarkeit und Eigentümer-Kreis

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_sichtbar_fuer_liefert_nur_eigene_erhebungen`, `test_sichtbar_fuer_liefert_alle_erhebungen_fuer_administration` | streichen | Schichtdoppelung: `Erhebung.objects.sichtbar_fuer` ist der gemeinsame Eigentümer-Kreis. #332 kam zum selben Ergebnis. | `config/tests/test_eigentuemer_kreis_contract.py::test_sichtbar_sind_die_eigenen_bestaende_und_der_administration_alle` (Fall `Erhebung`) |
| `test_geteilte_erhebung_ist_fuer_alle_eigentuemerinnen_sichtbar` | streichen | Doppelung: Der Kreis ist ein symmetrisches M2M. | wie oben |
| `test_laufende_erhebung_behaelt_aenderbaren_eigentuemerinnenkreis` | behalten | Hält fest, dass das Einfrieren den Kreis nicht erfasst, auch während einer laufenden Stichprobe. | – |
| `test_finale_erhebung_behaelt_aenderbaren_eigentuemerinnenkreis` | streichen | Doppelung: Der Test darüber fügt auf einer finalen Erhebung hinzu und entfernt zusätzlich. | `test_laufende_erhebung_behaelt_aenderbaren_eigentuemerinnenkreis` |

#### Zuordnungen

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_erhebung_haelt_finale_vignetten_in_fester_reihenfolge` | behalten | Die Sortierung ist Schnittstelle für Ablauf und Ziehung. Angelegt wird in umgekehrter Reihenfolge, das macht den Test aussagekräftig. | – |
| `test_erhebungsvignette_lehnt_entwurf_auch_per_bulk_insert_ab`, `test_erhebungsvignette_lehnt_fremde_finale_fassung_ab`, `test_erhebung_bindet_material_ueber_eine_kreis_schnittmenge_ein`, `test_erhebungsitem_schuetzt_finalitaet_eigentum_und_item_fassung` | behalten | DB-Invarianten über Trigger und `PROTECT`. `models.Model.delete(eigenes_item)` umgeht die Löschregel des Items, um `PROTECT` zu erreichen; das ist die zulässige interne Naht. | – |
| `test_erhebungsvignette_braucht_eine_position` | behalten | Hält fest, dass auch zufällige Erhebungen eine Position tragen (vgl. die gestrichene Positionsmigration). | – |
| `test_zufaellige_erhebung_bewahrt_vignettenpositionen` | streichen | Schichtdoppelung: Das Umschalten der Regel prüft die View mit denselben Zusicherungen. Auf Modellebene schreibt `save()` die Positionen ohnehin nicht. | `erhebungen/tests/test_forschenden_views.py::ErhebungenEntwurfKonfigurierenTests::test_umschalten_bewahrt_die_reihenfolge_hin_und_zurueck` |
| `test_vignettenposition_ist_je_erhebung_eindeutig`, `test_erhebungsvignette_bewahrt_die_menge_je_erhebung_eindeutig`, `test_erhebungsitem_darf_an_beide_andockpunkte_aber_je_nur_einmal`, `test_itemposition_ist_je_andockpunkt_eindeutig` | behalten | Constraint-Tests. | – |
| `test_feste_reihenfolge_hat_keine_doppelte_position` | streichen | Doppelung: dieselbe Constraint `erhebungen_vignettenposition_ist_eindeutig`. Die Reihenfolgeregel spielt für sie keine Rolle. | `test_vignettenposition_ist_je_erhebung_eindeutig` |
| `test_finale_erhebung_weist_jede_zuordnungsaenderung_ab`, `test_archivierte_erhebung_weist_jede_zuordnungsaenderung_ab`, `test_entwurf_bleibt_in_seinen_zuordnungen_frei`, `test_zurueckgezogene_erhebung_erlaubt_zuordnungen_wieder`, `test_entwurf_laesst_sich_mitsamt_seinen_zuordnungen_loeschen` | behalten | ADR-0027 auf jedem Schreibweg, parametrisiert über beide Arten. | – |

#### Antworten

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_abschlussantwort_ist_je_block_eindeutig_und_nonresponse_ist_gueltig`, `test_itemantwort_braucht_ihren_itemblock`, `test_itemantwort_erlaubt_hoechstens_eine_wertspalte`, `test_itemantwort_wert_passt_zum_itemtyp`, `test_itemantwort_sitzung_und_andockpunkt_passen_zur_teilnahme` | behalten | Constraint- und `clean()`-Tests. Der Aufbau mit `Itemblock.objects.create` ist hier nötig, um einzelne Verstöße zu erzeugen. | – |

#### Lebenszyklus

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_finalisieren_pinnt_die_aktive_modell_konfiguration`, `test_finalisieren_pinnt_die_schuelerin_nicht_lehrperson_oder_bewerter`, `test_zurueckziehen_und_erneutes_finalisieren_pinnt_aktuelle_konfiguration`, `test_zurueckziehen_ist_mit_nicht_archivierter_stichprobe_gesperrt`, `test_archivieren_ist_waehrend_laufender_stichprobe_gesperrt`, `test_archivieren_akzeptiert_nur_finale_erhebungen`, `test_archivieren_und_entarchivieren_bewahren_den_finalen_pin`, `test_finale_erhebung_ist_eingefroren_und_nicht_physisch_loeschbar`, `test_archivierte_erhebung_ist_auch_per_bulk_update_eingefroren`, `test_stichprobe_laesst_sich_nicht_per_bulk_update_archivieren` | behalten | Öffentlicher Lebenszyklus, Fehler über die Meldung. Die laufende Stichprobe entsteht über ihre Daten (± 1 Minute), ohne Zeitpatch. | – |
| `test_eigentuemerlose_erhebung_kann_nicht_entarchiviert_werden` | behalten | Fehlerfall. `eigentuemerinnen.clear()` ist eine Abkürzung im Aufbau; der öffentliche Weg wäre `austreten` der letzten Eigentümerin einer archivierten Erhebung. | – |
| `test_stichprobe_archivieren_schaltet_nur_ueber_ihre_lebenszyklus_methode` | umschreiben | Der Name verspricht „nur über die Methode“, geprüft ist nur der Erfolgsfall. Den Weg über `save()` prüft kein Test. | Zusätzlich: `archiviert = True` und `save()` auf einer gespeicherten, neu geladenen Instanz wirft `ValidationError` „Lebenszyklus-Methode“. Ein zweites `archivieren()` wirft „bereits archiviert“. |

#### Erhebungsbindung und Stichprobe

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_anlegen_vergibt_lesbare_eindeutige_teilnahme_tokens` | behalten | Das Alphabet steht als Literal im Test. | – |
| `test_anlegen_wiederholt_token_nach_kollision` | behalten | Startbefund 3: Der Patch ersetzt die Zufallsquelle, eine Systemgrenze. | – |
| `test_unfertige_teilnahme_verfaellt_nach_ende_des_erhebungszeitraums` | umschreiben | Patch auf `erhebungen.models.timezone.now` (#324). Nur der positive Fall. Fällt mit der Eigenschaft weg, falls #384 sie entfernt. | Mit `time-machine` auf 17:01 (#349). Dazu zwei Gegenfälle: abgeschlossene Bindung verfällt nicht, und um 16:59 verfällt nichts. |
| `test_phase_leitet_sich_aus_zeitraum_und_systemzeit_ab` | umschreiben | Patch auf `erhebungen.models.timezone.now` (#324). Die Grenzen sind nur beim Beginn geprüft. | Mit `time-machine` (#349). Die Fälle um 17:00 (laufend) ergänzen, damit beide Grenzen geprüft sind. |

## Folge-Issues

- #384 `Erhebungsbindung.verfallen` hat keinen Aufrufer.
- #385 `Stichprobe.traegt_daten` sucht die Bindung über `_meta.related_objects` statt über `erhebungsbindung_set`.

Weitere Probleme im Produktionscode hat das Review nicht gefunden. Dass die Token-Kollision nur über einen Patch der Zufallsquelle erreichbar ist, ist kein Mangel (Startbefund 3). Für `Eingabemodus.aus_formular` in `sitzungen` gibt es keinen direkten Unit-Test; den Rückfall prüfen die Erhebungs-Tests oben. Das gehört zum Bereich von #330.
