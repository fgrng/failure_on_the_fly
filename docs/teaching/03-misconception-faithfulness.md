# Lektion 3: Misconception Faithfulness und Sycophancy

## Worum es geht

Lektion 2 hat gezeigt, welche Prompting-Techniken die Persona
stabilisieren. Diese Lektion geht tiefer: Was passiert, wenn die
Teilnehmer:in der simulierten Schueler:in *widerspricht* oder sie zur
korrekten Loesung zu fuehren versucht? Genau das ist der Kern des
Diagnosegespraechs -- und genau hier versagen heutige LLMs am
deutlichsten.

## Das zentrale Befund-Paper

Srinivasan et al. (2025), *Simulating Students or Sycophantic Problem
Solving?*, testen sieben LLMs (4B bis 120B Parameter) auf ihre Faehigkeit,
eine Fehlvorstellung unter Feedback aufrechtzuerhalten. Die Ergebnisse
sind ernuechternd.

## Was ist Misconception Faithfulness?

**Definition:** Ein Simulator ist *misconception-faithful*, wenn er
seine simulierte Ueberzeugung nur dann aufgibt, wenn das Feedback die
*tatsaechliche* Fehlvorstellung adressiert -- und nicht einfach bei jedem
Widerspruch einknickt.

Das wird ueber drei Feedback-Bedingungen getestet:

1. **Targeted Feedback (f_T):** Adressiert die wahre Fehlvorstellung
   mit konkreter Anleitung.
2. **Misaligned Feedback (f_M):** Adressiert eine *andere*, thematisch
   plausible Fehlvorstellung.
3. **Generic Feedback (f_G):** Sagt nur "Das ist nicht richtig,
   versuch's nochmal."

Die Kennzahl ist der **Selective Flip Score (SFS)**:

```
SFS = F_T - 0.5 * (F_M + F_G)
```

- SFS nahe 1: Das Modell unterscheidet gezieltes von ungezieltem
  Feedback -- es knickt nur ein, wenn es *sollte*.
- SFS nahe 0: Das Modell knickt bei jedem Feedback gleich ein --
  oder bei keinem. Es unterscheidet nicht.

## Die Ergebnisse

### SFS ist bei *allen* Modellen nahe Null

Ueber alle sieben Modelle, beide Datensaetze und alle drei
Prompt-Varianten: **kein Modell zeigt zuverlaessige Misconception
Faithfulness rein durch Prompting.**

### Das Sycophancy-Problem

Die Modelle verhalten sich nicht wie Schueler:innen mit stabilen
Fehlvorstellungen, sondern wie *sycophantic problem solvers*: Sie
behandeln jedes Feedback als Signal, die simulierte Position aufzugeben
und das Problem mit ihrem eigenen Wissen neu zu loesen.

Das aeussert sich nicht in offensichtlichem "Umfallen":
- Die Modelle *engagieren sich mit dem Feedback* in ihrer Erklaerung.
- Sie *formulieren eine Begruendung*, die zum Feedback passt.
- Aber am Ende kommen sie *unabhaengig davon, ob das Feedback passt*,
  zur korrekten Loesung.

Das ist subtil und gefaehrlich: Die Antwort *sieht aus* wie eine
Lernreaktion, ist aber bloss Re-Solving aus internem Wissen.

### Staerkere Modelle sind *schlechter*

Es gibt eine starke negative Korrelation zwischen Modellstaerke und
SFS: Je kompetenter das Modell, desto leichter loest es das Problem
intern -- und desto weniger unterscheidet es zwischen den
Feedback-Bedingungen.

**Reasoning-Modelle** (z.B. Qwen3-80B-Thinking) sind am schlimmsten:
Sie haben hoehere Flip-Raten als ihre Instruct-Gegenstuecke, aber
*niedrigere* Sensitivitaet fuer den Feedback-Typ.

### Prompting hilft nicht

- **Reflective Prompt** ("Denke darueber nach, ob das Feedback zu
  deinem Loesungsweg passt"): Kein Effekt auf SFS.
- **Multi-Turn-Commitment** (erst Begruendung generieren, dann
  Feedback): Kein Effekt. Bei schwachen Modellen sogar
  destabilisierend.
- Die Autoren schliessen:

> The failure is not due to underspecified instructions, but is
> intrinsic to prompting-based simulation.

## Was das fuer FailureOnTheFly bedeutet

### Das konkrete Risiko

Im Diagnosegspraech passiert genau das, was die Studie testet: Die
Teilnehmer:in stellt Rueckfragen, schlaegt alternative Loesungen vor,
setzt andere Zahlen ein. Das ist gezieltes und ungezieltes Feedback in
natuerlicher Sprache. Wenn die simulierte Schueler:in bei jedem
Widerspruch zur korrekten Loesung wechselt, ist das
Diagnoseinstrument wertlos.

### Existierende Gegenmassnahmen im Kern

Der Simulationskern hat drei relevante Anweisungen:

1. "Auch bei neuen Beispielen und kritischen Nachfragen bleibst du bei
   dieser Regel."
2. "Du kennst den fachlich richtigen Loesungsweg nicht und wechselst
   innerhalb des kurzen Gespraeches nicht ploetzlich zu ihm."
3. "Legt das Gegenueber eine richtige Loesung nahe, pruefe sie
   ausschliesslich mit deiner festen inneren Regel. Stimme einer
   Korrektur nicht nur deshalb zu, weil sie von einer erwachsenen
   Person kommt."

Die dritte Anweisung ist besonders stark: Sie adressiert *Authority
Sycophancy* direkt. Aber die Forschung zeigt, dass solche Anweisungen
das Problem *mildern*, nicht *loesen*.

### Moegliche Verstaerkungen

**A. Explizite Ablehnung-Beispiele in der Fehlermuster-Beschreibung:**
Statt nur zu sagen, wie die Schueler:in begruendet, auch zeigen, wie sie
eine Korrektur *abweist*:

```
Setzt jemand Zahlen in seine Loesung ein und zeigt, dass sie nicht
aufgeht, prueft er das erneut mit seiner Regel und bleibt zunaechst
dabei: "Hmm, aber ich hab doch 8 plus 4 gerechnet, das ist 12.
Das stimmt doch."
```

Das Gleichheitszeichen-Beispiel in `04-beispiele.md` macht das bereits.
Es sollte zum Standard fuer alle Fehlermuster-Beschreibungen werden.

**B. Gegenpruefung durch die Denkspur:**
Die Denkspur gibt Forschenden die Moeglichkeit, *post hoc* zu pruefen,
ob das Modell tatsaechlich aus seiner Regel argumentiert hat oder ob
es intern korrekt geloest und dann kuenstlich "verschlechtert" hat. Ein
automatisierter Validator koennte die Denkspur darauf pruefen, ob die
Regel genannt und angewandt wird.

**C. Temperature und Sampling-Parameter:**
Hoeheres Temperature fuehrt zu *mehr* Variation, aber nicht zu *mehr*
Faithfulness. Die Forschung zeigt keine konsistenten Verbesserungen
durch Sampling-Parameter allein.

**D. Modellwahl:**
Die Studie legt nahe, dass mittelgrosse Modelle (8B--30B) in manchen
Faellen *bessere* Misconception Faithfulness zeigen als groessere Modelle,
weil ihr internes Wissen schwaecher ist. Das ist ein Tradeoff:
schwaecher im Re-Solving, aber auch schwaecher in Sprachqualitaet und
Regelanwendung.

## Das Sycophancy-Spektrum

Die Studie kategorisiert Antworten in eine Taxonomie:

| Kategorie | Beschreibung | Bewertung |
|-----------|--------------|-----------|
| Correct Flip | Engagiert sich mit Feedback, kommt zur richtigen Loesung | Gut, wenn f_T; schlecht, wenn f_M oder f_G |
| Sycophantic Flip | Korrekte Loesung ohne inhaltliche Auseinandersetzung | Immer schlecht |
| Different Wrong | Andere falsche Antwort | Instabilitaet |
| Constructive Pushback | Weist Feedback begruendet zurueck | Gut, wenn f_M oder f_G |
| Passive Maintain | Bleibt bei Antwort ohne Begruendung | Akzeptabel |
| Confusion | Inkonsistente oder verwirrte Antwort | Instabilitaet |

**Fuer FailureOnTheFly:** "Constructive Pushback" bei ungezieltem
Feedback ist das ideale Verhalten. Der Kern fordert es implizit, aber
die Forschung zeigt, dass es durch Prompting allein selten zuverlaessig
entsteht.

## Was *tatsaechlich* hilft

Die Studie testet auch Post-Training-Methoden:

| Methode | SFS-Verbesserung (Qwen3-4B, Malrule) |
|---------|--------------------------------------|
| Baseline (Prompting) | ~0 |
| SFT auf synthetischen Demonstrationen | +0.555 |
| GRPO mit SFS-aligniertem Reward | Konsistent positiv |
| DPO | Marginal |

**SFT (Supervised Fine-Tuning)** auf synthetischen Misconception-
Faithful-Demonstrationen bringt die staerksten Gewinne. Das ist
allerdings ein Aufwand, der weit ueber Prompt-Engineering hinausgeht
(siehe Lektion 4).

## Vertiefungsaufgaben

1. Suche in bestehenden Probelauf-Transkripten nach Stellen, an denen
   die simulierte Schueler:in "umkippt", obwohl das Feedback ungerichtet
   war. Dokumentiere die Muster.
2. Formuliere fuer das Julia-Beispiel (Variable als Objektbezeichnung)
   ein Rejection-Beispiel: Wie weist Julia einen Korrekturvorschlag
   mit ihrer eigenen Logik zurueck?
3. Diskutiere: Sollte der Kern die Schueler:in anweisen, *nie*
   umzukippen, oder gibt es einen Punkt, an dem das Umkippen realistisch
   waere? Was waere die Implikation fuer die Validitaet des
   Diagnoseinstruments?

## Quellen

- Srinivasan et al. (2025): *Simulating Students or Sycophantic Problem
  Solving? On Misconception Faithfulness of LLM Simulators.* arXiv
  2605.12748.
- Srinivasan et al. (2025): *Sycophancy is an Educational Safety Risk:
  Why LLM Tutors Need Sycophancy Benchmarks.* arXiv 2605.14604.
- Bowman et al. (2025): *"Check My Work?" Measuring Sycophancy in a
  Simulated Educational Context.* arXiv 2506.10297.
