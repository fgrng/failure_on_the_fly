# Vision und Scope

## Produktvision

FailureOnTheFly ist ein web-basierter Simulator von Schüler:innen mit spezifischen Fehlvorstellungen, mit dem (angehende) Lehrpersonen ihre diagnostische Kompetenz üben: Sie führen ein kurzes Gespräch mit einer LLM-simulierten Schüler:in, die kongruent zu einer fachbezogenen Fehlvorstellung oder einen systematischen Fehler handelt.

Die Simulation folgt keinem freien „spiel-eine-Schülerin"-Prompt, sondern einer explizit deklarierten Zustandsspezifikation (strukturierte Vignette + zentrale Prompt-Vorlage), die die Fehlvorstellung als stabile, systematisch angewandte Regel modelliert.

Das Produkt dient einerseits als Werkzeug für die Ausbildung von angehenden Lehrpersonen. Gleichzeitig dient es als forschungsbezogenes Erhebungsinstrument, um die diagnostischen Kompetenzen von (angehenden) Lehrpersonen zu untersuchen.

### Leitprinzipien

1. Als Forschungsinstrument steht die saubere, exportierbare, nachvollziehbare Datenspur (Gespräch mit simulierter Schüler:in, Diagnose durch angehende Lehrperson, interne Denkspur der Simulation, zusätzliche Fragebogenantworten) im Zentrum.
2. Das Vignetten-Modell ist fach-agnostisch. Das Projekt zielt damit auch auf eine fachübergreifende Bibliothek dokumentierter Fehlvorstellungen ab.
3. Fachexpert:innen (Didaktik, Psychometrie) sollen Vignetten und Erhebungen pflegen können, ohne Code verändern zu müssen.
4. Verhaltens- und Logikregeln der Simulationen sind *einmal zentral* spezifiziert und versioniert, nicht pro Vignette neu zu erfinden. Zentrale Aufgabe der Vignettenautor:innen ist die Beschreibung der Fehlvorstellung oder systematischer Fehlermuster.

### Zielgruppen und Personas

Studierende oder angehende Lehrpersonen üben das Erkennen und Einordnen von Fehlvorstellungen in Gesprächssituationen mit einer simulierten Schüler:in. Sie beschreiben nach dem Gespräch die Situation und die Fehlvorstellung. 

Ausbilder:innen diskutieren die simulierten Gespräche mit ihren Studierenden im Seminar oder mit (angehenden) Lehrpersonen in Fortbildungen. Die Studierenden lesen und reflektieren dabei die Transkripte ihrer geführten Gespräche.

Vignettenautor:innen beschreiben Fehlvorstellungen und systematsche Fehler. So erstellen Sie Vignetten zum Training diagnostischer Gesprächsführung oder zur Erhebung diagnostischer Kompetenz.

Forschende stellen Vignetten und Fragebogenitems zu Erhebungen zusammen und nutzen diese für Erhebungen an Studierenden und (angehenden) Lehrpersonen. Sie exportieren Gesprächstranskripte, Diagnoseurteile und Fragebogendaten in üblichen Statistikformaten.

Administratoren deployt und wartet Einzelinstanzen für Forschungsprojekte oder Lehrprojekte.

### Funktionsumfang

Der Funktionsumfang gliedert sich entlang der vier Personas: die diagnostische Sitzung für Teilnehmende, der Vignetten-Editor für Autor:innen, das Erhebungs-Management für Forschende sowie Datenspur/Export und Betrieb. Getragen werden alle vom zentral spezifizierten Simulationskern.

#### Diagnostische Gesprächssitzung (Teilnehmendensicht)

Es gibt zwei Modi, in denen eine diagnostische Gesprächssitzung absolviert werden kann. Zum einen die Teilnah
- **Zugang zur Erhebung** über einen Teilnahme-Link (mit oder ohne Registrierung, je nach Erhebungskonfiguration); pseudonyme Teilnahme wird unterstützt.
- **Zugang zu Trainingsumgebung** über die Navigation der Applikation. In diesem Modus können die Teilnehmenden ihre geführten Gespräche hinterher anzeigen lassen.

- **Diagnostisches Gespräch** mit der simulierten Schüler:in. Die Simulation handelt kongruent zur hinterlegten Fehlvorstellung bzw. zum systematischen Fehlermuster und wendet diese als stabile Regel an. Primär verwenden die Teilnehmenden die Spracheingabe (Spracherkennung). Entsprechende texteingabe muss alternativ verfügbar sein. Zudem wird die gesprochene Antwort in Transkriptform angezeigt und in den Chatprotokoll der Konversation eingeblendet.
- **Kontextanzeige** der Vignette, zu der das Gespräch geführt wird (z. B. eine bearbeitete Schüler:innen-Aufgabe).
- **Erfassung der Diagnose** nach dem Gespräch: Freitextliche Beschreibung der beobachteten Fehlvorstellung durch die Teilnehmenden.
- **Begleitende Fragebogenitems** nach dem Gespräch in einer Vignette und / oder nach Abschluss der Erhebung (Ablauf durch die Erhebung gesteuert).
- **Klarer Sitzungsablauf** mit definierten Grenzen (z. B. Nachrichten- oder Zeitbudget) und nachvollziehbarem Fortschritt über mehrere Vignetten hinweg.

#### Vignetten-Editor

Werkzeug für Vignettenautor:innen, um Fehlvorstellungen und systematische Fehler code-frei zu deklarieren. Zentrale Aufgabe ist die Beschreibung der Fehlvorstellung — nicht die Neudefinition von Verhaltensregeln (siehe Simulationskern).

Die Vignetten sind grundsätzlich in den folgenden Kontext eingebunden.
- Die Teilnehmenden schlüpfen in die Rolle einer angehenden Lehrperson die im Unterricht einer erfahrenen Lehrperson hospitiert.
- In einer Arbeitsphase zum individuellen Üben bearbeiten die Schüler:innen einen Lernauftrag (typischerweise eine Aufgabe). Die angehende Lehrperson beobachtet dabei die Schüler:innen und bekommt das Arbeitsheft einer Schüler:in angezeigt, in der eine Fehlvorstellung bzw. ein systematischer Fehler sichtbar wird.
- Die angehende Lehrperson beginnt das Gespräch mit dieser Schüler:in. Sie initiiert das diagnostische Gespräch. Anlass ist die aktuelle Bearbeitung der Lernaufgabe durch die Schüler:in in ihrem Arbeitsheft.
- Die Schüler:in wird von der Simulation gesteuert. Das Verhalten der Schüler:in richtet sich nach der Fehlvorstellung oder dem systematischen Fehler. Sie antwortet entsprechend. Die angehende Lehrperson kann dann in einem simulierten Gespräch wiederum darauf reagieren. Dies dient der Förderung bzw. Erfassung der diagnostischen Gesprächsführung.
- Nach einer definierten Anzahl an Gesprächsschritten wird die Situation unterbrochen. Die erfahrene Lehrperson beendet die Arbeitsphase und führt den Unterricht fort.

Der Vignetten-Editor unterstützt die folgenden Funktionen:
- **Strukturierte Vignette** mit Metadaten (Fach, Themengebiet, Klassenstufe, Quelle/Referenz) und der eigentlichen Beschreibung der Fehlvorstellung bzw. des systematischen Fehlermusters.
- **Deklaration der Fehlvorstellung als Regel**: was die simulierte Schüler:in systematisch (falsch) tut, inklusive typischer Äußerungen, Grenzen der Fehlvorstellung und Reaktion auf Nachfragen.
- **Minimalität** der Vignettenbeschreibung: Die Autor:innen müssen nur die wirklich notwendigen Daten eingeben (Metadaten, Fehlvorstellung). Andere Angaben für die Vignettendarstellung in der Teilnehmendenansicht sind vom System vorgegeben (Name der erfahrenen Lehrperson, Name der simulierten Schüler:in, Situations- und Ablaufbeschreibungen)
- **Fach-agnostisches Schema**, das dieselbe Struktur über alle Fächer hinweg nutzbar macht und die Grundlage der fachübergreifenden Bibliothek bildet.
- **Vorschau und Probelauf**: die Vignette gegen den aktuellen Simulationskern testen, bevor sie in eine Erhebung aufgenommen wird.
- **Versionierung** einzelner Vignetten, sodass frühere Fassungen erhalten und Erhebungen reproduzierbar bleiben.

#### Erhebungs-Management und Fragebogen-Editor

Werkzeug für Forschende, um aus Vignetten und Fragebogenitems eine durchführbare Erhebung zusammenzustellen und ihren Ablauf zu steuern.

- **Zusammenstellung einer Erhebung** aus ausgewählten Vignetten (Reihenfolge, Randomisierung, Zuweisung zu Gruppen/Bedingungen).
- **Fragebogen-Editor** für Items rund um die Gespräche (Item-Typen sind Freitext oder Likert-Skala).
- **Ablauf- und Teilnahmesteuerung**: Instruktionen, Einwilligungstext, Start-/Endseiten, Teilnahmefenster und -limits.
- **Statusübersicht** über den Erhebungsverlauf (angelegt, laufend, abgeschlossen) und die Zahl abgeschlossener Sitzungen.

#### Zentrale Simulations- und Verhaltensspezifikation

Verhaltens- und Logikregeln der Simulation sind einmal zentral spezifiziert und versioniert — nicht pro Vignette neu erfunden (Leitprinzip 4).

- **Zentrale Prompt-Vorlage**, die die deklarierte Vignette in konsistentes Simulationsverhalten übersetzt (Rollentreue, konsequente Anwendung der Fehlvorstellung, altersangemessene Sprache).
- **Versionierung des Simulationskerns**, sodass zu jeder Sitzung nachvollziehbar bleibt, welche Verhaltensspezifikation und welches Modell verwendet wurden.
- **Interne Denkspur** der Simulation wird als Teil der Datenspur erfasst (siehe Datenspur & Export).

#### Datenspur, Export und Auswertung

Als Forschungsinstrument steht die saubere, nachvollziehbare Datenspur im Zentrum (Leitprinzip 1).

- **Vollständige Erfassung pro Sitzung**: Gesprächstranskript, Diagnoseurteil der Teilnehmenden, interne Denkspur der Simulation und Fragebogenantworten — verknüpft mit Vignetten- und Simulationskern-Version.
- **Export in gängige Formate** (z. B. CSV/JSON) zur Weiterverarbeitung in üblicher Statistiksoftware.
- **Pseudonymisierung** der Teilnehmendendaten und Trennung von Kontakt- und Forschungsdaten.

#### Administration und Betrieb

Für Administratoren, die Einzelinstanzen für einzelne Lehr- oder Forschungsprojekte betreiben.

- **Einzelinstanz-Deployment** je Projekt (dedizierte Datenhaltung).
- **Nutzer- und Rollenverwaltung** (Teilnehmende, Autor:innen, Forschende, Administration).
- **Konfiguration** von LLM-Anbindung, Datenschutz-/Aufbewahrungseinstellungen und Instanz-Metadaten.

