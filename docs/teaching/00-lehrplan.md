# Lehrplan: LLM-basierte Simulation von Schüler:innen

Ziel dieses Lehrgangs ist es, die Techniken, Forschungsergebnisse und
Designentscheidungen zu verstehen, die nötig sind, um mit LLMs
Schüler:innen und deren Fehlermuster authentisch, konsistent und
lehrreich zu simulieren -- und daraus bessere Prompts, Guardrails und
Systemarchitekturen für *FailureOnTheFly* abzuleiten.

## Aufbau

Der Lehrgang ist in sechs Lektionen gegliedert. Jede Lektion hat einen
Wissensteil, einen Abschnitt "Was bedeutet das für FailureOnTheFly?" und
Vertiefungsaufgaben.

| # | Lektion | Datei |
|---|---------|-------|
| 1 | [Das Kompetenzparadox](01-kompetenzparadox.md) | `01-kompetenzparadox.md` |
| 2 | [Prompting-Techniken fuer Persona-Konsistenz](02-prompting-techniken.md) | `02-prompting-techniken.md` |
| 3 | [Misconception Faithfulness und Sycophancy](03-misconception-faithfulness.md) | `03-misconception-faithfulness.md` |
| 4 | [Jenseits von Prompting: Fine-Tuning und hybride Architekturen](04-jenseits-von-prompting.md) | `04-jenseits-von-prompting.md` |
| 5 | [Guardrails, Structured Output und Validierung](05-guardrails.md) | `05-guardrails.md` |
| 6 | [Evaluation und Qualitaetssicherung](06-evaluation.md) | `06-evaluation.md` |

## Anhang

| Datei | Inhalt |
|-------|--------|
| [Quellenverzeichnis](quellen.md) | Alle referenzierten Paper und Frameworks |
| [Glossar](glossar.md) | Fachbegriffe aus der Forschung, die ueber CONTEXT.md hinausgehen |

## Voraussetzungen

- Vertrautheit mit dem Projekt (CONTEXT.md, standardkern.py, ADR-0004, ADR-0005)
- Grundverstaendnis von LLM-Prompting (System-Prompt, User-Prompt, Structured Output)
- Keine ML-Vorkenntnisse fuer Lektionen 1--3 und 5--6; Lektion 4 fuehrt
  die noetigen Grundlagen ein

## Empfohlene Reihenfolge

Lektionen 1--3 bauen aufeinander auf. Lektion 4 ist ein Exkurs, der
zeigt, wo Prompting allein an seine Grenzen stoesst -- relevant fuer die
Roadmap, aber nicht fuer die aktuelle Prompt-Arbeit. Lektionen 5 und 6
sind direkt anwendbar und unabhaengig voneinander lesbar.
