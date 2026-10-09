# Testreview: Erhebungen – Verwaltung und Export

Bereich aus #326 (Spec #321). Geprüft ist `erhebungen/tests/test_forschenden_views.py` (97 Tests, 3 637 Zeilen). Die Modelltests (`test_models.py`) und die Teilnahme gehören zu #327 (`docs/testreview/erhebungen-teilnahme.md`). Hier stehen sie nur als Ersatztests oder als Gegenstück beim Prüfen auf Schichtdoppelung.

Für die Zeit gilt #324: Kein Test dieser Datei patcht `jetzt`, `timezone.now` oder eine andere Zeitfunktion. Laufende, vergangene und künftige Stichproben entstehen über ihre Daten (`timezone.now() ± 1 Tag`). Das Ende eines Erhebungszeitraums legt hier also kein Test über einen Patch fest. *Umschreiben* mit `time-machine` heißt hier etwas anderes: Ein Zeitstempel im Export soll als festes Literal erwartet werden statt über eine Nachbildung der Formatierung. Das braucht `time-machine` als Abhängigkeit; sie kommt mit #349. Für Migrationstests gilt #325; in dieser Datei gibt es keine.

Fünf Lesarten gelten für das ganze Dokument:

- **Kontext der Zuordnungslisten:** Die Detailseite gibt `aufgenommene_daten`, `verfuegbare_daten`, `nach_sitzung_…` und `am_ende_…` unverändert per `json_script` an `static/js/zuordnungsliste.js`. Diese Zeilen sind der Vertrag zum Skript. Tests, die sie über `response.context` lesen, sind deshalb nicht an die Implementierung gekoppelt. #328 urteilt bei den Fach- und Thema-Vorschlägen der Vignette genauso.
- **Positionen über das Modell lesen:** Die Reihenfolgelogik (`_einreihen`, `_reihenfolge_schreiben`) lebt in der View; einen Modelltest dafür gibt es nicht. Item-Zeilen tragen ihre `position`, und die Item-Tests lesen sie dort. Vignetten-Zeilen tragen nur ihre Reihenfolge, nicht die Nummer. Dass die Nummern bei 1 beginnen und lückenlos sind, zeigt also keine Seite. Diese Nummern darf ein View-Test über `Erhebungsvignette.objects` lesen. Das ist keine Schichtdoppelung und auch kein „Verifying through external means“ (CODING_STANDARDS.md), weil keine Schnittstelle sie zeigt. Die Reihenfolge allein zeigt die Seite; ein Test liest sie aus `aufgenommene_daten`.
- **Zustand nach einer Aktion:** Liest ein Test den Zustand nach einem POST über `refresh_from_db()`, obwohl die Detailseite ihn zeigt, prüft er an der Schnittstelle vorbei („Verifying through external means“, CODING_STANDARDS.md). Die Detailseite zeigt Status-Badge, Texte, `randomisierung-daten` und die Phase der Stichproben. Der Zieltest liest den Zustand dort. Bei den Sperrtests heißt „Zustand unverändert“ entsprechend: Badge und Zeilen der Detailseite bleiben gleich.
- **Datenspur im Export-Setup:** Die Export-Tests legen Sitzungen, Gesprächsschritte, Itemblöcke und Antworten direkt über die Modelle an, mit Status und Werten, die der Ablauf nur mühsam herstellt (alle vier Sitzungsstatus, ein antwortloser Schritt). Das ist zulässig: `datenspur_zip` liest nur Zeilen. Wie die Zeilen entstehen, prüft #327.
- **Schreibweise im Export:** #327 lässt Choice-Mitglieder wie `Sitzung.Status.ABGESCHLOSSEN` als Erwartung stehen, wo es um den entstehenden Zustand geht. Die Schreibweise sichere der Export-Kontrakt. Im Export ist die Schreibweise selbst die Zusage (ADR-0029). Ein Export-Test erwartet sie deshalb als Literal (`"abgeschlossen"`), nicht über die Konstante.

## Schnittstelle

### Zugang (`erhebungen/views.py`, `erhebungen/urls.py`)

- **Aufrufe:** alle Routen unter `/erhebungen/eigene/`: `liste`, `anlegen`, `detail`, `export`, `eigentuemerin_hinzufuegen`, `eigentuemerin_entfernen`, `vignette_hinzufuegen`, `vignette_entfernen`, `vignette_verschieben`, `reihenfolge_umschalten`, `item_hinzufuegen`, `item_entfernen`, `item_verschieben`, `item_umhaengen`, `konfiguration_speichern`, `loeschen`, `finalisieren`, `zurueckziehen`, `archivieren`, `entarchivieren`, `stichprobe_anlegen`, `stichprobe_archivieren`.
- **Invarianten:**
  - Jede Route verlangt eine Anmeldung (anonym: Weiterleitung zum Login) und die Rolle Forschende:r oder die Administration (ADR-0033), sonst 403.
  - Eine Erhebung außerhalb von `Erhebung.objects.sichtbar_fuer(konto)` ergibt 404, auf jeder Route mit `pk`.
  - Alle Routen außer `liste`, `anlegen`, `detail` und `export` nehmen nur POST an; GET ergibt 405.
- **Fehlerfälle:** siehe die einzelnen Abschnitte.
- **Konfiguration:** keine eigene.

### Liste und Anlegen

- **Aufrufe:** `GET erhebungen:liste`; `GET/POST erhebungen:anlegen` mit `ErhebungAnlegenFormular` (Feld `name`).
- **Invarianten:**
  - Die Liste zeigt die sichtbaren Erhebungen mit Status-Badge (`badge--draft`, `badge--final`, `badge--archived`). Der Name ist der Link der Zeile auf die Detailseite. Nur Entwürfe tragen den Lösch-Knopf mit der Beschriftung „<Name> löschen“.
  - Die Liste spielt kein Teilnahme-Token aus der Browser-Session in die Seitenleiste.
  - Anlegen legt einen Entwurf mit dem Konto als Eigentümerin an und leitet auf dessen Detailseite. Der Name wird an den Rändern gekürzt.
- **Fehlerfälle:** leerer oder zu langer Name: Status 200, Meldung am Feld, Eingabe bleibt stehen, nichts wird angelegt.
- **Konfiguration:** keine.

### Detailseite (`erhebungen:detail`)

- **Aufrufe:** `GET erhebungen:detail`.
- **Invarianten:**
  - Status-Badge und Bereich `area--research`.
  - Im Entwurf: Zuordnungslisten für Vignetten und beide Andockpunkte. Jede Zeile trägt `pk` und `label`, Vignetten dazu `fach` und `thema`. Aufgenommene Zeilen haben `verschieben_url` und `entfernen_url`, Items dazu `position` und, solange das Item nicht am anderen Andockpunkt hängt, `umhaengen_url`. Angebotene Zeilen haben `einfuegen_url`, Items dazu `badge` („schon am Ende“ bzw. „schon nach jeder Sitzung“). Angeboten werden nur eigene finale, noch nicht aufgenommene Fassungen.
  - Die Reihenfolgeregel geht als `randomisierung-daten` an das Skript.
  - Drei Texte (Instruktion, Einwilligung, Abschluss) als Lesefeld mit „Bearbeiten“ oder „Text schreiben“, Markdown-Feld mit Vorschau im Profil Informationstext, ein gemeinsames Formular `erhebung-konfiguration` für alle Speichern-Knöpfe und für „Finalisieren“, Verlassen-Warnung.
  - Final und archiviert: Listen ohne Auswahl und ohne Aktions-URLs, Texte gerendert, leerer Text als „—“, gepinnte Modell-Konfiguration mit Anbieter, Sprachmodell und Parametern, ohne Basis-URL und Token.
  - Aktionen nur, wenn der Zustand sie erlaubt (`kann_zurueckgezogen_werden`, `kann_archiviert_werden`, `kann_entarchiviert_werden`).
  - Stichproben mit absolutem Teilnahme-Link, Phase (archiviert mit Badge), Zahl der Teilnahmen, der abgelehnten Sprachmodelle und der flüchtigen Teilnahmen. „Archivieren“ nur bei datenfreien, nicht archivierten Stichproben.
  - Der Link „Datenspur herunterladen“ erscheint, sobald eine Stichprobe besteht, auch nach dem Archivieren.
- **Fehlerfälle:** keine eigenen.
- **Konfiguration:** keine.

### Eigentümer-Kreis-Routen

- **Aufrufe:** `POST eigentuemerin_hinzufuegen` mit `konto`, `POST eigentuemerin_entfernen/<konto_pk>`. Der Kreis selbst ist `konten/eigentuemerschaft.py` (`moegliche_ergaenzungen`, `austreten`), der Abschnitt das gemeinsame Include (#332).
- **Invarianten:** Hinzufügen nimmt nur Konten aus `moegliche_ergaenzungen()` auf und leitet auf die Detailseite. Wer sich selbst erfolgreich austrägt, landet auf der Liste; sonst bleibt es bei der Detailseite. Der Kreis bleibt auch bei finalen und laufenden Erhebungen änderbar.
- **Fehlerfälle:** Konto außerhalb der Kandidaten: 404. Austritt der letzten Eigentümerin: keine Änderung, Weiterleitung auf die Detailseite.
- **Konfiguration:** keine.

### Entwurf zusammenstellen

- **Aufrufe:**
  - Vignetten: `POST vignette_hinzufuegen` (optional `position`), `vignette_entfernen`, `vignette_verschieben` (`position`). Antwort: Weiterleitung auf die Detailseite.
  - Items: `POST item_hinzufuegen/<item_pk>/<andockpunkt>` (optional `position`), `item_entfernen`, `item_verschieben` (`position`), `item_umhaengen`. Antwort: Weiterleitung auf die Detailseite (ADR-0051).
  - `POST reihenfolge_umschalten` mit `randomisierung` (`fest` oder `zufällig`).
  - `POST konfiguration_speichern` mit den drei Texten.
- **Invarianten:**
  - Positionen sind 1-basiert und lückenlos. Einfügen ohne Position hängt ans Ende, mit Position an diese Stelle; eine Position außerhalb der Liste wird an den Rand geklemmt. Entfernen und Umhängen schließen die Lücke. Umhängen setzt ans Ende des anderen Andockpunkts.
  - Eine Item-Fassung steht je Andockpunkt höchstens einmal, an beiden Andockpunkten darf sie stehen.
  - Der Schalter ändert nur die Regel, die Positionen bleiben. Bei zufälliger Reihenfolge landet eine neue Vignette am Ende.
  - `konfiguration_speichern` übernimmt nur die drei Texte.
- **Fehlerfälle:**
  - Fremde oder nicht finale Fassung: 404. Item doppelt am Andockpunkt oder Umhängen auf einen besetzten Andockpunkt: 409. Fehlende oder nicht ganzzahlige Position beim Verschieben: 400. Unbekannte Regel: 400. Unbekannter Andockpunkt: 403.
  - Erhebung kein Entwurf: Jede dieser Routen leitet ohne Änderung auf die Detailseite und zeigt dort eine Meldung (ADR-0051). Ein `ValidationError` des Modells nimmt denselben Weg.
- **Konfiguration:** keine.

### Lebenszyklus-Aktionen

- **Aufrufe:** `POST finalisieren` (übernimmt vorher die gesendeten Texte), `zurueckziehen`, `archivieren`, `entarchivieren`, `loeschen`. Die Regeln liegen in den Modellmethoden (#327).
- **Invarianten:** Jede Aktion leitet auf die Detailseite, `loeschen` auf die Liste. Ein `ValidationError` des Modells erscheint als Meldung auf der Detailseite.
- **Fehlerfälle:** `loeschen` auf einer nicht-Entwurfs-Erhebung leitet mit Meldung auf die Liste (ADR-0051).
- **Konfiguration:** keine.

### Stichproben

- **Aufrufe:** `POST stichprobe_anlegen` mit `beginn` und `ende` (Wanduhrzeit aus `datetime-local`), `POST stichprobe_archivieren/<stichprobe_pk>`.
- **Invarianten:** Anlegen nur unter einer finalen Erhebung; im Entwurf und im Archiv leitet die Route still auf die Detailseite. Zeitpunkte ohne Zone gelten in `TIME_ZONE`. Archivieren läuft über `Stichprobe.archivieren()`.
- **Fehlerfälle:** ungültige Zeitpunkte oder Ende vor Beginn: 400 als nackte Textantwort (#386). Archivieren einer datentragenden Stichprobe: Meldung auf der Detailseite.
- **Konfiguration:** `TIME_ZONE`.

### Export (`erhebungen:export`, `erhebungen/export.py`)

- **Aufrufe:** `GET erhebungen:export` liefert `datenspur_zip(erhebung)` als `application/zip` mit dem Dateinamen `erhebung-<pk>-<slug des Namens>-<UTC-Zeitstempel %Y%m%dT%H%M%SZ>.zip`.
- **Invarianten:**
  - Genau die fünfzehn Dateien und Spalten der Tabelle in ADR-0029, je mit Kopfzeile, auch ohne Datenzeile. Ohne Datenbestand haben nur `erhebung.csv` (eine Zeile) und `likert_skala.csv` (sechs Stufen) Datenzeilen.
  - RFC 4180, UTF-8; `NA` für `NULL`, Leerstring bleibt leer; Wahrheitswerte `True`/`False`; Zeitstempel ISO 8601 in UTC, sekundengenau, `+00:00`; JSON-Parameter als JSON-Text; Bilder als Pfad.
  - Nur Zeilen dieser Erhebung: keine Trainingssitzungen, keine Sitzungen ohne Erhebungsbindung, keine Itemblöcke und Antworten anderer Erhebungen.
  - Fassungstabellen enthalten genau die referenzierten Vignetten (gezogen oder gespielt), Kerne (gespielt) und Konfigurationen (gepinnt oder gespielt), mit vollem Inhalt. `fragebogen_items.csv` enthält nur vorgelegte Fassungen.
  - Kein Anbieter-Token, keine Basis-URL, keine Transkriptions-Konfiguration.
  - Flüchtige Teilnahmen erscheinen mit Teilnahme- und Sitzungszeile, ohne Inhaltszeilen.
  - Die Zahl der Abfragen hängt nicht von der Zahl der Zeilen ab.
- **Fehlerfälle:** fremde Erhebung 404. Die Route liefert auch für einen Entwurf ohne Stichprobe ein wohlgeformtes Archiv; nur der Link fehlt dann. Darauf baut der Kontrakttest.
- **Konfiguration:** keine; der Zeitstempel im Dateinamen kommt aus der Systemzeit.

## Startbefunde

1. **Spaltenlisten neben dem Kontrakttest: bestätigt und erweitert.** `test_dateien_und_spalten_folgen_dem_kontrakt_aus_adr_0029` vergleicht Dateinamen *und* Kopfzeilen aller Dateien auf Gleichheit mit der Tabelle aus ADR-0029. Eine fehlende, zusätzliche oder umgestellte Spalte fällt dort auf. Die Kopfzeile schreibt `_csv_aus_objekten` unabhängig vom Datenbestand; ein leerer Export prüft sie also vollständig. Doppelt geprüft werden die Kopfzeilen von `gespraechsschritte.csv` und `diagnosen.csv` (`test_exportiert_gespraechsschritte_fehlversuche_und_diagnosen`), `item_antworten.csv`, `fragebogen_items.csv` und `likert_skala.csv`. Über die Startliste hinaus kommen dazu: `vignettenfassungen.csv` (`test_exportiert_nur_referenzierte_fassungen_mit_vollem_inhalt`) und `modellkonfigurationen.csv` (`test_exportiert_den_anbieter_und_kein_zugangsdatum`). Dazu zwei Abwesenheitsprüfungen, die derselbe Vergleich abdeckt: `einwilligung_erteilt` in `teilnahmen.csv` und `offene_spanne_seit` in `sitzungen.csv`. Bei `sitzungen.csv` steht keine Spaltenliste, nur diese eine Abwesenheit. Dasselbe gilt für die Dateiliste: `test_exportiert_die_transkriptions_konfiguration_nicht` und die `namelist`-Prüfung im Gesprächsschritt-Test. Alle diese Asserts werden gestrichen; die Zeilenprüfungen bleiben.
2. **ZIP-Lesen als Helfer: bestätigt.** In 14 Blöcken `with ZipFile(BytesIO(...))` steht 20-mal `TextIOWrapper(zip_datei.open(name), encoding="utf-8")`, 18-mal in `csv.DictReader` und zweimal in `csv.reader`; ein Test hat sich schon einen lokalen `_zeilen` gebaut. Vorschlag: ein Helfer in `erhebungen/tests/`, etwa `export_lesen(response) -> dict[str, list[dict[str, str]]]`, der alle Dateien des Archivs als Zeilen liefert. Der Kontrakttest braucht die Kopfzeilen; dafür reicht `list(zeilen[0])` nicht, weil leere Dateien keine Zeile haben. Er liest sie deshalb weiter selbst oder über einen zweiten Helfer `export_kopfzeilen(response)`. Mit dem Helfer fallen in den Export-Tests gut hundert Zeilen weg.
3. **Schichtdoppelung zu den Modelltests: geprüft, nur vereinzelt bestätigt.** Die Größe der Datei kommt nicht aus Doppelungen mit `test_models.py`. Der Export-Block umfasst 1 300 Zeilen, mehr als ein Drittel der Datei, und davon ist der größte Teil Setup der Datenspur. Dazu kommt wiederholtes Setup: 47-mal `groups.add(Group.objects.get(name="Forschende:r"))`, 27-mal `ModellKonfiguration.objects.aktivieren(...)` vor einem `finalisieren()`. Die meisten Lebenszyklus-Tests prüfen, was nur die View leistet: angebotene oder versteckte Aktionen, Meldung statt 500, Weiterleitung. Echte Doppelungen sind wenige: die Listen-Sichtbarkeit der Administration (`sichtbar_fuer`), das Wieder-Öffnen nach dem Zurückziehen und Zustandsprüfungen über `refresh_from_db()`, die die Seite selbst zeigt (Lesart oben). Sie sind unten einzeln geführt. Umgekehrt sind zwei View-Tests der einzige Beleg für Modellregeln: Archivieren einer datentragenden Stichprobe (`test_versteckt_datentragende_stichprobe_und_zeigt_guard_fehler`) und Zurückziehen bei datentragender archivierter Stichprobe (`test_datentragende_archivierte_stichprobe_versteckt_zurueckziehen`). Beide bleiben, #385 stützt sich auf sie. Vorschlag für das Setup: Helfer `_forschende(username)` und `_finale_erhebung(konto, name)` (aktiviert bei Bedarf eine Konfiguration und finalisiert). `_finale_vignette_anlegen` geht schon über den öffentlichen Weg. Es soll im gemeinsamen Helfer aufgehen, den #327, #328, #330 und #332 vorschlagen.

## Befunde

### `ErhebungenForschendenRollenTests`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_konto_ohne_forschendenrolle_erhaelt_auf_alle_forschenden_views_403` | umschreiben | Der Name verspricht alle Views, geprüft sind vier von 22 Routen. Anonymer Zugriff und GET auf POST-Routen sind gar nicht geprüft. | Ein Test über alle Forschenden-Routen aus `erhebungen.urls` (ohne `teilnahme/…`): Konto ohne Rolle bekommt 403, anonym geht es zum Login. Dazu GET auf jede POST-Route: 405. Vorbild sind die Zugriffstests der Vignetten (#328). |

### `ErhebungenAnlegenUndListeTests`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_anlegen_erstellt_eigenen_entwurf_und_liste_versteckt_fremde`, `test_administration_legt_eine_erhebung_an`, `test_anlegen_speichert_den_namen_ohne_randleerzeichen`, `test_anlegen_lehnt_ungueltige_namen_mit_meldung_am_feld_ab`, `test_anlegen_laesst_die_eingabe_nach_einem_fehler_stehen`, `test_anlegen_nennt_am_feld_wo_der_name_erscheint`, `test_liste_zeigt_kein_teilnahme_token_aus_der_browsersession` | behalten | HTTP, Verhalten laut docs/verhalten.md. Der Kontextzugriff auf `formular["name"].errors` belegt „Meldung am Feld“, was `assertContains` allein nicht kann. | – |
| `test_liste_traegt_bereichsfarbe_und_bekannte_badge_klassen` | umschreiben | `assertNotContains("badge--entwurf")` und `("badge--archiviert")` bewachen frühere Klassennamen (Abwesenheit). `area--research` gehört zur Bereichszuordnung, die `konten/tests/test_navigation.py::BereichszuordnungTests` für alle anderen Bereiche prüft. | Ohne die zwei `assertNotContains`. `erhebungen:liste` und `erhebungen:detail` als Zeilen mit Bereich `research` in `BereichszuordnungTests`; hier bleiben nur die drei Badge-Klassen. |
| `test_zeilen_sind_ueber_den_namen_verlinkt_und_nur_entwuerfe_haben_loeschknopf` | umschreiben | `button--secondary`, `button--danger` und „>Aktion<“ bewachen Entferntes. | Ohne diese drei `assertNotContains`. Der Rest bleibt. |
| `test_administration_sieht_fremde_erhebung_in_der_liste` | streichen | Schichtdoppelung: Die Liste ist `Erhebung.objects.sichtbar_fuer`; dass die Administration alles sieht, ist Sache des Eigentümer-Kreises. Dass sie den Forschungsbereich betritt, zeigt der Anlegen-Test. | `config/tests/test_eigentuemer_kreis_contract.py::test_sichtbar_sind_die_eigenen_bestaende_und_der_administration_alle` (Fall `Erhebung`) und `test_administration_legt_eine_erhebung_an`; dass die Liste den Kreis nutzt, zeigt `test_anlegen_erstellt_eigenen_entwurf_und_liste_versteckt_fremde` |

### `ErhebungenSichtbarkeitUndLoeschenTests`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_fremde_erhebung_ist_nicht_erreichbar` | behalten | 404 an der HTTP-Naht. Geht im umgeschriebenen Rollentest auf, wenn der auch fremde Erhebungen auf jeder `pk`-Route abdeckt. | – |
| `test_loescht_nur_eigenen_entwurf_und_bietet_finalen_keinen_loeschknopf` | umschreiben | Der Name verspricht „nur Entwurf“; geprüft ist aber nur, dass ein Entwurf verschwindet und der Knopf an der finalen Erhebung fehlt. Den Knopf prüft schon `test_zeilen_sind_ueber_den_namen_verlinkt_und_nur_entwuerfe_haben_loeschknopf`. Dass ein POST die finale Erhebung nicht löscht, prüft kein Test. | POST auf `loeschen` für Entwurf und finale Erhebung: Der Entwurf ist weg (Detailseite 404), die finale bleibt (Detailseite 200). Die Antwort auf den abgewiesenen POST nach #254. Ohne den Listenteil. |

### `ErhebungenKoForschendenViewTests`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_detail_nennt_die_erhebung` | behalten | Welches Artefakt der gemeinsame Abschnitt nennt, prüfen laut `config/tests/test_eigentuemerinnen_abschnitt.py` die Apps. | – |
| `test_hinzufuegen_gibt_ko_forschender_listen_und_editorzugriff` | umschreiben | Schichtdoppelung: Überschrift und Namen im Abschnitt prüft `test_eigentuemerinnen_abschnitt.py`. Dass eine hinzugefügte Eigentümerin bearbeiten darf, unterscheidet sie nicht von der ersten (#328 urteilt genauso). Das Speichern prüft `test_jeder_speichern_knopf_speichert_die_ganze_erhebung`. | POST leitet auf die Detailseite; danach sieht Grace die Erhebung in ihrer Liste und erreicht die Detailseite mit 200. Ohne Abschnitt-Inhalte und ohne den Speichern-Teil. |
| `test_selbstentfernung_uebergibt_finale_und_laufende_erhebung`, `test_nicht_eigentuemerin_loest_keinen_selbst_redirect_aus`, `test_teilen_laesst_nur_forschende_oder_administration_zu`, `test_administration_kann_fremde_erhebung_uebergeben` | behalten | Eigene Weiterleitungen und der 404 der View. Den Kreis lesen sie über die öffentliche Relation (Lesart aus #328). | – |
| `test_entfernen_der_letzten_eigentuemerin_wird_verweigert` | umschreiben | Schichtdoppelung: Dass der Kreis unverändert bleibt, ist `austreten` und prüft der Vertragstest. Eigen ist die Weiterleitung auf die Detailseite statt auf die Liste, und die prüft der Test nicht. | `assertRedirects(antwort, reverse("erhebungen:detail", …))`. Der Kreis ist gedeckt durch `config/tests/test_eigentuemer_kreis_contract.py::test_austritt_der_letzten_eigentuemerin_aendert_nichts`. |

### `ErhebungenEntwurfKonfigurierenTests`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_bietet_nur_eigene_finale_vignetten_zur_aufnahme_an` | streichen | Doppelung mit gleichem Aufbau (fremde finale, eigener Entwurf). `assertNotContains("Physik")` ist zudem schwach: Das Wort kann überall auf der Seite fehlen. | `test_haelt_fremde_und_unfertige_fassungen_aus_den_zeilen_heraus` (genaue Liste der angebotenen Zeilen) |
| `test_lehnt_fremde_und_unfertige_vignetten_ab` | behalten | 404 der View. Die Modellregel (`Erhebungsvignette.clean`) greift erst dahinter. | – |
| `test_nimmt_finale_vignette_auf_und_entfernt_sie_wieder`, `test_item_bleibt_am_anderen_andockpunkt_verfuegbar`, `test_badge_verschwindet_nach_entfernen_am_anderen_andockpunkt`, `test_doppelte_itemaufnahme_am_selben_andockpunkt_wird_abgelehnt`, `test_verschiebt_item_innerhalb_seines_andockpunkts_ohne_seitenwechsel` | behalten | HTTP und die Zeilen an das Skript (Lesarten oben). | – |
| `test_bibliothek_kennzeichnet_item_am_ende_nach_jeder_sitzung`, `test_bibliothek_kennzeichnet_item_nach_jeder_sitzung_am_ende` | umschreiben | Derselbe Test in zwei Richtungen; der erste prüft das Badge an der Zeile, der zweite nur irgendwo auf der Seite. | Ein Test, parametrisiert über beide Andockpunkte: Nach der Aufnahme an A trägt die angebotene Zeile an B `badge` „schon am Ende“ bzw. „schon nach jeder Sitzung“ und eine `einfuegen_url` für B. |
| `test_entfernen_schliesst_die_itemreihenfolge_lueckenlos` | streichen | Doppelung: Lückenloses Nachrücken nach dem Entfernen prüft der Umsortieren-Test über die `position` der Zeilen. | `test_entfernen_und_umhaengen_nach_umsortieren_gelingen` |
| `test_itemverwaltung_ist_nach_dem_zurueckziehen_wieder_offen` | streichen | Schichtdoppelung: Die View prüft nur `status == ENTWURF`; ein zurückgezogener Entwurf ist für sie ein Entwurf wie jeder andere. | `test_models.py::test_zurueckgezogene_erhebung_erlaubt_zuordnungen_wieder` und jeder Item-Test am Entwurf, etwa `test_item_bleibt_am_anderen_andockpunkt_verfuegbar`; dass Zurückziehen bearbeitbar macht, zeigt `test_zurueckziehen_macht_die_erhebung_wieder_bearbeitbar` |
| `test_stellt_zuordnungszeilen_mit_ihren_aktions_urls_bereit`, `test_haelt_fremde_und_unfertige_fassungen_aus_den_zeilen_heraus` | behalten | Vertrag der Zeilen an das Skript. | – |
| `test_detailseite_rendert_zuordnungslisten_ueber_include` | streichen | Implementation-coupled: `assertTemplateUsed` hält den Namen eines Includes fest. „>Hoch<“, „>Runter<“ und `name="vignetten"` bewachen entfernte Bedienelemente. | Keiner nötig: Dass die Listen erscheinen, zeigen die Zeilen- und Sperrtests. |
| `test_detailseite_traegt_bereichsfarbe_und_bekannte_badge_klasse` | umschreiben | Wie beim Listentest: `badge--entwurf` bewacht Entferntes; `area--research` gehört in `BereichszuordnungTests`. | Nur `badge--draft`. |
| `test_texte_erscheinen_gerendert_mit_bearbeiten_oder_text_schreiben` | umschreiben | `count=1 + 3` zählt den Knopf „Bearbeiten“ des Lesefelds zusammen mit den drei Umschaltern „Bearbeiten \| Vorschau“ aus `texte`. Ändert `texte` den Umschalter, bricht der Test ohne Änderung am Lesefeld. | Ohne die Bearbeiten-Zählung. Gerenderter Text, „Noch kein Text“ und „Text schreiben“ je zweimal, „Ganz anzeigen“ und das Textfeld bleiben. Den Umschalter prüft `test_entwurf_bietet_je_textfeld_hinweis_und_umschalter`. |
| `test_jeder_speichern_knopf_speichert_die_ganze_erhebung` | umschreiben | Die Knöpfe sind HTTP laut docs/verhalten.md. Die gespeicherten Texte liest er aber über `refresh_from_db()`, obwohl das Lesefeld der Detailseite sie zeigt (Lesart „Zustand nach einer Aktion“). | Die Prüfung der Knöpfe bleibt. Speichern mit `follow=True`; die drei Texte erscheinen gerendert auf der Detailseite. |
| `test_seite_warnt_vor_dem_verlassen_mit_ungespeicherten_aenderungen` | behalten | HTTP laut docs/verhalten.md; `data-ungespeichert-warnen` ist der Vertrag zum Skript. | – |
| `test_verschiebt_vignette_an_eine_neue_position`, `test_verschieben_ohne_position_wird_abgelehnt`, `test_umschalten_lehnt_unbekannte_regel_ab`, `test_fuegt_vignette_an_gewuenschter_position_ein`, `test_entfernen_schliesst_die_vignettenreihenfolge_lueckenlos`, `test_fuegt_item_an_gewuenschter_position_ein`, `test_haengt_item_an_den_anderen_andockpunkt_um`, `test_umhaengen_lehnt_doppelte_bindung_ab`, `test_entfernen_und_umhaengen_nach_umsortieren_gelingen` | behalten | Reihenfolgelogik der View über HTTP (Lesart „Positionen über das Modell lesen“). | – |
| `test_umschalten_bewahrt_die_reihenfolge_hin_und_zurueck` | umschreiben | Zugleich Ersatz für einen gestrichenen Modelltest aus #327. Die Regel liest er über `refresh_from_db()`, obwohl `randomisierung-daten` sie zeigt (Lesart „Zustand nach einer Aktion“). | Die Regel nach jedem Umschalten aus `randomisierung-daten` der Detailseite. Die Positionen weiter über `_vignettenpositionen()`. |
| `test_zufaellige_reihenfolge_nimmt_am_ende_der_liste_auf` | umschreiben | Prüft nur die Reihenfolge, nicht die Nummern, und liest sie über `Erhebungsvignette.objects`, obwohl die Seite sie zeigt (Lesart „Positionen über das Modell lesen“). | Die Reihenfolge aus `aufgenommene_daten` der Detailseite: `[zweite.pk, dritte.pk]`. |
| `test_schalter_setzt_nur_die_reihenfolgeregel` | umschreiben | Die Prüfung der Positionen wiederholt den Hin-und-zurück-Test. Die Regel liest er zusätzlich über `refresh_from_db()`, obwohl `randomisierung-daten` sie zeigt. | Ohne `_vignettenpositionen()` und ohne `refresh_from_db()`. Weiterleitung, „Zufällige Reihenfolge“ und `randomisierung-daten` bleiben. |
| `test_zufaellige_reihenfolge_blendet_nummern_und_positionswahl_aus` | streichen | Quelltext: prüft Alpine-Ausdrücke (`x-show="geordnet"`) im gerenderten Template. Das Verhalten liegt im Skript und hat keine Testnaht (#387). | Was der Server liefert, prüft `test_schalter_setzt_nur_die_reihenfolgeregel` (`randomisierung-daten`). |
| `test_konfiguration_speichern_laesst_die_regel_unberuehrt` | streichen | Totes Gewicht: prüft, dass ein früheres Formularfeld nicht mehr wirkt. `_konfiguration_uebernehmen` liest nur die drei Texte. | Keiner nötig: Dass Speichern die Texte schreibt, prüft `test_jeder_speichern_knopf_speichert_die_ganze_erhebung`. |

### `ErhebungsansichtAnbieterTests`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_zeigt_anbieter_sprachmodell_und_parameter`, `test_zeigt_weder_basis_url_noch_token` | behalten | HTTP. Dass Geheimnisse fehlen, ist eine Zusage (ADR-0036), keine Abwesenheit entfernten Codes. | – |

### `ErhebungenFinalisierenTests`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_finalisieren_sperrt_design_und_zeigt_gepinnte_konfiguration` | umschreiben | Zwei Zusicherungen können nicht scheitern: „Finale Vignetten aufnehmen“ steht in keinem Template, „>Entfernen<“ nur im Eigentümerinnen-Abschnitt bei mehreren Eigentümerinnen. `assertContains("Final")` besteht auf jeder Detailseite, weil dort „Finale Items je Andockpunkt“ steht. | Badge `<span class="badge badge--final">Final</span>`, `openrouter/forschung`, kein „Konfiguration speichern“ und kein `zuordnungsliste__einfuegen`. |
| `test_finalisieren_speichert_vorher_alle_felder` | umschreiben | Eigenes Verhalten der View: Felder vor dem Finalisieren speichern. Status und Texte liest er aber über `refresh_from_db()`, obwohl die finale Detailseite beides zeigt (Lesart „Zustand nach einer Aktion“). | Finalisieren mit `follow=True`: Badge `badge--final` und die drei Texte gerendert auf der Detailseite. Die Prüfung des Finalisieren-Knopfs bleibt. |
| `test_nicht_archivierte_stichprobe_versteckt_zurueckziehen`, `test_zurueckziehen_macht_die_erhebung_wieder_bearbeitbar` | behalten | Eigenes Verhalten der View: Aktion nur bei erlaubtem Zustand. | – |
| `test_datentragende_archivierte_stichprobe_versteckt_zurueckziehen` | behalten | Einziger Beleg für den Zweig „datentragend“ von `kann_zurueckgezogen_werden`; #385 stützt sich darauf. | – |

### `StichprobenAnlegenTests`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_legt_stichprobe_mit_zeitraum_und_teilnahme_link_an` | umschreiben | Tautologisch: `beginn` und `ende` erwartet er über `timezone.make_aware`, wie die View sie berechnet. Den Link baut er mit `build_absolute_uri(reverse(…))`, wie die View. Die Zeitumrechnung prüft der Ortszeit-Test mit Literalen. | Weiterleitung auf die Detailseite, die `http://testserver/erhebungen/teilnahme/<teilnahme_link>/` zeigt. Ohne `beginn` und `ende`. |
| `test_liest_den_eingegebenen_zeitraum_als_ortszeit`, `test_zeigt_phase_und_anzahl_teilnahmen_je_stichprobe`, `test_zaehlt_abgelehnte_sprachmodelle_und_speicherung_je_stichprobe`, `test_zeichnet_archivierte_stichproben_in_der_phasenspalte_aus`, `test_laesst_stichproben_nur_auf_eigenen_finalen_erhebungen_an` | behalten | HTTP, Erwartungen als Literale. Die Phase entsteht über die Daten der Stichprobe, ohne Zeitpatch. Die Zählungen sind Annotationen der View. | – |
| `test_lehnt_zeitraum_mit_ende_vor_beginn_ab` | behalten | Prüft die heutige 400. Ändert sich mit #386. Ungültige Zeitpunkte („Beginn und Ende müssen gültige Zeitpunkte sein.“) prüft kein Test; das gehört in den Zieltest von #386. | – |

### `ErhebungenArchivierenTests`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_archiviert_datenfreie_stichprobe_ueber_die_detailseite` | umschreiben | HTTP-Weg der Aktion. Das Ergebnis liest er über `refresh_from_db()`, obwohl die Phasenspalte der Detailseite es zeigt (Lesart „Zustand nach einer Aktion“). | Archivieren mit `follow=True`: Die Stichprobe trägt in der Phasenspalte `<span class="badge badge--archived">Archiviert</span>`, wie in `test_zeichnet_archivierte_stichproben_in_der_phasenspalte_aus`. |
| `test_versteckt_datentragende_stichprobe_und_zeigt_guard_fehler` | umschreiben | Einziger Beleg für den Guard „datentragend“ von `Stichprobe.archivieren`; #385 stützt sich darauf, der Test bleibt also erhalten. Dass nichts archiviert wurde, liest er über `refresh_from_db()` statt auf der Seite. | Meldung und fehlende Aktion bleiben. Die Phasenspalte der Detailseite zeigt kein `badge--archived`. |
| `test_archiviert_und_entarchiviert_finale_erhebung` | umschreiben | „Final“ ist kein Beleg: Es steht auf jeder Detailseite in „Finale Items je Andockpunkt“. Der Zustand wird zusätzlich über `refresh_from_db()` gelesen, obwohl die Seite ihn zeigt. | Nach Archivieren: Badge `badge--archived` und die URL von `entarchivieren`. Nach Entarchivieren: Badge `badge--final` und die URL von `archivieren`. Ohne `refresh_from_db()`. |
| `test_versteckt_erhebung_archivieren_bei_laufender_stichprobe`, `test_versteckt_entarchivieren_bei_laufender_stichprobe` | umschreiben | Aktion fehlt, Modellfehler erscheint als Meldung. Den Entarchivieren-Guard bei laufender Stichprobe prüft sonst kein Test. Die laufende Stichprobe entsteht über ihre Daten. Den unveränderten Status liest er aber über `refresh_from_db()`, obwohl die Seite nach der Weiterleitung das Badge zeigt (Lesart „Zustand nach einer Aktion“). | Fehlende Aktion und Meldung bleiben. Statt `refresh_from_db()`: Die Antwort trägt weiter `badge--final` bzw. `badge--archived`. |

### `ErhebungsExportTests`

Mit dem Helfer aus Startbefund 2 lesen alle Tests unten ihre Dateien über `export_lesen`; das ist bei *behalten* mitgemeint.

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_exportiert_erhebung_stichprobe_und_teilnahme_als_csvs` | umschreiben | `assertNotIn("einwilligung_erteilt", …)` prüft die Abwesenheit einer früheren Spalte (Startbefund 1). Das Format von `erstellt_am` kommt aus ADR-0029 und bleibt; #327 nennt diesen Test als Ersatz für `erstellt_am`. | Ohne die Abwesenheitsprüfung. |
| `test_exportiert_nur_referenzierte_fassungen_mit_vollem_inhalt` | umschreiben | Die Spaltenliste von `vignettenfassungen.csv` wiederholt den Kontrakt. Tautologisch: `finalisiert_am` erwartet er über `zweiter_kern.finalisiert_am.isoformat(timespec="seconds")`, die Formatierung des Exports. Die `assertNotIn` für die ungenutzte Vignette und Konfiguration folgen schon aus den Mengen-Gleichheiten davor. | Ohne Spaltenliste und ohne die zwei `assertNotIn`. Den Kern mit `time-machine` zu einem festen Zeitpunkt finalisieren und `finalisiert_am` als Literal erwarten, etwa `"2026-07-01T08:00:00+00:00"` (#324, #349). |
| `test_exportiert_den_anbieter_und_kein_zugangsdatum` | umschreiben | Die Schlüsselliste von `modellkonfigurationen.csv` wiederholt den Kontrakt und die folgende Zeilen-Gleichheit. `"infomaniak.com"` folgt aus der Prüfung auf die Basis-URL. | Zeilen-Gleichheit und die Prüfungen auf Token und Basis-URL. |
| `test_exportiert_die_transkriptions_konfiguration_nicht` | streichen | Doppelung (Startbefund 1): Eine zusätzliche Datei bricht den Vergleich der Dateinamen mit ADR-0029. | `test_dateien_und_spalten_folgen_dem_kontrakt_aus_adr_0029` |
| `test_exportiert_ziehungen_und_alle_erhebungssitzungen` | umschreiben | Erwartet die Status über `Sitzung.Status.values`; im Export ist die Schreibweise die Zusage (Lesart oben). | Die vier Status als Literale `"laufend"`, `"abgeschlossen"`, `"abgebrochen"`, `"gescheitert"`, je einer Bindung zugeordnet. |
| `test_exportiert_die_verbrauchte_zeit_ohne_die_offene_spanne` | umschreiben | `assertNotIn("offene_spanne_seit", …)` deckt der Kontrakt (Startbefund 1). | Nur die verbrauchten Zeiten `"417.5"` und `"0.0"`; Name etwa `test_exportiert_die_verbrauchte_zeit_in_sekunden`. |
| `test_exportiert_fluechtige_teilnahme_mit_geruest_ohne_inhaltszeilen` | umschreiben | Erwartet `Sitzung.Status.ABGESCHLOSSEN` (Lesart oben). Sonst gut: Die Datenspur entsteht über `sitzung_starten` und `gespraechsschritt_ausfuehren`, die Zeit über feste Zeitpunkte am Sink. | `"abgeschlossen"` als Literal. |
| `test_exportiert_gespraechsschritte_fehlversuche_und_diagnosen` | umschreiben | Kopfzeilen von `gespraechsschritte.csv` und `diagnosen.csv` sowie die `namelist`-Prüfung wiederholen den Kontrakt (Startbefund 1). | Die Zeilen von Schritten, Fehlversuchen und Diagnose samt der Zeilen aus Trainingssitzungen, die fehlen müssen, bleiben. Die Format-Regex für `erstellt_am` stammt aus ADR-0029 und bleibt. |
| `test_exportiert_itembloecke_mit_vorlage_und_erledigt_zeitstempel` | umschreiben | Tautologisch: `_zeitstempel` bildet `_zellenwert` aus `export.py` nach. `andockpunkt` erwartet er über `block.andockpunkt`, also über den Modellwert. Die Abfrageprüfung zählt SQL-Texte mit `"erhebungen_itemblock"` und hängt damit an Tabellenname und Abfrageform. | Mit `time-machine` zu festen Zeitpunkten vorlegen und erledigen; `vorgelegt_am` und `erledigt_am` als Literale, `andockpunkt` als `"nach_sitzung"`/`"am_ende"`. Die Abfrageprüfung wandert in den Skalierungstest unten. Danach entfällt `_zeitstempel`. |
| `test_exportiert_item_antworten_mit_erhaltener_null_semantik` | umschreiben | Die Kopfzeile wiederholt den Kontrakt (Startbefund 1). | Nur die Zeilen-Gleichheit, die schon ganz aus Literalen besteht. |
| `test_export_ist_eigentumsgebunden_und_auch_ohne_daten_wohlgeformt` | umschreiben | Der Dateiname wird nur per Regex geprüft (`\d+`, `\d{8}T\d{6}Z`): Ob der Zeitstempel in UTC und zum Abrufzeitpunkt steht, merkt der Test nicht. | Mit `time-machine` auf einen festen Zeitpunkt in Sommerzeit, etwa 2026-07-01 10:00 Europe/Berlin: `filename="erhebung-<pk>-leerer-entwurf-20260701T080000Z.zip"` als Literal (#324, #349). Fehlender Link, 404 für fremde Erhebung und Zeilenzahlen ohne Datenbestand bleiben. |
| `test_exportiert_die_vorgelegten_items_mit_vollem_wortlaut`, `test_exportiert_die_kodierung_der_likert_skala` | umschreiben | Die Kopfzeilen wiederholen den Kontrakt (Startbefund 1). | Nur die Zeilen-Gleichheiten. Die Likert-Pole stehen so in docs/verhalten.md. |
| `test_export_braucht_unabhaengig_von_der_itemzahl_gleich_viele_abfragen` | umschreiben | Gut: Die Zahl der Abfragen bei einem und drei Items ist eine Zusage, die keine Implementierung festlegt. Nur die Itemblöcke prüft er nicht mit. | Dieselbe Skalierung auch über Itemblöcke und Bindungen: ein und drei Blöcke ergeben gleich viele Abfragen. Ersetzt die SQL-Zählung im Itemblock-Test. |
| `test_detail_zeigt_export_mit_stichprobe_auch_nach_archivierung` | behalten | HTTP, Link folgt dem Datenbestand. | – |
| `test_dateien_und_spalten_folgen_dem_kontrakt_aus_adr_0029` | behalten | Kontrakttest gegen eine externe Spec, ausdrücklich zulässig (#321). Er liest die Tabelle aus ADR-0029 als Erwartungswert. Damit prüft er nicht den Wortlaut der Dokumentation, sondern nimmt die Erwartung aus einer Spec, wie CODING_STANDARDS.md es verlangt („Never expected values from the module under test“). | – |

### `ErhebungenGesperrteItemzuordnungTests`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_finale_erhebung_zeigt_items_je_andockpunkt_ohne_bibliothek_oder_aktionen`, `test_archivierte_erhebung_zeigt_leere_andockpunktbereiche_gesperrt` | behalten | HTTP: Die Lesefassung der Listen rendert der Server ohne Auswahl und ohne Aktions-URLs. | – |
| `test_finale_erhebung_zeigt_vignetten_ohne_aktionen` | umschreiben | `assertTemplateUsed` hält den Namen des Includes fest. | Ohne `assertTemplateUsed`. Der Rest bleibt. |

### `ErhebungstexteVorschauUndLeseansichtTests`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_entwurf_bietet_je_textfeld_hinweis_und_umschalter`, `test_vorschau_entspricht_der_teilnahmeseite` | behalten | HTTP; `hx-post` und das Profil sind der Vertrag zu htmx und zum Vorschau-Endpunkt. | – |
| `test_finale_erhebung_zeigt_die_texte_gerendert_und_nur_lesend`, `test_archivierte_erhebung_zeigt_die_texte_gerendert` | umschreiben | Derselbe Test für zwei Zustände, der zweite mit weniger Zusicherungen. | Ein Test, parametrisiert über final und archiviert, mit allen Zusicherungen des ersten. |

### Helfer am Kopf der Datei

| Helfer | Urteil | Grund | Zielzustand |
|---|---|---|---|
| `_zeitstempel` | streichen | Tautologisch, bildet `_zellenwert` nach (siehe Itemblock-Test). | Entfällt mit dem Umschreiben des Itemblock-Tests. |
| `_laufende_bindung`, `_forschungskonfiguration`, `_infomaniak_konfiguration`, `_finales_item_anlegen`, `_item_zuordnen` | behalten | Öffentliche Wege; `_laufende_bindung` setzt das Token fest, damit die Export-Tests Literale erwarten können. | – |
| `_finale_vignette_anlegen` | umschreiben | Öffentlicher Weg, aber eine weitere Kopie desselben Helfers (Startbefund 3). | Der gemeinsame Helfer aus #327, #328, #330 und #332. |

## Folge-Issues

- #386 Stichprobe anlegen: Ein ungültiger Zeitraum endet in einer nackten 400-Textseite statt in einer Meldung.
- #387 `zuordnungsliste.js`: Das Verhalten der Zuordnungslisten hat keine Testnaht.

Bestehende Issues, die dieses Review berührt:

- #254 Antwort-Idiom abgewiesener Schreibaktionen: entschieden in ADR-0051, umgesetzt mit #393 samt den Sperrtests.
- #249 Die Item-Routen renderten die Detailseite innerhalb von `@transaction.atomic`. Seit #393 leiten sie weiter; keine Route rendert mehr in einer Transaktion.
- #385 `Stichprobe.traegt_daten`; die zwei Tests, auf die es sich stützt, bleiben.

Weitere Probleme im Produktionscode hat das Review nicht gefunden. Dass `erhebungen:export` auch für einen Entwurf ohne Stichprobe ein Archiv liefert, obwohl die Seite den Link erst mit einer Stichprobe zeigt, ist kein Mangel: Das Archiv enthält dann nur Kopfzeilen und die Erhebung selbst, und der Kontrakttest baut darauf.
