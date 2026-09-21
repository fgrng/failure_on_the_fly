---
status: accepted
---
# Lebenszyklus versionierter Artefakte: Entwurf, final, archiviert, Historie

Dieses ADR fasst den Stand von ADR-0003, ADR-0017 und ADR-0021 zusammen und
ersetzt sie. Die Kern-Sonderform steht in ADR-0035, die Erhebung als
Nicht-Artefakt in ADR-0027; beide gelten fort. Von ADR-0028 bleibt die
Privatheit des Items (heute in ADR-0039), die Ausnahme von der
Historien-Archivierung wird hier aufgehoben.

## Reproduzierbarkeit verlangt unveränderliche Fassungen

Als Forschungsinstrument muss FailureOnTheFly reproduzierbar sein: Eine
abgeschlossene Sitzung zeigt auf exakt die Fassungen von Artefakten, die damals gespielt wurden.
Vignette, Simulationskern und Fragebogen-Item sind deshalb **versionierte
Artefakte**: Ein **Entwurf** ist veränderlich, eine **finale** Fassung ist
unveränderlich. Das Bearbeiten einer finalen Fassung erzeugt einen neuen
Entwurf, der die Vorgängerin referenziert; die alte Fassung bleibt erhalten.
Eine **Historie** gruppiert die sequenziell entstandenen Fassungen.

Trainings und Erhebungen binden nur **finale** Fassungen ein. Jede Sitzung
protokolliert zusätzlich die tatsächlich verwendete Vignettenfassung,
Kern-Fassung und Modell-Konfiguration, damit die Datenspur auch dann
vollständig bleibt, wenn ein Artefakt später doch mutiert oder gelöscht wird.

Nicht versioniert sind die **Modell-Konfiguration** (unveränderlich und
append-only, ADR-0013), das **Gesprächsbudget** (ein Feld der Vignette, wird
mit ihr eingefroren, ADR-0012) und die **Erhebung** (ein einzelnes Objekt, das
nur die Statusnamen leiht, ADR-0027).

Einen Status **„veröffentlicht"** gibt es nicht, weil es nichts zu
veröffentlichen gibt (ADR-0039).

## Die Historie bleibt linear

Je Historie existiert **höchstens ein Entwurf**. Zwei offene Entwürfe wären
eine Verzweigung, und „die neueste Fassung" wäre nicht mehr eindeutig. Ein
neuer Entwurf entsteht immer aus der neuesten nicht-archivierten Fassung.

**Entwürfe dürfen physisch gelöscht werden.** Sie waren nie final, nie
eingebunden, und keine Datenspur zeigt auf sie.

## Archivierung statt Löschen

Eine finale Fassung kann **archiviert** werden: das logische Löschen.
Physisches Löschen finaler Fassungen gibt es nicht, denn Datenspuren müssen
sie noch Jahre später darstellen können. Was Archivierung bewirkt:

- **Neu einbinden:** unmöglich. Die Fassung verschwindet aus jeder Auswahl.
- **Training:** Die Fassung ist sofort nicht mehr spielbar. Bereits gespielte
  Sitzungen bleiben einsehbar.
- **Erhebung:** Eine laufende Erhebung **ignoriert die Archivierung**. Sie hat
  die Fassung gepinnt, Teilnehmende spielen sie zu Ende.
- **Datenspur:** Archivierte Fassungen bleiben aus jeder Sitzung heraus lesbar.

Die Asymmetrie zwischen Training und Erhebung folgt der Linie „ein Training ist
ein Übungsangebot, eine laufende Erhebung ist eine Messung". Eine Autor:in, die
eine fehlerhafte Vignette archiviert, stoppt sie im Training sofort, in der
Erhebung nicht. Dort hält die Forschende:r die Erhebung an; das ist eine
Forschungsentscheidung, keine Autorenentscheidung.

Archivieren wirkt auch **rückwärts auf die Linie**: Wird die Spitze
archiviert, ist die vorletzte Fassung wieder die neueste nicht-archivierte und
damit die Basis für neue Entwürfe. Eine misslungene Fassung lässt sich so
zurücknehmen, ohne sie zu löschen.

**Archivierung ist umkehrbar.** Eine archivierte Fassung kann entarchiviert
werden, solange dabei keine Verzweigung entsteht: Ist aus ihr oder ihrer Vorgängerinnen
inzwischen eine neue finale Fassung entstanden, bliebe die entarchivierte als
Verzweigung zurück. Genau das ist ausgeschlossen.

Eine ganze **Historie** ist archivierbar: Sie archiviert alle Fassungen und
löscht den offenen Entwurf. Eine vollständig archivierte Historie ist eine
tote Linie. Das gilt für Vignettenhistorie und Fragebogen-Item-Historie
gleichermaßen.

**Für den Simulationskern gilt das nicht.** Dort heißt `archiviert`
**überholt**: Es entsteht nur als Nebenwirkung des Finalisierens der
Nachfolgerin, ist nicht umkehrbar, und zu jedem Zeitpunkt trägt die eine
Kern-Historie genau eine finale Fassung (ADR-0035).

## Die Form: vier Felder und partielle Unique-Indizes

Jedes versionierte Artefakt implementiert dieselbe Form:

| Feld               | Zweck                                                   |
| ------------------ | ------------------------------------------------------- |
| `zustand`        | `TextChoices`: `entwurf`, `final`, `archiviert` |
| `finalisiert_am` | nullbar, einmal gesetzt,**nie zurückgesetzt**    |
| `historie`       | Fremdschlüssel,**NOT NULL**                      |
| `vorgaengerin`   | selbstreferenzierend, nullbar                           |

Der Automat hat drei Kanten: `entwurf → final`, `final → archiviert`,
`archiviert → final`. Beim Kern bleibt davon nur `entwurf → final` als
eigenständiger Übergang (ADR-0035). Ein Entwurf wird nie archiviert, sondern
gelöscht. Deshalb impliziert `archiviert` immer „war einmal final", und
`finalisiert_am` überlebt das Entarchivieren.

Die Invarianten leben in der Datenbank, nicht in Prüfungen:

```python
UniqueConstraint(fields=['historie'],     condition=Q(zustand='entwurf'))
UniqueConstraint(fields=['vorgaengerin'], condition=~Q(zustand='archiviert'))
```

Der erste erzwingt „höchstens ein Entwurf je Historie". Der zweite verbietet
zwei nicht-archivierte Fassungen mit derselben Vorgängerin, womit das
Entarchivieren gar nicht erst falsch ausgehen kann. Dazu ein
`CheckConstraint`: `zustand='entwurf'` genau dann, wenn `finalisiert_am IS NULL`. Der Kern ergänzt einen dritten partiellen Index für die eine finale
Fassung (ADR-0035). 

Die **Historie entsteht eifrig**, in derselben Transaktion wie die erste
Fassung. Bei fauler Entstehung müsste der `historie`-Fremdschlüssel an der
bereits finalen ersten Fassung nachgetragen werden, ein Schreibzugriff auf eine
unveränderliche Zeile. Zudem beißt der Entwurf-Index nur über eine
Nicht-NULL-Spalte. „Sichtbar und benennbar erst ab der zweiten Fassung" ist
deshalb eine Präsentationsregel, keine Entstehungsregel.

**Vollständigkeit** (welche Felder ein Entwurf zum Finalisieren gefüllt haben
muss) gehört nicht in diese Form. Sie ist je Artefakt verschieden und lebt in
dessen `finalisieren()`.

## Die Form wird je Artefakt eigenständig implementiert

Es gibt **keine gemeinsame Lebenszyklus-Basis**: keine abstrakte Basisklasse,
keine generische `ContentType`-Tabelle, keine geteilte Übergangs-Funktion. Jede
App schreibt ihre Felder, Constraints und Übergänge selbst. Dieses ADR ist eine
Spezifikation, die drei Apps unabhängig erfüllen, keine Implementierung.

Die Gemeinsamkeit ist kleiner, als sie aussieht. Die Vignette pinnt einen Kern,
kann vorgespult werden (ADR-0004), friert das Gesprächsbudget ein und trägt an
ihrer Historie einen Eigentümer-Kreis (ADR-0039). Der Kern ist eine einzige
Linie mit genau einer finalen Fassung, gehört der Administration und trägt
keinen Kreis. Das Fragebogen-Item hat Kreis, aber keinen Kern und kein
Gesprächsbudget. Eine Basis über diesen dreien müsste jede Abweichung
durch sich hindurchpressen; der übliche Ausgang ist ein Flaggenfeld je
Abweichung.

Den Ausschlag gibt die Reversibilität: Von duplizierten Feldern zu einer
abstrakten Basis zu wechseln, erzeugt in Django keine Migration. Der umgekehrte
Weg, eine generische Tabelle auseinanderzunehmen, ist eine Datenmigration über
Forschungsdaten. Wir wählen die Option, die am wenigsten voraussetzt.

Die Basis für den Eigentümer-Kreis (ADR-0037) widerspricht dem nicht: Sie
spannt quer zur Lebenszyklus-Achse und trägt keinen Zustand.

## Erwogene Optionen

- **Ein Status *veröffentlicht*** — verworfen. Es gibt nichts zu
  veröffentlichen.
- **Physisches Löschen finaler Fassungen** — verworfen. Datenspuren müssen sie
  darstellen können.
- **Irreversibles Archivieren** — verworfen. Ohne Umkehrbarkeit wäre
  Archivieren ein physisches Löschen unter anderem Namen. Für den Kern später
  doch gewählt, weil dort nichts verschwindet (ADR-0035).
- **Abstrakte Basismodelle in einer `versioning`-App** — verworfen. Setzt
  voraus, dass die drei Lebenszyklen gleich bleiben; sie sind es schon heute
  nicht.
- **Eine konkrete Fassungstabelle mit `GenericForeignKey`** — verworfen.
  Polymorpher Zugriff gegen echte Fremdschlüssel und eine schwer umkehrbare
  Datenmigration.
- **Ein gemeinsamer parametrisierter Testvertrag über die Invarianten** —
  verworfen zugunsten vollständiger Unabhängigkeit, einschließlich der Tests.
- **Invarianten als Modell-Prüfungen (`clean()`)** — verworfen. Sie hängen am
  Aufruf von `full_clean()` und lassen sich per `save()` oder Bulk-Write
  umgehen.
- **Faule Historie-Entstehung** — verworfen, weil sie eine finale Fassung
  mutieren müsste.

## Folgen

- Autor:innen zahlen mit einem Entwurf/Final-Zyklus; dafür ist „welche
  Fassung lief in Erhebung X?" trivial beantwortbar.
- Trainings dürfen im laufenden Betrieb Vignetten austauschen. Alte Sitzungen
  zeigen die damals gespielte Fassung.
- „Höchstens ein Entwurf je Historie" ist seit der Ko-Autorschaft (ADR-0039)
  eine echte Schranke, keine unmögliche Situation mehr. Der partielle Index
  trägt sie.
- Die Form ist an drei Stellen implementiert und kann auseinanderlaufen. Ein
  Fehler im Entarchivieren, der in `vignetten` behoben wird, bleibt in
  `fragebogen_items` liegen. Das ist der bewusst gezahlte Preis; dieses ADR
  macht die Form explizit, damit eine Abweichung als Abweichung erkennbar ist.
  Wer eine Abweichung einführt, kommentiert sie.
- Der Kern braucht eine Historie, obwohl er eine einzige Linie ist, sonst hätte
  der Entwurf-Index keine Spalte. Seine Historie ist ein namenloser Singleton.
- Ein späterer Architektur-Review wird die gemeinsame Basis erneut vorschlagen.
  Dieses ADR ist die Antwort darauf; ADR-0037 zeigt, wie eine Basis aussieht,
  die *nicht* darunterfällt.
