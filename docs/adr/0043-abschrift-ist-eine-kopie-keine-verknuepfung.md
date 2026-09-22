---
status: accepted
---

# Die Abschrift ist eine Kopie, keine Verknüpfung

Wer an einer Erhebung teilgenommen hat, kann ihre Sitzungen mit dem Teilnahme-Token in das eigene Nutzerkonto holen. Der Import legt dafür eine **neue Teilnahme** an und kopiert Sitzungen, Gesprächsschritte, Fehlversuche, Diagnosen und Vignettenpositionen als echte Zeilen derselben Modelle hinein. Die bestehende `Erhebungsbindung` wird ausschließlich **gelesen**: kein Fremdschlüssel, kein gespeichertes Token, kein Hash, kein Merker auf der Erhebungsseite. Die entstehende `training.Abschrift` hält Teilnahme, Konto, den **Namen der Erhebung als Text** und den Importzeitpunkt.

Der naheliegende Gegenentwurf — dieselbe Teilnahme bekommt zusätzlich eine konto-tragende Bindung — wäre technisch trivial und genau deshalb gefährlich: Konto ↔ Token wäre ein Join über zwei Kanten. Die Kopie vermeidet diesen Pfad strukturell (ADR-0006, ADR-0018).

Die Kante zeigt von `training` nach `erhebungen` und nie umgekehrt. `erhebungen` ist die App, die nichts von Konten wissen darf; eine Funktion dort, die ein `Konto` entgegennimmt, wäre der erste Riss in der Trennung, die dieser ADR absichert — auch ohne Fremdschlüssel.

## Considered Options

- **Geteilte Teilnahme mit zweiter Bindung** — verworfen: stellt die verbotene Verknüpfung als Join wieder her.
- **Token-Dauerzugriff auf die Forschungsdaten** — verworfen: die Teilnehmer:in läse dann das Forschungsdatum selbst, und dessen Lebenszyklus gehört der Forschenden.
- **Eingeloggte Erhebungsteilnahme** — verworfen: sie hebt ADR-0006 auf.
- **Deduplizierung wiederholter Importe** — verworfen: sie verlangte, dass sich das System merkt, welches Token in welches Konto ging.

## Consequences

- **Die Kopie ist inhaltsgleich mit dem Forschungsdatum** und daher über den Transkripttext matchbar. Zugesichert ist deshalb nicht Unverknüpfbarkeit, sondern: *das System führt die Verknüpfung nicht und bietet sie nicht an.*
- **Art. 15 DSGVO erfasst die Kopie samt Denkspur.** Sie liegt unter einem Konto und ist damit personenbezogen — obwohl ADR-0005 die Denkspur der Teilnehmer:in nie zeigt. Die Sichtbarkeitszusage sitzt im Rendering, nicht in den Daten: Der CheckConstraint auf dem Gesprächsschritt verlangt Denkspur und Äußerung gemeinsam, eine denkspurfreie Kopie verlöre auch die Äußerungen.
- **Die kopierten Sitzungen führen die Importzeit, nicht die Spielzeit.** `erstellt_am` ist `auto_now_add`. Wo in der Abschrift ein Datum erscheint, ist es als Importzeitpunkt zu beschriften; die Reihenfolge der Vignetten kommt aus der Vignettenposition und ist davon unberührt.
- **Fragebogen-Antworten werden nicht kopiert.** Die `ItemAntwort` hängt an der Erhebungsbindung; sie ist Messinstrument der Forschenden und stünde ohne den Wortlaut ihrer Items als bedeutungsloser Wert da. Die Abschrift enthält Transkript, Ausgang und eigene Diagnose — sonst nichts.
- **Der Hebel der Forschenden ist das Archivieren.** Abgelehnt wird, was nicht abgeschlossen ist oder zu einer archivierten Stichprobe oder Erhebung gehört; die Phase der Stichprobe spielt keine Rolle. Jede Ablehnung liefert dieselbe Meldung ohne Grund, damit der Import kein Orakel über fremde Tokens wird.
- **Abschriften sind kontoprivat** und gehören nicht in die Trainingsdaten einer Ausbilder:in: Deren Abfragen hängen an der `Trainingsbindung`.
