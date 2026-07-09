---
status: accepted
---

# Ein zentraler, fach-agnostischer Simulationskern, den die Vignette beim Finalisieren pinnt

Verhaltens- und Logikregeln der Simulation werden **einmal zentral spezifiziert**, nicht pro Vignette neu erfunden. Es gibt konzeptionell genau **eine Kern-Linie für alle Vignetten**, über alle Fächer hinweg. Der Kern ist ein versioniertes Artefakt (siehe ADR-0003) und wird ausschließlich von Administrator:innen gepflegt — nicht von Autor:innen, deren Aufgabe allein die Beschreibung des Fehlermusters ist.

## Der Kern hat zwei Hälften, die sich nie berühren

Die **Prompt-Vorlagen** — System-Prompt-Vorlage und User-Prompt-Vorlage — sprechen ausschließlich zur simulierten Schüler:in. Die **Rahmenhandlung** spricht ausschließlich zur Teilnehmer:in: eine Einleitung mit den Akteuren und der Hospitationssituation, und ein Debrief, in dem die erfahrene Lehrperson um die Diagnose bittet. Kein Wort der Rahmenhandlung erreicht je einen Prompt.

Die Rahmenhandlung wird **je Sitzung** dargeboten, nicht je Teilnahme: Jede Vignettensitzung ist ihre eigene Hospitation. Eine Sitzung, die ihren narrativen Rahmen von außen bezöge, wäre nicht mehr die atomare Auswertungseinheit, als die sie definiert ist. Die Rahmenhandlung ist selbst eine Vorlage — ihre Platzhalter füllt die Vignette mit ihren Akteuren und ihrem Unterrichtskontext (siehe ADR-0010).

Die Situationsrahmung existiert damit zweimal in verschiedenen Worten: als Einleitung für den Menschen und als Rollenanweisung im System-Prompt. Beide liegen im selben Artefakt und werden gemeinsam versioniert; mehr Schutz gegen ihr Auseinanderdriften gibt es nicht.

## Wo das Pinning sitzt

Ein **Vignettenentwurf pinnt bei Anlage** den aktuellsten finalen Kern. Entsteht der Entwurf durch Bearbeiten einer finalen Fassung, **erbt er den Kern der Vorgängerin** — eine Korrektur am Lernauftrag darf das Gesprächsverhalten nicht mitverändern. Die Autor:in kann ausdrücklich auf den aktuellsten Kern **vorspulen**; ein Kern-Wechsel ist immer eine bewusste Handlung, nie ein Nebeneffekt. Das Finalisieren friert den Pin ein.

Erhebung und Training pinnen keinen eigenen Kern, sondern erben ihn transitiv über die finalen Vignettenfassungen. Sie **dürfen Vignetten mit verschiedenen Kernen mischen**; es gibt keine Einheitlichkeits-Invariante.

Davon **getrennt** steht die **Modell-Konfiguration** (Sprachmodell und Parameter). Sie ändert sich aus anderen Gründen und durch andere Personen — Betrieb und Kosten, nicht Didaktik. Ein Modellwechsel darf keine neue Kern-Version erzeugen. Ihr Pinning regelt ADR-0013.

## Considered Options

- **Die Vignette pinnt bei Erstellung, die Erhebung erzwingt Einheitlichkeit über alle enthaltenen Vignetten** — verworfen. Eine Kern-Version aus Betriebsgründen hätte jede beteiligte Vignette zu einer inhaltsleeren Neuversion gezwungen, deren einziger Unterschied eine Fremdschlüsselnummer ist. Die Vignettenhistorie soll die didaktische Entwicklung eines Fehlermusters erzählen, nicht Kern-Updates protokollieren.
- **Die Erhebung pinnt den Kern und überschreibt, was die Vignetten mitbringen** — verworfen. Ein Training hat keinen Aktivierungszeitpunkt und bliebe ohne Kern.
- **Der Kern wird erst beim Sitzungsstart aufgelöst, die Erhebung friert ihn ein** — verworfen. Autor:innen verlassen sich auf das Verhalten, das sie im Probelauf gesichtet haben; der gepinnte Kern gehört zu diesem Verhalten und damit zur Vignette.
- **Der Entwurf löst den Kern dynamisch auf und pinnt erst beim Finalisieren** — verworfen. Erscheint zwischen dem letzten Probelauf und dem Finalisieren eine neue Kern-Fassung, finalisiert die Autor:in still gegen einen Kern, den sie nie gesehen hat.

## Consequences

- Leitprinzip 4 („einmal zentral spezifiziert und versioniert") wird strukturell erzwungen, nicht nur konventionell.
- Autor:innen finalisieren nur gegen einen Kern, den sie testen konnten. Der Preis: Eine Vignettenhistorie kann über viele Fassungen auf einem sehr alten Kern verharren. Dagegen hilft nur ein Hinweis am Entwurf, dass ein neuerer Kern verfügbar ist.
- Eine Erhebung kann Vignetten mit verschiedenen Rahmenhandlungen enthalten. Teilnehmende erleben dann leichte Tonwechsel zwischen den Sitzungen. Das ist der bewusst gezahlte Preis dafür, dass ältere Vignetten ohne Neuversionierung weiterlaufen.
- Der Kern ist fach-agnostisch, aber **nicht sprach-agnostisch**. Mehrsprachigkeit würde die Kern-Linie vervielfachen und das Prinzip aufweichen; die App ist deshalb vorerst deutschsprachig.
