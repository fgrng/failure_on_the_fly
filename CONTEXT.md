# FailureOnTheFly

Web-basierter Simulator von Schüler:innen mit Fehlermustern, an dem (angehende) Lehrpersonen diagnostische Gesprächsführung üben und an dem diagnostische Kompetenz erhoben wird.

Dieses Dokument fixiert die gemeinsame Sprache des Projekts. Es ist ein Glossar — keine Spezifikation. Entscheidungen und ihre Begründungen liegen in `docs/adr/`.

## Simulationsinhalt

**Vignette**:
Die konkrete Trainingssituation, in der eine simulierte Schüler:in ein Fehlermuster systematisch anwendet. Sie ist die Einheit, die Autor:innen anlegen, die Trainings und Erhebungen einbinden und die Teilnehmende spielen.
_Avoid_: Fall, Szenario, Case, Aufgabe

**Fehlermuster**:
Die stabile, systematisch angewandte Regel, kongruent zu der die simulierte Schüler:in handelt. Sie wird in genau einer Vignette beschrieben und ist kein eigenständig wiederverwendbares Objekt.
_Avoid_: Fehlvorstellung, systematischer Fehler, Misconception — fachdidaktische Unterkategorien, die dasselbe Modellierungsobjekt meinen.

**Aufgabenkontext**:
Der Teil der Vignette, der den Gesprächsanlass liefert. Besteht aus Lernauftrag, Arbeitsheft-Inhalt und Beschreibung des Arbeitsheft-Inhalt.

**Unterrichtskontext**:
Die fachliche Verortung einer Vignette: Unterrichtsfach, Unterrichtsthema und Klassenstufe.
_Avoid_: Metadaten, Fachbezug, Rahmendaten

**Erfahrene Lehrperson**:
Die Akteurin der Vignette, die die Teilnehmer:in bei der Hospitation begleitet und die im Debrief nach der Diagnose fragt. Sie erscheint ausschließlich in der Rahmenhandlung und ist der simulierten Schüler:in unbekannt.
_Avoid_: Mentorin, Lehrkraft, Betreuerin

**Lernauftrag**:
Der Aufgabentext, den die simulierte Schüler:in bearbeitet hat.
_Avoid_: Aufgabe, Auftrag, Übung

**Arbeitsheft-Inhalt**:
Die sichtbare, fehlerhafte Bearbeitung der simulierten Schüler:in, wie sie der Teilnehmer:in angezeigt wird. Auch als Bild. Ausgangspunkt für das diagnostische Gespräch.
_Avoid_: Schülerlösung, Lösung, Heft

**Bearbeitungsbeschreibung**:
Die textuelle Beschreibung dessen, was im Arbeitsheft-Inhalt zu sehen ist. Sie existiert für die Simulation, während der Arbeitsheft-Inhalt für den Menschen existiert.
_Avoid_: Bildbeschreibung, Alt-Text

**Referenzdiagnose**:
Die fachdidaktische Notiz der Autor:in zum Fehlermuster ihrer Vignette. Optional und ohne jede Wirkung auf Simulation und Ablauf.
_Avoid_: Musterlösung, Goldstandard, Erwartungshorizont

**Gesprächsbudget**:
Die Grenze, an der das Gespräch einer Sitzung endet. Pro Vignette ist genau ein Budget-Typ aktiv: Gesprächsschritte oder Zeitbegrenzung. Der Teilnehmer:in wird es nicht angezeigt.
_Avoid_: Limit, Zeitlimit, Nachrichtenbudget

**Gesprächsschritt**:
Ein Austauschpaar aus einer Eingabe der Teilnehmer:in und der darauffolgenden Antwort der simulierten Schüler:in. Enthält intern noch die Denkspur der simulierten Schüler:in und eventuelle Fehlversuche.
_Avoid_: Nachricht, Turn, Zug

## Simulation

**Simulationskern**:
Die zentrale, fach-agnostische Verhaltensspezifikation der Simulation: System-Prompt-Vorlage, User-Prompt-Vorlage und Rahmenhandlung. Es gibt genau einen Kern für alle Vignetten.
_Avoid_: Prompt, Prompt-Vorlage, Systemprompt, Engine

**Rahmenhandlung**:
Die vom Simulationskern vorgegebene Situationsrahmung, die ausschließlich der Teilnehmer:in angezeigt wird: die Einleitung mit den Akteuren und der Hospitationssituation sowie der Debrief. Sie erreicht keinen Prompt und wird je Sitzung dargeboten.
_Avoid_: Setting, Szenario, Narrativ

**Simulierte Schüler:in**:
Die vom Simulationskern gesteuerte Gesprächspartnerin, die das Fehlermuster ihrer Vignette konsequent anwendet.
_Avoid_: Bot, Agent, KI-Schüler, Avatar

**Modell-Konfiguration**:
Das verwendete Sprachmodell samt seiner Parameter. Vom Simulationskern getrennt, unveränderlich und je Instanz von Administrator:innen gesetzt; genau eine ist aktiv. Kein versioniertes Artefakt.
_Avoid_: LLM-Einstellungen, KI-Konfiguration

**Denkspur**:
Das interne Reasoning der simulierten Schüler:in, das zu jeder ihrer Antworten entsteht und getrennt von der sichtbaren Äußerung gespeichert wird.
_Avoid_: Chain-of-Thought, Reasoning, Gedankengang

**Fehlversuch**:
Eine verworfene Antwort der simulierten Schüler:in samt ihrem Grund. Sie war nie Teil des Gesprächs und steht deshalb neben dem Transkript, nicht darin.
_Avoid_: Fehler, Retry, Exception

**Transkript**:
Der in Text überführte Gesprächsverlauf einer Sitzung. Es ist die alleinige Quelle der Wahrheit; Audio wird nicht aufbewahrt.
_Avoid_: Protokoll, Chatverlauf, Mitschrift

## Versionierung

**Versioniertes Artefakt**:
Ein Objekt, das den Lebenszyklus Entwurf → final durchläuft und von einer Historie gruppiert wird. Vignette, Simulationskern und Fragebogen-Item sind versionierte Artefakte.

**Entwurf**:
Der veränderliche Zustand eines versionierten Artefakts. Nur Entwürfe sind bearbeitbar, und nur sie sind physisch löschbar.
_Avoid_: Draft, unveröffentlicht

**Final**:
Der unveränderliche Zustand eines versionierten Artefakts. Nur finale Fassungen dürfen von Trainings und Erhebungen eingebunden werden; das Bearbeiten einer finalen Fassung erzeugt einen neuen Entwurf, der die Vorgängerin referenziert.
_Avoid_: veröffentlicht, publiziert, freigegeben — Vignetten sind privat, es gibt nichts zu veröffentlichen.

**Archiviert**:
Der zurückgenommene Zustand einer finalen Fassung. Sie ist nicht mehr einbindbar und nicht mehr spielbar, bleibt aber aus jeder Datenspur heraus lesbar. Das einzige Löschen, das finale Fassungen kennen; umkehrbar.
_Avoid_: gelöscht, deaktiviert, zurückgezogen

**Historie**:
Das Objekt, das die sequenziell entstandenen Fassungen eines versionierten Artefakts zusammenfasst. Sie bleibt linear und trägt höchstens einen Entwurf. Entsteht automatisch und wird erst ab der zweiten Fassung sichtbar und benennbar. Konkret: Vignettenhistorie, Simulationskern-Historie, Fragebogen-Item-Historie.
_Avoid_: Familie, Reihe, Strang, Lineage

## Durchführung

**Probelauf**:
Das schreibfreie Testgespräch über einem frei zusammengestellten Tripel aus Vignette, Simulationskern und Modell-Konfiguration; welche Teile wählbar sind, bestimmt die Rolle. Nur hier ist die Denkspur live sichtbar.
_Avoid_: Vorschau, Testlauf, Preview

**Sitzung**:
Ein Gespräch zu genau einer Vignette samt der zugehörigen Diagnose und Denkspur. Die atomare Auswertungseinheit; jeder Durchlauf einer Vignette ist eine eigene Sitzung.
_Avoid_: Gespräch, Durchlauf, Konversation, Session

**Debrief**:
Der Abschnitt der Rahmenhandlung, in dem die erfahrene Lehrperson nach dem Gespräch um die Diagnose bittet. Er beendet jede Sitzung und erreicht keinen Prompt.
_Avoid_: Nachbesprechung, Reflexion, Auswertung

**Diagnose**:
Die freie Beschreibung des beobachteten Fehlermusters durch die Teilnehmer:in, genau einmal am Ende jeder Sitzung. Sie wird erfasst, nicht bewertet.
_Avoid_: Diagnoseurteil, Befund, Einschätzung, Bewertung

**Teilnahme**:
Die Klammer, unter der alle Sitzungen einer Person in genau einem Training oder genau einer Erhebung zusammengefasst sind.
_Avoid_: Durchlauf, Session, Sitzung

**Training**:
Ein von einer Ausbilder:in kuratierter Satz finaler Vignetten, die Teilnehmende in freier Reihenfolge und beliebig oft spielen. Ohne Fragebogen-Items; Zugang über die Navigation mit Nutzerkonto.
_Avoid_: Übung, Kurs, Übungsmodus

**Erhebung**:
Ein von Forschenden zusammengestelltes Untersuchungsdesign aus finalen Vignetten, ihrer Reihenfolge und Fragebogen-Items. Zugang über einen Teilnahme-Link.
_Avoid_: Studie, Umfrage, Survey, Experiment

**Stichprobe**:
Eine organisatorische Untergruppe einer Erhebung, die einen eigenen Teilnahme-Link trägt und die über ihn entstandenen Teilnahmen bündelt. Sie dient der Gruppenstruktur im Export, nicht einer eigenen experimentellen Bedingung.
_Avoid_: Gruppe, Bedingung, Kohorte, Arm

**Teilnahme-Link**:
Der stabile Zugangsweg zu genau einer Stichprobe. Er ist für alle Teilnehmenden dieser Stichprobe identisch.
_Avoid_: Einladungslink, Studienlink

**Teilnahme-Token**:
Das pseudonyme Kennzeichen, das beim Öffnen eines Teilnahme-Links entsteht und die Forschungsdaten einer Teilnahme bündelt. Von jedem Nutzerkonto und jeder Trainingsaktivität strikt getrennt.
_Avoid_: Teilnehmer-ID, Nutzer-ID, Pseudonym

**Datenspur**:
Die vollständige, exportierbare Aufzeichnung einer Teilnahme: Transkripte, Diagnosen, Denkspuren, Fehlversuche, Fragebogen-Antworten sowie die tatsächlich verwendete Vignettenfassung, Simulationskern-Fassung und Modell-Konfiguration.
_Avoid_: Logs, Rohdaten, Protokoll

## Fragebögen

**Fragebogen-Item**:
Eine einzelne Frage an Teilnehmende, entweder als Freitext oder als sechsstufige Likert-Skala ohne neutrale Mitte. Die atomare, wiederverwendbare und versionierte Einheit.
_Avoid_: Frage, Item, Fragebogen

**Andockpunkt**:
Die Stelle im Ablauf einer Erhebung, an der ein Fragebogen-Item erhoben wird: nach jeder Vignettensitzung oder am Ende nach allen Vignettensitzungen.
_Avoid_: Zeitpunkt, Trigger, Position

**Fragebogen**:
Informeller Sammelbegriff für die Fragebogen-Items einer Erhebung samt ihren Andockpunkten. Kein eigenständiges Objekt.

## Rollen

**Teilnehmer:in**:
Wer Sitzungen führt und diagnostiziert. In einer Erhebung pseudonym über ein Teilnahme-Token, im Training über ein Nutzerkonto.
_Avoid_: Proband, Nutzer, Studierende

**Autor:in**:
Wer Vignetten anlegt und pflegt. Sieht und bearbeitet ausschließlich die eigenen. Wählt den Simulationskern nicht aus, kann einen Entwurf aber auf den aktuellsten Kern vorspulen.
_Avoid_: Vignettenautor, Redakteur

**Ausbilder:in**:
Wer Trainings zusammenstellt und die Sitzungen der eigenen Trainingsteilnehmenden namentlich einsieht.
_Avoid_: Dozent, Lehrender, Trainer

**Forschende:r**:
Wer Erhebungen zusammenstellt, ihren Ablauf steuert und die Datenspur exportiert.
_Avoid_: Wissenschaftler, Studienleiter

**Administrator:in**:
Wer die Instanz betreibt, Nutzer und Rollen verwaltet, die Modell-Konfiguration setzt und als Einzige den Simulationskern pflegt.
_Avoid_: Admin, Betreiber
