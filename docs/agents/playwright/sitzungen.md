# Sitzungen

Eine Sitzung als Teilnehmer:in durchlaufen: Rahmenhandlung, Diagnosegespräch, Debrief mit Diagnose, Fortsetzen; dazu der Probelauf. Setzt [README.md](README.md) voraus (Sessions, Anmelden, Prod-Regeln, Snapshots). Begriffe in `GLOSSARY.md` (Abschnitt «Sitzung einer Vignette»), erwartetes Verhalten in `docs/verhalten.md` («Trainingssitzung fortsetzen», «Audioverarbeitung im Training», «Erhebungsteilnahme»).

## Prod

Auf <https://onthefly.fgrng.de/> startet ein Agent weder Sitzung noch Probelauf und sendet keinen Gesprächsschritt: jeder Schritt ruft das echte Sprachmodell, und Trainings- und Erhebungssitzungen sind Daten echter Teilnehmer:innen. Erlaubt ist Lesen, etwa eine eigene Sitzung über `/trainings/sitzung/<pk>/ansehen/` öffnen; Gesprächsverläufe und Diagnosen anderer gehören nicht in Dateien. Alles Folgende ist für Dev (<http://127.0.0.1:8000/>, Fake-Sprachmodell aus dem Seed).

## Wo Sitzungen laufen

Die App `sitzungen/` hat eigene URLs nur für den Probelauf; Trainings- und Erhebungssitzungen rendern dieselbe Sitzungsseite (`sitzungen/sitzung.html`) unter den URLs ihres Anlasses. Wie man hineinkommt, steht in [training.md](training.md) (Beitritt, Vignette wählen, Einwilligung) und [erhebungen.md](erhebungen.md) (Teilnahme-Link, Einwilligungen, Token).

| Anlass | Gespräch (GET zeigt, POST sendet Schritt) | Beenden | Debrief (POST Diagnose) | Abbrechen |
|---|---|---|---|---|
| Training | `/trainings/sitzung/<pk>/gespraech/` | `…/gespraech/beenden/` | `/trainings/sitzung/<pk>/debrief/` | `/trainings/sitzung/<pk>/abbrechen/` |
| Erhebung | `/erhebungen/teilnahme/token/<token>/gespraech/` | `…/gespraech/beenden/` | `…/<token>/debrief/` | `…/<token>/abbrechen/` |
| Probelauf | `/sitzungen/probelauf/gespraech/` | `/sitzungen/probelauf/beenden/` | `/sitzungen/probelauf/debrief/` | gibt es nicht |

Der Start ist ein POST, der die Sitzungsseite direkt rendert, ohne Weiterleitung: Die Adresszeile bleibt auf der Startadresse (Training `/trainings/<t>/vignetten/<v>/`, Probelauf `/sitzungen/probelauf/<vignette_pk>/starten/`). Die Sitzungs-pk liest man aus dem Formular, nicht aus `location`:

```bash
playwright-cli -s=dev --raw eval "document.querySelector('#gespraechseingabe-formular').getAttribute('action')"
# "/trainings/sitzung/2/gespraech/"
```

Danach immer über `goto …/gespraech/` weiterarbeiten, nicht über `reload`: ein Neuladen der Startadresse wiederholt den Start-POST.

## Aufbau der Seite

Eine Seite, von oben nach unten; der Titel ist der Anlass (`Training`, `Probelauf`):

- `section.rahmenhandlung`: Kopf «Die Ausgangslage», Illustration `img.sitzung-illustration`, Hospitationseinleitung `.rahmenhandlung__text`, Lernauftrag in `.aufgabenkontext`.
- `#sitzung-fortsetzung`: der Teil, den HTMX austauscht. Darin `#diagnosegespraech` mit Illustration, Gesprächseinleitung `.gespraechseinleitung__text`, Arbeitsheft `.aufgabenkontext--arbeitsheft`, Verlauf `.diagnosegespraech-verlauf`, Eingabe `#gespraechseingabe-formular` und Aktionszeile `.sitzung-aktionen`; nach dem Beenden zusätzlich `#sitzung-debrief`, bei Erhebungen darunter der Fragebogen `#sitzung-anhang`.

Lernauftrag und Arbeitsheft bestehen je aus Text vor dem Bild, Bild `img.aufgabenkontext-bild` (aus `/media/vignettenbilder/`, Bildbeschreibung als `alt`) und Text nach dem Bild. Der Inhalt eines Bildes steht nur im `alt`, nicht im Text: für den Inhalt `alt` lesen, für die Darstellung Screenshot.

Die drei Illustrationen sind statisch und hängen am Geschlecht in der Vignette: `/static/images/sitzung/rahmenhandlung-einstieg-<m|w>.webp` und `rahmenhandlung-debrief-<m|w>.webp` nach der Lehrperson, `gespraechsanlass-<m|w>.webp` nach der Schüler:in.

## Gesprächsschritt senden und warten

Synchron über HTMX, kein Streaming, kein Polling: Das Formular postet `eingabe` und `eingabemodus`, der Server ruft das Modell im selben Request und antwortet mit dem neuen Inhalt von `#sitzung-fortsetzung`. `click` kehrt zurück, bevor die Antwort da ist. Während der Anfrage tragen Formular und Knöpfe `htmx-request`, Senden, Spracheingabe, «Gespräch beenden» und «Sitzung abbrechen» sind gesperrt, das Feld ist schreibgeschützt.

Zuverlässig warten: Schrittzahl vorher merken (ein HTMX-Tausch lässt `window` stehen), senden, dann auf einen der vier Ausgänge warten — neuer Schritt, Modellfehler, Budget erschöpft (Debrief), Anfragefehler:

```bash
playwright-cli -s=dev --raw eval "window.__n = document.querySelectorAll('.gespraechsschritt').length"
playwright-cli -s=dev fill "#eingabe" "Wie bist du auf die 12 gekommen?"
playwright-cli -s=dev click ".gespraechseingabe__senden"
playwright-cli -s=dev --raw run-code "async page => { await page.waitForFunction(() => document.querySelectorAll('.gespraechsschritt').length > window.__n || document.querySelector('.gespraechseingabe--fehler, #sitzung-debrief') || !document.getElementById('anfragefehler').hidden, null, {timeout: 120000}); return 'fertig'; }"
```

Mit dem Fake-Modell kommt die Antwort sofort; mit einem echten Modell dauert ein Schritt Sekunden bis über eine Minute, daher das großzügige Timeout. Was danach vorliegt:

- neuer `.gespraechsschritt`: Der letzte trägt `#gespraechsschritt-neu` und hat den Fokus.
- `.gespraechseingabe--fehler`: «Die Antwort konnte nicht erzeugt werden.» Im Probelauf mit Knopf «Erneut senden» (schickt dieselbe Eingabe noch einmal); in Training und Erhebung ist die Sitzung damit gescheitert. Auf Dev nicht nachgestellt.
- `#sitzung-debrief` ohne Klick auf Beenden: Das Gesprächsbudget ist erschöpft. Das Budget zeigt die UI nie an. Auf Dev nicht nachgestellt.
- `#anfragefehler` sichtbar: Die Anfrage kam nicht an (Netz, 4xx/5xx); Text bleibt im Feld, erneut senden.

## Verlauf auslesen

Per `eval` statt Snapshot, als JSON:

```bash
playwright-cli -s=dev --raw eval "JSON.stringify([...document.querySelectorAll('.gespraechsschritt')].map(s => ({frage: s.querySelector('.gespraechsschritt__eingabe p')?.innerText, antwort: s.querySelector('.gespraechsschritt__aeusserung p')?.innerText ?? null, denkspur: s.querySelector('.denkspur p')?.textContent ?? null})))"
```

`antwort: null` heißt: Schritt ohne Antwort, der Antwortversuch ist endgültig gescheitert. Die Denkspur (`details.denkspur`, «Denkspur ansehen») gibt es im Probelauf und in der Einsicht in Erhebungen (siehe [erhebungen.md](erhebungen.md)); `textContent` liest sie auch zugeklappt. Training, Teilnahme an einer Erhebung und die Fremdeinsicht im Training zeigen sie nie.

## Beenden, Debrief, Diagnose

- **«Gespräch beenden →»** (`.sitzung-aktionen__beenden`) ist ein HTMX-POST ohne Rückfrage: `#sitzung-debrief` erscheint unter dem Verlauf, Fokus auf «Ihre Diagnose», die Adresse bleibt. Warten mit `run-code "async page => { await page.waitForSelector('#sitzung-debrief'); return 'ok'; }"`.
- Die Sitzung läuft danach weiter, bis die Diagnose abgegeben ist: Im Training zeigt ein `goto` oder Neuladen von `…/gespraech/` wieder das Gespräch mit Eingabefeld statt des Debriefs, der Debrief kommt mit erneutem Beenden zurück. Im Probelauf zeigt `/sitzungen/probelauf/gespraech/` nach dem Beenden den Debrief.
- **Diagnose:** `#diagnose` füllen, `#diagnose-formular button[type=submit]` («Diagnose abgeben») klicken. Das ist ein normaler POST ohne HTMX, einmalig und unumkehrbar. Training: Sitzung `abgeschlossen`, Weiterleitung auf `/trainings/<t>/`. Probelauf: Diagnose und Verlauf werden verworfen, Weiterleitung auf `/vignetten/<pk>/` (vom Admin-Auswähler zurück auf diesen). Erhebung: Fragebogen der Sitzung oder nächste Stelle, siehe [erhebungen.md](erhebungen.md).
- **«Sitzung abbrechen»** (`.sitzung-aktionen__abbrechen button`, nur Training und Erhebung) verwirft die Sitzung ohne Diagnose und ohne Rückfrage, Status `abgebrochen`, unumkehrbar.

Ein Probelauf ist nach der Diagnose weg: `/sitzungen/probelauf/gespraech/` antwortet dann 404 «Kein laufender Probelauf.».

## Fortsetzen und Einsicht

Trainingssitzungen hängen an ihrer Adresse, nicht am Browser. Auf `/trainings/<t>/` trägt eine laufende Sitzung die Links «Fortsetzen» (`/trainings/sitzung/<pk>/gespraech/`) und «Sitzung #<pk> ansehen» (`/trainings/sitzung/<pk>/ansehen/`). `goto` auf die Gesprächsadresse setzt mit dem bisherigen Verlauf fort; bei einer abgeschlossenen zeigt sie den Debrief mit schreibgeschütztem `#diagnose`. Die Ansehen-Seite ist lesend: ohne Eingabe, Diagnose als `.sitzung-debrief__diagnose`. Wer im selben Training eine zweite Vignette startet, landet auf «Es läuft noch eine Sitzung» (siehe [training.md](training.md)).

Der Probelauf hängt an Browser und Konto (Cookie unter `/sitzungen/probelauf/`, ein Tag ab letztem Zugriff, Abmelden löscht ihn); `goto /sitzungen/probelauf/gespraech/` setzt ihn fort.

## Probelauf

Für Autor:innen über **Probelauf starten** auf `/vignetten/<pk>/` (Entwurf oder finale Fassung) oder die Liste `/sitzungen/probelauf/` (Formulare `POST /sitzungen/probelauf/<pk>/starten/`, in der Navigation nicht verlinkt). Er nimmt den an der Vignette gepinnten Kern und die aktive Modell-Konfiguration für die Schüler:in. Administrator:innen kombinieren frei auf `/sitzungen/probelauf/administratorin/`: Selects `[name=kern_pk]`, `[name=modell_konfiguration_pk]`, `[name=vignette_pk]`, dann «Probelauf starten». Nichts wird gespeichert; Kopf «Probelauf · Rahmenhandlung», Denkspur sichtbar, kein Abbrechen, keine Einwilligung.

## Spracheingabe

Ohne Freigabe steht statt des Mikrofons «Spracheingabe nicht freigegeben. Sie nutzen die Tastatur.» (`.spracheingabe__status`); so auf Dev mit dem Seed. Mit Freigabe `button.spracheingabe__steuerung` («Spracheingabe starten»); die Aufnahme geht an `…/transkription/`. Ein Agent bedient sie nicht, sondern tippt. Unbelegt auf Dev.

## Aussehen prüfen

Element-Screenshots halten den Abschnitt ohne Navigation; vorher die Fenstergröße setzen (README):

```bash
playwright-cli -s=dev resize 1280 800
playwright-cli -s=dev screenshot ".rahmenhandlung" --filename=/tmp/pw/rahmenhandlung.png
playwright-cli -s=dev screenshot "#diagnosegespraech" --filename=/tmp/pw/gespraech.png
playwright-cli -s=dev screenshot "#sitzung-debrief" --filename=/tmp/pw/debrief.png
playwright-cli -s=dev resize 390 844
playwright-cli -s=dev screenshot "#diagnosegespraech" --filename=/tmp/pw/gespraech-telefon.png
```

- `--full-page` zeigt die Illustration des Diagnosegesprächs (`loading="lazy"`) als leere Fläche, obwohl sie geladen ist; der Element-Screenshot zeigt sie. Für Illustrationen daher Element-Screenshots.
- Die Sitzungsspalte ist auch bei 1280 px nur rund 420 px breit (`.sitzung-seite`: `grid-column: 3 / span 4`, volle Breite erst unter 1050 px). Die Aktionszeile bricht dort schon um: «Sitzung abbrechen» rechts oben, darunter der Erklärsatz, darunter «Gespräch beenden →».
- Eigene Fragen stehen rechts in hellgrünen Blasen («Sie»), Antworten links in dunkelgrünen («Schüler:in»).
- Zum Prüfen einer abgeschlossenen Sitzung ohne neuen Lauf eignet sich `/trainings/sitzung/<pk>/ansehen/`: Rahmenhandlung, Verlauf und Debrief stehen dort vollständig.
