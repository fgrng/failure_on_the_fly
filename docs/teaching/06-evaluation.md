# Lektion 6: Evaluation und Qualitaetssicherung

## Worum es geht

Die bisherigen Lektionen haben Techniken vorgestellt, um die Simulation
besser zu machen. Diese Lektion fragt: Wie misst man, *ob* sie besser
geworden ist? Welche Metriken, Tests und Prozesse braucht es, um die
Qualitaet der Simulation systematisch zu pruefen?

## 1. Die drei Evaluationsebenen

Die Forschung unterscheidet drei Ebenen, auf denen ein Schueler:innen-
Simulator evaluiert werden kann:

### Ebene 1: Oberflaechliche Realistik

*Klingt die Schueler:in wie eine Schueler:in?*

- Laenge und Komplexitaet der Antworten
- Altersangemessener Wortschatz
- Tonfall (freundlich, kooperativ, knapp)
- Grammatikalische Fehler passend zur Klassenstufe

**Messbar durch:** Menschliche Bewertung, automatisierte
Lesbarkeitsmetriken (Flesch-Kincaid etc.), LLM-as-Judge.

**Limitation:** Oberflaechliche Realistik sagt nichts ueber die
Qualitaet des Fehlermusters. Eine fluessig formulierte, aber
inkonsistente Simulation ist schlimmer als eine steife, aber
konsistente.

> "Fluent interaction can obscure unrealistic error patterns and
> learning dynamics." (Li et al., 2025)

### Ebene 2: Fehler-Konsistenz (Misconception Faithfulness)

*Wendet die Schueler:in das Fehlermuster konsistent an?*

Das ist die zentrale Ebene fuer FailureOnTheFly. Relevante Metriken:

| Metrik | Beschreibung | Quelle |
|--------|-------------|--------|
| Selective Flip Score (SFS) | Unterscheidet das Modell gezieltes von ungezieltem Feedback? | Srinivasan et al., 2025 |
| Cross-Problem Consistency | Wendet das Modell die Regel auf isomorphe Aufgaben gleich an? | Li et al., 2025 |
| Characteristics Alignment | Sind Fehler kausal auf das Schema zurueckfuehrbar? | MATHVC |
| Dual Fidelity | Fehlt das Muster bei nicht-relevanten Aufgaben, loest es korrekt? | Stanford CSMs |
| Statement Consistency | Widerspricht sich das Modell ueber Turns hinweg? | Hua et al., NeurIPS 2025 |

### Ebene 3: Diagnostische Brauchbarkeit

*Kann eine Lehrperson das Fehlermuster durch geschicktes Nachfragen
aufdecken?*

Das ist die Ebene, die fuer das Projektziel zaehlt: Diagnostische
Kompetenz trainieren und erheben. Sie ist die schwerste zu messen,
weil sie die Interaktion von Teilnehmer:in und Simulation einschliesst.

**Messbar durch:**
- Expert:innen-Bewertung von Probelauf-Transkripten
- Vergleich: Diagnosen nach Gespraech mit Simulation vs. Diagnosen
  nach Gespraech mit echten Schueler:innen
- Itemschwierigkeit-Korrelation: Produziert die Simulation dieselbe
  Rangfolge der Schwierigkeit wie echte Schueler:innen?

## 2. Ein Evaluationsrahmen fuer FailureOnTheFly

### Was bereits moeglich ist

FailureOnTheFly speichert fuer jede Sitzung:
- Das vollstaendige Transkript
- Die Denkspur zu jeder Antwort
- Etwaige native Reasoning-Spuren
- Etwaige Fehlversuche mit Grund und Rohantwort
- Die verwendete Vignettenfassung, Kern-Fassung und
  Modell-Konfiguration

Das ist eine reichhaltige Datenbasis fuer die Evaluation.

### Vorgeschlagene Pruefungen

#### A. Denkspur-Konsistenz-Pruefung (automatisierbar)

Fuer jeden Gespraechsschritt:
1. Enthaelt die Denkspur eine Referenz auf die feste Regel?
2. Wendet die Denkspur die Regel *an* (nicht nur erwaehnt)?
3. Stimmt die Aeusserung mit dem Ergebnis der Denkspur ueberein?

**Implementierung:** Ein zweiter LLM-Aufruf (oder ein spezialisierter
Classifier) bekommt Denkspur, Aeusserung und Fehlermuster-Beschreibung
und bewertet die Konsistenz. Das koennte als Batch-Evaluation ueber
gespeicherte Sitzungen laufen, nicht zur Laufzeit.

#### B. Isomorphie-Test (automatisierbar)

Fuer jedes Fehlermuster:
1. Generiere drei isomorphe Aufgaben (andere Zahlen, gleiches Muster).
2. Stelle sie der Simulation in einem Probelauf.
3. Pruefe: Wendet die Simulation das Muster auf alle drei gleich an?

**Implementierung:** Koennte als Management-Command oder als
Ergaenzung des Probelaufs umgesetzt werden.

#### C. Sycophancy-Stress-Test (automatisierbar)

Fuer jedes Fehlermuster:
1. Fuehre einen Probelauf mit drei verschiedenen Feedback-Typen:
   - Gezieltes Feedback (adressiert das tatsaechliche Muster)
   - Fehlleitendes Feedback (adressiert ein anderes Muster)
   - Generisches Feedback ("Das ist falsch")
2. Pruefe: Reagiert die Simulation unterschiedlich?
3. Berechne den SFS.

**Implementierung:** Automatisierte Probelaeufe mit vorgefertigten
Eingabe-Sequenzen.

#### D. Expert:innen-Review (manuell)

Fachdidaktiker:innen bewerten Transkripte auf:
1. Ist das Fehlermuster erkennbar?
2. Ist es aufdeckbar durch geschicktes Nachfragen?
3. Ist das Gespraech realistisch?
4. Wuerde die Simulation eine sinnvolle Trainings-Erfahrung bieten?

## 3. ESS-Berichtsboegen: Falsifizierbare Anforderungen

Li et al. (2025) schlagen vor, fuer jeden Simulator einen
ESS-Berichtsbogen auszufuellen. Uebertragen auf FailureOnTheFly:

### E1-Kriterien (Static Bounded)

| Kriterium | Erfuellt? | Nachweis |
|-----------|-----------|---------|
| **Named Ignorance:** Was weiss die Schueler:in *nicht*? | Teilweise | Implizit durch "kennt den richtigen Weg nicht"; nicht fuer Wissen ausserhalb des Musters |
| **Implementation Anchor:** Wo wird die Grenze erzwungen? | Ja | System-Prompt + Structured Output |

### E3-Kriterien (Misconception-Structured)

| Kriterium | Erfuellt? | Nachweis |
|-----------|-----------|---------|
| **Misconception Inventory:** Explizites Fehlvorstellungs-Verzeichnis? | Ja | Fehlermuster-Beschreibung pro Vignette |
| **Generative Mechanism:** Kausal bestimmtes Verhalten? | Ja | "Feste innere Regel" + Denkspur |
| **Cross-Problem Consistency:** Pruefung ueber isomorphe Aufgaben? | **Nein** | Nicht systematisch |

### E4-Kriterien (Calibrated/Learned)

| Kriterium | Erfuellt? |
|-----------|-----------|
| **Data Source** | Nicht anwendbar (kein kalibriertes Modell) |
| **Fitted Parameters** | Nicht anwendbar |
| **Predictive Test** | Nicht anwendbar |

## 4. Evaluation der Fehlermuster-Beschreibung

Die Qualitaet der Simulation haengt massgeblich von der Qualitaet der
Fehlermuster-Beschreibung ab. Der bestehende Leitfaden
(`03-fehlermuster-leitfaden.md`) gibt Kriterien; hier eine
operationalisierte Checkliste:

| Kriterium | Pruefung | Methode |
|-----------|----------|---------|
| Regel statt Etikett | Enthaelt die Beschreibung einen anwendbaren Mechanismus? | Manuell |
| Kontrastierung | Ist die korrekte Loesung als Kontrast benannt? | Manuell |
| Uebertragbarkeit | Gibt es mindestens zwei Beispiele an anderen Aufgaben? | Manuell |
| Begruendungssaetze | Gibt es Beispielsaetze in Alltagssprache? | Manuell |
| Abgrenzung | Ist klar, was es *nicht* ist? | Manuell |
| Zyklus-Konsistenz | Reproduziert die Simulation den erwarteten Fehler? | Automatisierbar |
| Rejection-Beispiel | Zeigt die Beschreibung, wie die Schueler:in Korrekturen abweist? | Manuell |

## 5. Continuous Evaluation: Was regelmaessig pruefen?

### Bei jedem neuen Fehlermuster (Autor:innen-Workflow)
- Probelauf mit mindestens fuenf verschiedenen Eingaben
- Denkspur auf Regel-Anwendung pruefen
- Mindestens eine Eingabe, die zur richtigen Loesung fuehrt (Sycophancy-Check)

### Bei jedem neuen Kern (Administrator:innen-Workflow)
- Alle bestehenden Vignetten im Probelauf gegen den neuen Kern testen
- SFS fuer eine Stichprobe von Vignetten berechnen
- Vergleich der Denkspur-Konsistenz mit dem vorherigen Kern

### Bei jedem Modellwechsel
- Gleiche Pruefungen wie beim Kern-Wechsel
- Zusaetzlich: Vergleich der Sprachqualitaet und des Tonfalls

## Vertiefungsaufgaben

1. Fuehre den ESS-Berichtsbogen fuer FailureOnTheFly vollstaendig aus.
   Welche E3-Kriterien sind noch nicht erfuellt? Was waere noetig?
2. Entwirf einen automatisierten Sycophancy-Stress-Test als
   Management-Command: Welche Eingaben wuerdest du verwenden, und was
   waere das Akzeptanzkriterium?
3. Entwickle eine Checkliste fuer das Expert:innen-Review von
   Probelauf-Transkripten mit mindestens sechs Pruefpunkten.

## Quellen

- Li et al. (2025): *Towards Valid Student Simulation with Large
  Language Models.* arXiv 2601.05473.
- Srinivasan et al. (2025): *Simulating Students or Sycophantic Problem
  Solving?* arXiv 2605.12748.
- Hua et al. (2025): *Consistently Simulating Human Personas with
  Multi-Turn Reinforcement Learning.* NeurIPS 2025.
- FailureOnTheFly: ADR-0005, ADR-0010, ADR-0011.
