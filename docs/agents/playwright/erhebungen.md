# Erhebungen

Die App `erhebungen/` unter `/erhebungen/`: Erhebungen anlegen und zusammenstellen, finalisieren, Stichproben, Teilnahme über den Teilnahme-Link (ohne Konto), Einsicht und Datenspur-Export. Setzt [README.md](README.md) voraus (Sessions, Anmelden, Produktion, Formulare, Snapshots). Das Gespräch selbst (Senden, Beenden, Debrief, Diagnose, Abbrechen) steht in [sitzungen.md](sitzungen.md), die Items selbst in [fragebogen_items.md](fragebogen_items.md); hier steht nur, wie sie in eine Erhebung kommen und wo sie im Ablauf erscheinen. Begriffe: `GLOSSARY.md` (Erhebung, Stichprobe, Teilnahme-Link, Teilnahme-Token, Teilnahmekennung, Einwilligungen, Flüchtige Teilnahme, Datenspur, Fremdeinsicht, Andockpunkt, Itemblock); Soll-Verhalten: `docs/verhalten.md`, «Erhebungsteilnahme», «Erhebungen verwalten», «Einsicht in die Erhebung». Texte und Items der ersten Studie: `docs/erhebung/2026-09-23-erhebungstexte.md`.

## Prod

Auf <https://onthefly.fgrng.de/> laufen Erhebungen mit echten Teilnehmer:innen; jede Teilnahme ist ein Forschungsdatum. Zusätzlich zu [Produktion](README.md#produktion):

- **Einen Teilnahme-Link nie öffnen**, auch nicht zum Ansehen: Schon der GET auf `/erhebungen/teilnahme/<uuid>/` legt eine Teilnahme mit Token an. Sie zählt in der Spalte «Teilnahmen», steht im Export, und die Stichprobe gilt ab da als datentragend (nicht mehr archivierbar, Erhebung nicht mehr zurückziehbar). Löschen lässt sie sich über keine Route.
- **Einsicht** (`…/einsicht/…`) zeigt Gesprächsverläufe, Diagnosen, Denkspuren und Fragebogen-Antworten; der **Export** enthält zusätzlich die Teilnahme-Tokens (`teilnahmen.csv`, `itembloecke.csv`, `item_antworten.csv`), mit denen sich Teilnahmen fortsetzen und Abschriften holen lassen. Beides öffnet ein Agent auf Prod nur mit ausdrücklichem Auftrag, lädt den Export nicht ungefragt herunter und schreibt nichts davon in Dateien oder ins Repo.
- Die Detailseite (`/erhebungen/eigene/<pk>/`) zeigt keine Teilnahme-Inhalte: Design, Texte, Stichproben mit Zählern und Teilnahme-Link, dazu die Konten der Eigentümer:innen.

## Rollen

- **Kreis**: die Eigentümer:innen einer Erhebung mit Rolle Forschende:r, dazu die Administration (Superuser), die alle Erhebungen sieht und mit denselben Knöpfen bearbeitet. Ohne Forschungsrolle antworten alle `/erhebungen/eigene/…`-Seiten mit 403 (belegt mit `studi`); fremde Erhebungen sind 404 (laut Code, `sichtbar_fuer`; auf Dev nicht nachgestellt, weil `autor` Superuser ist).
- **Teilnehmer:in**: niemand mit Konto. Wer den Teilnahme-Link öffnet, bekommt ein Token im Cookie `erhebung_teilnahme_tokens` (Pfad `/erhebungen/teilnahme/`). Ein nebenbei angemeldetes Konto spielt keine Rolle.

Auf Dev ist `autor` Superuser: Die Liste `/erhebungen/eigene/` zeigt auch Erhebungen anderer Agenten, und die Auswahlen «Hinzufügen …» bieten alle finalen Vignetten und Items der Instanz an, nicht nur eigene. Eigene Objekte am Namen erkennen (Präfix vergeben) und nur diese anfassen. «Eigentümer:in hinzufügen» ist auf Dev leer, weil alle Forschenden schon im Kreis sind; das Formular hat sonst ein `select[name=konto]` und **Hinzufügen**.

## Seiten

| URL | Wer | Inhalt |
|---|---|---|
| `/erhebungen/eigene/` | Kreis | «Meine Erhebungen»: Name, Zustand, Papierkorb nur bei Entwürfen |
| `/erhebungen/eigene/anlegen/` | Kreis | ein Feld `[name=name]`, Knopf **Erhebung anlegen**; führt auf die Detailseite |
| `/erhebungen/eigene/<pk>/` | Kreis | Detailseite: Lebenszyklus-Knöpfe, Eigentümer:innen, Texte, Vignetten, Fragebogen, Stichproben |
| `/erhebungen/eigene/<pk>/export/` | Kreis | ZIP-Download der Datenspur |
| `/erhebungen/eigene/<pk>/einsicht/` | Kreis | Raster je Stichprobe |
| `…/einsicht/sitzungen/<sitzung_pk>/` | Kreis | eine beendete Sitzung samt Denkspur und Items |
| `…/einsicht/teilnahmen/<teilnahme_pk>/abschluss/` | Kreis | Antworten des Blocks «Am Ende» |
| `/erhebungen/teilnahme/<uuid>/` | alle | Teilnahme-Link; leitet weiter, wohin die Teilnahme gehört |
| `/erhebungen/teilnahme/<uuid>/einwilligung/`, `…/abbruch/`, `…/instruktion/`, `…/abschluss/` | Teilnahme | Einwilligung, Abbruchseite, Instruktion, Abschluss |
| `/erhebungen/teilnahme/token/<token>/gespraech/`, `…/debrief/`, `…/items/` | Teilnahme | Sitzung (siehe [sitzungen.md](sitzungen.md)), Fragebogen «Am Ende» |

Jede schreibende Route nimmt nur POST. Auf Dev erkennt man eine 404 am Seitentitel `Page not found at …`, eine 403 an Chromiums Fehlerseite «HTTP ERROR 403».

## Lebenszyklus

Eine Erhebung ist **Entwurf**, **Final** oder **Archiviert** (Badge im Seitenkopf, `.page-head .badge`). Kein Knopf der Erhebung fragt nach; alles wirkt beim Klick.

- **Anlegen**: Leerer oder nur aus Leerzeichen bestehender Name ergibt «Bitte geben Sie einen Namen ein.» am Feld. Umbenennen geht später nicht.
- **Entwurf löschen**: Papierkorb in der Liste (`getByRole('button', {name: '<Name> löschen'})`), physisch und ohne Rückfrage. Nur Entwürfe.
- **Finalisieren** (Knopf oben): speichert vorher die drei Texte und pinnt die aktive Modell-Konfiguration der Verwendung Schüler:in; die finale Seite zeigt sie unter «Gepinnte Konfiguration» (Anbieter, Sprachmodell, Parameter). Gelingt nur mit Zero-Retention-Erklärung oder Anbieter `fake` (laut Code; auf Dev ist `fake` aktiv). Danach ist das Design gesperrt: Texte, Vignetten und Items nur noch als Leseansicht, der Eigentümer-Kreis bleibt änderbar.
- **Zurückziehen** (nur Final): zurück in den Entwurf. Der Knopf erscheint nur, solange keine Stichprobe nicht-archiviert ist und keine Daten trägt. Erneutes Finalisieren pinnt die dann aktive Konfiguration neu.
- **Erhebung archivieren** / **Erhebung entarchivieren**: nur ohne laufende Stichprobe; Entarchivieren zusätzlich nur mit mindestens einer Eigentümerin (laut Code).
- **Stichprobe anlegen** (nur Final): `[name=beginn]`, `[name=ende]` sind `datetime-local`, Format `2026-10-21T06:00`, Zeitzone Europe/Berlin. Ende vor Beginn ergibt die Meldung «Das Ende darf nicht vor dem Beginn liegen.», die Felder sind danach leer. Die Phase (Geplant, Läuft, Abgeschlossen) folgt allein aus der Uhrzeit.
- **Stichprobe archivieren** (Knopf in der Zeile): nur solange sie datenfrei ist, also bevor jemand ihren Link geöffnet hat. Die Phasenspalte zeigt danach zusätzlich «Archiviert».

Unumkehrbar, auf Prod vor dem Klick als solches zu nennen:

- **Stichprobe anlegen**: Es gibt keine Route zum Löschen oder Ändern von Beginn und Ende. Eine laufende Stichprobe lässt sich nicht vorzeitig beenden, und solange sie läuft, sind weder Zurückziehen noch Archivieren der Erhebung möglich.
- **Teilnahme-Link öffnen** (siehe [Prod](#prod)): macht die Stichprobe dauerhaft datentragend und damit die Erhebung dauerhaft final oder archiviert.
- **Stichprobe archivieren**: keine Route zum Entarchivieren. Aus einer archivierten Stichprobe lässt sich keine Abschrift mehr holen.
- **Entwurf löschen**.
- **Finalisieren** ist umkehrbar, solange keine Stichprobe besteht oder alle archiviert und datenfrei sind; danach nicht mehr.

## Entwurf zusammenstellen

**Texte** (Abschnitt «Konfiguration»): Instruktion, Einwilligung, Abschluss. Alle drei `textarea` stehen immer im Formular `#erhebung-konfiguration`, auch zugeklappt (`[name=instruktionstext]`, `[name=einwilligungstext]`, `[name=abschlusstext]`). Ein Agent setzt sie per `eval` (README, [Formulare füllen](README.md#formulare-füllen)) und klickt **Konfiguration speichern**: das speichert alle drei, ohne vorher **Text schreiben** / **Bearbeiten** zu öffnen (belegt). Zurücklesen über `document.querySelector('[name=…]').value`. Mit ungespeicherten Änderungen warnt die Seite beim Verlassen (laut `verhalten.md`, nicht nachgeprüft); vor einem `goto` also erst speichern.

**Vignetten** (Abschnitt «Vignetten») und **Fragebogen** (Abschnitt «Fragebogen», Listen «Nach jeder Vignettensitzung» und «Am Ende»): je eine Liste mit Auswahl, Positionswahl und **Einfügen**. Aufnehmbar sind nur finale Fassungen; die Erhebung bindet genau die gewählte Fassung. Jede Aktion ist ein eigener POST und gilt sofort; die Seite lädt danach neu.

```bash
playwright-cli -s=dev select "getByRole('combobox', {name: 'Vignettensitzungen: hinzufügen'})" "Variablen als Objektbezeichnungen"
playwright-cli -s=dev select "getByRole('combobox', {name: 'Einfügen an'}).first()" "am Anfang"
playwright-cli -s=dev click "getByRole('button', {name: 'Einfügen'}).first()"
playwright-cli -s=dev select "getByRole('combobox', {name: 'Am Ende: hinzufügen'})" "<Wortlaut des Items>"
playwright-cli -s=dev click "getByRole('button', {name: 'Einfügen'}).nth(2)"
```

Die drei **Einfügen**-Knöpfe und die drei «Einfügen an»-Auswahlen kommen in der Reihenfolge Vignetten, Nach jeder Vignettensitzung, Am Ende. Ein Item, das schon am anderen Andockpunkt hängt, trägt in der Auswahl den Zusatz «(schon nach jeder Sitzung)» bzw. entsprechend. Zeilenknöpfe heißen nach dem Eintrag: `<Name> nach oben`, `<Name> nach unten`, `<Name> entfernen`, bei Items zusätzlich `<Name> nach »Am Ende« umhängen` bzw. `… nach »Nach jeder Vignettensitzung« umhängen`. Den aktuellen Stand liest man ohne Snapshot aus den eingebetteten JSON-Daten (`#aufgenommene-daten`, `#nach-sitzung-aufgenommene-daten`, `#am-ende-aufgenommene-daten`, `#randomisierung-daten`) oder aus `[aria-label=Vignettensitzungen] .zuordnungsliste__text`.

Der Schalter `getByRole('switch', {name: 'Zufällige Reihenfolge'})` speichert sofort (`POST …/reihenfolge/`); `#randomisierung-daten` wechselt zwischen `fest` und `zufällig`, die Listenreihenfolge bleibt beim Zurückschalten erhalten (belegt).

Eine Änderung an einer Erhebung, die kein Entwurf mehr ist (etwa über eine veraltete Seite), ändert nichts und zeigt auf der Detailseite «Die Erhebung ist kein Entwurf mehr. Es wurde nichts geändert.» (belegt).

## Stichproben und Teilnahme-Link

Die Tabelle unter «Stichproben» hat je Stichprobe Zeitraum, Phase, Teilnahmen, Sprachmodelle abgelehnt, Ohne Speicherung, Link (schreibgeschütztes `input`) und Aktion. Den Link liest man aus dem Feld:

```bash
playwright-cli -s=dev --raw eval "[...document.querySelectorAll('table tbody tr input')].map(i => i.value)"
```

Die Zähler lesen sich so (belegt): «Teilnahmen» zählt jeden ersten Link-Aufruf eines Browsers, auch ohne jede Entscheidung, auch die liegen gebliebene Teilnahme nach einem Token-Wiedereinstieg. «Sprachmodelle abgelehnt» und «Ohne Speicherung» überschneiden sich: Wer beides ablehnt, zählt in beiden.

Sobald eine Stichprobe besteht, stehen oben **Datenspur herunterladen** und, sobald es eingewilligte Teilnahmen gibt, **Einsicht**.

## Teilnahme auf Dev durchspielen

Die Teilnahme läuft in einer eigenen, nicht angemeldeten Session neben der Forschenden-Session. Voraussetzung: eine finale Erhebung mit laufender Stichprobe (Beginn in der Vergangenheit, Ende in der Zukunft).

```bash
playwright-cli -s=dev-teilnahme open "<Teilnahme-Link>"
# landet auf …/einwilligung/; Token in der Seitenleiste:
playwright-cli -s=dev-teilnahme --raw eval "document.querySelector('[aria-label=Hauptnavigation]').innerText"
playwright-cli -s=dev-teilnahme check "[name=sprachmodell_eingewilligt][value=ja]"
playwright-cli -s=dev-teilnahme check "[name=speicherung_eingewilligt][value=ja]"
playwright-cli -s=dev-teilnahme click "getByRole('button', {name: 'Weiter'})"   # → …/instruktion/
playwright-cli -s=dev-teilnahme click "getByRole('button', {name: 'Weiter'})"   # → …/token/<token>/gespraech/
```

Einwilligungen sind Radiogruppen `ja`/`nein` ohne Vorauswahl: `sprachmodell_eingewilligt`, `speicherung_eingewilligt` und nur bei transkribierender Instanz `audioverarbeitung_eingewilligt` (auf Dev mit Fake-Transkription nicht angeboten). Sobald Sprachmodelle einmal bejaht sind, stehen alle drei fest.

- **Sprachmodelle `nein`** → `…/abbruch/` «Keine Teilnahme möglich»; der Link «Zur Startseite der Erhebung» führt zurück auf das Einwilligungsformular ohne Vorauswahl, eine neue Entscheidung ersetzt die alte (belegt).
- **Speicherung `nein`** → flüchtige Teilnahme: gleicher Ablauf, die Abschlussseite zeigt statt «Ihre Abschrift» den Abschnitt «Keine Speicherung» (belegt).

Ablauf je Vignette: Gespräch und Debrief wie in [sitzungen.md](sitzungen.md). Nach der Diagnose bleibt die Seite auf `…/debrief/` und zeigt darunter «Fragen zu dieser Sitzung», ein Formular auf `…/token/<token>/items/` mit Feldern `item_<n>` (Likert: Radios `value` 1 bis 6, beschriftet «Stimme gar nicht zu» bis «Stimme voll zu»; Freitext: `textarea`) und **Weiter**. Auch nach «Sitzung abbrechen» erscheint der Block. Ohne Antwort **Weiter** ist «übersprungen». Danach startet die nächste Vignette sofort, nach der letzten folgt `…/items/` «Fragebogen zum Abschluss» und dann `…/abschluss/` mit Abschlusstext und Token.

```bash
playwright-cli -s=dev-teilnahme check "[name=item_1][value='5']"
playwright-cli -s=dev-teilnahme fill "main textarea" "Freitext"
playwright-cli -s=dev-teilnahme click "getByRole('button', {name: 'Weiter'})"
```

`<n>` ist die Zuordnung in der Erhebung, nicht die Item-ID; die Felder liest man mit `[...document.querySelectorAll('main [name^=item_]')].map(e => e.name)`.

**Weitere Teilnahme oder anderer Browser**: `playwright-cli -s=dev-teilnahme cookie-clear`, dann den Link erneut öffnen: Das ergibt eine neue Teilnahme mit neuem Token. Um stattdessen eine bestehende fortzusetzen, auf der Einwilligungsseite `[name=token]` füllen (Schreibweise egal, `6nde 6ras` gilt als `6NDE-6RAS`) und **Hier fortsetzen** klicken; es geht genau dort weiter, wo die Teilnahme stand (belegt bis zum offenen Fragebogen am Ende). Das Anmelden eines Kontos in derselben Session beendet die Zuordnung nicht.

Die Teilnahme-Session ist nicht angemeldet; für Kontentests (Abschrift holen, siehe [training.md](training.md)) meldet man sich dort mit `studi` an.

## Einsicht

`/erhebungen/eigene/<pk>/einsicht/` hat je Stichprobe eine Tabelle: Zeilenkopf ist die Teilnahmekennung (`code`, acht Hexzeichen), eine Spalte je Vignette, dazu «Abschluss». Flüchtige Zeilen tragen «flüchtig, nur Ablaufgerüst», ihre Bubbles sind keine Links. Eine Stichprobe ohne eingewilligte Teilnahmen zeigt «Noch keine Teilnahme mit Einwilligung.». Das Token steht nirgends. Die Links tragen ihren Status im Namen:

```bash
playwright-cli -s=dev --raw eval "[...document.querySelectorAll('main table a')].map(a => a.getAttribute('aria-label') || a.textContent + ' ' + a.title).join('\n')"
playwright-cli -s=dev click "getByRole('link', {name: 'Position 1, Abgeschlossen'})"
```

Linknamen: `Position <k>, Abgeschlossen` / `…, Abgebrochen` auf `…/einsicht/sitzungen/<pk>/`, `Abschluss, beantwortet` auf `…/einsicht/teilnahmen/<pk>/abschluss/`. Die Sitzungsansicht zeigt Kopf (Teilnahme, Stichprobe, Status), Rahmenhandlung, Transkript, je Schritt eingeklappt «Denkspur ansehen», Debrief mit Diagnose und «Fragen zu dieser Sitzung» mit Skalenpol oder Freitext; unten «Zurück zur Einsicht». Sitzungen flüchtiger Teilnahmen antworten mit 404 (belegt).

## Datenspur-Export

**Datenspur herunterladen** (`/erhebungen/eigene/<pk>/export/`) liefert synchron `erhebung-<pk>-<slug-des-namens>-<UTC-Zeitstempel>.zip` mit `erhebung.csv`, `stichproben.csv`, `teilnahmen.csv`, `vignettenziehungen.csv`, `sitzungen.csv`, `gespraechsschritte.csv`, `fehlversuche.csv`, `diagnosen.csv`, `itembloecke.csv`, `item_antworten.csv`, `vignettenfassungen.csv`, `simulationskerne.csv`, `modellkonfigurationen.csv`, `transkriptionskonfigurationen.csv`, `fragebogen_items.csv`, `likert_skala.csv`. Fehlende Werte stehen als `NA`. `teilnahmen.csv` enthält jede Teilnahme, auch abgelehnte und nie entschiedene, mit Token und Kennung.

Auf Dev lädt ein Agent das ZIP mit dem Session-Cookie per `curl`, entpackt es in ein eigenes Verzeichnis unter `/tmp` und löscht es danach:

```bash
sid=$(playwright-cli -s=dev --raw cookie-get sessionid | sed 's/^sessionid=//; s/ .*//')
curl -s -o /tmp/pw/export/e.zip -b "sessionid=$sid" http://127.0.0.1:8000/erhebungen/eigene/<pk>/export/
```

## Nicht nachgeprüft

- 404 für fremde Forschende und für Ausgetretene aus dem Kreis (Dev hat nur den Superuser `autor` als Forschende:n).
- Finalisieren mit nicht erklärter Modell-Konfiguration (Meldung laut Code: «… Eine Administrator:in muss zuerst eine erklärte Konfiguration für die Schüler:in aktivieren.»).
- Archivieren und Entarchivieren einer Erhebung, Phase «Abgeschlossen», Verfall unfertiger Teilnahmen nach dem Fenster.
- Spracherkennung als dritte Einwilligung (braucht eine Transkriptions-Konfiguration mit echtem Anbieter).
- Umsortieren durch Ziehen am Griff; Verschieben mit ↑/↓ und Umhängen mit ⇄ sind vorhanden, aber nicht geklickt.
