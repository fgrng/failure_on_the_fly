---
status: accepted
---

# Die Prompt-Vorlagen dürfen die Lehrperson als Klassenlehrperson nennen, nicht als Zuhörerin

Dieses ADR führt ADR-0054 nach (#518). ADR-0054 hält die erfahrene Lehrperson
ganz aus `VERTRAG_PROMPT` heraus: Eine simulierte Schüler:in, die weiß, dass
ihre Lehrerin zuhört, hat einen Grund, weniger freimütig über ihren Rechenweg
zu sprechen. Diese Regel ändert sich.

## Anlass

Die Rahmenhandlung nennt der Teilnehmer:in die Lehrperson beim Namen. Fragt die
Teilnehmer:in die simulierte Schüler:in, bei wem sie Unterricht hat, kennt die
Schüler:in den Namen nicht und muss ausweichen oder einen erfinden. Beides
bricht die Szene. Die Prompt-Entwürfe ab dem 19.10.2026
(`docs/simulation_prompts/`) nennen die Lehrperson deshalb in `<rolle>`:
„Du sitzt im Fach $fach bei $lehrperson_anrede $lehrperson_name an einer
Aufgabe zum Thema $thema.“

## Entscheidung

`VERTRAG_PROMPT` enthält zusätzlich `$lehrperson_name` und
`$lehrperson_anrede`. Die Anrede (`Frau`, `Herr`) entsteht aus dem Geschlecht
der Lehrperson über dieselbe Zuordnung wie in der Rahmenhandlung; es gibt sie
im Code nur einmal. `VERTRAG_LEHRPERSON` und `VERTRAG_BEWERTER` leiten sich von
`VERTRAG_PROMPT` ab und erhalten beide Platzhalter mit, damit die Evalvorlagen
dieselben Vignettenwerte sehen wie die Simulation.

`$lehrperson_geschlecht`, `$lehrperson_pronomen` und `$lehrperson_possessiv`
bleiben der Rahmenhandlung vorbehalten. Der Prompt braucht von der Lehrperson
nur, wie die Schüler:in sie nennt, nicht, wie man über sie spricht.

## Warum die Störvariable damit vertretbar ist

Die Störvariable aus ADR-0054 ist eine **zuhörende** Lehrperson, nicht eine
**bekannte**. Dass eine Schüler:in ihre Klassenlehrperson kennt, ist der
Normalfall jeder Unterrichtsstunde und verändert ihre Auskunftsfreude
gegenüber einer Praktikant:in nicht. Der Name allein sagt nichts über
Anwesenheit.

Die Grenze trägt deshalb die Vorlage: Eine Prompt-Vorlage nennt die Lehrperson
als die Lehrperson der Klasse und rahmt sie **nicht** als anwesend, zuhörend
oder bewertend. Das prüft kein Code; es ist Prompt-Engineering der
Administrator:in wie jede andere Formulierung der Vorlage.

## Erwogene Optionen

- **Lehrperson weiter aus dem Prompt heraushalten** — verworfen. Die
  Schüler:in könnte die naheliegende Frage nach ihrer Lehrperson nicht
  beantworten.
- **Alle `$lehrperson_*`-Platzhalter im Prompt erlauben** — verworfen. Pronomen
  und Possessiv braucht der Prompt nicht, und jeder zusätzliche Platzhalter lädt
  dazu ein, die Lehrperson im Prompt mehr als zu nennen.
- **Anrede im Prompt aus einer eigenen Zuordnung** — verworfen. ADR-0054
  verlangt, dass jede Liste eine bleibt.

## Folgen

- Bestehende finale Kern-Fassungen bleiben gültig: Der Vertrag ist eine
  Obergrenze und wird nur größer. Die Vignette trägt Name und Geschlecht der
  Lehrperson schon; eine Datenmigration entfällt.
- Die Platzhalterhinweise unter den Prompt-Vorlagen und die Platzhalterknöpfe
  des Evalkatalogs zeigen die beiden neuen Namen, weil sie den Vertrag lesen.
- Eine Vignette ohne Lehrperson-Geschlecht lässt sich nicht mehr in eine
  Prompt-Vorlage rendern. Gespeicherte Vignetten tragen es immer (ADR-0054).
