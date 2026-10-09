# Testreview: Querschnitt – Design-System, Seitenvokabular, Verträge

Bereich aus #332 (Spec #321). Geprüft sind `static/tests/test_design_system.py`, alle Dateien in `config/tests/` und die Wurzel-`conftest.py`. Für Tests, die die Zeit patchen oder eine Migration prüfen, gelten die Regeln aus #324 und #325. Keiner der Tests hier tut das.

## Schnittstelle

### Design-System (`static/css/`)

- **Aufrufe:** `templates/base.html` bindet die Stylesheets ein. Templates benutzen die Klassen der gemeinsamen Komponenten (`.card`, `.badge--…`, `.area--…`, `.page-section`, `.table--zeilenlink` …).
- **Tokens:** `tokens.css` deklariert die PHSG-Primitive (`--phsg-…`), die semantischen Farb-Tokens (`--color-…`, `--color-area-<bereich>-…`), das Abstandsraster (`--space-…`), `--radius` und `--content-max-width`.
- **Invarianten** über alle Dateien:
  - Feature-CSS liest nur semantische Farb-Tokens, nie `--phsg-…`.
  - Abstände (`margin`, `padding`, `gap`, `inset`, `top` …) stehen nie in Pixeln, sondern im Raster.
  - Die Überschriften h3–h5 in Markdown-Texten sind fallend gestaffelt: auf Seitenfeldern kleiner als der Abschnittskopf, in der Sitzung nie kleiner als der Fließtext.
- **Fehlerfälle:** Eine Deklaration mit einer nicht deklarierten Custom Property verwirft der Browser stillschweigend. Das passiert heute mit `--radius-sm` (#374) und mit den Inline-Styles in `training/templates/training/detail.html` (#375).
- **Konfiguration:** keine.

### Seitenvokabular (Templates aller Apps)

- **Aufrufe:** jede Seite über HTTP.
- **Invarianten** (Entscheidung zu #287, #313):
  - Der Seitenkopf `<header class="page-head">` trägt als Überzeile Bereich und Unterbereich („Entwicklung / Vignetten“) und als `h1` die Aktion oder das Objekt.
  - Absendeknöpfe tragen das Verb der Aktion. Das Verb fürs Neuanlegen heißt „anlegen“, nicht „erstellen“.

### Startseite und Anmeldung (`config/urls.py`, `templates/start.html`, `templates/registration/login.html`)

- **Aufrufe:**
  - `GET /` (`start`) liefert eine statische `TemplateView`, ohne Anmeldung erreichbar.
  - `GET` und `POST` auf `/accounts/login/` laufen über Djangos `LoginView`.
- **Invarianten:**
  - Die Sidebar zeigt Anonymen nur den Login-Link.
  - Angemeldete sehen „Abmelden“ und die Links ihrer Rollen. Diese berechnet `konten.navigation`; die Tests dazu liegen in `konten`.
  - Ein Login ohne `next` leitet auf `start` weiter (`LOGIN_REDIRECT_URL`).

### Eigentümerinnen-Abschnitt (`templates/includes/eigentuemerinnen.html`)

- **Aufrufe:** Vier Detailseiten binden den Abschnitt per `{% include %}` ein: Vignette, Fragebogen-Item, Training (Kuratieren) und Erhebung. Sie übergeben `kreis`, `objekt_pk`, die beiden Routennamen, die Artikelformen des Artefakts und die Abschnittsnummer.
- **Invarianten:**
  - Eine Tabelle mit Name, allen Rollen und Aktion je Konto im Kreis. Die eigene Zeile trägt „(Sie)“, „Mich entfernen“ und einen Hinweis, was der Austritt bewirkt.
  - Steht nur eine Person im Kreis, gibt es keine Entfernen-Aktion, sondern den Hinweis „Letzte Eigentümer:in“.
  - Unter „Eigentümer:in hinzufügen“ stehen eine Auswahl der möglichen Ergänzungen und der Knopf „Hinzufügen“. Gibt es keine Ergänzungen, steht dort stattdessen ein Satz.

### Eigentümer-Kreis (`konten/eigentuemerschaft.py`)

- **Aufrufe:**
  - `Modell.objects.anlegen(konto, **werte)` und `Modell.objects.sichtbar_fuer(konto)`.
  - Am Bestand: `austreten(konto_pk) -> bool`, `moegliche_ergaenzungen()`, `ist_aktiv()` und `hat_mehrere_eigentuemerinnen`.
  - `bestandsmodelle()` liefert alle Erbinnen.
- **Invarianten** (ADR-0032):
  - Ein Kreis ist nie leer. `austreten` lehnt die letzte Person ab, bedingungslos und auch bei einem stillgelegten Bestand. Ein Konto, das nicht im Kreis steht, kann nicht austreten.
  - Die Administration sieht alle Bestände.
  - Eintragbar sind die Trägerinnen der `ROLLENGRUPPE` und die Administration, ohne die schon Eingetragenen.
  - Ein Konto lässt sich nicht löschen, solange es die einzige Eigentümerin eines aktiven Bestands ist.
- **Fehlerfälle:**
  - `austreten` meldet eine Ablehnung nur über den Rückgabewert `False`.
  - Beim Löschen eines Kontos wirft Django `ProtectedError`.
- **Konfiguration:** `ROLLENGRUPPE` und `LOESCHSPERRE_MELDUNG` je Erbin.

### Eigentümer-Kreis-Routen (`<app>/urls.py`)

- **Aufrufe:**
  - `<app>:eigentuemerin_hinzufuegen` mit `pk`.
  - `<app>:eigentuemerin_entfernen` mit `pk` und `konto_pk`.
  - Beide nehmen nur POST an und leiten auf die Detailseite weiter, bzw. auf die Liste, wenn jemand sich selbst entfernt.
- **Invarianten:** Die Routennamen sind in allen vier Apps gleich. Code leitet sie aber nirgends ab: Jede Detailseite reicht sie ausdrücklich an das Include durch. Das Pfadsegment `eigentuemerinnen/…` nennt kein Link und keine Dokumentation.

### Prompt-Umgebungen (`simulation/models.py`, `vignetten/models.py`, `simulation/__init__.py`)

- **Aufrufe:**
  - `prompt_platzhalter(vignette)` und `rahmen_platzhalter(vignette)` liefern die Werte je Platzhaltername.
  - `Simulationskern.clean()` lehnt Vorlagen mit Platzhaltern außerhalb von `VERTRAG_PROMPT` bzw. `VERTRAG_RAHMEN` ab.
  - `vorlage_rendern(vorlage, platzhalter)` setzt nur die benutzten Platzhalter ein. Aufrufer sind `antwort_versuchen` und `rahmenhandlung_rendern`.
- **Invarianten:**
  - Jeder Vertragsname hat einen Wert.
  - Die Platzhalter in `PROMPT_PLATZHALTER_MIT_UMGEBUNG` erzeugen eine XML-artige Umgebung `<name>…</name>`. Das Formular und die Platzhalteranzeige der Kern-Bearbeitung nennen sie so.
- **Fehlerfälle:** Fehlt einem Vertragsnamen der Wert, wirft `vorlage_rendern` beim Rendern einen `KeyError`. Das passiert erst in der Sitzung, nicht schon beim Speichern des Kerns.

### Zeitzone (`config/settings.py`)

- **Konfiguration:**
  - `TIME_ZONE` kommt aus der Umgebung, sonst gilt `Europe/Berlin`. Vorher lädt `load_dotenv` die `.env`; `.env.example` setzt `TIME_ZONE=Europe/Berlin`.
  - `USE_TZ = True`.
- **Invariante:** Nackte Wanduhrzeit aus `datetime-local`-Feldern gilt als Ortszeit.

### Gemeinsame Test-Helfer (`config/tests/`, `conftest.py`)

- `config/tests/formular.py`: `submit_knoepfe(antwort)` liefert Beschriftung und Formular-ID jedes Absendeknopfs. Ein `button` ohne `type` zählt als Absendeknopf, und das `form`-Attribut geht dem umschließenden Formular vor. Genutzt in `vignetten`, `simulation` und `erhebungen`.
- `config/tests/exportkontrakt.py`: `exportkontrakt_aus_adr_0029()` liest die Dateitabelle aus ADR-0029. Genutzt vom Export-Test in `erhebungen`.
- `conftest.py` (Wurzel): MD5-Hasher für alle pytest-Läufe.

## Befunde

### `static/tests/test_design_system.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_design_system_exposes_semantic_tokens` (17 Fälle) | umschreiben | Tautologisch: Die 17 Zuordnungen sind wörtlich aus `tokens.css` abgeschrieben. Das ist eine Assertion auf Quelltext. | Lint-Regel über alle CSS-Dateien: Jede mit `var(--x)` benutzte Custom Property ist irgendwo als `--x:` deklariert. Das fängt einen Tippfehler oder einen gelöschten Token in jeder Datei. Heute schlägt die Regel bei `--radius-sm` fehl, deshalb erst nach #374 umsetzen. Die Zuordnung Token → PHSG-Farbe selbst bleibt ungetestet; sie steht in ADR-0024 und in `tokens.css`. |
| `test_design_system_exposes_shared_component` (18 Fälle) | streichen | Quelltext: prüft, ob Selektorstrings in `main.css` vorkommen. Ein fehlender Selektor ändert nichts, was pytest beobachten kann. | Keiner nötig. Die Existenz eines Selektors ist keine Zusage an einen Aufrufer. Die Klassen in den Templates prüfen die View-Tests, wo sie Verhalten tragen (`area--…` in `konten/tests/test_navigation.py::BereichszuordnungTests`). |
| `test_card_body_stays_on_the_neutral_surface` | streichen | Quelltext; die erste Zusicherung trifft jede beliebige Regel mit `background: var(--color-surface)`. | Keiner; kein über HTTP beobachtbares Verhalten. |
| `test_form_controls_are_styled_without_a_form_wrapper` | streichen | Quelltext samt Zeilenumbruch (`"input,\ntextarea,\nselect {"`); ein Umformatieren bricht den Test. | Keiner. |
| `test_feature_styles_only_consume_semantic_color_tokens` | behalten | Lint-Regel über alle Dateien einer Art, ausdrücklich erlaubt (CODING_STANDARDS). | Inline-Styles in Templates prüft sie nicht, siehe #375. |
| `test_main_layout_exposes_eight_column_grid` | streichen | Startbefund bestätigt: Rasterspalten, `column-gap` und `max-width` sind wörtlich aus drei Dateien abgeschrieben. | Keiner. |
| `test_page_sections_follow_the_main_area_not_the_viewport` | umschreiben | Fünf der sechs Zusicherungen sind abgeschriebene Deklarationen. Die letzte („keine `@media`-Regel nennt `.page-section`/`.field-grid`“) ist eine echte Regel, prüft aber nur `page.css`. | Lint-Regel über alle CSS-Dateien: Kein `@media`-Block nennt `.page-section` oder `.field-grid`, denn Seitenabschnitte brechen am Hauptbereich um, nicht am Viewport. Die übrigen Zusicherungen fallen weg. |
| `test_three_fields_keep_three_columns_at_medium_width` | streichen | Quelltext; hängt zusätzlich an der Reihenfolge der `@container`-Blöcke (`split`). | Keiner. |
| `test_form_actions_stay_visible_at_the_top` | streichen | Startbefund bestätigt: `z-index: 2`, `order: -1` und `position: sticky` sind wörtlich abgeschrieben. `"box-shadow" not in` prüft eine Abwesenheit. | Keiner. |
| `test_feature_styles_use_spacing_tokens` | behalten | Lint-Regel über alle Dateien. | Sie liest nur `static/css/` und erkennt nur `px`. Feste `rem`-Abstände wie in den Inline-Styles aus #375 fielen ihr auch dort nicht auf. |
| `test_markdown_text_steps_its_headings_below_the_section_head` | behalten | Relationale Regel (fallend, verschieden, kleiner als der Kopf). Die Erwartung ist nicht abgeschrieben. Der Regex hängt am Selektor `.markdown-text.markdown-text hN`; das ist der Preis, eine Größenrelation überhaupt zu prüfen. | – |
| `test_szenentext_headings_stand_above_the_scene_text` | behalten | Wie oben, für `sitzung.css`. | – |
| `test_markdown_text_is_shielded_against_page_heading_rules` | streichen | Quelltext: Selektoren in `markdown-text.css` und der Pfad im `<link>` von `base.html`. | Die doppelten Selektoren setzen die beiden Staffeltests voraus; ihr Regex findet sonst keine Größe und der Test bricht. Das Einbinden in `base.html` ist Template-Quelltext; ohne Browsertest beobachtet es niemand. |
| `test_aktive_navigation_traegt_die_bereichsfarbe` | streichen | Quelltext: ganze Regelblöcke samt Einrückung und Zeilenumbrüchen sind abgeschrieben. | Keiner. Die Zuordnung Sidebar-Gruppe → Bereich steht in ADR-0024. Die Seiten-Bereiche prüft `BereichszuordnungTests` über HTTP. |
| `test_zeilenlink_tabelle_ist_opt_in_und_behaelt_trennlinien` | streichen | Quelltext; `"vignette-index-table tbody" not in` prüft die Abwesenheit einer entfernten Regel (totes Gewicht). | Keiner. |
| `test_zeilenaktion_liegt_ueber_dem_zeilenlink` | streichen | Quelltext (`z-index: 1`, Hover-Farbe). | Keiner. |

**Startbefund Design-System: bestätigt.**

- Bleiben sollen die Regeln über alle Dateien: semantische Tokens, das Abstandsraster und die relational gestaffelten Überschriften.
- Zwei Regeln kommen dazu: „Jede benutzte Custom Property ist deklariert“ und „Seitenabschnitte nur mit Container-Queries“. Sie ersetzen einzelne Abschriften.
- Der Rest fällt weg. Visuelles Verhalten wie Sticky-Leiste, Stapelreihenfolge oder Spaltenzahl beobachtet pytest nicht. Dafür bräuchte es Browsertests, und die hat das Projekt nicht.

### `config/tests/test_eigentuemer_kreis_contract.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_anlegen_traegt_genau_eine_eigentuemerin_ein`, `test_austritt_entfernt_solange_eine_eigentuemerin_bleibt`, `test_sichtbar_sind_die_eigenen_bestaende_und_der_administration_alle`, `test_kandidatenliste_nennt_die_rolle_und_die_administration`, `test_einzige_eigentuemerin_eines_aktiven_bestands_ist_nicht_loeschbar`, `test_eine_von_zwei_eigentuemerinnen_ist_loeschbar` | behalten | Startbefund bestätigt: Vorbild der Suite. Parametrisiert über `bestandsmodelle()`, nur äußeres Verhalten, Erwartungen aus festen Konten. | – |
| `test_austritt_der_letzten_eigentuemerin_aendert_nichts` | umschreiben | Implementation-coupled: Der Fall `stillgelegt` patcht `ist_aktiv` am eigenen Modell (`monkeypatch.setattr(modell, "ist_aktiv", …)`). Damit hält er fest, dass `austreten` die Methode nicht ruft. | Nur den Fall `aktiv` behalten, ohne Patch. Den stillgelegten Bestand deckt `konten/tests/test_eigentuemerschaft.py::test_archivierter_bestand_behaelt_seine_letzte_eigentuemerin` über einen echt archivierten Bestand. Ein Modell reicht, weil `austreten` nur einmal in der gemeinsamen Basis in `konten/eigentuemerschaft.py` steht. |

Hinweis für die App-Reviews (#326 bis #331): Diese Datei ist der deckende Ersatz für die einzelnen `sichtbar_fuer`-Tests der Historien und Bestände:

- `training/tests/test_models.py::test_sichtbar_fuer_liefert_eigene_trainings_und_alle_fuer_administration`
- `erhebungen/tests/test_models.py::test_sichtbar_fuer_liefert_nur_eigene_erhebungen` und `…_alle_erhebungen_fuer_administration`
- `fragebogen_items/tests/test_fragebogen_item_models.py::…test_sichtbar_fuer_liefert_nur_den_eigentuemer_kreis` und `…_alle_historien_fuer_administration`

Die Fassungs-Querysets (`Vignette.objects`, `FragebogenItem.objects`) haben eine eigene `sichtbar_fuer`, die der Vertrag nicht abdeckt.

### `config/tests/test_eigentuemer_kreis_routen.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_hinzufuegen_fuehrt_ueber_das_eigentuemerinnen_segment` (4 Fälle) | streichen | Implementation-coupled: Das Pfadsegment ist keine öffentliche Zusage. Die Routen nehmen nur POST an, niemand verlinkt sie von Hand, und keine Dokumentation nennt sie. Der gleiche Name ist eine Konvention; das gemeinsame Include bekommt die Namen ausdrücklich übergeben und leitet sie nicht aus dem `app_label` ab. | Jede App ruft beide Routen per Namen und POST auf: `vignetten/tests/test_views.py::VignetteKoautorschaftViewTests`, `training/tests/test_views.py::TrainingKoautorschaftTests`, `erhebungen/tests/test_forschenden_views.py::ErhebungenKoForschendenViewTests`, `fragebogen_items/tests/test_views.py::FragebogenItemKoautorschaftViewTests`. Ein falscher Name lässt dort `reverse()` scheitern, und jede Detailseite rendert das Include mit beiden Namen. |
| `test_entfernen_fuehrt_ueber_das_eigentuemerinnen_segment` (4 Fälle) | streichen | wie oben | wie oben |

**Startbefund Routen: bestätigt.** Der Test prüft ein Implementierungsdetail.

### `config/tests/test_eigentuemerinnen_abschnitt.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| Hilfsfunktion `_vignette_mit_eigentuemerinnen` | umschreiben | Legt die Vignette über die private Naht `Vignette.objects._erstellen` an. Die Datei steht deshalb auf der SLF001-Übergangsliste in `pyproject.toml`. Es wird keine DB-Invariante geprüft, die die Naht rechtfertigen würde. | Einen finalen Simulationskern anlegen (`Simulationskern.objects.anlegen()`, `finalisieren()`), denn `anlegen` pinnt den aktuellen finalen Kern. Dann `Vignette.objects.anlegen(erste)` und danach `vignette.historie.eigentuemerinnen.add(*weitere)`. Danach den Eintrag aus der Übergangsliste streichen. |
| `test_tabelle_nennt_name_und_alle_rollen` | behalten | HTTP, Erwartungen als Literale. | – |
| `test_eigene_zeile_heisst_mich_entfernen_mit_erklaerung` | umschreiben | Leicht implementation-coupled: Die Markierung „(Sie)“ wird über den Klassennamen `eigentuemerinnen__sie` gesucht. | Den Zeilentext ohne Tags prüfen („ada (Sie)“). Der Rest bleibt: Entfernen-Route, „Mich entfernen“, Erklärsatz, `aria-label`. |
| `test_letzte_eigentuemerin_hat_keine_aktion` | behalten | – | – |
| `test_hinzufuegen_steht_unter_eigener_unterueberschrift` | umschreiben | Der Knopf wird mit Markup samt `class="button"` gesucht. | Den Knopf über `config.tests.formular.submit_knoepfe` prüfen: „Hinzufügen“ ist unter den Absendeknöpfen. Überschrift und Option bleiben wie bisher. |
| `test_ohne_moegliche_ergaenzungen_steht_ein_satz` | umschreiben | `assertNotContains(response, '<select name="konto">')` prüft eine Abwesenheit über einen genauen Markup-String. Eine andere Attributreihenfolge oder ein zusätzliches Attribut lässt den Test grundlos bestehen. | `assertNotContains(response, 'name="konto"')`, dazu der Satz wie bisher. |

Keine Schichtdoppelung: `vignetten/tests/test_views.py::VignetteDetailViewTests::test_zeigt_die_eigentuemerin_der_historie` und `training/tests/test_views.py::TrainingKuratierenTests::test_zeigt_den_eigentuemer_kreis` prüfen nur, dass ihre Seite den Abschnitt einbindet, nicht seinen Inhalt.

### `config/tests/test_prompt_umgebungen_contract.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_vignettenwerte_decken_sich_mit_beiden_vertraegen` | umschreiben | Vergleicht zwei Modulkonstanten miteinander. Die Richtung „Wert ohne Vertragsnamen“ ist nicht beobachtbar, weil `vorlage_rendern` nur benutzte Platzhalter einsetzt. Der echte Fehlerfall ist der `KeyError` beim Rendern. | Über die Schnittstelle: Ein Kern, dessen Prompt-Vorlage jeden Namen aus `VERTRAG_PROMPT` benutzt, besteht `full_clean()`. `vorlage_rendern(vorlage, prompt_platzhalter(vignette))` liefert dann einen Text ohne `$`. Für die Rahmenhandlung dasselbe mit `VERTRAG_RAHMEN` über `sitzungen.durchlauf.rahmenhandlung_rendern`. Der Vertrag dient dabei als Eingabe, nicht als Erwartung. |
| `test_platzhalter_mit_umgebung_deckt_sich_mit_der_erzeugten_ausgabe` | behalten | Die Erwartung kommt aus der erzeugten Ausgabe, nicht aus der Konstante. Der Test hält zwei von Hand gepflegte Listen über die App-Grenze zusammen, und die Liste speist einen sichtbaren Hinweis in der Kern-Bearbeitung. | Beide Zusicherungen bleiben. Die zweite (`<= VERTRAG_PROMPT`) folgt nicht aus dem Zieltest oben, denn der sichert nur „jeder Vertragsname hat einen Wert“. Sie hält fest, dass der Hinweis nur Platzhalter nennt, die `clean()` in einer Vorlage zulässt. |

### `config/tests/test_seitenvokabular.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `setUp` | umschreiben | Legt die finale Vignette über `Vignette.objects._erstellen` an (SLF001-Übergangsliste). | Öffentlicher Weg: `Vignette.objects.anlegen`, die Pflichtfelder setzen und `finalisieren()` aufrufen. Das Muster `_finale_vignette_anlegen` steht schon in `training/tests/test_abschriften.py` und drei Dateien in `erhebungen/tests`. Ein gemeinsamer Helfer in `config/tests/` würde die vier Kopien ersetzen; das gehört in das Umsetzungsticket. |
| `_knoepfe` | umschreiben | Eigener Regex-Parser für Absendeknöpfe neben `config.tests.formular.submit_knoepfe`. Er übersieht Knöpfe ohne ausdrückliches `type="submit"`. | `submit_knoepfe(antwort)` benutzen, nur die Beschriftungen auswerten. |
| `test_seiten_zeigen_ueberzeile_titel_und_knopf` | behalten | Die Erwartungen sind Literale aus der Entscheidung zu #287 (Spec), der Weg ist HTTP. | – |
| `test_einwilligung_nennt_training_starten` | behalten | Eigener Weg (POST auf `training:wahl`). | – |
| `test_vignettenformular_ohne_schritt_fuer_schritt` | streichen | Totes Gewicht: prüft die Abwesenheit eines entfernten Titels. | `test_seiten_zeigen_ueberzeile_titel_und_knopf` prüft für `vignetten:anlegen` positiv Überzeile und Titel „Vignette anlegen“. |
| `test_seitenkoepfe_und_knoepfe_sagen_anlegen_statt_erstellen` | streichen | Abwesenheit eines Worts auf ganzen Seiten, beschränkt auf drei willkürliche URLs. Bricht bei jedem Hilfetext mit „erstellen“, ohne dass das Vokabular verletzt wäre. | `test_seiten_zeigen_ueberzeile_titel_und_knopf` prüft „… anlegen“ positiv auf allen Anlegeseiten und Knöpfen. Die Sidebar-Einträge („Neue Vignette anlegen“, „Neues Training anlegen“, „Neue Erhebung anlegen“) prüft `konten/tests/test_navigation.py::SidebarNavigationTests`. |

**Startbefund Seitenvokabular: verworfen.**

- Mit den View-Tests der Apps gibt es keine Doppelung. Keine App prüft Überzeile oder `h1` ihrer Seiten.
- Die einzigen Überschneidungen sind Knopfbeschriftungen. `erhebungen/tests/test_forschenden_views.py::ErhebungenFinalisierenTests` prüft „Konfiguration speichern“ und `simulation/tests/test_kern_view.py` prüft „Entwurf ziehen“. Beide prüfen aber, *wann* der Knopf erscheint, also eigenes Verhalten.

### `config/tests/test_startseite.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_anonyme_navigation_bietet_den_login` | behalten | Einziger Test der Sidebar ohne Anmeldung. Die `konten`-Tests melden immer ein Konto an. Belegt zugleich, dass die Startseite ohne Anmeldung erreichbar ist (`assertContains` verlangt Status 200). | – |
| `test_angemeldete_navigation_bietet_den_logout` | behalten | – | – |
| `test_teilnehmerin_sieht_nur_teilnahmenavigation` | streichen | Schichtdoppelung: Die Sidebar ist auf jeder Seite dieselbe; die Startseite trägt nichts Eigenes bei. | `konten/tests/test_navigation.py::SidebarNavigationTests::test_teilnehmerin_sieht_nur_teilnahme_links` |
| `test_sonderrollen_sehen_ihre_bereiche` | streichen | Schichtdoppelung wie oben. | `SidebarNavigationTests` (`test_autorin_…`, `test_ausbilderin_…`, `test_forschende_…`, `test_administratorin_…`) und `test_navigation_berechnet_sichtbarkeit_aus_kontorollen`, der die Sichtbarkeit je Rollenkombination festhält. |
| `test_rollenspalten_folgen_der_farbcodierung` | streichen | Implementation-coupled: sucht Klassenstrings (`welcome__spalte area--…`) in einem statischen Template, in dem nichts berechnet wird. Der Test liest damit `start.html` über HTTP ab. | Keiner nötig. Die Bereichsfarbe berechneter Seiten prüft `konten/tests/test_navigation.py::BereichszuordnungTests`. |
| `test_startseite_nennt_die_plattform_ohne_anmeldung` | streichen | Tautologisch: Die Zusicherungen sind Wörter aus dem statischen `start.html`. | Dass die Startseite ohne Anmeldung erreichbar ist und „Anmelden“ anbietet, belegt `test_anonyme_navigation_bietet_den_login`. |
| `test_loginseite_rendert_das_passwortfeld` | umschreiben | Die Zusicherung `class="site-sidebar"` hängt am Klassennamen. | Den Seitenrahmen über die Landmarke prüfen (`aria-label="Hauptnavigation"`, sie ist auch für Screenreader zugesagt), dazu `name="password"` wie bisher. |
| `test_direkter_login_fuehrt_zur_startseite` | behalten | HTTP, eigenes Template, Erwartung als fester Routenname. | – |

### `config/tests/test_zeitzone_contract.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_zeitzone_kommt_aus_der_umgebung_und_faellt_auf_ortszeit_zurueck` | streichen | Startbefund bestätigt: Die Erwartung wird wie in `settings.py` berechnet (`os.environ.get("TIME_ZONE", "Europe/Berlin")`), der Test besteht per Konstruktion. Den Rückfall prüft er nicht einmal: `load_dotenv` setzt `TIME_ZONE` vorher aus `.env`. | `erhebungen/tests/test_forschenden_views.py::StichprobenAnlegenTests::test_liest_den_eingegebenen_zeitraum_als_ortszeit` prüft die Folge aus dem Docstring über HTTP mit festen UTC-Literalen: Die Eingabe gilt als Ortszeit, nicht als UTC. Die Zone setzt er selbst (`override_settings(TIME_ZONE="Europe/Berlin")`), den Wert aus `settings.py` prüft er also nicht. Mit `USE_TZ = False` schlüge der Vergleich mit den aware-Datumswerten fehl. Der Rückfallwert selbst ist eine Konfigurationszeile; der Prozess lädt `.env` vor dem Rückfall, also lässt er sich nicht hermetisch testen. |

### Gemeinsame Test-Helfer

| Datei | Urteil | Grund |
|---|---|---|
| `config/tests/formular.py` | behalten | Schmale Schnittstelle (`submit_knoepfe`), in drei Apps benutzt. Ein zweiter Nutzer innerhalb dieses Bereichs kommt mit dem Umschreiben von `test_seitenvokabular.py` und `test_eigentuemerinnen_abschnitt.py` dazu. |
| `config/tests/exportkontrakt.py` | behalten | Kontrakt aus einer externen Spec (ADR-0029), von #321 ausdrücklich erlaubt. |
| `conftest.py` | behalten | Testweite Einstellung, prüft nichts. |
| `config/tests/aufbau.py` | behalten | Nachtrag (#396): Aufbau über die öffentlichen Manager- und Lebenszyklusmethoden aus #392, in mehreren Apps benutzt. |
| `config/tests/sprachmodell.py` | behalten | Nachtrag (#396): Aufzeichnung der Anfragen am Fake-Sprachmodell je Test aus #379, in drei Apps benutzt. |

### `config/tests/test_aufbau.py` (Nachtrag #396)

Die Datei kam mit #392 nach dem Review dazu.

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_konto_traegt_die_uebergebenen_rollen`, `test_konto_ohne_rolle_traegt_keine`, `test_konto_mit_unbekannter_rolle_scheitert` | behalten | Prüfen den Helfer über `Konto.rollen()` und die Abweisung eines unbekannten Rollennamens; Erwartungen als Literale. | – |
| `test_finaler_kern_ist_final`, `test_finaler_kern_liefert_beim_zweiten_aufruf_denselben` | behalten | Äußeres Verhalten des Helfers: Zustand und Wiederverwendung des finalen Kerns. | – |
| `test_aktive_modell_konfiguration_belegt_die_verwendung` | behalten | Liest die Belegung über den öffentlichen Manager (`belegte`). | – |
| `test_vignetten_entwurf_ist_ein_entwurf`, `test_vignetten_entwurf_liegt_im_bestand_des_kontos` | behalten | Zustand und Sichtbarkeit über `sichtbar_fuer`. | – |
| `test_finale_vignette_ist_final_und_pinnt_einen_finalen_kern`, `test_finale_vignette_uebernimmt_uebergebene_felder`, `test_finale_vignette_weist_ein_unbekanntes_feld_ab` | behalten | Die Zusagen des Helfers aus #391 (legt den Kern bei Bedarf an, Felder überschreibbar), Erwartungen als Literale. | – |

## Folge-Issues

- #374 `--radius-sm` wird in `vignette-form.css` benutzt, aber nirgends deklariert. Die vorgeschlagene Lint-Regel „jede benutzte Custom Property ist deklariert“ setzt die Behebung voraus.
- #375 `training/templates/training/detail.html` umgeht das Design-System mit Inline-Styles: undefinierte Farb-Tokens (`--color-grey-…`, `--color-primary-600`), feste `rem`-Abstände statt des Rasters, Hover per `onmouseover`. Die Lint-Regeln lesen nur `static/css/`.
