# Issue-Labels

Dieses Dokument beschreibt die Labels, die im Issue-Tracker dieses Projekts (`fgrng/failure_on_the_fly`) tatsächlich relevant sind und verwendet werden. Es ist die kanonische Referenz: Wenn ein Skill von einer Label-Rolle spricht (z. B. „apply the AFK-ready triage label"), ist damit das hier dokumentierte Projekt-Label gemeint.

## Spec und Ticket

Diese beiden Labels trennen Spezifikation von ausführbarer Arbeit.

- **`Spec`** — Ein Spezifikations- bzw. Umbrella-Issue, das eine Anforderung beschreibt. Ein `Spec` wird **nie** mit `AFK` versehen: AFK-Agenten dürfen eine Spec nicht direkt umsetzen, sie ist ausschließlich die Grundlage, aus der Tickets abgeleitet werden.
- **`Ticket`** — Eine ausführbare Teilaufgabe, die einen Teil einer `Spec` umsetzt. Ein Ticket trägt `AFK`, sobald es umsetzungsreif ist.

Eine `Spec` und ihre `Ticket`s überschneiden sich stark (dieselben Dateien, dieselben Modelle). Trüge die Spec ebenfalls das `AFK`-Label, würde der Planner sowohl die Spec als auch ihre Tickets greifen und doppelte, konfligierende Branches erzeugen. Deshalb: `AFK` nur auf Tickets.

## Ausführung: AFK und HITL

Diese Labels sagen aus, **wer** ein umsetzungsreifes Issue abarbeitet. Sie sind bewusst von der Triage getrennt (siehe unten) — ein Issue kann kategorisiert sein, lange bevor entschieden ist, wer es umsetzt.

- **`AFK`** — *away from keyboard.* Das Issue ist vollständig spezifiziert und von einem autonomen Agenten ausführbar. Der Sandcastle-Planner (`.sandcastle/plan-prompt.md`) greift genau die offenen Issues mit diesem Label. In den Skills heißt diese Rolle `ready-for-agent`.
- **`HITL`** — *human in the loop.* Das Issue braucht menschliche Umsetzung und wird nicht an einen AFK-Agenten übergeben. In den Skills heißt diese Rolle `ready-for-human`.

Historie: Diese beiden Labels hießen früher `Sandcastle` (→ `AFK`) und `ready-for-human` (→ `HITL`). Das Automatisierungssystem selbst heißt weiterhin *Sandcastle*; nur das Label wurde umbenannt.

## Wayfinder

Die `wayfinder:*`-Labels gehören zum `/wayfinder`-Fluss, der eine große, noch unklare Aufgabe als Karte aus Untersuchungs-Tickets auf dem Tracker führt (siehe `.agents/skills/wayfinder/SKILL.md`).

- **`wayfinder:map`** — Die kanonische Wegkarte eines Vorhabens. Das Map-Issue ist die zentrale Karte; seine Tickets sind Kind-Issues davon.
- **`wayfinder:grilling`** — Ein HITL-Ticket-Typ: Die Entscheidung wird im Gespräch per `/grilling` geklärt.
- **`wayfinder:research`** — Ein Ticket-Typ für Recherche bzw. Untersuchung einer offenen Frage.
- **`wayfinder:prototype`** — Ein Ticket-Typ für einen Prototyp zur Klärung einer Design-Frage.
- **`wayfinder:task`** — Ein Ticket-Typ für eine konkrete Aufgabe bzw. Entscheidung auf der Karte.

## Triage / Kategorisierung

Diese Labels beschreiben, **was** ein Issue ist. Es sind GitHub-Standard-Labels; im Projekt aktiv genutzt werden vor allem `enhancement` und `question`.

- **`enhancement`** — Neues Feature oder Verbesserungswunsch.
- **`question`** — Es fehlen noch Informationen bzw. es ist eine offene Frage.
- **`bug`** — Etwas funktioniert nicht wie erwartet.
- **`documentation`** — Verbesserungen oder Ergänzungen an der Dokumentation.
- **`wontfix`** — Wird nicht bearbeitet.
- **`duplicate`** — Issue oder PR existiert bereits.

Weitere GitHub-Standard-Labels (`good first issue`, `help wanted`, `invalid`) existieren, werden aber im Projekt derzeit nicht verwendet.
