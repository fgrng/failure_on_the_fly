# Trainings

Die App `training/` unter `/trainings/`: Trainings anlegen und kuratieren, Beitritt über den Trainings-Link, Austritt, Entfernen und Wiederbeitritt, Fremdeinsicht, Trainingsexport und Abschriften. Setzt [README.md](README.md) voraus (Sessions, Anmelden, Produktion, Formulare, Snapshots). Wie eine einzelne Sitzung läuft (Gespräch, Debrief, Spracheingabe), steht in [sitzungen.md](sitzungen.md); hier steht nur, wie man aus dem Training hineinkommt. Begriffe: `GLOSSARY.md` (Training, Trainings-Link, Austritt, Abschrift, Fremdeinsicht, Trainingsexport); Soll-Verhalten: `docs/verhalten.md`, «Trainings verwalten» bis «Trainingsexport», «Audioverarbeitung im Training», «Abschriften holen».

## Rollen

- **Kreis**: die Eigentümer:innen eines Trainings mit Rolle Ausbilder:in, dazu die Administration (sieht alle Trainings). Kuratiert, sieht Fremdeinsicht, zieht den Export. Der Kreis kommt ohne Beitritt auf die Trainingsseite.
- **Trainingsteilnehmer:in**: jedes Konto mit aktiver Trainingsbindung, entstanden über den Trainings-Link. Ohne Bindung ist ein Training für sie unbekannt (404), auch über die direkte Adresse.

Auf Dev ist `autor` Superuser mit allen Rollen, also Kreis und Administration zugleich: Er sieht jedes Training, auch fremde, und kann darum weder «fremde Ausbilder:in» (404) noch «Eigentümer:in hinzufügen» testen (alle Ausbilder:innen sind schon im Kreis). `studi` hat keine Rolle und ist die Teilnehmer:in. Die Navigation unterscheidet sich danach: `autor` sieht unter «Ausbildung» **Trainings ansehen**, **Neues Training anlegen**, **Meine Abschriften**; `studi` sieht **Training starten** (`/trainings/`), **Meine Trainings** (`/trainings/historie/`), **Meine Abschriften**.

## Seiten

| URL | Wer | Inhalt |
|---|---|---|
| `/trainings/` | alle | «Trainingskataloge»: Kreis sieht eigene Trainings (auch Entwürfe, Link «Kuratieren») und beigetretene; Teilnehmende nur beigetretene |
| `/trainings/eigene/` | Kreis | Liste zum Kuratieren, Überschrift «Meine Trainings»; nicht in der Navigation, Ziel von «Zurück zur Übersicht» |
| `/trainings/anlegen/` | Kreis | ein Feld `[name=name]`, Knopf **Training anlegen** |
| `/trainings/eigene/<pk>/` | Kreis | Kuratierseite: Trainings-Link, Fremdeinsicht, Export, Vignetten, Eigentümer:innen |
| `/trainings/<pk>/` | Teilnehmende, Kreis | Trainingsseite: Vignetten, eigene Sitzungen, Austritt |
| `/trainings/historie/` | alle | «Meine Trainings» der Teilnehmenden: Fortschritt, Sitzungen je Status, Kennzeichen «ausgetreten» |
| `/trainings/beitreten/<uuid>/` | alle | Trainings-Link |
| `/trainings/abschriften/`, `…/abschriften/<pk>/` | alle | Abschriften holen, lesen, freigeben, löschen |

Ohne Rolle Ausbilder:in antworten `/trainings/eigene/…`, `/trainings/anlegen/` und der Export mit 403. Jede schreibende Route nimmt nur POST (GET: 405). Auf Dev läuft `DEBUG`: Eine 404 erkennt man am Seitentitel `Page not found at …`, nicht an einer App-Seite.

## Lebenszyklus

Ein Training ist **Entwurf** oder **Veröffentlicht**; es ist kein versioniertes Artefakt.

- **Anlegen** (`/trainings/anlegen/`) führt auf die Kuratierseite. Den Namen ändert danach keine Route der App mehr.
- **Vignetten**: Abschnitt «03 Finale Vignetten aufnehmen» listet die finalen Vignetten des eigenen Kreises; **Aufnehmen** hängt ans Ende. Abschnitt «02 Vignetten» nummeriert sie (`1. …`) mit **Hoch**, **Runter**, **Entfernen**, im Entwurf wie veröffentlicht, ohne Rückfrage.
- **Veröffentlichen** (Knopf nur im Entwurf) wirkt sofort, ohne Rückfrage. Erst danach funktioniert der Trainings-Link; im Entwurf antwortet er für alle mit 404, auch wenn die Kuratierseite ihn schon zeigt.

Die Knöpfe der Vignetten sind über Zeile und Namen eindeutig:

```bash
playwright-cli -s=dev click "getByRole('row', { name: 'Variablen als Objektbezeichnungen' }).getByRole('button', { name: 'Aufnehmen' })"
playwright-cli -s=dev click "getByRole('button', { name: 'Variablen als Objektbezeichnungen nach oben' })"
```

Ein Training ohne Vignetten lässt sich veröffentlichen und beitreten (laut `verhalten.md`; nicht nachgeprüft).

## Unumkehrbar und auf Prod heikel

Für alles gilt [Produktion](README.md#produktion). Zusätzlich:

- **Veröffentlichen** ist unumkehrbar: Kein Weg führt zurück in den Entwurf, und es gibt keine Route zum Löschen eines Trainings. Ein angelegtes Training bleibt also im Katalog des Kreises.
- **Entfernen** einer Teilnehmer:in, **Sperren** des Beitritts, **Vignette entfernen** und **Hoch/Runter** treffen sofort echte Teilnehmende: Die Reihenfolge sehen sie sofort, eine entfernte Vignette verschwindet von ihrer Trainingsseite. Entfernen und Sperren sind umkehrbar (Wiederbeitritt, **Wieder öffnen**), aber für die Betroffene sichtbar.
- **Eigentümer:in entfernen**, besonders **Mich entfernen**: Wer sich selbst entfernt, verliert den Zugang zum Training.
- Jeder **Sitzungsstart** auf Prod ruft ein echtes Sprachmodell; README verbietet ihn dort. Auch ein Kreis-Konto bekommt beim Start eine Trainingsbindung und steht danach als Teilnehmer:in in der eigenen Fremdeinsicht.
- **Abschrift löschen** und **Austritt bestätigen** betreffen das eigene Konto; Löschen ist endgültig und hat keine Rückfrage.

## Trainings-Link und Beitritt

Die Kuratierseite zeigt oben das Band «Gruppe beitreten lassen» mit dem Link als schreibgeschütztes Feld, **Kopieren**, **Sperren** und darunter «N Person(en) beigetreten». Den Link liest man aus dem Feld, nicht aus der Zwischenablage:

```bash
playwright-cli -s=dev --raw eval "document.querySelector('[aria-label=Trainings-Link]').value"
```

- Konto ohne Kreiszugang öffnet den Link: tritt bei und landet auf `/trainings/<pk>/`. Wiederholtes Öffnen tritt nicht erneut bei.
- Kreis und Administration öffnen den Link: landen auf der Trainingsseite **ohne** Beitritt; die Zahl bleibt gleich.
- **Sperren**: Das Band heißt «Beitritt gesperrt», Knopf **Wieder öffnen**. Neue und Ausgetretene sehen die Seite «Beitritt gesperrt» (403, Titel `Beitritt gesperrt`); wer aktiv dabei ist, kommt weiter hinein.
- Der Link ist ein Zugangsweg für jedes Konto: Den Prod-Link nicht ins Repo oder in Dateien schreiben.

## Vom Training in eine Sitzung

Auf der Trainingsseite trägt jede Vignettenzeile **Neu starten** → `/trainings/<pk>/vignetten/<vignette_pk>/` («Vignette gewählt») → **Training starten** (POST). Die Sitzung erscheint als Antwort auf diesen POST, die Adresse bleibt die der Wahl. Die Sitzungsnummer steht in den Formularzielen:

```bash
playwright-cli -s=dev-studi --raw eval "[...document.querySelectorAll('form')].map(f=>f.getAttribute('action')).join(' ')"
# /trainings/sitzung/<id>/gespraech/ /trainings/sitzung/<id>/abbrechen/ /trainings/sitzung/<id>/gespraech/beenden/
```

Weiter in [sitzungen.md](sitzungen.md). Nach **Diagnose abgeben** führt die App zurück auf `/trainings/<pk>/`. Dort zeigt die Spalte «Ihre Sitzungen» je Status einen aufklappbaren Zähler («1 abgeschlossen ▾»); laufende tragen **Fortsetzen** (`/trainings/sitzung/<id>/gespraech/`), alle **Sitzung #<id> ansehen** (`/trainings/sitzung/<id>/ansehen/`, lesend).

- Je Training läuft höchstens eine Sitzung: Ein zweiter Start zeigt «Es läuft noch eine Sitzung» (409) mit **Fortsetzen**, **Abbrechen und neu starten**, **Zurück zum Training**.
- **Audioverarbeitung**: Ist das Transkriptions-Tor offen (aktive Transkriptions-Fassung erklärt und nicht `fake`), kommt vor dem ersten Start die Seite «Audioverarbeitung» mit **Einwilligen und Training starten** / **Ohne Audio fortfahren**; die Entscheidung gilt einmal je Teilnahme und lässt sich nicht ändern. Mit dem Seed (Fake-Transkription) startet die Sitzung direkt, die Seite ist auf Dev nicht zu sehen.

## Austritt, Entfernen, Wiederbeitritt

- **Austritt** (Teilnehmer:in): Am Ende der Trainingsseite «Austritt aus dem Training» → **Aus dem Training austreten** (`<details>`, klappt die Erklärung auf) → **Austritt bestätigen**. Danach: Meldung «Sie sind aus dem Training „…“ ausgetreten.», Trainingsseite nur lesend («Sie sind nicht mehr Teilnehmer:in dieses Trainings.»), kein **Neu starten**, nicht mehr im Katalog, in «Meine Trainings» als ausgetreten. Wahl und Sitzungsadressen antworten mit 404, die Sitzungsansicht `…/ansehen/` bleibt für sie lesbar.
- **Entfernen** (Kreis): In der Fremdeinsicht klappt **Entfernen** (letzte Spalte, `<details>`) die Bestätigung auf; **Entfernen bestätigen** führt mit «<Name> ist aus dem Training entfernt.» zurück. Für die Person derselbe Zustand wie nach dem Austritt. `getByText('Entfernen')` trifft in der Zeile zwei Elemente (Knopf und Erklärtext) und scheitert; den `summary` anklicken:

  ```bash
  playwright-cli -s=dev click "getByRole('row', { name: /studi/ }).locator('summary')"
  playwright-cli -s=dev click "getByRole('button', { name: 'Entfernen bestätigen' })"
  ```

- Für den Kreis verschwindet die Person sofort rückwirkend: keine Zeile, nicht gezählt, ihre Sitzungen 404, nicht im Export; ihre Abschrift-Freigaben ruhen.
- **Wiederbeitritt**: Die Person öffnet den Link erneut (nur bei offenem Beitritt). Dieselbe Bindung lebt auf: alte Sitzungen wieder in der Fremdeinsicht, ruhende Freigaben wieder wirksam, eine liegengebliebene laufende Sitzung wieder fortsetzbar.

## Fremdeinsicht und Export

Abschnitt «01 Fremdeinsicht» der Kuratierseite: Tabelle mit den aktiven Teilnehmenden als Zeilen (Name = voller Name, sonst Benutzername) und den Vignetten als Spalten. Jede **abgeschlossene** Sitzung ist ein nummerierter Kreis, ein Link auf `/trainings/sitzung/<id>/ansehen/`; laufende, abgebrochene und gescheiterte fehlen. Die Adressen liest man direkt:

```bash
playwright-cli -s=dev --raw eval "[...document.querySelectorAll('.fremdeinsicht__sitzung')].map(a=>a.getAttribute('href')+' '+a.dataset.datum).join(' ')"
```

Die lesende Ansicht zeigt Transkript und Diagnose, nie die Denkspur und kein Formular. Darunter «Freigegebene Abschriften» (Teilnehmer:in, Erhebung, Geholt am, Sitzungen).

**Trainingsexport (ZIP)** (`/trainings/eigene/<pk>/export/`) lädt `training-<pk>-<name>-<UTC>.zip`. Ein Download über den Browser landet nicht im Shell-Verzeichnis; im Kontext der Seite holen und dekodieren:

```bash
playwright-cli -s=dev --raw eval "(async()=>{const r=await fetch('/trainings/eigene/3/export/');const b=new Uint8Array(await r.arrayBuffer());let s='';b.forEach(x=>s+=String.fromCharCode(x));return btoa(s)})()" | jq -r . | base64 -d > /tmp/pw/export.zip
unzip -l /tmp/pw/export.zip
```

Inhalt: je Person `teilnehmer-<kennung>/NN-<vignette>.md` (Vignettenname, Ausgang, Datum, Transkript, Diagnose), freigegebene Abschriften als Unterordner `<erhebungsname>/`. Pseudonym, aber nicht anonym: Freitext bleibt ungeschwärzt.

## Zwei Sessions: Beitritt und Fremdeinsicht testen

Kreis in `dev`, Teilnehmer:in in `dev-studi` (Anmeldung wie in README, `studi`/`entwicklung`). Ablauf, auf Dev belegt:

1. `dev`: Training anlegen, eine Vignette aufnehmen, veröffentlichen, Link aus dem Feld lesen.
2. `dev-studi`: `/trainings/<pk>/` → 404; Link öffnen → Trainingsseite; eine Vignette starten, eine Frage senden, **Gespräch beenden**, Diagnose abgeben.
3. `dev`: Kuratierseite neu laden → «1 Person beigetreten», Zeile `studi` mit Kreis «1»; Sitzung öffnen; Export ziehen.
4. Austritt oder Entfernen, dann in `dev` prüfen (Zeile weg, Sitzung 404), Link erneut öffnen, wieder prüfen.

Zum Prüfen von Zugriffsregeln ohne Navigieren: Statuscodes per `fetch` aus der jeweiligen Session.

```bash
playwright-cli -s=dev-studi --raw eval "Promise.all(['/trainings/eigene/3/','/trainings/3/'].map(u=>fetch(u).then(r=>u+' '+r.status))).then(a=>a.join(' | '))"
```

Der Seed hat schon ein veröffentlichtes Training «Diagnose-Grundlagen»; für Tests ein eigenes anlegen, damit Zahlen und Zeilen nicht mit anderer Arbeit kollidieren.

## Abschriften

`/trainings/abschriften/`: Feld `[name=token]` (Teilnahme-Token, Groß-/Kleinschreibung und Leerraum egal), **Abschrift holen**. Ein unbrauchbares Token gibt immer dieselbe Meldung «Zu diesem Teilnahme-Token lässt sich keine Abschrift holen.». Holbar ist nur eine abgeschlossene Erhebungsteilnahme; ein Token entsteht auf Dev, indem man selbst an einer Erhebung teilnimmt (siehe [erhebungen.md](erhebungen.md)), die Abschlussseite zeigt es.

Die Abschrift-Seite (`/trainings/abschriften/<pk>/`) zeigt die Sitzungen lesend, dann «Freigabe»: Checkboxen `[name=training]` mit dem Training-pk als Wert, nur für aktiv beigetretene Trainings, Knopf **Freigaben speichern**. Nach einem Austritt steht die Freigabe unter «Ruhende Freigaben» mit **Freigabe widerrufen**. **Abschrift löschen** löscht sofort, ohne Rückfrage, samt Freigaben.

```bash
playwright-cli -s=dev-studi check "[name=training][value='3']"
playwright-cli -s=dev-studi click "getByRole('button', { name: 'Freigaben speichern' })"
```

## Personenbezogene Daten

- Fremdeinsicht und «Freigegebene Abschriften»: Namen der Teilnehmenden, verknüpft mit ihren Gesprächen und Diagnosen.
- Sitzungsansichten, Abschriften und der Trainingsexport: Freitext der Teilnehmenden (Fragen, Diagnosen), ungeschwärzt; der Export trägt keine Namen, aber Kennungen, die über Exporte desselben Trainings gleich bleiben.
- Eigentümer:innen-Abschnitt und Auswahl «Eigentümer:in hinzufügen»: Kontonamen.

Auf Prod liest ein Agent diese Stellen nur, wenn die Aufgabe es verlangt; Exporte und Screenshots davon bleiben unter `/tmp` und werden danach gelöscht.

## Belegt und offen

Auf Dev durchgespielt (2026-10-21): Anlegen, Aufnehmen, Hoch, Veröffentlichen, Link im Entwurf 404, Beitritt, Kreis über den Link ohne Beitritt, Sitzung starten und abschließen, «Es läuft noch eine Sitzung», Fremdeinsicht und lesende Ansicht ohne Denkspur, Export (auch mit Abschrift-Unterordner), Sperren mit Zugang für Aktive und 403 für Ausgetretene, Austritt, Entfernen, Wiederbeitritt mit Fortsetzen, Abschrift holen, freigeben, ruhen lassen, löschen, Statuscodes 403/405.

Nicht nachgeprüft, nur aus Code und `verhalten.md`: Einwilligungsseite zur Audioverarbeitung (braucht eine echte Transkriptions-Konfiguration), Eigentümer:in hinzufügen und entfernen, 404 für fremde Ausbilder:innen, Rollenentzug, Training ohne Vignetten veröffentlichen, **Runter**, **Freigabe widerrufen**.
