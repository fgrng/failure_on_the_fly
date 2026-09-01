# Quellenverzeichnis

Alle Paper und Frameworks, die in den Lektionen referenziert werden,
chronologisch sortiert.

## Primaerquellen

### Kompetenzparadox und Validitaet

- **Li et al. (2025):** *Towards Valid Student Simulation with Large
  Language Models.*
  arXiv 2601.05473.
  https://arxiv.org/abs/2601.05473
  Referenziert in: Lektion 1, 2, 4, 5, 6.
  Kernbeitrag: Competence Paradox, Epistemic State Specification (ESS),
  Constrained-Generation-Rahmen, ESS-Berichtsbogen.

### Misconception Faithfulness und Sycophancy

- **Srinivasan et al. (2025):** *Simulating Students or Sycophantic
  Problem Solving? On Misconception Faithfulness of LLM Simulators.*
  arXiv 2605.12748.
  https://arxiv.org/abs/2605.12748
  Referenziert in: Lektion 2, 3, 6.
  Kernbeitrag: Selective Flip Score (SFS), Sycophantic Problem Solving,
  Nachweis der Wirkungslosigkeit von Reflective Prompting.

- **Srinivasan et al. (2025):** *Sycophancy is an Educational Safety
  Risk: Why LLM Tutors Need Sycophancy Benchmarks.*
  arXiv 2605.14604.
  https://arxiv.org/abs/2605.14604
  Referenziert in: Lektion 3.
  Kernbeitrag: Reasoning Sycophancy Paradox, Authority Sycophancy.

- **Bowman et al. (2025):** *"Check My Work?" Measuring Sycophancy in a
  Simulated Educational Context.*
  arXiv 2506.10297.
  https://arxiv.org/abs/2506.10297
  Referenziert in: Lektion 3.

### Fine-Tuning und MISTAKE

- **Stacey et al. (2024):** *Learning to Make MISTAKEs: Modeling
  Incorrect Student Thinking And Key Errors.*
  arXiv 2510.11502.
  https://arxiv.org/abs/2510.11502
  Referenziert in: Lektion 4.
  Kernbeitrag: MISTAKE-Framework, Zyklus-Konsistenz-Filter,
  Misconception-Guided Chain-of-Thought.

### Kognitive Modelle und Dual Fidelity

- **Stanford SCALE (2024):** *LLM-based Cognitive Models of Students
  with Misconceptions.* MalAlgoPy-Framework.
  https://scale.stanford.edu/ai/repository/llm-based-cognitive-models-students-misconceptions
  Referenziert in: Lektion 4.
  Kernbeitrag: Dual Fidelity, Mischungsverhaeltnis-Kalibrierung.

### Persona-Konsistenz und Role-Playing

- **Hua et al. (2025):** *Consistently Simulating Human Personas with
  Multi-Turn Reinforcement Learning.*
  NeurIPS 2025.
  https://proceedings.neurips.cc/paper_files/paper/2025/file/4c91443877f8388d8190c938ac5a4d4d-Paper-Conference.pdf
  Referenziert in: Lektion 4, 6.
  Kernbeitrag: Statement Consistency, Persona Adherence, Dialogue
  Coherence als Metriken.

- **Yang et al. (2026):** *Beyond Static Persona Consistency: Dynamic
  Persona Coherence in LLM Role-Playing.*
  ACL 2026.
  https://aclanthology.org/2026.acl-long.1336/
  Referenziert in: Lektion 2.
  Kernbeitrag: Identity Layer / Adaptive Layer, L/M/S Psychological
  State Model.

- **Wang et al. (2026):** *PersonaForge: Psychology-Grounded
  Dual-Process Architecture for Personality-Consistent Role-Playing
  Agents.*
  Findings of ACL 2026.
  https://aclanthology.org/2026.findings-acl.386/
  Referenziert in: Lektion 2.

- **Chen et al. (2026):** *MENTOR: Mitigating Identity Drift in Dynamic
  Role-Playing via Dual-Chain Structured Memory.*
  Findings of ACL 2026.
  https://aclanthology.org/2026.findings-acl.1046/
  Referenziert in: Lektion 2.

### Kognitive Diversitaet und CPM

- **Wang et al. (2025):** *Embracing Imperfection: Simulating Students
  with Diverse Cognitive Levels Using LLM-based Agents.*
  ACL 2025.
  https://aclanthology.org/2025.acl-long.488/
  Referenziert in: Lektion 2.
  Kernbeitrag: Cognitive Parameter Module, parameterisierte
  System-Prompts.

### Pedagogical Chain-of-Thought

- **Sonkar et al. (2024):** *LLMs can Find Mathematical Reasoning
  Mistakes by Pedagogical Chain-of-Thought.*
  arXiv 2405.06705.
  https://arxiv.org/abs/2405.06705
  Referenziert in: Lektion 2.

### GPTeach und fruehe Ansaetze

- **Markel et al. (2023):** *GPTeach: Interactive TA Training with
  GPT-based Students.*
  L@S 2023.
  Referenziert in: Lektion 2.
  Kernbeitrag: Few-Shot mit authentischen Transkripten.

## Weitere Frameworks (erwaehnt, aber nicht direkt verwendet)

- **EduPersona** (2025): Benchmark fuer subjektive Faehigkeitsgrenzen
  virtueller Schueler:innen-Agenten.
  https://arxiv.org/abs/2510.04648

- **SOEI Framework** (2024): Konstruktion und Evaluation virtueller
  Schueler:innen-Agenten.
  https://arxiv.org/abs/2410.15701

- **PersonaGPT** (2025): Dynamische Lerner-Personas mit reflexivem
  Dialog.
  IEEE SMAP 2025.

## Interne Referenzen (FailureOnTheFly)

- CONTEXT.md -- Glossar
- ADR-0004 -- Zentraler, fach-agnostischer Simulationskern
- ADR-0005 -- Denkspur pro Antwort und ihre Sichtbarkeit
- ADR-0010 -- Fester Vertrag zwischen Vignette und Prompt-Vorlagen
- ADR-0011 -- Gespraechsschritt ist atomar; Fehlversuche neben dem
  Transkript
- docs/vignette-author-gem/knowledge/02-prompt-und-sichtbarkeit.md
- docs/vignette-author-gem/knowledge/03-fehlermuster-leitfaden.md
- docs/vignette-author-gem/knowledge/04-beispiele.md
- simulation/standardkern.py
- simulation/sprachmodell/__init__.py
- simulation/__init__.py
