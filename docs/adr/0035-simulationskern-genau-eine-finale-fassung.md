---
status: accepted
---

# Der Simulationskern trägt genau eine finale Fassung; Finalisieren archiviert die Vorgängerin

`Simulationskern.finalisieren()` archiviert die bisherige finale Fassung der
Historie. Der partielle Unique-Index
`simulation_eine_finale_fassung_pro_historie` macht daraus eine Eigenschaft der
Daten: Zu jedem Zeitpunkt steht genau eine Kern-Fassung auf `final`.

Damit wird eingelöst, was das Glossar bis dahin nur behauptet hat — der Kern ist
eine einzige Linie. Die Folge trägt die Oberfläche: `Vignette.objects.anlegen()`
und `Vignette.vorspulen()` greifen über `.latest("finalisiert_am", "pk")` nach
der aktuellsten finalen Fassung. Bei genau einer finalen Fassung ist das kein
Ranking mehr, sondern die einzige Kandidatin. Der Verwaltungsbereich zeigt
entsprechend **eine** finale Fassung, ohne die Markierung, welche davon die
verwendete sei.

## Widerruf dreier Sätze aus ADR-0003 — nur für den Simulationskern

Für den Kern gelten diese drei Sätze aus ADR-0003 nicht mehr:

1. »Das Archivieren der Spitze macht die vorletzte Fassung wieder zur Basis für neue Entwürfe.«
2. »Archivierung ist umkehrbar, solange sie keine Verzweigung erzeugt.«
3. »Ein irreversibles Archivieren wäre ein physisches Löschen mit besserer Presse. Deshalb die Umkehrbarkeit.«

Satz 3 begründet die beiden anderen, und er trägt für den Kern nicht mehr:
`ARCHIVIERT` heißt hier künftig **überholt**, nicht *zurückgenommen*. Der Inhalt
einer überholten Fassung bleibt in der Verwaltungsübersicht vollständig lesbar
und wandert unverändert in den Datenspur-Export (ADR-0029). Es wird nichts
gelöscht, also braucht es keine Umkehrbarkeit.

Für Vignette und Fragebogen-Item bleibt ADR-0003 unberührt. Dort ist das
Archivieren weiterhin eine eigene Geste einer Autor:in und weiterhin umkehrbar.

## Der bewusst gezahlte Preis

Der Simulationskern ist danach das einzige der drei versionierten Artefakte,
dessen Lebenszyklus nicht die von ADR-0021 fixierte Form hat. Von den drei
Kanten bleibt `entwurf → final` als eigenständiger Übergang;
`final → archiviert` existiert nur noch als Nebenwirkung des Finalisierens,
`archiviert → final` gar nicht mehr. `archivieren()` und `entarchivieren()`
entfallen samt Routen, Views und Knöpfen.

Eine misslungene Fassung wird deshalb nicht zurückgenommen, sondern durch eine
neue ersetzt, deren Inhalt die Administration bei Bedarf von Hand aus der
Übersicht kopiert. Das ist Handarbeit für einen seltenen
Administrationsvorfall — der Kern hat genau eine Historie und eine einzige
Pflegerin (ADR-0033).

Die Abweichung ist als Abweichung markiert: ADR-0003 und ADR-0021 tragen an der
betroffenen Stelle je einen Zeiger hierher, damit in keinem akzeptierten ADR
eine Zusage unmarkiert stehen bleibt, die der Code bricht.

Ein Entwurf auf einer überholten Fassung bleibt finalisierbar und spielbar:
`Vignette.finalisieren()` prüft den Kern-Zustand nicht mehr. Das ist die
Reproduzierbarkeit aus ADR-0003 — gespielt wird, worauf gepinnt wurde — und
hält Vorspulen als Wahl der Autor:in, nicht als Bedingung (ADR-0004). Die
Detailansicht weist darauf mit einem statischen Hinweis hin.

## Erwogene Optionen

- **Ein vierter Zustand `ÜBERHOLT` bzw. ein Unterscheidungsfeld**, um *überholt*
  von *absichtlich archiviert* zu trennen — verworfen. Der Begriff wäre nur
  gebraucht worden, solange die absichtliche Archivierung als Geste bestehen
  bleibt; mit ihrem Wegfall ist er gegenstandslos. Er bräche zudem die von
  ADR-0021 ausdrücklich fixierte Form für alle drei Apps, statt für eine.
- **`archivieren()` als Zurücknehmen der Spitze**, spiegelbildlich zum
  automatischen Archivieren — verworfen. Es hielte beide ADR-0021-Kanten am
  Leben, führte aber genau die Doppeldeutigkeit von `ARCHIVIERT` wieder ein, die
  der Wegfall des vierten Begriffs erst auflöst.
- **`entarchivieren()` als Zurückrollen über mehrere Stufen** — verworfen. Es
  verletzte den neuen Index und ist unter der neuen Semantik aktiv kaputt.
- **`bearbeiten()` auch auf archivierten Fassungen**, um den Inhalt einer
  älteren Fassung wiederherzustellen — verworfen zugunsten von Handarbeit
  (siehe »Preis«). Fünf Textfelder aus den `<pre>`-Blöcken der Übersicht zu
  kopieren ist kein Code wert (YAGNI).
- **Eine Datenmigration für Bestandsdaten** — verworfen. Es gibt keine
  Produktivumgebung; Entwicklungs- und Testdatenbanken entstehen neu. Die
  Migration fügt ausschließlich den Constraint hinzu.
- **Eine `messages`-Meldung statt eines statischen Hinweistexts** in der
  Vignettenansicht — verworfen. Der überholte Pin ist ein Zustand, kein
  Ereignis: Er gilt, bis die Autor:in vorspult oder finalisiert. Eine Meldung,
  die beim nächsten Klick verschwindet, wäre genau dann weg, wenn sie gebraucht
  wird.
- **Den nun redundanten Schwestern-Constraint
  `simulation_keine_nichtarchivierten_schwestern` entfernen** — verworfen. Er
  ist zwar logisch impliziert, aber ADR-0021 verlangt Invarianten als partielle
  Indizes; ein Index kostet nichts, sichert künftige Schreibwege ab, und ihn zu
  entfernen wäre eine weitere Migration plus ein weiterer Formbruch.

## Folgen

- Die Administration verliert das Zurücknehmen einer Fassung als Geste. Was
  bleibt, ist das Ersetzen durch eine neue Fassung — die Linie wächst immer nach
  vorn.
- Autor:innen merken das Überholen nicht als Sperre, sondern als Hinweis. Eine
  Kern-Finalisierung ändert für offene Vignettenentwürfe nichts, was sie tun
  dürfen.
- Wer einen künftigen Lebenszyklus am Kern liest, findet hier die Begründung für
  die fehlenden Kanten — nicht in ADR-0003 oder ADR-0021, die für den Kern an
  dieser Stelle hierher verweisen.
