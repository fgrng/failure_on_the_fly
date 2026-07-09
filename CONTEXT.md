# FailureOnTheFly

Web-basierter Simulator von Schüler:innen mit Fehlermustern, an dem (angehende) Lehrpersonen diagnostische Gesprächsführung üben und an dem diagnostische Kompetenz erhoben wird.

Dieses Dokument fixiert die gemeinsame Sprache des Projekts. Es ist ein Glossar — keine Spezifikation. Entscheidungen und ihre Begründungen liegen in `docs/adr/`.

## Vignettenkontext

**Vignette**:
Die konkrete Trainingssituation, in der eine simulierte Schüler:in ein Fehlermuster systematisch anwendet. Sie ist die Einheit, die Autor:innen anlegen, die Trainings und Erhebungen einbinden und die Teilnehmende spielen.
_Avoid_: Fall, Szenario, Case, Aufgabe

**Fehlermuster**:
Die stabile, systematisch angewandte Regel, kongruent zu der die simulierte Schüler:in handelt. Sie wird in genau einer Vignette beschrieben und ist kein eigenständig wiederverwendbares Objekt.
_Avoid_: Fehlvorstellung, systematischer Fehler, Misconception — fachdidaktische Unterkategorien, die dasselbe Modellierungsobjekt meinen.

**Referenzdiagnose**:
Die fachdidaktische Notiz der Autor:in zum Fehlermuster ihrer Vignette. Optional und ohne jede Wirkung auf Simulation und Ablauf.
_Avoid_: Musterlösung, Goldstandard, Erwartungshorizont

**Unterrichtskontext**:
Die fachliche Verortung einer Vignette: Unterrichtsfach, Unterrichtsthema und Klassenstufe.
_Avoid_: Metadaten, Fachbezug, Rahmendaten

**Erfahrene Lehrperson**:
Die Akteurin der Vignette, die die Teilnehmer:in bei der Hospitation begleitet und die im Debrief nach der Diagnose fragt. Sie erscheint ausschließlich in der Rahmenhandlung und ist der simulierten Schüler:in unbekannt.
_Avoid_: Mentorin, Lehrkraft, Betreuerin

## Aufgabenkontext

**Aufgabenkontext**:
Der Teil der Vignette, der den Gesprächsanlass liefert. Besteht aus Lernauftrag, Arbeitsheft-Inhalt und Bearbeitungsbeschreibung.

**Lernauftrag**:
Der Aufgabentext, den die simulierte Schüler:in bearbeitet hat.
_Avoid_: Aufgabe, Auftrag, Übung

**Arbeitsheft-Inhalt**:
Die sichtbare, fehlerhafte Bearbeitung der simulierten Schüler:in, wie sie der Teilnehmer:in angezeigt wird. Auch als Bild. Ausgangspunkt für das Diagnosegespräch.
_Avoid_: Schülerlösung, Lösung, Heft

**Bearbeitungsbeschreibung**:
Die textuelle Beschreibung dessen, was im Arbeitsheft-Inhalt zu sehen ist. Sie existiert für die Simulation, während der Arbeitsheft-Inhalt für den Menschen existiert.
_Avoid_: Bildbeschreibung, Alt-Text

## Sitzung einer Vignette

**Rahmenhandlung**:
Die vom Simulationskern vorgegebene Situationsrahmung, die ausschließlich der Teilnehmer:in angezeigt wird: die Einleitung mit den Akteuren und der Hospitationssituation sowie der Debrief. Sie erreicht keinen Prompt und wird je Sitzung dargeboten.
_Avoid_: Setting, Szenario, Narrativ

**Sitzung**:
Ein Durchlauf genau einer Vignette: Rahmenhandlung, Diagnosegespräch, Debrief und Diagnose. Die atomare Auswertungseinheit; jedes Spielen einer Vignette ist eine eigene Sitzung.
_Avoid_: Gespräch, Durchlauf, Konversation, Session

**Diagnosegespräch**:
Der Teil einer Sitzung, in dem die Teilnehmer:in mit der simulierten Schüler:in spricht: die Sitzung ohne Rahmenhandlung und ohne Debrief. Es besteht aus Gesprächsschritten und wird vom Gesprächsbudget begrenzt.
_Avoid_: Gespräch, Chat, Dialog

**Simulierte Schüler:in**:
Die vom Simulationskern gesteuerte Gesprächspartnerin, die das Fehlermuster ihrer Vignette konsequent anwendet.
_Avoid_: Bot, Agent, KI-Schüler, Avatar

**Gesprächsschritt**:
Ein Austauschpaar aus einer Eingabe der Teilnehmer:in und der darauffolgenden Antwort der simulierten Schüler:in. Enthält intern noch die Denkspur der simulierten Schüler:in, eine etwaige native Reasoning-Spur und eventuelle Fehlversuche. Scheitert der Antwortversuch endgültig, bleibt der Gesprächsschritt ohne Antwort bestehen: Er trägt die Fehlversuche und dokumentiert damit den Abbruch der Sitzung.
_Avoid_: Nachricht, Turn, Zug

**Debrief**:
Der Abschnitt der Rahmenhandlung, in dem die erfahrene Lehrperson nach dem Diagnosegespräch um die Diagnose bittet. Er beendet jede Sitzung und erreicht keinen Prompt.
_Avoid_: Nachbesprechung, Reflexion, Auswertung

**Diagnose**:
Die freie Beschreibung des beobachteten Fehlermusters durch die Teilnehmer:in, genau einmal am Ende jeder Sitzung. Sie wird erfasst, nicht bewertet.
_Avoid_: Diagnoseurteil, Befund, Einschätzung, Bewertung

**Transkript**:
Der in Text überführte Verlauf des Diagnosegesprächs einer Sitzung. Es ist die alleinige Quelle der Wahrheit; Audio wird nicht aufbewahrt.
_Avoid_: Protokoll, Chatverlauf, Mitschrift

## Simulationsablauf

**Modell-Konfiguration**:
Das verwendete Sprachmodell samt seiner Parameter. Vom Simulationskern getrennt, unveränderlich und je Instanz von Administrator:innen gesetzt; genau eine ist aktiv. Kein versioniertes Artefakt.
_Avoid_: LLM-Einstellungen, KI-Konfiguration

**Simulationskern**:
Die zentrale, fach-agnostische Verhaltensspezifikation der Simulation: System-Prompt-Vorlage, User-Prompt-Vorlage und Rahmenhandlung. Er ist ein versioniertes Artefakt, und es gibt genau eine Kern-Historie für alle Vignetten und alle Fächer — aber mehrere Fassungen nebeneinander im Umlauf. Jede Vignettenfassung pinnt genau eine finale Kern-Fassung und spielt für immer gegen diese; ein Training oder eine Erhebung darf Vignetten mit verschiedenen gepinnten Kern-Fassungen mischen.
_Avoid_: Prompt, Prompt-Vorlage, Systemprompt, Engine — „ein Kern" meint eine Linie, nicht ein Objekt.

**Denkspur**:
Das interne Reasoning der simulierten Schüler:in, das zu jeder ihrer Antworten entsteht und getrennt von der sichtbaren Äußerung gespeichert wird. Der Simulationskern verlangt sie; sie gehört zur Rolle.
_Avoid_: Chain-of-Thought, Reasoning, Gedankengang

**Native Reasoning-Spur**:
Das vom Sprachmodell selbst erzeugte Reasoning, das manche Modell-Konfigurationen neben der Antwort ausliefern. Sie stammt vom Modell, nicht von der simulierten Schüler:in, und ist deshalb nicht die Denkspur: Wo die Denkspur zur Rolle gehört und immer entsteht, gehört sie zur Modell-Konfiguration und fehlt, wenn diese sie nicht liefert. Sie wird, wenn vorhanden, am Gesprächsschritt aufbewahrt und ist Teil der Datenspur.
_Avoid_: Reasoning-Tokens, Thinking, Denkspur

**Fehlversuch**:
Eine verworfene Antwort der simulierten Schüler:in samt ihrem Grund. Sie war nie Teil des Diagnosegesprächs und steht deshalb neben dem Transkript, nicht darin. Sie wird am Gesprächsschritt aufbewahrt, zu dem ihr Antwortversuch gehörte.
_Avoid_: Fehler, Retry, Exception

**Antwortversuch**:
Das Bemühen der Simulation, auf eine Eingabe der Teilnehmer:in genau eine Antwort der simulierten Schüler:in zu erzeugen. Er setzt begrenzt oft an; jedes misslungene Ansetzen ist ein Fehlversuch. Er trägt, was dabei entsteht: die sichtbare Äußerung, die Denkspur, die angefallenen Fehlversuche und eine etwaige native Reasoning-Spur. Er ist flüchtig und wird selbst nicht gespeichert. Aus ihm und der vorausgegangenen Eingabe entsteht ein Gesprächsschritt — mit Antwort, wenn er glückt; ohne Antwort, wenn er endgültig scheitert. Im zweiten Fall endet die Sitzung im Abbruch.
_Avoid_: Schrittergebnis, Ergebnis, Response, Modellantwort — ein Antwortversuch, der nur Fehlversuche enthält, ist ein gültiger Antwortversuch und hat kein Ergebnis.

**Gesprächsbudget**:
Die Grenze, an der das Diagnosegespräch einer Sitzung endet und der Debrief folgt. Pro Vignette ist genau ein Budget-Typ aktiv: Gesprächsschritte oder Zeitbegrenzung. Der Teilnehmer:in wird es nicht angezeigt.
_Avoid_: Limit, Zeitlimit, Nachrichtenbudget

## Versionierung

**Versioniertes Artefakt**:
Ein Objekt, das den Lebenszyklus Entwurf → final → archiviert durchläuft und von einer Historie gruppiert wird. Vignette, Simulationskern und Fragebogen-Item sind versionierte Artefakte.

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
Das Objekt, das die sequenziell entstandenen Fassungen eines versionierten Artefakts zusammenfasst. Sie bleibt linear und trägt höchstens einen Entwurf. Entsteht automatisch und wird erst ab der zweiten Fassung sichtbar und benennbar.

Der vollausgestattete Fall ist die **Vignettenhistorie**: Sie trägt eine Eigentümer:in und ist als Ganzes archivierbar. Die **Fragebogen-Item-Historie** kennt beides nicht. Für den Simulationskern ist offen, ob seine Historie je benannt werden muss — er ist konzeptionell eine einzige Linie und gehört der Administration. Was die drei teilen, ist der Zustandsautomat, nicht die Ausstattung.
_Avoid_: Familie, Reihe, Strang, Lineage

## Anlässe für Sitzungen

**Probelauf**:
Die schreibfreie Sitzung über einem frei zusammengestellten Tripel aus Vignette, Simulationskern und Modell-Konfiguration; welche Teile wählbar sind, bestimmt die Rolle. Er läuft wie eine Sitzung ab und wird wie eine dargeboten — Rahmenhandlung, Diagnosegespräch, Debrief und Diagnose. Der Unterschied liegt allein in der Persistierung: Nichts davon wird aufbewahrt. Nur hier ist die Denkspur live sichtbar.
_Avoid_: Vorschau, Testlauf, Preview

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
Die vollständige, exportierbare Aufzeichnung einer Teilnahme an einer Erhebung: Transkripte, Diagnosen, Denkspuren, native Reasoning-Spuren, Fehlversuche, Item-Antworten sowie die tatsächlich verwendete Vignettenfassung, Simulationskern-Fassung und Modell-Konfiguration. Trainingsteilnahmen tragen keine Datenspur und werden nicht exportiert.
_Avoid_: Logs, Rohdaten, Protokoll

## Fragebögen

**Fragebogen**:
Informeller Sammelbegriff für die Fragebogen-Items einer Erhebung samt ihren Andockpunkten. Kein eigenständiges Objekt.

**Fragebogen-Item**:
Eine einzelne Frage an Teilnehmende, entweder als Freitext oder als sechsstufige Likert-Skala ohne neutrale Mitte. Die atomare, wiederverwendbare und versionierte Einheit.
_Avoid_: Frage, Item, Fragebogen

**Item-Antwort**:
Was eine Teilnehmer:in auf ein Fragebogen-Item geantwortet hat: ein Freitext oder eine Stufe der Likert-Skala. Sie gehört der Erhebung, nicht dem Item. Nicht zu verwechseln mit der Antwort der simulierten Schüler:in in einem Gesprächsschritt — hier antwortet der Mensch, dort die Simulation.
_Avoid_: Antwort, Fragebogen-Antwort, Response

**Andockpunkt**:
Die Stelle im Ablauf einer Erhebung, an der ein Fragebogen-Item erhoben wird: nach jeder Vignettensitzung oder am Ende nach allen Vignettensitzungen.
_Avoid_: Zeitpunkt, Trigger, Position

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

## Architektur

**Naht**:
Eine Stelle, an der Verhalten ausgetauscht werden kann, ohne den umgebenden Code zu ändern. Sie wird nur eingezogen, wo mindestens zwei Adapter tatsächlich existieren.
_Avoid_: Seam, Port, Interface, Abstraktionsschicht
