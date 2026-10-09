# Verhalten der Plattform

Dieses Dokument beschreibt das sichtbare Verhalten der Plattform je Bereich so,
wie es heute umgesetzt ist. Es ist die Referenz für die Frage »Was tut die
Anwendung an dieser Stelle genau?« — für Begriffe siehe [GLOSSARY.md](../GLOSSARY.md),
für die Gründe hinter dem Verhalten [docs/adr/](adr/). Wer das Verhalten ändert,
ändert diesen Text mit.

## Start und Anmeldung

Die öffentliche Startseite unter `/` ist eine kurze Willkommensseite: Sie nennt
den Zweck der Plattform und stellt die Funktionen in drei Rollenspalten vor
(Autor:in, Lehrperson in Ausbildung, Ausbildung & Forschung). Sie verlinkt
selbst auf keinen geschützten Bereich; ohne Anmeldung führt sie zum Login unter
`/accounts/login/`. Nach der Anmeldung zeigt die Sidebar nur die Bereiche und
Links der jeweiligen Gruppenrollen; die Administration ist dabei ein Django-
Superuser, keine Group, und wird mit `manage.py createsuperuser` eingerichtet.
Über `/admin/` legt die Administration weitere Konten an, setzt deren Passwörter,
vergibt die drei fachlichen Rollen als Groups und kann weitere Superuser ernennen.
Konten lassen sich dort bewusst nicht löschen, solange #156 den Umgang mit
Löschbegehren noch nicht festlegt.

Die Sidebar gliedert die Links in die Gruppen Entwicklung (gelb), Ausbildung
(grün), Forschung (violett) und System (blau). Die aktive Seite trägt die
Fläche und einen Balken links im Ton ihrer Gruppe, beim Überfahren erscheint
die halbe Tönung; die Schrift bleibt dunkel. Jede Seite trägt die Bereichsfarbe
der Gruppe, unter der sie in der Sidebar steht: Vignetten und der
Simulationskern samt Verwaltung gehören zu Entwicklung, Trainingskatalog,
eigene Trainings, Training anlegen und kuratieren zu Ausbildung.

Die Seitenköpfe folgen einem Vokabular. Die Überzeile nennt Sidebar-Gruppe
und Eintrag, etwa »Entwicklung / Vignetten«, »Entwicklung / Simulationskern«,
»Ausbildung / Trainings«, »Ausbildung / Training starten«, »Forschung / Meine
Erhebungen«, »Forschung / Fragebogen-Items« oder »System /
Modell-Konfiguration«; Trainingskatalog und eigene Trainings tragen nur
»Ausbildung«. Der Titel nennt die Aktion oder das Objekt: »Vignette anlegen«,
»Vignette bearbeiten«, »Aktueller Kern«, »Kern verwalten«, »Kern-Entwurf
bearbeiten«, »Training anlegen«, »Erhebung anlegen«, »Fragebogen-Item anlegen«,
»Modell-Konfiguration anlegen«; Detailseiten tragen den Namen des Objekts. Das
Verb heißt überall »anlegen«, nie »erstellen«. Der Absendeknopf einer
Anlegen-Seite wiederholt den Titel (»Vignette anlegen«, »Training anlegen«,
»Erhebung anlegen«, »Fragebogen-Item anlegen«; im Editor der
Modell-Konfiguration »Konfiguration anlegen«). Auf Bearbeiten-Seiten heißt er
»Änderungen speichern«, ebenso auf der Transkriptions-Konfiguration.

Die gesamte Oberfläche ist deutschsprachig, auch Djangos eigene Texte:
Formularfehler (»Dieses Feld ist zwingend erforderlich.«), die Bedienelemente
bereits hochgeladener Bilder und die Datumsanzeige. Auswahlfelder ohne
Vorbelegung zeigen »Bitte wählen …«.

## Formulare

In den Formularen zum Anlegen und Bearbeiten (Vignetten, Trainings, Erhebungen,
Fragebogen-Items, Simulationskern, Modell- und Transkriptions-Konfiguration)
stehen die Aktionen wie »Abbrechen« und »Änderungen speichern« oben im
Formular und bleiben beim Scrollen sichtbar, solange das Formular im Bild ist.
Die Tab-Reihenfolge führt weiter erst durch die Felder. Auf den Seiten der
Teilnahme stehen die Aktionen weiterhin am Ende, etwa »Einwilligen« nach der
Wahl zur Audioverarbeitung. Aktionen außerhalb eines Formulars, etwa auf
Detailseiten, bleiben an ihrer Stelle.

## Listen

In »Meine Vignetten« und der Fragebogen-Item-Liste ist die ganze Zeile
klickbar und öffnet die Detailseite; eine Spalte »Aktion« mit einem Knopf
»Öffnen« je Zeile gibt es dort nicht mehr. Der Name in der ersten Spalte ist
der einzige Link der Zeile, fett in Textfarbe. Mit Tab erreicht man je Zeile
genau diesen Link, ein Mittelklick öffnet die Detailseite in einem neuen Tab.
Beim Überfahren und beim Tastaturfokus tönt sich die Zeile halb im Bereichston
der Seite, am Zeilenende erscheint in Grün »Öffnen ›«. Der Tastaturfokus
zeichnet zusätzlich den grünen Fokus-Ring um die Zeile. Die Trennlinien
zwischen den Zeilen bleiben dabei sichtbar. Suche, Filter und Sortierung
bleiben unverändert.

Die Erhebungsliste hat dieselben klickbaren Zeilen. Entwürfe tragen am
Zeilenende zusätzlich einen Lösch-Knopf mit Mülleimer-Symbol, in Ruhe
gedämpft, beim Überfahren rot umrandet. Er ist ein eigenes Element mit der
Beschriftung »<Name> löschen«: Mit Tab erreicht man ihn nach dem Namen, ein
Klick darauf löscht den Entwurf sofort und öffnet nicht die Detailseite.
Finale und archivierte Erhebungen haben keinen Lösch-Knopf.

Genauso funktionieren die Trainingskataloge, »Meine Trainings« der
Ausbilder:innen, die Trainingshistorie und »Meine Abschriften«. Dort nennt der
Hinweis am Zeilenende die jeweilige Aktion statt »Öffnen ›«: in den
Trainingskatalogen je Zeile »Kuratieren ›« (Trainings, die man kuratieren darf)
oder »Öffnen ›«, in »Meine Trainings« »Kuratieren ›«, in der Historie
»Ansehen ›« und in »Meine Abschriften« »Lesen ›«. Der Link führt jeweils zum
bisherigen Ziel. Tabellen mit echten Aktionen statt Navigation, etwa auf der
Kuratieren-Seite oder in der Trainingsdetailansicht, bleiben unverändert.

## Vignetten verwalten

Autor:innen sehen die Vignetten ihres Eigentümer-Kreises; Administrator:innen
sehen alle. In der Detailansicht lässt sich eine weitere Autorin oder
Administratorin als Eigentümer:in hinzufügen oder eine vorhandene entfernen. Der
Kreis bleibt dabei immer besetzt; die eigene Entfernung übergibt die Historie an
die verbleibenden Eigentümer:innen.

Der Abschnitt »Eigentümer:innen« sieht auf Vignette, Fragebogen-Item, Erhebung
und Training gleich aus und nennt jeweils das Artefakt. Eine Tabelle führt Name,
alle Rollen des Kontos (etwa »Autor:in, Administrator:in«) und die Aktion. Das
Entfernen ist ein roter Textlink. Die eigene Zeile trägt »(Sie)«, dort heißt
die Aktion »Mich entfernen«, und ein Satz erklärt, dass das Artefakt bei den
übrigen Eigentümer:innen bleibt. Bei nur einer Eigentümer:in steht statt einer
Aktion »Letzte Eigentümer:in«, darunter der Hinweis, zuerst jemanden
hinzuzufügen. Das Hinzufügen folgt nach einer Trennlinie unter eigener
Unterüberschrift. Gibt es niemanden mehr, steht dort ein Satz statt eines
leeren Auswahlfelds.

Im Lernauftrag- und Arbeitsheft-Text legt der Positionsmarker `[bild]` fest, wo
das hochgeladene Bild steht und wo das Sprachmodell die Bildbeschreibung
erhält. Er zählt nur allein auf einer Zeile (Leerraum und Groß- und
Kleinschreibung egal); mitten in einer Zeile oder als `[bild](…)` bleibt er
gewöhnlicher Text. Der erste Marker gewinnt, weitere verschwinden. Ohne Marker
steht das Bild unter dem Text, ohne Bild verschwinden die Marker ersatzlos.

Lernauftrag- und Arbeitsheft-Text erscheinen als gerendertes Markdown im Profil
Szenentext: in der Sitzung von Training, Erhebung und Probelauf, in der
Abschrift und in der Vignetten-Detailansicht. Der Umfang gleicht dem der
Erhebungstexte (siehe „Erhebungsteilnahme"), nur ohne Links: Link-Syntax
erscheint wörtlich. Die Teile vor und nach dem Bild werden je für sich
gerendert. In der Sitzung stehen Überschriften über dem großen Fließtext der
Szene. Rechenschritte mit Einrückung lassen sich als eingerückter Block setzen. Schülernotation mit `*`, `_`, führendem `-` oder `1.` escapen
Autor:innen mit einem Backslash. Bildbeschreibung und Simulationshinweise
bleiben reiner Text. Prompt und Datenspur-Export erhalten die unveränderte
Markdown-Quelle. Im Vignettenformular stehen unter beiden Feldern der
Markdown-Hinweis ohne Link-Syntax, samt Backslash- und Einrückungsregel, und derselbe
Umschalter »Bearbeiten | Vorschau« wie bei den Erhebungstexten; die Vorschau
rendert den ungespeicherten Text im Profil Szenentext so wie die Sitzung. Bei
einem Text mit Positionsmarker zeigt sie `[bild]` wörtlich.

Im Formular zum Anlegen und Bearbeiten stehen Lernauftrag- und Arbeitsheft-Bild
jeweils mit ihrer Bildbeschreibung in einer Bildkarte. Ein Bild lässt sich
auswählen oder auf die Bildfläche ziehen; Dateien, die kein Bild sind, weist die
Karte gleich ab. Ein gewähltes oder gespeichertes Bild erscheint als Vorschau,
ein neu gewähltes ist bis zum Speichern als »Neu · noch nicht gespeichert«
markiert. Der Kopf der Karte zeigt, ob das Bild am Positionsmarker `[bild]` im
Text oder mangels Marker unter dem Text erscheint, und die Karte weist auf eine
fehlende Bildbeschreibung hin. »Bild entfernen« entfernt beim Speichern auch die
Bildbeschreibung, »Rückgängig« holt beides zurück. Hat das Formular beim
Speichern einen Fehler, geht eine gerade gewählte Datei verloren; die Karte
nennt sie dann und bittet, sie erneut zu wählen.

Formular und Detailansicht beschriften die Felder gleich und gekoppelt wie in
GLOSSARY.md, etwa »Fehlermuster-Beschreibung«, »Lernauftrag-Bild«,
»Arbeitsheft-Bildbeschreibung«, »Vorname der Schüler:in« und »Budget-Typ«. Das
gilt auch für Legende und Felder der Bildkarte. Scheitert das Finalisieren an
leeren Pflichtfeldern, nennt die Meldung sie mit diesen Beschriftungen.

Die großen Texte des Formulars (Lernauftrag- und Arbeitsheft-Text, beide
Simulationshinweise, Fehlermuster-Beschreibung und Referenzdiagnose) stehen wie
die Erhebungstexte zunächst zum Lesen, auf wenige Zeilen gekürzt; »Ganz
anzeigen« klappt einen langen Text auf. Die beiden Szenentexte erscheinen als
gerendertes Markdown, die übrigen als reiner Text. Ein leerer Text zeigt »Noch
kein Text« und statt »Bearbeiten« den Knopf »Text schreiben«; beim Anlegen gilt
das für alle. »Bearbeiten« öffnet nur diesen Text, bei den Szenentexten im
Markdown-Feld mit Vorschau, mit eigenen Knöpfen »Speichern« und »Abbrechen«.
Jeder Speichern-Knopf, am Text wie »Änderungen speichern« oder »Vignette
anlegen«, speichert die ganze Vignette mit allen Feldern und allen geöffneten
Texten; beim Anlegen legt er sie an. »Abbrechen« verwirft nur die Änderungen an diesem Text. Ein Text mit
Fehler steht nach dem Speichern offen. Wer die Seite mit ungespeicherten
Änderungen verlässt, wird vom Browser gewarnt. Die Bildbeschreibung bleibt Teil
der Bildkarte.

## Trainings verwalten

Ausbilder:innen sehen die Trainings ihres Eigentümer-Kreises;
Administrator:innen sehen alle. In der Kuratierungsansicht lässt sich eine
weitere Ausbilderin oder Administratorin als Eigentümer:in hinzufügen oder eine
vorhandene entfernen. Der Kreis bleibt auch bei veröffentlichten Trainings
besetzt; die eigene Entfernung übergibt das Training an die verbleibenden
Eigentümer:innen.

## Geschlossenes Training und Beitritt

Ein Training ist geschlossen (ADR-0049). Teilnehmende sehen im
Trainingskatalog nur Trainings, denen sie beigetreten sind; Trainingsseite,
Vignettenwahl und Sitzungsstart eines anderen Trainings antworten mit 404, auch
über die direkte Adresse. Kreis und Administration erreichen ihre Trainings
wie bisher ohne Beitritt. Wer schon vor dem Trainings-Link in einem Training
gespielt hat, gilt als beigetreten und behält Zugang und Sitzungen.

Jedes Training hat einen festen Trainings-Link. Die Kuratierseite zeigt ihn
ganz oben in einem Band „Gruppe beitreten lassen“ mit den Knöpfen „Kopieren“
und „Sperren“ und nennt darunter die Zahl der Beigetretenen. Ist der Beitritt
gesperrt, färbt sich das Band rot, heißt „Beitritt gesperrt“, und „Wieder
öffnen“ hebt die Sperre auf. Jede Eigentümerin des Kreises darf sperren und
öffnen.

Wer den Link eingeloggt öffnet, tritt bei und landet auf der Trainingsseite;
erneutes Öffnen führt ohne Fehler direkt dorthin. Ohne Anmeldung führt der
Link über den Login zurück zum Beitritt. Bei gesperrtem Beitritt sehen neue
Konten die Meldung „Beitritt gesperrt“ mit der Bitte, sich an die Ausbilder:in
zu wenden; Beigetretene kommen weiter ins Training, ebenso der Eigentümer-Kreis
und die Administration, ohne dadurch beizutreten. Der Link eines Entwurfs
nimmt noch niemanden auf. Ein Training ohne Vignetten lässt sich
veröffentlichen und beitreten.

Die Trainingsseite trägt unter dem Titel den festen Hinweis „Die
Ausbilder:innen dieses Trainings sehen Ihre abgeschlossenen Sitzungen
namentlich.“

## Fremdeinsicht im Training

Unter dem Band des Trainings-Links zeigt die Kuratierseite über die ganze
Breite die Fremdeinsicht (ADR-0049): eine Tabelle mit allen Beigetretenen als
Zeilen, nach Namen sortiert, und den Vignetten des Trainings in
Kuratierreihenfolge als Spalten. Wer noch keine abgeschlossene Sitzung hat,
steht mit gedämpfter Schrift trotzdem in der Tabelle. Jede abgeschlossene
Sitzung erscheint in ihrer Zelle als runder Kreis mit ihrer laufenden Nummer
zu dieser Vignette; beim Zeigen oder Fokussieren erscheint sofort ihr Datum.
Eine leere Zelle trägt einen blassen Strich. Ein Training ohne Vignetten zeigt
statt der Tabelle einen Hinweis.

Ein Kreis öffnet die Sitzung lesend, so wie die Teilnehmer:in sie sieht: Szene,
Transkript, Ausgang, Debrief und Diagnose, nie die Denkspur. Einsehen dürfen
alle aktuellen Eigentümer:innen des Trainings, auch für Sitzungen von vor
ihrer Aufnahme, und die Administration. Laufende, abgebrochene und
gescheiterte fremde Sitzungen, Sitzungen derselben Person in einem fremden
Training und jede Sitzung für ausgetretene Kreismitglieder, fremde Konten oder
die Autor:in der Vignette antworten mit 404. Die eigenen Sitzungen bleiben für
die Teilnehmer:in in jedem Status lesbar, ebenfalls ohne Denkspur.

Unter der Tabelle folgt die Liste „Freigegebene Abschriften“ mit den Spalten
Teilnehmer:in, Erhebung, Geholt am und Sitzungen, nach Namen sortiert. Sie
zeigt jede Abschrift, die eine Beigetretene für dieses Training freigegeben
hat, beschriftet mit Erhebungsname und Importzeitpunkt, und verlinkt ihre
abgeschlossenen Sitzungen untereinander. Ohne Freigaben steht dort „Niemand hat
eine Abschrift freigegeben.“ Eine solche Sitzung öffnet sich lesend wie eine
Trainingssitzung, ohne Denkspur und samt der gespielten Szene ihrer Vignette,
auch wenn die Vignette dem Kreis nicht gehört (dritte Ausnahme in ADR-0015).
Im Vignettenbestand des Kreises erscheint sie nicht, und aufnehmen lässt sie
sich nicht. Eine nicht freigegebene Abschrift erscheint in keiner
Fremdeinsicht, auch nicht für die Administration; nach dem Widerruf oder dem
Löschen der Abschrift antwortet auch eine gemerkte Adresse mit 404.

## Trainingsexport

In der Werkzeugleiste über der Tabelle steht rechts der Knopf „Trainingsexport
(ZIP)“, davor der gedämpfte Hinweis „pseudonym, nicht anonym“; sein Tooltip
sagt, dass Kennzeichen je Export neu gezogen werden und Freitext nicht
geschwärzt wird. Der Download heißt
`training-<id>-<name>-<UTC-Zeitstempel>.zip` und enthält genau die Sitzungen
der Fremdeinsicht (ADR-0049): je Person einen Ordner mit einem zufälligen
Kennzeichen wie `teilnehmer-3f9a01c2`, darin eine Markdown-Datei je
abgeschlossener Sitzung (`01-brüche-addieren.md`) mit Vignettenname, Ausgang,
Datum, dem Transkript als Wechsel von Eingabe und Äußerung und der Diagnose.
Freigegebene Abschriften liegen als Unterordner mit dem Erhebungsnamen im
Ordner der Person; private und widerrufene fehlen, ebenso laufende,
abgebrochene und gescheiterte Sitzungen. Das Archiv enthält keine Kontodaten,
keine Denkspur, keine Fehlversuche, keine Modell-Konfiguration und keinen
Kern; zwei Exporte vergeben verschiedene Kennzeichen. Herunterladen dürfen der
Kreis und die Administration; fremde Ausbilder:innen bekommen 404, Konten ohne
Ausbilder:innen-Rolle 403. Der Trainingsexport ist keine Datenspur und
unterliegt nicht dem Exportkontrakt aus ADR-0029.

## Simulationskern

Autor:innen und Administrator:innen können die finale Kern-Fassung und die
Modell-Konfiguration der Schüler:in schreibgeschützt unter `/system/kern/` einsehen. Ist noch
kein finaler Kern vorhanden, stellt die Ansicht das nur fest. Administrator:innen
erhalten unter `/system/kern/verwalten/` (Sidebar: Entwicklung) außerdem den Überblick über den Entwurf, die
finale Fassung und die eingeklappten archivierten Kern-Fassungen. Solange es überhaupt
keine Fassung gibt, legen sie die erste dort als Entwurf an — leer oder aus dem
Standardkern. Danach ziehen sie aus der finalen Fassung einen Entwurf, bearbeiten
dessen Vorlagen auf einer eigenen Seite, finalisieren ihn oder verwerfen ihn wieder. Der Kern trägt zu jedem Zeitpunkt genau eine finale Fassung: Das Finalisieren
archiviert die bisherige. Archivierte Fassungen bleiben eingeklappt lesbar, tragen aber keine
Aktionen mehr; eine misslungene Fassung wird nicht zurückgenommen, sondern durch eine
neue ersetzt. Das Überholen trifft laufende Sitzungen nicht, und Vignettenentwürfe
auf der bisherigen Fassung bleiben finalisierbar und spielbar. Ihre Detailansicht
weist neben dem Vorspulen-Knopf auf den überholten Pin hin; Vorspulen bleibt eine
Wahl der Autor:in.

Die drei Abschnitte der Rahmenhandlung (Hospitationseinleitung,
Gesprächseinleitung, Debrief) sind Markdown im Profil Szenentext: derselbe Umfang
wie bei den Erhebungstexten, aber ohne Links, Link-Syntax bleibt wörtlich. In
jeder Sitzung (Training, Erhebung, Probelauf) erscheinen sie gerendert. Die
Werte der Vignette werden vor dem Einsetzen escaped, sodass nur das Markdown des
Kerns wirkt: `**$thema**` hebt das Thema hervor, ein Thema mit `*` oder `_`
erscheint dagegen wörtlich. Die Leseansichten der Kern-Fassungen zeigen die
Rahmenhandlung gerendert, die Platzhalter wörtlich als `$name`; ein leerer
Abschnitt zeigt »—«. Auf der
Bearbeitungsseite des Entwurfs tragen die drei Felder denselben Markdown-Hinweis
und Umschalter »Bearbeiten | Vorschau« wie das Vignettenformular; auch dort
bleiben die Platzhalter in der Vorschau wörtlich stehen.

Auf der Bearbeitungsseite stehen die drei Abschnitte der Rahmenhandlung und die
beiden Prompt-Vorlagen wie die großen Texte des Vignettenformulars zunächst
gekürzt zum Lesen, die Rahmenhandlung gerendert, die Prompt-Vorlagen als reiner
Text. »Bearbeiten« bzw. bei leerem Text »Text schreiben« öffnet nur diesen
Text. Jeder Speichern-Knopf, am Text wie »Kern-Entwurf speichern«, speichert den
ganzen Entwurf; »Abbrechen« verwirft nur die Änderungen an diesem Text. Ein
Text mit ungültigem Platzhalter steht nach dem Speichern offen. Wer die Seite
mit ungespeicherten Änderungen verlässt, wird vom Browser gewarnt.

## Modell-Konfiguration

Administrator:innen setzen das Sprachmodell unter `/system/modell-konfiguration/`.
Jede Konfiguration trägt eine Bezeichnung, die beim Anlegen Pflicht ist und
danach wie alle Felder unveränderlich bleibt; eindeutig muss sie nicht sein.
Konfigurationen, die vor Einführung der Bezeichnung angelegt wurden, heißen
»<Sprachmodell> (Nr. <Nummer>)«.
Der Anbieter ist eine feste Auswahl — `fake`, `openrouter` oder `infomaniak` —,
der Modellname bleibt freier Text; Basis-URL und Token liegen an der Konfiguration
und nicht in der Umgebung. Die Parameter nehmen nur Mikro-Stellschrauben des
Modellverhaltens auf, bei `fake` ausschließlich das Skript. Im Editor schlägt
neben dem Sprachmodell der Knopf „Modelle und Basis-URL laden“ die Modelle des
gewählten Anbieters vor: bei `openrouter` die mit Structured Output, bei
`infomaniak` die Sprachmodelle des Kontos. Die beiden unterscheiden sich darin,
was der Abruf verlangt: `openrouter` beantwortet seine Modellliste öffentlich,
ganz ohne Zugangsdaten, `infomaniak` erst gegen das im Formular eingetippte
Token — weder eine gespeicherte Fassung noch die Basis-URL sind dafür nötig.
Bei `fake` erscheint der Knopf nicht; dieser Anbieter telefoniert nicht nach
außen. Bei `infomaniak` füllt derselbe Druck zusätzlich die Basis-URL: Aus der
Produktabfrage des Kontos entsteht die Endpunktwurzel des Sprachmodells. Sie
entsteht nur bei genau einem AI-Produkt — ein geratenes wäre schlimmer als ein
leeres Feld — und überschreibt nie eine schon getippte Angabe. Die Liste wird
nur auf Druck geholt und bleibt ein Vorschlag — ein Name, den sie nicht kennt,
ist weiterhin eintragbar, und die eingesetzte Wurzel ist frei überschreibbar.
Über die Tauglichkeit sagt der Vorschlag nichts: Was die Liste führt, kann an
dieser Naht trotzdem scheitern, und was sie nicht führt, kann laufen. Die
prüfende Instanz bleibt der Probelauf — er entlarvt ein untaugliches Modell,
bevor es eine Erhebung erreicht.
Aktiv ist je Verwendung (Schüler:in, Lehrperson, Bewerter) höchstens eine
Konfiguration; dieselbe darf mehreren Verwendungen dienen, und eine einmal
belegte Verwendung bleibt belegt. Sitzungen, Probelauf, Training und der Pin der
Erhebung lesen allein die Verwendung Schüler:in; Lehrperson und Bewerter sind den
Evals vorbehalten und bleiben unbelegt, bis die Administration sie setzt.
Die Seite zeigt alle je angelegten Konfigurationen als schmale Tabelle, die
neueste zuerst: Bezeichnung, darunter das Sprachmodell, dazu Anbieter und
Anlagedatum. Konfigurationen, die vor Einführung des Anlagedatums entstanden,
tragen dort den Zeitpunkt ihrer frühesten Sitzung — da bestand sie nachweislich
schon; nie gebrauchte zeigen »—«, statt den Zeitpunkt der Umstellung als Datum
auszugeben. Die Kürzel S, L
und B vor der Bezeichnung nennen die Verwendungen, für die eine Konfiguration
gerade aktiv ist. Neben der Tabelle steht das Detail der gewählten Zeile: Nr.,
Anlagezeitpunkt, Bezeichnung, Anbieter, Sprachmodell, Basis-URL, maskiertes Token
und Parameter. Ohne Wahl zeigt es die Konfiguration der Schüler:in, solange keine
aktiv ist die neueste. Im Detail steht je Verwendung ein Knopf, etwa „Für
Bewerter aktivieren (statt …)“ mit der Bezeichnung der bisher aktiven
Konfiguration; bei einer unbelegten Verwendung entfällt der „statt“-Teil. Ist die
gewählte Konfiguration für eine Verwendung schon aktiv, steht dort ein
deaktivierter Knopf „Aktiv für …“. Das Umschalten fragt nicht nach, bewegt nur
den Zeiger der genannten Verwendung und führt zurück auf dieselbe Konfiguration;
eine unbekannte Verwendung ergibt 404.
Die Seite bietet genau zwei Gesten: Anlegen und Aktivieren. Angelegt wird in
einem getrennten Editor unter `/system/modell-konfiguration/neu/`, erreichbar
über „Neue Konfiguration“ im Kopf der Liste. Die Bezeichnung steht dort zuerst.
„Als Vorlage für eine neue Konfiguration“ im Detail öffnet den Editor mit
Anbieter, Basis-URL, Sprachmodell und Parametern der gewählten Zeile und der
Bezeichnung mit dem Zusatz „(Kopie)“; eine unbekannte Vorlage ergibt 404. Das
Token übernimmt die Vorlage nie, es wird jedes Mal neu eingegeben. Die Vorlage
bleibt unverändert, angelegt wird immer eine neue Zeile. Der Editor prüft die
Anbieterbindung wie zuvor am Feld und aktiviert nichts: Nach dem Anlegen führt er
mit einer Meldung zurück zur Liste, die neue Konfiguration im Detail, und alle
Verwendungen bleiben, wie sie waren. Bearbeiten und Löschen gibt es nicht —
eine Konfiguration ist unveränderlich, weil jede Erhebung ihre Fassung pinnt. Ein
Umschalten der Schüler:in trifft laufende Trainings sofort und laufende Erhebungen
gar nicht; eine Schlüsselrotation ist deshalb kein Feldupdate, sondern Anlegen
plus Aktivieren für jede Verwendung der alten Fassung. Das Token wird eingegeben,
aber nie zurückgegeben: Das Detail zeigt es nur maskiert mit seinen letzten vier
Zeichen, kurze Werte ausschließlich als Punkte.
Im freien Probelauf der Administration steht jede Konfiguration zur Auswahl als
»Bezeichnung (Sprachmodell)«.

## Evalkatalog

Administrator:innen pflegen unter `/system/evalkatalog/` (Sidebar: System) den
Evalkatalog, gegen den künftig jeder Evallauf prüft (ADR-0046). Eine Instanz
startet ohne Katalog; einen Standardkatalog gibt es nicht. Solange die Linie
leer ist, bietet die Seite „Evalkatalog anlegen“ an. Das legt einen leeren
Entwurf an und öffnet dessen Editor. Es gibt höchstens einen Entwurf zugleich:
Mit Entwurf bietet die Seite nur „Entwurf bearbeiten“ und „Entwurf verwerfen“
an, ein zweites Anlegen wird mit einer Meldung abgelehnt. Das Verwerfen löscht
den Entwurf, danach lässt sich wieder ein Katalog anlegen.

Der Editor zeigt links den Katalog als Baum, rechts den gewählten Knoten. Der
Baum trägt die Knoten „Durchlauf und Vorlagen“ und „Übergreifende Kriterien“,
darunter jedes Eval als eigenen Knoten in seiner Reihenfolge, unter jedem Eval
seine Evalinputs.
„Durchlauf und Vorlagen“ trägt *k*, die Zahl der
Wiederholungen je Evalinput (Startwert 3), die Lehrperson-Vorlage und die
Bewerter-Vorlage. Unter jeder Vorlage stehen ihre erlaubten Platzhalter als
Knöpfe: in der Lehrperson-Vorlage die des Promptvertrags sowie `$inputstrategie`
und `$verlauf`, in der Bewerter-Vorlage die des Promptvertrags sowie
`$kriterium` und `$verlauf`. Hervorgehoben und vorn steht der Platzhalter, den
nur diese Vorlage kennt. Ein Klick fügt ihn an der Schreibmarke ein. Geprüft
werden die Vorlagen erst beim Finalisieren. „Änderungen speichern“ übernimmt die
Werte und bleibt im Editor, „Abbrechen“ führt ohne Speichern zurück zur
Übersicht. Die Aktionszeile klebt wie bei den übrigen Formularen oben. Wer den
Editor mit ungespeicherten Änderungen verlässt, wird vom Browser gewarnt.

Am Knoten „Übergreifende Kriterien“ (im Baum mit der Zahl seiner Kriterien)
pflegt die Administrator:in die Rubriken, nach denen der Bewerter jedes
Evalgespräch aller Evals beurteilt, etwa Rollentreue. Kriterien sind reiner Text
ohne Platzhalter; ein Hinweis am Knoten bittet, sie kern-neutral zu formulieren
(ADR-0046). Das ist eine Pflegeregel, keine Prüfung. „Kriterium hinzufügen“
hängt ein leeres Kriterium ans Ende. Je Zeile rücken Hoch und Runter das
Kriterium um eine Stelle, wie bei den Zuordnungslisten der Erhebung; Hoch ist an
der ersten, Runter an der letzten Zeile gesperrt. Der Papierkorb löscht es. Die
Reihenfolge bleibt gespeichert. Jede dieser Gesten übernimmt zugleich die
getippten Texte aller Kriterien, ebenso „Änderungen speichern“. Ein Katalog darf
ohne übergreifende Kriterien auskommen. Ein neuer Entwurf aus einer finalen
Fassung übernimmt die Kriterien in gleicher Reihenfolge. Alle schreibenden
Routen des Knotens erreichen nur Entwürfe.

„Eval hinzufügen“ unter dem Baum hängt ein Eval namens „Neues Eval“ ans Ende und
öffnet seinen Knoten. Dort benennt die Administrator:in das Eval um (höchstens
200 Zeichen, ein längerer Name bleibt ungespeichert); ein Eval ohne Namen
erscheint im Baum als „Unbenanntes Eval“. Neben dem Namen rücken Hoch und
Runter das Eval um eine Stelle im Katalog (an erster bzw. letzter Stelle
gesperrt), der Papierkorb löscht es samt Evalkriterien und Evalinputs und führt zurück
zu „Durchlauf und Vorlagen“. Darunter pflegt sie die Evalkriterien des Evals,
nach denen der Bewerter jedes Evalgespräch dieses Evals beurteilt: anlegen,
bearbeiten, löschen und umordnen genau wie die übergreifenden Kriterien, ebenfalls
reiner Text ohne Platzhalter. Jede Geste im Editor, auch „Eval hinzufügen“ aus
einem anderen Knoten heraus, übernimmt zugleich alle getippten Werte des
Formulars; gültige Werte von „Durchlauf und Vorlagen“ eingeschlossen. Ein
ungültiger Wert dort, etwa ein negatives *k*, bleibt ungespeichert; der Editor
nennt ihn, und „Änderungen speichern“ meldet dann keinen Erfolg. Ein neuer
Entwurf aus einer finalen Fassung übernimmt die Evals samt Evalkriterien in
gleicher Reihenfolge. Leere Kriterien weist erst das Finalisieren zurück.
Alle schreibenden Routen der Evals und Evalkriterien erreichen nur Entwürfe.

Am Eval-Knoten legt „Evalinput hinzufügen“ einen weiteren Evalinput an; ein Eval
darf mehrere haben. Ein neuer Evalinput startet mit drei leeren, festen
Inputschritten und öffnet seinen Knoten. Im Baum hängt jeder Evalinput unter
seinem Eval („Evalinput 1“, „Evalinput 2“ …), daneben die Folge seiner Schritte
als Kürzel, F für fest und G für gelenkt (etwa „FGF“). Der Knoten zeigt den
Evalinput als Drehbuch: Die Inputschritte stehen untereinander, nach jedem steht
„Schüler:in antwortet“. Ein Segmentknopf je Schritt wählt zwischen „sagt
wörtlich“ (fest: der Text ist die Inputäußerung) und „formuliert nach
Strategie“ (gelenkt: der Text ist die Inputstrategie, auch bedingt formuliert).
Gelenkte Schritte erscheinen als gestrichelte, kursive Blase. Inputschritte
sind reiner Text ohne Platzhalter. „Inputschritt hinzufügen“ hängt einen leeren,
festen Schritt ans Ende; je Schritt rücken Hoch und Runter ihn um eine Stelle (am
Rand gesperrt), der Papierkorb entfernt ihn. Reihenfolge, Art und Text bleiben
gespeichert; jede Geste übernimmt zugleich alle getippten Werte. Der Papierkorb
am Kopf löscht den Evalinput samt seiner Schritte und führt zurück zum Eval.
Neben dem Drehbuch stehen die Evalkriterien des Evals, nach denen seine
Gespräche beurteilt werden. Die Länge eines Evalgesprächs ist die Zahl der
Inputschritte; eine eigene Obergrenze gibt es nicht. Ein neuer Entwurf aus einer
finalen Fassung übernimmt die Evalinputs samt Inputschritten. Leere Schritte
weist erst das Finalisieren zurück. Alle schreibenden Routen der Evalinputs und
Inputschritte erreichen nur Entwürfe.

„Finalisieren“ in der Aktionszeile des Editors übernimmt zuerst alle getippten
Werte und prüft dann den Entwurf, ohne ein Sprachmodell aufzurufen. Abgelehnt
wird er, wenn eine Vorlage leer ist, einen ungültigen Platzhalter enthält oder
einen Platzhalter außerhalb ihres Vertrags (`$kriterium` in der
Lehrperson-Vorlage, `$inputstrategie` in der Bewerter-Vorlage, unbekannte
Namen), wenn *k* kleiner als 1 ist, wenn der Katalog kein Eval hat, ein Eval
kein Evalkriterium oder keinen Evalinput, ein Evalinput keinen Inputschritt,
oder wenn ein Inputschritt, ein Evalkriterium oder ein übergreifendes Kriterium
leer ist. Übergreifende Kriterien dürfen fehlen. Der Editor nennt dann jede
Lücke als eigene Meldung, etwa „Evalinput 2 von Eval „Muster“ hat keinen
Inputschritt.“ oder „Die Bewerter-Vorlage enthält Platzhalter außerhalb ihres
Vertrags: $inputstrategie.“; der Entwurf bleibt Entwurf, die getippten Werte
bleiben gespeichert. Ist der getippte Durchlauf selbst ungültig, etwa ein
negatives *k*, bleibt der ungültige Wert ungespeichert, gültige Vorlagen werden
übernommen, der Editor nennt den Fehler, und der Entwurf bleibt Entwurf. Ebenso
bleibt er Entwurf mit einer Meldung, wenn er beim Finalisieren inzwischen
geändert wurde. Ein vollständiger Entwurf wird final, und die
Administrator:in landet auf der Übersicht, die zeigt, seit wann die finale
Fassung gilt. Ab dann prüft jeder Evallauf gegen sie. Die bisherige finale
Fassung ist im selben Schritt überholt; überholt ist nicht umkehrbar, es gibt
immer genau eine finale Fassung. Andere Apps fragen sie über
`Evalkatalog.objects.finale_fassung()` ab, das ohne finale Fassung `None`
liefert.

Finale und überholte Fassungen lassen sich vollständig lesen, damit
nachvollziehbar bleibt, wogegen ein älterer Evallauf geprüft hat. Die Übersicht
führt mit „Finale Fassung lesen“ zur finalen Fassung und listet unter
„Überholte Fassungen“ jede überholte, die zuletzt gültige zuerst, mit dem
Datum, ab dem sie galt. Beide öffnen sich im Editor über dieselben Adressen wie
ein Entwurf, mit Baum und allen Knoten. Ein Hinweisband nennt den Zustand („final
seit …“ bzw. „überholt“, mit dem Datum, ab dem sie galt). Alle Felder sind
gesperrt; Platzhalterknöpfe, Hinzufügen, Hoch, Runter, Löschen, Speichern und
Finalisieren fehlen, die Aktionszeile führt nur zurück zur Übersicht. Jede
schreibende Anfrage an eine finale oder überholte Fassung wird abgewiesen.

„Neue Fassung“ (auf der Übersicht und im Hinweisband der finalen Fassung) leitet
aus der finalen Fassung einen Entwurf ab und öffnet seinen Editor. Der Entwurf
ist eine Tiefenkopie: *k*, beide Vorlagen, die übergreifenden Kriterien und der
ganze Baum aus Evals, Evalkriterien, Evalinputs und Inputschritten (mit Art und
Text) in gleicher Reihenfolge; er verweist auf die finale Fassung als
Vorgängerin. Änderungen am Entwurf berühren die Vorgängerin nicht. Solange ein
Entwurf besteht, bieten die Seiten „Neue Fassung“ nicht an, und ein Versuch wird
mit der Meldung „Ein Evalkatalog-Entwurf existiert bereits.“ abgelehnt. Aus
überholten Fassungen und Entwürfen lässt sich keine neue Fassung ableiten.

Autor:innen und alle anderen Rollen erhalten auf keiner Route des Evalkatalogs
Zugriff.

## Transkriptions-Konfiguration

Die Transkription hängt an einer eigenen Konfiguration, die die Administration
unter `/system/transkription/` bearbeitet — mit denselben Anbieterfeldern wie das
Sprachmodell, aber unabhängig davon: Das Gespräch darf über den einen und das
Audio über den anderen Anbieter laufen. Es gibt genau eine Zeile und genau eine
Geste, Bearbeiten; eine Tokenrotation überschreibt sie, statt eine Fassung
anzulegen, denn diese Konfiguration wird weder gepinnt noch exportiert
(ADR-0026). Ein leer gelassenes Tokenfeld heißt »unverändert«, nicht »löschen«.
Neben dem Transkriptionsmodell steht derselbe Knopf „Modelle und Basis-URL
laden“ wie an der Sprachmodell-Naht: bei `openrouter` die Modelle mit
Transkriptions-Modalität — in der ungefilterten Modellliste erscheinen sie
nicht —, bei `infomaniak` das eine Modell vom Typ `stt` und dazu die
Endpunktwurzel der Transkription, die bei diesem Anbieter unter einer anderen
API-Version liegt als die des Sprachmodells. Der eingesetzte Wert trägt hier
bei beiden Anbietern kein Präfix: Diese Naht läuft nicht über LiteLLM, sondern
reicht den Namen roh an die Route des Anbieters durch. Abgefragt wird wie an der
Sprachmodell-Naht: `openrouter` ohne Zugangsdaten, `infomaniak` gegen das
getippte Token — auch dann, wenn schon eines hinterlegt ist.
Ob überhaupt transkribiert wird, entscheidet weiterhin die Instanz über
`TRANSKRIPTION_ZERO_RETENTION` in der Umgebung — die Zusage der Betreiber:in
gehört nicht in dasselbe Formular wie die Anbieterwahl.

## Audioverarbeitung im Training

Vor dem ersten Start eines Trainings entscheiden Teilnehmende einmalig, ob ihr
Audio zur Transkription an einen externen Auftragsverarbeiter übermittelt werden
darf. Das Audio wird danach nicht gespeichert. Bei Ablehnung bleibt das Training
uneingeschränkt über die Tastatur spielbar.

Nach Einwilligung lässt sich jede Frage im Diagnosegespräch per Tastatur oder
über „Spracheingabe starten“ eingeben. Die Aufnahme wird bewusst beendet, direkt
transkribiert und anschließend automatisch als Gesprächsschritt abgeschickt;
das Transkript wird davor nicht bearbeitet. Im Debrief kann die Diagnose ebenfalls
in mehreren Aufnahmen ergänzt werden; erst „Training beenden“ schickt sie bewusst
und unwiderruflich ab. Bei einer leeren oder fehlgeschlagenen Transkription kann
die Aufnahme wiederholt werden.

In Gespräch und Debrief steht das Feld in voller Breite. Darunter liegt die
Eingabezeile: links der umrandete Knopf der Spracheingabe mit Mikrofon-Symbol,
daneben ihr Status, rechts „Senden“ bzw. „Diagnose abgeben“ als einzige gefüllte
Hauptaktion. Während einer Aufnahme ist der Knopf rot umrandet („Spracheingabe
beenden“) und vor dem Status pulsiert ein roter Punkt. Während der Transkription
ist der Knopf gesperrt, vor dem Status dreht sich ein Spinner und das Feld ist
schreibgeschützt. In beiden Phasen ist Senden gesperrt. Fehler erscheinen rot im
Status. Ohne Einwilligung gibt es keinen Knopf; an seiner Stelle steht still
„Spracheingabe nicht freigegeben. Sie nutzen die Tastatur.“ Auf schmalen
Bildschirmen stehen Spracheingabe und Senden in einer Zeile, der Status darunter.

Im Gespräch folgt unter der Eingabezeile eine eigene Aktionszeile, durch eine
Trennlinie abgesetzt. Rechts steht „Gespräch beenden →“ als grau umrandeter
Knopf, davor in gedämpfter Schrift „Genug gefragt? Danach folgt der Debrief mit
Ihrer Diagnose.“ Links steht in Training und Erhebung „Sitzung abbrechen“ als
roter Textlink; die Sitzung wird damit verworfen. Im Probelauf gibt es kein
Abbrechen. Beide Aktionen wirken ohne Rückfrage. Nach einer fehlgeschlagenen
Antwort heißt der Knopf „Gespräch beenden und Debrief anzeigen“. Im Debrief gibt
es keine Aktionszeile. Auf schmalen Bildschirmen steht der Erklärsatz allein
oben, Abbrechen und Beenden teilen sich die Zeile darunter.

Eine einzelne Aufnahme ist auf 15 MB begrenzt — je nach Kodierung grob 15 bis 60
Minuten Sprache. Ist die Grenze erreicht, endet die Aufnahme von selbst und wird
transkribiert; das bereits Gesagte geht nicht verloren. Dieselbe Grenze hält der
Transkriptions-Endpunkt: Eine größere Aufnahme lehnt er ab, bevor er sie einliest.

Im **Probelauf** der Autor:innen gibt es keinen Einwilligungsschritt: Dort
spricht die angemeldete Autor:in über ihr eigenes Material, nicht eine
pseudonyme Teilnehmer:in. Das Mikrofon steht im Diagnosegespräch und im
Debrief unmittelbar bereit und hängt allein an
`TRANSKRIPTION_ZERO_RETENTION`.

## Erhebungsteilnahme

Ein Teilnahme-Link einer Stichprobe legt im Browser eine pseudonyme Teilnahme an
oder setzt sie fort. Dafür ist kein Nutzerkonto erforderlich; die
Forschungsdaten sind über ein ablesbares Teilnahme-Token von Trainingsaktivitäten
getrennt. Während das Teilnahmefenster läuft, führt der Link zuerst über die
Einwilligung und die Instruktion; diese weist darauf hin, dass das
Diagnosegespräch begrenzt ist. Anschließend werden die gezogenen Vignetten als
persistierte Sitzungen gespielt; Gespräch, Diagnose und interne Denkspur bleiben
Teil der Datenspur, wobei die Denkspur nie in der Teilnehmer:innenansicht erscheint.
Die Einwilligungsseite zeigt unter dem Einwilligungstext der Forschenden drei
getrennte Einwilligungen mit je einem festen, nicht abschaltbaren Systemtext zur
Folge einer Ablehnung: Verarbeitung durch Sprachmodelle, Spracherkennung und
Speicherung und Verwendung für Forschungszwecke; der Text zur Speicherung nennt
den Widerruf per Teilnahme-Token bei der Studienleitung. Jede ist eine
Pflichtwahl Ja/Nein ohne Vorauswahl, danach folgt »Weiter«. Die Spracherkennung
wird nur gefragt, wenn die Instanz transkribiert (Zero-Retention-Zusage
gesetzt). Wer der Verarbeitung durch Sprachmodelle nicht zustimmt, landet auf
einer systemseitigen Abbruchseite ohne Abschlusstext, Fragebogen oder Token;
Teilnahme-Link, Token-Wiedereinstieg und alle übrigen Teilnahmeseiten führen
dann dorthin, und es entstehen weder Ziehung noch Sitzung. Ihr Knopf »Zur
Startseite der Erhebung« führt zurück zum Einwilligungsformular ohne
Vorauswahl; eine neue Entscheidung ersetzt die alte. Ist die Verarbeitung durch
Sprachmodelle einmal erteilt, stehen alle drei Entscheidungen fest; ein
erneuter Aufruf des Einwilligungsformulars führt dann in den Ablauf.
Wer der Speicherung nicht zustimmt, macht eine flüchtige Teilnahme: Die
Vignetten werden genauso gespielt, Verlauf, Debrief und Diagnose erscheinen wie
gewohnt, und ein Neuladen im selben Browser setzt an derselben Stelle fort.
Gesprächsschritte, Fehlversuche und Diagnose liegen dabei aber nur in der
Browser-Session und werden nie gespeichert; gespeichert und exportiert wird nur
das Ablaufgerüst (Ziehung, Sitzungen mit Status, Zeitstempeln und verbrauchter
Zeit, Vignettenposition). Auch die Fragebögen werden ihr wie allen anderen
vorgelegt, doch ihre Antworten werden beim Abschicken verworfen: Es entsteht
keine Item-Antwort, auch keine Markierung »vorgelegt, übersprungen«; nur der
Itemblock hält mit Vorlage und Erledigung fest, dass der Ablauf weiterging.
Das Token führt auch eine flüchtige Teilnahme in einem anderen Browser fort.
Liegt der Verlauf einer laufenden Sitzung dort nicht vor, etwa in einem anderen
Browser oder nach Ablauf der Session, endet diese Sitzung als `abgebrochen`,
statt mit einer Schüler:in ohne Gedächtnis weiterzulaufen. Danach geht der
Ablauf regulär weiter: mit dem Fragebogen der Sitzung, der nächsten Vignette
oder dem Abschluss.
Wer der Spracherkennung zustimmt, kann Eingaben im Diagnosegespräch und die
Diagnose per Mikrofon eingeben; ohne Zustimmung bleibt die Tastatureingabe
vollständig nutzbar.
Nach jeder beendeten Sitzung erscheinen ihre freiwilligen Fragebogen-Items direkt
unter dem Verlauf; sie können beantwortet oder übersprungen werden, bevor die
nächste Vignette beginnt. Nach der letzten Sitzung folgen zusätzlich die
freiwilligen Fragebogen-Items am Andockpunkt `am Ende` als eigene Seite. Jede
Item-Antwort wird sofort gespeichert, und auch übersprungene Fragebogen-Items
bleiben als vorgelegt dokumentiert. Likert-Items bieten dabei die global
festgelegten Skalenpole zur Auswahl an; festgehalten wird die zugehörige Stufe.
Ein noch nicht abgeschickter Fragebogen — nach einer Sitzung ebenso wie am
Ende — wird auch in einem anderen Browser erneut vorgelegt; ein abgeschickter
nicht mehr. Der gesamte Fortschritt hängt am
Teilnahme-Token und nicht am Browser: Ein Aufruf setzt die Teilnahme genau dort
fort, wo sie steht — bei der Instruktion, im laufenden Gespräch, beim offenen
Fragebogen oder bei der nächsten Vignette. Anschließend endet die Teilnahme
mit dem Abschlusstext.
Damit das Token jederzeit ablesbar ist, zeigt die Seitenleiste es auf allen
Teilnahmeseiten — von der Einwilligung über Instruktion, Diagnosegespräch und
Debrief bis zu Fragebogen- und Abschlussseite — an der Stelle, an der sonst
Konto oder Anmeldelink stehen, in fester Laufweite und mit der Bitte, es zu
notieren.
Während einer Teilnahme erscheinen dort weder Kontoblock noch Anmeldelink, auch
nicht bei nebenbei angemeldetem Konto; in Forschenden-Ansichten erscheint
umgekehrt kein Teilnahme-Token.
Unter dem Abschlusstext steht auf der Abschlussseite zusätzlich ein
systemseitiger Hinweis, den die Forschende nicht abschalten kann: das Token
groß und in fester Laufweite, dazu die Erklärung, dass sich damit angemeldet
später eine Abschrift der eigenen Sitzungen ins Nutzerkonto holen lässt und
dass es ohne das Token keine Abschrift gibt, samt Link auf die Token-Eingabe.
Ein erneuter Aufruf der Abschlussseite zeigt beides wieder.
Bei einer flüchtigen Teilnahme ersetzt diesen Baustein der ebenso
unabschaltbare Hinweis »Sie haben der Speicherung Ihrer Daten nicht zugestimmt.
Ihre Gespräche, Diagnosen und Fragebogen-Antworten wurden deshalb nicht
gespeichert.« — ohne Token, Abschrift-Erklärung und Link; auch er erscheint bei
jedem Aufruf wieder. Abschlusstext und Token in der Seitenleiste bleiben.
Ein Diagnosegespräch kann vorzeitig in den Debrief geführt werden; eine Sitzung
kann ohne Diagnose abgebrochen werden. Ist die Diagnose abgegeben, bleibt sie im
Debrief sichtbar, lässt sich aber nicht mehr ändern; hängt an der Sitzung ein
Fragebogenblock, erscheint er darunter als eigener Abschnitt. Scheitert ein Antwortversuch endgültig,
bleibt der Gesprächsschritt ohne Antwort erhalten.
Nach dem Teilnahmefenster sind unfertige Teilnahmen verfallen und nicht fortsetzbar.

Einwilligungs-, Instruktions- und Abschlusstext erscheinen als gerendertes
Markdown: Absätze durch Leerzeilen, jeder einfache Zeilenumbruch bleibt
erhalten, dazu **fett**, *kursiv*, Aufzählungen, nummerierte Listen und
Zitatblock. Überschriften `#`, `##` und `###` ordnen sich als dritte bis fünfte
Ebene unter den Abschnittskopf der Seite ein. Ein nach einer Leerzeile um vier
Leerzeichen eingerückter Block erscheint in Festbreitenschrift und behält seine
Einrückung. Links sind nur mit `https:`, `http:` und `mailto:` möglich. Web-Links
öffnen in einem neuen Tab, tragen einen sichtbaren Pfeil und kündigen Screenreadern
das Öffnen in neuem Tab an; E-Mail-Links öffnen das Mailprogramm im selben Tab,
tragen einen Briefumschlag und kündigen sich als E-Mail an. Rohes
HTML, Bilder, Tabellen, umzäunte Codeblöcke, tiefere Überschriften, andere Link-Ziele
wie `javascript:` oder relative Pfade sowie nackte URLs erscheinen wörtlich;
ein vorangestellter Backslash zeigt Markdown-Zeichen wörtlich.

## Abschriften holen

Unter `/trainings/abschriften/` gibt jedes eingeloggte Konto ein Teilnahme-Token
ein und holt damit eine abgeschlossene Erhebungsteilnahme als **Abschrift** in
das eigene Konto: Die Sitzungen werden unter eine eigene, neue Teilnahme kopiert;
Fragebogen-Antworten bleiben bei der Erhebung. Die Erhebungsdaten selbst bleiben
unberührt, es wird kein Token gespeichert und keine Verknüpfung zwischen Konto
und Teilnahme festgehalten. Der Import gelingt unabhängig vom Teilnahmefenster,
solange weder Stichprobe noch Erhebung archiviert sind, und ist beliebig oft
wiederholbar; jede Wiederholung erzeugt eine weitere Abschrift. Unbrauchbare
Tokens — auch das einer flüchtigen Teilnahme — werden ohne Angabe eines Grundes
abgelehnt. Die Liste zeigt je Abschrift
den Namen der Erhebung und den Importzeitpunkt — nicht die Spielzeit der
Erhebung.
Von der Liste führt jede Abschrift in eine eigene, nur lesende Ansicht: die
gespielten Vignetten in der Reihenfolge ihrer Vignettenposition, je Vignette
Lernauftrag und Arbeitsheft, das Transkript des Diagnosegesprächs, den Ausgang
der Sitzung und die eigene Diagnose. Die Denkspur der simulierten Schüler:in erscheint auch hier nicht; es
gibt weder Eingabefeld noch Sitzungsnavigation. Abschriften sind kontoprivat —
eine fremde ist nicht erreichbar. Aus der Ansicht heraus lässt sich die Abschrift
löschen; dabei verschwinden ihre Teilnahme, die kopierten Sitzungen und alle
Freigaben, während die Daten der Erhebung unberührt bleiben.

Vor dem Löschknopf steht die Sektion „Freigabe“: eine Checkbox-Liste aller
Trainings, denen das Konto beigetreten ist, angehakt heißt freigegeben, und der
Knopf „Freigaben speichern“. Freigegeben wird immer die ganze Abschrift, für
beliebig viele Trainings und unabhängig davon, ob ihre Vignetten zum Training
gehören (ADR-0049). Ein abgewählter Haken widerruft die Freigabe sofort. Ein
Training ohne eigene Trainingsbindung wird mit 404 abgewiesen. Der Seitenkopf
nennt die Trainings, für die die Abschrift freigegeben ist; ohne Freigabe heißt
es dort „Ihre Abschrift — nur Sie lesen sie.“ Einen Hinweis auf bereits
gezogene Trainingsexporte oder zur Wiedererkennung durch Forschende gibt es
bewusst nicht. Wer noch keinem Training beigetreten ist, liest statt der Liste
einen Hinweis.

## Erhebungen verwalten

Forschende und Administrator:innen erreichen unter `/erhebungen/eigene/` die
Erhebungen ihres Eigentümer-Kreises; Administrator:innen sehen dort alle
Erhebungen und arbeiten an ihnen mit denselben Gesten wie Forschende. Eine neue
Erhebung bekommt auf einer eigenen Anlegen-Seite ihren Namen: höchstens 255
Zeichen, Leerzeichen am Rand werden abgeschnitten, ein leerer Name wird
abgelehnt. Ein Hilfetext am Feld nennt, wo der Name erscheint (Erhebungsliste,
Dateiname der Datenspur, Abschriften der Teilnehmenden). Meldungen stehen am
Feld, die Eingabe bleibt nach einem Fehler stehen. Umbenennen lässt sich eine
Erhebung nicht. In einem Entwurf stellen sie finale Vignetten zu einer Liste
zusammen (siehe unten) und pflegen Instruktions-, Einwilligungs- und
Abschlusstext. Die drei Texte stehen im Entwurf zunächst
gerendert zum Lesen, auf wenige Zeilen gekürzt; »Ganz anzeigen« klappt einen
langen Text auf. Ein leerer Text zeigt »Noch kein Text« und statt
»Bearbeiten« den Knopf »Text schreiben«. »Bearbeiten« öffnet nur diesen Text
im Markdown-Feld, mit eigenen Knöpfen »Speichern« und »Abbrechen«. Jeder
Speichern-Knopf der Seite, am Text wie unter den Texten »Konfiguration
speichern«, speichert alle drei Texte, auch die geöffneten.
»Abbrechen« verwirft nur die Änderungen an diesem Text. Auch »Finalisieren«
speichert vorher alles, offene Texte eingeschlossen. Wer die Seite mit
ungespeicherten Änderungen verlässt, wird vom Browser gewarnt. Die drei Texte
bleiben optional und sperren das Finalisieren nicht. Unter jedem Markdown-Feld
steht ein kurzer Markdown-Hinweis samt Link-Syntax; der Umschalter
»Bearbeiten | Vorschau« zeigt den ungespeicherten Text so, wie die
Teilnahmeseite ihn rendert. Die Vorschau holt das Fragment vom Endpunkt `/texte/vorschau/`, der
Quelle und Profil (Informations- oder Szenentext) annimmt, mit derselben
Funktion wie die Anzeigeseite rendert und nichts speichert; er steht nur
angemeldeten Autor:innen, Forschenden und Administrator:innen offen. Finale und
archivierte Erhebungen zeigen die drei Texte gerendert als Leseansicht, ein
leerer Text erscheint als »—«. Reine Entwürfe lassen sich löschen; das Design
finaler Erhebungen bleibt unveränderlich, ihr Eigentümer-Kreis änderbar. Das
Finalisieren pinnt die Modell-Konfiguration der Verwendung Schüler:in
sichtbar; ein Rückzug ist nur ohne nicht-archivierte oder
datentragende Stichprobe möglich. Finale Erhebungen lassen sich archivieren und
wieder entarchivieren, sofern keine Stichprobe läuft und mindestens eine
Eigentümerin eingetragen ist. Eigentümer:innen teilen und übergeben eine Erhebung
über die Detailansicht; auch bei finalen und laufenden Erhebungen bleibt dieser
Kreis änderbar. Unter einer finalen Erhebung lassen sich
Stichproben mit Beginn und Ende anlegen; die Detailseite zeigt ihren kopierbaren
Teilnahme-Link, ihre aus dem Zeitraum abgeleitete Phase — geplant, läuft oder
abgeschlossen — und die Zahl ihrer Teilnahmen. Daneben stehen, nach dem
aktuellen Stand der Einwilligungen, die Zahl der Teilnahmen, die die Verarbeitung
durch Sprachmodelle abgelehnt haben, und die Zahl der Teilnahmen ohne
Speicherung. Datenfreie Stichproben lassen sich archivieren; die Phasenspalte
weist sie danach als archiviert aus.
Der optionale Fragebogen eines Entwurfs besteht aus eigenen finalen Items an
zwei getrennten Andockpunkten: nach jeder Vignettensitzung oder am Ende. Eine
Fassung kann an beiden Stellen, je Stelle aber nur einmal vorkommen.
Vignetten und beide Andockpunkte sind je eine Liste; ihre Reihenfolge ist die
Reihenfolge der Erhebung, ein eigenes Positionsfeld gibt es nicht. Über jeder
Liste wählt man unter »Hinzufügen …« eine Fassung und die Stelle, an der sie
eingefügt wird (»am Ende«, »am Anfang« oder »nach …«). Jede Zeile trägt
Symbolknöpfe mit Beschriftung für Hilfstechnik: ↑ und ↓ verschieben um eine
Stelle, der Papierkorb entfernt; ein Item hat zusätzlich ⇄ zum Umhängen ans
Ende des anderen Andockpunkts, solange es dort nicht schon hängt. Umsortieren lässt sich auch
durch Ziehen am Griff, mit Maus wie mit Touch, aber nur innerhalb einer Liste;
ohne Maus reichen die Knöpfe und Auswahlfelder. Jede Änderung gilt sofort, beim
Entfernen und Umhängen schließt sich die Reihenfolge. Ist eine Fassung bereits
am anderen Andockpunkt gebunden, kennzeichnet die Auswahl dies, ohne ihre
Aufnahme zu verhindern. Der Schalter »Zufällige Reihenfolge« über der
Vignettenliste mischt die Vignetten je Teilnahme; dann zeigt die Liste keine
Nummern, keine Positionswahl und kein Verschieben. Das Umschalten ändert nur
die Regel: Die Reihenfolge der Liste bleibt gespeichert, beim Wechsel zurück zu
fest gilt wieder die zuvor festgelegte Reihenfolge, neu aufgenommene Vignetten
stehen am Ende.
Finale und archivierte Erhebungen zeigen Vignetten und Items weiterhin als
Listen, samt Reihenfolgeregel, ohne Auswahl und Änderungsaktionen; nach einem
Rückzug sind sie wieder bearbeitbar.
Trifft eine Änderung dennoch eine Erhebung, die kein Entwurf mehr ist, etwa
über eine veraltete Schaltfläche in einem zweiten Tab, bleibt alles, wie es
war: Die Seite führt zurück auf die Detailseite, beim Löschen auf die Liste,
und die Meldung »Die Erhebung ist kein Entwurf mehr. Es wurde nichts
geändert.« nennt den Grund. Weist die Erhebung eine Änderung aus einem anderen
Grund ab, steht dieser Grund ebenso als Meldung auf der Detailseite. Eine
fremde Erhebung bleibt dabei unauffindbar.
Sobald eine Stichprobe besteht, lässt sich an der Erhebung die Datenspur als
ZIP mit relationalen CSV-Dateien herunterladen, einschließlich der geplanten
Vignettenziehungen, der tatsächlich gelaufenen Sitzungen, Gesprächsschritte,
Fehlversuche und Diagnosen. Jeder Gesprächsschritt und jede Diagnose vermerken
dabei den Eingabemodus: ob der Text getippt, eingesprochen oder aus beidem
zusammengesetzt wurde. Der Wert wird im Browser der Teilnehmer:in bestimmt und
ist damit eine Angabe für die Auswertung, kein Nachweis. Jede Sitzungszeile
nennt die verbrauchte Zeit in Sekunden; bei einer Vignette mit
schrittbasiertem Budget bleibt sie bei null, der Wert ist also zusammen mit dem
Budget-Typ der Vignettenfassung zu lesen. Die verwendeten
Vignettenfassungen, Simulationskern-Fassungen und Modell-Konfigurationen liegen
mit ihrem vollständigen Inhalt als eigene Tabellen bei, damit der Export ohne
Datenbankzugriff interpretierbar bleibt. Für den Fragebogen-Teil gilt dasselbe:
Die tatsächlich vorgelegten Fassungen der Fragebogen-Items liegen mit ihrem
vollen Wortlaut bei; eine zugeordnete, aber nie vorgelegte Fassung erscheint
nicht. Eine eigene Tabelle nennt die Kodierung der Likert-Skala, deren Stufe von
1 »Stimme gar nicht zu« bis 6 »Stimme voll zu« mit der Zustimmung steigt, und
die vorgelegten Itemblöcke stehen mit ihrem Andockpunkt sowie den Zeitstempeln
der Vorlage und der Erledigung darin — ein übersprungener Block bleibt so als
vorgelegt erkennbar. Die Antworten selbst liegen als eigene Tabelle bei, eine
Zeile je vorgelegtem Fragebogen-Item, mit getrennten Spalten für Freitext und
Likert-Stufe. Eine vorgelegte, aber unbeantwortete Zeile bleibt mit leeren
Werten erhalten; nur so unterscheidet die Auswertung »freiwillig übersprungen«
von »nie gesehen«. Flüchtige Teilnahmen haben Itemblöcke, aber keine
Antwortzeilen.

## Fragebogen-Items verwalten

Forschende und Administrator:innen erreichen unter `/fragebogen-items/` die
private Item-Bibliothek. Dort legen sie Freitext- oder Likert-Items zunächst als
Entwurf an und finalisieren sie, sobald ihr Wortlaut feststeht. Finale Fassungen
sind unveränderlich und für Erhebungen einbindbar; eine neue Fassung erzeugt
stattdessen einen bearbeitbaren Folgeentwurf. Finale Fassungen lassen sich
archivieren und bei Bedarf wieder entarchivieren; Entwürfe lassen sich physisch
löschen. Lehnt das Item das Finalisieren oder Archivieren ab, etwa weil der
Wortlaut fehlt, erscheint der Grund als Meldung auf der Detailansicht. Die Bibliothek zeigt Items aus dem eigenen Eigentümer-Kreis;
Administrator:innen sehen alle Items. Eigentümer:innen lassen sich direkt an der
Item-Historie hinzufügen oder entfernen. Der Kreis bleibt dabei immer besetzt;
die eigene Entfernung übergibt die Historie an die verbleibenden Eigentümer:innen
und führt zurück in die Item-Bibliothek.
Likert-Items verwenden die sechs global festgelegten, nicht editierbaren
Skalenstufen von 1 = „Stimme gar nicht zu" bis 6 = „Stimme voll zu".

