---
status: accepted
---

# Der Lebenszyklus wird je versioniertem Artefakt eigenständig implementiert

ADR-0003 gibt **einen** Lebenszyklus vor — Entwurf → final → archiviert, gruppiert von einer linearen Historie —, und **drei** Artefakte durchlaufen ihn: Vignette, Simulationskern und Fragebogen-Item. Sie leben nach ADR-0016 in drei verschiedenen Apps. Es entsteht **keine** gemeinsame Abstraktion: keine abstrakte Basisklasse, keine generische `ContentType`-Tabelle, keine geteilte Übergangs-Funktion. Jede App schreibt ihre Felder, ihre Constraints und ihre Übergänge selbst.

## Die Gemeinsamkeit ist kleiner, als ADR-0003 sie erscheinen lässt

Geteilt sind ein Zustandsautomat aus drei Zuständen und zwei Invarianten: höchstens ein Entwurf je Historie, und Entarchivieren nur, wenn keine Schwesterfassung entsteht. Das ist wenig Substanz. Die Unterschiede sind schon heute sichtbar und werden wachsen:

Die **Vignette** pinnt beim Anlegen einen Kern, kann auf einen neueren vorgespult werden (ADR-0004), friert das Gesprächsbudget ein (ADR-0012) und trägt an ihrer Historie eine Eigentümer:in (ADR-0015). Der **Simulationskern** ist konzeptionell eine einzige Linie, gehört der Administration und kennt keine Eigentümer:in; ob er überhaupt eine benennbare Historie braucht, ist offen. Das **Fragebogen-Item** ist die kleine, wiederverwendbare Einheit ohne beides.

Eine Basisklasse über diesen dreien müsste jede spätere Abweichung durch sich hindurchpressen. Der übliche Ausgang ist ein Flaggenfeld je Abweichung, und dann kostet die Abstraktion mehr, als die Duplikation je gekostet hätte.

## Der Ausschlag gibt die Reversibilität

Von duplizierten Feldern zu einer abstrakten Basisklasse zu wechseln, ist in Django folgenlos: Die Felder landen in denselben Spalten derselben Tabellen, der Migrationszustand bleibt identisch, es entsteht keine Migration. **Die Extraktion später kostet fast nichts.** Der umgekehrte Weg — eine generische Tabelle wieder auseinandernehmen — ist eine Datenmigration über produktive Forschungsdaten.

Wir wählen deshalb die Option, die am wenigsten voraussetzt. Wenn sich in einem Jahr zeigt, dass die drei Lebenszyklen tatsächlich identisch geblieben sind, wird die Basis gezogen. Wenn nicht, war es richtig, sie nie gezogen zu haben.

## Considered Options

- **Abstrakte Basismodelle in einer `versioning`-App, drei erbende Apps** — verworfen, siehe oben. Sie setzt voraus, dass die drei Lebenszyklen gleich bleiben; das wissen wir heute nicht.
- **Eine konkrete Fassungstabelle mit `GenericForeignKey`** — verworfen. Sie kauft polymorphen Zugriff für den Export mit dem Verlust echter Fremdschlüssel, schwächerer Integrität in der Datenbank und einer schwer umkehrbaren Datenmigration.
- **Duplizierte Modelle, aber ein gemeinsamer, parametrisierter Testvertrag über die beiden Invarianten** — verworfen. Er hätte die Drift-Gefahr gedämpft, ohne den Produktivcode zu koppeln; die Entscheidung fiel bewusst für vollständige Unabhängigkeit, einschließlich der Tests.

## Consequences

- Die zwei Invarianten sind an drei Stellen implementiert und können auseinanderlaufen. Ein Fehler im Entarchivieren, der in `vignetten` gefunden und behoben wird, bleibt in `fragebogen_items` liegen. Das trifft die Reproduzierbarkeit, also Leitprinzip 1, und ist der bewusst gezahlte Preis.
- Drei fast identische Modelldateien, die sich in Details unterscheiden, sind für spätere Leser — Mensch wie Agent — mehrdeutig: Eine Abweichung könnte Absicht oder Versehen sein. Wer eine Abweichung einführt, sollte sie kommentieren.
- Ein späterer Architektur-Review wird die gemeinsame Basis erneut vorschlagen, weil der Deletion-Test scheinbar für sie spricht. Dieser ADR ist die Antwort darauf.
- Sollte sich der Simulationskern als Artefakt ohne echte Historie erweisen, kostet das keine Umstellung anderswo.
