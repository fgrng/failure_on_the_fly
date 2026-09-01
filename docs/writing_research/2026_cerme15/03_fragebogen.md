# Instrument: Fragebogen zur wahrgenommenen Vignettenqualität

Stand 2026-09-01. Grundlage: Entwurf aus der NotebookLM-Auswertung von Notebook A,
plus Abgleich mit dem Tool.

## 1. Was daran für das Paper trägt

Die vier Dimensionen sind nicht bloß eine Sammlung subjektiver Einschätzungen – sie sitzen genau
auf dem Argument aus `02_konzept.md`:

| Dimension | Bezug zum roten Faden |
|---|---|
| A – Kontextuelle Authentizität | prüft die Prämisse aus Schritt 5: wird die Simulation als Gegenüber angenommen |
| **B – Responsivität / ESRU** | **misst genau das, was Schritt 3 als Zugewinn behauptet** |
| C – Extraneous Cognitive Load | prüft, ob die Technik den Zugewinn wieder auffrisst |
| D – Immersion | die zweite Hälfte der Prämisse |

Dimension B ist der wichtigste Fund. Sie schließt den Kreis: Die Theorie identifiziert Kontingenz
und den eliciting-Zyklus als das, was statische Vignetten nicht können; das Instrument fragt
Studierende genau danach, ob die dynamische Vignette es kann. Das ist keine allgemeine
Akzeptanzbefragung mehr, sondern eine Prüfung der eigenen theoretischen Behauptung. **Das gehört so
in Abschnitt 7 des Papers geschrieben** – es ist der Grund, warum die Studie trotz fehlender
Wirksamkeitsdaten etwas über die Sache aussagt.

Ein zusätzliches Item in Dimension A verdient Aufmerksamkeit: die Einschätzung, ob der Fehler als
**systematische Fehlvorstellung** und nicht als Flüchtigkeitsfehler wahrgenommen wird. Das ist die
Validitätsprüfung des zentralen Konstrukts – eine simulierte Schüler:in, deren Fehlermuster nicht
als systematisch erlebt wird, hat ihre Aufgabe verfehlt. Für das Paper ist das anschlussfähig an den
Begriff **Fehlermuster** aus `CONTEXT.md`.

## 2. Skala: sechsstufig, entschieden

**Sechsstufige Likert-Skala ohne neutrale Mitte**, in Erhebung und Paper. Das deckt sich mit dem
Tool: `fragebogen_items/models.py` setzt die Stufen 1–6 global und nicht editierbar
(„Stimme gar nicht zu" … „Stimme voll zu"), `erhebungen/models.py` erzwingt den Bereich per
Datenbank-Constraint. Die entfallende Mitte ist begründbar (keine Ausweichkategorie bei
Einschätzungsurteilen) und im Paper einen Halbsatz wert.

Folge für die Berichterstattung: Items, die aus fünf- oder siebenstufigen Originalen stammen, sind
nach der Umskalierung **adaptiert, nicht validiert**. So sind sie zu berichten. Eine
Vergleichbarkeit mit den Kennwerten der Originalstudien ist damit nicht behauptbar – sie ist aber
auch nicht nötig, weil dieses Paper keine Skalenkennwerte berichtet.

## 3. Status: Befragung läuft noch nicht

Damit ist das Instrument **noch gestaltbar** und nicht durch finale Item-Fassungen fixiert. Zwei
Konsequenzen:

- Der obige Entwurf ist Planungsstand, nicht Dokumentation. Abschnitt 7 des Papers beschreibt das
  **geplante** Instrument – im Futur bzw. als Design, nicht als Bericht.
- Vor dem Finalisieren der Items lohnt der Blick auf Abschnitt 5: Was im Paper stehen soll, sollte
  auch erhoben werden, und umgekehrt.

**Terminlich wichtig:** Die finale Fassung des Papers ist erst am **12.12.2026** fällig (Einreichung
15.09.2026). Läuft die Erhebung im Herbstsemester und ist die Auswertung bis Anfang Dezember
belastbar, können **erste Ergebnisse noch in die Proceedings-Fassung**. Das ändert nichts am
Zuschnitt der Einreichung, ist aber ein Grund, den Erhebungszeitplan früh gegen den 12.12. zu
stellen.

## 4. Zu verifizieren vor Verwendung im Paper

Zu prüfen ist nur, was im Paper **aktiv zitiert** wird. Kennwerte (Cronbach's α, Korrelationen)
gehören nicht dazu: Dieses Paper berichtet keine Skalenkennwerte, und die Items werden ohnehin als
adaptiert ausgewiesen. Die Liste beschränkt sich daher auf Zuschreibungen, die im Text tragen:

- [ ] Wirth et al. (2023): die fünf Qualitätskriterien (Authentizität, Typikalität,
      Repräsentativität, Interesse, Aussagekraft) – Wortlaut und ob sie dort auf
      Aufschnaiter et al. (2017) zurückgeführt werden
- [ ] **Aufschnaiter et al. (2017)** liegt in keinem der beiden Notebooks. Beschaffen, falls direkt
      zitiert; sonst korrekt als Sekundärzuschreibung über Wirth et al. formulieren.
- [ ] Ruiz-Primo (2011) / Ruiz-Primo & Furtak (2007): ESRU als Bezeichnung und die Bedeutung der
      vier Schritte – dieser Begriff trägt in Abschnitt 2 des Papers Gewicht
- [ ] Hoppe et al. (2024) / Syring et al. (2015): woher die Immersions-Items stammen, um die
      Adaption korrekt zuzuschreiben

Hintergrund: Die ursprüngliche Item-Herleitung stammt aus einer KI-Zusammenfassung, in der mehrere
Zitatmarker leergelaufen sind („angepasst nach" ohne folgende Quelle). Die Provenienz ist dort also
nicht aus dem Text rekonstruierbar. Bei einem **offenen** Review durch Autor:innen derselben TWG ist
eine falsche Zuschreibung teurer als anderswo.

## 5. Was davon ins Paper passt

Abschnitt 7 hat **rund eine Seite** für Kontext, Stichprobe, Instrument und Auswertung. 16 Items
passen dort nicht hinein.

Realistische Form:

- die vier Dimensionen benennen, mit ihrer theoretischen Herkunft in je einem Halbsatz
- Zahl der Items je Dimension und je Andockpunkt (nach jeder Vignettensitzung / am Ende)
- **ein bis zwei Beispielitems**, am besten aus Dimension B, weil dort der Theoriebezug sichtbar wird
- Skala: sechsstufig ohne neutrale Mitte
- ein Satz zum geplanten Auswertungsverfahren

Der vollständige Itemsatz gehört nicht ins Paper. Wenn er sichtbar sein soll, dann über einen
Verweis auf ein Supplement oder auf die Präsentation.

## 6. Weiterführender Vorschlag aus dem Entwurf

Die Anregung, nach dem Vorbild von Wirth et al. (2023) eine strukturierte Expertenlösung je
Vignette zu entwerfen, um die **inhaltliche Diagnosequalität** der Studierenden auszuwerten, geht
über den Zuschnitt dieses Papers hinaus – sie führt zur nächsten Studie, nicht zu dieser.

Bemerkenswert ist aber: Das Tool hat dafür bereits einen Platz. Die **Referenzdiagnose** ist laut
`CONTEXT.md` genau das – die fachdidaktische Notiz der Autor:in zum Fehlermuster, optional und ohne
Wirkung auf den Ablauf. Für das Paper ist das eine gute halbe Zeile im Ausblick: Die Architektur
sieht den Anschluss an eine Auswertung der Diagnosegüte bereits vor.
