# Sandcastle-Probelauf

Der Sandcastle-Ablauf über Integrations-Branches und Pull Requests (#335) ist bisher nur gegen Fakes getestet. Der Sandcastle-Probelauf schickt eine minimale Probe-Spec mit zwei Tickets einmal echt durch diesen Ablauf, vom Integrations-Branch `spec/<n>` bis zum PR nach `main` (vgl. #344). Er zeigt, ob die echte Verdrahtung mit `git` und `gh` trägt; Anwendungscode ändert er nicht.

## Geprüfte Schritte

Aufruf: `npm run sandcastle -- --spec <n>`. Die Regeln dazu stehen in `docs/agents/issue-tracker.md`, Abschnitt „Abschluss von Arbeit“.

1. **Integrations-Branch**: `spec/<n>` entsteht nach `git fetch origin` von `origin/main`.
2. **Ticket-Merge und Schließen**: Das erste Ticket wird umgesetzt und nach `spec/<n>` gemergt. Das Skript prüft den Merge mit `git merge-base --is-ancestor` und schließt das Ticket selbst.
3. **Reihenfolge nach Blocked-by-Kante**: Das zweite Ticket wird erst eingeplant, wenn sein Blocker in `spec/<n>` gemergt und geschlossen ist; danach wird es ebenso gemergt und geschlossen.
4. **Abschlussphase**: Sind beide Tickets geschlossen, laufen `code-review` über die ganze Spec gegen `main`, die Behebung der Befunde und der PR-Text mit dem Skill `pr`.
5. **PR mit `Closes #<n>`**: Sandcastle pusht `spec/<n>` und legt den PR nach `main` an; der PR-Text endet mit `Closes #<n>`.
6. **Merge von Hand**: Die Maintainerin bzw. der Maintainer mergt den PR bei grüner CI mit Merge-Commit; dabei schließt die Spec.
