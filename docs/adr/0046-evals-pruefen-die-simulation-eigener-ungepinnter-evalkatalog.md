---
status: accepted
---

# Evals prüfen die Simulation, nicht die Diagnose — ein eigener, ungepinnter Evalkatalog

Ob die simulierte Schüler:in einer Vignette ihr Fehlermuster trägt, prüfte bisher allein die Autor:in im Probelauf, von Hand, einmalig und ohne Spur (ADR-0014). Künftig kann sie dafür einen **Evallauf** anstoßen: Eine simulierte Lehrperson führt nach systemweit festgelegten **Evals** kurze **Evalgespräche** mit der simulierten Schüler:in, und ein **Bewerter** beurteilt jedes davon nach Rubriken. Der Begriff „Eval“ folgt dem etablierten Sprachgebrauch für Conversational Agents (Anthropic, *Demystifying evals for AI agents*); „Evaluation“ bleibt gemieden, weil es in der Bildungsforschung die Auswertung meint.

## Was geprüft wird, und was nicht

Evals beurteilen das **Verhalten der Simulation**, nie die **Diagnose der Teilnehmer:in**. ADR-0009 bleibt unberührt: Die Diagnose wird weiterhin erfasst und nicht bewertet. Auch die **Referenzdiagnose** bleibt ohne Wirkung — weder simulierte Lehrperson noch Bewerter sehen sie. Was sie brauchen, trägt die Pflicht-Beschreibung des Fehlermusters, die ohnehin als Regel an die Simulation geschrieben ist. Eine Referenzdiagnose, die die Prüfung läse, hätte Wirkung, und ihr Fehlen schwächte die Prüfung.

## Der Evalkatalog ist ein eigenes Artefakt, und nichts pinnt ihn

Die Evals liegen in einem **Evalkatalog**: einem versionierten Artefakt mit eigener Linie neben dem Simulationskern, gepflegt allein von der Administration, mit genau einer finalen Fassung und dem Lebenszyklus des Kerns (ADR-0035). Er trägt die Evals, die übergreifenden Kriterien, die Lehrperson- und die Bewerter-Vorlage und die Zahl *k* der Wiederholungen.

Jeder Evallauf prüft gegen die **aktuell finale** Fassung. Weder die Vignette noch der Kern pinnen den Katalog. Der Kern-Pin aus ADR-0004 schützt Verhalten, auf das sich Autor:innen nach dem Probelauf verlassen; ein Prüfmaßstab ist kein solches Verhalten, und eine bessere Rubrik soll sofort für alle gelten. Eine neue finale Fassung macht alle Evalläufe gegen die alte **veraltet**, mehr nicht.

Weil Vignetten auf verschiedenen Kern-Fassungen stehen, sind die Kriterien des Katalogs **kern-neutral**: Sie prüfen, was jeder Kern verlangt — Treue zum Fehlermuster, Rollentreue, kein ungefragtes Verraten der Regel —, keine Stilregeln einer bestimmten Kern-Fassung. Das ist eine Pflegeregel der Administration, keine Mechanik.

## Das Urteil ist binär, bestanden heißt jedes Mal, und es sperrt nichts

Jedes Kriterium wird an jedem Evalgespräch als *erfüllt* oder *nicht erfüllt* mit Begründung beurteilt. Über die *k* Wiederholungen eines Evalinputs gilt **pass^k**: bestanden nur, wenn jedes Urteil erfüllt ist — in einer Erhebung trägt jede Teilnehmer:in genau ein Gespräch, eine Schüler:in, die ihr Muster nur manchmal zeigt, verfälscht die Daten. Die **Quote** wird immer mitgezeigt, weil „2 von 3“ und „0 von 3“ verschiedene Befunde sind.

Der Evallauf ist beim Finalisieren einer Vignette ein **Hinweis, keine Sperre** — dieselbe Linie wie „Warnung statt Sperre“ beim überholten Kern (#189). Der Bewerter ist ein Sprachmodell; sein Urteil muss überstimmbar sein, und das Finalisieren darf nicht an einem Hintergrundprozess und drei erreichbaren Anbietern hängen.

## Considered Options

- **Evals als dritter Teil des Simulationskerns** — verworfen. Kernregel und Kriterium wären gemeinsam versioniert und könnten nicht auseinanderdriften; aber jede Rubrik-Korrektur erzeugte eine Kern-Fassung und erreichte keine finale Vignette.
- **Die Vignette pinnt beim Finalisieren auch den Katalog** — verworfen, aus demselben Grund, aus dem ADR-0004 die Einheitlichkeits-Invariante verwarf: Eine Rubrik-Korrektur erzwänge inhaltsleere Vignetten-Neufassungen.
- **Der Bewerter misst an der System-Prompt-Vorlage des gepinnten Kerns** — verworfen. Das Urteil hinge an zwei Modelltexten statt an einem, und dasselbe Kriterium bedeutete je Vignette anderes.
- **Evals je Vignette, von der Autor:in geschrieben** — verworfen. Die Prüfung ist fach-agnostisch und systemweit wie der Kern; Vignettenspezifisches erhält sie über den Vertrag (ADR-0010).

## Consequences

- ADR-0014 gilt nicht mehr ganz: Das System weiß künftig, ob für eine Vignettenfassung ein Evallauf existiert und wie er ausging. Erzwungen wird weiterhin nichts, und der Probelauf bleibt schreibfrei.
- Ein Evallauf wird anders als der Probelauf **aufbewahrt** — je Vignettenfassung höchstens einer, der jüngste ersetzt den älteren.
- Ohne finalen Evalkatalog oder ohne belegte Verwendungen (ADR-0013) sieht die Autor:in nichts von Evals.
- Eine Administrator:in kann einen Katalog-Entwurf nicht vorab erproben. Ein schlechter Katalog richtet wenig Schaden an — Urteile sind Hinweise und berühren keine Datenspur —, und eine neue Fassung überholt ihn sofort. Freie Wahl von Katalog und Konfigurationen gehört in eine spätere Regressionsreihe der Administration.
