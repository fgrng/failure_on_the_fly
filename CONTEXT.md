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
Der Teil der Vignette, der den Gesprächsanlass liefert. Er gliedert sich in zwei gleich gebaute Teile: Lernauftrag und Arbeitsheft, jeweils bestehend aus Text, optionalem Bild, Bildbeschreibung und Simulationshinweisen.

**Aufgabenkontextteil**:
Einer der beiden gleich gebauten Teile des Aufgabenkontexts — der Lernauftrag oder das Arbeitsheft. Er trägt Text (zerlegt am Positionsmarker), Bild, Bildbeschreibung und Simulationshinweise und ist die Einheit, über die Anzeige, Vollständigkeitsprüfung und Prompt-Komposition arbeiten.
_Avoid_: Kontextteil, Abschnitt, Block

**Lernauftrag-Text**:
Der Aufgabentext, den die simulierte Schüler:in bearbeitet hat. Mit dem Positionsmarker `[bild]` allein auf einer Zeile wird festgelegt, an welcher Stelle das Bild erscheint; ohne Marker steht es unter dem Text. Für Teilnehmer:in sichtbar.
_Avoid_: Aufgabe, Auftrag, Übung

**Lernauftrag-Bild**:
Die optionale Abbildung zum Lernauftrag. Für Teilnehmer:in sichtbar.
_Avoid_: Abbildung, Grafik, Lernauftragsbild

**Lernauftrag-Bildbeschreibung**:
Die textuelle Beschreibung dessen, was auf dem Lernauftrag-Bild zu sehen ist. Sie ist Alt-Text für Teilnehmer:innen und die textuelle Bildfassung für die Simulation.
_Avoid_: Bildtext, Bearbeitungsbeschreibung

**Arbeitsheft-Text**:
Der Textinhalt des Arbeitshefts der simulierten Schüler:in (die abgetippte Bearbeitung). Mit dem Positionsmarker `[bild]` allein auf einer Zeile wird festgelegt, an welcher Stelle das Bild erscheint; ohne Marker steht es unter dem Text. Für Teilnehmer:in sichtbar.
_Avoid_: Schülerlösung, Lösung, Heft, Arbeitsheft-Inhalt

**Arbeitsheft-Bild**:
Die optionale Abbildung des Arbeitshefts der simulierten Schüler:in. Für Teilnehmer:in sichtbar.
_Avoid_: Schülerarbeit, Heftseite, Abbildung

**Arbeitsheft-Bildbeschreibung**:
Die textuelle Beschreibung dessen, was auf dem Arbeitsheft-Bild zu sehen ist. Sie ist Alt-Text für Teilnehmer:innen und die textuelle Bildfassung für die Simulation.
_Avoid_: Bearbeitungsbeschreibung

**Simulationshinweise**:
Zusätzliche fachdidaktische oder verhaltensbezogene Hinweise zum Lernauftrag oder Arbeitsheft ausschließlich für die Simulation. Sie erreichen keinen Prompt der Teilnehmer:in und sind für diese nicht sichtbar.
_Avoid_: Systemhinweise, Prompthinweise, Regieanweisungen

**Positionsmarker**:
Die Kennzeichnung `[bild]` allein auf einer Zeile im Lernauftrag- oder Arbeitsheft-Text, die festlegt, an welcher Stelle das jeweilige Bild bzw. im Prompt die Bildbeschreibung erscheint. Leerraum um den Marker und Groß- und Kleinschreibung spielen keine Rolle; mitten in einer Zeile oder als Linktext (`[bild](…)`) ist `[bild]` gewöhnlicher Text. Der erste Marker gewinnt; ohne Bild oder ohne Marker greift das Standardverhalten.
_Avoid_: Platzhalter, Bildplatzhalter, Marker

## Sitzung einer Vignette

**Rahmenhandlung**:
Die vom Simulationskern vorgegebene Situationsrahmung, die ausschließlich der Teilnehmer:in angezeigt wird: Hospitationseinleitung, Gesprächseinleitung und Debrief. Sie erreicht keinen Prompt und wird je Sitzung dargeboten. Ihre visuelle Repräsentation (Illustrationen) passt sich dynamisch an das Geschlecht der jeweiligen Lehrperson und Schüler:in an.
_Avoid_: Setting, Szenario, Narrativ

**Hospitationseinleitung**:
Der Abschnitt der Rahmenhandlung, der die allgemeine Hospitationssituation und die erfahrene Lehrperson einführt.
_Avoid_: Ausgangslage, allgemeine Einleitung

**Gesprächseinleitung**:
Der Abschnitt der Rahmenhandlung, der die konkrete Begegnung mit der simulierten Schüler:in unmittelbar vor dem Diagnosegespräch einführt.
_Avoid_: Gesprächsanlass, Gesprächssituation

**Sitzung**:
Ein Durchlauf genau einer Vignette und die atomare Auswertungseinheit; jedes Spielen einer Vignette ist eine eigene Sitzung. Regulär umfasst sie Rahmenhandlung, Diagnosegespräch, Debrief und Diagnose. Ein gewollter Abbruch oder ein technisches Scheitern beendet sie ohne Diagnose.
_Avoid_: Gespräch, Durchlauf, Konversation, Session

**Diagnosegespräch**:
Der Teil einer Sitzung, in dem die Teilnehmer:in mit der simulierten Schüler:in spricht: die Sitzung ohne Rahmenhandlung und ohne Debrief. Es besteht aus Gesprächsschritten und wird vom Gesprächsbudget begrenzt.
_Avoid_: Gespräch, Chat, Dialog

**Simulierte Schüler:in**:
Die vom Simulationskern gesteuerte Gesprächspartnerin, die das Fehlermuster ihrer Vignette konsequent anwendet.
_Avoid_: Bot, Agent, KI-Schüler, Avatar

**Gesprächsschritt**:
Ein Austauschpaar aus einer Eingabe der Teilnehmer:in und der darauffolgenden Antwort der simulierten Schüler:in. Enthält intern noch die Denkspur der simulierten Schüler:in und eventuelle Fehlversuche. Scheitert der Antwortversuch endgültig, bleibt der Gesprächsschritt ohne Antwort bestehen: Er trägt die Fehlversuche und dokumentiert damit den Abbruch der Sitzung.
_Avoid_: Nachricht, Turn, Zug

**Eingabemodus**:
Woher der abgeschickte Text einer freien Eingabe stammt: **getippt**, **transkribiert** (ausschließlich aus Aufnahmen) oder **gemischt** (getippter und transkribierter Anteil im selben Text). Er beschreibt die Herkunft des Textes, nicht eine Bearbeitung: »gemischt« heißt nicht »nachträglich überarbeitet«, und ob eine Teilnehmer:in ihr Transkript vor dem Absenden geändert hat, hält das System nirgends fest. Im Browser bestimmt und darum kein fälschungssicherer Nachweis, sondern eine Kovariate für die Auswertung; er geht mit der Datenspur in den Export (ADR-0029). In der Gesprächseingabe entsteht »gemischt« nicht, weil das Transkript dort schreibgeschützt und sofort abgeschickt wird.
_Avoid_: bearbeitet, redigiert, Eingabeart, Modalität, Input-Modus

**Debrief**:
Der Abschnitt der Rahmenhandlung, in dem die erfahrene Lehrperson nach dem Diagnosegespräch um die Diagnose bittet. Er beendet jede regulär abgeschlossene Sitzung und erreicht keinen Prompt.
_Avoid_: Nachbesprechung, Reflexion, Auswertung

**Diagnose**:
Die freie Beschreibung des beobachteten Fehlermusters durch die Teilnehmer:in, genau einmal am Ende jeder regulär abgeschlossenen Sitzung. Sie wird erfasst, nicht bewertet; abgebrochene und gescheiterte Sitzungen haben keine.
_Avoid_: Diagnoseurteil, Befund, Einschätzung, Bewertung

**Transkript**:
Der in Text überführte Verlauf des Diagnosegesprächs einer Sitzung. Es ist die alleinige Quelle der Wahrheit; Audio wird nicht aufbewahrt.
_Avoid_: Protokoll, Chatverlauf, Mitschrift

## Simulationsablauf

**Anbieter**:
Der Dienst, der eine Naht nach außen bedient — eine feste Auswahl aus `fake`, `openrouter` und `infomaniak` (ADR-0036). Aus ihm folgt, welches Präfix der Modellname trägt, ob Basis-URL und Token nötig sind und welche Stellschrauben in den Parametern erlaubt sind. Sprachmodell und Transkription wählen ihn je für sich; `fake` telefoniert nicht nach außen und braucht keine Zugangsdaten.
_Avoid_: Provider, Vendor, Backend, Hoster

**Modell-Konfiguration**:
Das verwendete Sprachmodell samt seiner Parameter. Sie benennt auch den **Anbieter** und trägt dessen Zugangsdaten — Basis-URL und Token liegen an der Konfiguration, nicht in der Umgebung (ADR-0036). Vom Simulationskern getrennt, unveränderlich und je Instanz von Administrator:innen gesetzt; genau eine ist aktiv. Die Fassung, unter der eine Erhebung lief, bleibt an ihr gepinnt und geht mit der Datenspur in den Export (ADR-0029); deshalb wird sie nie bearbeitet, sondern neu angelegt. Kein versioniertes Artefakt.
_Avoid_: LLM-Einstellungen, KI-Konfiguration

**Transkriptions-Konfiguration**:
Der eine Anbieterzugang der Audio-Transkription: **Anbieter**, Basis-URL, Token, Transkriptionsmodell und Sprache. Sie trägt dieselbe Anbieter-Feldgruppe wie die Modell-Konfiguration, ist aber veränderlich und einmalig — sie wird weder gepinnt noch exportiert (ADR-0026, ADR-0036).
_Avoid_: Transkriptionseinstellungen, Whisper-Konfiguration, STT-Konfiguration

**Modellvorschläge**:
Die Liste der Modellnamen, die ein **Anbieter** auf Druck des Ladeknopfes zur Modell-Konfiguration und zur Transkriptions-Konfiguration liefert. Sie ist ein Vorschlag und keine Gültigkeitsaussage: Ein Name, den sie nicht führt, bleibt eintragbar, und ob ein eingesetzter an seiner Naht taugt, entlarvt erst der Probelauf (ADR-0014). Die einzige Prüfung, die am Modellnamen wirklich stattfindet, ist seine Anbieterbindung (ADR-0036). Bei `fake` gibt es nichts abzurufen.
_Avoid_: Autovervollständigung, Autocomplete, Typeahead, Modellpicker, Modellauswahl — eine Auswahl schlösse aus, was hier nur vorgeschlagen wird.

**Simulationskern**:
Die zentrale, fach-agnostische Verhaltensspezifikation der Simulation: System-Prompt-Vorlage, User-Prompt-Vorlage und Rahmenhandlung. Er ist ein versioniertes Artefakt, und es gibt genau eine Kern-Historie für alle Vignetten und alle Fächer — aber mehrere Fassungen nebeneinander im Umlauf. Jede Vignettenfassung pinnt genau eine finale Kern-Fassung und spielt für immer gegen diese; ein Training oder eine Erhebung darf Vignetten mit verschiedenen gepinnten Kern-Fassungen mischen.
_Avoid_: Prompt, Prompt-Vorlage, Systemprompt, Engine — „ein Kern" meint eine Linie, nicht ein Objekt.

**Standardkern**:
Die im Code mitgeführte kanonische Erstfassung der fünf Inhaltsfelder des Simulationskerns. Er ist selbst keine Fassung und kein Zustand, sondern der Ausgangspunkt, aus dem eine frische Instanz ihre erste Kern-Fassung zieht — über die Verwaltungsseite als Entwurf, über `manage.py kern_initialisieren` als sofort spielbare finale Fassung. Danach spielt er keine Rolle mehr: Jede spätere Fassung entsteht aus ihrer Vorgängerin, nie erneut aus ihm.
_Avoid_: mitgelieferte Vorlagen, Standardvorlagen, Default-Kern, Seed-Kern, Werkseinstellung

**Denkspur**:
Das interne Reasoning der simulierten Schüler:in, das zu jeder ihrer Antworten entsteht und getrennt von der sichtbaren Äußerung gespeichert wird. Der Simulationskern verlangt sie; sie gehört zur Rolle.
_Avoid_: Chain-of-Thought, Reasoning, Gedankengang, native Reasoning-Spur — das vom Modell selbst erzeugte Reasoning wird nicht aufbewahrt (ADR-0005).

**Fehlversuch**:
Eine verworfene Antwort der simulierten Schüler:in samt ihrem Grund. Sie war nie Teil des Diagnosegesprächs und steht deshalb neben dem Transkript, nicht darin. Sie wird am Gesprächsschritt aufbewahrt, zu dem ihr Antwortversuch gehörte.
_Avoid_: Fehler, Retry, Exception

**Antwortversuch**:
Das Bemühen der Simulation, auf eine Eingabe der Teilnehmer:in genau eine Antwort der simulierten Schüler:in zu erzeugen. Er setzt begrenzt oft an; jedes misslungene Ansetzen ist ein Fehlversuch. Er trägt, was dabei entsteht: die sichtbare Äußerung, die Denkspur und die angefallenen Fehlversuche. Er ist flüchtig und wird selbst nicht gespeichert. Aus ihm und der vorausgegangenen Eingabe entsteht ein Gesprächsschritt — mit Antwort, wenn er glückt; ohne Antwort, wenn er endgültig scheitert. Im zweiten Fall endet die Sitzung im Abbruch.
_Avoid_: Schrittergebnis, Ergebnis, Response, Modellantwort — ein Antwortversuch, der nur Fehlversuche enthält, ist ein gültiger Antwortversuch und hat kein Ergebnis.

**Gesprächsbudget**:
Die Grenze, an der das Diagnosegespräch einer Sitzung endet und der Debrief folgt. Pro Vignette ist genau ein Budget-Typ aktiv: Gesprächsschritte oder Zeitbegrenzung. Der Teilnehmer:in wird es nicht angezeigt (ADR-0012); es ist eine Obergrenze, kein Soll.

Wie weit eine Sitzung ihr Budget verbraucht hat, ist ihr **Budgetstand**: die Zahl der geglückten Gesprächsschritte oder die **verbrauchte Zeit**. Er gehört der Sitzung und überlebt einen Browserwechsel; die verbrauchte Zeit ist eine Größe der Datenspur. Bei Zeitbegrenzung misst die **Uhr** ausschließlich den **Zug** der Teilnehmer:in — die Zeit vom Anzeigen der Gesprächsseite bis zum Absenden ihrer Eingabe. Während die simulierte Schüler:in antwortet, steht die Uhr; Fehlversuche kosten keine Zeit. Bei schrittbasiertem Budget läuft keine Uhr: Dort wird die verbrauchte Zeit nicht gemessen, sondern bleibt null. Der laufende, noch nicht abgesendete Zug ist die **offene Spanne**; wer die Gesprächsseite erneut aufruft, setzt sie neu an, ohne dass bereits verbrauchte Zeit verloren geht oder die Spanne dazugerechnet wird. Erschöpft sich das Budget während eines Gesprächsschritts, wird dieser zu Ende geführt.
_Avoid_: Limit, Zeitlimit, Nachrichtenbudget, Timer, Countdown, Restzeit, Restbudget, Zeitstand — es gibt keinen Rest, den jemand sieht; Denkzeit, Bearbeitungszeit, Sitzungsdauer — die Uhr misst den Zug, nicht die Sitzung.

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
Der zurückgenommene Zustand einer finalen Fassung. Sie ist nicht mehr einbindbar und nicht mehr spielbar, bleibt aber aus jeder Datenspur heraus lesbar. Das einzige Löschen, das finale Fassungen kennen; umkehrbar. Beim Simulationskern heißt derselbe Zustand **überholt**: Dort entsteht er nur als Nebenwirkung des Finalisierens der Nachfolgerin und ist nicht umkehrbar (ADR-0035).
_Avoid_: gelöscht, deaktiviert, zurückgezogen

**Historie**:
Das Objekt, das die sequenziell entstandenen Fassungen eines versionierten Artefakts zusammenfasst. Sie bleibt linear und trägt höchstens einen Entwurf. Entsteht automatisch und wird erst ab der zweiten Fassung sichtbar und benennbar.

Der vollausgestattete Fall ist die **Vignettenhistorie**: Sie trägt einen Eigentümer-Kreis und ist als Ganzes archivierbar. Die **Fragebogen-Item-Historie** trägt ebenfalls einen Eigentümer-Kreis, ist aber nicht als Ganzes archivierbar. Die **Simulationskern-Historie** ist namenlos: Der Kern ist eine einzige Linie — ein partieller Unique-Index lässt je Historie nur eine finale Fassung zu (ADR-0035) —, gehört der Administration und braucht keinen Namen, um Historien voneinander zu unterscheiden. Was die drei teilen, ist der Zustandsautomat, nicht die Ausstattung.
_Avoid_: Familie, Reihe, Strang, Lineage

## Anlässe für Sitzungen

**Probelauf**:
Die schreibfreie Sitzung über einem frei zusammengestellten Tripel aus Vignette, Simulationskern und Modell-Konfiguration; welche Teile wählbar sind, bestimmt die Rolle. Er läuft wie eine Sitzung ab und wird wie eine dargeboten — Rahmenhandlung, Diagnosegespräch, Debrief und Diagnose. Der Unterschied liegt allein in der Persistierung: Nichts davon wird aufbewahrt. Nur hier ist die Denkspur live sichtbar.
_Avoid_: Vorschau, Testlauf, Preview

**Teilnahme**:
Die Klammer, unter der alle Sitzungen einer Person in genau einem Training, genau einer Erhebung oder genau einer Abschrift zusammengefasst sind. Die Teilnahme einer Abschrift ist ein Behälter für kopierte Sitzungen und **keine zweite Teilnahme derselben Person** — sie wird nirgends mitgezählt.
_Avoid_: Durchlauf, Session, Sitzung

**Abschrift**:
Die konto-gebundene Kopie einer abgeschlossenen Erhebungsteilnahme im Trainingsbereich: Transkript, Ausgang und eigene Diagnose, in der gespielten Reihenfolge. Sie entsteht durch Eingabe des Teilnahme-Tokens, hält den Namen der Erhebung als Text und den Importzeitpunkt — kein Token, keinen Rückzeiger. Sie gehört der Teilnehmer:in persönlich und ist ausdrücklich kein Forschungsdatum (ADR-0043).
_Avoid_: Export, Mitschrift, Transkriptarchiv — „Kopie“ benennt in ADR-0043 das Verfahren (Kopie statt Verknüpfung), nie die Sache selbst.

**Training**:
Ein von einem Eigentümer-Kreis der Ausbilder:innen kuratierter Satz finaler Vignetten, die Teilnehmende in freier Reihenfolge und beliebig oft spielen. Ohne Fragebogen-Items; Zugang über die Navigation mit Nutzerkonto.
_Avoid_: Übung, Kurs, Übungsmodus

**Erhebung**:
Ein von einem Eigentümer-Kreis der Forschenden zusammengestelltes Untersuchungsdesign aus finalen Vignetten, ihrer Reihenfolge und Fragebogen-Items. Zugang über einen Teilnahme-Link.
_Avoid_: Studie, Umfrage, Survey, Experiment

**Stichprobe**:
Eine organisatorische Untergruppe einer Erhebung, die einen eigenen Teilnahme-Link trägt und die über ihn entstandenen Teilnahmen bündelt. Sie dient der Gruppenstruktur im Export, nicht einer eigenen experimentellen Bedingung. Ihr Archivieren hat eine zweite Bedeutung: Aus einer archivierten Stichprobe — wie aus einer archivierten Erhebung — lässt sich keine Abschrift mehr holen. Ihre **Phase** ist nichts Gespeichertes, sondern die Lage ihres Zeitraums zur Systemzeit: _geplant_ (noch nicht offen), _läuft_ (Teilnahme möglich) oder _abgeschlossen_ (geschlossen; erst jetzt ist eine Abschrift zu holen).
_Avoid_: Gruppe, Bedingung, Kohorte, Arm

**Teilnahme-Link**:
Der stabile Zugangsweg zu genau einer Stichprobe. Er ist für alle Teilnehmenden dieser Stichprobe identisch.
_Avoid_: Einladungslink, Studienlink

**Teilnahme-Token**:
Das pseudonyme Kennzeichen, das beim Öffnen eines Teilnahme-Links entsteht und die Forschungsdaten einer Teilnahme bündelt. Von jedem Nutzerkonto und jeder Trainingsaktivität strikt getrennt: Auch wer es zum Holen einer Abschrift eingibt, hinterlässt keine gespeicherte Verbindung zwischen Konto und Token (ADR-0043).
_Avoid_: Teilnehmer-ID, Nutzer-ID, Pseudonym

**Datenspur**:
Die vollständige, exportierbare Aufzeichnung einer Teilnahme an einer Erhebung: Transkripte, Diagnosen, Denkspuren, Fehlversuche, Item-Antworten sowie die tatsächlich verwendete Vignettenfassung, Simulationskern-Fassung und Modell-Konfiguration. Trainingsteilnahmen tragen keine Datenspur und werden nicht exportiert.
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

**Itemblock**:
Die Fragebogen-Items eines Andockpunkts, wie sie einer Teilnahme tatsächlich vorgelegt wurden. Er hält als eigener Datensatz fest, wann er vorgelegt und wann er abgeschickt wurde — auch ohne einzige Antwort — und trägt die Item-Antworten (ADR-0041). Je Vignettensitzung und je Erhebungsbindung am Ende entsteht höchstens einer.
_Avoid_: Fragebogenseite, Block, Formular

## Rollen

**Eigentümer-Kreis**:
Die Menge gleichrangiger Konten, denen ein fachlicher Bestand gehört: eine Vignettenhistorie, eine Fragebogen-Item-Historie, ein Training oder eine Erhebung. Eigentümerschaft ist uniform und alles-oder-nichts je Objekt; bei Vignette und Fragebogen-Item hängt der Kreis an der Historie, bei Training und Erhebung am Objekt selbst (ADR-0032, ADR-0037). Ein Bestand ist sichtbar für seinen Kreis und die Administration, für niemanden sonst. Ein aktiver Bestand hat mindestens ein Mitglied; **Austritt** ist das Verlassen des Kreises und für das letzte Mitglied gesperrt. Eine Übertragung gibt es nicht, nur Aufnehmen und Austreten. **Ko-Autorschaft** ist der Weg in den Kreis, kein Synonym: Wer aufgenommen wird, ist Ko-Autor:in und damit Mitglied (ADR-0022).
_Avoid_: Ko-Eigentümerin, Besitzerin, Inhaberin, Owner

**Teilnehmer:in**:
Wer Sitzungen führt und diagnostiziert. In einer Erhebung pseudonym über ein Teilnahme-Token, im Training über ein Nutzerkonto.
_Avoid_: Proband, Nutzer, Studierende

**Autor:in**:
Wer Vignetten anlegt und pflegt. Sieht und bearbeitet ausschließlich die Vignetten, deren Eigentümer-Kreis sie angehört. Wählt den Simulationskern nicht aus, kann einen Entwurf aber auf den aktuellsten Kern vorspulen.
_Avoid_: Vignettenautor, Redakteur

**Ausbilder:in**:
Wer Trainings zusammenstellt, deren Eigentümer-Kreis die Person angehört, und die Sitzungen ihrer Trainingsteilnehmenden namentlich einsieht.
_Avoid_: Dozent, Lehrender, Trainer

**Forschende:r**:
Wer Erhebungen zusammenstellt, deren Eigentümer-Kreis die Person angehört, ihren Ablauf steuert und die Datenspur exportiert.
_Avoid_: Wissenschaftler, Studienleiter

**Administrator:in**:
Wer die Instanz betreibt, Nutzer und Rollen verwaltet, die Modell- und die Transkriptions-Konfiguration setzt und als Einzige den Simulationskern pflegt. Technisch ist sie ein Django-Superuser, keine Group.
_Avoid_: Admin, Betreiber

## Architektur

**Naht**:
Eine Stelle, an der Verhalten ausgetauscht werden kann, ohne den umgebenden Code zu ändern. Sie wird nur eingezogen, wo mindestens zwei Adapter tatsächlich existieren.
_Avoid_: Seam, Port, Interface, Abstraktionsschicht
