---
status: accepted
---

# Der Probelauf ist eine schreibfreie Funktion über einem Tripel

Ein **Probelauf** ist eine schreibfreie Sitzung über einem Tripel aus **Vignette, Simulationskern und Modell-Konfiguration**. Er persistiert nichts, verändert nichts und zeigt als einziger Ort die Denkspur live. Er ist damit keine Eigenschaft der Vignette, sondern eine Funktion, deren Freiheitsgrade die Rolle bestimmt:

- Die **Autor:in** wählt ihren Vignettenentwurf. Kern und Modell-Konfiguration sind vorgegeben: der an ihrem Entwurf gepinnte Kern und die aktive Konfiguration. Sie hat keine Wahl, und laut ADR-0004 soll sie keine haben.
- Die **Administrator:in** wählt Kern und Modell-Konfiguration frei, auch Entwürfe und noch nicht aktive Konfigurationen. Als Vignette nimmt sie irgendeine finale — deren Pin sich dabei **nicht** ändert, denn der Probelauf schreibt nichts.

Der Probelauf durchläuft die **volle Sitzung**: Rahmenhandlung, Diagnosegespräch, Debrief und Diagnosefeld. Ablauf und Ansicht sind identisch mit denen einer Sitzung; der einzige Unterschied ist die Persistierung. Die Autor:in sieht, was die Teilnehmer:in sehen wird, plus die Denkspur, die diese nie sieht. Auch die Diagnose wird nicht persistiert.

## Consequences

- `CONTEXT.md` definiert die Diagnose als etwas, das „erfasst, nicht bewertet" wird (ADR-0009). Im Probelauf wird sie **weder** erfasst noch bewertet: Sie wird eingegeben, damit die Autor:in den Debrief so erlebt wie die Teilnehmer:in, und dann verworfen. Das „erfasst" von ADR-0009 grenzt gegen *bewerten* ab, nicht gegen *verwerfen*, und gilt für Sitzungen einer Teilnahme.

- Das System weiß nicht, ob eine Vignette je getestet wurde. „Finalisieren nur nach erfolgreichem Probelauf" ist damit nicht erzwingbar und bleibt Disziplin der Autor:in. Dasselbe gilt für den Kern.
- Ein Probelauf einer Administrator:in gegen einen Kern-Entwurf läuft mit einer Vignette, die für einen anderen Kern geschrieben wurde. Ihre Felder passen, weil der Vertrag fest ist (ADR-0010) — ihr Fehlermuster wurde gegen diesen Kern nie geprüft. Das ist richtig so: Die Administrator:in prüft den Kern, nicht die Vignette.
- Probeläufe verursachen Modellkosten, ohne eine Spur zu hinterlassen. Ob das Betreibende interessiert, ist eine Frage der Admin-Seite.
- Administrator:innen können eine neue Modell-Konfiguration erproben, bevor sie sie aktiv schalten (ADR-0013).
