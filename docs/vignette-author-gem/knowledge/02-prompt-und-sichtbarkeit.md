# Wie der Simulationskern die Felder nutzt

Damit du die Felder richtig formulierst, musst du wissen, **was die App zur
Laufzeit damit macht**. Verhalten und Denken der simulierten Schüler:in stehen
im **Simulationskern**: der zentralen, fach-agnostischen Verhaltensspezifikation
aus System-Prompt-Vorlage, User-Prompt-Vorlage und Rahmenhandlung. Es gibt genau
eine Kern-Historie für alle Vignetten und alle Fächer. Autor:innen schreiben den
Kern nicht; sie liefern nur die Inhaltsfelder ihrer Vignette.

Jede Vignettenfassung **pinnt** genau eine finale Kern-Fassung und spielt für
immer gegen diese. Ein Entwurf lässt sich per **Vorspulen** auf den aktuellsten
Kern heben.

## Der Vertrag: acht promptrelevante Felder

Die Vorlagen sind `string.Template`-Texte mit `$platzhalter`. Der Vertrag
zwischen Vignette und Prompt-Vorlagen ist fest und in `simulation/models.py` als
`VERTRAG_PROMPT` erzwungen — eine Kern-Fassung mit anderen Platzhaltern lässt
sich nicht finalisieren. **Genau diese acht Felder** erreichen den Prompt:

| Platzhalter | Editor-Feld |
| :--- | :--- |
| `$fehlermuster_beschreibung` | Fehlermuster Beschreibung |
| `$lernauftrag` | Lernauftrag |
| `$arbeitsheft_beschreibung` | Arbeitsheft Beschreibung |
| `$schuelerin_name` | Schüler:in Vorname |
| `$schuelerin_geschlecht` | Schüler:in Geschlecht |
| `$fach` | Fach |
| `$thema` | Thema |
| `$klassenstufe` | Klassenstufe |

Alles andere erreicht den Prompt **nie**: Lehrperson (Name, Geschlecht),
Arbeitsheft-Text, Arbeitsheft-Bild, Referenzdiagnose, Budget-Typ und Budget-Wert.

## Was der System-Prompt aus deinen Feldern baut

Die System-Prompt-Vorlage des Standardkerns setzt Name, Geschlecht,
Klassenstufe, Fach und Thema in einen Identitätssatz ein („Du bist …“) und
stellt die **Fehlermuster-Beschreibung** in den Abschnitt „deine Denkweise“.
Anschließend folgen — systemweit konstant und für alle Vignetten identisch —
die Vorgaben:

- Die Denkweise ist keine Rolle und kein Fehler, den die simulierte Schüler:in
  kennt; ihre Bearbeitung ist so entstanden. Den fachlich richtigen Weg kennt
  sie nicht und kann ihn im Gespräch nicht herleiten.
- Sie spricht nie über ihre Denkweise als Regel, sondern nur über die konkreten
  Zahlen, Wörter oder Dinge ihrer Aufgabe.
- Fehlermuster-Beschreibung und Simulationshinweise dürfen in der Du-Form, in
  der dritten Person oder abstrakt formuliert sein; der Kern liest jede Form
  als Beschreibung der Schüler:in selbst. Simulationshinweise gehen im
  Einzelfall vor.
- **Auskunftsleiter:** Auf eine offene Frage nennt sie nur, was sie
  hingeschrieben hat; das Wie erklärt sie erst auf die Frage nach dem Wie, das
  Warum erst auf die Frage nach dem Warum. Ungefragte Schritte bleiben
  ungesagt. Sie stellt keine Rückfragen, die das Gesprächsbudget kosten.
- **Reaktionsleiter:** Bei bloßem Zweifel bleibt sie bei ihrem Ergebnis. Bei
  einem Gegenbeispiel wendet sie ihre Denkweise darauf an und ist eher
  verwirrt als einsichtig. Wird ihr der richtige Weg vorgeführt, hört sie
  höflich zu und fällt beim nächsten eigenen Beispiel in ihre Denkweise zurück.
- Sie spricht altersgemäß und mündlich, kennt keine fachdidaktischen Begriffe,
  erfindet nichts über den Arbeitskontext hinaus und verlässt die Rolle nicht.
- Sie erzeugt zu jeder Antwort eine **Denkspur** (ihr Mitdenken in der
  Ich-Form, zwei bis vier Sätze) getrennt von der sichtbaren **Äußerung**. Die
  Denkspur wird nie verraten.

**Konsequenz für dich:** Weil die Denkweise generativ angewandt wird, muss die
Fehlermuster-Beschreibung eine **anwendbare Regel** sein, kein Etikett. Je
mechanistischer sie ist, desto konsistenter simuliert die App neue Fälle. Und
weil Tonfall, Auskunftsverhalten und Hartnäckigkeit bereits systemweit gesetzt
sind, brauchst du keine Persona-Anweisungen zu schreiben — was du an Persona
brauchst, gehört eingebettet in die Fehlermuster-Beschreibung oder in die
Simulationshinweise.

## Was der User-Prompt aus deinen Feldern baut

Die User-Prompt-Vorlage liefert den Arbeitskontext: den **Lernauftrag** und
das **Arbeitsheft**, jeweils als Text mit Bildbeschreibung an der Bildposition,
und direkt darunter die jeweiligen **Simulationshinweise**, falls vorhanden.
Sie schließt mit der Anweisung, auf die kommende Ansprache mit Denkspur und
Äußerung zu antworten.

**Konsequenz für dich:** Was nicht im Lernauftrag, im Arbeitsheft oder in den
Simulationshinweisen steht, existiert für die simulierte Schüler:in nicht.
Wenn ein Bild die Bearbeitung trägt, muss die Arbeitsheft-Bildbeschreibung sie
vollständig in Worte fassen — sonst kann die Simulation ihre eigene Bearbeitung
nicht erklären.

## Die Rahmenhandlung

Die Rahmenhandlung wird ausschließlich der Teilnehmer:in angezeigt und erreicht
keinen Prompt. Sie besteht aus drei Abschnitten des Simulationskerns:

- **Hospitationseinleitung** — führt die Hospitationssituation und die erfahrene
  Lehrperson ein.
- **Gesprächseinleitung** — führt die Begegnung mit der simulierten Schüler:in
  unmittelbar vor dem Diagnosegespräch ein.
- **Debrief** — hier bittet die erfahrene Lehrperson nach dem Diagnosegespräch um
  die Diagnose.

Ihr Platzhaltervertrag (`VERTRAG_RAHMEN`) ist weiter als der Prompt-Vertrag: Er
umfasst zusätzlich Name und Geschlecht der Lehrperson sowie die daraus
abgeleiteten Grammatikformen `$schuelerin_pronomen`, `$schuelerin_possessiv`,
`$lehrperson_pronomen`, `$lehrperson_possessiv` und `$lehrperson_anrede`
(„Frau“/„Herr“). Deshalb genügen für die Lehrperson Nachname und Geschlecht —
die Anrede entsteht automatisch.

Die Illustrationen der Rahmenhandlung wählen sich ebenfalls aus den beiden
Geschlechtsfeldern.

## Teilnehmendensichtbarkeit

Was Teilnehmende sehen, ist systemweit fest und nicht pro Vignette einstellbar:

- **Während der ganzen Sitzung im Aufgabenkontext:** der **Lernauftrag**, der
  Vorname der simulierten Schüler:in und der **Arbeitsheft-Inhalt** — das Bild,
  wenn eines hochgeladen ist, sonst der Arbeitsheft-Text.
- **In der Rahmenhandlung:** die Namen und Geschlechter beider Akteurinnen, Fach,
  Thema und Klassenstufe, soweit die Kern-Vorlagen sie einsetzen.
- **Nie sichtbar:** Fehlermuster-Beschreibung, Arbeitsheft-Beschreibung (außer
  als Alt-Text des Bildes), Referenzdiagnose, Gesprächsbudget, Denkspur.

Die Denkspur ist nur im **Probelauf** der Autor:in live sichtbar; in Trainings
und Erhebungen wird sie gespeichert, aber nicht angezeigt.

**Wichtig:** Sichtbare Felder — vor allem der Lernauftrag und der
Arbeitsheft-Text — dürfen das Fehlermuster **nicht benennen und nicht
erklären**. Das Aufdecken ist ja die Übung. Die fachdidaktische Benennung gehört
in die Fehlermuster-Beschreibung (fürs Modell) und in die Referenzdiagnose (für
die Autor:in).

## Das Gesprächsbudget

Budget-Typ und Budget-Wert bestimmen, wann das Diagnosegespräch endet und der
Debrief folgt: nach so vielen **Gesprächsschritten** oder nach so vielen
**Sekunden**. Der Teilnehmer:in wird das Budget nicht angezeigt. Für dich heißt
das: Das Fehlermuster muss in wenigen Gesprächsschritten aufdeckbar sein.
