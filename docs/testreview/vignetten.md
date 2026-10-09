# Testreview: Vignetten

Bereich aus #328 (Spec #321). Geprüft sind `vignetten/tests/test_vignetten_models.py` und `vignetten/tests/test_views.py`. Kein Test im Bereich patcht die Zeit (#324). Die Regel für Migrationstests (#325, ADR-0031) trifft genau einen Test.

Zwei Lesarten gelten für das ganze Dokument:

- Ein View-Test, der nach dem Request den Zustand über die öffentliche Modell-API liest (`refresh_from_db()`, Attribute), zählt nicht als „DB-Abfrage statt Schnittstelle“. Das Urteil fällt erst, wenn die Prüfung Modellverhalten wiederholt, das der Modelltest schon festhält (Schichtdoppelung), oder wenn die View das Ergebnis selbst sichtbar macht.
- Lernauftrag und Arbeitsheft laufen im Modell durch denselben Code (`_aufgabenkontextteil`), im Formular durch dieselbe Bildkarte. Tests, die sich nur im Teil unterscheiden, bekommen *umschreiben*: ein parametrisierter Test über beide Teile. So bleiben beide Feldnamen geprüft, und der Text steht nur einmal da.

## Schnittstelle

### Vignette (`vignetten/models.py`)

- **Aufrufe:**
  - Anlegen: `Vignette.objects.anlegen(konto)` legt einen Entwurf samt neuer Vignettenhistorie an. Das Konto ist die erste Eigentümerin, gepinnt wird die neueste finale Kern-Fassung, die Akteure kommen aus `zufaellige_akteure()`.
  - Lebenszyklus: `finalisieren()`, `bearbeiten() -> Vignette` (Folgeentwurf derselben Historie), `vorspulen()` (Entwurf auf die neueste finale Kern-Fassung), `archivieren()`, `entarchivieren()`, `delete()`.
  - Abfragen: `Vignette.objects.sichtbar_fuer(konto)`, `.einbindbar()` (nur finale Fassungen), beide in beliebiger Reihenfolge verkettbar. `QuerySet.delete()`.
  - Lesende Eigenschaften: `lernauftrag` und `arbeitsheft` (je ein `Aufgabenkontextteil` mit `text_vor_bild`, `text_nach_bild`, `text`, `bild`, `bildbeschreibung`, `simulationshinweise`), `anzeigename`, `uhr_laeuft`, `kern_pin_ueberholt`, `hat_nicht_archivierte_nachfolgerin`, `schuelerin_bildkuerzel`, `lehrperson_bildkuerzel`.
  - Modulfunktionen: `prompt_platzhalter(vignette)` und `rahmen_platzhalter(vignette)` liefern die Werte für die Prompt-Vorlagen und die Rahmenhandlung (ADR-0010, ADR-0030). `zufaellige_akteure()` liefert Startwerte für Name und Geschlecht beider Akteure. `vignetten_bild_pfad` vergibt jedem Upload einen neuen Dateinamen.
  - `FELDBESCHRIFTUNGEN`: die Beschriftungen aus GLOSSARY.md, die Formular, Detailansicht und Finalisieren-Meldung teilen.
- **Invarianten:**
  - Fassungen entstehen nur über `anlegen` und `bearbeiten`. `create`, `bulk_create`, `bulk_update`, `update` und `save()` auf einer neuen Instanz werfen `RuntimeError`.
  - Finale und archivierte Fassungen sind unveränderlich, auch `finalisiert_am`. Zustandswechsel laufen nur über die Lebenszyklus-Methoden.
  - Finalisieren verlangt Fehlermuster-Beschreibung, Schüler:in-Vorname, Lehrperson-Name, Fach, Thema, Klassenstufe und Budget-Typ; Lernauftrag und Arbeitsheft je Text oder Bild; zu jedem Bild eine Bildbeschreibung; ein Budget größer als 0 und eine gepinnte Kern-Fassung. Ein überholter Kern-Pin bleibt zulässig (ADR-0003).
  - `bearbeiten()` liest die Quelle aus der Datenbank und übernimmt alle Inhaltsfelder, Bildpfade und den Kern-Pin. Eine Fassung mit nicht archivierter späterer Fassung zieht keinen Entwurf mehr.
  - Die Datenbank erlaubt je Historie höchstens einen Entwurf und je Vorgängerin höchstens eine nicht archivierte Nachfolgerin. `finalisiert_am` passt zum Zustand. Nicht-Entwürfe tragen in Lernauftrag und Arbeitsheft je Text oder Bild. Beide Geschlechter sind nie leer.
  - Gelöscht werden nur Entwürfe, einzeln wie gesammelt. Eine dadurch fassungslose Historie wird mitgelöscht.
  - Die Sichtbarkeit einer Fassung folgt dem Eigentümer-Kreis ihrer Historie; die Administration sieht alles.
  - Positionsmarker `[bild]` zählt nur allein auf seiner Zeile. Der erste Marker teilt den Text, alle verschwinden; ohne Bild verschwinden sie ersatzlos.
  - `prompt_platzhalter` fasst lange Werte in XML-artige Umgebungen, lässt leere ungefasst und reicht Nutzereingaben roh durch.
  - `uhr_laeuft` ist nur beim Schrittbudget falsch, auch ohne Budget-Typ wahr.
- **Fehlerfälle:**
  - Verstöße gegen Lebenszyklus und Vollständigkeit werfen `ValidationError` mit lesbarer Meldung.
  - Constraint-Verstöße werfen `IntegrityError`: über die interne Naht `_erstellen` und bei `entarchivieren()`, wenn die Vorgängerin schon eine nicht archivierte Nachfolgerin hat.
  - `anlegen` ohne finale Kern-Fassung wirft `Simulationskern.DoesNotExist` (#381).
- **Konfiguration:** keine eigene. `MEDIA_ROOT` bestimmt den Ablageort der Bilder.

### Vignettenhistorie (`vignetten/models.py`)

- **Aufrufe:** der Eigentümer-Kreis aus `konten/eigentuemerschaft.py` (`objects.anlegen`, `objects.sichtbar_fuer`, `austreten`, `moegliche_ergaenzungen`, `hat_mehrere_eigentuemerinnen`). Dazu `name`, `archiviert` und `ist_aktiv()`.
- **Invarianten:** Die Rollengruppe ist Autor:in. Archiviert ist die Historie nicht mehr aktiv. Das Archiv-Kennzeichen hat keine öffentliche Geste (#236) und wirkt nur auf das Löschen von Konten.
- **Fehlerfälle und Konfiguration:** wie beim Eigentümer-Kreis (`docs/testreview/config-static.md`, #332).

### Formular (`vignetten/forms.py`)

- **Aufrufe:** `VignetteForm` mit den Inhaltsfeldern (ohne Zustand, Historie, Vorgängerin und Kern). `form.bildkarten` liefert je Teil, was die Bildkarte zeichnet.
- **Invarianten:** Beide Geschlechter sind Pflichtfelder. Ein entferntes Bild leert beim Speichern auch seine Bildbeschreibung (#288). Die Bildkarte kennt die Zustände `leer`, `gespeichert`, `entfernen`, `verloren` und `fehler`.
- **Fehlerfälle:** Formularfehler; eine Datei, die kein Bild ist, ist ein Fehler am Bildfeld.
- **Konfiguration:** keine. `FinalisierenForm` ist ungenutzt (#382).

### Editor (`vignetten/views.py`, `vignetten/urls.py`)

- **Aufrufe:** `vignetten:liste`, `anlegen`, `detail`, `bearbeiten` (GET/POST). Nur POST: `finalisieren`, `archivieren`, `entarchivieren`, `vorspulen`, `neue_fassung` (Alias `reversionieren`, #383), `eigentuemerin_hinzufuegen`, `eigentuemerin_entfernen`.
- **Invarianten:**
  - Alle Routen verlangen eine Anmeldung und die Rolle Autor:in oder die Administration, sonst 403. Anonyme gehen zum Login.
  - Fremde Fassungen und Fassungen im falschen Zustand ergeben 404, GET auf eine Aktion 405.
  - Die Liste zeigt je sichtbarer Historie mit Fassung genau eine Zeile, die neueste Fassung; der Name verlinkt die Detailseite.
  - Das Anlegeformular ist mit Akteuren vorbelegt und bietet keine Kernwahl. Anlegen und Bearbeiten teilen ein Formular mit `autocomplete="off"`, Datei-Upload, Lesefeldern, Bildkarten, Markdown-Vorschau, Verlassen-Warnung und den Vorschlägen für Fach und Thema aus allen finalen Vignetten.
  - Die Detailansicht zeigt den Aufgabenkontext (Szenentexte als Markdown, Nebenfelder roh), die Beschriftungen aus `FELDBESCHRIFTUNGEN`, den Kern-Pin samt Hinweis bei überholtem Pin am Entwurf, den Eigentümerinnen-Abschnitt und nur die Aktionen, die der Zustand erlaubt. „Neue Fassung“ gibt es nur ohne nicht archivierte Nachfolgerin.
  - Modellfehler einer Lebenszyklus-Aktion erscheinen als Meldung auf der Detailseite.
  - `neue_fassung` öffnet einen vorhandenen Entwurf der Historie, statt einen zweiten zu ziehen.
  - Wer sich selbst austrägt, landet auf der Liste; sonst bleibt es bei der Detailseite.
- **Konfiguration:** keine.

## Startbefunde

1. **`random.choice` im Modul der Vignetten: bestätigt.** `test_formular_belegt_akteure_vor_und_bietet_keine_kernwahl` patcht `"vignetten.models.random.choice"`. Der Pfad funktioniert nur, weil das Modul `import random` schreibt; ersetzt wird dabei `random.choice` für den ganzen Prozess. Die Erhebungen patchen dagegen den im Modul gebundenen Namen (`"erhebungen.models.choice"` nach `from secrets import choice`, #327). Beide hängen am Importstil, nur verschieden. Zufall an der Systemgrenze zu patchen erlaubt CODING_STANDARDS.md („Mocking“); der Fehler liegt im Patchziel, das am Importstil hängt. Nötig ist der Patch hier ohnehin nicht: Die Spec sagt nur, dass die Akteure vorbelegt und überschreibbar sind, nicht welche. Das ist über HTTP ohne Patch prüfbar (siehe Befund). Welche Namen im Topf liegen, ist Inhalt, kein Verhalten; ein Test darauf wäre aus `models.py` abgeschrieben.
2. **`objects._erstellen` als Abkürzung: bestätigt.** Die beiden Dateien rufen `_erstellen` 60-mal auf (31 im Modelltest, 29 im View-Test). Legitim sind nur die 9 Aufrufe in `VignetteConstraintTests`: Die Zustände dort kann der Lebenszyklus nicht herstellen. Die übrigen 51 sind Setup. Ein Teil davon erzeugt Zustände, die der Lebenszyklus nie herstellt, etwa finale Fassungen ohne Kern-Pin und ohne Pflichtfelder (`VignetteArchivierenViewTests`, `VignetteAutovervollstaendigungViewTests`, `VignetteSichtbarFuerQuerySetTests`). Alle 51 lassen sich über `anlegen` → Felder setzen → `save()` → `finalisieren()` → `bearbeiten()`/`archivieren()` aufbauen. Das zeigen schon `VignetteFinalisierenViewTests` und `VignetteNeueFassungViewTests`. Hindernis ist allein, dass `anlegen` eine finale Kern-Fassung voraussetzt (#381). Vorschlag für die Umsetzung: zwei Helfer in `vignetten/tests/`, etwa `entwurf_anlegen(konto, **felder)` und `finale_anlegen(konto, **felder)`, die bei Bedarf eine Kern-Fassung anlegen und finalisieren. Sie lösen `_vollstaendige_vignette` in `test_views.py` ab, der das für Entwürfe schon tut. Danach kann `vignetten/tests/test_views.py` von der SLF001-Übergangsliste. In `test_vignetten_models.py` bleibt `_erstellen` nur in `VignetteConstraintTests`, mit `# noqa: SLF001` je Zeile statt Dateiausnahme. Der Abschnitt „Setup“ in den Befunden nennt die betroffenen Tests. Ihr Urteil bezieht sich auf die Prüfung; das Setup stellt die Umsetzung zusätzlich um.
3. **Migrationstest der Geschlechterfelder: bestätigt.** `test_geschlechter_migration_fuellt_leere_bestandswerte_auf` prüft `0007_geschlechter_nicht_leer`, die auf `main` liegt. Streichen nach #325 und ADR-0031.

## Befunde

### `vignetten/tests/test_vignetten_models.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_prompt_platzhalter_ordnet_arbeitsheft_text_und_bildbeschreibung` | umschreiben | Durchgerechnetes Beispiel über das ganze Wörterbuch, gut. Nur `"schuelerin_geschlecht": Vignette.Geschlecht.WEIBLICH` nimmt die Erwartung aus dem Modul. Ändert sich der Wert der Konstante, ändert sich der Prompt-Vertrag, und der Test merkt es nicht. | Erwartung als Literal `"weiblich"`. Der Rest bleibt. |
| `test_prompt_platzhalter_ordnet_lernauftrag_text_und_bildbeschreibung`, `test_prompt_platzhalter_fasst_simulationshinweise_in_umgebungen`, `test_prompt_platzhalter_reicht_spitze_klammern_unveraendert_durch`, `test_prompt_platzhalter_laesst_leere_lange_werte_ungefasst` | behalten | Öffentliche Funktion, Erwartungen als Literale. Der Lernauftrag-Fall prüft `\r\n` und Tabulator, also mehr als der Arbeitsheft-Fall. | – |
| `test_prompt_platzhalter_entfernt_marker_ohne_bild`, `test_prompt_platzhalter_entfernt_lernauftrag_marker_ohne_bild` | umschreiben | Gleicher Test, nur der Teil wechselt. | Ein Test, parametrisiert über `lernauftrag` und `arbeitsheft`: `"Oben\n[BILD]\nunten\n[bild]"` ohne Bild ergibt `<teil>\n<teil_text>Oben\nunten\n</teil_text>\n</teil>`. |
| `test_prompt_platzhalter_ordnet_bild_ohne_marker_nach_dem_text`, `test_prompt_platzhalter_ordnet_lernauftrag_bild_ohne_marker_nach_dem_text` | umschreiben | wie oben | Ein parametrisierter Test: Text ohne Marker, Bild und Beschreibung ergeben Textumgebung, dann Bildbeschreibungsumgebung. |
| `test_prompt_platzhalter_laesst_leere_textstuecke_weg`, `test_prompt_platzhalter_laesst_leere_lernauftrag_textstuecke_weg` | umschreiben | wie oben | Ein parametrisierter Test: Nur Bild und Beschreibung ergeben keine leere Textumgebung. |
| `test_positionsmarker_zaehlt_nur_allein_auf_einer_zeile`, `test_positionsmarker_auf_eigener_zeile_zerlegt_den_text` | behalten | `lernauftrag`/`arbeitsheft` sind öffentlich; die Templates lesen `text_vor_bild` und `text_nach_bild`. Die Fälle stehen so in docs/verhalten.md. | – |
| `test_rahmen_platzhalter_enthaelt_alle_weiblichen_werte` | umschreiben | Wie beim Prompt: `"schuelerin_geschlecht"` und `"lehrperson_geschlecht"` erwarten `Vignette.Geschlecht.WEIBLICH`. | Beide Erwartungen als Literal `"weiblich"`. |
| `test_rahmen_platzhalter_leitet_maennliche_formen_beider_akteure_ab` | behalten | Literale Grammatikformen. | – |
| `test_bildkuerzel_mappt_geschlecht_auf_w_oder_m` | umschreiben | Die Kürzel bilden die Dateinamen der Illustrationen in `sitzungen`, das bleibt. Der Fall `lehrperson_geschlecht=""` prüft aber einen Zustand, den die Constraint ausschließt. | Wie heute, nur mit `lehrperson_geschlecht=Vignette.Geschlecht.WEIBLICH` im weiblichen Fall. |
| `test_oeffentliches_create_umgeht_den_lebenszyklus_nicht`, `test_bulk_create_umgeht_den_lebenszyklus_nicht` | behalten | Fehlerfälle der Schnittstelle. | – |
| `test_anlegen_erstellt_entwurf`, `test_anlegen_pinnt_neuesten_finalen_kern`, `test_anlegen_traegt_konto_als_eigentuemerin_ein` | behalten | Öffentliche Manager-Methode, je eine Zusicherung. Die Eigentümerin prüft auch der Vertrag (`test_anlegen_traegt_genau_eine_eigentuemerin_ein`), aber nur für `Vignettenhistorie.objects.anlegen`, nicht für den Weg über die Vignette. | – |
| `test_anlegen_vergibt_akteure` | umschreiben | `assertIn(…, Vignette.Geschlecht.values)` nimmt die erlaubte Menge aus dem Modul. | Erwartung als Literal: Name nicht leer, Geschlecht in `{"weiblich", "männlich"}`, für beide Akteure. |
| `test_fassung_braucht_beide_geschlechter`, `test_historie_hat_hoechstens_einen_entwurf`, `test_entwurf_darf_keinen_finalisierungszeitpunkt_haben`, `test_entarchivieren_zu_einer_schwester_wird_verhindert` | behalten | Constraint-Tests über die interne Naht, ausdrücklich zulässig (#321). | – |
| `test_finalisiert_am_muss_genau_dem_zustand_entsprechen` | umschreiben | Die Zeile verletzt zwei Constraints: Ohne `lernauftrag_text` greift auch `vignetten_lernauftrag_text_oder_bild`. Fiele die geprüfte Constraint weg, bestünde der Test trotzdem. | Dieselbe Fassung mit `lernauftrag_text="Lernauftrag"`, sodass nur `vignetten_finalisiert_am_passt_zu_zustand` greifen kann. |
| `test_finale_fassung_braucht_arbeitsheft_text_oder_bild` | umschreiben | Wie oben: Ohne `lernauftrag_text` greift auch die Lernauftrag-Constraint. Für die Lernauftrag-Constraint gibt es keinen eigenen Test. | Parametrisiert über beide Teile: eine finale Fassung mit `finalisiert_am`, Text im anderen Teil und leerem geprüftem Teil wirft `IntegrityError`. |
| `test_geschlechter_migration_fuellt_leere_bestandswerte_auf` | streichen | Totes Gewicht, die Migration liegt auf `main` (#325). | Keiner nötig, Begründung ADR-0031. |
| `VignetteSichtbarFuerQuerySetTests`: `test_sichtbar_fuer_liefert_eigene_und_geteilte_fassungen`, `…_unbeteiligter_keine_fassung`, `…_administration_alle_fassungen`, `…_laesst_sich_vor_einbindbar_verketten`, `…_laesst_sich_nach_einbindbar_verketten` | behalten | Öffentliche Abfrage der Fassungen. Die beiden Verkettungen prüfen je, dass eine der Methoden das eigene QuerySet zurückgibt. Setup siehe unten. | – |
| `test_sichtbar_fuer_liefert_koeigentuemerin_geteilte_fassung` | streichen | Doppelung: Ada und Grace stehen gleichrangig im Eigentümer-Kreis; welche zuerst eingetragen wurde, macht keinen Unterschied. | `test_sichtbar_fuer_liefert_eigene_und_geteilte_fassungen` |
| `test_sichtbar_fuer_liefert_dritter_ihre_fassung` | streichen | Doppelung: „eigene Fassung ja, fremde nein“. | `test_sichtbar_fuer_liefert_eigene_und_geteilte_fassungen` (Linus' Fassung fehlt bei Ada) und `test_sichtbar_fuer_liefert_unbeteiligter_keine_fassung` |
| `VignetteQuerySetTests::test_sichtbar_fuer_liefert_nur_den_eigentuemer_kreis`, `::test_sichtbar_fuer_liefert_alle_historien_fuer_administration` | streichen | Schichtdoppelung: `Vignettenhistorie.objects.sichtbar_fuer` ist der gemeinsame Eigentümer-Kreis. | `config/tests/test_eigentuemer_kreis_contract.py::test_sichtbar_sind_die_eigenen_bestaende_und_der_administration_alle` (Fall `Vignettenhistorie`) |
| `test_einbindbar_liefert_nur_finale_fassungen` | behalten | Öffentliche Abfrage. Setup siehe unten. | – |
| `test_historie_archivieren_beruehrt_keine_fassung` | streichen | Horizontal slicing: Prüft, dass das Setzen eines Feldes keine Nebenwirkung hat, die kein Code je hatte. Eine Archiv-Geste für Historien gibt es nicht (#236). | Keiner nötig: Es geht kein Verhalten verloren. Kommt #236, prüft dessen Test die Geste. |
| `test_finalisieren_ueberfuehrt_vollstaendigen_entwurf_nach_final`, `test_finale_fassung_ist_unveraenderlich`, `test_finalisiert_am_wird_nie_zurueckgesetzt`, `test_finale_fassung_laesst_keine_massenmutation_zu`, `test_finalisieren_lehnt_nichtentwuerfe_ab`, `test_finalisieren_lehnt_nichtpositives_budget_ab`, `test_finalisieren_laesst_ueberholten_kern_pin_zu`, `test_finalisieren_lehnt_fehlenden_kern_pin_ab` | behalten | Öffentlicher Lebenszyklus, Fehler über die Meldung. Setup siehe unten. | – |
| `test_finalisieren_in_zweitem_tab_lehnt_den_uebergang_ab`, `test_archivieren_in_zweitem_tab_lehnt_den_uebergang_ab`, `test_entarchivieren_in_zweitem_tab_lehnt_den_uebergang_ab` | behalten | Nachtrag (#402): Öffentlicher Lebenszyklus, Fehlerfall über die Meldung. Der veraltete zweite Tab ist nur hier herbeizuführen. Setup über die Helfer. | – |
| `test_finalisieren_lehnt_leeren_lernauftrag_ab`, `test_finalisieren_lehnt_leeres_arbeitsheft_ab` | umschreiben | Gleicher Test, nur der Teil wechselt. | Parametrisiert über beide Teile: leerer Text ohne Bild wirft `ValidationError` mit dem Label des Teils. |
| `test_finalisieren_nimmt_lernauftrag_nur_mit_bild_an`, `test_finalisieren_nimmt_arbeitsheft_nur_mit_bild_an` | umschreiben | wie oben | Parametrisiert: Bild mit Beschreibung ohne Text wird final. |
| `test_finalisieren_erlaubt_leere_lernauftrag_bildbeschreibung_ohne_bild`, `test_finalisieren_erlaubt_leere_bildbeschreibung_ohne_bild` | umschreiben | wie oben | Parametrisiert: leere Beschreibung ohne Bild wird final. |
| `test_finalisieren_braucht_lernauftrag_bildbeschreibung_mit_bild`, `test_finalisieren_braucht_bildbeschreibung_mit_bild` | umschreiben | wie oben | Parametrisiert: Bild ohne Beschreibung wirft `ValidationError` mit „<Teil>-Bild“. |
| `test_bearbeiten_erbt_pin_und_akteure_ohne_finale_zu_mutieren` | umschreiben | Prüft nur einen Teil der übernommenen Felder. Die vollständige Liste prüft heute der View-Test `test_zieht_aus_finaler_fassung_einen_entwurf_mit_geerbtem_bildpfad`; das Verhalten gehört aber dem Modell. | Der Modelltest übernimmt die Feldliste des View-Tests als Literal: alle Inhaltsfelder, beide Bildpfade, Kern-Pin, Historie und Vorgängerin. Dazu wie heute: eine ungespeicherte Änderung an der Quelle wird nicht übernommen, die Quelle bleibt final. |
| `test_bearbeiten_lehnt_finale_fassung_mit_nicht_archivierter_nachfolgerin_ab`, `test_bearbeiten_lehnt_fassung_mit_aktiver_spaeterer_fassung_ab`, `test_vorspulen_aktualisiert_nur_den_pin_eines_entwurfs`, `test_finale_fassung_kann_archiviert_und_entarchiviert_werden`, `test_nur_entwuerfe_duerfen_physisch_geloescht_werden`, `test_letzte_fassung_nimmt_ihre_historie_mit`, `test_historie_mit_weiterer_fassung_bleibt_bestehen`, `test_massenloeschung_raeumt_leer_gewordene_historien_ab` | behalten | Öffentlicher Lebenszyklus und Löschregel. Setup siehe unten. | – |
| `test_zustandswechsel_sind_auf_lebenszyklus_methoden_beschraenkt` | behalten | Fehlerfall von `save()`. #365 baut die Übergänge um; der Test bleibt dort gültig, weil `save()` Zustandswechsel weiter abweist. | – |
| `VignetteGespraechsbudgetTests` (3 Tests) | behalten | Öffentliche Eigenschaft, die `sitzungen/sink.py` liest. Der dritte Fall hält eine bewusste Regel fest. | – |

### `vignetten/tests/test_views.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_speichert_ueberschriebene_akteure_und_zeigt_gepinnten_kern` | umschreiben | Schichtdoppelung: Kern-Pin und Eigentümerin prüft er über `Vignette.objects.get()` wie `test_anlegen_pinnt_neuesten_finalen_kern` und `test_anlegen_traegt_konto_als_eigentuemerin_ein`. Eigen ist nur, dass die Formularwerte die Vorbelegung überschreiben. | POST mit `follow=True`: landet auf der Detailseite, die „Mia“, „Weber“, Lehrperson männlich und „Gepinnter Simulationskern: <pk>“ zeigt. Ohne Zugriff auf das Modell. |
| `test_formular_belegt_akteure_vor_und_bietet_keine_kernwahl` | umschreiben | Implementation-coupled, Startbefund 1. | Ohne Patch: GET `vignetten:anlegen`; `schuelerin_name` und `lehrperson_name` tragen einen nicht leeren Wert, in beiden Geschlechtsauswahlen ist eine Option gewählt, kein Feld `gepinnter_kern`. |
| `test_formular_unterbindet_die_browserseitige_wiederherstellung` (`VignetteAnlegenViewTests`) und gleichnamig in `VignetteBearbeitenViewTests` | umschreiben | Die Zusicherung `'autocomplete="off"'` trifft auch die Eingaben für Fach und Thema, die das Attribut für die Vorschläge tragen. Entfiele es am Formular, bestünden beide Tests trotzdem. | Ein Test über beide Editoren: Das Element `<form id="vignette-formular">` trägt `autocomplete="off"`, etwa mit einem `HTMLParser` wie in `config/tests/formular.py`. |
| `test_fassungslose_historie_legt_die_liste_nicht_lahm`, `test_jede_historie_erscheint_trotz_mehrerer_fassungen_einmal` | behalten | HTTP, eigene Logik der Liste: fassungslose Historien, keine Doppelzeilen. Setup siehe unten. | – |
| `test_zeilen_sind_ueber_den_namen_verlinkt` | umschreiben | Die Zusicherung `'<a class="zeilenlink" :href="r.url" x-text="r.label"></a>'` prüft Alpine-Ausdrücke, also Quelltext. Die `assertNotContains` auf `button--secondary` und „>Aktion<“ bewachen Entferntes. | Die Liste enthält die URL der Detailseite und den Namen der Zeile; die Tabelle trägt `table--zeilenlink`, den Vertrag zum CSS, das #332 prüft. Ohne den Alpine-Ausdruck und ohne die `assertNotContains`. Setup siehe unten. |
| `test_zeigt_die_eigentuemerin_der_historie` | umschreiben | Schichtdoppelung: Überschrift, Hinzufügen und Name stehen in `config/tests/test_eigentuemerinnen_abschnitt.py`. Eigen ist nur der Artefaktname. | Nur „Wer diese Vignette sehen und bearbeiten darf“ auf der Detailseite. |
| `test_rendert_die_rohfelder_des_aufgabenkontexts` | streichen | Doppelung: Lernauftrag, Arbeitsheft und Bildbeschreibung erscheinen auch im Szenentext-Test. | `test_rendert_lernauftrag_und_arbeitsheft_als_szenentext` |
| `test_rendert_lernauftrag_und_arbeitsheft_als_szenentext`, `test_rendert_simulationshinweise` | behalten | HTTP, sichtbares Rendering laut docs/verhalten.md. | – |
| `test_zeigt_den_hinweis_am_entwurf_mit_ueberholtem_kern`, `test_zeigt_keinen_hinweis_am_entwurf_mit_aktuellem_kern`, `test_zeigt_keinen_hinweis_an_nicht_vorspulbaren_fassungen` | behalten | HTTP über den öffentlichen Lebenszyklus. `kern_pin_ueberholt` hat keinen eigenen Modelltest; diese Tests decken ihn. | – |
| `test_versteckt_fremde_fassung` | behalten | 404 an der HTTP-Naht. | – |
| `test_hinzufuegen_gibt_koautorin_listenzugriff`, `test_nur_autorinnen_oder_administration_koennen_hinzugefuegt_werden`, `test_administration_kann_fremde_historie_uebergeben`, `test_nicht_eigentuemerin_loest_keinen_selbst_redirect_aus`, `test_eigentuemerin_hinzufuegen_ist_nur_per_post_erreichbar`, `test_eigentuemerin_entfernen_ist_nur_per_post_erreichbar` | behalten | HTTP-Verhalten der Kreis-Routen der Vignette. | – |
| `test_selbstentfernung_uebergibt_die_historie` | umschreiben | Prüft nur den 404 danach. Die eigene Weiterleitung der View bei Selbstaustritt (auf die Liste) prüft kein Test; nur der Gegenfall in `test_nicht_eigentuemerin_loest_keinen_selbst_redirect_aus`. | `assertRedirects(antwort, reverse("vignetten:liste"))` nach dem POST, dann wie heute 404 auf die Detailseite. |
| `test_entfernen_der_letzten_eigentuemerin_wird_verweigert` | behalten | Den Beleg trägt der Status 200 der Detailseite; ausgetragen bekäme Grace 404. `assertContains(…, grace.username)` sagt darüber hinaus nichts. | – |
| `test_koautorin_kann_einen_entwurf_bearbeiten`, `test_koautorin_kann_einen_entwurf_finalisieren` | streichen | Doppelung: Eine hinzugefügte Eigentümerin unterscheidet sich nicht von der ersten. Bearbeiten und Finalisieren prüfen schon die übrigen Tests als Eigentümerin. | `test_hinzufuegen_gibt_koautorin_listenzugriff` (der Eintrag wirkt) mit `VignetteBearbeitenViewTests` und `test_finalisiert_vollstaendigen_eigenen_entwurf` (Eigentümerin darf) |
| `test_leeres_geschlecht_zeigt_formularfehler` | umschreiben | Prüft nur das Geschlecht der Schüler:in. | Parametrisiert über beide Geschlechtsfelder: Formularfehler, Wert unverändert. Ersetzt danach `test_geschlechter_sind_pflichtfelder`. |
| `test_speichert_entwurf_mit_leeren_inhaltsfeldern`, `test_detail_verlinkt_editor_fuer_entwurf`, `test_formular_akzeptiert_datei_uploads`, `test_formular_zeigt_dieselbe_gliederung_wie_das_anlegeformular` | behalten | HTTP. `enctype` ist nur hier prüfbar, weil der Test-Client auch ohne das Attribut mehrteilig sendet. | – |
| `test_lagert_hochgeladenes_bild_unter_media_root_ab`, `test_lagert_hochgeladenes_lernauftrag_bild_unter_media_root_ab` | streichen | Doppelung: Der Bildwechsel-Test lädt hoch und prüft beide Dateien unter `MEDIA_ROOT`. | `test_bildwechsel_erstellt_neue_datei_und_erhaelt_die_alte` und sein Lernauftrag-Zwilling, nach dem Umschreiben ein parametrisierter Test |
| `test_zeigt_hochgeladenes_bild_im_detail`, `test_zeigt_hochgeladenes_lernauftrag_bild_im_detail` | umschreiben | Gleicher Test, nur der Teil wechselt. | Parametrisiert über beide Teile: Nach dem Upload zeigt die Detailseite die URL des Bildes. |
| `test_bildwechsel_erstellt_neue_datei_und_erhaelt_die_alte`, `test_lernauftrag_bildwechsel_erstellt_neue_datei_und_erhaelt_die_alte` | umschreiben | wie oben | Parametrisiert: Zwei Uploads ergeben zwei Dateien, die alte bleibt liegen. |
| `test_bild_entfernen_leert_auch_die_bildbeschreibung`, `test_rueckgaengig_vor_dem_speichern_behaelt_bild_und_beschreibung`, `test_zeigt_bildkarte_statt_eigenem_feld_bildbeschreibung`, `test_markiert_datei_ohne_bild_als_fehler`, `test_zeigt_gespeichertes_bild_als_vorschau_statt_als_pfad`, `test_nennt_nach_formularfehler_die_verlorene_datei` | behalten | HTTP-Verhalten der Bildkarte laut docs/verhalten.md. Die `data-`Attribute sind der Vertrag zum Skript der Bildkarte. | – |
| `test_versteckt_fremden_entwurf`, `test_versteckt_eigene_finale_fassung` | behalten | 404 an der HTTP-Naht. Setup siehe unten. | – |
| `test_liefert_finale_fach_und_thema_werte_dedupliziert_an_beide_editoren` | behalten | Liest `response.context`; die Werte gehen als JSON an ein Skript. Setup siehe unten. | – |
| `test_geschlechter_sind_pflichtfelder` | streichen | Schichtdoppelung: ruft das Formular direkt auf, die View zeigt denselben Fehler. | `test_leeres_geschlecht_zeigt_formularfehler`, nachdem er über beide Felder läuft |
| `test_beide_editoren_rendern_alle_formularfelder` | behalten | Die Erwartung kommt aus `VignetteForm().fields`, geprüft wird aber das Template: Es darf kein Feld des Formulars weglassen. | – |
| `VignetteMarkdownVorschauViewTests` (3 Tests), `VignetteLangeTexteViewTests` (4 Tests) | behalten | HTTP-Verhalten laut docs/verhalten.md, Vorschau und Anzeige mit demselben Rendering. | – |
| `test_formulare_zeigen_gekoppelte_beschriftungen`, `test_detail_zeigt_dieselben_beschriftungen` | umschreiben | Die positiven Erwartungen sind Literale aus GLOSSARY.md, gut. Die `assertNotContains` auf frühere Schreibweisen („Schüler:in Vorname“, „Budget Typ“, „Fehlermuster Beschreibung“) bewachen Entferntes. | Ohne die `assertNotContains`. Der Rest bleibt. |
| `test_zeigt_finalisieren_und_vorspulen_aktionen`, `test_finalisiert_vollstaendigen_eigenen_entwurf` | behalten | HTTP über den öffentlichen Lebenszyklus. | – |
| `test_finalisieren_ist_ohne_simulationshinweise_moeglich` | streichen | Doppelung: Der Entwurf aus `setUp` hat schon keine Simulationshinweise, der Test setzt nur leer auf leer. | `test_finalisiert_vollstaendigen_eigenen_entwurf` |
| `test_nennt_fehlende_pflichtfelder_mit_ihrer_beschriftung` | behalten | Prüft, dass die View Modellfehler als Meldung zeigt, mit den Beschriftungen aus GLOSSARY.md. Die Meldung zu fehlenden Pflichtfeldern prüft kein Modelltest. | – |
| `test_zeigt_fehler_fuer_leeren_lernauftrag` | streichen | Schichtdoppelung: Wie Modellfehler auf die Seite kommen, zeigt schon der Pflichtfeld-Test; die Regel prüft der Modelltest. | `test_nennt_fehlende_pflichtfelder_mit_ihrer_beschriftung` und `test_finalisieren_lehnt_leeren_lernauftrag_ab` |
| `test_zeigt_fehler_fuer_lernauftrag_bild_ohne_bildbeschreibung` | streichen | wie oben | dto. und `test_finalisieren_braucht_lernauftrag_bildbeschreibung_mit_bild` |
| `test_zeigt_fehler_fuer_leeres_arbeitsheft` | streichen | wie oben | dto. und `test_finalisieren_lehnt_leeres_arbeitsheft_ab` |
| `test_zeigt_fehler_fuer_arbeitsheft_bild_ohne_bildbeschreibung` | streichen | wie oben | dto. und `test_finalisieren_braucht_bildbeschreibung_mit_bild` |
| `test_zeigt_fehler_fuer_budget_null` | streichen | wie oben | dto. und `test_finalisieren_lehnt_nichtpositives_budget_ab` |
| `test_zeigt_fehler_fuer_fehlenden_kern_pin` | streichen | wie oben | dto. und `test_finalisieren_lehnt_fehlenden_kern_pin_ab` |
| `test_finalisiert_einen_entwurf_mit_ueberholtem_kern_pin` | streichen | Schichtdoppelung, die View trägt nichts bei. | `test_finalisieren_laesst_ueberholten_kern_pin_zu` |
| `test_zieht_aus_finaler_fassung_einen_entwurf_mit_geerbtem_bildpfad` | umschreiben | Schichtdoppelung: Prüft die Übernahme aller Felder, die `bearbeiten()` leistet, über `Vignette.objects.get(vorgaengerin=…)`. | Die Feldliste wandert in den Modelltest (siehe `test_bearbeiten_erbt_pin_und_akteure_ohne_finale_zu_mutieren`). Der View-Test prüft: POST leitet auf die Detailseite eines Entwurfs weiter, die ein Entwurfs-Badge und den Fehlermuster-Text der Quelle zeigt. |
| `test_laesst_die_finale_fassung_unveraendert` | streichen | Schichtdoppelung. | `test_bearbeiten_erbt_pin_und_akteure_ohne_finale_zu_mutieren` (Quelle bleibt final). Den Bildpfad schützt `test_finale_fassung_ist_unveraenderlich`. |
| `test_detail_bietet_die_neue_fassung_aktion_nur_fuer_finale_fassungen`, `test_erneute_aktion_oeffnet_den_bereits_vorhandenen_entwurf`, `test_nachfolgerin_verhindert_neue_fassung_mit_fehlermeldung`, `test_detail_verbirgt_neue_fassung_bei_nicht_archivierter_nachfolgerin` | behalten | Eigenes Verhalten der View: Angebot der Aktion, Wiederverwendung des Entwurfs, Meldung statt Fehlerseite. | – |
| `test_archiviert_eigene_finale_fassung_ueber_post`, `test_entarchiviert_eigene_archivierte_fassung_ueber_post` | umschreiben | Lesen den Zustand über `refresh_from_db()`, obwohl die Detailseite ihn selbst zeigt (Lesart oben). | POST mit `follow=True`: landet auf der Detailseite, die das Badge „Archiviert“ bzw. „Final“ und die Gegenaktion anbietet. Setup siehe unten. |
| `test_aktionen_sind_post_only_und_fuer_fremde_historien_unsichtbar` | behalten | HTTP-Naht der Lebenszyklus-Aktionen. Setup siehe unten. | – |
| `test_anonyme_zugriffe_werden_zum_login_geleitet`, `test_teilnehmerin_erhaelt_auf_alle_editor_urls_403`, `test_administratorin_erreicht_den_editor` | behalten | Zugriffsschutz jeder Route. Fällt der Alias `reversionieren` (#383), fällt sein Eintrag mit. | – |

### Setup über `objects._erstellen` (Startbefund 2)

Diese Tests bauen ihren Ausgangszustand über `_erstellen` statt über den Lebenszyklus. Ihr Urteil oben gilt für die Prüfung. Bei der Umsetzung wechselt das Setup auf `anlegen` → `finalisieren` → `bearbeiten()`/`archivieren()` bzw. auf die Helfer aus Startbefund 2.

- `test_vignetten_models.py`: `VignetteSichtbarFuerQuerySetTests.setUp`, `test_einbindbar_liefert_nur_finale_fassungen`, `VignetteFinalisierenTests._vollstaendigen_entwurf_anlegen` und `test_finalisieren_lehnt_nichtentwuerfe_ab`, alle Tests in `VignetteBearbeitenTests`.
- `test_views.py`: `_vignette_mit_eigentuemerinnen` (und damit alle Tests, die ihn nutzen), `VignetteListeViewTests`, die Detailtests zu Rohfeldern, Szenentext, Simulationshinweisen und fremder Fassung, `VignetteBearbeitenViewTests.setUp`, `test_versteckt_fremden_entwurf`, `test_versteckt_eigene_finale_fassung`, `VignetteAutovervollstaendigungViewTests`, `VignetteFormularSeiteTests`, `VignetteMarkdownVorschauViewTests.setUp`, `VignetteFeldbeschriftungenTests.setUp`, `VignetteLangeTexteViewTests.setUp`, `VignetteArchivierenViewTests` und `VignettenLoginTests`.

Nicht betroffen: `VignetteConstraintTests` (legitim) und die Tests, die schon über `anlegen` gehen (`VignetteAnlegenTests`, `VignetteFinalisierenViewTests`, `VignetteNeueFassungViewTests`, die Hinweistests zum überholten Kern-Pin und `test_koautorin_…`).

## Folge-Issues

- #381 Vignette anlegen ohne finalen Simulationskern endet mit 500
- #382 `vignetten.forms.FinalisierenForm` ist toter Code
- #383 Route `vignetten:reversionieren` ist ein Alias ohne Aufrufer
