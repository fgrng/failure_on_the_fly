---
status: accepted
---

# Die Datenspur wird long-relational, selbsttragend und pro Erhebung exportiert

Der Export ist ein veröffentlichter Datenformatvertrag: Änderungen daran können
Analyseskripte und bereits ausgegebene Datensätze brechen. Ab der ersten
ausgelieferten Erhebung sind Formatänderungen deshalb nicht mehr rückwirkend;
sie brauchen dann einen eigenen Vorgang. Er liefert einen
ZIP-Download mit relationalen CSV-Dateien nach RFC 4180. Jede Entität hat eine
eigene Tabelle; es gibt keinen Wide-Pivot und kein Einebnen. Das Pivotieren
bleibt der Forschenden und ihrer Auswertungssoftware überlassen.

Die Erhebung ist die Exporteinheit, über alle ihre Stichproben hinweg. Die
Stichprobe ist als Spalte an der Teilnahme enthalten und bildet damit die in
`CONTEXT.md` gemeinte Gruppenstruktur im Export ab. Ein Export je Stichprobe
wäre kein Abbild des Untersuchungsdesigns, sondern ein willkürlicher Ausschnitt.

Der Export ist selbsttragend: Die tatsächlich verwendeten Vignetten- und
Simulationskern-Fassungen sowie Modell-Konfigurationen werden mit vollständigem
Inhalt in eigenen Tabellen ausgeliefert und per ID referenziert. Kein
exportierter Fremdschlüssel zeigt ins Leere. So bleibt der Datensatz ohne
Datenbankzugriff interpretierbar, ohne denselben Fassungstext in jeder
Sitzungszeile zu wiederholen.

Die CSV schreibt `NA` für `NULL`; ein Leerstring bleibt leer. Ein
leeres CSV-Feld würde beide Werte einebnen. Das Ausgabeschema der
Sprachmodell-Naht prüft Denkspur und Äußerung nicht auf Nichtleere: Eine
inhaltsleere, aber erfolgreiche Antwort ist daher möglich. Der antwortlose
Gesprächsschritt nach ADR-0011 trägt dagegen `NULL`. Nur `NA` bewahrt diesen
Abbruch als unterscheidbaren Befund.

Historien-Tabellen werden nicht exportiert. Sie enthalten über ihre
Eigentümerinnen Klarnamen und gehören deshalb nicht in den pseudonymen
Datensatz. Die Historie bleibt allein als Gruppierungsschlüssel der verwendeten
Fassungen erhalten.

Jeder Gesprächsschritt und jede Diagnose tragen in `eingabemodus`, woher der
abgeschickte Text stammt: `getippt`, `transkribiert` oder `gemischt`. Der Wert
ist nie leer und nie `NA`. Er beschreibt die Herkunft des Textes, nicht seine
Bearbeitung — ein Vergleich zwischen Rohtranskript und abgeschickter Fassung
findet nicht statt, und das Rohtranskript wird nicht aufbewahrt. Bestimmt wird
er im Browser der Teilnehmer:in: Er taugt zur Varianzkontrolle in der
Auswertung, nicht als fälschungssicherer Nachweis. Zeilen aus der Zeit vor
seiner Einführung tragen den Startwert `getippt`, ohne dass er dort erhoben
wurde. `gemischt` entsteht allein an der Diagnose: Nur dort hängt das
Spracheingabe-Skript das Transkript an die Tastatureingabe an, statt sie zu
ersetzen und sofort abzuschicken.

## Dateiformat

Der ZIP-Download enthält **fünfzehn Dateien**, auch wenn eine von ihnen keine
Datenzeilen hat; sie enthält dann dennoch ihre Kopfzeile. Alle CSVs folgen RFC
4180: Sie verwenden Kommas, UTF-8 ohne BOM und doppelte Anführungszeichen;
Zeilenumbrüche innerhalb von Zellen bleiben erhalten. Wahrheitswerte erscheinen
als `True` oder `False`, Zeitstempel als ISO 8601 in UTC, sekundengenau und mit
`+00:00`. JSON-Felder stehen als gequoteter JSON-Text in einer Zelle, Bilder als
Pfade statt als Inhalt.

| Datei | Spalten |
| --- | --- |
| `erhebung.csv` | `id`, `name`, `randomisierung`, `instruktionstext`, `einwilligungstext`, `abschlusstext`, `modell_konfiguration_id` |
| `stichproben.csv` | `id`, `beginn`, `ende`, `archiviert` |
| `teilnahmen.csv` | `token`, `stichprobe_id`, `einwilligung_erteilt`, `audioverarbeitung_eingewilligt`, `randomisierungs_seed`, `erstellt_am` |
| `vignettenziehungen.csv` | `token`, `vignette_id`, `position` |
| `sitzungen.csv` | `id`, `token`, `position`, `status`, `vignette_id`, `simulationskern_id`, `modell_konfiguration_id`, `erstellt_am`, `verbrauchte_zeit` |
| `gespraechsschritte.csv` | `id`, `sitzung_id`, `reihenfolge`, `eingabe`, `denkspur`, `aeusserung`, `erstellt_am`, `eingabemodus` |
| `fehlversuche.csv` | `gespraechsschritt_id`, `grund`, `rohantwort` |
| `diagnosen.csv` | `sitzung_id`, `text`, `erstellt_am`, `eingabemodus` |
| `itembloecke.csv` | `id`, `teilnahme_token`, `andockpunkt`, `sitzung_id`, `vorgelegt_am`, `erledigt_am` |
| `item_antworten.csv` | `itemblock_id`, `teilnahme_token`, `item_id`, `item_typ`, `andockpunkt`, `sitzung_id`, `position`, `freitext`, `likert_stufe` |
| `vignettenfassungen.csv` | `id`, `historie_id`, `finalisiert_am`, `fehlermuster_beschreibung`, `lernauftrag_text`, `lernauftrag_bild`, `lernauftrag_bildbeschreibung`, `lernauftrag_simulationshinweise`, `arbeitsheft_text`, `arbeitsheft_bild`, `arbeitsheft_bildbeschreibung`, `arbeitsheft_simulationshinweise`, `schuelerin_name`, `schuelerin_geschlecht`, `lehrperson_name`, `lehrperson_geschlecht`, `fach`, `thema`, `klassenstufe`, `referenzdiagnose`, `budget_typ`, `budget_wert` |
| `simulationskerne.csv` | `id`, `historie_id`, `finalisiert_am`, `system_prompt_vorlage`, `user_prompt_vorlage`, `rahmenhandlung_einleitung`, `rahmenhandlung_gespraechseinleitung`, `rahmenhandlung_debrief` |
| `modellkonfigurationen.csv` | `id`, `anbieter`, `sprachmodell`, `parameter` |
| `fragebogen_items.csv` | `id`, `typ`, `wortlaut` |
| `likert_skala.csv` | `stufe`, `pol` |

## Die Modell-Konfiguration im Export

`modellkonfigurationen.csv` trägt `id`, `anbieter`, `sprachmodell`, `parameter`.
Der Anbieter steht **vor** dem Modellnamen, weil derselbe Modellstring bei
verschiedenen Anbietern Verschiedenes bedeutet: Ohne ihn ist der Name nicht
vollständig interpretierbar, die Lesereihenfolge folgt also der Abhängigkeit.

Zwei Felder der Konfiguration bleiben aus je eigenem Grund draußen:
`anbieter_token`, weil es ein Geheimnis ist und in keinem ausgelieferten
Artefakt erscheinen darf; `anbieter_basis_url`, weil sie bei Infomaniak eine
`product_id` und damit einen Kontoidentifikator trägt, der im pseudonymen
Datensatz nichts zu suchen hat. Das Selbsttragend-Prinzip bleibt gewahrt: Es
verlangt den *Inhalt* der Konfiguration, und der ist mit Anbieter, Modell und
Parametern vollständig — die Basis-URL ist Infrastruktur.

Der Provider-Filter, mit dem die Sprachmodell-Naht bei OpenRouter die
Datenschutz-Zusicherung erzwingt, wird nicht eigens exportiert. Er folgt
eindeutig aus dem Anbieter: Aus `anbieter` ist ablesbar, welche Zusicherung für
die Zeile galt; eine zusätzliche Spalte würde eine Wahlmöglichkeit vortäuschen,
die keine Konfiguration hat.

Die Transkriptions-Konfiguration erscheint gar nicht im Export (ADR-0026): Die
Transkription ist eine Deployment-Entscheidung der Betreiber:in, keine
Eigenschaft der Datenspur.

## Die verbrauchte Gesprächszeit im Export

`sitzungen.csv` trägt in `verbrauchte_zeit` die tatsächlich verbrauchte
Gesprächszeit der Sitzung in Sekunden — derselben Einheit, in der `budget_wert`
einer Vignettenfassung mit `budget_typ` `zeit` bemessen ist. Die verbrauchte
Zeit ist nach ADR-0012 selbst eine Größe der Datenspur: Sie sagt etwas über
diagnostische Ökonomie aus, und genau dafür ist das Budget eine Obergrenze und
kein Soll. Seit ADR-0042 steht sie an der Sitzung und kann deshalb exportiert
werden.

**Die Spalte ist nur zusammen mit dem Budget-Typ der Vignettenfassung zu
lesen.** Für Sitzungen einer Vignette mit schrittbasiertem Budget bleibt sie
bei null — dort läuft keine Uhr, die Null ist kein gemessener Wert.

**Der Startpunkt der laufenden Spanne erscheint nicht.** Er ist interne
Buchführung der Uhr und über das Ende einer Sitzung hinaus bedeutungslos.

## Der Fragebogen im Export

Vier Tabellen tragen den Fragebogen-Teil einer Erhebung: `itembloecke.csv` je
vorgelegtem Block, `item_antworten.csv` je vorgelegtem Item,
`fragebogen_items.csv` mit dem vollen Wortlaut der tatsächlich vorgelegten
Item-Fassungen und `likert_skala.csv` mit der globalen Kodierung.

**`likert_stufe` steigt mit der Zustimmung**, ebenso `stufe` in
`likert_skala.csv` — es ist dieselbe Zahl. 1 ist »Stimme gar nicht zu«, 6 ist
»Stimme voll zu«. Aus einer nackten Zahl in der CSV ist die Richtung nicht
erkennbar, und eine still umgedrehte Skala ist der klassische
Auswertungsfehler; deshalb liegt die Kodierung als eigene Tabelle im ZIP und
nicht nur im Quellcode. Die Pole gelten global und stehen deshalb nicht als
Eigenschaft an jeder Item-Fassung.

**Der Erledigt-Marker sitzt am Itemblock**, nicht an der Antwortzeile
(ADR-0041). Erst `vorgelegt_am` und `erledigt_am` am Block trennen »vorgelegt
und bewusst leer abgeschickt« von »vorgelegt, aber abgebrochen« und von »nie
vorgelegt« — Fragebogen-Items sind freiwillig (ADR-0008), aus den Werten allein
folgt das nicht. Den Marker je Antwortzeile mitzuführen, wiederholte denselben
Zeitstempel *n*-fach je Block und ebnete ein, was dieser Kontrakt getrennt
hält; die Antwortzeile bleibt reine Datenspur.

**Die Item-Historie läuft nicht mit, auch nicht als bloße ID.** Bei
`vignettenfassungen.csv` steht `historie_id` als reiner Gruppierungsschlüssel,
weil Vignetten gezogen werden und die Ziehung auf die Linie verweist. Items
werden nicht gezogen: Die Historie hätte in der Auswertung keinen Referenten,
und die Tabelle selbst bleibt nach der Regel oben ohnehin draußen.

**Diese Erweiterung ist rein additiv.** Zu den ursprünglich elf Dateien sind
Tabellen ausschließlich hinzugefügt worden. Keine bestehende Datei, Spalte oder
Spaltenreihenfolge ändert sich, bestehende Analyseskripte brechen nicht — die
Regel oben, dass Formatänderungen ab der ersten ausgelieferten Erhebung nicht
mehr rückwirkend sind, ist damit gewahrt.

## Erwogene Optionen

- **Wide-Export mit einer Zeile je Teilnahme oder Sitzung** — verworfen. Er
  würde Gesprächsschritte, Fehlversuche und verwendete Fassungen entweder
  vervielfachen oder verlieren.
- **Leere Felder für `NULL`** — verworfen. Sie unterschieden einen Abbruch
  nicht mehr von einer erfolgreichen, inhaltsleeren Modellantwort.
- **Historien mit Eigentümerinnen exportieren** — verworfen. Sie würden die
  Pseudonymität des Forschungsdatensatzes brechen.
- **Die Likert-Kodierung als Kommentarzeile in der Antwortdatei** — verworfen.
  RFC 4180 kennt keine Kommentare; jeder Parser stolperte darüber.
- **Die Likert-Kodierung als Liesmich-Datei im ZIP** — verworfen. Sie wäre das
  einzige nicht maschinenlesbare Artefakt im Download und ließe sich nicht
  joinen. Die eigene kleine Tabelle folgt stattdessen dem long-relationalen
  Prinzip.

## Folgen

- CSV-Dateien, Schlüsselspalten und die Bedeutung von `NA` sind Teil des
  stabilen Datenformatvertrags.
- Auswertungen können alle Stichproben einer Erhebung gemeinsam lesen und bei
  Bedarf über die Stichprobenspalte gruppieren.
- Die vollständige Datenspur bleibt ohne Zugriff auf die Anwendungsdatenbank
  nachvollziehbar; Identitäten von Forschenden bleiben außerhalb des Exports.
