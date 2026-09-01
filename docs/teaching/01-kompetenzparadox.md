# Lektion 1: Das Kompetenzparadox

## Das Problem in einem Satz

Ein LLM, das alles weiss, soll sich verhalten wie jemand, der etwas
Bestimmtes *nicht* weiss -- und genau das geht nicht, indem man es
einfach darum bittet.

## Was ist das Kompetenzparadox?

Der Begriff stammt aus dem Survey-Paper *Towards Valid Student
Simulation with Large Language Models* (Li et al., 2025). Er beschreibt
den Kern des Problems:

> Models trained to be broadly capable, self-correcting, and prosocial
> cannot genuinely "unknow" solution schemas or expert heuristics once
> internalized. Even when prompted to act like a novice, their latent
> reasoning trajectories remain shaped by expert priors that the target
> student has not acquired.

Konkret heisst das:

1. **Irreduzibler Prior-Knowledge-Entanglement.** Das Modell hat die
   korrekte Loesung *internalisiert*. Selbst wenn der Prompt sagt "du
   kennst den richtigen Weg nicht", fliesst das korrekte Wissen in die
   Token-Wahrscheinlichkeiten ein. Die Fehler, die das Modell dann macht,
   gleichen oberflaechlichen Abweichungen vom Expertenwissen -- nicht
   stabilen, diagnose-relevanten Fehlermustern.

2. **Fluenz maskiert Invalitaet.** Die Antworten *klingen* wie
   Schueler:innen, aber die Fehlerstruktur passt nicht. Fliessendes
   Deutsch und kooperativer Tonfall verdecken, dass das Modell im
   Hintergrund das Problem korrekt loest und dann kuenstlich
   "verschlechtert".

3. **Self-Correction-Bias.** Instruktions-getunte Modelle sind darauf
   trainiert, sich selbst zu korrigieren. Genau das ist bei einer
   simulierten Schueler:in das Gegenteil des gewuenschten Verhaltens: Sie
   *soll* bei ihrem Fehler bleiben, auch unter Druck.

## Das Kompetenzparadox bei FailureOnTheFly

Unser Simulationskern adressiert Teile dieses Problems bereits -- aber
nicht alle:

| Massnahme im Kern | Adressiert | Limitation |
|---|---|---|
| "Du kennst den fachlich richtigen Loesungsweg nicht" | Self-Correction-Bias | Anweisung allein genuegt nicht (siehe Lektion 3) |
| Fehlermuster als *anwendbare Regel* | Irreduzibler Prior | Je mechanistischer die Regel, desto besser; aber das Modell kann sie trotzdem unterlaufen |
| Denkspur *vor* Aeusserung (Structured Output) | Fluenz-Maskierung | Gibt Einblick, ob das Modell wirklich aus dem Muster argumentiert |
| Denkspur fliesst nicht in den Kontext zurueck (ADR-0005) | Konsistenz | Verhindert Praezedenzfaelle aus frueheren Fehlern |
| Beispiele in der Fehlermuster-Beschreibung | Prior-Knowledge-Entanglement | Stabilisiert, aber loest das Grundproblem nicht |

## Der zentrale Denkrahmen: Constrained Generation

Li et al. schlagen vor, die Simulation nicht als "Role-Playing" zu
rahmen, sondern als *Constrained Generation*: Das Modell soll nicht frei
eine Rolle spielen, sondern Text unter exakt spezifizierten
Einschraenkungen erzeugen. Dieser Perspektivwechsel hat Konsequenzen:

- **Role-Playing-Perspektive:** "Sei eine Schueler:in mit diesem
  Fehler." -- Das Modell hat Spielraum, die Rolle zu interpretieren.
- **Constrained-Generation-Perspektive:** "Erzeuge Antworten, die
  *ausschliesslich* aus dieser Regel folgen. Wende die Regel auf jede
  Frage an. Beantworte nichts, was ausserhalb der Regel liegt." -- Der
  Spielraum ist kleiner.

Der Simulationskern von FailureOnTheFly bewegt sich bereits in Richtung
Constrained Generation (die "feste innere Regel"), liegt aber sprachlich
noch nahe am Role-Playing ("Du spielst $schuelerin_name").

## Epistemic State Specification (ESS)

Das Paper schlaegt ein Reifegradmodell fuer die Wissensspezifikation vor:

| Stufe | Name | Beschreibung |
|-------|------|--------------|
| E0 | Unspecified | Keine explizite Wissenseinschraenkung definiert |
| E1 | Static Bounded | Festes, vorab definiertes Set von Wissenselementen und Fehlerquellen; aendert sich waehrend der Interaktion nicht |
| E2 | Curriculum-Indexed | Wissen wird anhand eines externen Progressionssignals aktualisiert |
| E3 | Misconception-Structured | Verhalten wird durch ein explizites, stabiles Modell von Fehlvorstellungen kausal bestimmt |
| E4 | Calibrated/Learned | Zustandsrepraesentation und Uebergangsdynamik sind aus echten Schueler:innendaten gelernt oder kalibriert |

**FailureOnTheFly steht bei E1/E3.** Der Kern spezifiziert eine feste
innere Regel (E1: statisch, aendert sich nie), und die
Fehlermuster-Beschreibung mit ihren Beispielen definiert ein explizites
Misconception-Modell (E3). Was fehlt: eine formale Spezifikation dessen,
was die Schueler:in *ausserhalb* des Fehlermusters weiss und kann
("Named Ignorance").

## Drei gekoppelte Anforderungen

Jede valide Simulation muss drei Anforderungen gleichzeitig erfuellen:

1. **Fidelity of Error (Fehlertreue).** Das Fehlermuster muss auf
   allen relevanten Aufgabentypen konsistent angewandt werden.

2. **Epistemic Consistency (epistemische Konsistenz).** Fehler muessen
   kausal auf die beschriebene Wissensgrenze zurueckfuehrbar sein und
   ueber isomorphe Aufgaben und Gespraechsschritte hinweg stabil bleiben.

3. **Boundary of Competence (Kompetenzgrenze).** Ausserhalb des
   Fehlerbereichs muss die Schueler:in sich gemaess ihrem
   angenommenen Kompetenzniveau verhalten -- keine Experten-Abkuerzungen,
   aber auch kein zufaelliger Unsinn.

## Was bedeutet das fuer FailureOnTheFly?

### Bereits gut geloest
- Die Fehlermuster-Beschreibung als mechanistische Regel (nicht bloss
  ein Etikett) ist genau das, was die Forschung empfiehlt.
- Die Trennung Denkspur/Aeusserung gibt Forschenden eine Pruefstelle
  fuer Fehlertreue.
- Das Nicht-Zurueckfliessen der Denkspur in den Kontext verhindert
  eine bekannte Drift-Quelle.

### Offene Hebel
- **Named Ignorance:** Der Kern sagt nicht, was die Schueler:in
  *sonst* weiss. Das Modell faellt auf sein eigenes Wissen zurueck --
  das ist Expertenwissen. Hier koennte eine explizite Kompetenzgrenze
  im Prompt oder in den Simulationshinweisen helfen.
- **Constrained-Generation-Framing:** Der Einstieg "Du spielst ..."
  koennte durch eine staerker constraint-orientierte Formulierung
  ergaenzt werden, die dem Modell weniger Interpretationsspielraum
  laesst.
- **Beispieldichte:** Die Forschung zeigt, dass mehr Beispiele fuer
  fehlerbezogenes Verhalten die Simulation stabilisieren. Drei
  Beispiele (wie im Leitfaden empfohlen) sind ein guter Anfang; fuer
  besonders schwierige Muster koennten mehr noetig sein.

## Vertiefungsaufgaben

1. Lies ADR-0004 (zentraler Simulationskern) und markiere Stellen, an
   denen der Kern das Kompetenzparadox adressiert oder nicht adressiert.
2. Formuliere fuer das Gleichheitszeichen-Beispiel (04-beispiele.md)
   eine "Named Ignorance"-Passage: Was weiss Lukas *nicht*, und was
   weiss er *schon*?
3. Schreibe den Rollensatz "Du spielst $schuelerin_name ..." in einer
   Constrained-Generation-Variante um, ohne den Vertrag
   (`VERTRAG_PROMPT`) zu verletzen.

## Quellen

- Li et al. (2025): *Towards Valid Student Simulation with Large
  Language Models.* arXiv 2601.05473.
  https://arxiv.org/abs/2601.05473
