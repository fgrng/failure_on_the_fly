# Issue-Tracker: GitHub

Issues und Specs liegen als GitHub-Issues in diesem Repo; Zugriff über die `gh`-CLI.

- **Lesen**: `gh issue view <n> --comments`.
- **Auflisten**: `gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'`, gefiltert mit `--label` / `--state`.
- **Arbeit abschließen**: `gh issue close <n> --comment "..."`, nach den Regeln unter [Abschluss von Arbeit](#abschluss-von-arbeit).
- **PRs as a request surface: no.** _(`/triage` liest dieses Flag.)_ PRs kommen hier aus Integrations-Branches und sind Arbeit der Maintainerin bzw. des Maintainers, keine Anfragen von außen.

## Abschluss von Arbeit

Aus Sandcastle kommt Code nur über einen Pull Request von einem **Integrations-Branch** nach `main`:

- Spec `<n>` (Label `Spec`) hat einen eigenen Integrations-Branch `spec/<n>`, der beim ersten Gebrauch von `main` entsteht. Ihre Tickets zweigen davon ab und werden dorthin zurückgemergt.
- Tickets ohne Eltern-Spec teilen sich den fortlaufenden Integrations-Branch `sandcastle/standalone`.

Tickets ohne Spec, die interaktiv statt über Sandcastle umgesetzt werden, landen direkt auf `main`. Die Commit-Nachricht verweist als `(#<n>` auf das Ticket; daran erkennt Sandcastle, dass ein solcher Blocker auf `main` liegt.

Sandcastle führt zu Beginn jedes Laufs `git fetch origin` aus und misst alles gegen `origin/main`; `main` heißt im Folgenden `origin/main`. Den Checkout, aus dem der Lauf gestartet wurde, fasst Sandcastle nie an: Ein dort ausgecheckter Integrations-Branch wird für den ganzen Lauf ausgelassen (kein Update, keine seiner Tickets, keine Abschlussphase), und das Log meldet das.

`npm run sandcastle -- --spec <n>` wirkt nur auf Spec `<n>`: Der Lauf plant nur ihre Sub-Issues ein, aktualisiert nur `spec/<n>` und schließt nur diese Spec ab. `sandcastle/standalone` und andere `spec/<m>` bleiben unberührt: kein Update, kein Neustart, kein Push, kein PR.

Jedes Issue schließt bei seinem eigenen Merge:

- **Ticket**: schließt, sobald sein Branch im Integrations-Branch liegt, nicht erst auf `main`. Sandcastle schließt es selbst, nachdem es den Merge mit `git merge-base --is-ancestor` geprüft hat; Agents lassen es offen. Endet der Merger ohne Abschlusssignal, setzt Sandcastle den Integrations-Branch auf den Stand vor dem Merger zurück und schließt keines seiner Tickets.
- **Blocker aus derselben Spec**: gilt als erledigt, sobald er in `spec/<n>` gemergt ist (dann schließt ihn das Skript).
- **Blocker aus einer anderen Spec**: gilt erst als erledigt, wenn diese Spec geschlossen und nach `main` gemergt ist, über ihren PR oder, bei einem Merge von Hand, weil `spec/<m>` in `main` enthalten ist.
- **Blocker ohne Spec**: gilt als erledigt, sobald er auf `main` liegt: Sein Branch `sandcastle/issue-<n>` ist dort enthalten, oder ein Commit dort verweist als `(#<n>` auf ihn (diese Commit-Konvention beibehalten).
- **Spec**: schließt, wenn ihr PR nach `main` gemergt wird, über das `Closes #<n>` am Ende des PR-Texts. Dieser PR ist der einzige Weg, auf dem eine Spec schließt. Eltern-Issues bleiben deshalb beim Schreiben, Umsetzen und Schließen von Tickets unangetastet (Status, Text, Labels).

Sind alle Sub-Issues einer Spec geschlossen und hat `spec/<n>` keinen offenen PR, führt Sandcastle die **Abschlussphase** der Spec aus: `code-review` über die ganze Spec gegen `main`, Behebung der Standards- und Korrektheitsbefunde, Streichen der Tests auf die Migrationen, die `spec/<n>` gegenüber `main` neu anlegt (ADR-0031; ohne neue Migrationen entfällt der Schritt, und ohne Abschlusssignal bleibt der PR aus), PR-Text mit dem Skill `pr` und den Spec-Befunden als „Offene Punkte“, dann Push und PR von `spec/<n>` nach `main`. Eine gescheiterte Abschlussphase versucht erst der nächste Lauf erneut, nicht eine spätere Iteration desselben Laufs. Ab dann ist die Spec **gesperrt**: Sandcastle kommentiert ihre übrigen Tickets und stellt sie von `ready-for-agent` auf `ready-for-human` um. Spätere Arbeit gehört in eine neue Spec.

`sandcastle/standalone` hat keine Abschlussphase. Hat der Branch Commits, die nicht auf `main` liegen, pusht Sandcastle ihn und legt seinen PR an oder ergänzt ihn; nach dem Merge dieses PRs beginnt der Branch im nächsten Lauf neu von `main`.

Die Maintainerin bzw. der Maintainer mergt jeden PR von Hand, mit Merge-Commit und erst bei grüner CI. Der Merge-Commit hält die Commits je Ticket samt Issue-Referenzen in der Historie von `main`, für `code-review` und `retro`.

## Beziehungen: Sub-Issues und Blocker-Kanten

Beide Endpunkte erwarten die numerische **Datenbank-`id`** des anderen Issues (`gh api repos/{owner}/{repo}/issues/<n> --jq .id`, nicht die `#number` und nicht die `node_id`) als typisierte Ganzzahl (`-F`, nicht `-f`). Eltern-Issues und Blocker zuerst anlegen. `gh api` setzt `{owner}/{repo}` selbst ein.

```bash
# Kind als Sub-Issue einer Spec oder einer Wayfinder-Map
gh api --method POST repos/{owner}/{repo}/issues/<parent>/sub_issues -F sub_issue_id=<child-id>
# Blocker-Kante (native Abhängigkeit, kein „Blocked by #N“ im Text)
gh api --method POST repos/{owner}/{repo}/issues/<blocked>/dependencies/blocked_by -F issue_id=<blocker-id>
# prüfen (gh issue view --json blockedBy liefert kein .number)
gh api repos/{owner}/{repo}/issues/<blocked>/dependencies/blocked_by --jq '[.[].number]'
```

Ein Ticket ist unblockiert, wenn `issue_dependencies_summary.blocked_by` 0 ist (gezählt werden nur offene Blocker).

## Wayfinding

Für `/wayfinder`.

- **Map**: ein Issue mit Label `wayfinder:map`; sein Text hat die Abschnitte Notes / Decisions-so-far / Fog.
- **Kind-Ticket**: ein Sub-Issue der Map mit Label `wayfinder:<type>` (`research`/`prototype`/`grilling`/`task`).
- **Frontier**: die offenen, nicht zugewiesenen Sub-Issues der Map ohne offene Blocker; das erste in Map-Reihenfolge gewinnt.
- **Beanspruchen**: `gh issue edit <n> --add-assignee @me`, der erste Schreibzugriff der Sitzung.
- **Auflösen**: die Antwort kommentieren, das Ticket schließen, dann einen Kontext-Zeiger (Kern + Link) an Decisions-so-far der Map anhängen.
