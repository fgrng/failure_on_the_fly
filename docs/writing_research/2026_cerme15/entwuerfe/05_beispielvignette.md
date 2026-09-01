# Abschnitt 5: Failure on the Fly, mit Beispielvignette und Gesprächsauszug (Entwurf)

Stand 2026-09-01. Oben die Textfassung, darunter das Artefakt und der Apparat. Die Vignette folgt
dem Datenmodell aus `CONTEXT.md`, damit sie ohne Umbau ins Werkzeug übernommen werden kann.

## Textfassung

> **Failure on the Fly**
>
> Failure on the Fly is a web application in which a participant holds a diagnostic conversation
> with a simulated student. A session opens with a framing narrative. The participant is visiting a
> class, an experienced teacher introduces the situation, and the participant then sits down with
> one student. The narrative situates the conversation, and without that situating the
> approximation to practice does not hold. Every vignette specifies exactly one error pattern and
> holds it fixed, so the diagnostic object is the same for every participant. That is what makes a
> vignette an instrument rather than a case. Each
> vignette also carries a task context, a learning task and the student's exercise book, so the
> conversation starts from work already done, as it does in a classroom. A turn limit ends the
> conversation and we do not show participants how much of it is left, which keeps a measured
> amount of the pressure of the real situation. The session closes with a debrief in which the
> experienced teacher asks for a diagnostic account. We record that account and do not score it,
> which keeps the format a rehearsal rather than a test. The simulation core is subject-agnostic.
> The mathematics sits in the vignette.
>
> One of the [N] vignettes may stand for the rest. Lea is in grade 8. She has worked on two
> boxplots showing the heights of the players in two basketball teams of 20 players each, shown in
> Figure 1. She was asked which team has the greater range, how many players in Team B are taller
> than 1.98 m, and in which team more players lie between the lower and the upper quartile. She
> gives the range correctly. She answers the other two from the size of the box, about three
> players above 1.98 m because the whisker above the box is short, and Team B for the last question
> because its box is wide. Lea reads frequency from area. Heursen et al. (2025) describe this error
> as an incomplete conceptual change from bar and pie charts, where area is indeed proportional to
> frequency, to the boxplot, which is a density display whose box holds the middle 50% whatever its
> width. Lea reads all five summary values correctly and can state the definition of a quartile.
> The error surfaces only when someone asks how many, which is what makes the vignette a diagnostic
> task and not a puzzle.
>
> The exchange below is one we wrote to show what the vignette specifies. It is not a record of a
> session, and no participant has yet played this vignette. P marks the participant and S the
> simulated student. We wrote it in German, the language of the study, and have translated it here.
> The German original is available from the authors.
>
> **P** How many players lie between the lower and the upper quartile?
>
> **S** For Team B about 14 or 15. The box takes up almost everything. For Team A more like eight.
>
> **P** You just said quartile. What is a quartile again?
>
> **S** A quarter. At the lower quartile a quarter is below it, and at the upper one a quarter is
> above.
>
> **P** If a quarter lies below the lower quartile and a quarter above the upper one, how many lie
> in between?
>
> **S** Then it would be half. But the box for Team A is much narrower, so there cannot be as many
> in it as for Team B. I think half is right when the box is normally wide. For Team B it is wider,
> so there are more.
>
> A static case would have shown the written work and the two wrong answers. It could not have
> shown the third turn, in which Lea states the definition of a quartile correctly and keeps her
> area rule anyway. That turn exists only because the participant asked for the definition, and a
> fixed case has no way of offering it, whoever reads it.

Dazu die Abbildung mit dem Titel darunter, Stil `FigTitle`, ohne Schlusspunkt:

> Figure 1: Heights of the players in two basketball teams

### Umfang

660 Wörter, davon etwa 538 Fließtext und 122 Gesprächsauszug. Aufgeteilt auf die drei Bestandteile:

| Bestandteil | geschätzt |
|---|---|
| Fließtext, vier Absätze im Stil `Normal` | 1,0 Seite |
| Gesprächsauszug, sechs Beiträge im Stil `Transcript` | 0,3 Seiten |
| Abbildung mit Titel | 0,25 Seiten |
| **Summe** | **1,55 Seiten** |

Veranschlagt waren 1,5 Seiten. Die Überschreitung liegt damit bei 0,05 statt der 0,25, die vor dem
Schreiben zu befürchten waren. Der Abschnitt ist bewusst knapper gehalten als die zuvor
geschriebenen; die Begründungstabelle aus `02_konzept.md` Schritt 4 steckt vollständig im ersten
Absatz, aber je Designelement nur in einem Halbsatz.

Wenn doch gekürzt werden muss, ist der erste Absatz die einzige Stelle mit Spielraum. Die
Übertragbarkeit („The simulation core is subject-agnostic. The mathematics sits in the vignette.")
ist der schwächste der sechs Begründungspunkte, weil sie für die Forschungsfrage nichts leistet.
Sie kostet 14 Wörter. Alles Übrige im Abschnitt trägt entweder den mathematischen Inhalt, den TWG18
vorangestellt sehen will, oder das Argument aus den Abschnitten 3 und 4.

## Vorbemerkung, die nicht übergangen werden darf

**Der Gesprächsverlauf unten ist konstruiert und stammt nicht aus einem Durchlauf des Werkzeugs.**
Ich habe ihn geschrieben, nicht erhoben.

**Entschieden am 2026-09-01: Er wird im Paper als konstruiert gekennzeichnet.** Die Kennzeichnung
steht unten im Abschnitt „Auszug für das Paper" und ist Teil des Textes, nicht eine Fußnote und
keine Randbemerkung. Sie steht vor dem Auszug, weil eine Kennzeichnung danach zu spät kommt: Wer
den Auszug liest und ihn für eine Aufzeichnung hält, hat den falschen Eindruck bereits gewonnen.

Was das kostet und was es nicht kostet. Der Auszug zeigt jetzt, was das Werkzeug tun soll, und
nicht, was es tut. An der Stelle des fehlenden Ergebnisteils ist er dadurch schwächer. Die Aussage
über die Kontingenz bleibt tragfähig, weil sie eine Eigenschaft des Formats ist: Dass eine andere
Frage eine andere Antwort erzeugt und ein fixierter Fall diese Antwort gar nicht anbieten kann, ist
unabhängig davon, ob dieser konkrete Verlauf gespielt wurde. Der Text unten formuliert genau diese
Grenze und behauptet nichts darüber hinaus.

Sobald die Vignette einmal im Werkzeug gespielt ist, ist der Tausch gegen einen echten Verlauf eine
Sache von Minuten. Die finale Fassung ist erst am 12.12.2026 fällig. Bis dahin ist das die
lohnendste kleine Verbesserung am ganzen Paper.

## Warum dieser Fehler

Heursen et al. (2025) beschreiben drei systematische Fehler bei der Interpretation statistischer
Graphen. Ich habe den dritten gewählt, „Größere Fläche bedeutet größere Häufigkeit" bei Boxplots
(S. 7f.).

**Klassenstufe passt.** Boxplots werden nach den curricularen Vorgaben in den Klassen 7/8
eingeführt (Heursen et al., 2025, S. 4). Die Studie befragt Studierende des
Sekundarschullehramts. Die beiden anderen Fehler sitzen an Histogrammen, und die kommen erst in
Klasse 10 oder in der Sekundarstufe II.

**Der Fehler trägt ein Gespräch.** Er ist eine Regel, keine Wissenslücke, und lässt sich auf jede
Nachfrage nach einer Anzahl anwenden: auf die Box, auf die Antennen und auf den Vergleich zweier
Boxplots. Genau das braucht eine simulierte Schüler:in, die ihr Fehlermuster konsequent anwendet.

**Er ist unter der Oberfläche versteckt.** Die Schülerin liest Minimum, Quartile, Median und
Maximum korrekt ab und benennt sie richtig. Sie kann sogar die Definition des Quartils aufsagen.
Der Fehler zeigt sich erst, wenn nach einer Häufigkeit gefragt wird. Eine Teilnehmer:in, die nur
das Arbeitsheft liest, hält das für einen Flüchtigkeitsfehler. Wer nachfragt, findet die Regel.
Das ist der Grund, warum diese Vignette das Argument der Abschnitte 3 und 4 trägt und nicht nur
illustriert.

**Er hat eine theoretische Anbindung, die schon im Paper steht.** Heursen et al. führen ihn auf
einen nicht vollzogenen Grundvorstellungsumbruch von Säulen- und Kreisdiagrammen zurück, wo mehr
Fläche tatsächlich mehr Häufigkeit bedeutet, hin zum Boxplot, der ein Dichtegraph ist (S. 7f.).
Sie stützen sich dabei auf die Conceptual-Change-Theorie und zitieren Vamvakoussi et al. (2013)
und Prediger (2008), die beide ohnehin in Notebook A liegen und für Abschnitt 2 vorgesehen sind.

## Die Vignette

Aufbau nach `CONTEXT.md`. Die Rahmenhandlung fehlt hier, weil sie zum Simulationskern gehört und
nicht zur Vignette.

### Unterrichtskontext

- **Unterrichtsfach:** Mathematik
- **Unterrichtsthema:** Boxplots und Datenverteilungen
- **Klassenstufe:** 8

### Fehlermuster

Lea liest Häufigkeiten aus der Fläche des Boxplots ab. Je mehr Platz ein Abschnitt des Boxplots
einnimmt, desto mehr Datenpunkte vermutet sie darin. Sie wendet diese Regel auf die Box, auf beide
Antennen und auf den Vergleich zweier Boxplots gleichermaßen an.

Die Regel greift ausschließlich bei Fragen nach einer Anzahl oder einem Anteil. Kennzahlen liest
Lea korrekt ab, benennt sie mit den richtigen Begriffen und rechnet mit ihnen fehlerfrei. Sie kennt
auch die Definition des Quartils und kann sie auf Nachfrage wiedergeben. Den Widerspruch zwischen
dieser Definition und ihrer Flächenregel bemerkt sie nicht von selbst.

### Aufgabenkontext, Lernauftrag

**Text:**

> Die Boxplots zeigen die Körpergrößen der Spielerinnen zweier Basketballteams. Beide Teams haben
> 20 Spielerinnen.
>
> [bild]
>
> a) Welches Team hat die größere Spannweite der Körpergrößen?
> b) Wie viele Spielerinnen von Team B sind größer als 1,98 m? Begründe deine Antwort.
> c) In welchem Team liegen mehr Spielerinnen zwischen dem unteren und dem oberen Quartil?
>    Begründe deine Antwort.

**Bildbeschreibung:**

> Zwei waagerechte Boxplots übereinander auf einer gemeinsamen Achse von 1,65 m bis 2,10 m.
>
> Team A, oben: Minimum 1,72 m, unteres Quartil 1,80 m, Median 1,86 m, oberes Quartil 1,92 m,
> Maximum 2,05 m. Die Box ist schmal, die obere Antenne ist lang.
>
> Team B, unten: Minimum 1,70 m, unteres Quartil 1,76 m, Median 1,86 m, oberes Quartil 1,98 m,
> Maximum 2,02 m. Die Box ist breit, die obere Antenne ist kurz.
>
> Beide Boxplots haben denselben Median.

**Simulationshinweise** (erreichen die Teilnehmer:in nicht):

> Die richtigen Antworten lauten: a) Team A, Spannweite 0,33 m gegenüber 0,32 m. b) Fünf
> Spielerinnen, weil 1,98 m das obere Quartil ist und darüber ein Viertel von 20 liegt. c) In
> beiden Teams gleich viele, nämlich je zehn, weil zwischen den Quartilen immer die Hälfte der
> Daten liegt.
>
> Lea hat a) richtig gelöst und b) und c) nach ihrer Flächenregel beantwortet. Sie hält an dieser
> Regel fest. Wird sie auf den Widerspruch zur Quartilsdefinition gestoßen, gibt sie die Regel
> nicht auf, sondern baut sich eine Zwischenerklärung, die beides zusammenbringen soll, etwa dass
> die Hälfte gilt, solange die Box normal breit ist. Sie korrigiert sich nie von selbst und nennt
> ihre Regel nie als Regel, sondern begründet immer am konkreten Bild.
>
> Sie spricht wie eine Achtklässlerin, in kurzen Sätzen, ohne Fachjargon über das hinaus, was im
> Unterricht vorkam. Sie ist zugewandt und antwortet bereitwillig. Sie stellt keine Gegenfragen,
> außer wenn sie eine Frage nicht versteht.

### Aufgabenkontext, Arbeitsheft

**Text:**

> a) Team A: 2,05 − 1,72 = 0,33. Team B: 2,02 − 1,70 = 0,32. Team A hat die größere Spannweite.
>
> b) Ungefähr 3. Über der Box ist nur noch ein kurzes Stück, da ist kaum Platz.
>
> c) Team B, weil die Box von Team B viel breiter ist als die von Team A. Da passen mehr rein.

**Simulationshinweise:**

> Das Arbeitsheft ist Leas eigene Bearbeitung von vorhin. Sie erinnert sich daran und steht dazu.

### Referenzdiagnose

> Lea vollzieht den Grundvorstellungsumbruch vom Säulen- und Kreisdiagramm zum Boxplot nicht. Dort
> ist die Fläche proportional zur Häufigkeit, und diese Vorstellung trägt. Der Boxplot ist dagegen
> ein Dichtegraph, in dem die Box unabhängig von ihrer Größe immer die mittleren 50 % umfasst. Die
> übertragene Vorstellung erzeugt einen systematischen Fehler, keinen Flüchtigkeitsfehler (Heursen
> et al., 2025, S. 7f.).
>
> Diagnostisch entscheidend ist, dass Leas Ablesen der Kennzahlen intakt ist. Wer nur das
> Arbeitsheft sieht, kann den Fehler für Ungenauigkeit halten. Erkennbar wird er erst, wenn nach
> einer Anzahl gefragt und die Begründung erfragt wird.

### Gesprächsbudget

Zwölf Gesprächsschritte. Das reicht für die Elizitierung, ohne dass die Teilnehmer:in die Regel
beiläufig findet.

## Gesprächsverlauf

Konstruiert, siehe Vorbemerkung. P ist die Teilnehmer:in, S ist Lea. Sechs Gesprächsschritte.

**P1** Hallo Lea. Ich habe mir deine Lösung angeschaut. Magst du mir erklären, wie du bei c) auf
Team B gekommen bist?

**S1** Ja klar. Die Box von Team B geht von 1,76 bis 1,98, die ist richtig breit. Bei Team A geht
sie nur von 1,80 bis 1,92. Wo mehr Platz ist, passen auch mehr Spielerinnen rein. Deswegen Team B.

**P2** Was zeigt die Box in einem Boxplot denn an?

**S2** Wo die mittleren Spielerinnen liegen. Das untere Quartil ist bei 1,76 und das obere bei
1,98, und dazwischen ist die Box.

**P3** Wie viele Spielerinnen liegen denn zwischen dem unteren und dem oberen Quartil?

**S3** Bei Team B so vierzehn oder fünfzehn. Die Box nimmt ja fast alles ein. Bei Team A eher acht.

**P4** Du hast gerade Quartil gesagt. Was ist noch mal ein Quartil?

**S4** Ein Viertel. Beim unteren Quartil liegt ein Viertel drunter und beim oberen ein Viertel
drüber.

**P5** Wenn unter dem unteren Quartil ein Viertel liegt und über dem oberen auch, wie viele liegen
dann dazwischen?

**S5** Dann wäre das die Hälfte. Aber bei Team A ist die Box doch viel schmaler, da können nicht
gleich viele drin sein wie bei Team B. Ich glaube, die Hälfte stimmt, wenn die Box normal breit
ist. Bei Team B ist sie breiter, also sind es mehr.

**P6** Und bei b), wie kommst du auf ungefähr 3?

**S6** Über der Box ist nur noch ein kurzes Stück bis 2,02. Da ist wenig Platz, also nur ein paar.
Bei Team A geht der Strich viel weiter, bis 2,05, da wären es mehr.

### Was der Verlauf zeigt

S1 bis S3 hätte auch ein statischer Fall geliefert, denn die Regel steht schon im Arbeitsheft.
S4 und S5 nicht. Dort sagt Lea die Quartilsdefinition korrekt auf und hält trotzdem an der
Flächenregel fest, und sie baut in S5 die synthetische Vorstellung, die Heursen et al. theoretisch
beschreiben. Dieser Schritt existiert nur, weil P4 danach gefragt hat. Eine andere Teilnehmer:in
hätte an dieser Stelle etwas anderes gefragt und etwas anderes zu sehen bekommen. Das ist die
Kontingenz, die Abschnitt 2 als konstitutiv für On-the-Fly-Assessment beschreibt, und der Grund,
warum der Auszug im Paper an der Stelle steht, an der sonst Ergebnisse stünden.

### Anmerkungen zum Auszug

Der Auszug steht oben in der Textfassung. Übernommen sind drei Gesprächsschritte, P3 bis S5. Sie
tragen die Pointe allein, und mehr passt nicht ins Budget. Der einleitende Absatz gehört zum Auszug
und darf nicht von ihm getrennt werden.

Der Schlussabsatz sagt, was der Auszug leistet, und bleibt dabei innerhalb dessen, was ein
konstruierter Verlauf hergibt. Er behauptet nichts über das Verhalten des Werkzeugs in einem
Durchlauf, sondern über die Bauart des Formats, und das ist genau die Aussage, die die Abschnitte 3
und 4 brauchen. „Could not have shown" statt „would not have shown" ist Absicht: Der statische Fall
kann diesen Gesprächsschritt nicht anbieten, er hat ihn nicht bloß zufällig nicht.

Acht Zeilen im Stil `Transcript` mit hängendem Einzug, dazu die beiden Rahmenabsätze im Stil
`Normal`. Grob 0,4 Seiten.

**Entschieden am 2026-09-01: nur die Übersetzung, kein zweispaltiges Original.** Das ist eine
bewusste Abweichung vom Template, das für Übersetzungen zwei Spalten neben dem Original verlangt.
Sie spart gut 0,2 Seiten, die im Budget nicht vorhanden sind.

Das Risiko halte ich für klein. Die Desk-Reject-Drohung im Call zielt auf Layout- und
Formatverstöße, also Schriftart, Ränder, Stile, Umfang. Der Auszug steht im vorgeschriebenen Stil
`Transcript`, ist als Übersetzung gekennzeichnet und lässt nur die zweite Spalte weg. Ein
übersetzter Gesprächsauszug ohne Paralleltext ist bei CERME zudem gängig.

Zur Absicherung nennt der Rahmenabsatz die Erhebungssprache und bietet das Original an. Das kostet
einen halben Satz und nimmt der Abweichung die Spitze. Eine Fußnote mit dem deutschen Wortlaut
wäre die template-nähere Lösung, kostet aber wieder rund 0,1 Seiten und lohnt den Aufwand nicht.

## Folgen für den Rest des Papers

**Erledigt am 2026-09-01.** Der Inhaltsbereich ist auf beschreibende Statistik festgelegt, und die
abhängigen Stellen sind nachgezogen.

- `02_konzept.md` Punkt 6a trägt jetzt die Entscheidung samt Begründung statt der überholten
  Empfehlung für Arithmetik.
- `02_konzept.md` Abschnitt 7, Literaturzuordnung: Heursen et al. 2025 trägt den Inhaltsbereich.
  Vamvakoussi et al. 2013 und Prediger 2008 rutschen nach Abschnitt 2, weil Heursen et al. sich
  selbst auf beide stützen und eine Doppelung zu vermeiden ist.
- `02_konzept.md` Abschnitt 4, Seitenbudget: die Boxplot-Abbildung ist als zusätzlicher Posten von
  etwa 0,25 Seiten in Abschnitt 5 vermerkt, Gegenfinanzierung in Abschnitt 4.
- `entwuerfe/07_studiendesign.md`: der Satz zur Reichweite lautet jetzt „among them descriptive
  statistics as well as arithmetic". Der Abschnitt ist damit 580 Wörter lang.

**Ein Hinweis zum offenen Review.** Ayline Heursen und Markus Vogel sind an der PH Heidelberg, also
an einem der beiden Erhebungsstandorte, ebenso wie Marita Friesen, die die TWG18 leitet und bei
Wirth et al. (2023) Ko-Autorin ist. Das spricht nicht gegen die Wahl, im Gegenteil. Es heißt nur,
dass die Zuschreibungen an diese Arbeiten besonders genau sitzen müssen.

## Literaturangabe

```
Heursen, A., Schreiter, S., & Vogel, M. (2025). Mit neuem Blick auf Statistik: Conceptual Change
    und systematische Fehler bei der Interpretation statistischer Graphen [A new look at
    statistics: Conceptual change and systematic errors in the interpretation of statistical
    graphs]. mathematica didactica, 48, 1–11.
```

Zu klären: ob *mathematica didactica* für diesen Jahrgang DOIs vergibt. Das Template verlangt den
DOI als volle URL, wo einer existiert. Im PDF steht als Kolumnentitel nur „math.did. 48(2025)",
eine Heftnummer ist nicht erkennbar. Vor der Einreichung an der Zeitschriftenseite prüfen.

## Offene Punkte

1. **Wird die Abbildung selbst gezeichnet?** Der Boxplot muss ins Paper, sonst ist der Auszug nicht
   lesbar. Als Abbildung mit Titel darunter, Stil `FigTitle`, kostet etwa 0,25 Seiten. Das drückt
   Abschnitt 5 über die veranschlagten 1,5 Seiten, Gegenfinanzierung wäre Abschnitt 4.
2. **Zahlen gegenprüfen.** Ich habe die fünf Kennzahlen je Team so gewählt, dass die Flächenregel
   in b) und c) zu falschen und in a) zu richtigen Antworten führt. Vor dem Anlegen im Werkzeug
   einmal nachrechnen.
3. **Vor dem 12.12.2026 die Vignette einmal spielen.** Kein Blocker für die Einreichung, aber der
   Tausch des konstruierten Auszugs gegen einen echten Verlauf ist die lohnendste kleine
   Verbesserung am Paper. Er macht aus einer Absichtserklärung eine Demonstration und kostet nur
   den einen Rahmenabsatz.


## Nachtrag 2026-09-01: Umformulierung nach Abschnitt 4

Der Satz zum Fehlermuster lautete: „Every vignette specifies exactly one error pattern, which the
simulated student applies consistently, so the diagnostic object is fixed and is the same for every
participant."

Er lautet jetzt: „Every vignette specifies exactly one error pattern and holds it fixed, so the
diagnostic object is the same for every participant."

**Grund.** Die Quellenprüfung für Abschnitt 4 hat fünf unabhängige Arbeiten ergeben, die berichten,
dass ein Sprachmodell die gespielte Fehlvorstellung aufgibt, sobald jemand nachfragt (Kortenkamp &
Larkin, 2026; Martynova et al., 2025; Chen et al., 2026; Wang et al., 2026; Liu et al., 2026).
„applies consistently" behauptete damit als Designeigenschaft, was Abschnitt 4 zwei Seiten vorher als
offen einräumt. Die neue Fassung sagt, was die Vignette festlegt, und nicht, was das Modell tut.
Begründung vollständig in `entwuerfe/04_simulierte.md`.

**Nebeneffekt.** Der Satz ist 13 Wörter kürzer, und die Doppelung von „fixed" ist weg. Die
Umfangsangaben unten sind um diese 13 Wörter zu hoch; der Abschnitt liegt jetzt bei etwa
1,53 statt 1,55 Seiten.

**Was offen bleibt.** Wenn der Simulationskern mehr tut, als das Fehlermuster in den Prompt zu
schreiben, wäre ein Halbsatz dazu die stärkste verfügbare Antwort auf die Gegenbefunde in
Abschnitt 4. Das ist eine Frage an den Autor und kostet Platz, den dieser Abschnitt nicht hat.
