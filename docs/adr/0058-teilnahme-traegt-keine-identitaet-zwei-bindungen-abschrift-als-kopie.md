---
status: amended
amended-by: ["fluechtige-inhalte-im-kurzlebigen-speicher"]
---

# Die Teilnahme trägt keine Identität: zwei Bindungen, Abschrift als Kopie

> **Nachgeführt durch ADR „Flüchtige Inhalte liegen in einem kurzlebigen
> Speicher, außerhalb der Forschungsdatenbank und getrennt von der
> Konto-Session“:** Eine Abschrift entsteht auch aus einer flüchtigen
> Teilnahme, über dasselbe Token-Formular und mit denselben Regeln, solange
> deren Inhalte vorgehalten werden; danach wird das Token wie jedes
> unbrauchbare ohne Grund abgelehnt. Sie gleicht der normalen genau, samt
> Denkspur. Die Zusage „Das System führt die Verknüpfung nicht“ gilt auch für
> die Browser-Session: Teilnahme-Tokens stehen nicht mehr in der Konto-Session,
> sondern in einem eigenen signierten Cookie.

Dieses ADR fasst den Stand von ADR-0018 (samt Nachführungen durch ADR-0043
und #235) und ADR-0043 (samt Nachführung durch ADR-0049) zusammen und ersetzt
beide. Es schärft ADR-0006 und ersetzt keine seiner Aussagen; die flüchtige
Teilnahme regelt ADR-0045, die Einsicht ADR-0049.

## Die Teilnahme ist ein Objekt ohne Identität

Die **Teilnahme** ist genau ein Objekt, so wie `GLOSSARY.md` sie definiert: die
Klammer, unter der alle Sitzungen einer Person in genau einem Training oder
genau einer Erhebung zusammengefasst sind. Sie trägt ihre Sitzungen, ihre
**Teilnahmekennung** (ein kurzer gespeicherter Zufallswert für Einsicht und
Export, ADR-0049) und sonst nichts: weder Training noch Stichprobe, weder
Nutzerkonto noch Teilnahme-Token.

Woran eine Teilnahme hängt und wer hinter ihr steht, liegt in **Bindungen**,
die jeweils ihrer eigenen App gehören und mit einer 1:1-Beziehung auf die
Teilnahme zeigen:

- `training.Trainingsbindung` hält Training und Nutzerkonto.
- `erhebungen.Erhebungsbindung` hält Stichprobe und Teilnahme-Token.
- `training.Abschrift` hält Konto, den Namen der Erhebung als Text und den
  Importzeitpunkt (siehe unten).

Alle Fremdschlüssel zeigen von `training` und `erhebungen` nach `sitzungen`;
`sitzungen` kennt keinen seiner Aufrufer (ADR-0055).

## Pseudonymität im Schema und in einer Prüfung

ADR-0006 verlangt, dass Erhebungs-Teilnahmen strikt von jedem Nutzerkonto
getrennt sind. Eine einzige Teilnahme-Tabelle mit nullbaren Spalten für Konto
und Token könnte das erfüllen, solange ein Check-Constraint hält; sie wäre eine
Tabelle, in der die verbotene Verknüpfung *ausdrückbar* ist und nur verboten
wird. Mit getrennten Bindungstabellen hat keine Tabelle eine Spalte für ein
Nutzerkonto und eine für ein Token.

Das reicht allein nicht: Beide Bindungen zeigen auf dieselbe Art Teilnahme,
und nichts hinderte sie daran, auf *dieselbe Zeile* zu zeigen; Konto ↔ Token
wäre dann ein Join über zwei Kanten. Deshalb steht neben dem Schema **eine**
Prüfung: Die gemeinsame Basis `sitzungen.bindungen.Bindung` weist jede Bindung
ab, die eine Teilnahme belegt, an der schon eine Bindung der anderen Art hängt
(`KONTO_TRAGEND`), beim Anlegen wie beim Umhängen, auch über `bulk_create`
und `update`. Sie steht bei der Teilnahme, weil `erhebungen` nichts von Konten
und damit nichts von `training` wissen darf. Der Schutz sitzt im Schema **und**
in dieser einen Prüfung.

## Die Abschrift ist eine Kopie, keine Verknüpfung

Wer an einer Erhebung teilgenommen hat, kann ihre Sitzungen mit dem
Teilnahme-Token in das eigene Nutzerkonto holen. Der Import legt dafür eine
**neue Teilnahme** mit eigener Teilnahmekennung an und kopiert Sitzungen,
Gesprächsschritte, Fehlversuche, Diagnosen und Vignettenpositionen als echte
Zeilen derselben Modelle hinein. Die bestehende `Erhebungsbindung` wird
ausschließlich **gelesen**: kein Fremdschlüssel, kein gespeichertes Token, kein
Hash, kein Merker auf der Erhebungsseite. Die Kante zeigt von `training` nach
`erhebungen` und nie umgekehrt; eine Funktion in `erhebungen`, die ein `Konto`
entgegennimmt, wäre der erste Riss in der Trennung, auch ohne Fremdschlüssel.

Der naheliegende Gegenentwurf, dieselbe Teilnahme bekommt zusätzlich eine
konto-tragende Bindung, wäre technisch trivial und genau deshalb gefährlich:
Er stellte die verbotene Verknüpfung als Join wieder her. Die Kopie vermeidet
diesen Pfad strukturell, und die Prüfung oben weist ihn zusätzlich ab.

Abschriften sind **kontoprivat**. Die Teilnehmer:in kann eine Abschrift
ausdrücklich für ein Training freigeben, dem sie beigetreten ist; dann sieht
der Kreis dieses Trainings sie in seiner Fremdeinsicht. Die Freigabe umfasst
die ganze Abschrift, ist widerrufbar und ruht nach einem Austritt aus dem
Training (ADR-0049).

## Erwogene Optionen

- **Eine Teilnahme-Tabelle mit nullbaren Spalten und korrelierten
  Check-Constraints** — verworfen. Die Pseudonymität hinge an den
  Constraints, und `sitzungen` müsste `training` und `erhebungen` kennen.
- **Zwei Teilnahme-Modelle, je eines in `training` und `erhebungen`** —
  verworfen. Der Begriff Teilnahme hätte kein Gegenstück im Code, die Sitzung
  bräuchte zwei nullbare Fremdschlüssel, und der Export zwei Pfade durch ein
  und dieselbe Aufzeichnung.
- **Geteilte Teilnahme mit zweiter Bindung für die Abschrift** — verworfen:
  stellt die verbotene Verknüpfung als Join wieder her.
- **Token-Dauerzugriff auf die Forschungsdaten** — verworfen: Die
  Teilnehmer:in läse dann das Forschungsdatum selbst, und dessen Lebenszyklus
  gehört der Forschenden.
- **Eingeloggte Erhebungsteilnahme** — verworfen: Sie hebt ADR-0006 auf.
- **Deduplizierung wiederholter Importe** — verworfen: Sie verlangte, dass
  sich das System merkt, welches Token in welches Konto ging.

## Folgen

- Der Export der Datenspur (`erhebungen/export.py`) liest je Datenspur eine
  Teilnahme und joint genau eine Erhebungsbindung; Trainings werden nicht
  exportiert (ADR-0029).
- Eine Teilnahme ohne Bindung ist technisch möglich und fachlich unsinnig. Sie
  entsteht nur, wenn Teilnahme und Bindung nicht in derselben Transaktion
  angelegt werden; das ist eine Regel des Codes, nicht des Schemas.
- Das Löschen der Forschungsdaten einer Erhebung und das Löschen der
  Verbindung zu ihren Teilnahme-Tokens sind zwei getrennte Vorgänge.
- **Die Kopie ist inhaltsgleich mit dem Forschungsdatum** und daher über den
  Transkripttext matchbar. Zugesichert ist nicht Unverknüpfbarkeit, sondern:
  Das System führt die Verknüpfung nicht und bietet sie nicht an. Dass Dritte
  eine freigegebene Abschrift mit dem Erhebungsexport abgleichen können, ist
  bewusst hingenommen (ADR-0049).
- **Art. 15 DSGVO erfasst die Kopie samt Denkspur.** Sie liegt unter einem
  Konto und ist personenbezogen, obwohl ADR-0005 die Denkspur der
  Teilnehmer:in nie zeigt. Die Sichtbarkeitszusage sitzt im Rendering, nicht
  in den Daten: Der CheckConstraint auf dem Gesprächsschritt verlangt Denkspur
  und Äußerung gemeinsam.
- **Die kopierten Sitzungen führen die Importzeit, nicht die Spielzeit.** Wo in
  der Abschrift ein Datum erscheint, ist es als Importzeitpunkt zu beschriften;
  die Reihenfolge kommt aus der Vignettenposition.
- **Fragebogen-Antworten werden nicht kopiert.** Sie hängen an der
  Erhebungsbindung und sind Messinstrument der Forschenden. Die Abschrift
  enthält Transkript, Ausgang und eigene Diagnose, sonst nichts.
- **Der Hebel der Forschenden ist das Archivieren.** Abgelehnt wird, was nicht
  abgeschlossen ist oder zu einer archivierten Stichprobe oder Erhebung
  gehört. Jede Ablehnung liefert dieselbe Meldung ohne Grund, damit der Import
  kein Orakel über fremde Tokens wird.
- Die Abfragen einer Ausbilder:in hängen an der `Trainingsbindung`; eine
  Abschrift erreicht sie nur über die Freigabe.
