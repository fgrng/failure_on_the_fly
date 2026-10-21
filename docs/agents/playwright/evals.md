# Evalläufe

Ein Evallauf spielt alle Evals des finalen Evalkatalogs über einer Vignettenfassung durch und lässt jedes Evalgespräch vom Bewerter beurteilen. Diese Datei setzt [README.md](README.md) voraus (Sessions, Anmelden, Produktion, Snapshots). Den Evalkatalog selbst und die Modell-Konfigurationen pflegt man unter `/system/`, siehe [simulation.md](simulation.md). Das erwartete Verhalten steht in `docs/verhalten.md`, Abschnitt «Evalläufe».

## Produktion

Auf <https://onthefly.fgrng.de/> ruft jeder Evallauf drei echte Sprachmodelle (Schüler:in, Lehrperson, Bewerter) für jedes Eval × Evalinput × *k* Wiederholungen und kostet Geld. Ein Agent startet dort keinen Lauf (**Evallauf starten**, **Erneut prüfen**) ohne ausdrückliche Bitte des Users, auch nicht zum Ausprobieren. Ansehen und Auslesen sind lesend. Ein Urteil korrigieren oder eine Korrektur zurücknehmen ist Schreiben und braucht die Freigabe des einzelnen Schritts.

Unumkehrbar:

- **Erneut prüfen** löscht den bisherigen Lauf samt Gesprächen, Urteilen und manuellen Korrekturen sofort beim Klick, nicht erst, wenn der neue Lauf fertig ist; auf die neuen Urteile wird nichts übertragen.
- **Korrektur ändern** ersetzt Begründung, Konto und Zeitpunkt der Korrektur ohne Historie.
- Ein gestarteter Lauf lässt sich in der UI nicht abbrechen; die Modellaufrufe laufen bis zum Ende.

## Wo und wann

Die Ansicht ist `/evals/vignette/<pk>/`, `<pk>` ist die Fassung (dieselbe Zahl wie in `/vignetten/<pk>/`). Die Vignettendetailseite nennt den Zustand in einer Zeile «Evallauf: noch keiner · Evals ansehen» (Selektor `.vignette-detail-kern`); an einem Entwurf steht zusätzlich ein Hinweis bei **Finalisieren** mit demselben Link.

Evals gibt es nur, wenn ein Evalkatalog final ist und Schüler:in, Lehrperson und Bewerter je eine aktive Modell-Konfiguration haben. Fehlt etwas, fehlt der Link ohne Hinweis und alle `/evals/…`-Routen geben 404: ein 404 heißt also zuerst «Evals nicht verfügbar», nicht «falsche Fassung». Prüfen ohne UI-Suche:

```bash
playwright-cli -s=dev --raw eval "fetch('/evals/vignette/1/').then(r => r.status)"
```

Zugang haben Konten mit Autor:innen-Rolle im Eigentümer-Kreis der Vignette und die Administration; fremde Fassungen geben 404, Konten ohne Autor:innen-Rolle 403. Archivierte Fassungen sind lesbar, aber weder startbar noch korrigierbar (aus dem Code, auf Dev nicht nachgeprüft).

## Dev vorbereiten

Der Seed (`entwicklungsdaten_anlegen`) aktiviert das Fake-Sprachmodell nur für die Schüler:in und legt keinen Evalkatalog an: Auf einem frisch geseedeten Dev-Server sind Evals nicht verfügbar. Nötig sind zwei weitere Fake-Konfigurationen, deren Skript zum Ausgabeschema der Rolle passt (Lehrperson `{"aeusserung"}`, Bewerter `{"begruendung", "erfuellt"}`; das Schüler:innen-Skript des Seeds taugt dafür nicht), und ein finaler Katalog. In der UI geht das unter `/system/` (siehe [simulation.md](simulation.md)); schneller per Shell mit denselben Umgebungsvariablen wie der Server:

```bash
uv run python manage.py shell -c "
from simulation.models import *
lp = ModellKonfiguration.objects.create(bezeichnung='Offline Lehrperson (fake)', anbieter='fake', sprachmodell='fake', parameter={'skript': [{'aeusserung': 'Wie bist du auf deine Zahl gekommen?'}]})
bw = ModellKonfiguration.objects.create(bezeichnung='Offline Bewerter (fake)', anbieter='fake', sprachmodell='fake', parameter={'skript': [{'begruendung': 'Fake-Bewerter.', 'erfuellt': False}]})
ModellKonfiguration.objects.aktivieren(lp, Verwendung.LEHRPERSON)
ModellKonfiguration.objects.aktivieren(bw, Verwendung.BEWERTER)
k = Evalkatalog.objects.anlegen(); k.k = 2
k.lehrperson_vorlage = 'Du bist Lehrperson. Strategie: \$inputstrategie'
k.bewerter_vorlage = 'Beurteile nach \$kriterium den Verlauf: \$verlauf'
k.save(); k.kriterium_anlegen('Die Schülerin bleibt in ihrer Rolle.')
e = k.eval_anlegen('Vorgehen erfragen'); e.kriterium_anlegen('Die Schülerin beschreibt ihr Vorgehen.')
i = e.input_anlegen()
for s in i.schritte.all(): s.delete()
i.schritt_anlegen(text='Erklär mir, wie du gerechnet hast.')
i.schritt_anlegen(Inputschritt.Art.GELENKT, 'Frage nach dem Gleichheitszeichen.')
k.finalisieren(); print(evals_verfuegbar())"
```

`input_anlegen()` legt drei leere feste Schritte an, an denen `finalisieren()` scheitert; daher die Schleife mit `delete()`. Der Katalog ist instanzweit einer (`anlegen()` gelingt nur einmal): Gibt es schon einen, nicht einen zweiten anlegen, sondern den vorhandenen benutzen. Der Fake-Bewerter urteilt immer gleich, mit `'erfuellt': False` gibt es etwas zu korrigieren.

## Starten und auf das Ende warten

**Evallauf starten** (`form[action$='/starten/'] button`, POST) steht oben, solange es keinen Lauf gibt; nach einem fertigen oder abgebrochenen Lauf heißt derselbe Knopf **Erneut prüfen** und steht in der Fußzeile (`.evallauf-fuss`). Danach steht der Lauf auf «Wartet», der Knopf ist durch **Stand neu laden** ersetzt. Eine abgewiesene Startprüfung (etwa «Für diese Fassung wartet oder läuft bereits ein Evallauf.») erscheint als Meldung in `.messages`.

Der Webserver führt keinen Lauf aus: Das tut der Hintergrundprozess `manage.py evallaeufe_abarbeiten`, auf Prod ein eigener supervisord-Dienst. Auf Dev läuft er nicht mit `runserver` mit; ohne ihn bleibt ein Lauf für immer «Wartet». Ein Agent arbeitet den Lauf auf Dev selbst ab, im Wegwerf-Fall mit denselben Variablen (`DATABASE_PFAD`, `MEDIA_ROOT`, `FLUECHTIG_PFAD`, `EVALLAEUFE_SPERRE`) wie der Server:

```bash
uv run python manage.py evallaeufe_abarbeiten --einmal
```

`--einmal` nimmt den ältesten wartenden Lauf der Instanz, der auch einer anderen Session gehören kann. Mit Fake-Modell dauert ein kleiner Katalog unter einer Sekunde, das Log auf stderr meldet «Evallauf <n> gestartet.» und «… fertig.». Läuft schon ein Prozess mit derselben Sperrdatei, meldet der zweite das und tut nichts. Auf Prod startet ein Agent den Prozess nie selbst.

Die Seite aktualisiert sich nicht von selbst. Warten heißt neu laden und den Zustand lesen, bis er nicht mehr «Wartet» oder «Läuft» ist:

```bash
playwright-cli -s=dev reload
playwright-cli -s=dev --raw eval "document.querySelector('.evallauf-zeile').innerText"
```

Ergebnis etwa `Evallauf\nFertig · Nicht bestanden\n21.10.2026 07:25 · 2 Wiederholungen je Evalinput\n\nErneut prüfen`. Mögliche Zustände: «Noch nicht geprüft», «Wartet», «Läuft», «Fertig · Bestanden», «Fertig · Nicht bestanden», «Abgebrochen», jeweils ggf. mit «· manuell korrigiert», «· Unvollständig», «· Veraltet» (die letzten drei Zusätze und «Abgebrochen» auf Dev nicht nachgeprüft). Die eingeklappten **Angaben zum Lauf** (`.evallauf-angaben`) nennen Zeitpunkte, *k*, Kern, Katalogfassung und die drei Konfigurationen.

## Ergebnisse auslesen

Die Seite ist lang (je Wechsel Denkspur, je Urteil ein Formular). Statt des Snapshots per `eval` reduzieren:

```bash
# Übersicht links: je Evalinput Link und Quote je Kriterium
playwright-cli -s=dev --raw eval "[...document.querySelectorAll('.evallauf-inputs li a')].map(a => a.getAttribute('href') + ' | ' + a.innerText.replace(/\s+/g, ' '))"
# Verlauf des gewählten Gesprächs
playwright-cli -s=dev --raw eval "[...document.querySelectorAll('.evallauf-verlauf > li')].map(li => li.querySelector('strong').innerText + ': ' + li.querySelector('p')?.innerText)"
# Urteile des gewählten Gesprächs samt Korrektur-Adresse
playwright-cli -s=dev --raw eval "[...document.querySelectorAll('.evallauf-urteile > li')].map(li => ({titel: li.querySelector('strong').innerText, begruendung: li.querySelector(':scope > p')?.innerText, korrigieren: li.querySelector('form')?.getAttribute('action')}))"
```

Eine Übersichtszeile lautet etwa `/evals/vignette/1/?input=1 | Evalinput 1 FG Die Schülerin beschreibt ihr Vorgehen. 0 von 2 · nicht bestanden …`: das Kriterium steht mit seinem vollen Text, «FG» ist die Folge fester und gelenkter Schritte. Ein Urteilstitel lautet `<Kriteriumstext> · nicht erfüllt`. Das Gespräch wählt man per Adresse, `?input=<Evalinput-pk>&wiederholung=<1…k>`; ohne Parameter zeigt die Seite den ersten Evalinput und seine erste ausgeführte Wiederholung. Jede Wiederholung muss einzeln geladen werden, die Urteile anderer Wiederholungen stehen nur als Quote links.

## Urteil korrigieren und zurücknehmen

Korrigierbar sind Bewerterurteile eines fertigen oder abgebrochenen Laufs; während der Lauf wartet oder läuft, gibt es keine Formulare. Die Korrektur kehrt das Bewerterurteil um, eine Richtung wählt man nicht: Der Knopf heißt «Als erfüllt werten» oder «Als nicht erfüllt werten», je nach Bewerterurteil. Das Formular steckt in einem zugeklappten `<details>` («Urteil korrigieren»), das erst aufgeklappt werden muss. Die Urteil-pk aus der Formular-Adresse nehmen: Sie wechselt mit jedem neuen Lauf.

```bash
playwright-cli -s=dev click "form[action\$='/urteil/5/korrigieren/'] >> xpath=ancestor::details >> summary"
playwright-cli -s=dev fill "#korrektur-5" "Die Schülerin beschreibt ihr Vorgehen."
playwright-cli -s=dev click "form[action\$='/urteil/5/korrigieren/'] button"
```

Die Begründung (`[name=begruendung]`, id `korrektur-<urteil-pk>`) ist Pflicht. Danach landet die Seite auf `?input=…&wiederholung=…` des Urteils, `.messages` zeigt «Korrektur gespeichert.», das Urteil heißt `<Kriterium> · erfüllt · manuell korrigiert` mit `Korrektur von <Konto>, <Zeit>: <Begründung>` und darunter `Bewerter: nicht erfüllt · <Begründung des Bewerters>`. Quote links (`1 von 2 · nicht bestanden · manuell korrigiert`) und Fußzeile (`Fertig · Nicht bestanden · manuell korrigiert`) rechnen mit dem korrigierten Urteil.

Im selben `<details>` (jetzt «Korrektur ändern») stehen dann **Korrektur ändern** und **Korrektur zurücknehmen** (`form[action$='/urteil/<pk>/zuruecknehmen/'] button`). Zurücknehmen lässt wieder das Bewerterurteil gelten, Meldung «Korrektur zurückgenommen.», Quote und Kennzeichnung gehen zurück. Ein Urteil eines ersetzten Laufs (alte Adresse nach **Erneut prüfen**) wird mit «Dieses Urteil gehört nicht zum aktuellen Evallauf.» abgewiesen.

Nicht korrigierbar, also ohne Formular: Kriterien ohne Urteil, nicht ausgeführte Wiederholungen und die automatisch nicht erfüllten Urteile eines gescheiterten Antwortversuchs (aus dem Code, auf Dev nicht nachgeprüft).
