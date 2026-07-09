---
status: accepted
---

# Fester Vertrag zwischen Vignette und Prompt-Vorlagen

Die Prompt-Vorlagen des Simulationskerns haben Leerstellen, die die Vignette füllt. Welche Leerstellen es gibt, ist **im Code festgelegt** und nicht vom Kern deklarierbar. Der Kern ist laut ADR-0004 ausdrücklich fach-agnostisch; damit ist die Menge der Leerstellen konstant, und ihre Konstanz ist eine Aussage über die Domäne, keine Bequemlichkeit.

Autor:innen beschreiben **wer** und **was falsch läuft**. Dass die simulierte Schüler:in ihrem Fehlermuster konsequent folgt und auch unter Nachfragen nicht aus der Rolle fällt, leistet die Prompt-Vorlage. Prompt-Engineering ist Sache der Administrator:in.

## Der Vertrag

| Vignettenfeld | Prompt | Nutzeransicht |
|---|---|---|
| Fehlermuster-Beschreibung | ja | nein |
| Lernauftrag | ja | ja |
| Bearbeitungsbeschreibung | ja | nein |
| Arbeitsheft-Inhalt | nein | ja |
| Simulierte Schüler:in (Name, Geschlecht) | ja | ja |
| Erfahrene Lehrperson (Name, Geschlecht) | nein | ja |
| Unterrichtskontext (Fach, Thema, Klassenstufe) | ja | ja |
| Referenzdiagnose | nein | nein |

Der Arbeitsheft-Inhalt bleibt aus dem Prompt heraus, weil er ein Bild sein kann; dafür existiert die Bearbeitungsbeschreibung (ADR-0005). Die erfahrene Lehrperson bleibt heraus, weil eine simulierte Schüler:in, die weiß, dass ihre Lehrerin zuhört, einen Grund hat, weniger freimütig über ihren Rechenweg zu sprechen — eine Störvariable, die niemand kontrolliert und die pro Vignette anders ausfällt. Die Referenzdiagnose bleibt heraus, weil sie eine Notiz ist (ADR-0009).

**Beide Akteure sind Vignettenfelder**, nicht Kernfelder: Dieselbe Schüler:in dürfte sonst in jeder Klassenstufe und jedem Fach dieselbe sein, und dasselbe gilt eine Rolle weiter für die Lehrperson. Namen und Geschlechter werden im Anlegen-Formular zufällig vorbelegt und sind überschreibbar — der Zufall ist eine Freundlichkeit der Oberfläche, keine Eigenschaft der Domäne. Sie werden mit der Vignette versioniert und beim Finalisieren eingefroren; ein Entwurf aus einer finalen Fassung erbt sie.

Die **Rahmenhandlung ist ebenfalls eine Vorlage** und schöpft aus demselben Vertrag, jedoch nur aus dessen Nutzeransicht-Spalte.

## Consequences

- Eine Kern-Fassung lässt sich nur finalisieren, wenn ihre Vorlagen ausschließlich Platzhalter des Vertrags verwenden. Diese Prüfung ist statisch und ruft **kein** Modell auf — eine Invariante, die vom Wohlwollen eines externen Anbieters abhinge, wäre keine.
- Der Vertrag steht an zwei Orten: im Code, der die Platzhalter bereitstellt, und in der Validierung, die sie prüft. Das ist dieselbe Liste, und sie muss eine bleiben.
- Ein **freies Profilfeld** für die simulierte Schüler:in gibt es nicht. Es wäre die Hintertür, durch die Prompt-Engineering unkuratiert zurückkehrt, und es machte Auskunftsfreude und Ausweichverhalten zwischen Vignetten unvergleichbar. Sollten diese Dimensionen gebraucht werden, gehören sie als benannte Stufen in den Kern — eine additive Änderung.
- **Namenskollisionen werden nirgends geprüft**, auch nicht beim Zusammenstellen einer Erhebung oder eines Trainings. Zwei gleichnamige simulierte Schüler:innen in einer Teilnahme sind ein Darstellungsproblem, kein Datenfehler.
- Eine neue Leerstelle bedeutet ein neues Vignettenfeld, eine Migration und eine Code-Änderung. Ein vom Kern deklarierter Vertrag wurde verworfen: Er hätte das Vorspulen eines Vignettenentwurfs auf einen neueren Kern (ADR-0004) scheitern lassen können, womit der Entwurf auf einem alten Kern gefangen wäre.
