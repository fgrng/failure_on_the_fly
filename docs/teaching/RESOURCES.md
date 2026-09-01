# Resources

Bewertete Anlaufstellen für Wissen und Wisdom. Die vollständige,
formatierte Zitationsliste liegt in [quellen.md](quellen.md); hier steht,
*wofür* eine Quelle taugt und wie sehr ich ihr traue.

## Primärquellen (hohes Vertrauen, geprüft im Projektkontext)

### Li et al. (2025) — Towards Valid Student Simulation with LLMs
- **Link:** https://arxiv.org/abs/2601.05473
- **Typ:** Survey / Positionspapier
- **Wofür:** Competence Paradox, Epistemic State Specification (E0–E4),
  Constrained-Generation-Rahmen, die drei gekoppelten Anforderungen.
- **Vertrauen:** Hoch — der begriffliche Rahmen des ganzen Lehrgangs.
- **Status:** gelesen (Lektion 1)

### Srinivasan et al. (2025) — Simulating Students or Sycophantic Problem Solving?
- **Link:** https://arxiv.org/abs/2605.12748
- **Typ:** Empirisch, mit Metrik
- **Wofür:** Selective Flip Score, Nachweis dass Reflective Prompting
  nicht wirkt. Direkt relevant für unsere Evaluation.
- **Vertrauen:** Hoch — liefert die einzige Metrik, die unser Kernrisiko misst.
- **Status:** gelesen (Lektion 3)

### Stacey et al. (2024) — Learning to Make MISTAKEs
- **Link:** https://arxiv.org/abs/2510.11502
- **Wofür:** Zyklus-Konsistenz als Prüfidee — auch ohne Fine-Tuning auf
  unsere Vignetten-Qualitätssicherung übertragbar.
- **Vertrauen:** Hoch für das Prüfkonzept, mittel für die Übertragbarkeit
  (dort Fine-Tuning, bei uns Prompting).
- **Status:** gelesen (Lektion 4)

### Wang et al. (2025) — Embracing Imperfection (ACL)
- **Link:** https://aclanthology.org/2025.acl-long.488/
- **Wofür:** Cognitive Parameter Module — Vorlage für eine explizite
  Kompetenzgrenze im System-Prompt.
- **Vertrauen:** Hoch (peer-reviewed, ACL Long).
- **Status:** gelesen (Lektion 2)

## Sekundärquellen (nützlich, noch nicht tief geprüft)

- **Bowman et al. (2025)** — *"Check My Work?"*, https://arxiv.org/abs/2506.10297.
  Sycophancy-Messung im Bildungskontext. Noch nicht gegen unsere Vignetten geprüft.
- **EduPersona (2025)** — https://arxiv.org/abs/2510.04648. Benchmark für
  subjektive Fähigkeitsgrenzen; potenzielle Evaluationsvorlage.
- **SOEI (2024)** — https://arxiv.org/abs/2410.15701. Konstruktions- und
  Evaluationsrahmen für virtuelle Schüler:innen-Agenten.

## Interne Quellen (höchstes Vertrauen, weil verifizierbar)

- `CONTEXT.md` — verbindliche Projektsprache
- `docs/adr/` — ADR-0004 (Simulationskern), ADR-0005 (Denkspur),
  ADR-0010 (Prompt-Vertrag), ADR-0011 (atomarer Gesprächsschritt)
- `simulation/standardkern.py` — der Prompt, um den sich alles dreht
- `docs/vignette-author-gem/knowledge/` — Autor:innen-Leitfäden

## Communities (Wisdom)

Noch nicht ausgewählt. Kandidaten für die Ebene "Testen der eigenen
Argumente an anderen Praktiker:innen":

- **CERME / ERME TWG18** — die fachdidaktische Zielcommunity des Papers.
  Die Working Group selbst ist das Peer-Feedback-Format.
- **GDM (Gesellschaft für Didaktik der Mathematik)**, Arbeitskreis
  Mathematikunterricht und digitale Werkzeuge.
- **SIG:Learning Analytics / L@S-Community (ACM Learning at Scale)** —
  dort sitzt die technische Hälfte des Problems.

> Offen: Möchtest du überhaupt eine Community einbeziehen, oder bleibt
> CERME der einzige externe Prüfstein? Siehe NOTES.md.

## Lücken

- Keine Quelle bislang zu **Evaluation mit echten Lehramtsstudierenden**
  (Validität der Simulation aus Nutzersicht statt aus Modellsicht).
- Keine deutschsprachige fachdidaktische Quelle zu Fehlermustern im
  Verhältnis zur LLM-Literatur — für CERME vermutlich nötig.
