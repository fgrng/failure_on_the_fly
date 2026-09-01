# Lektion 4: Jenseits von Prompting -- Fine-Tuning und hybride Architekturen

## Worum es geht

Lektion 3 hat gezeigt, dass Prompting allein das Sycophancy-Problem
nicht loest. Diese Lektion stellt Techniken vor, die ueber Prompting
hinausgehen: Fine-Tuning, hybride Architekturen und externe Controller.
Sie liegen ausserhalb des aktuellen FailureOnTheFly-Scopes, aber zu
wissen, *was moeglich ist*, hilft, die Grenzen des Prompting-Ansatzes
einzuschaetzen und die Roadmap zu planen.

## 1. MISTAKE: Unsupervised Fine-Tuning fuer Fehlersimulation

Das Paper *Learning to Make MISTAKEs* (Stacey et al., 2024) loest ein
konkretes Problem: Wie bringt man ein LLM dazu, *bestimmte* Fehler zu
machen, ohne echte Schueler:innendaten zu brauchen?

### Die Architektur

MISTAKE besteht aus zwei Modellen, die iterativ verbessert werden:

1. **Student Simulation Model (M_s):** Bekommt eine Frage und eine
   Fehlvorstellungs-Beschreibung, erzeugt einen Loesungsweg *aus der
   Fehlvorstellung* und eine (falsche) Antwort.

2. **Misconception Inference Model (M_m):** Bekommt eine Frage und eine
   falsche Antwort, erzeugt eine Erklaerung, *warum* diese Antwort
   entstanden sein koennte, und benennt die Fehlvorstellung.

### Der Zyklus-Konsistenz-Filter

Die entscheidende Qualitaetssicherung: Wenn die erschlossene
Fehlvorstellung die falsche Antwort wirklich erklaert, dann muss die
Simulation mit dieser Fehlvorstellung dieselbe falsche Antwort
reproduzieren. Tut sie das nicht, ist die Erklaerung unzuverlaessig und
wird abgewertet.

```
Frage + korrekte Antwort
    |
    v
Sampling: erzeugt plausible falsche Antwort a
    |
    v
M_m: erschliesst Fehlvorstellung m aus (Frage, a)
    |
    v
M_s: simuliert Schueler:in mit m, erzeugt Antwort s
    |
    v
Pruefe: s == a?  --> Ja: hohe Gewichtung
                  --> Nein, aber s != korrekt: mittlere Gewichtung
                  --> s == korrekt: verwerfen
```

### Ergebnisse

- GPT-4o erreicht 64% Genauigkeit bei der Fehlersimulation (gegenueber
  85% beim Loesen der Aufgabe -- der Kompetenzparadox-Gap).
- Fine-Tuning auf MISTAKE-Daten hebt ein 8B-Modell von 41% auf 44%.
- Der Zyklus-Konsistenz-Filter allein verbessert die Praezision von
  Distraktoren um 65%.

### Relevanz fuer FailureOnTheFly

MISTAKE erzeugt *Antworten*, nicht *Gespraeche*. Aber zwei Ideen sind
uebertragbar:

**A. Der Zyklus-Konsistenz-Test als Qualitaetspruefung fuer
Fehlermuster-Beschreibungen:**
Koennte man vor dem Finalisieren einer Vignette automatisiert pruefen:
"Wenn ich dem Modell nur die Fehlermuster-Beschreibung gebe und eine
neue Aufgabe stelle -- kommt dann ein Fehler heraus, der zum Muster
passt?" Das waere ein automatisierter Probelauf mit Validierung.

**B. Misconception-Guided Chain-of-Thought:**
MISTAKE zeigt, dass der Loesungsweg *aus der Fehlvorstellung* heraus
erzeugt werden muss -- nicht ein korrekter Weg, der dann verfaelscht
wird. Die Denkspur im Kern tut genau das: "Wende in der Denkspur deine
feste innere Regel an." Aber die *Qualitaet* der Denkspur-Anweisung
koennte sich an MISTAKEs Prompt-Design orientieren.

## 2. Cognitive Student Models (CSMs): Dual Fidelity

Das Paper *LLM-based Cognitive Models of Students with Misconceptions*
(Stanford, 2024) adressiert ein Problem, das FailureOnTheFly aus der
Praxis kennt:

> Eine Schueler:in, die ein Fehlermuster hat, macht nicht *bei jeder*
> Aufgabe Fehler -- nur bei denen, auf die das Muster anwendbar ist.
> Bei allen anderen Aufgaben rechnet sie richtig.

### Das Dual-Fidelity-Problem

Ein CSM muss zwei Eigenschaften gleichzeitig erfuellen:

1. **Fehlermuster replizieren** auf Aufgaben, wo es greift.
2. **Korrekt loesen** auf Aufgaben, wo es nicht greift.

Fine-Tuning nur auf Fehlermuster-Beispielen zerstoert die Faehigkeit,
korrekt zu loesen. Fine-Tuning nur auf korrekte Beispiele verdraengt
das Fehlermuster.

### Die Loesung: Mischungsverhaeltnis

Die entscheidende Variable ist das *Verhaeltnis von korrekten zu
fehlerhaften Beispielen* im Training. Bereits ein Verhaeltnis von 0.25
(ein korrektes Beispiel auf vier fehlerhafte) genuegt, um beide
Eigenschaften zu erhalten.

### Relevanz fuer FailureOnTheFly

Das Dual-Fidelity-Problem existiert auch im Prompting-Setting: Wenn die
Teilnehmer:in eine Aufgabe stellt, die *nichts* mit dem Fehlermuster zu
tun hat, soll die Schueler:in sie korrekt loesen. Der Kern sagt
implizit: "Wende deine Regel an" -- aber was, wenn die Regel nicht
anwendbar ist?

**Moegliche Ergaenzung im Kern:**
"Wenn die Frage oder Aufgabe nichts mit deiner festen inneren Regel zu
tun hat, beantworte sie nach bestem Wissen deiner Klassenstufe."

## 3. Hybride Architekturen: LLM + externer Controller

Mehrere Papers schlagen vor, das LLM nicht allein entscheiden zu lassen,
sondern einen externen Controller dazwischenzuschalten.

### MATHVC: Symbolisches Character Schema + Dialog-Controller

- Ein strukturiertes Schema definiert, welche Variablen die Schueler:in
  kennt und welche sie missverstanden hat.
- Ein Controller filtert Antworten, die Variablen *ausserhalb* des
  Schemas referenzieren.
- Das LLM erzeugt den Text; der Controller validiert.

### Agent4Edu: Entkoppelte kognitive Module

- **Learner Profile:** IRT-Parameter (Schwierigkeit, Faehigkeit)
- **Memory Module:** Ebbinghaus-Vergessenskurve
- **Action Module:** LLM, das auf den abgerufenen Zustand konditioniert
  wird

### Over-Generate-Then-Select (HypoCompass)

- Das LLM generiert mehrere Antwort-Varianten.
- Ein Filter waehlt die Variante aus, die syntaktisch korrekt, aber
  logisch fehlerhaft ist.
- Das ist konzeptionell verwandt mit den Fehlversuchen in
  FailureOnTheFly, aber proaktiv statt reaktiv.

### Relevanz fuer FailureOnTheFly

Die Architektur von FailureOnTheFly hat bereits eine minimale
Controller-Funktion: den Antwortversuch mit seinen Fehlversuchen und
dem Formatbruch-Filter. Ein *inhaltlicher* Controller -- z.B. ein
zweites Modell, das die Aeusserung gegen das Fehlermuster prueft, bevor
sie an die Teilnehmer:in geht -- waere ein architektonischer naechster
Schritt.

**Over-Generate-Then-Select bei FailureOnTheFly:**
Statt drei Versuche *bei Fehler* (reaktiv) koennte der Kern
standardmaessig *mehrere Antworten generieren* und die
fehlerkonsistenteste waehlen (proaktiv). Das wuerde die Latenz erhoehen,
aber die Konsistenz verbessern.

## 4. Reinforcement Learning: Persona-Konsistenz belohnen

Das Paper *Consistently Simulating Human Personas with Multi-Turn
Reinforcement Learning* (NeurIPS 2025) trainiert Modelle mit einem
Reward-Signal, das Persona-Konsistenz ueber mehrere Turns belohnt.

Drei automatische Metriken:
1. **Statement Consistency:** Widerspricht sich das Modell selbst?
2. **Persona Adherence:** Passt die Antwort zur definierten Persona?
3. **Dialogue Coherence:** Ist die Antwort kontextuell stimmig?

Die Ergebnisse: RL-trainierte Modelle zeigen signifikant weniger
Persona-Drift als nur per Prompt instruierte Modelle.

### Relevanz fuer FailureOnTheFly

RL-Training ist ausserhalb des aktuellen Scopes. Aber die drei Metriken
sind direkt als *Evaluationskriterien* fuer den Kern verwendbar (siehe
Lektion 6).

## Zusammenfassung: Die Landkarte jenseits von Prompting

| Technik | Aufwand | Relevanz fuer FotF |
|---------|---------|-------------------|
| MISTAKE (Fine-Tuning) | Hoch | Ideen uebertragbar (Zyklus-Test, CoT-Design) |
| CSMs (Dual Fidelity) | Mittel-hoch | Prompt-Erweiterung fuer Nicht-Fehler-Faelle |
| Hybrider Controller | Mittel | Denkbar als Over-Generate-Then-Select |
| RL fuer Persona-Konsistenz | Sehr hoch | Metriken uebertragbar |

## Vertiefungsaufgaben

1. Entwirf einen Zyklus-Konsistenz-Test fuer das Lukas-Beispiel: Welche
   drei neuen Aufgaben wuerdest du stellen, und welche Antworten
   erwartest du, wenn das Muster konsistent ist?
2. Formuliere die Kern-Ergaenzung fuer das Dual-Fidelity-Problem:
   Was soll die Schueler:in tun, wenn die Frage nichts mit ihrem
   Fehlermuster zu tun hat?
3. Diskutiere: Ist Over-Generate-Then-Select bei einem synchronen
   Diagnosegepraech (Latenzbudget ~10s) realisierbar? Was waere der
   Tradeoff?

## Quellen

- Stacey et al. (2024): *Learning to Make MISTAKEs: Modeling Incorrect
  Student Thinking And Key Errors.* arXiv 2510.11502.
- Stanford SCALE (2024): *LLM-based Cognitive Models of Students with
  Misconceptions.*
- Hua et al. (2025): *Consistently Simulating Human Personas with
  Multi-Turn Reinforcement Learning.* NeurIPS 2025.
- Li et al. (2025): *Towards Valid Student Simulation with Large
  Language Models.* arXiv 2601.05473.
