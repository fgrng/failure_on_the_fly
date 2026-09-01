# Glossar: Forschungsbegriffe zur LLM-basierten Schueler:innensimulation

Dieses Glossar ergaenzt CONTEXT.md um Fachbegriffe aus der Forschung,
die in den Lektionen verwendet werden.

---

**Authority Sycophancy:**
Das Modell gibt einer Korrektur nach, *weil* sie von einer
erwachsenen oder autoritaeren Person kommt -- nicht weil sie inhaltlich
ueberzeugt. Im Kontext von FailureOnTheFly: Die simulierte Schueler:in
stimmt der Teilnehmer:in zu, weil diese die Lehrkraft-Rolle hat.

**Boundary of Competence:**
Die dritte der drei gekoppelten Anforderungen (Li et al., 2025). Das
Modell soll sich *ausserhalb* des Fehlermusters gemaess seinem
angenommenen Kompetenzniveau verhalten -- weder Expertenwissen zeigen
noch zufaellig falsch antworten.

**Cognitive Parameter Module (CPM):**
Ein strukturierter Prompt-Baustein, der das kognitive Niveau
mehrdimensional parametrisiert (z.B. Klassenstufe x Bloom's-Stufe).
Quelle: Wang et al. (2025).

**Competence Paradox (Kompetenzparadox):**
Der Widerspruch zwischen der breiten Kompetenz eines LLM und der
Aufgabe, partielle Inkompetenz darzustellen. Das Modell kann erworbenes
Wissen nicht gezielt "vergessen". Quelle: Li et al. (2025).

**Constrained Generation:**
Perspektivwechsel: Schueler:innensimulation nicht als freies
Role-Playing, sondern als Textgenerierung unter exakt spezifizierten
Einschraenkungen.

**Cross-Problem Consistency:**
Pruefung, ob das Fehlermuster auf isomorphe Aufgaben (andere Zahlen,
gleiches Muster) gleich angewandt wird.

**Cycle Consistency (Zyklus-Konsistenz):**
Qualitaetspruefung aus dem MISTAKE-Framework: Wenn eine erschlossene
Fehlvorstellung die falsche Antwort wirklich erklaert, muss eine
Simulation mit dieser Fehlvorstellung dieselbe falsche Antwort
reproduzieren. Quelle: Stacey et al. (2024).

**Dual Fidelity:**
Die Anforderung, dass ein simulierter Schueler (a) Fehler bei
relevanten Aufgaben repliziert und (b) korrekt loest, wo das
Fehlermuster nicht greift. Quelle: Stanford CSMs.

**Epistemic Consistency:**
Die zweite der drei gekoppelten Anforderungen. Fehler muessen kausal
auf die beschriebene Wissensgrenze zurueckfuehrbar sein und ueber
isomorphe Aufgaben hinweg stabil bleiben.

**Epistemic State Specification (ESS):**
Eine formale Deklaration dessen, was die simulierte Schueler:in weiss,
welche Fehlerquellen aktiv sind und wie sich der Zustand aendert.
Fuenfstufiges Reifegradmodell (E0--E4). Quelle: Li et al. (2025).

**Fidelity of Error (Fehlertreue):**
Die erste der drei gekoppelten Anforderungen. Das Fehlermuster muss
auf allen relevanten Aufgabentypen konsistent angewandt werden.

**Identity Drift / Persona Drift:**
Das schrittweise Verlassen der zugewiesenen Persona ueber mehrere
Gespraechsschritte hinweg. Das Modell "vergisst" seine Rolle.

**MISTAKE:**
Ein unsupervised Framework, das zwei iterativ verbesserte Modelle
(Student Simulation + Misconception Inference) nutzt, um synthetische
Beispiele fehlerhaften Denkens zu erzeugen. Quelle: Stacey et al. (2024).

**Misconception Faithfulness:**
Die Faehigkeit eines Simulators, eine simulierte Fehlvorstellung nur
dann aufzugeben, wenn das Feedback die tatsaechliche Fehlvorstellung
adressiert.

**Named Ignorance:**
Explizite Auflistung dessen, was die simulierte Schueler:in *nicht*
weiss. Teil der E1-Kriterien im ESS-Berichtsbogen.

**Over-Generate-Then-Select:**
Architektur-Muster: Das LLM generiert mehrere Antwort-Varianten, ein
Filter waehlt die konsistenteste aus.

**Pedagogical Chain-of-Thought (PedCoT):**
Eine CoT-Variante, bei der das Modell seine Fehlvorstellung
Schritt fuer Schritt auf die Aufgabe anwendet, bevor es antwortet.
Quelle: Sonkar et al. (2024).

**Selective Flip Score (SFS):**
Metrik fuer Misconception Faithfulness. Misst, ob das Modell gezieltes
von ungezieltem Feedback unterscheidet.
SFS = F_T - 0.5 * (F_M + F_G), Wertebereich [-1, 1].
Quelle: Srinivasan et al. (2025).

**Sycophantic Problem Solving:**
Fehlermodus, bei dem das Modell jedes Feedback als Signal behandelt,
die simulierte Position aufzugeben und das Problem mit seinem eigenen
(korrekten) Wissen neu zu loesen.
Quelle: Srinivasan et al. (2025).
