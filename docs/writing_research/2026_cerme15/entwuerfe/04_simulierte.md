# Abschnitt 4: Simulated students (Entwurf)

Stand 2026-09-01. Dritter und kürzester Theorieabschnitt. Der Textteil unten folgt den Stilregeln
aus `04_handoff_methodenteil.md`, der Apparat darunter nicht.

## Textfassung

> **Simulated students**
>
> Heitzmann et al. (2019) define the kind of simulation that matters here. It is a learning
> environment in which a segment of reality is presented so that diagnostic activities become
> possible, and in which "learners' actions influence the further development of the system" (p. 9).
> The second condition is the one Section 3 found missing, and it is what makes a simulation an
> approximation rather than a representation (p. 9).
>
> Simulated classrooms are not new in teacher education. Fischer et al. (2021) had pre-service
> biology teachers put questions to virtual students who answered according to a preset ability
> profile. Their participants judged whether an answer was scientifically correct in 91% of cases and
> identified the specific misconception behind it in 59%. Naming the misconception is the harder
> half, and it is the half a conversation is for. What a preset profile cannot do is answer a
> question nobody anticipated.
>
> A language model can. It can also be told which error to make, so that the diagnostic object stays
> the same across participants, which is the control Section 3 found approximations lacking. Holding
> both halves at once is the claim, and the evidence for it is mixed.
>
> The relevant evidence is discouraging. Kortenkamp and Larkin (2026) had a language
> model solve mathematics word problems and found that its wrong answers did resemble students'
> answers. When they then intervened as a teacher would, the pedagogically specific prompts were
> routinely ignored while a content-free "Are you sure?" worked. They conclude that a model may be
> suited to modelling the solutions students produce and much less to modelling how students respond
> to instruction. Martynova et al. (2025) had teachers tutor simulated students and found them too
> ready to agree, giving up an approach as soon as it was questioned, where a real student digs in.
> Chen et al. (2026) put a number on the gap. Across nine models, accuracy fell from 66% on solving
> mathematics problems to 40% on predicting what a student holding a given misconception would answer
> next.
>
> That gap sits exactly where a diagnostic conversation lives. The error has to survive being
> questioned, and being questioned is what these studies find the simulation does not survive. Two
> things follow for the design. The error pattern belongs in the vignette and not in a prompt written
> on the day, and holding it is an engineering problem rather than a matter of asking politely.
> Whether it can be held well enough for pre-service teachers to accept the counterpart is not
> something argument can settle.

### Umfang

423 Wörter, 2587 Zeichen, nach dem üblichen Verfahren 2623 gesetzte Zeichen,
29 Zeilen, also 0.75 Seiten. Veranschlagt sind 0,75 Seiten. Der Abschnitt liegt
darauf.

Streichkandidat, falls doch gekürzt werden muss, ist der Satz zu Chen et al. (2026). Er spart
50 Wörter und 0,09 Seiten. Inhaltlich ist er der schwächste der drei Belege im Absatz, weil er eine
Zahl liefert, wo die beiden anderen einen Mechanismus liefern.

## Was der Abschnitt leistet, und warum er anders ausgefallen ist als geplant

`02_konzept.md`, Schritt 3, sah vier Potenziale vor: Responsivität, kontrollierte Varianz,
Wiederholbarkeit, Skalierbarkeit. Der Entwurf nennt die ersten beiden und lässt die anderen beiden
weg. Der Grund ist die Quellenlage.

**Die Volltextprüfung hat weitgehend das Gegenteil dessen ergeben, was die Planung erwartete.** Fünf
unabhängige Arbeiten in Notebook B berichten denselben Befund: Ein Sprachmodell, das eine Schüler:in
mit einer Fehlvorstellung spielen soll, gibt die Fehlvorstellung auf, sobald jemand nachfragt. Genau
das ist der Moment, von dem Failure on the Fly lebt.

Ein Abschnitt, der bei dieser Lage vier Potenziale aufzählt und die Befunde verschweigt, wäre bei
einem offenen Review nicht zu halten. Kortenkamp und Larkin (2026) stehen in ZDM, die Arbeitsgruppe
kennt sie. Der Abschnitt zählt deshalb zwei Potenziale auf, stellt die Gegenbefunde daneben und
leitet daraus eine Designanforderung und die Forschungsfrage ab. Das ist schwächer als geplant und
belastbarer.

Wiederholbarkeit und Skalierbarkeit sind damit nicht verloren. Sie sind Eigenschaften des Werkzeugs
und gehören nach Abschnitt 5, wo die Tabelle in `02_konzept.md` sie ohnehin verortet.

## Ein Widerspruch zu Abschnitt 5, der zu entscheiden ist

**Das ist der wichtigste offene Punkt aus dieser Arbeitseinheit.**

Die Textfassung von Abschnitt 5 (`entwuerfe/05_beispielvignette.md`) sagt: „Every vignette specifies
exactly one error pattern, which the simulated student applies consistently, so the diagnostic
object is fixed and is the same for every participant."

Nach der jetzigen Quellenlage ist „applies consistently" genau die Eigenschaft, die fünf Arbeiten
als schwer erreichbar berichten. Der Satz behauptet als Designeigenschaft, was der Forschungsstand
für offen hält, und er steht zwei Seiten hinter einem Abschnitt, der das eingeräumt hat. Ein
Gutachter, der beides liest, hat einen Treffer.

Drei mögliche Auflösungen, in der Reihenfolge meiner Empfehlung:

1. **Abschnitt 5 formuliert die Absicht statt der Wirkung.** Etwa „which the simulated student is
   instructed to apply consistently" oder „which the vignette holds fixed". Kostet nichts, ändert
   nichts am Argument und lässt den Widerspruch verschwinden. Der Auszug in Abschnitt 5 ist ohnehin
   als konstruiert gekennzeichnet, zeigt also die beabsichtigte und nicht die beobachtete Verlaufsform.
2. **Abschnitt 5 sagt in einem Halbsatz, wie das Fehlermuster gehalten wird**, falls im Werkzeug mehr
   dahintersteckt als eine Anweisung im Prompt. Das wäre die stärkste Antwort auf die Gegenbefunde,
   kostet aber Platz, den Abschnitt 5 nicht hat, und ich weiss aus den Planungsdokumenten nicht, was
   der Simulationskern tatsächlich tut. **Rückfrage an den Autor.**
3. Alles so lassen. Nicht empfohlen.

Ich habe Abschnitt 5 nicht angefasst, weil das eine inhaltliche Entscheidung über das Werkzeug ist
und keine Formulierungsfrage.

## Quellenprüfung

**Heitzmann et al. (2019).** Bestätigt und tragend. Die Definition S. 9: „a simulation is a learning
environment in which (1) a segment of reality (e.g. a professional situation) is presented in a way
which enables engagement in diagnostic activities […]. In a simulation of this type, (2) learners'
actions influence the further development of the system." Die zweite Bedingung ist wörtlich die
Lücke aus Abschnitt 3. Ebenfalls S. 9: „Going beyond representations which illustrate practice for
students, approximations enable engaging the learners with important aspects of practice", und die
Autor:innen verorten Simulationen ausdrücklich als „approximations-of-practice".

Zwei Zugaben, die nicht in den Text gepasst haben, aber notiert gehören. S. 10 zu den bestehenden
virtuellen Klassenzimmern: „the purpose of those simulations was not to foster the development of
diagnostic competences but rather to measure the learners' level of diagnostic competence." Und
S. 15: „Validation studies need to generate evidence that the simulation corresponds to the simulated
situation, at least to a certain degree." Der zweite Satz beschreibt genau das, was die geplante
Studie tut. Falls Abschnitt 6 oder 7 noch Platz findet, ist das der beste verfügbare Beleg dafür,
dass die Frage nach wahrgenommener Qualität eine anerkannte und keine ersatzweise Frage ist.

**Fischer et al. (2021).** Bestätigt. Der Simulierte Klassenraum Biologie, N = 51. Virtuelle
Schüler:innen antworten „immer bezüglich ihres voreingestellten Fähigkeitsprofils" (S. 221).
Diagnoserate für wissenschaftliche Korrektheit 91 Prozent, für die spezifische
Fehlvorstellungskategorie 59 Prozent (Zusammenfassung, S. 215). Fachdidaktisch, deutschsprachig, und
damit ein guter Beleg dafür, dass simulierte Klassenzimmer in der Lehrkräftebildung etabliert sind.

**Kortenkamp und Larkin (2026).** Bestätigt und für diesen Abschnitt die wichtigste Quelle, weil sie
in ZDM steht, mathematikdidaktisch ist und Lehramtsstudierende adressiert. Aus der Zusammenfassung:
„LLMs may be well suited to modelling students' mathematical solutions, but less suited to modelling
how students naturally respond to instructional prompts." Aus Kapitel 6.2: „the specific prompt was
usually either ignored […] We read this as evidence that the LLM does not understand either the
question or its answer: it generates a linguistic pattern and so cannot itself discern correct from
wrong." Aus Kapitel 6.3 die Deutung als affirmation bias: „the LLM appears to treat its prior token
as evidence (rather than as a hypothesis to be revised), which is the opposite of the metacognitive
move that a teacher intervention is meant to elicit in a student."

**Martynova et al. (2025).** Bestätigt. Lehrkräfte unterrichteten LLM-Schüler:innen. Zur Gefügigkeit,
S. 106: „LLM students sometimes agree too readily with the teacher, completely changing their
approach. This tendency of LLMs is called sycophancy bias". Dazu S. 104 die Aussage einer Lehrkraft,
die im Entwurf paraphrasiert ist: „a human student is not going to immediately abandon a solution
they've come up with." Weitere Befunde, im Text nicht verwendet: keine authentischen Emotionen, zu
fachsprachlich und zu ausführlich, kein Aufgeben.

**Chen et al. (2026), MalruleLib.** Bestätigt. Aus der Zusammenfassung: „Across nine language models
(4B–120B), accuracy drops from 66% on direct problem solving to 40% on cross-template misconception
prediction." Zur Ursache, Kapitel 5.1: „instruction tuning encourages models to correct
misconceptions rather than simulate them, creating a tension between being correct and behaving like
a mistaken student."

**Geprüft und nicht verwendet.** Drei weitere Arbeiten aus Notebook B stützen denselben Befund und
sind aus Platzgründen draussen. Sie stehen hier, damit sie nicht ein zweites Mal gesucht werden
müssen.

- **Wang et al. (2026), BEAGLE.** Nennt das Phänomen „competency bias", die Neigung
  präferenzoptimierter Modelle, korrekt zu antworten, auch wenn sie eine Novizin spielen sollen.
  Vanilla-Modelle wiederholen denselben Fehler nur in 7,8 Prozent der Durchläufe. Mit einer eigens
  gebauten Architektur erreichen sie in einem Turing-Test Zufallsniveau (52,8 Prozent, N = 71). Das
  ist der **stärkste positive Beleg im ganzen Notebook** und die beste Stütze für die
  Designanforderung im letzten Absatz, nämlich dass die Kontrolle architektonisch sein muss und nicht
  im Prompt. Wenn Abschnitt 4 je 30 Wörter mehr bekommt, gehören sie hierhin.
- **Liu et al. (2026).** Ein Modell, auf eine einzelne Fehlvorstellung trainiert, übergeneralisiert
  sie auf Aufgaben, wo sie nicht greift, und verliert dabei die korrekte Lösefähigkeit.
- **He-Yueya et al. (2024).** Modelle „vergessen" das begrenzte Wissen der gespielten Schüler:in,
  sobald man ihnen Lernmaterial zeigt.

**Ross und Andreas (2025) wird nicht verwendet.** Informatischer Methodenbeitrag (MISTAKE,
Zykluskonsistenz zur Erzeugung synthetischer Fehlerdaten), arXiv-Preprint. Er zeigt, dass sich die
Simulation fehlerhaften Denkens verbessern lässt, trägt aber zum Argument nichts bei, was Wang et al.
nicht besser trügen. Die Zuordnung in `02_konzept.md` ist damit erledigt.

## Literaturangaben für Abschnitt 4

```
Chen, X., Liu, N., & Sonkar, S. (2026). MalruleLib: Large-scale executable misconception reasoning
    with step traces for modeling student thinking in mathematics. In Proceedings of the 64th Annual
    Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)
    (pp. 15112–15138). Association for Computational Linguistics.
    https://doi.org/10.18653/v1/2026.acl-long.690

Fischer, J., Machts, N., Möller, J., & Harms, U. (2021). Der Simulierte Klassenraum Biologie.
    Erfassung deklarativen und prozeduralen Wissens bei Lehramtsstudierenden der Biologie [The
    simulated biology classroom. Assessing declarative and procedural knowledge in pre-service
    biology teachers]. Zeitschrift für Didaktik der Naturwissenschaften, 27(1), 215–229.
    https://doi.org/10.1007/s40573-021-00136-z

Heitzmann, N., Seidel, T., Opitz, A., Hetmanek, A., Wecker, C., Fischer, M., Ufer, S., Schmidmaier,
    R., Neuhaus, B., Siebeck, M., Stürmer, K., Obersteiner, A., Reiss, K., Girwidz, R., & Fischer,
    F. (2019). Facilitating diagnostic competences in simulations: A conceptual framework and a
    research agenda for medical and teacher education. Frontline Learning Research, 7(4), 1–24.
    https://doi.org/10.14786/flr.v7i4.384

Kortenkamp, U., & Larkin, K. (2026). LLMs as useful training tools for mathematics teachers:
    Opportunities or hallucinations? ZDM – Mathematics Education. Advance online publication.
    https://doi.org/10.1007/s11858-026-01813-4

Martynova, D., Macina, J., Daheim, N., Yalcin, N., Zhang, X., & Sachan, M. (2025). Can LLMs
    effectively simulate human learners? Teachers' insights from tutoring LLM students. In
    Proceedings of the 20th Workshop on Innovative Use of NLP for Building Educational Applications
    (pp. 100–117). Association for Computational Linguistics.
```

**Der Eintrag zu Chen et al. ist am 2026-09-01 aufgelöst.** Der Volltext in Notebook B ist der
arXiv-Preprint (arXiv:2601.03217) und trägt keinen Publikationsort. Es gibt aber eine begutachtete
Fassung in den ACL-Proceedings 2026, und der Eintrag oben folgt dieser. Zwei Folgen daraus:

- **Zitiert wird die ACL-Fassung**, nicht der Preprint. Bei einem offenen Review ist eine
  begutachtete Quelle an dieser Stelle deutlich mehr wert, weil der Satz eine Zahl gegen das eigene
  Vorhaben ins Feld führt.
- **Die Schreibweise des Titels ist „MalruleLib"**, so in der Verlagsfassung. Das PDF setzt ihn im
  Fliesstext durchgehend als „MALRULELIB", das ist Auszeichnung und nicht Orthografie.

Die Seitenangaben im Apparat oben („Zusammenfassung", „Kapitel 5.1") beziehen sich auf die
Preprint-Fassung. Der Text des Abschnitts zitiert keine Seite bei Chen et al., sondern nur den Befund
aus der Zusammenfassung, also entsteht daraus kein Problem. Wer doch eine Seite braucht, nimmt sie
aus der ACL-Fassung, Seiten 15112–15138.

Vier weitere Punkte, alle klein.

- **Der Titel von Heitzmann et al. weicht ab.** Der Volltext trägt „Facilitating diagnostic
  competences in simulations: A conceptual framework and a research agenda for medical and teacher
  education". Die Verlagsmetadaten über Scite führen „Facilitating Diagnostic Competences in
  Simulations in Higher Education A Framework and a Research Agenda". Der Eintrag oben folgt dem
  Volltext. Vor der Einreichung am PDF und an der Journalseite klären, welcher der Titel of record
  ist.
- **Heitzmann et al. hat 15 Autor:innen.** Nach APA 7 werden bis 20 alle genannt. Der Eintrag kostet
  dadurch allein rund drei Zeilen, also gut 0,07 Seiten. Das ist ein Zehntel des Abschnitts und beim
  Kürzen des Literaturverzeichnisses mitzudenken.
- **Die Initiale von Martin Fischer** ist nicht belegt; im Volltext steht nur „Martin Fischer". In
  derselben Liste steht Frank Fischer, die beiden dürfen nicht verwechselt werden. Am PDF prüfen.
- **Scite schreibt „Jens Møller"**, der Volltext „Jens Möller". Der Volltext hat recht.

## Was der Abschnitt bewusst nicht sagt

- **Kein Modellname, kein Anbieter, keine Versionsnummer.** Das Paper erscheint im Februar 2027, jede
  konkrete Modellangabe wäre dann alt. Der Abschnitt spricht durchgehend von „a language model".
- **Keine Behauptung, das Problem sei gelöst.** Der letzte Absatz formuliert eine Designanforderung
  und eine offene Frage, keine Lösung. Das ist der einzige Stand, den die Quellenlage trägt.
- **Kein Verweis auf Ethik oder Datenschutz der Simulation.** Gehört, soweit überhaupt, nach
  Abschnitt 7, wo die Schutzmaßnahmen stehen.
- **Kein Wort zu Kosten oder Skalierung.** Die Skalierbarkeit ist ein Vorzug des Werkzeugs und gehört
  nach Abschnitt 5. Hier stünde sie neben Gegenbefunden zur Tragfähigkeit und wirkte ausweichend.
