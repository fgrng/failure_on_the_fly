---
status: accepted
---

# Der Ablauf-Schritt ist ein Objekt, und der Itemblock bekommt eine Tabelle

ADR-0016 hat drei Dinge abgelehnt, die hier eingeführt werden. Alle drei stehen
dort außerhalb der als bindend markierten Liste — sie sind Folgerungen, keine
Grundsätze. Dieses ADR führt sie nach und hält fest, warum die damalige
Ablehnung nicht mehr trägt.

## Warum die frühere Ablehnung nicht mehr trägt

ADR-0016 schloss, der Sitzungs-Block sei kein Ablauf-Schritt, weil er — anders
als der Abschluss-Block — nicht aus der Datenbank rekonstruierbar sei. Diese
Beobachtung war richtig, aber ihre Ursache lag nicht beim Sitzungs-Block.

Fragebogen-Items sind freiwillig (ADR-0008). Damit ist eine leere Antwort eine
gültige Endantwort, und „nicht ausgefüllt" ist von „bewusst leer gelassen"
nicht zu unterscheiden. Aus den Antwortzeilen allein folgt deshalb **für keinen
Andockpunkt**, ob sein Block noch offen ist. Dass der Abschluss-Block dennoch
als rekonstruierbar galt, lag an einer Hilfsannahme: Er ist der letzte Schritt,
also stand hinter ihm der Abschlusszeitpunkt der Erhebungsbindung als Ersatz für
den fehlenden Marker. Der Sitzungs-Block hat keinen solchen Nachbarn und musste
sich sein Gedächtnis deshalb anderswo suchen — er fand es in der Browser-Session,
als dreiteiliges Besuchsprotokoll, neben der Freigabe des Abschluss-Blocks.

Die Ablehnung trug also nur so lange, wie man bereit war, den Fortschritt einer
pseudonymen Teilnahme im Browser zu halten. Das ist keine Architekturfrage,
sondern ein Datenverlust: Der Teilnahme-Link ist stabil und der Wiedereinstieg
ausdrücklich vorgesehen (ADR-0006, ADR-0018), aber ein Browserwechsel, ein
Fensterschluss oder eine verfallene Session kostete Fortschritt. Sobald der
Erledigt-Marker als Spalte existiert, ist der Sitzungs-Block genauso
rekonstruierbar wie der Abschluss-Block, und die Asymmetrie zwischen den beiden
Andockpunkten verschwindet — sie war nie eine Aussage über den Fachbereich.

## Die drei Nachführungen

**Ein allgemeiner Ablauf-Schritt als Objekt wird eingeführt.**
`erhebungen.ablauf.naechster_schritt(erhebungsbindung)` liefert einen
geschlossenen Typ über sechs Fälle: noch nicht begonnen, laufende Sitzung,
nächste Vignette, offener Sitzungs-Block, offener Abschluss-Block, Ende.
ADR-0016 hatte ihn abgelehnt, weil der Sitzungs-Block ohnehin nicht darin
vorkommen konnte; ein Typ über die halbe Wahrheit wäre teurer gewesen als eine
Union aus Vignette, Block und Ende. Mit dem Marker sind die Fälle erschöpfend,
und die Erhebungs-Views verzweigen einmal darüber statt an sechs Stellen per
Typprüfung und an drei weiteren per Statusabfrage.

**Der Itemblock bekommt eine Tabelle.** Ein Datensatz je vorgelegtem Block, mit
Bezug auf die Erhebungsbindung, den Andockpunkt und — nur am Andockpunkt nach
einer Sitzung — die Sitzung, dazu ein Vorlage- und ein Erledigt-Zeitstempel. Die
Item-Antworten hängen an ihm.

Der Marker sitzt am Block und nicht an den Antwortzeilen: Ein Feld je Zeile wäre
für einen Block *n*-fach redundant, erzeugte den fachlich nicht vorgesehenen
Zustand „teilweise abgeschickt" und belastete den Export (ADR-0029) mit einer
Spalte ohne Forschungsbedeutung. Die Item-Antwort bleibt damit reine Datenspur.
Für die Forschung ist der Vorlage-Zeitstempel selbst ein Gewinn: Erst mit ihm
ist „vorgelegt und bewusst leer abgeschickt" von „nie vorgelegt" unterscheidbar,
und fehlende Werte werden interpretierbar.

**Der Sitzungs-Block ist aus der Datenbank rekonstruierbar.** Damit entfallen
beide Ablaufmarker der Browser-Session. Was dort bleibt, ist die Zuordnung von
Teilnahme-Link zu Token — Zugang, nicht Fortschritt.

## Was unverändert bindend bleibt

Die bindende Liste aus ADR-0016 wird **nicht** angetastet:

- **Der Schnitt entlang der Domänenobjekte.** Der Fortschritt bleibt im
  bestehenden Ablaufmodul der Erhebungs-App und behält seinen Namen. Der
  Itemblock ist ein Objekt der Erhebung, kein neues Modul.
- **Die Azyklizität samt Kantenrichtung.** Die Schnittstelle hängt an der
  **Erhebungsbindung**, nicht an der Teilnahme. Ein Erhebungsmodul, dessen Anker
  der aufgerufenen App gehört, drehte die Blickrichtung um. Der Fortschritt liest
  von einer Sitzung ausschließlich deren Status — nie Gesprächsschritte,
  Zeitbudget, Diagnose oder Transkript.
- **Die Zahl der Nähte: zwei.** Es kommt **keine dritte** hinzu. Das
  Fortschrittsmodul hat genau eine Implementierung und ist damit keine Naht im
  Sinne von ADR-0016. Dass Tests ohne HTTP an ihm ansetzen, macht es nicht zu
  einer: Ein Ansatzpunkt für einen Test ist keine Stelle, an der Verhalten
  ausgetauscht wird.

Unberührt bleiben ebenso ADR-0008 (genau zwei Andockpunkte — es kommt keiner
hinzu) sowie ADR-0006 und ADR-0018 (die Teilnahme trägt keine Identität; der
Fortschritt hängt am Token und macht ihn gerade deshalb browserunabhängig).

## Die Darstellung ändert sich nicht

**ADR-0025 bleibt unberührt.** Der Sitzungs-Block wird weiterhin als bereits
gerendertes Fragment in den generischen Anhang-Slot der Sitzungsdarstellung
gehängt und reist mit dem HTMX-Swap der Sitzungsfortsetzung mit; der
Abschluss-Block bleibt eine eigene Seite. Was der Anhang-Slot verliert, ist
allein der Ablaufzustand: Er ist danach ein reiner Darstellungsmechanismus.

Dass beide Andockpunkte im Ablauf nun gleich behandelt werden, heißt
ausdrücklich nicht, dass sie gleich dargeboten werden. Der Unterschied ist eine
Frage des Erhebungsinstruments, nicht der Architektur: Der Sitzungs-Block trägt
die Beurteilung der eben beendeten Sitzung, und ein Seitenwechsel unmittelbar
nach dem Debrief erhöhte die Abbruchwahrscheinlichkeit an der verletzlichsten
Stelle. Der Anhang-Slot ist damit dauerhaft und keine Übergangslösung.

## Erwogene Optionen

- **Einen Erledigt-Marker je Antwortzeile statt einer Tabelle** — verworfen.
  Redundant je Block, erzeugt den Zustand „teilweise abgeschickt" und schleppt
  eine bedeutungslose Spalte in den Export.
- **Den Sitzungs-Block über den Sitzungsstatus ableiten** — verworfen. Eine
  beendete Sitzung sagt nichts darüber, ob ihr Fragebogen abgeschickt wurde;
  genau das ist die Lücke, die das Besuchsprotokoll in der Browser-Session
  füllte.
- **Das Besuchsprotokoll in der Browser-Session belassen und nur aufräumen** —
  verworfen. Es hätte den Datenverlust beim Browserwechsel erhalten, der der
  eigentliche Anlass ist.
- **Einen Ablauf für Training und Erhebung gemeinsam abstrahieren** — verworfen
  (vorerst). Ein Training ist ein Vorrat in freier Reihenfolge, keine Sequenz;
  eine Abstraktion über genau einen Fall. Die Trennlinie „der Fortschritt liest
  von einer Sitzung nur deren Status" ist bewusst so gelegt, dass sie auch für
  einen Trainingsablauf gälte.

## Folgen

- Die Frage „was kommt als Nächstes" wird an genau einer Stelle beantwortet. Die
  Abfrage ist **schreibfrei**; daneben stehen benannte, idempotente Kommandos für
  jeden Schreibvorgang: die Ziehung festschreiben, eine Vignette beginnen, einen
  Block vorlegen, einen Block erledigen, die Bindung abschließen.
- Die Vignettenziehung — Forschungsdaten — entsteht nicht mehr als Nebenwirkung
  eines Seitenaufrufs, sondern an einer benannten Stelle.
- Der Abschlusszeitpunkt der Erhebungsbindung bleibt ein Feld und wird nicht
  abgeleitet: Der Zeitstempel trägt selbst Bedeutung, weil an ihm hängt, ob eine
  Teilnahme nach Ende des Erhebungsfensters unvollständig geblieben ist. Gelesen
  und geschrieben wird er nur noch im Ablaufmodul.
- Die schreibenden Kommandos sperren die Erhebungsbindung. Der Bedarf entsteht
  durch diese Änderung selbst: Solange der Fortschritt im Browser lag, war er pro
  Browser serialisiert. Ein harter Datenbank-Constraint gegen mehrere gleichzeitig
  laufende Sitzungen gehörte der Sitzungs-App und träfe auch Trainings; er ist
  hier bewusst nicht Teil der Entscheidung.
- Die bisherige Block-Dataclass entfällt ersatzlos — sie existierte nur, weil es
  keine Tabelle gab. Der Fachbegriff **Itemblock** hat danach genau einen
  Referenten und steht im Glossar. Der **Fortschritt** bekommt keinen Eintrag: Er
  ist eine abgeleitete Antwort, kein Gegenstand — dieselbe Begründung, mit der
  ADR-0016 den Ausgang eines Gesprächsschritts aus dem Glossar heraushält.
- Die Tabelle entsteht als Neuanlage ohne Backfill; der Bezug der Item-Antwort
  auf den Block ist sofort verpflichtend. Ein Backfill käme ohnehin nicht in
  Frage: Der Erledigt-Zustand ist für Altdaten grundsätzlich nicht
  rekonstruierbar — genau deshalb gibt es die Tabelle.
