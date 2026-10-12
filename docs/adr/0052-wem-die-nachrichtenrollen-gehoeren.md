---
status: accepted
---

# Wem die Nachrichtenrollen gehören

Jede `user`-Nachricht an die simulierte Schüler:in ist eine Ansprache der Teilnehmer:in, ohne Ausnahme. Der Arbeitskontext instanziiert die Rolle und ist nicht Teil des Gesprächs; er steht deshalb im System-Prompt. Anlass (#269): Als erste `user`-Nachricht hielt das Modell den Arbeitskontext für die erste Frage der Teilnehmer:in, und Metafragen wie „Was hatte ich dich als Erstes gefragt?“ beantwortete es uneinheitlich.

Dieselbe Ordnung gilt für die simulierte Lehrperson, gespiegelt: Ihre eigenen Äußerungen, auch die wörtlich vorgegebenen fester Inputschritte, reisen als `assistant`, die Äußerungen der Schüler:in als `user`, beide nativ und ohne Denkspur. Die Inputstrategie steht allein im System-Prompt. Weil die Lehrperson das Gespräch eröffnet, trägt ihr erster Zug eine feste technische `user`-Nachricht; jede weitere `user`-Nachricht ist eine Äußerung der Schüler:in.

Der Bewerter führt kein Gespräch. Er erhält den Verlauf samt Denkspur im System-Prompt; seine einzige `user`-Nachricht ist das Kriterium.

## Altbestand

Gepinnte Fassungen sind unveränderlich (ADR-0035), die Nachrichtenordnung ist Code. Sie gilt deshalb ab dem Deploy für alle Fassungen, auch für solche in laufenden Erhebungen; dass eine Datenspur Gespräche beider Ordnungen enthält, nehmen wir hin.

- **Simulationskern**: Das Feld `user_prompt_vorlage` bleibt in Datenbank und Datenspur-Export (ADR-0029). Neue Fassungen lassen es leer und schreiben den Arbeitskontext in die System-Prompt-Vorlage. Ist es gefüllt, wird es gerendert an den System-Prompt angehängt. Formular und Übersicht zeigen es nur, wenn es nicht leer ist.
- **Lehrperson-Vorlage**: `$verlauf` gehört nicht mehr zu ihrem Vertrag. Für Altvorlagen wird er als leerer Text eingesetzt, damit sie weiter rendern, ohne den Verlauf doppelt zu führen.

## Erwogene Optionen

- **Die User-Prompt-Vorlage streichen und beide Felder zusammenführen** — verworfen. Altfassungen hätten ein Feld, das es nicht mehr gibt: Entweder würden finale Fassungen umgeschrieben (verbietet ADR-0035), oder es bliebe ein dauerhaft zweiter Codepfad. Zudem bräche der Exportkontrakt für bereits erhobene Daten.
- **Nur den Prompttext ändern, den Nachrichtenaufbau lassen** — verworfen. Die erste `user`-Nachricht bliebe mehrdeutig.
- **Die Inputstrategie als letzte `user`-Nachricht der Lehrperson** — verworfen. Sie sähe für die Lehrperson aus wie eine Äußerung der Schüler:in.

## Folgen

- Ob und wie sich die Schüler:in an das bisherige Gespräch erinnert, regelt allein der Prompttext einer Kern-Fassung, nicht der Code.
- Der Standardkern behält seine gefüllte User-Prompt-Vorlage; frische Instanzen zeigen das Feld, bis eine neue Fassung es leert.
