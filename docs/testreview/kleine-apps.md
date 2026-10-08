# Testreview: Konten, Fragebogen-Items, Texte und Seeds

Bereich aus #331 (Spec #321). Geprüft sind alle Testdateien in `konten/tests/`, `fragebogen_items/tests/`, `texte/tests/` und `seeds/tests/`. Kein Test im Bereich patcht die Zeit (#324). Die Regel für Migrationstests (#325, ADR-0031) trifft genau einen Test in `konten`.

## Schnittstelle

### Konto (`konten/models.py`)

- **Aufrufe:**
  - `Konto.objects.create_user(...)` und `create_superuser(...)` wie bei Django. `Konto` ist `AUTH_USER_MODEL`.
  - `Konto.objects.mit_rolle_oder_administration(rolle)` liefert die Konten mit der Gruppe `rolle` und alle Superuser, ohne Duplikate. Einziger Aufrufer ist `EigentuemerKreis.moegliche_ergaenzungen`.
  - `konto.rollen()` nennt die Fachrollen in der Reihenfolge von `KONTOROLLEN` (Autor:in, Ausbilder:in, Forschende:r), dahinter „Administrator:in“, wenn das Konto Superuser ist.
  - `konto.delete()`.
- **Invarianten:**
  - `save()` setzt `is_staff = is_superuser`, auch bei `update_fields`.
  - Ein Konto lässt sich nicht löschen, solange es die einzige Eigentümerin eines aktiven Bestands ist (ADR-0032). Welche Bestände das sind, liefert `bestandsmodelle()`. Ob einer aktiv ist, sagt `ist_aktiv()`.
- **Fehlerfälle:** `delete()` wirft `ProtectedError(modell.LOESCHSPERRE_MELDUNG, [bestand])`. Kein Produktionscode fängt die Ausnahme. Der Django-Admin bietet kein Löschen an (#156), die Meldung sieht also heute niemand.
- **Konfiguration:** Der `post_migrate`-Handler `erstelle_kontorollen` (`konten/apps.py`) legt die drei Gruppen aus `KONTOROLLEN` an und entzieht ihnen bei jedem Lauf alle Django-Permissions.

### Kontoverwaltung (`konten/admin.py`)

- **Aufrufe:** die Admin-Routen `admin:konten_konto_add`, `…_change`, `…_changelist` und `admin:auth_user_password_change`.
- **Invarianten:**
  - Anlegen und Passwortwechsel laufen über Djangos `UserAdmin`. Passwörter liegen nur gehasht vor.
  - Die Anlage-Maske setzt Benutzername, Passwort, `is_active`, `is_superuser` und Gruppen.
  - `is_staff` und `user_permissions` erscheinen weder in den Masken noch in der Liste oder den Filtern.
  - Konten sind nicht löschbar: Die Löschseite antwortet 403, und die Sammelaktion „löschen“ fehlt (bis #156).
  - Den Django-Admin erreicht nur, wer Superuser ist. `is_staff` folgt aus `Konto.save()`.

### Rollen und Navigation (`konten/navigation.py`)

- **Aufrufe:**
  - Prädikate `ist_autorin`, `ist_forschende`, `ist_administratorin` und die Fabrik `rolle_oder_administration(gruppe)`.
  - Decorator-Fabrik `rolle_erforderlich(rollen_pruefung)` und die fertigen `autorin_erforderlich` und `administratorin_erforderlich`.
  - Context-Processor `navigation(request)`.
- **Invarianten:**
  - Die Administration besteht jede Rollenprüfung.
  - Der Decorator antwortet 403, auch Anonymen. Die Weiterleitung zum Login übernimmt `login_required` davor.
  - `navigation` liefert sechs Booleans. Anonyme sehen nichts. Konten ohne Rolle und ohne Administration sehen nur „Teilnahme“ und „Abschriften“. „Abschriften“ sieht jedes angemeldete Konto (ADR-0043). „System“ sieht nur die Administration.
  - Die Sidebar (`templates/includes/sidebar.html`) liest nur diese Booleans.
  - Jede Seite trägt die Bereichsfarbe ihrer Sidebar-Gruppe (`area--…`, ADR-0024).
- **Konfiguration:** die Gruppennamen `AUTORIN_GRUPPE`, `AUSBILDERIN_GRUPPE`, `FORSCHENDE_GRUPPE`.

### Eigentümer-Kreis (`konten/eigentuemerschaft.py`)

Die Schnittstelle steht in `docs/testreview/config-static.md` (#332). Für diesen Bereich zählt außerdem:

- `bestandsmodelle()` liefert heute genau Vignettenhistorie, Fragebogen-Item-Historie, Training und Erhebung.
- `ist_aktiv()` ist für Training und Fragebogen-Item-Historie immer wahr. Vignettenhistorie und Erhebung sind archiviert nicht mehr aktiv. Einziger Leser ist `Konto.delete()`.
- `austreten()` liest und schreibt in einer Transaktion. Zwei gleichzeitige Austritte können den Kreis deshalb nicht leeren.
- `hat_mehrere_eigentuemerinnen` steuert im Eigentümerinnen-Abschnitt, ob es eine Entfernen-Aktion gibt.

### Fragebogen-Item (`fragebogen_items/models.py`)

- **Aufrufe:**
  - Anlegen: `FragebogenItem.objects.anlegen(konto, *, typ="freitext", wortlaut="")` legt einen Entwurf samt neuer Historie an. Das Konto ist die erste Eigentümerin.
  - Lebenszyklus: `item.finalisieren()`, `item.bearbeiten() -> FragebogenItem`, `item.archivieren()`, `item.entarchivieren()`, `item.kann_entarchiviert_werden()`, `item.delete()`.
  - Abfragen: `FragebogenItem.objects.sichtbar_fuer(konto)`, `.einbindbar()` und `QuerySet.delete()`.
  - Die Historie: `FragebogenItemHistorie.objects.anlegen/sichtbar_fuer` und der Eigentümer-Kreis.
  - `LikertSkalenpol`: sechs Pole in aufsteigender Zustimmung, `stufen()`, `stufe_fuer(pol)`, `fuer_stufe(stufe)` und `stufenbereich_meldung()`.
- **Invarianten:**
  - Fassungen entstehen nur über `anlegen` und `bearbeiten`. `create`, `bulk_create`, `bulk_update`, `update` und ein `save()` auf einer neuen Instanz werfen `RuntimeError`.
  - Finale und archivierte Fassungen sind unveränderlich. Zustandswechsel laufen nur über die Lebenszyklus-Methoden.
  - Zum Finalisieren braucht es einen Wortlaut. `finalisiert_am` bleibt beim Archivieren und Entarchivieren erhalten.
  - Die Datenbank erlaubt je Historie höchstens einen Entwurf und je Vorgängerin höchstens eine nicht archivierte Nachfolgerin. `finalisiert_am` passt zum Zustand.
  - Gelöscht werden nur Entwürfe, einzeln wie gesammelt. Bleibt eine Historie ohne Fassung zurück, wird sie mitgelöscht, sonst sperrte sie das Löschen ihres Kontos.
  - Die Sichtbarkeit einer Fassung folgt dem Eigentümer-Kreis ihrer Historie. Die Administration sieht alles.
  - Die Likert-Pole sind global; ein Fragebogen-Item kann sie nicht konfigurieren.
- **Fehlerfälle:**
  - Verstöße gegen den Lebenszyklus werfen `ValidationError`.
  - `bearbeiten()` auf einer überholten Fassung endet aber in einem `IntegrityError` aus dem Constraint. Die Regel „nur die neueste nicht archivierte Fassung“ steht nur in der View (#376).
  - `fuer_stufe` außerhalb von 1–6 wirft `ValueError`.

### Fragebogen-Item-Editor (`fragebogen_items/views.py`)

- **Aufrufe:** `fragebogen_items:liste`, `anlegen`, `detail`, `bearbeiten` (GET/POST). Nur POST: `neue_fassung`, `finalisieren`, `archivieren`, `entarchivieren`, `loeschen`, `eigentuemerin_hinzufuegen`, `eigentuemerin_entfernen`.
- **Invarianten:**
  - Alle Routen verlangen eine Anmeldung und die Rolle Forschende:r oder die Administration, sonst 403.
  - Fremde Fassungen und Fassungen im falschen Zustand ergeben 404.
  - Die Bibliothek zeigt je sichtbarer Historie nur die neueste Fassung, mit Name (hilfsweise Wortlaut), Typ und Zustand.
  - Die Detailseite bietet nur die Aktionen an, die der Zustand erlaubt. „Neue Fassung“ gibt es nur auf der neuesten nicht archivierten Fassung, und ein vorhandener Entwurf wird wiederverwendet. „Entarchivieren“ gibt es nur, wenn `kann_entarchiviert_werden()` gilt.
  - Fragebogen-Items vom Typ Likert zeigen die sechs Pole in aufsteigender Reihenfolge, nur lesend.
  - Der Eigentümerinnen-Abschnitt nennt das Fragebogen-Item. Wer sich selbst austrägt, landet in der Bibliothek. Scheitert der Austritt, bleibt es bei der Detailseite.
- **Konfiguration:** keine.

### Markdown-Profile (`texte/markdown.py`, `texte/templatetags/texte.py`)

- **Aufrufe:**
  - `informationstext(quelle)` und `szenentext(quelle) -> SafeString`.
  - `woertlich(wert)` escaped einen Wert, damit er wörtlich erscheint.
  - `PROFILE[name]` liefert `rendern` und `hinweis`.
  - Template: die Filter `|informationstext`, `|szenentext` und `|markdown:profil` sowie das Tag `{% markdown_hinweis profil %}`.
- **Invarianten:**
  - Beide Profile kennen Absätze mit erhaltenem Zeilenumbruch, Fett, Kursiv, Listen, Zitat und eingerückte Codeblöcke. `#` bis `###` werden zu `h3` bis `h5`, tiefere Überschriften bleiben Text.
  - Rohes HTML, Bilder, Tabellen, Fences und Backticks erscheinen wörtlich.
  - Nur der Informationstext verlinkt, und nur auf `https:`, `http:` und `mailto:`. Web-Links öffnen in einem neuen Tab mit `rel="noopener noreferrer"` und einem Hinweis für Screenreader. E-Mail-Links öffnen keinen neuen Tab.
  - Eine leere Quelle ergibt einen leeren String.
- **Fehlerfälle:** Ein unbekannter Profilname wirft im Template einen `KeyError`.

### Lesefeld (`texte/templates/texte/includes/`)

- **Aufrufe:**
  - `markdown_lesefeld.html` mit `feld_id`, `label`, `wert`, `feld_name` oder `field`, optional `profil` und `offen`.
  - `lesefeld_formularfeld.html` mit `field` und optional `profil`.
  - `markdown_feld.html`, das Eingabefeld mit Vorschau. Das Lesefeld bindet es ein, wenn ein Profil gesetzt ist.
- **Invarianten:**
  - Mit Profil steht der Text gerendert im Profil, ohne Profil als Klartext mit `linebreaks`.
  - Ein leerer Text zeigt „Noch kein Text“ und den Knopf „Text schreiben“.
  - Das Label steht genau einmal.
  - „Speichern“ sendet das umgebende Formular, „Abbrechen“ nicht.
  - Ein Feld mit Fehlern startet geöffnet und zeigt den Fehler.
  - Mit Profil gibt es eine Vorschau, die das Profil an `texte:vorschau` schickt.

### Vorschau (`texte/views.py`)

- **Aufrufe:** `POST texte:vorschau` mit `profil` und `quelle`.
- **Invarianten:**
  - Nur angemeldete Autor:innen, Forschende und die Administration. Anonyme werden zum Login weitergeleitet, andere Konten erhalten 403.
  - GET ergibt 405.
  - Die Antwort ist das Fragment `<div class="markdown-text">…</div>`, gerendert mit derselben Funktion wie die Anzeigeseite.
- **Fehlerfälle:** Ein unbekanntes Profil ergibt 400.

### Seed `entwicklungsdaten_anlegen`

- **Aufrufe:** `manage.py entwicklungsdaten_anlegen`, ohne Argumente.
- **Invarianten:**
  - Läuft nur bei `DEBUG=True`, sonst `CommandError`.
  - Ist idempotent und legt alles über die öffentlichen Nähte an.
  - Legt die Konten `autor` (alle Rollen und Superuser) und `studi` (keine Rolle) mit dem Passwort `entwicklung` an.
  - Stellt eine finale Kern-Fassung mit dem Inhalt des Standardkerns bereit. Weicht die neueste finale Kern-Fassung davon ab, zieht er eine neue Kern-Fassung und spult die vorhandenen Vignetten darauf vor.
  - Legt eine aktive Fake-Konfiguration an.
  - Legt zwei finale Vignetten an, eine mit dem Positionsmarker `[bild]` zwischen zwei Textzeilen und eine mit reinem Bild-Arbeitsheft. Ihr Text erscheint als Szenentext ohne ungewollte Auszeichnung.
  - Legt ein veröffentlichtes Training und einen Trainingsentwurf an.
- **Fehlerfälle:** `CommandError`, wenn eine Kern-Fassung im Entwurf existiert.

### Seed `workshopdaten_anlegen`

- **Aufrufe:** `manage.py workshopdaten_anlegen [--anzahl N] [--praefix P] [--passwort X] [--passwoerter-neu]`.
- **Invarianten:**
  - Läuft auch bei `DEBUG=False`.
  - Legt N Konten `<praefix>01…` an, die genau die Rolle Autor:in tragen, ohne Administration.
  - Gibt die Anmeldedaten einmal aus. Wiederholte Läufe lassen die Passwörter stehen, außer mit `--passwoerter-neu`.
  - Stellt eine finale Kern-Fassung und die aktive Konfiguration `fake` bereit.
  - Ein Konto ist mehrfach gleichzeitig anmeldbar.

## Befunde

### `konten/tests/test_model.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_kontorollen_werden_nach_migration_angelegt`, `test_erneute_migration_dupliziert_kontorollen_nicht`, `test_erneute_migration_entfernt_berechtigungen_der_kontorollen` | behalten | Prüfen den `post_migrate`-Handler über seinen echten Auslöser. Die Erwartungen sind Literale. | – |
| `test_administrationsmigration_macht_gruppenmitglied_zum_superuser` | streichen | Startbefund bestätigt: totes Gewicht, die Migration `0002` liegt auf `main` (#325, ADR-0031). | Keiner nötig, Begründung ADR-0031. |
| `test_konto_kann_mehrere_rollen_tragen` | streichen | Prüft Djangos M2M `groups`. Eigenes Verhalten steckt nicht darin. | `test_rollen_nennen_alle_fachrollen_und_die_administration` trägt zwei Rollen und die Administration zugleich. |
| `test_rollen_nennen_alle_fachrollen_und_die_administration`, `test_rollen_sind_ohne_rolle_leer` | behalten | Eigene Methode, Erwartungen als Literale. Die Reihenfolge ist vertauscht eingegeben. | – |
| `test_konto_ist_das_aktive_nutzermodell` | streichen | Tautologisch: prüft die Zeile `AUTH_USER_MODEL` in den Settings. | `fragebogen_items/tests/test_views.py::FragebogenItemReversionierenViewTests::test_erstellt_aus_finaler_fassung_einen_entwurf` legt das Konto über `get_user_model()` an und trägt es über `anlegen` in den Eigentümer-Kreis ein, der auf `konten.Konto` zeigt. Mit einem anderen Nutzermodell scheiterte das, ebenso in jedem anderen Test, der so anlegt. |
| `test_konto_behaelt_django_standardfelder` | streichen | Prüft Djangos `AbstractUser`. | Keiner nötig. |
| `test_superuser_wird_beim_speichern_auch_staff` | umschreiben | Eigenes Verhalten, aber nur eine Richtung und ohne `update_fields`. | Ein Superuser wird Staff. Entzieht man ihm `is_superuser`, verliert er auch `is_staff`. Ein `save(update_fields=["is_superuser"])` schreibt `is_staff` mit. Jeweils nach `refresh_from_db()`. |
| `test_konten_mit_rolle_oder_administration_enthaelt_beide` | streichen | Schichtdoppelung: Der einzige Aufrufer ist `moegliche_ergaenzungen`. | `config/tests/test_eigentuemer_kreis_contract.py::test_kandidatenliste_nennt_die_rolle_und_die_administration` prüft dieselbe Menge (Rolle, Administration, kein rollenloses Konto) für alle vier Bestände. |
| `test_konto_loeschen_alleinige_eigentuemerin_aktiver_historie_wird_blockiert` | streichen | Schichtdoppelung mit dem Vertrag. | `test_einzige_eigentuemerin_eines_aktiven_bestands_ist_nicht_loeschbar` (Fall `Vignettenhistorie`) |
| `test_konto_loeschen_archivierte_oder_geteilte_historie_ist_erlaubt` | umschreiben | Der Fall „geteilt“ steht schon im Vertrag. Beide Fälle haben keine Zusicherung; der Test besteht schon, wenn `delete()` nicht wirft. | Nur der Fall „archiviert“: Die einzige Eigentümerin einer archivierten Vignettenhistorie wird gelöscht, danach gibt es das Konto nicht mehr. `archiviert=True` bleibt gesetzt, bis #236 eine öffentliche Geste bringt. |
| `test_konto_loeschen_alleinige_eigentuemerin_eines_trainings_wird_blockiert` | streichen | Schichtdoppelung mit dem Vertrag. `match="Trainings"` prüft die `LOESCHSPERRE_MELDUNG`, die bis #156 niemand zu sehen bekommt. | `test_einzige_eigentuemerin_eines_aktiven_bestands_ist_nicht_loeschbar` (Fall `Training`). Will man festhalten, welcher Bestand sperrt, gehört `excinfo.value.protected_objects == {bestand}` in den Vertrag. |
| `test_konto_loeschen_geteiltes_training_ueberlebt` | streichen | Schichtdoppelung. | `test_eine_von_zwei_eigentuemerinnen_ist_loeschbar` (Fall `Training`) |
| `test_konto_loeschen_aktive_alleinige_erhebung_wird_blockiert` | streichen | wie beim Training | `test_einzige_eigentuemerin_eines_aktiven_bestands_ist_nicht_loeschbar` (Fall `Erhebung`) |
| `test_konto_loeschen_geteilte_oder_archivierte_erhebung_ueberlebt` | umschreiben | Der geteilte Teil steht schon im Vertrag. Der archivierte Teil setzt den Status über die private Naht `_schreibqueryset()`; das ist der einzige SLF001-Treffer der Datei. Die Sichtbarkeit für die Administration prüft schon der Vertrag. | Nur der Fall „archiviert“, über den öffentlichen Lebenszyklus wie in `test_erhebung_ist_archiviert_nicht_mehr_aktiv`: Konfiguration aktivieren, `anlegen`, `finalisieren()`, `archivieren()`. Danach die einzige Eigentümerin löschen; die Erhebung bleibt ohne Eigentümerin bestehen. Damit kann `konten/tests/test_model.py` von der SLF001-Übergangsliste. |
| `test_konto_meldet_sich_mit_username_und_passwort_an` | streichen | Prüft Djangos `authenticate`. | `config/tests/test_startseite.py::test_direkter_login_fuehrt_zur_startseite` meldet sich über HTTP an. |
| `test_konto_loeschen_alleinige_eigentuemerin_einer_item_historie_wird_blockiert` | streichen | Schichtdoppelung, Meldungsprüfung wie beim Training. | `test_einzige_eigentuemerin_eines_aktiven_bestands_ist_nicht_loeschbar` (Fall `FragebogenItemHistorie`) |
| `test_konto_loeschen_geteilte_item_historie_ueberlebt` | streichen | Schichtdoppelung. | `test_eine_von_zwei_eigentuemerinnen_ist_loeschbar` (Fall `FragebogenItemHistorie`) |
| `test_konto_loeschen_fassungslose_item_historie_blockiert_nicht` | streichen | Prüft das Aufräumen in `fragebogen_items`, nicht in `konten`. Wenn die Historie weg ist, ist das Konto löschbar, ohne dass `Konto.delete()` etwas Eigenes beiträgt. | `fragebogen_items/tests/test_fragebogen_item_models.py::test_loeschen_der_letzten_fassung_raeumt_die_historie_ab`. Dass eine Historie mit Fassung sperrt, prüft der Vertrag. |

### `konten/tests/test_admin.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_administration_legt_konto_mit_gehashtem_passwort_an`, `test_administration_vergibt_rolle_und_superuser_beim_anlegen`, `test_administration_aendert_passwort_gehasht`, `test_administration_entzieht_rolle` | behalten | HTTP über die Admin-Routen. Sie halten die Wahl von `UserAdmin` und die eigene `KontoCreationForm` fest. | – |
| `test_nur_superuser_erreicht_nicht_leeren_admin_index` | umschreiben | Die Links stehen als feste Pfade (`'href="/admin/konten/konto/"'`). | Die Pfade über `reverse("admin:konten_konto_changelist")` und `reverse("admin:auth_group_changelist")` bilden. Der Rest bleibt. |
| `test_masken_zeigen_nur_rollenfelder_und_keine_loeschwege` | umschreiben | Implementation-coupled: `deletelink`, `column-is_staff` und `is_staff__exact` sind Markup und Query-Parameter von Djangos Admin-Templates. Ein Django-Update kann sie umbenennen; die Abwesenheitsprüfungen bestünden dann grundlos. | Zwei Tests. (1) Felder: Die Schlüssel von `detail.context["adminform"].form.fields` enthalten `groups` und `is_superuser`, aber nicht `is_staff` und `user_permissions`. `liste.context["cl"].list_display` enthält `is_superuser`, aber nicht `is_staff`. (2) Löschen: Die Löschseite antwortet 403. Ein POST der Sammelaktion `delete_selected` mit dem Konto lässt es bestehen. |

### `konten/tests/test_eigentuemerschaft.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_die_vier_bestaende_tragen_den_gemeinsamen_kreis` | behalten | Die einzige Stelle, die festhält, welche Modelle `bestandsmodelle()` liefert. Der Vertragstest verweist darauf. Die Erwartung ist eine feste Menge. | – |
| `test_simulationskern_traegt_keinen_eigentuemer_kreis` | streichen | Totes Gewicht: `not hasattr(…, "eigentuemerinnen")` prüft eine Abwesenheit. | Die Mengengleichheit in `test_die_vier_bestaende_tragen_den_gemeinsamen_kreis` schließt den Kern schon aus. |
| `test_jeder_kreis_zeigt_auf_konten` | streichen | Tautologisch: Das Feld ist auf der abstrakten Basis deklariert, alle Erbinnen haben es per Konstruktion. Es prüft `_meta`, nicht das Verhalten. | Jeder Vertragstest trägt Konten in den Kreis ein und liest sie aus. |
| `test_jeder_kreis_nennt_seine_rollengruppe` | umschreiben | Die Erwartungen sind Modulkonstanten (`AUTORIN_GRUPPE` …), und `ROLLENGRUPPE` wird als Attribut geprüft. Der Vertragstest benutzt `modell.ROLLENGRUPPE` selbst als Eingabe, hält die Zuordnung also nicht fest. | Parametrisiert über `bestandsmodelle()` mit Literal je Modell (`Vignettenhistorie → "Autor:in"`, `Training → "Ausbilder:in"`, `Erhebung → "Forschende:r"`, `FragebogenItemHistorie → "Forschende:r"`). Ein Konto mit genau dieser Gruppe steht in `moegliche_ergaenzungen()`, ein Konto mit einer anderen Fachrolle nicht. |
| `test_training_und_item_historie_sind_immer_aktiv` | streichen | Schichtdoppelung: Der einzige Leser von `ist_aktiv()` ist `Konto.delete()`. | `test_einzige_eigentuemerin_eines_aktiven_bestands_ist_nicht_loeschbar` sperrt für beide Modelle. Das gelingt nur, wenn sie aktiv sind. |
| `test_vignettenhistorie_ist_archiviert_nicht_mehr_aktiv` | streichen | Schichtdoppelung, wie oben. | Der umgeschriebene `test_konto_loeschen_archivierte_oder_geteilte_historie_ist_erlaubt` (archiviert, löschbar). Dass eine nicht archivierte sperrt, prüft der Vertrag. Erst streichen, wenn die Umschreibung umgesetzt ist. |
| `test_erhebung_ist_archiviert_nicht_mehr_aktiv` | streichen | Schichtdoppelung, wie oben. | Der umgeschriebene `test_konto_loeschen_geteilte_oder_archivierte_erhebung_ueberlebt`, dazu der Vertrag. Erst streichen, wenn die Umschreibung umgesetzt ist. |
| `test_kreis_meldet_ob_mehr_als_eine_eigentuemerin_eingetragen_ist` | behalten | Öffentliche Eigenschaft, die das gemeinsame Template liest. Der Docstring („was heute vier Views als Kontext bauen“) ist veraltet und sollte beim Umsetzen mitgehen. | – |
| `test_austritt_eines_fremden_kontos_entfernt_nichts` | behalten | Nur hier geprüft, der Vertrag kennt den Fall nicht. | – |
| `test_archivierter_bestand_behaelt_seine_letzte_eigentuemerin` | behalten | Der Querschnitt-Review (#332) nennt ihn als Ersatz für den gepatchten Vertragsfall. | – |
| `test_austritt_laeuft_vollstaendig_in_einer_transaktion` | behalten | Beobachtet SQL statt Verhalten und hängt am Tabellennamen. Der eigentliche Fehler, ein Wettlauf zweier Austritte, lässt sich unter SQLite nicht deterministisch herbeiführen. Ohne den Test bliebe die Zusage aus ADR-0032 ungeprüft. | – |

### `konten/tests/test_navigation.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_navigation_berechnet_sichtbarkeit_aus_kontorollen` | behalten | Der Context-Processor ist eine öffentliche Funktion. Die Tabelle aus Literalen ist die Spec der Sichtbarkeit. | – |
| `test_ist_administratorin_prueft_die_administrationsrolle` | streichen | Tautologisch: Die Funktion ist `return konto.is_superuser`, der Test spiegelt sie. | `test_administratorin_erforderlich_schuetzt_views_mit_der_administrationsrolle` und die Administrationszeile von `test_navigation_berechnet_sichtbarkeit_aus_kontorollen` |
| `test_administratorin_erforderlich_schuetzt_views_mit_der_administrationsrolle` | behalten | Öffentlicher Decorator, inklusive anonymem Konto. | – |
| `SidebarNavigationTests` (`test_teilnehmerin_sieht_nur_teilnahme_links`, `test_autorin_sieht_entwicklung_mit_lesendem_kern_link`, `test_jede_rolle_erreicht_die_abschriften`, `test_forschende_sieht_forschungsbereich`, `test_administratorin_sieht_alle_bereiche_ausser_teilnahme`) | behalten | HTTP. Sie belegen, dass das Template die Booleans in Links umsetzt; die Funktion allein zeigt das nicht. | – |
| `test_ausbilderin_sieht_nur_kuratierung_in_der_ausbildung` | umschreiben | `"Trainingsdaten <small>geplant</small>"` hängt am Markup. | `assertIn("Trainingsdaten", sidebar)`. Der Rest bleibt. |
| `test_simulationskern_verwalten_steht_unter_entwicklung` | umschreiben | Schneidet die Sidebar an den Klassen `sidebar-nav__group--development` und `--system`. | An den sichtbaren Gruppenköpfen schneiden: vom `<h2>Entwicklung</h2>` bis zum nächsten `<h2>`, vom `<h2>System</h2>` bis `</section>`. |
| `BereichszuordnungTests::test_seiten_tragen_den_bereich_ihrer_sidebar_gruppe` | behalten | Die Klasse `area--…` ist die einzige beobachtbare Form der Bereichsfarbe (ADR-0024). #332 nennt den Test als Ersatz. | – |

### `fragebogen_items/tests/test_fragebogen_item_models.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_anlegen_erstellt_entwurf_mit_historie_und_eigentuemerin` | behalten | Eigene Anlege-Naht der Fassung, nicht die der Historie aus dem Vertrag. | – |
| `test_anlegen_laesst_keine_lebenszykluswerte_zu` | streichen | Prüft die Signatur über Pythons `TypeError` für ein unbekanntes Schlüsselwort, also die Abwesenheit eines Parameters. | `test_anlegen_erstellt_entwurf_mit_historie_und_eigentuemerin` belegt den Entwurf. Ein `zustand="final"` ohne `finalisiert_am` scheiterte am Check-Constraint, siehe `test_check_constraint_gilt_bei_direktem_save`. |
| `test_historie_kennt_keine_archivierung_als_ganzes` | streichen | Startbefund bestätigt: totes Gewicht, `_meta.fields` und `hasattr` prüfen Abwesenheit. Der Test widerspricht zudem dem offenen #236, das genau diese Archivierung einführt. | Keiner nötig. |
| `test_sichtbar_fuer_liefert_nur_den_eigentuemer_kreis`, `test_sichtbar_fuer_liefert_alle_historien_fuer_administration` | streichen | Schichtdoppelung, wie #332 schon festhält. | `config/tests/test_eigentuemer_kreis_contract.py::test_sichtbar_sind_die_eigenen_bestaende_und_der_administration_alle` (Fall `FragebogenItemHistorie`). Ein weiteres Mitglied des Eigentümer-Kreises deckt `test_sichtbar_fuer_liefert_fassungen_der_koeigentuemerin` auf Fassungsebene. |
| `FragebogenItemQuerySetTests::test_sichtbar_fuer_liefert_fassungen_der_eigentuemerin`, `…_der_koeigentuemerin`, `…_dritten_keine_fassungen`, `…_der_administration_alle_fassungen` | behalten | Die Fassungs-`sichtbar_fuer` deckt der Vertrag nicht ab. | – |
| `test_sichtbar_fuer_ist_nach_zustandsfilter_verkettbar`, `test_sichtbar_fuer_ist_vor_zustandsfilter_verkettbar` | streichen | `einbindbar()` ist selbst ein Zustandsfilter. Die beiden Tests wiederholen die `einbindbar`-Tests mit `filter(zustand=…)`. | `test_sichtbar_fuer_ist_nach_einbindbar_verkettbar`, `test_sichtbar_fuer_ist_vor_einbindbar_verkettbar` |
| `test_sichtbar_fuer_ist_nach_einbindbar_verkettbar`, `test_sichtbar_fuer_ist_vor_einbindbar_verkettbar` | umschreiben | Im `setUp` sind alle drei Fassungen final. `einbindbar()` filtert dort also nichts, und die Tests prüfen nur die Verkettung. | Im `setUp` zusätzlich einen eigenen Entwurf und eine eigene archivierte Fassung anlegen. Beide Reihenfolgen liefern dann genau `[eigenes, geteiltes]`. So ist zugleich belegt, dass `einbindbar()` Entwürfe und Archiviertes ausschließt. |
| `FragebogenItemConstraintTests::_direkt_speichern` | umschreiben | Baut die Anlege-Naht mit `item._wird_angelegt = True` nach. Das ist der SLF001-Treffer der Datei. | `FragebogenItem.objects._erstellen(**werte)` mit `# noqa: SLF001` an dieser einen Zeile. Das ist die interne Naht, die #321 für Constraint-Tests ausdrücklich erlaubt. Danach die Datei von der Übergangsliste streichen. |
| `test_constraints_gelten_bei_direktem_save`, `test_check_constraint_gilt_bei_direktem_save` | behalten | Constraint-Tests über die interne Naht, von #321 erlaubt. | – |
| `test_archivierte_schwester_gibt_vorgaengerin_fuer_neue_fassung_frei` | umschreiben | Braucht die interne Naht nicht: Der Fall lässt sich über den öffentlichen Lebenszyklus herstellen. | `schwester = vorgaengerin.bearbeiten()`, finalisieren, archivieren. Danach liefert `vorgaengerin.bearbeiten()` einen Entwurf mit `vorgaengerin` als Vorgängerin. |
| `test_reversionieren_erhaelt_finale_vorgaengerin_und_erweitert_die_kette`, `test_finalisieren_bearbeiten_und_archivieren` | behalten | Öffentlicher Lebenszyklus, Erwartungen als Literale. | Lücken, nicht Teil dieses Reviews: Finalisieren ohne Wortlaut, `bearbeiten()` auf einem Entwurf und ein direkter Zustandswechsel über `save()` sind nirgends geprüft. |
| `test_nur_entwuerfe_duerfen_physisch_geloescht_werden`, `test_loeschen_der_letzten_fassung_raeumt_die_historie_ab`, `test_loeschen_einer_fassung_neben_anderen_erhaelt_die_historie`, `test_massenloeschung_raeumt_leer_gewordene_historien_ab` | behalten | Öffentliche Schnittstelle (`delete()` einzeln und gesammelt). Belegt wird über den Manager der Historie. | – |
| `FragebogenItemSchreibnahtTests` (3 Tests) | behalten | Die Sperre der Massenschreibwege ist eine Zusage der Schnittstelle. `update()` fehlt; das kann beim Umsetzen dazu. | – |
| `test_likert_skalenpole_sind_aufsteigend_deklariert` | behalten | Die Liste der Pole ist die Spec der globalen Skala. | – |
| `test_likert_skalenpol_wird_aus_seiner_stufe_abgeleitet` | streichen | Tautologisch: Die Erwartung kommt aus `enumerate(LikertSkalenpol)`, also aus der Reihenfolge des Moduls. `fuer_stufe` hat außerdem keinen Aufrufer (#377). | Keiner nötig, wenn #377 die Methode entfernt. Bleibt sie, wird der Test umgeschrieben: `fuer_stufe(1)` ist „Stimme gar nicht zu“, `fuer_stufe(6)` ist „Stimme voll zu“, `0` und `7` werfen `ValueError`. |
| `test_likert_stufe_wird_aus_ihrem_skalenpol_abgeleitet` | umschreiben | Tautologisch wie oben. | Literale: `stufe_fuer(STIMME_GAR_NICHT_ZU) == 1`, `stufe_fuer(STIMME_VOLL_ZU) == 6`. Der Export (`erhebungen`) und das Antwortformular lesen diese Zuordnung. |
| `test_likert_skalenpole_sind_nicht_pro_item_konfigurierbar` | streichen | Startbefund bestätigt: totes Gewicht, `_meta.fields` prüft eine Abwesenheit. | `test_views.py::FragebogenItemLikertViewTests::test_detail_zeigt_die_likert_stufen_aufsteigend` zeigt die globalen Pole an jedem Fragebogen-Item vom Typ Likert. |

**Startbefund Abwesenheitstests: bestätigt.** Beide Tests fallen weg.

### `fragebogen_items/tests/test_views.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `FragebogenItemAnlegenViewTests` (2 Tests) | behalten | HTTP mit Redirect und Wirkung. | – |
| `test_zeigt_finalisieren_bei_entwurf`, `test_finalisieren_leitet_zur_detailansicht_weiter`, `test_finalisieren_setzt_den_finalen_zustand`, `test_finalisierte_fassung_zeigt_keine_finalisieren_aktion`, `test_finalisieren_akzeptiert_keine_bereits_finale_fassung` | behalten | Eigene View-Logik: Angebot je Zustand, Redirect und 404 im falschen Zustand. | – |
| `test_finalisieren_setzt_den_zeitpunkt` | streichen | Den Zeitpunkt setzt das Modell; die View trägt nichts bei. Eine finale Fassung ohne `finalisiert_am` verbietet der Check-Constraint. | `test_finalisieren_setzt_den_finalen_zustand` zusammen mit `test_check_constraint_gilt_bei_direktem_save` |
| `test_finalisierte_fassung_zeigt_final_in_der_bibliothek` | streichen | Schichtdoppelung innerhalb der Datei. | `FragebogenItemListeViewTests::test_zeigt_pro_historie_nur_die_neueste_fassung_mit_ihrem_zustand` zeigt „Final“ in der Bibliothek. Den Übergang per POST prüft `test_finalisieren_setzt_den_finalen_zustand`. |
| `FragebogenItemReversionierenViewTests` (4 Tests) | behalten | Eigene View-Logik: Entwurf aus der finalen Fassung, Typwechsel-Hinweis, keine neue Fassung aus einer überholten Fassung, archivierte Detailseite. Nach #376 prüft der Modelltest die Regel. Der View-Test hält dann nur noch Angebot und Abweisung fest. | Lücke, nicht Teil dieses Reviews: Dass `neue_fassung` einen vorhandenen Entwurf wiederverwendet, statt einen zweiten anzulegen, prüft kein Test. |
| `test_finale_fassung_bietet_archivieren`, `test_archivieren_leitet_zur_detailansicht_weiter`, `test_archivieren_setzt_den_archivierten_zustand`, `test_archivierte_fassung_bietet_entarchivieren`, `test_entarchivieren_leitet_zur_detailansicht_weiter`, `test_entarchivieren_setzt_den_finalen_zustand`, `test_archivierte_schwester_mit_aktiver_nachfolgerin_bleibt_archiviert` | behalten | HTTP, eigene Bedingungen. | – |
| `test_archivieren_ist_destruktiv_gekennzeichnet` | streichen | Implementation-coupled: sucht die CSS-Klasse `button--danger` irgendwo auf der Seite. Die Klasse belegt nicht, welcher Knopf sie trägt, und die Farbe sieht pytest nicht. | Keiner. Wie in #332 bleibt visuelles Verhalten ohne Browsertest ungeprüft. |
| `test_editor_bietet_keine_historien_archivierung` | streichen | Totes Gewicht: prüft die Abwesenheit einer verworfenen Geste, die #236 jetzt doch einführen will. | Keiner nötig. |
| `test_entarchivieren_erhaelt_den_finalisierungszeitpunkt` | streichen | Schichtdoppelung: Den Zeitpunkt hält das Modell, die View ruft nur `entarchivieren()`. | `test_fragebogen_item_models.py::test_finalisieren_bearbeiten_und_archivieren` prüft `finalisiert_am` nach Archivieren und Entarchivieren. |
| `test_entwurf_bietet_loeschen`, `test_loeschen_leitet_zur_bibliothek_weiter`, `test_loeschen_entfernt_den_entwurf` | behalten | – | – |
| `test_loeschen_ist_destruktiv_gekennzeichnet` | streichen | wie `test_archivieren_ist_destruktiv_gekennzeichnet` | Keiner. |
| `FragebogenItemSichtbarkeitViewTests` (2 Tests) | behalten | Eigene Rollenprüfung und Sichtbarkeit über HTTP. | – |
| `FragebogenItemKoautorschaftViewTests` (11 Tests) | behalten | Eigene View-Logik der App: Rollenprüfung, Objektauflösung, Rückweg nach Selbstaustritt, Wortlaut des Abschnitts. #364 legt die Views zusammen und verlangt, dass diese Tests ohne inhaltliche Änderung grün bleiben. | – |
| `test_detail_zeigt_die_likert_stufen_aufsteigend` | behalten | Erwartung als Literal. | – |
| `test_detail_enthaelt_keine_eingabefelder_fuer_skalenpole` | streichen | Totes Gewicht: prüft die Abwesenheit eines Felds, das es nie gab. Die Detailseite hat kein Formular für Item-Inhalte. | Keiner nötig. |
| `test_zeigt_pro_historie_nur_die_neueste_fassung_mit_ihrem_zustand` | umschreiben | `badge--final` und `badge--research` sind CSS-Klassen. Den Zustand belegt schon der sichtbare Text „Final“. | Die beiden Klassen-Zusicherungen streichen, der Rest bleibt. |
| `test_zeilen_sind_ueber_den_namen_verlinkt` | umschreiben | `class="zeilenlink"` und `table--zeilenlink` sind Markup. `button--secondary` und `>Aktion<` prüfen die Abwesenheit entfernter Elemente. | Die Zeile verlinkt die Detailseite: `href="{reverse('fragebogen_items:detail', …)}"` steht genau einmal auf der Seite. |

### `texte/tests/test_markdown.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `GemeinsamerUmfangTests` (12 Tests) | behalten | Die Schnittstelle ist das HTML. Die Erwartungen sind Literale. Die Negativprüfungen (`<script`, `<img`, `<table` …) sind die Sicherheitszusage, keine Abwesenheit entfernter Felder. | – |
| `InformationstextLinkTests` (3 Tests) | behalten | – | – |
| `SzenentextLinkTests::test_link_syntax_bleibt_woertlich` | behalten | – | – |
| `WoertlichTests::test_markdown_zeichen_eines_werts_wirken_nicht` | behalten | Die Erwartung kommt aus Djangos `escape`, nicht aus dem Modul. | – |
| `ProfilRegisterTests::test_register_rendert_wie_die_einstiegspunkte` | streichen | Tautologisch: `PROFILE[…].rendern` *ist* `informationstext` bzw. `szenentext`, der Test vergleicht eine Funktion mit sich selbst. | `texte/tests/test_vorschau.py::test_informationstext_rendert_links_im_eigenen_container` und `test_szenentext_laesst_link_syntax_woertlich_stehen` holen das Profil über das Register und prüfen den Unterschied im HTML. |
| `ProfilRegisterTests::test_nur_der_informationstext_nennt_link_syntax` | behalten | Der Hinweis ist sichtbarer Editortext, keine Doku. Die Zusage „Szenentext wirbt nicht mit Links“ hat eine feste Erwartung. | – |

### `texte/tests/test_lesefeld.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_rendert_den_text_im_uebergebenen_profil` | behalten | Das gerenderte Include ist die Schnittstelle. `"profil": "szenentext"` ist der vom Server eingesetzte Wert im `hx-vals` und damit der einzige Beleg, dass die Vorschau das richtige Profil schickt. | – |
| `test_leerer_text_laedt_zum_schreiben_ein`, `test_traegt_das_label_nur_einmal` | behalten | – | – |
| `test_speichern_sendet_das_umgebende_formular` | umschreiben | `feld.value = feld.defaultValue` ist ein fester JS-Ausdruck im Template, also Quelltext. Der Knopf wird mit Markup samt `class="button"` gesucht. | Über einen Parser wie `config/tests/formular.py`: „Speichern“ ist der einzige Absendeknopf, „Abbrechen“ ist keiner. `submit_knoepfe` nimmt heute eine `HttpResponse`; für gerenderte Strings braucht er eine Variante. Die JS-Zusicherung fällt weg. |
| `LesefeldFormularfeldTests::test_markdown_feld_liest_wert_und_label_aus_dem_formularfeld`, `test_leerer_klartext_laedt_zum_schreiben_ein` | behalten | – | – |
| `test_klartext_steht_ohne_markdown_und_ohne_vorschau` | umschreiben | Die letzte Zusicherung sucht den Knopf mit Markup samt `class="button"`. | „Speichern“ als Absendeknopf, wie oben. |
| `test_feld_mit_fehler_startet_offen` | behalten | `bearbeiten: true` ist der vom Server entschiedene Startzustand in der Ausgabe, nicht fester Quelltext. Ohne Browser ist das der einzige Beleg. | – |

Keine Schichtdoppelung mit den Apps: Die Editor-Tests in `vignetten`, `simulation` und `erhebungen` prüfen nicht die Mechanik der Hülle.

### `texte/tests/test_vorschau.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `VorschauTests` (7 Tests) | behalten | HTTP mit Rollen, Methode, Fehlerfall und Profilwahl. `<h3>` und `<strong>` in `test_informationstext_rendert_links_im_eigenen_container` wiederholen `test_markdown.py`, aber der Test belegt dazu den Container und das gewählte Profil. | – |

### `seeds/tests/test_entwicklungsdaten.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_legt_vignetten_mit_allen_neuen_feldern_an` | behalten | Prüft, dass die Demodaten die Fälle abdecken, die man manuell testen will (Positionsmarker zwischen zwei Textzeilen, reines Bild-Arbeitsheft). „neue Felder“ im Namen ist veraltet. | – |
| `test_aufgabenkontext_erscheint_als_szenentext_unverfaelscht` | behalten | Prüft echte Daten gegen den echten Renderer. | – |
| `test_aktive_modell_konfiguration_traegt_eine_bezeichnung` | umschreiben | Tautologisch: „Offline (fake)“ ist aus dem Command abgeschrieben. Zugesagt ist laut Docstring nur, dass die Konfiguration erkennbar ist. | `assertTrue(aktive.bezeichnung)` und `aktive.sprachmodell == "fake"`. |
| `test_zweiter_lauf_ist_idempotent` | behalten | Zählt nur Vignetten. Konten und Trainings lassen sich beim Umsetzen ergänzen. | – |
| `test_trainings_werden_fuer_die_ausbilderin_im_eigentuemerinnenkreis_angelegt` | behalten | – | – |
| `test_autor_ist_administrationskonto` | umschreiben | `is_staff` wiederholt `Konto.save()`. | Nur `is_superuser`. Den Staff-Status deckt `konten/tests/test_model.py::test_superuser_wird_beim_speichern_auch_staff`. |

Lücke: Die Weigerung bei `DEBUG=False` ist nicht getestet. Sie schützt Produktivdatenbanken; ein Test mit `override_settings(DEBUG=False)` und `CommandError` gehört ins Umsetzungsticket.

### `seeds/tests/test_workshopdaten.py`

| Test | Urteil | Anti-Pattern / Grund | Deckender Ersatztest bzw. Zieltest |
|---|---|---|---|
| `test_legt_zehn_reine_autorenkonten_mit_nutzbarem_passwort_an` | behalten | Prüft genau das, was der Seed zusagt: Rolle, keine Administration, Anmeldung mit den ausgegebenen Daten. | – |
| `test_stellt_kern_und_aktive_modell_konfiguration_bereit` | umschreiben | Tautologisch: `SIMULATIONSMODELL` wird aus dem geprüften Command importiert, und „Workshop (fake)“ ist abgeschrieben. | `aktive.sprachmodell == "fake"` als Literal, die Bezeichnung nur als nicht leer. Danach entfällt der Import aus dem Command. |
| `test_zweiter_lauf_legt_nichts_doppelt_an_und_laesst_passwoerter_stehen`, `test_passwoerter_neu_setzt_die_zugaenge_zurueck`, `test_gemeinsames_passwort_gilt_fuer_alle_konten` | behalten | Optionen und Idempotenz des Commands. | – |
| `WorkshopkontoRechteTests::test_autorenbereiche_sind_erreichbar` | streichen | Schichtdoppelung: Ob die Rolle Autor:in eine Seite öffnet, prüfen die Apps. Der Seed trägt nur „genau Autor:in, kein Superuser“ bei. | `test_legt_zehn_reine_autorenkonten_mit_nutzbarem_passwort_an` für die Rollen. Die Zugänge prüfen `vignetten/tests/test_views.py` (Autorinnen-Editor), `simulation/tests/test_kern_view.py::test_verweist_autorinnen_nicht_auf_die_verwaltung` und `sitzungen/tests/test_probelauf.py::ProbelaufStartTests`. |
| `WorkshopkontoRechteTests::test_fremde_bereiche_bleiben_verschlossen` | streichen | Schichtdoppelung wie oben. | `erhebungen/tests/test_forschenden_views.py::test_konto_ohne_forschendenrolle_erhaelt_auf_alle_forschenden_views_403`, `training/tests/test_views.py::test_konto_ohne_ausbilderrolle_kann_kein_training_anlegen`, `fragebogen_items/tests/test_views.py::test_konto_ohne_forschungsrolle_erhaelt_403`, `sitzungen/tests/test_probelauf.py::test_nicht_administratorin_erreicht_freien_auswaehler_nicht` |
| `WorkshopkontoRechteTests::test_dasselbe_konto_ist_mehrfach_gleichzeitig_angemeldet` | behalten | Die einzige Zusage, die der Command ausdrücklich ausgibt. Heute ist sie Django-Standard. Sie bricht, sobald jemand Anmeldungen je Konto begrenzt. Ohne die beiden anderen Tests braucht die Klasse ihr `setUp` nicht mehr; der Test kann in `WorkshopdatenTests` wandern. | – |

**Startbefund Workshop-Seed: bestätigt.**

- Die Laufzeit hat #323 behoben: `conftest.py` setzt MD5 als Hasher.
- Die beiden Rechteprüfungen wiederholen die Rollentests der Apps. Sie fallen weg.
- Der Seed-spezifische Teil bleibt: die Rollenmenge der Konten und die Mehrfachanmeldung.

## Folge-Issues

- #376 `FragebogenItem.bearbeiten()` kennt die Nachfolgerinnen-Regel nicht. Auf einer überholten Fassung endet der Aufruf in einem `IntegrityError`; die Regel steht nur in der View. `Vignette.bearbeiten()` prüft sie im Modell.
- #377 `LikertSkalenpol.fuer_stufe` hat keinen Aufrufer außer seinem Test.
