# Verhalten der Plattform

Dieses Dokument beschreibt das sichtbare Verhalten der Plattform je Bereich so,
wie es heute umgesetzt ist. Es ist die Referenz für die Frage »Was tut die
Anwendung an dieser Stelle genau?« — für Begriffe siehe
[GLOSSARY.md](../GLOSSARY.md), für die Gründe hinter dem Verhalten
[docs/adr/](adr/). Wer das Verhalten ändert, ändert diesen Text mit.

## Start und Anmeldung

Die öffentliche Startseite unter `/` ist eine kurze Willkommensseite: Sie nennt
den Zweck der Plattform und stellt die Funktionen in drei Rollenspalten vor
(Autor:in, Lehrperson in Ausbildung, Ausbildung & Forschung). Sie verlinkt
selbst auf keinen geschützten Bereich; ohne Anmeldung führt sie zum Login unter
`/accounts/login/`. Nach der Anmeldung zeigt die Sidebar nur die Bereiche und
Links der jeweiligen Gruppenrollen; die Administration ist dabei ein Django-
Superuser, keine Group, und wird mit `manage.py createsuperuser` eingerichtet.
Über `/admin/` legt die Administration weitere Konten an, setzt deren
Passwörter, vergibt die drei fachlichen Rollen als Groups und kann weitere
Superuser ernennen. Konten lassen sich dort bewusst nicht löschen, solange #156
den Umgang mit Löschbegehren noch nicht festlegt.

Jede kontogebundene Seite leitet anonyme Anfragen, etwa nach abgelaufener
Session, auf den Login mit `next` um; erst ein angemeldetes Konto ohne passende
Rolle bekommt 403. Das gilt auch für alle Seiten der Administration unter
`/system/`. Endpunkte, die das Frontend per JavaScript aufruft, wie die
Transkription einer Trainingssitzung, antworten anonym mit 403 statt mit einem
Redirect. Die Teilnahme-Routen der Erhebungen hängen an einem Token, nicht an
einem Konto, und leiten nicht um.

Die Sidebar gliedert die Links in die Gruppen Entwicklung (gelb), Ausbildung
(grün), Forschung (violett) und System (blau). Die aktive Seite trägt die Fläche
und einen Balken links im Ton ihrer Gruppe, beim Überfahren erscheint die halbe
Tönung; die Schrift bleibt dunkel. Jede Seite trägt die Bereichsfarbe der
Gruppe, unter der sie in der Sidebar steht: Vignetten und der Simulationskern
samt Verwaltung gehören zu Entwicklung, Trainingskatalog, eigene Trainings,
Training anlegen und kuratieren zu Ausbildung.

Die Seitenköpfe folgen einem Vokabular. Die Überzeile nennt Sidebar-Gruppe und
Eintrag, etwa »Entwicklung / Vignetten«, »Entwicklung / Simulationskern«,
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
Modell-Konfiguration »Konfiguration anlegen«, auf der
Transkriptions-Konfiguration »Fassung anlegen«). Auf Bearbeiten-Seiten heißt er
»Änderungen speichern«.

Die gesamte Oberfläche ist deutschsprachig, auch Djangos eigene Texte:
Formularfehler (»Dieses Feld ist zwingend erforderlich.«), die Bedienelemente
bereits hochgeladener Bilder und die Datumsanzeige. Auswahlfelder ohne
Vorbelegung zeigen »Bitte wählen …«.

## Formulare

In den Formularen zum Anlegen und Bearbeiten (Vignetten, Trainings, Erhebungen,
Fragebogen-Items, Simulationskern, Modell- und Transkriptions-Konfiguration)
stehen die Aktionen wie »Abbrechen« und »Änderungen speichern« oben im Formular
und bleiben beim Scrollen sichtbar, solange das Formular im Bild ist. Die
Tab-Reihenfolge führt weiter erst durch die Felder. Auf den Seiten der Teilnahme
stehen die Aktionen weiterhin am Ende, etwa »Einwilligen« nach der Wahl zur
Audioverarbeitung. Aktionen außerhalb eines Formulars, etwa auf Detailseiten,
bleiben an ihrer Stelle.

## Listen

In »Meine Vignetten« und der Fragebogen-Item-Liste ist die ganze Zeile klickbar
und öffnet die Detailseite; eine Spalte »Aktion« mit einem Knopf »Öffnen« je
Zeile gibt es dort nicht mehr. Der Name in der ersten Spalte ist der einzige
Link der Zeile, fett in Textfarbe. Mit Tab erreicht man je Zeile genau diesen
Link, ein Mittelklick öffnet die Detailseite in einem neuen Tab. Beim Überfahren
und beim Tastaturfokus tönt sich die Zeile halb im Bereichston der Seite, am
Zeilenende erscheint in Grün »Öffnen ›«. Der Tastaturfokus zeichnet zusätzlich
den grünen Fokus-Ring um die Zeile. Die Trennlinien zwischen den Zeilen bleiben
dabei sichtbar. Suche, Filter und Sortierung bleiben unverändert.

Die Erhebungsliste hat dieselben klickbaren Zeilen. Entwürfe tragen am
Zeilenende zusätzlich einen Lösch-Knopf mit Mülleimer-Symbol, in Ruhe gedämpft,
beim Überfahren rot umrandet. Er ist ein eigenes Element mit der Beschriftung
»<Name> löschen«: Mit Tab erreicht man ihn nach dem Namen, ein Klick darauf
löscht den Entwurf sofort und öffnet nicht die Detailseite. Finale und
archivierte Erhebungen haben keinen Lösch-Knopf.

Genauso funktionieren die Trainingskataloge, »Meine Trainings« der
Ausbilder:innen, die Trainingshistorie und »Meine Abschriften«. Dort nennt der
Hinweis am Zeilenende die jeweilige Aktion statt »Öffnen ›«: in den
Trainingskatalogen je Zeile »Kuratieren ›« (Trainings, die man kuratieren darf)
oder »Öffnen ›«, in »Meine Trainings« »Kuratieren ›«, in der Historie »Ansehen
›« und in »Meine Abschriften« »Lesen ›«. Der Link führt jeweils zum bisherigen
Ziel. Tabellen mit echten Aktionen statt Navigation, etwa auf der
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
Entfernen ist ein roter Textlink. Die eigene Zeile trägt »(Sie)«, dort heißt die
Aktion »Mich entfernen«, und ein Satz erklärt, dass das Artefakt bei den übrigen
Eigentümer:innen bleibt. Bei nur einer Eigentümer:in steht statt einer Aktion
»Letzte Eigentümer:in«, darunter der Hinweis, zuerst jemanden hinzuzufügen. Das
Hinzufügen folgt nach einer Trennlinie unter eigener Unterüberschrift. Gibt es
niemanden mehr, steht dort ein Satz statt eines leeren Auswahlfelds.

Im Lernauftrag- und Arbeitsheft-Text legt der Positionsmarker `[bild]` fest, wo
das hochgeladene Bild steht und wo das Sprachmodell die Bildbeschreibung erhält.
Er zählt nur allein auf einer Zeile (Leerraum und Groß- und Kleinschreibung
egal); mitten in einer Zeile oder als `[bild](…)` bleibt er gewöhnlicher Text.
Der erste Marker gewinnt, weitere verschwinden. Ohne Marker steht das Bild unter
dem Text, ohne Bild verschwinden die Marker ersatzlos.

Lernauftrag- und Arbeitsheft-Text erscheinen als gerendertes Markdown im Profil
Szenentext: in der Sitzung von Training, Erhebung und Probelauf, in der
Abschrift und in der Vignetten-Detailansicht. Der Umfang gleicht dem der
Erhebungstexte (siehe „Erhebungsteilnahme"), nur ohne Links: Link-Syntax
erscheint wörtlich. Die Teile vor und nach dem Bild werden je für sich
gerendert. In der Sitzung stehen Überschriften über dem großen Fließtext der
Szene. Rechenschritte mit Einrückung lassen sich als eingerückter Block setzen,
auch gleich am Anfang des Textes: Beim Speichern fallen nur Leerzeilen und
Leerraum außen weg, die Einrückung der ersten Zeile bleibt. Schülernotation mit
`*`, `_`, führendem `-` oder `1.` escapen Autor:innen mit einem Backslash.
Bildbeschreibung und Simulationshinweise bleiben reiner Text. Prompt und
Datenspur-Export erhalten die unveränderte Markdown-Quelle. Im Vignettenformular
stehen unter beiden Feldern der Markdown-Hinweis ohne Link-Syntax, samt
Backslash- und Einrückungsregel, und derselbe Umschalter »Bearbeiten | Vorschau«
wie bei den Erhebungstexten; die Vorschau rendert den ungespeicherten Text im
Profil Szenentext so wie die Sitzung. Bei einem Text mit Positionsmarker zeigt
sie `[bild]` wörtlich.

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
Texten; beim Anlegen legt er sie an. »Abbrechen« verwirft nur die Änderungen an
diesem Text. Ein Text mit Fehler steht nach dem Speichern offen. Gibt es noch
keinen finalen Simulationskern, legt »Vignette anlegen« nichts an: Das Formular
nennt den Grund, die Eingaben bleiben stehen. Wer die Seite mit ungespeicherten
Änderungen verlässt, wird vom Browser gewarnt. Die Bildbeschreibung bleibt Teil
der Bildkarte.

Den Probelauf startet eine Autor:in über eine eigene Fassung im Zustand Entwurf
oder final, aus der Detailansicht oder von der Probelauf-Auswahl, die beide samt
Zustand listet. Eine archivierte Fassung ist nicht mehr spielbar; auch ein
direkter Start über sie scheitert. Administrator:innen wählen im freien
Probelauf Kern und Modell-Konfiguration beliebig, als Vignette nur eine finale.
Wird die Fassung während eines laufenden Probelaufs archiviert, läuft er bis zum
Debrief weiter.

Der laufende Probelauf samt Denkspur liegt nicht in der Session des Kontos,
sondern im kurzlebigen Speicher (`FLUECHTIG_PFAD`) außerhalb von Datenbank und
Backup. Ein eigenes Cookie, das nur unter `/sitzungen/probelauf/` gilt, ordnet
ihn dem Browser zu; jeder Browser hat so seinen eigenen Probelauf, auch beim
selben Konto. Er gilt nur für das Konto, das ihn gestartet hat: Meldet sich im
selben Browser ein anderes Konto an, gibt es für dieses keinen laufenden
Probelauf. Neuladen setzt an derselben Stelle fort, und jeder Aufruf einer
Probelaufseite verlängert die Frist; nach einem Tag ohne Zugriff ist er
verfallen. Das Abmelden löscht die Probeläufe des Kontos, in allen Browsern.
Gibt es keinen laufenden Probelauf, antworten Gespräch, Beenden und Debrief mit
404; ein neuer startet über die Detailansicht oder die Auswahl.

Eine archivierte Fassung bietet »Entarchivieren« nur an, solange ihre
Vorgängerin keine andere nicht archivierte Nachfolgerin hat; ein Versuch führt
sonst mit einer Meldung zurück auf ihre Detailansicht.

Probelauf-Auswahl und Probelauf-Start setzen die Rolle Autor:in voraus, wie der
Vignetteneditor; ohne sie antworten beide mit 403, auch einer Eigentümer:in, der
die Rolle entzogen wurde. Der Kreis der Vignette bleibt dabei unverändert; mit
der Rolle zurück ist der Probelauf wieder erreichbar (ADR-0037).

## Trainings verwalten

Ausbilder:innen sehen die Trainings ihres Eigentümer-Kreises;
Administrator:innen sehen alle. In der Kuratierungsansicht lässt sich eine
weitere Ausbilderin oder Administratorin als Eigentümer:in hinzufügen oder eine
vorhandene entfernen. Der Kreis bleibt auch bei veröffentlichten Trainings
besetzt; die eigene Entfernung übergibt das Training an die verbleibenden
Eigentümer:innen.

Die Vignetten eines Trainings stehen in einer empfohlenen Reihenfolge. Eine neu
aufgenommene Vignette steht am Ende; beim Entfernen rücken die übrigen lückenlos
nach. Auf der Kuratierseite verschieben »Hoch« und »Runter« eine Vignette um
eine Stelle, im Entwurf wie nach dem Veröffentlichen; die erste Vignette hat
keinen Hoch-, die letzte keinen Runter-Knopf. Verschieben darf, wer aufnehmen
und entfernen darf. Teilnehmende sehen die neue Reihenfolge sofort, ihre
bisherigen Sitzungen bleiben unberührt. Kuratierseite und Trainingsseite der
Teilnehmenden zeigen die Vignetten in dieser Reihenfolge und nummeriert (1., 2.,
…); auf der Trainingsseite laufen die Nummern über die angezeigten finalen
Vignetten. Die Reihenfolge ist nur ein Vorschlag: Jede Vignette bleibt frei und
beliebig oft startbar, der Spielstand je Vignette bleibt sichtbar.
Trainingssitzungen halten keine Vignettenposition fest, und der Trainingsexport
bleibt unverändert.

## Geschlossenes Training und Beitritt

Ein Training ist geschlossen (ADR-0049). Teilnehmende sehen im Trainingskatalog
nur Trainings, denen sie beigetreten sind; Trainingsseite, Vignettenwahl und
Sitzungsstart eines anderen Trainings antworten mit 404, auch über die direkte
Adresse. Kreis und Administration erreichen ihre Trainings wie bisher ohne
Beitritt. Wer schon vor dem Trainings-Link in einem Training gespielt hat, gilt
als beigetreten und behält Zugang und Sitzungen.

Jedes Training hat einen festen Trainings-Link. Die Kuratierseite zeigt ihn ganz
oben in einem Band „Gruppe beitreten lassen“ mit den Knöpfen „Kopieren“ und
„Sperren“ und nennt darunter die Zahl der Beigetretenen. Ist der Beitritt
gesperrt, färbt sich das Band rot, heißt „Beitritt gesperrt“, und „Wieder
öffnen“ hebt die Sperre auf. Jede Eigentümerin des Kreises darf sperren und
öffnen.

Wer den Link eingeloggt ohne Kreis- oder Administrationszugang öffnet, tritt bei
und landet auf der Trainingsseite; auch eine Ausbilderrolle allein begründet
keinen Kreiszugang. Erneutes Öffnen führt ohne zusätzlichen Beitritt direkt
dorthin. Ohne Anmeldung führt der Link über den Login zurück zum Beitritt. Bei
gesperrtem Beitritt sehen neue und ausgetretene Konten die Meldung „Beitritt
gesperrt“ (403) mit der Bitte, sich an die Ausbilder:in zu wenden; aktive
Trainingsteilnehmende kommen weiter ins Training. Der aktuelle Eigentümer-Kreis
und die Administration gelangen über offene wie gesperrte Trainings-Links direkt
zur Trainingsseite, ohne beizutreten: Auch wiederholte Aufrufe erzeugen weder
Trainingsbindung noch Teilnahme und erhöhen die Zahl der Beigetretenen nicht.
Der Kreiszugang setzt die Rolle Ausbilder:in voraus (ADR-0037): Einer
Eigentümer:in, der die Rolle entzogen wurde, öffnet der Kreis weder
Trainingsseite noch Vignettenwahl noch den Weg an der Beitrittssperre vorbei.
Sie gilt dann wie jedes andere Konto, erreicht das Training nur über eine eigene
aktive Trainingsbindung und tritt über den offenen Link bei. Mit der Rolle
zurück gilt wieder der Kreiszugang. Erst ein tatsächlicher Sitzungsstart legt
bei Bedarf die erforderliche Bindung und Teilnahme an. Bestehende Bindungen und
Sitzungen bleiben beim Linkaufruf unverändert erhalten. Der Link eines Entwurfs
bleibt für alle Konten unbekannt (404). Ein Training ohne Vignetten lässt sich
veröffentlichen und beitreten.

Die Trainingsseite trägt unter dem Titel den festen Hinweis „Die Ausbilder:innen
dieses Trainings sehen Ihre abgeschlossenen Sitzungen namentlich.“

## Trainingssitzung fortsetzen

Eine Trainingssitzung ist über ihre eigene Adresse erreichbar; der Browser merkt
sich keine aktuelle Sitzung. Gespräch, Gespräch beenden, Abbrechen, Debrief und
Spracheingabe tragen die Sitzung in der Adresse. Erreichbar ist sie nur für das
Konto, dessen Trainingsbindung sie gehört; jede andere Sitzungsadresse antwortet
mit 404. Beendete, abgebrochene und gescheiterte Sitzungen lassen sich über
diese Adressen nicht weiterspielen.

Auf der Trainingsseite trägt jede eigene laufende Sitzung neben „Sitzung #…
ansehen“ den Link „Fortsetzen“. Er führt mit dem bisherigen Gespräch zurück in
die Sitzung, auch in einem anderen Tab, einem anderen Browser oder auf einem
anderen Gerät.

Je Training läuft höchstens eine eigene Sitzung. Wer eine Vignette startet,
während noch eine Sitzung läuft, auch bei derselben Vignette und aus einem
anderen Tab oder Gerät, sieht statt eines neuen Gesprächs die Seite „Es läuft
noch eine Sitzung“. Sie nennt die laufende Vignette und ihren Beginn und bietet
an:

- **Fortsetzen**: zurück in die laufende Sitzung mit dem bisherigen Gespräch.
- **Abbrechen und neu starten**: Die laufende Sitzung wird abgebrochen, und die
  gewählte Vignette startet. Läuft inzwischen eine andere Sitzung als die
  genannte, wird nichts abgebrochen und die Seite nennt die aktuelle.

Die Abfrage zur Audioverarbeitung kommt wie bisher vor dieser Seite. In
verschiedenen Trainings darf gleichzeitig je eine Sitzung laufen. Liegen
gebliebene ältere laufende Sitzungen aus der Zeit vor dieser Regel stehen als
abgebrochen in der Liste; die jüngste ist fortsetzbar.

## Austritt aus dem Training

Am Ende der Trainingsseite steht für Trainingsteilnehmer:innen der Abschnitt
„Austritt aus dem Training“. „Aus dem Training austreten“ klappt eine Erklärung
auf: Der Kreis sieht die eigenen Sitzungen danach nicht mehr, Freigaben von
Abschriften für dieses Training ruhen, nichts wird gelöscht, und über den
Trainings-Link ist ein Wiederbeitritt möglich, solange der Beitritt offen ist.
Erst „Austritt bestätigen“ tritt aus (nur per POST, sonst 405) und führt mit der
Meldung „Sie sind aus dem Training … ausgetreten.“ zurück auf die
Trainingsseite. Ein zweiter Austritt ändert nichts und führt ebenso dorthin; ein
Austritt aus einem Training, dem das Konto nie beigetreten ist, bekommt 404.

Danach ist die Person keine Trainingsteilnehmer:in mehr:

- Der Trainingskatalog zeigt das Training nicht mehr. „Meine Trainings“ führt es
  weiter, mit dem Kennzeichen „ausgetreten“.
- Die Trainingsseite bleibt erreichbar, zeigt statt der Einleitung und des
  Hinweises zur Fremdeinsicht „Sie sind nicht mehr Teilnehmer:in dieses
  Trainings.“ und listet die eigenen Sitzungen in jedem Status, aber weder „Neu
  starten“ noch den Austritt. Eigene Sitzungen öffnen sich weiter lesend, auch
  laufende, ohne Denkspur.
- Vignettenwahl, Einwilligung und Sitzungsstart antworten mit 404; es entsteht
  keine Sitzung. Das gilt auch, wenn die Person zum Kreis gehört, bis sie über
  den Trainings-Link wieder beitritt.
- Eine beim Austritt laufende Sitzung bleibt laufend liegen. Gespräch, Beenden,
  Abbrechen, Debrief und Transkription antworten auch aus einem noch offenen Tab
  mit 404 und verändern nichts.

Für Kreis und Administration verschwindet die Person rückwirkend und spurlos aus
diesem Training: keine Zeile mehr in der Fremdeinsicht, kein Mitzählen in der
Zahl der Beigetretenen, keine Sitzungen in einem danach gezogenen
Trainingsexport, und jede ihrer Sitzungen dieses Trainings antwortet mit 404,
auch eine, die vorher lesbar war. Ein vorher gezogener Export bleibt, wo er ist.
Ihre für dieses Training freigegebenen Abschriften ruhen (siehe „Abschriften
holen“): Sie stehen nicht mehr unter „Freigegebene Abschriften“, ihre Sitzungen
antworten mit 404, und ein danach gezogener Export enthält sie nicht. In anderen
Trainings, denen die Person weiter angehört, bleibt sie für deren Kreise
einsehbar, auch mit dort wirksamen Freigaben derselben Abschrift. Der Zugang von
Kreis und Administration zum Training selbst ändert sich durch den Austritt von
Teilnehmenden nicht.

## Entfernen aus dem Training

Jede Zeile der Fremdeinsicht trägt in der letzten Spalte „Entfernen“. Das klappt
eine Bestätigung auf: Die Person kann über den offenen Trainings-Link wieder
beitreten; wer fernbleiben soll, wird über die Sperre des Beitritts
ferngehalten. Erst „Entfernen bestätigen“ entfernt (nur per POST, sonst 405) und
führt mit der Meldung „… ist aus dem Training entfernt.“ zurück auf die
Kuratierseite. Entfernen dürfen alle Eigentümer:innen des Trainings und die
Administration in jedem Training; fremde Ausbilder:innen bekommen 404, ebenso
ein Entfernen für ein Konto ohne aktive Bindung an dieses Training. Konten ohne
Rolle Ausbilder:in bekommen 403, Trainingsteilnehmende ebenso wie
Eigentümer:innen, denen die Rolle entzogen wurde. Es ändert sich dann nichts.

Entfernen führt in denselben Zustand wie ein eigener Austritt (siehe oben): Die
Person verschwindet für Kreis und Administration rückwirkend aus Fremdeinsicht,
Beigetretenen-Zahl und Trainingsexport, und sie selbst sieht genau das, was sie
nach einem eigenen Austritt sähe. Wer entfernt hat, wird nicht gespeichert und
nirgends angezeigt.

## Wiederbeitritt

Wer ausgetreten ist oder entfernt wurde, tritt über den offenen Trainings-Link
wieder bei. Dieselbe Trainingsbindung lebt wieder auf; es entsteht weder eine
zweite Bindung noch eine zweite Teilnahme. Das Training steht wieder im Katalog,
die Trainingsseite bietet wieder Wahl, Start und Austritt, und „Meine Trainings“
kennzeichnet es nicht mehr als ausgetreten. Die Person erscheint wieder in der
Fremdeinsicht und in der Zahl der Beigetretenen, ihre früheren Sitzungen sind
für Kreis und Administration wieder lesbar. Ruhende Freigaben wirken wieder,
ohne neu erteilt zu werden; widerrufene bleiben widerrufen. Eine beim Austritt
liegengebliebene laufende Sitzung lässt sich wieder fortsetzen.

Das gilt ebenso für Kreis und Administration mit ausgetretener Trainingsbindung:
Der Trainings-Link belebt auch ihre Bindung wieder.

Ist der Beitritt gesperrt, bekommt die Ausgetretene die Meldung „Beitritt
gesperrt“ (403) und bleibt ausgetreten. Kreis und Administration landen bei
gesperrtem Beitritt wie bisher auf der Trainingsseite, ihre Bindung bleibt aber
ausgetreten. Ein Sitzungsstart belebt die Bindung nicht; das geht nur über den
Trainings-Link.

## Fremdeinsicht im Training

Unter dem Band des Trainings-Links zeigt die Kuratierseite über die ganze Breite
die Fremdeinsicht (ADR-0049): eine Tabelle mit allen Beigetretenen, die nicht
aus dem Training ausgetreten sind, als Zeilen, nach Namen sortiert, und den
Vignetten des Trainings in empfohlener Reihenfolge als Spalten. Wer noch keine
abgeschlossene Sitzung hat, steht mit gedämpfter Schrift trotzdem in der
Tabelle. Jede abgeschlossene Sitzung erscheint in ihrer Zelle als runder Kreis
mit ihrer laufenden Nummer zu dieser Vignette; beim Zeigen oder Fokussieren
erscheint sofort ihr Datum. Eine leere Zelle trägt einen blassen Strich. Ein
Training ohne Vignetten zeigt statt der Tabelle einen Hinweis.

Ein Kreis öffnet die Sitzung lesend, so wie die Teilnehmer:in sie sieht: Szene,
Transkript, Ausgang, Debrief und Diagnose, nie die Denkspur. Einsehen dürfen
alle aktuellen Eigentümer:innen des Trainings mit der Rolle Ausbilder:in, auch
für Sitzungen von vor ihrer Aufnahme, und die Administration. Nach einem
Rollenentzug ist eine fremde Sitzung auch für eine Eigentümer:in unbekannt
(404); ihre eigenen Sitzungen bleiben lesbar. Laufende, abgebrochene und
gescheiterte fremde Sitzungen, Sitzungen derselben Person in einem fremden
Training, jede Sitzung einer aus dem Training Ausgetretenen und jede Sitzung für
aus dem Kreis ausgetretene Eigentümer:innen, fremde Konten oder die Autor:in der
Vignette antworten mit 404. Die eigenen Sitzungen bleiben für die Teilnehmer:in
in jedem Status lesbar, ebenfalls ohne Denkspur. Die lesende Ansicht zeigt die
Diagnose als Text, ohne Formular.

Unter der Tabelle folgt die Liste „Freigegebene Abschriften“ mit den Spalten
Teilnehmer:in, Erhebung, Geholt am und Sitzungen, nach Namen sortiert. Sie zeigt
jede Abschrift, die eine Beigetretene für dieses Training freigegeben hat,
solange sie dem Training noch angehört, beschriftet mit Erhebungsname und
Importzeitpunkt, und verlinkt ihre abgeschlossenen Sitzungen untereinander. Ohne
Freigaben steht dort „Niemand hat eine Abschrift freigegeben.“ Eine solche
Sitzung öffnet sich lesend wie eine Trainingssitzung, ohne Denkspur und samt der
gespielten Szene ihrer Vignette, auch wenn die Vignette dem Kreis nicht gehört
(dritte Ausnahme in ADR-0039). Im Vignettenbestand des Kreises erscheint sie
nicht, und aufnehmen lässt sie sich nicht. Eine nicht freigegebene Abschrift
erscheint in keiner Fremdeinsicht, auch nicht für die Administration; nach dem
Widerruf oder dem Löschen der Abschrift antwortet auch eine gemerkte Adresse mit
dem Status 404.

## Trainingsexport

In der Werkzeugleiste über der Tabelle steht rechts der Knopf „Trainingsexport
(ZIP)“, davor der gedämpfte Hinweis „pseudonym, nicht anonym“; sein Tooltip
sagt, dass die Teilnahmekennung statt Namen erscheint, gleich in jedem Export
dieses Trainings, und Freitext nicht geschwärzt wird. Der Download heißt
`training-<id>-<name>-<UTC-Zeitstempel>.zip` und enthält genau die Sitzungen der
Fremdeinsicht (ADR-0049): je Person einen Ordner mit der Teilnahmekennung ihrer
Trainingsbindung wie `teilnehmer-3f9a01c2`, darin eine Markdown-Datei je
abgeschlossener Sitzung (`01-brüche-addieren.md`) mit Vignettenname, Ausgang,
Datum, dem Transkript als Wechsel von Eingabe und Äußerung und der Diagnose.
Freigegebene Abschriften liegen als Unterordner mit dem Erhebungsnamen im Ordner
der Person; private und widerrufene fehlen, ebenso laufende, abgebrochene und
gescheiterte Sitzungen. Wer aus dem Training ausgetreten ist, hat in einem
danach gezogenen Export weder Ordner noch Dateien. Das Archiv enthält keine
Kontodaten, keine Denkspur, keine Fehlversuche, keine Modell-Konfiguration und
keinen Kern. Zwei Exporte desselben Trainings tragen für dieselbe Person
denselben Ordnernamen, auch nach Austritt und Wiederbeitritt, weil die Bindung
bleibt; in einem anderen Training trägt dieselbe Person eine andere Kennung. Die
Ordner stehen nach Kennung sortiert im Archiv, die Reihenfolge verrät also keine
Namen. Tragen zwei Personen zufällig dieselbe Kennung, bekommt die später
beigetretene eine Zählung (`teilnehmer-3f9a01c2-2`). Herunterladen dürfen der
Kreis und die Administration; fremde Ausbilder:innen bekommen 404, Konten ohne
Ausbilder:innen-Rolle 403. Der Trainingsexport ist keine Datenspur und
unterliegt nicht dem Exportkontrakt aus ADR-0029.

## Simulationskern

Autor:innen und Administrator:innen können die finale Kern-Fassung und die
Modell-Konfiguration der Schüler:in schreibgeschützt unter `/system/kern/`
einsehen. Ist noch kein finaler Kern vorhanden, stellt die Ansicht das nur fest.
Administrator:innen erhalten unter `/system/kern/verwalten/` (Sidebar:
Entwicklung) außerdem den Überblick über den Entwurf, die finale Fassung und die
eingeklappten archivierten Kern-Fassungen. Solange es überhaupt keine Fassung
gibt, legen sie die erste dort als Entwurf an — leer oder aus dem Standardkern.
Danach ziehen sie aus der finalen Fassung einen Entwurf, bearbeiten dessen
Vorlagen auf einer eigenen Seite, finalisieren ihn oder verwerfen ihn wieder.
Der Kern trägt zu jedem Zeitpunkt genau eine finale Fassung: Das Finalisieren
archiviert die bisherige. Archivierte Fassungen bleiben eingeklappt lesbar,
tragen aber keine Aktionen mehr; eine misslungene Fassung wird nicht
zurückgenommen, sondern durch eine neue ersetzt. Das Überholen trifft laufende
Sitzungen nicht, und Vignettenentwürfe auf der bisherigen Fassung bleiben
finalisierbar und spielbar. Ihre Detailansicht weist neben dem Vorspulen-Knopf
auf den überholten Pin hin; Vorspulen bleibt eine Wahl der Autor:in.

Die drei Abschnitte der Rahmenhandlung (Hospitationseinleitung,
Gesprächseinleitung, Debrief) sind Markdown im Profil Szenentext: derselbe
Umfang wie bei den Erhebungstexten, aber ohne Links, Link-Syntax bleibt
wörtlich. In jeder Sitzung (Training, Erhebung, Probelauf) erscheinen sie
gerendert. Die Werte der Vignette werden vor dem Einsetzen escaped, sodass nur
das Markdown des Kerns wirkt: `**$thema**` hebt das Thema hervor, ein Thema mit
`*` oder `_` erscheint dagegen wörtlich. Die Leseansichten der Kern-Fassungen
zeigen die Rahmenhandlung gerendert, die Platzhalter wörtlich als `$name`; ein
leerer Abschnitt zeigt »—«. Auf der Bearbeitungsseite des Entwurfs tragen die
drei Felder denselben Markdown-Hinweis und Umschalter »Bearbeiten | Vorschau«
wie das Vignettenformular; auch dort bleiben die Platzhalter in der Vorschau
wörtlich stehen.

Auf der Bearbeitungsseite stehen die drei Abschnitte der Rahmenhandlung und die
beiden Prompt-Vorlagen wie die großen Texte des Vignettenformulars zunächst
gekürzt zum Lesen, die Rahmenhandlung gerendert, die Prompt-Vorlagen als reiner
Text. »Bearbeiten« bzw. bei leerem Text »Text schreiben« öffnet nur diesen Text.
Jeder Speichern-Knopf, am Text wie »Kern-Entwurf speichern«, speichert den
ganzen Entwurf; »Abbrechen« verwirft nur die Änderungen an diesem Text. Ein Text
mit ungültigem Platzhalter steht nach dem Speichern offen. Wer die Seite mit
ungespeicherten Änderungen verlässt, wird vom Browser gewarnt.

Der Arbeitskontext steht in der System-Prompt-Vorlage; die User-Prompt-Vorlage
ist ein Altfeld (ADR-0052). Die Bearbeitungsseite zeigt sie nur, solange der
Entwurf oder die abgeschickten Daten sie füllen, auch nach einem
Validierungsfehler. So lässt sich der Arbeitskontext einer Altfassung in die
System-Prompt-Vorlage verschieben und das Feld leeren; danach erscheint es nicht
mehr. Ohne das Feld lässt das Speichern die Vorlage unberührt. Die Leseansichten
zeigen den Abschnitt je Fassung nur bei gefüllter Vorlage, auch bei archivierten
Fassungen.

Die Prompt-Vorlagen kennen nur die Platzhalter des Promptvertrags:
`$fehlermuster_beschreibung`, `$lernauftrag`, `$arbeitsheft`,
`$lernauftrag_simulationshinweise`, `$arbeitsheft_simulationshinweise`,
`$schuelerin_name`, `$schuelerin_geschlecht`, `$lehrperson_name`,
`$lehrperson_anrede`, `$fach`, `$thema` und `$klassenstufe`. Die Hinweise unter
den beiden Vorlagen nennen sie. `$lehrperson_anrede` ist »Frau« oder »Herr« nach
dem Geschlecht der Lehrperson, wie in der Rahmenhandlung. Geschlecht, Pronomen
und Possessiv der Lehrperson bleiben der Rahmenhandlung vorbehalten; eine
Prompt-Vorlage mit ihnen oder einem anderen Platzhalter speichert nicht und
zeigt »Enthält ungültige Platzhalter.«

Die simulierte Schüler:in erhält ihren Arbeitskontext im System-Prompt, in
Sitzung, Probelauf und Evalgespräch gleich: Der System-Prompt ist die gerenderte
System-Prompt-Vorlage. Ist die User-Prompt-Vorlage der Kern-Fassung gefüllt,
wird sie gerendert und mit einer Leerzeile angehängt; ist sie leer, hängt nichts
an. Danach wechseln sich die Ansprachen der Teilnehmer:in (`user`) und die
Antworten der Schüler:in (`assistant`) ab, die erste `user`-Nachricht ist die
erste Ansprache. Jede `user`-Nachricht stammt von der Teilnehmer:in (ADR-0052).
Jede `assistant`-Nachricht trägt die frühere Antwort vollständig als JSON-Objekt
nach dem Ausgabeschema, `{"denkspur": "…", "aeusserung": "…"}` (ADR-0064). Ein
Schritt ohne Antwort fehlt im Verlauf.

## Modell-Konfiguration

Administrator:innen setzen das Sprachmodell unter
`/system/modell-konfiguration/`. Jede Konfiguration trägt eine Bezeichnung, die
beim Anlegen Pflicht ist und danach wie alle Felder unveränderlich bleibt;
eindeutig muss sie nicht sein. Konfigurationen, die vor Einführung der
Bezeichnung angelegt wurden, heißen »<Sprachmodell> (Nr. <Nummer>)«. Der
Anbieter ist eine feste Auswahl — `fake`, `openrouter` oder `infomaniak` —, der
Modellname bleibt freier Text; Basis-URL und Token liegen an der Konfiguration
und nicht in der Umgebung. Die Parameter nehmen nur Mikro-Stellschrauben des
Modellverhaltens auf, bei `fake` ausschließlich das Skript und den Schalter
`skript_fortlesen` sowie die Zahl `verzoegerung`, die jeden Aufruf so viele
Sekunden warten lässt wie ein langsames Modell (nur als endliche Zahl ab 0; als
Text, `true`, negativ oder unendlich wartet er nicht). Die Wartezeit endet
spätestens an der übergebenen Anfragefrist. Erreicht die Verzögerung diese
Frist, zählt der Aufruf als Anbieterfehler und verbraucht seinen Skripteintrag;
weitere Versuche laufen ausschließlich über den bestehenden Mechanismus mit
gemeinsamer Frist. Ohne `skript_fortlesen` beginnt das Skript bei jedem
Antwortversuch von vorn, mit ihm — nur als `true`, nicht als Text — liest es
eine zusammenhängende Ausführung wie ein Evallauf über alle Aufrufe derselben
Konfiguration fort; jede neue Ausführung beginnt wieder vorn. Im Editor schlägt
neben dem Sprachmodell der Knopf „Modelle und Basis-URL laden“ die Modelle des
gewählten Anbieters vor: bei `openrouter` die mit Structured Output, bei
`infomaniak` die Sprachmodelle des Kontos. Die beiden unterscheiden sich darin,
was der Abruf verlangt: `openrouter` beantwortet seine Modellliste öffentlich,
ganz ohne Zugangsdaten, `infomaniak` erst gegen das im Formular eingetippte
Token — weder eine gespeicherte Fassung noch die Basis-URL sind dafür nötig. Bei
`fake` erscheint der Knopf nicht; dieser Anbieter telefoniert nicht nach außen.
Bei `infomaniak` füllt derselbe Druck zusätzlich die Basis-URL: Aus der
Produktabfrage des Kontos entsteht die Endpunktwurzel des Sprachmodells. Sie
entsteht nur bei genau einem AI-Produkt — ein geratenes wäre schlimmer als ein
leeres Feld — und überschreibt nie eine schon getippte Angabe. Die Liste wird
nur auf Druck geholt und bleibt ein Vorschlag — ein Name, den sie nicht kennt,
ist weiterhin eintragbar, und die eingesetzte Wurzel ist frei überschreibbar.
Über die Tauglichkeit sagt der Vorschlag nichts: Was die Liste führt, kann an
dieser Naht trotzdem scheitern, und was sie nicht führt, kann laufen. Die
prüfende Instanz bleibt der Probelauf — er entlarvt ein untaugliches Modell,
bevor es eine Erhebung erreicht. Aktiv ist je Verwendung (Schüler:in,
Lehrperson, Bewerter) höchstens eine Konfiguration; dieselbe darf mehreren
Verwendungen dienen, und eine einmal belegte Verwendung bleibt belegt.
Sitzungen, Probelauf, Training und der Pin der Erhebung lesen allein die
Verwendung Schüler:in; Lehrperson und Bewerter sind den Evals vorbehalten und
bleiben unbelegt, bis die Administration sie setzt. Die Seite zeigt alle je
angelegten Konfigurationen als schmale Tabelle, die neueste zuerst: Bezeichnung,
darunter das Sprachmodell, dazu Anbieter und Anlagedatum. Konfigurationen, die
vor Einführung des Anlagedatums entstanden, tragen dort den Zeitpunkt ihrer
frühesten Sitzung — da bestand sie nachweislich schon; nie gebrauchte zeigen
»—«, statt den Zeitpunkt der Umstellung als Datum auszugeben. Die Kürzel S, L
und B vor der Bezeichnung nennen die Verwendungen, für die eine Konfiguration
gerade aktiv ist. Neben der Tabelle steht das Detail der gewählten Zeile: Nr.,
Anlagezeitpunkt, Bezeichnung, Anbieter, Sprachmodell, Basis-URL, maskiertes
Token und Parameter. Ohne Wahl zeigt es die Konfiguration der Schüler:in,
solange keine aktiv ist die neueste. Im Detail steht je Verwendung ein Knopf,
etwa „Für Bewerter aktivieren (statt …)“ mit der Bezeichnung der bisher aktiven
Konfiguration; bei einer unbelegten Verwendung entfällt der „statt“-Teil. Ist
die gewählte Konfiguration für eine Verwendung schon aktiv, steht dort ein
deaktivierter Knopf „Aktiv für …“. Das Umschalten fragt nicht nach, bewegt nur
den Zeiger der genannten Verwendung und führt zurück auf dieselbe Konfiguration;
eine unbekannte Verwendung ergibt 404. Die Seite bietet genau vier Gesten:
Anlegen, Aktivieren sowie Abgeben und Widerrufen der Zero-Retention-Erklärung
(unten). Angelegt wird in einem getrennten Editor unter
`/system/modell-konfiguration/neu/`, erreichbar über „Neue Konfiguration“ im
Kopf der Liste. Die Bezeichnung steht dort zuerst. „Als Vorlage für eine neue
Konfiguration“ im Detail öffnet den Editor mit Anbieter, Basis-URL, Sprachmodell
und Parametern der gewählten Zeile und der Bezeichnung mit dem Zusatz „(Kopie)“;
eine unbekannte Vorlage ergibt 404. Das Token übernimmt die Vorlage nie, es wird
jedes Mal neu eingegeben. Die Vorlage bleibt unverändert, angelegt wird immer
eine neue Zeile. Der Editor prüft die Anbieterbindung wie zuvor am Feld und
aktiviert nichts: Nach dem Anlegen führt er mit einer Meldung zurück zur Liste,
die neue Konfiguration im Detail, und alle Verwendungen bleiben, wie sie waren.
Bearbeiten und Löschen gibt es nicht — eine Konfiguration ist unveränderlich,
weil jede Erhebung ihre Fassung pinnt. Ein Umschalten der Schüler:in trifft
laufende Trainings sofort und laufende Erhebungen gar nicht; eine
Schlüsselrotation ist deshalb kein Feldupdate, sondern Anlegen plus Aktivieren
für jede Verwendung der alten Fassung. Das Token wird eingegeben, aber nie
zurückgegeben: Das Detail zeigt es nur maskiert mit seinen letzten vier Zeichen,
kurze Werte ausschließlich als Punkte. Im freien Probelauf der Administration
steht jede Konfiguration zur Auswahl als »Bezeichnung (Sprachmodell)«.

An einer Konfiguration gibt eine Administrator:in die
**Zero-Retention-Erklärung** ab: dass für dieses Modell bei diesem Anbieter eine
Zusage vorliegt, dass Eingaben weder gespeichert noch zum Training genutzt
werden. Im Editor steht sie als dritter Abschnitt: ein Häkchen
„Zero-Retention-Erklärung abgeben“ und der Beleg der Zusage als Freitext, etwa
„AVV mit Infomaniak vom …“. Erst das Häkchen erklärt; ein Beleg ohne Häkchen
ergibt einen Fehler am Häkchen, ein Häkchen ohne Beleg einen am Belegfeld. Eine
Konfiguration ohne Erklärung bekommt sie nachträglich im Detail der Liste, über
dasselbe Belegfeld und „Zero-Retention-Erklärung abgeben“; auch dort ist der
Beleg Pflicht. Zeitpunkt und erklärendes Konto werden mitgeschrieben. Danach ist
die Erklärung unveränderlich wie der Rest der Konfiguration: Das Detail zeigt
Beleg, Zeitpunkt und Konto, aber kein Formular mehr, und ein zweiter Versuch
wird mit einer Meldung abgewiesen. Beim Anbieter `fake` ist keine Erklärung
zulässig, weder im Editor noch nachträglich. Für die Verwendung **Schüler:in**
lässt sich nur eine erklärte Konfiguration oder eine mit Anbieter `fake`
aktivieren; die Regel gilt in der Domäne, nicht nur auf der Seite. Fehlt die
Erklärung, steht im Detail statt des Knopfs ein deaktivierter „Für Schüler:in
erst nach der Erklärung“ samt Grund; wer die Aktivierung dennoch aufruft, liest
den Grund als Meldung, und der Zeiger bleibt, wo er war. Lehrperson und Bewerter
bleiben ohne Erklärung aktivierbar, denn Evals verarbeiten nur simulierte
Gespräche. Fällt die Zusage weg, etwa weil der Anbieter sie zurückzieht oder das
Modell keinen ZDR-Endpunkt mehr hat, widerruft eine Administrator:in die
Erklärung im Detail der Liste: Unter „Grund des Widerrufs“ steht ein Freitext,
der Pflicht ist; ohne ihn gibt es einen Fehler am Feld. Zeitpunkt und
widerrufendes Konto werden mitgeschrieben. Den Widerruf bietet das Detail nur an
einer Konfiguration mit gültiger Erklärung an; eine nie abgegebene oder schon
widerrufene Erklärung lässt sich nicht widerrufen, ein Aufruf ohne Formular wird
mit einer Meldung abgewiesen. Der Widerruf ist endgültig: Er lässt sich nicht
zurücknehmen, und an derselben Konfiguration lässt sich keine neue Erklärung
abgeben — wer die Zusage zurückhat, legt eine neue Konfiguration an. Beleg und
Zeitpunkt der Erklärung bleiben stehen, das Detail zeigt darunter Grund,
Zeitpunkt und Konto des Widerrufs. Eine widerrufene Konfiguration gilt als nicht
erklärt und lässt sich für **keine** Verwendung mehr aktivieren, auch nicht für
Lehrperson und Bewerter: Statt der Knöpfe stehen deaktivierte „Für … gesperrt:
Erklärung widerrufen“, und wer die Aktivierung dennoch aufruft, liest den Grund
als Meldung. Ist sie gerade aktiv, bleibt der Zeiger bestehen, und über der
Seite steht ein deutlicher Hinweis mit den betroffenen Verwendungen. Erhebungen,
die sie schon gepinnt haben, behalten sie. Die Tabelle zeigt je Zeile in der
Spalte „Zero Retention“ den Erklärungsstand: „erklärt“, „fehlt“, „widerrufen am
…“ samt Grund oder bei `fake` „nicht nötig“. Trägt die aktive Konfiguration der
Schüler:in keine Erklärung — etwa eine aus der Zeit vor der Erklärung —, bleibt
sie aktiv, Training und Probelauf laufen weiter, und über der Seite steht ein
deutlicher Hinweis, dass ihr die Erklärung fehlt und eine Erhebung sich erst
danach finalisieren lässt. Bei OpenRouter sichert der Provider-Filter Zero
Retention zusätzlich technisch ab; die Erklärung ersetzt ihn nicht.

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
seine Evalinputs. „Durchlauf und Vorlagen“ trägt *k*, die Zahl der
Wiederholungen je Evalinput (Startwert 3), die Lehrperson-Vorlage und die
Bewerter-Vorlage. Unter jeder Vorlage stehen ihre erlaubten Platzhalter als
Knöpfe: in der Lehrperson-Vorlage die des Promptvertrags sowie
`$inputstrategie`, in der Bewerter-Vorlage die des Promptvertrags sowie
`$kriterium` und `$verlauf`. Hervorgehoben und vorn stehen die Platzhalter, die
nur diese Vorlage kennt. Ein Klick fügt ihn an der Schreibmarke ein. Geprüft
werden die Vorlagen erst beim Finalisieren. „Änderungen speichern“ übernimmt die
Werte und bleibt im Editor, „Abbrechen“ führt ohne Speichern zurück zur
Übersicht. Die Aktionszeile klebt wie bei den übrigen Formularen oben. Wer den
Editor mit ungespeicherten Änderungen verlässt, wird vom Browser gewarnt.

An den Knoten „Übergreifende Kriterien“, Eval und Evalinput wird beim Speichern
nichts teilweise gespeichert: Scheitert ein Teil, bleiben alle Eingaben
ungespeichert. Nach dem Speichern folgt die Weiterleitung auf denselben Knoten.

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
erscheint im Baum als „Unbenanntes Eval“. Neben dem Namen rücken Hoch und Runter
das Eval um eine Stelle im Katalog (an erster bzw. letzter Stelle gesperrt), der
Papierkorb löscht es samt Evalkriterien und Evalinputs und führt zurück zu
„Durchlauf und Vorlagen“. Darunter pflegt sie die Evalkriterien des Evals, nach
denen der Bewerter jedes Evalgespräch dieses Evals beurteilt: anlegen,
bearbeiten, löschen und umordnen genau wie die übergreifenden Kriterien,
ebenfalls reiner Text ohne Platzhalter. Jede Geste im Editor, auch „Eval
hinzufügen“ aus einem anderen Knoten heraus, übernimmt zugleich alle getippten
Werte des Formulars; gültige Werte von „Durchlauf und Vorlagen“ eingeschlossen.
Ein ungültiger Wert dort, etwa ein negatives *k*, bleibt ungespeichert; der
Editor nennt ihn, und „Änderungen speichern“ meldet dann keinen Erfolg. Ein
neuer Entwurf aus einer finalen Fassung übernimmt die Evals samt Evalkriterien
in gleicher Reihenfolge. Leere Kriterien weist erst das Finalisieren zurück.
Alle schreibenden Routen der Evals und Evalkriterien erreichen nur Entwürfe.

Am Eval-Knoten legt „Evalinput hinzufügen“ einen weiteren Evalinput an; ein Eval
darf mehrere haben. Ein neuer Evalinput startet mit drei leeren, festen
Inputschritten und öffnet seinen Knoten. Im Baum hängt jeder Evalinput unter
seinem Eval („Evalinput 1“, „Evalinput 2“ …), daneben die Folge seiner Schritte
als Kürzel, F für fest und G für gelenkt (etwa „FGF“). Der Knoten zeigt den
Evalinput als Drehbuch: Die Inputschritte stehen untereinander, nach jedem steht
„Schüler:in antwortet“. Ein Segmentknopf je Schritt wählt zwischen „sagt
wörtlich“ (fest: der Text ist die Inputäußerung) und „formuliert nach Strategie“
(gelenkt: der Text ist die Inputstrategie, auch bedingt formuliert). Gelenkte
Schritte erscheinen als gestrichelte, kursive Blase. Inputschritte sind reiner
Text ohne Platzhalter. „Inputschritt hinzufügen“ hängt einen leeren, festen
Schritt ans Ende; je Schritt rücken Hoch und Runter ihn um eine Stelle (am Rand
gesperrt), der Papierkorb entfernt ihn. Reihenfolge, Art und Text bleiben
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
geändert wurde. Ein vollständiger Entwurf wird final, und die Administrator:in
landet auf der Übersicht, die zeigt, seit wann die finale Fassung gilt. Ab dann
prüft jeder Evallauf gegen sie. Die bisherige finale Fassung ist im selben
Schritt überholt; überholt ist nicht umkehrbar, es gibt immer genau eine finale
Fassung. Andere Apps fragen sie über `Evalkatalog.objects.finale_fassung()` ab,
das ohne finale Fassung `None` liefert.

Finale und überholte Fassungen lassen sich vollständig lesen, damit
nachvollziehbar bleibt, wogegen ein älterer Evallauf geprüft hat. Die Übersicht
führt mit „Finale Fassung lesen“ zur finalen Fassung und listet unter „Überholte
Fassungen“ jede überholte, die zuletzt gültige zuerst, mit dem Datum, ab dem sie
galt. Beide öffnen sich im Editor über dieselben Adressen wie ein Entwurf, mit
Baum und allen Knoten. Ein Hinweisband nennt den Zustand („final seit …“ bzw.
„überholt“, mit dem Datum, ab dem sie galt). Alle Felder sind gesperrt;
Platzhalterknöpfe, Hinzufügen, Hoch, Runter, Löschen, Speichern und Finalisieren
fehlen, die Aktionszeile führt nur zurück zur Übersicht. Jede schreibende
Anfrage an eine finale oder überholte Fassung wird abgewiesen.

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

## Evalläufe

Evals gibt es nur, wenn ein finaler Evalkatalog existiert und alle drei
Verwendungen (Schüler:in, Lehrperson, Bewerter) belegt sind. Sonst fehlen
Verlinkung, Ansicht und Start ganz, ohne erklärenden Hinweis; beide Routen
ergeben 404.

Die Detailansicht einer Vignette nennt dann den Zustand ihres Evallaufs („noch
keiner“, „Wartet“, „Läuft“, „Fertig“, „Abgebrochen“, dazu gegebenenfalls
„veraltet“) und verlinkt mit „Evals ansehen“ die Ansicht unter
`/evals/vignette/<Fassung>/`. Sie steht Mitgliedern des Eigentümer-Kreises und
der Administration offen; fremde Fassungen ergeben 404, Konten ohne
Autor:innen-Rolle 403. Vignettentitel und Fassung im Seitenkopf geben den
Kontext. Ohne Lauf und solange ein Lauf wartet oder läuft, stehen Zustand und
Aktion oben: „Evallauf starten“ (POST) gibt es an Entwürfen und finalen
Fassungen, solange kein Lauf wartet oder läuft; archivierte Fassungen sind nicht
startbar. Während ein Lauf wartet oder läuft, steht statt des Knopfs der
Hinweis, dass die Seite geschlossen werden darf, und „Stand neu laden“, das die
gewählte Auswahl behält; aktualisiert wird nur durch Neuladen, ohne
automatisches Polling. Ein fertiger oder abgebrochener Lauf steht dagegen als
dezente Fußzeile unter den Ergebnissen: Zustand samt Gesamtergebnis, „Erneut
prüfen“ als sekundäre Aktion und eingeklappt die „Angaben zum Lauf“ (Auslöse-,
Start- und Endzeitpunkt, *k*, Simulationskern, Katalogfassung und die drei
Konfigurationen). Eine abgewiesene Startprüfung führt mit Meldung zurück auf die
Ansicht und lässt den bisherigen Lauf unberührt.

Je Fassung gibt es höchstens einen Evallauf. Ein neuer Start ersetzt einen
fertigen oder abgebrochenen Vorgänger samt seinen Gesprächen im selben Zug; ein
wartender oder laufender wird auch bei gleichzeitigen Starts weder verdoppelt
noch ersetzt. Der Start hält den gepinnten Kern, die finale Katalogfassung, die
drei aktiven Konfigurationen und die Prompt-Werte der Fassung fest: Wird der
Entwurf danach gespeichert oder vorgespult, spielt der Lauf trotzdem den Stand
beim Start. Die Referenzdiagnose gehört nicht zu diesen Werten und erreicht
keinen Modellaufruf. Finalisieren behält den Lauf an derselben Fassung; das
Löschen eines Entwurfs entfernt ihn.

Ein Lauf ist *veraltet*, sobald sich seit seinem Auslösen etwas geändert hat,
das ihn bestimmte: Der Entwurf wurde gespeichert (jedes Speichern zählt, auch
ohne inhaltliche Änderung, und auch das Vorspulen), der gepinnte Kern ist ein
anderer, eine der drei Verwendungen zeigt auf eine andere Konfiguration, oder
eine andere Katalogfassung ist final. Verglichen wird mit dem Stand beim
Auslösen, nicht mit dem Arbeitsbeginn des Hintergrundprozesses; eine Änderung,
während der Lauf wartet oder läuft, macht ihn also ebenso veraltet. Eine neue
finale Kern-Fassung allein ändert nichts, solange die Fassung nicht vorspult;
Finalisieren ändert ebenfalls nichts. Die Ansicht ergänzt jeden Zustand um
„Veraltet“, nennt darunter die Gründe („Seit dem Start: Vignette bearbeitet,
Konfiguration Bewerter gewechselt.“) und den Auslösezeitpunkt; die „Angaben zum
Lauf“ nennen zusätzlich den geprüften Stand der Vignette. Die Ergebnisse bleiben
lesbar; ein neuer Lauf prüft den aktuellen Stand.

An einem Entwurf steht unmittelbar bei „Finalisieren“ ein Hinweis auf den
Evallauf: „Vor dem Finalisieren: Noch kein Evallauf.“ oder Zustand samt
Gesamtergebnis (nur fertig: „Bestanden“/„Nicht bestanden“), „Veraltet“ mit
Gründen und „Unvollständig“; darunter je Eval und Evalinput die Quote jedes
Kriteriums samt „ohne Urteil“ und „noch nicht ausgeführt“. Der Hinweis sperrt
nichts: Finalisieren ist in jedem Zustand des Laufs möglich, allein die
Vollständigkeitsregeln der Vignette gelten. Ohne verfügbare Evals fehlt er ganz.

Ausgeführt wird ein Lauf vom Hintergrundprozess
`python manage.py evallaeufe_abarbeiten`, der im Betrieb als eigener
supervisord-Dienst neben gunicorn läuft (`docs/DEPLOYMENT.md`). Er arbeitet die
wartenden Läufe nacheinander ab, den ältesten zuerst, setzt jeden auf „Läuft“
und am Ende auf „Fertig“, jeweils mit Zeitpunkt; ein Fehler mitten im Lauf
hinterlässt ihn „Abgebrochen“, das bis dahin Geschriebene bleibt. Wartet kein
Lauf, sieht er nach `--intervall` Sekunden (Standard 10) wieder nach; ein
Intervall, das keine positive Zahl ist, weist der Command ab. Ein Stopp (SIGTERM
wie von supervisord, oder Strg+C) bricht einen laufenden Lauf sofort ab,
schließt ihn als „Abgebrochen“ ab und beendet den Prozess. Mit `--einmal`
arbeitet er höchstens den ältesten wartenden Lauf ab und endet, für Tests und
Fehlersuche. Start, Ende, jeder Lauf und aufgeräumte verwaiste Läufe stehen im
Log auf stderr. Instanzweit arbeitet nur ein Hintergrundprozess: Er hält dafür
eine Sperrdatei (`EVALLAEUFE_SPERRE`, standardmäßig `evallaeufe.lock` im
Projektverzeichnis), die das Betriebssystem freigibt, wenn der Prozess endet
oder stirbt. Findet ein zweiter Aufruf sie gesperrt, meldet er das und rührt
nichts an, auch keinen laufenden Lauf. Wer die Sperre erhält, setzt zuerst jeden
Lauf, der noch „Läuft“ sagt, auf „Abgebrochen“ (Endzeitpunkt ist die
Bereinigung); wartende bleiben wartend. Abgebrochene Läufe werden weder
fortgesetzt noch um Wiederholungen ergänzt; ein neuer Start beginnt von vorn.
Wartezeit auf ein Modell belegt keinen Web-Thread, und weil kein Modellaufruf
eine Schreibtransaktion hält, schreiben Sitzungen währenddessen ungehindert. Für
jedes Eval, jeden Evalinput und jede Wiederholung 1 bis *k* entsteht ein
Evalgespräch, für jeden Inputschritt ein Wechsel in der Reihenfolge des
Evalinputs; feste und gelenkte Schritte dürfen sich mischen. Bei einem festen
Schritt ist die Inputäußerung wörtlich die Äußerung der Lehrperson. Bei einem
gelenkten formuliert die simulierte Lehrperson sie mit der festgehaltenen
Lehrpersonen-Konfiguration: Ihr System-Prompt ist die gerenderte
Lehrperson-Vorlage des festgehaltenen Katalogs mit `$inputstrategie` (Text des
Schritts); die Inputstrategie steht nur dort, nie als Nachricht. Das Gespräch
führt die Lehrperson nativ, spiegelbildlich zur Schüler:in: Ihr Verlauf beginnt
mit der festen Einstiegsnachricht „Beginnen Sie das Gespräch.“ als `user`,
danach stehen ihre eigenen Äußerungen, auch die wörtlichen fester Schritte, als
`assistant` und die Äußerungen der Schüler:in ohne Denkspur als `user`. Die
letzte Nachricht ist die jüngste Äußerung der Schüler:in, im ersten Zug die
Einstiegsnachricht. Eine Lehrperson-Vorlage mit `$verlauf` wird beim
Finalisieren abgelehnt; in einer schon finalisierten Altvorlage bleibt
`$verlauf` leer. Die Schüler:in antwortet in beiden Fällen über denselben
Antwortversuch wie in der Sitzung, mit derselben Nachrichtenordnung und ohne
Denkspur im Kontext. Danach beurteilt der Bewerter das Gespräch nach jedem
Evalkriterium des Evals und jedem übergreifenden Kriterium. Sein System-Prompt
ist die gerenderte Bewerter-Vorlage mit `$kriterium` und `$verlauf` (Verlauf
samt Denkspur); den Verlauf erhält er nur dort. Seine einzige `user`-Nachricht
ist der Kriteriumstext. Inputstrategie und Kriterium werden als reiner Text
eingesetzt und nicht selbst als Vorlage ausgewertet; Anweisungen stehen allein
in den Vorlagen des Katalogs. Jedes Gespräch, jeder Wechsel und jedes Urteil
wird sofort geschrieben; kein Modellaufruf hält eine Schreibtransaktion offen.

Scheitert der Antwortversuch der Schüler:in endgültig, endet das Gespräch mit
einem Wechsel ohne Antwort samt Fehlversuchen, und jedes seiner Kriterien ist
*nicht erfüllt* mit der Begründung „Antwortversuch gescheitert“. Liefert der
Bewerter nach allen Versuchen nichts Auswertbares, bleibt dieses Kriterium *ohne
Urteil*. Liefert die Lehrperson nach allen Versuchen keine Äußerung, endet das
Gespräch vor diesem Schritt, und alle seine Kriterien bleiben *ohne Urteil*.
Fehlversuche von Lehrperson und Bewerter bleiben mit Grund und Rohantwort
gespeichert, auch wenn eine Wiederholung danach eine gültige Ausgabe liefert.
Lehrpersonenfehler werden sofort nach dem Versuch festgehalten, Bewerterfehler
zusammen mit dem Urteil. Ein Prozessabbruch erhält diese Details. Erfolgreiche
Wiederholungen bleiben erfolgreich; ihre Fehlversuche ändern weder Quote noch
Bestehen.

Sobald ein Lauf nicht mehr wartet, zeigt die Ansicht zwei Spalten. Links stehen
je Eval seine Evalinputs (mit der Folge ihrer Schritte, etwa „FFG“) und darunter
je Kriterium, die übergreifenden eingeschlossen, Quote und Bestehen zusammen,
etwa „2 von 3 · nicht bestanden“; bestanden ist ein Kriterium nur, wenn alle *k*
Urteile erfüllt sind. Dahinter stehen getrennt gezählt Kriterien ohne Urteil („1
ohne Urteil“) und Wiederholungen, die noch nicht oder wegen eines Abbruchs nie
ausgeführt wurden („1 noch nicht ausgeführt“). Ohne Urteil zählt weder als
erfüllt noch als nicht erfüllt. Jeder Evalinput ist ein Link; der gewählte ist
markiert. Rechts steht das Evalgespräch des gewählten Evalinputs (`?input=`) in
der gewählten Wiederholung (`?wiederholung=`, Auswahlfeld mit „Anzeigen“): die
Äußerungen von Lehrperson (mit Schritt und Art) und Schüler:in in ihrer
Reihenfolge, je Antwort die Denkspur, Fehlversuche mit Grund und Rohantwort, ein
endgültig gescheiterter Antwortversuch als solcher, danach jedes Kriterium mit
seinem Urteil („erfüllt“, „nicht erfüllt“, „ohne Urteil“, „noch nicht
beurteilt“) und seiner Begründung. So lässt sich jedes Bewerterurteil fachlich
nachprüfen und, wenn nötig, manuell korrigieren (siehe unten). Bei allen drei
Rollen öffnet „Fehlversuche · N“ die technischen Details, zunächst eingeklappt:
bei der Lehrpersonenäußerung, der Schüler:innen-Antwort oder dem Bewerterurteil.
Die Übersicht erhält keine zusätzlichen Fehlermarken. Scheitert die Lehrperson
endgültig, steht im Verlauf etwa „Lehrperson konnte Schritt 1 nicht
formulieren.“ mit ihren Fehlversuchen; frühere Schritte bleiben sichtbar, eine
Schüler:innen-Antwort wird dafür nicht angezeigt. Solange nach einem
erfolgreichen Lehrpersonenversuch noch kein vollständiger Wechsel gespeichert
ist, zeigt die Ansicht diesen Teilstand ausdrücklich als solchen. Ohne Auswahl
zeigt die Ansicht den ersten Evalinput und seine erste ausgeführte Wiederholung.
Eine Wiederholung ohne Gespräch heißt „nicht ausgeführt“. Unlesbare Werte, ein
Evalinput außerhalb des festgehaltenen Katalogs oder eine Wiederholung außerhalb
1 bis *k* weichen dieser Vorgabe; gesucht wird stets nur unter den Gesprächen
des aktuellen Laufs der Fassung, sodass eine alte Adresse nach „Erneut prüfen“
den aktuellen Stand zeigt. Auf schmalem Hauptbereich stehen die Spalten
untereinander. Blieb mindestens ein Kriterium ohne Urteil, heißt der Lauf
*unvollständig*, und die Ansicht empfiehlt einen neuen Lauf. Ein Gesamtergebnis
nennt nur ein fertiger Lauf („Fertig · Bestanden“ oder „Fertig · Nicht
bestanden“), bestanden nur, wenn jedes Kriterium jedes Evalinputs besteht; ein
wartender, laufender oder abgebrochener Teilstand nennt nur seinen Zustand, auch
wenn jedes bisher geschriebene Urteil erfüllt ist. Ein abgebrochener Lauf zeigt
seine fertigen Gespräche und Urteile weiter, mit dem Hinweis, dass ein neuer
Lauf von vorn beginnt. Evalläufe erzeugen weder Teilnahme noch Sitzung und
erscheinen weder in der Datenspur noch im Trainingsexport.

Ein fachlich falsches Bewerterurteil lässt sich im gewählten Gespräch manuell
korrigieren, von Mitgliedern des Eigentümer-Kreises und der Administration,
sobald der Lauf fertig oder abgebrochen ist. Unter dem Urteil öffnet „Urteil
korrigieren“ ein Formular mit einer Pflicht-Begründung; „Als erfüllt werten“
bzw. „Als nicht erfüllt werten“ kehrt das Bewerterurteil um. Das Urteil heißt
dann etwa „Muster gezeigt · erfüllt · manuell korrigiert“, darunter stehen
Korrektur samt Konto, Zeitpunkt und Begründung und das ursprüngliche
Bewerterurteil mit seiner Begründung; überschrieben wird es nie. „Korrektur
ändern“ ersetzt Begründung, Konto und Zeitpunkt ohne Historie früherer
Fassungen, „Korrektur zurücknehmen“ lässt wieder das Bewerterurteil gelten. Das
wirksame Urteil bestimmt überall Quote und Bestehen: in den Quoten links, im
Gesamtergebnis und im Hinweis beim Finalisieren; aus „2 von 3 · nicht bestanden“
wird so „3 von 3 · bestanden“ und mit der Rücknahme wieder umgekehrt. Manuelle
Korrekturen sind auch an den Quoten, im Laufstand und im Finalisierungs-Hinweis
als „manuell korrigiert“ gekennzeichnet. Nicht korrigierbar sind Kriterien ohne
Urteil, nicht ausgeführte Wiederholungen und die automatisch nicht erfüllten
Urteile eines endgültig gescheiterten Antwortversuchs; ein wartender oder
laufender Lauf ist schreibgeschützt. Archivierte Fassungen bleiben lesbar,
erlauben aber weder neue Korrekturen noch Änderungen oder Rücknahmen bestehender
Korrekturen. Ein abgebrochener Lauf bleibt auch mit korrigierten Urteilen
abgebrochen und nennt kein Gesamtergebnis. Korrigieren und Zurücknehmen laufen
per POST mit CSRF-Schutz und prüfen Fassung, Laufzustand und Zuordnung des
Urteils frisch; ein Urteil, das nicht zum aktuellen Lauf der Fassung gehört
(etwa aus einem alten Browserstand nach „Erneut prüfen“), wird mit Meldung
abgewiesen. Eine Korrektur ändert weder die Fassung noch „veraltet“. Ein neuer
Lauf ersetzt den alten samt Korrekturen; auf neue Urteile wird nichts
übertragen.

## Transkriptions-Konfiguration

Die Transkription hängt an einer eigenen Konfiguration, die die Administration
unter `/system/transkription/` führt — mit denselben Anbieterfeldern wie das
Sprachmodell, aber unabhängig davon: Das Gespräch darf über den einen und das
Audio über den anderen Anbieter laufen. Sie ist wie die Modell-Konfiguration
append-only: Eine Fassung wird angelegt und aktiviert, nie bearbeitet. Die Seite
listet alle Fassungen mit Nummer, Anbieter, Transkriptionsmodell, Anlagedatum
und Stand; genau eine ist »aktiv«. Wer eine Zeile wählt, sieht rechts Anbieter,
Modell, Sprache, Basis-URL und das maskierte Token und kann sie mit »Aktivieren«
zur aktiven machen. Eine frische Instanz hat eine Fassung mit Anbieter `fake`,
also keine Transkription. Die bei der Umstellung übernommene bisherige
Einzelzeile ist die erste Fassung, aktiv und mit unveränderten Werten, aber ohne
Anlagedatum.

Jede Sitzung in Training und Erhebung pinnt beim Start die aktive Fassung. Alle
ihre Aufnahmen gehen an diese Fassung; ein Umschalten wirkt erst ab der nächsten
Sitzung. Der Probelauf hat keine Sitzung und nimmt bei jeder Aufnahme die gerade
aktive Fassung. Sitzungen, die bei der Umstellung auf Fassungen liefen, sind auf
die damals aktive Fassung gepinnt. Ohne Pin bleiben Sitzungen, die schon vorher
endeten, und laufende, wenn es bei der Umstellung noch keine Fassung gab; diese
folgen weiter der aktiven.

Das Token einer Fassung lässt sich ohne neue Fassung ersetzen: »Token ersetzen«
im Detail einer Fassung mit echtem Anbieter tauscht es aus, Anbieter und
Basis-URL bleiben. Ein leeres Token weist die Seite ab („Ohne Token bedient der
Anbieter keinen Aufruf.“); bei `fake` gibt es nichts zu ersetzen.

Unter der Liste steht das Formular einer neuen Fassung, vorbelegt aus der
aktiven außer dem Token; »Fassung anlegen« legt sie an, ohne sie zu aktivieren.
Ein leer gelassenes Tokenfeld übernimmt das Token der aktiven Fassung, solange
Anbieter und Basis-URL gleich bleiben. Wechselt eines von beiden, wird das alte
Token nicht übernommen: Ein echter Anbieter meldet dann am Tokenfeld „Ohne Token
bedient der Anbieter keinen Aufruf.“, eine `fake`-Fassung entsteht ohne Token.
Neben dem Transkriptionsmodell steht derselbe Knopf „Modelle und Basis-URL
laden“ wie an der Sprachmodell-Naht: bei `openrouter` die Modelle mit
Transkriptions-Modalität — in der ungefilterten Modellliste erscheinen sie nicht
—, bei `infomaniak` das eine Modell vom Typ `stt` und dazu die Endpunktwurzel
der Transkription, die bei diesem Anbieter unter einer anderen API-Version liegt
als die des Sprachmodells. Der eingesetzte Wert trägt hier bei beiden Anbietern
kein Präfix: Diese Naht läuft nicht über LiteLLM, sondern reicht den Namen roh
an die Route des Anbieters durch. Abgefragt wird wie an der Sprachmodell-Naht:
`openrouter` ohne Zugangsdaten, `infomaniak` gegen das getippte Token — auch
dann, wenn schon eines hinterlegt ist.

Anlegen, Aktivieren und Token ersetzen sind der Administration vorbehalten.

Der Export einer Erhebung führt je Sitzung die Nummer ihrer gepinnten Fassung
(`transkriptions_konfiguration_id` in `sitzungen.csv`, `NA` für Sitzungen ohne
Pin) und in `transkriptionskonfigurationen.csv` die referenzierten Fassungen mit
Anbieter, Transkriptionsmodell, Sprache und Anlagedatum, ohne Token und
Basis-URL (ADR-0029).

Ob transkribiert wird, entscheidet die Zero-Retention-Erklärung an der Fassung:
Transkribiert wird nur mit einer Fassung, deren Anbieter nicht `fake` ist und
die eine nicht widerrufene Erklärung trägt. Erklärung und Widerruf folgen
denselben Regeln und Meldungen wie an der Modell-Konfiguration: Im Detail einer
Fassung ohne Erklärung steht »Zero-Retention-Erklärung abgeben« mit dem
Pflichtfeld »Beleg der Zusage«, Zeitpunkt und Konto werden mitgeschrieben, bei
`fake` ist keine Erklärung zulässig, und danach ist sie unveränderlich. Das
Formular einer neuen Fassung bietet die Erklärung ebenfalls an. Eine erklärte
Fassung lässt sich mit Grund widerrufen; eine widerrufene Fassung lässt sich
nicht mehr aktivieren („Die Zero-Retention-Erklärung dieser Fassung ist
widerrufen; sie lässt sich nicht mehr aktivieren.“). Die Liste zeigt je Fassung
den Erklärungsstand (»erklärt«, »fehlt«, »nicht nötig« bei `fake` oder
»widerrufen am …« samt Grund), das Detail Beleg, Zeitpunkt und Konto der
Erklärung und des Widerrufs.

Maßgeblich ist der Erklärungsstand zum Zeitpunkt jeder Anfrage: für eine Sitzung
der ihrer gepinnten Fassung, im Probelauf der der aktiven. Ein Widerruf schließt
das Tor also sofort, auch in laufenden Sitzungen; die nächste Aufnahme wird
abgewiesen, das Mikrofon schaltet ab („Die Transkription ist nicht verfügbar.
Nutzen Sie die Tastatureingabe.“), und es geht per Tastatur weiter. Ist das Tor
der aktiven Fassung zu, steht über der Seite „Die Spracheingabe ist aus.“, und
weder Erhebung noch Training bieten die Einwilligung in die Spracherkennung an.
Das Mikrofon zeigt jede Sitzungsseite nur bei offenem Tor derselben Fassung wie
am Endpunkt; nach einem Widerruf fehlt es ab der nächsten Seite. Nach der
Umstellung trägt die übernommene Fassung keine Erklärung: Bis eine
Administrator:in sie abgibt, ist die Spracheingabe aus.

Erklären und Widerrufen sind der Administration vorbehalten. Der Export führt in
`transkriptionskonfigurationen.csv` auch den Erklärungsstand jeder Fassung:
erklärt, Beleg, Zeitpunkt der Erklärung, Zeitpunkt und Grund des Widerrufs, ohne
Konten (ADR-0029).

## Audioverarbeitung im Training

Vor dem ersten Start eines Trainings entscheiden Teilnehmende einmalig, ob ihr
Audio zur Transkription an einen externen Auftragsverarbeiter übermittelt werden
darf. Das Audio wird danach nicht gespeichert. Bei Ablehnung bleibt das Training
uneingeschränkt über die Tastatur spielbar. Gefragt wird nur, wenn das
Transkriptions-Tor der aktiven Fassung offen ist (erklärt, nicht `fake`). Ist es
zu, startet die Sitzung direkt mit Tastatureingabe, und die Entscheidung bleibt
offen; nach dem Öffnen des Tors wird beim nächsten Start gefragt.

Nach Einwilligung und bei offenem Tor der gepinnten Fassung lässt sich jede
Frage im Diagnosegespräch per Tastatur oder über „Spracheingabe starten“
eingeben. Die Aufnahme wird bewusst beendet, direkt transkribiert und
anschließend automatisch als Gesprächsschritt abgeschickt; das Transkript wird
davor nicht bearbeitet. Im Debrief kann die Diagnose ebenfalls in mehreren
Aufnahmen ergänzt werden; erst „Training beenden“ schickt sie bewusst und
unwiderruflich ab. Bei einer leeren oder fehlgeschlagenen Transkription kann die
Aufnahme wiederholt werden.

In Gespräch und Debrief steht das Feld in voller Breite. Darunter liegt die
Eingabezeile: links der umrandete Knopf der Spracheingabe mit Mikrofon-Symbol,
daneben ihr Status, rechts „Senden“ bzw. „Diagnose abgeben“ als einzige gefüllte
Hauptaktion. Während einer Aufnahme ist der Knopf rot umrandet („Spracheingabe
beenden“) und vor dem Status pulsiert ein roter Punkt. Während der Transkription
ist der Knopf gesperrt, vor dem Status dreht sich ein Spinner und das Feld ist
schreibgeschützt. In beiden Phasen ist Senden gesperrt. Fehler erscheinen rot im
Status. Ohne Einwilligung gibt es keinen Knopf; an seiner Stelle steht still
„Spracheingabe nicht freigegeben. Sie nutzen die Tastatur.“ Auf schmalen
Bildschirmen stehen Spracheingabe und Senden in einer Zeile, der Status
darunter.

Im Gespräch folgt unter der Eingabezeile eine eigene Aktionszeile, durch eine
Trennlinie abgesetzt. Rechts steht „Gespräch beenden →“ als grau umrandeter
Knopf, davor in gedämpfter Schrift „Genug gefragt? Danach folgt der Debrief mit
Ihrer Diagnose.“ Links steht in Training und Erhebung „Sitzung abbrechen“ als
roter Textlink; die Sitzung wird damit verworfen. Im Probelauf gibt es kein
Abbrechen. Beide Aktionen wirken ohne Rückfrage. Nach einer fehlgeschlagenen
Antwort heißt der Knopf „Gespräch beenden und Debrief anzeigen“. Im Debrief gibt
es keine Aktionszeile. Auf schmalen Bildschirmen steht der Erklärsatz allein
oben, Abbrechen und Beenden teilen sich die Zeile darunter.

Solange eine Frage abgeschickt ist und beantwortet wird, sind Senden,
Spracheingabe, „Gespräch beenden“ und „Sitzung abbrechen“ gesperrt und das Feld
ist schreibgeschützt. Ein zweiter Klick auf „Senden“ löst keinen zweiten Schritt
aus, auch ohne htmx. Kommt die Anfrage nicht an (Netzabriss, Serverfehler),
erscheint unten auf der Seite rot und für Screenreader angesagt „Die Anfrage ist
nicht angekommen. Bitte versuchen Sie es erneut.“; der Hinweis gilt für jede
htmx-Anfrage der Plattform und verschwindet mit der nächsten gelungenen. Danach
ist das Feld wieder beschreibbar, der Text steht noch darin, und alle Knöpfe
sind wieder frei. Scheitert dagegen die Antwort des Sprachmodells, erscheint wie
bisher „Die Antwort konnte nicht erzeugt werden.“ mit „Erneut senden“. Eine
leere oder nur aus Leerraum bestehende Denkspur oder Äußerung zählt dabei als
ungültige Ausgabe, ebenso eine, die nur aus `true`, `false` oder `null` besteht,
und wird wie jede andere wiederholt; dasselbe gilt für die Äußerung der
Lehrperson und die Begründung des Bewerters im Evallauf.

Nach jedem Tausch in der Sitzung springt der Tastaturfokus auf den neuen Inhalt,
damit Screenreader ihn ansagen: nach einem Gesprächsschritt auf den neuen
Schritt mit Frage und Antwort, nach einer gescheiterten Antwort auf die
Fehleranzeige, nach „Gespräch beenden“ auf die Überschrift „Ihre Diagnose“ und
beim Fragebogen unter der Sitzung auf dessen Überschrift „Fragen zu dieser
Sitzung“. Gescrollt wird dabei wie bisher; der Fokus erzeugt keinen zusätzlichen
Sprung.

Gilt eine Eingabe nicht mehr, wenn ihre Antwort eintrifft, verfällt sie: Sie
wird kein Gesprächsschritt, und nichts davon bleibt gespeichert, auch kein
Fehlschlag. Das geschieht, wenn die Sitzung inzwischen in einem anderen Tab oder
auf einem anderen Gerät abgeschlossen oder abgebrochen wurde, und bei zwei
gleichzeitig abgeschickten Eingaben derselben Sitzung für die später
beantwortete. Die Seite lädt dann neu und zeigt den tatsächlichen Stand: im
Training die beendete Sitzung, in der Erhebung die aktuelle Stelle des Ablaufs,
bei zwei gleichzeitigen Eingaben das Gespräch mit der zuerst beantworteten. Nur
wenn die Sitzung inzwischen beendet ist, steht oben der Hinweis „Diese Sitzung
wurde inzwischen an anderer Stelle beendet; Ihre letzte Eingabe wurde nicht mehr
verarbeitet.“ Eine beendete Sitzung wechselt ihren Status nicht mehr: Ein
späteres Abbrechen, Abschließen oder Scheitern ändert nichts und zeigt ihren
Stand, und die Uhr eines Zeitbudgets bucht danach keine Zeit mehr.

Eine einzelne Aufnahme ist auf 15 MB begrenzt — je nach Kodierung grob 15 bis 60
Minuten Sprache. Ist die Grenze erreicht, endet die Aufnahme von selbst und wird
transkribiert; das bereits Gesagte geht nicht verloren. Dieselbe Grenze hält der
Transkriptions-Endpunkt: Eine größere Aufnahme lehnt er ab, bevor er sie
einliest.

Im **Probelauf** der Autor:innen gibt es keinen Einwilligungsschritt: Dort
spricht die angemeldete Autor:in über ihr eigenes Material, nicht eine
pseudonyme Teilnehmer:in. Das Mikrofon steht im Diagnosegespräch und im Debrief
genau dann bereit, wenn das Tor der aktiven Transkriptions-Fassung offen ist
(erklärt, nicht `fake`); sonst bleibt nur die Tastatur.

## Erhebungsteilnahme

Ein Teilnahme-Link einer Stichprobe legt im Browser eine pseudonyme Teilnahme an
oder setzt sie fort. Dafür ist kein Nutzerkonto erforderlich; die
Forschungsdaten sind über ein ablesbares Teilnahme-Token von
Trainingsaktivitäten getrennt. Während das Teilnahmefenster läuft, führt der
Link zuerst über die Einwilligung und die Instruktion; diese weist darauf hin,
dass das Diagnosegespräch begrenzt ist. Anschließend werden die gezogenen
Vignetten als persistierte Sitzungen gespielt; Gespräch, Diagnose und interne
Denkspur bleiben Teil der Datenspur, wobei die Denkspur nie in der
Teilnehmer:innenansicht erscheint. Die Einwilligungsseite zeigt unter dem
Einwilligungstext der Forschenden drei getrennte Einwilligungen mit je einem
festen, nicht abschaltbaren Systemtext zur Folge einer Ablehnung: Verarbeitung
durch Sprachmodelle, Spracherkennung und Speicherung und Verwendung für
Forschungszwecke; der Text zur Speicherung sagt, dass ohne sie Gespräche und
Diagnosen nur bis einen Tag nach dem letzten Schritt vorgehalten werden und sich
bis dahin eine Abschrift ins Nutzerkonto holen lässt, dass Fragebogen-Antworten
gar nicht gespeichert werden, und nennt den Widerruf per Teilnahme-Token bei der
Studienleitung. Jede ist eine Pflichtwahl Ja/Nein ohne Vorauswahl, danach folgt
»Weiter«. Die Spracherkennung wird nur gefragt, wenn die Instanz transkribiert,
also die aktive Transkriptions-Fassung einen echten Anbieter und eine nicht
widerrufene Zero-Retention-Erklärung trägt. Wer der Verarbeitung durch
Sprachmodelle nicht zustimmt, landet auf einer systemseitigen Abbruchseite ohne
Abschlusstext, Fragebogen oder Token; Teilnahme-Link, Token-Wiedereinstieg und
alle übrigen Teilnahmeseiten führen dann dorthin, und es entstehen weder Ziehung
noch Sitzung. Ihr Knopf »Zur Startseite der Erhebung« führt zurück zum
Einwilligungsformular ohne Vorauswahl; eine neue Entscheidung ersetzt die alte.
Ist die Verarbeitung durch Sprachmodelle einmal erteilt, stehen alle drei
Entscheidungen fest; ein erneuter Aufruf des Einwilligungsformulars führt dann
in den Ablauf. Solange die Teilnahme dieses Browsers nicht eingewilligt hat,
bietet die Einwilligungsseite darunter in einem eigenen Formular einen zweiten
Weg: »Sie haben schon ein Teilnahme-Token?« mit Feld und »Hier fortsetzen«.
Groß- und Kleinschreibung, Leerzeichen und ein fehlender Bindestrich zählen
nicht (`vc9h ynfr` gilt als `VC9H-YNFR`). Gehört das Token zu einer laufenden,
nicht archivierten Stichprobe, wird es unter deren Teilnahme-Link an den Browser
gebunden — auch wenn die Seite über einen anderen Link erreicht wurde —, und es
geht dort weiter, wo die Teilnahme steht, nach abgelehnter Verarbeitung durch
Sprachmodelle also auf der Abbruchseite. Die beim Link-Aufruf angelegte, noch
einwilligungslose Teilnahme bleibt dabei unverbunden liegen. Ein unbekanntes
Token, eines außerhalb des Fensters oder einer archivierten Stichprobe und eine
leere Eingabe ergeben dieselbe Meldung „Zu diesem Token lässt sich keine
Teilnahme fortsetzen.“ auf der Einwilligungsseite, ohne zu verraten, ob das
Token existiert. Welches Token der Browser zu welchem Teilnahme-Link hält, steht
in einem eigenen signierten Cookie, das nur unter `/erhebungen/teilnahme/` gilt,
nie in der Session des Nutzerkontos: Auch bei nebenbei angemeldetem Konto oder
einer Anmeldung nach der Teilnahme liegen Konto und Token auf dem Server nie im
selben Datensatz, und eine Anmeldung oder Abmeldung beendet die Zuordnung nicht.
Jeder Aufruf einer Teilnahmeseite verlängert sie; nach einem Tag ohne Zugriff
ordnet der Browser die Teilnahme nicht mehr zu, der Teilnahme-Link legt dann
eine neue an, und das notierte Token führt über die Eingabe weiter in die alte.
Wer der Speicherung nicht zustimmt, macht eine flüchtige Teilnahme: Die
Vignetten werden genauso gespielt, Verlauf, Debrief und Diagnose erscheinen wie
gewohnt, und ein Neuladen setzt an derselben Stelle fort. Gesprächsschritte,
Fehlversuche und Diagnose gelangen dabei aber nie in die Forschungsdatenbank,
auch nicht in die Session des Browsers: Der Server hält sie je Sitzung in einem
kurzlebigen Speicher außerhalb von Datenbank und Backup vor (`FLUECHTIG_PFAD`),
bis einen Tag nach dem letzten Zugriff der Teilnahme; jeder Aufruf einer ihrer
Seiten verschiebt diese Frist, und weder der Abschluss noch ein anderer Schritt
löscht vorher etwas. Abgelaufene Inhalte entfernt ein nächtlicher Aufräumlauf
vom Server. Gespeichert und exportiert wird nur das Ablaufgerüst (Ziehung,
Sitzungen mit Status, Zeitstempeln und verbrauchter Zeit, Vignettenposition).
Auch die Fragebögen werden ihr wie allen anderen vorgelegt, doch ihre Antworten
werden beim Abschicken verworfen: Es entsteht keine Item-Antwort, auch keine
Markierung »vorgelegt, übersprungen«; nur der Itemblock hält mit Vorlage und
Erledigung fest, dass der Ablauf weiterging. Das Token führt auch eine flüchtige
Teilnahme in jedem Browser fort, samt bisherigem Verlauf und Gedächtnis der
simulierten Schüler:in. Sind die Inhalte einer laufenden Sitzung abgelaufen,
endet diese Sitzung beim nächsten Zugriff als `abgebrochen`, statt mit einer
Schüler:in ohne Gedächtnis weiterzulaufen. Danach geht der Ablauf regulär
weiter: mit dem Fragebogen der Sitzung, der nächsten Vignette oder dem
Abschluss. Wer der Spracherkennung zustimmt, kann Eingaben im Diagnosegespräch
und die Diagnose per Mikrofon eingeben; ohne Zustimmung bleibt die
Tastatureingabe vollständig nutzbar. Nach jeder beendeten Sitzung erscheinen
ihre freiwilligen Fragebogen-Items direkt unter dem Verlauf; sie können
beantwortet oder übersprungen werden, bevor die nächste Vignette beginnt. Nach
der letzten Sitzung folgen zusätzlich die freiwilligen Fragebogen-Items am
Andockpunkt `am Ende` als eigene Seite. Jede Item-Antwort wird sofort
gespeichert, und auch übersprungene Fragebogen-Items bleiben als vorgelegt
dokumentiert. Likert-Items bieten dabei die global festgelegten Skalenpole zur
Auswahl an; festgehalten wird die zugehörige Stufe. Ein noch nicht abgeschickter
Fragebogen — nach einer Sitzung ebenso wie am Ende — wird auch in einem anderen
Browser erneut vorgelegt; ein abgeschickter nicht mehr. Der gesamte Fortschritt
hängt am Teilnahme-Token und nicht am Browser: Ein Aufruf setzt die Teilnahme
genau dort fort, wo sie steht — bei der Instruktion, im laufenden Gespräch, beim
offenen Fragebogen oder bei der nächsten Vignette. Anschließend endet die
Teilnahme mit dem Abschlusstext. Damit das Token jederzeit ablesbar ist, zeigt
die Seitenleiste es auf allen Teilnahmeseiten — von der Einwilligung über
Instruktion, Diagnosegespräch und Debrief bis zu Fragebogen- und Abschlussseite
— an der Stelle, an der sonst Konto oder Anmeldelink stehen, in fester Laufweite
und mit der Bitte, es zu notieren, weil sich die Teilnahme damit in einem
anderen Browser fortsetzen lässt. Während einer Teilnahme erscheinen dort weder
Kontoblock noch Anmeldelink, auch nicht bei nebenbei angemeldetem Konto; in
Forschenden-Ansichten erscheint umgekehrt kein Teilnahme-Token. Unter dem
Abschlusstext steht auf der Abschlussseite zusätzlich ein systemseitiger
Hinweis, den die Forschende nicht abschalten kann: das Token groß und in fester
Laufweite, dazu die Erklärung, dass sich damit angemeldet später eine Abschrift
der eigenen Sitzungen ins Nutzerkonto holen lässt und dass es ohne das Token
keine Abschrift gibt, samt Link auf die Token-Eingabe. Ein erneuter Aufruf der
Abschlussseite zeigt beides wieder. Bei einer flüchtigen Teilnahme steht
stattdessen der ebenso unabschaltbare Abschnitt „Keine Speicherung“: »Sie haben
der Speicherung Ihrer Daten für die Forschung nicht zugestimmt. Ihre Gespräche
und Diagnosen werden deshalb nur bis einen Tag nach Ihrem letzten Schritt
vorgehalten und dann gelöscht; Ihre Fragebogen-Antworten wurden nicht
gespeichert.« Darunter steht das Token wie bei eingewilligten Teilnahmen, mit
dem Hinweis, dass sich damit angemeldet innerhalb dieser Frist eine Abschrift
der eigenen Sitzungen ins Nutzerkonto holen lässt und es danach keine mehr gibt,
samt Link auf die Token-Eingabe; auch er erscheint bei jedem Aufruf wieder.
Abschlusstext und Token in der Seitenleiste bleiben. Ein Diagnosegespräch kann
vorzeitig in den Debrief geführt werden; eine Sitzung kann ohne Diagnose
abgebrochen werden. Ist die Diagnose abgegeben, bleibt sie im Debrief sichtbar,
lässt sich aber nicht mehr ändern; hängt an der Sitzung ein Fragebogenblock,
erscheint er darunter als eigener Abschnitt. Scheitert ein Antwortversuch
endgültig, bleibt der Gesprächsschritt ohne Antwort erhalten. Nach dem
Teilnahmefenster sind unfertige Teilnahmen verfallen und nicht fortsetzbar.
Außerhalb des laufenden Fensters oder bei archivierter Stichprobe gilt das Token
als unbekannt: Es ergibt dasselbe 404 wie ein geratenes Token und verrät so
nicht, ob es existiert.

Einwilligungs-, Instruktions- und Abschlusstext erscheinen als gerendertes
Markdown: Absätze durch Leerzeilen, jeder einfache Zeilenumbruch bleibt
erhalten, dazu **fett**, *kursiv*, Aufzählungen, nummerierte Listen und
Zitatblock. Überschriften `#`, `##` und `###` ordnen sich als dritte bis fünfte
Ebene unter den Abschnittskopf der Seite ein. Ein nach einer Leerzeile um vier
Leerzeichen eingerückter Block erscheint in Festbreitenschrift und behält seine
Einrückung. Links sind nur mit `https:`, `http:` und `mailto:` möglich.
Web-Links öffnen in einem neuen Tab, tragen einen sichtbaren Pfeil und kündigen
Screenreadern das Öffnen in neuem Tab an; E-Mail-Links öffnen das Mailprogramm
im selben Tab, tragen einen Briefumschlag und kündigen sich als E-Mail an. Rohes
HTML, Bilder, Tabellen, umzäunte Codeblöcke, tiefere Überschriften, andere
Link-Ziele wie `javascript:` oder relative Pfade sowie nackte URLs erscheinen
wörtlich; ein vorangestellter Backslash zeigt Markdown-Zeichen wörtlich.

## Abschriften holen

Unter `/trainings/abschriften/` gibt jedes eingeloggte Konto ein Teilnahme-Token
ein und holt damit eine abgeschlossene Erhebungsteilnahme als **Abschrift** in
das eigene Konto: Die Sitzungen werden unter eine eigene, neue Teilnahme
kopiert; Fragebogen-Antworten bleiben bei der Erhebung. Die Erhebungsdaten
selbst bleiben unberührt, es wird kein Token gespeichert und keine Verknüpfung
zwischen Konto und Teilnahme festgehalten. Der Import gelingt unabhängig vom
Teilnahmefenster, solange weder Stichprobe noch Erhebung archiviert sind, und
ist beliebig oft wiederholbar; jede Wiederholung erzeugt eine weitere Abschrift.
Auch eine flüchtige Teilnahme ergibt eine Abschrift, solange ihre Inhalte
vorgehalten werden: Gesprächsschritte samt Denkspur, Fehlversuche und Diagnose
kommen dann aus dem kurzlebigen Speicher, und es entsteht dieselbe Abschrift wie
bei einer eingewilligten. Der Import liest nur und verschiebt die Frist nicht.
Unbrauchbare Tokens — auch das einer flüchtigen Teilnahme, deren Inhalte
abgelaufen sind — werden mit derselben Meldung ohne Angabe eines Grundes
abgelehnt. Die Liste zeigt je Abschrift den Namen der Erhebung und den
Importzeitpunkt — nicht die Spielzeit der Erhebung. Von der Liste führt jede
Abschrift in eine eigene, nur lesende Ansicht: die gespielten Vignetten in der
Reihenfolge ihrer Vignettenposition, je Vignette Lernauftrag und Arbeitsheft,
das Transkript des Diagnosegesprächs, den Ausgang der Sitzung und die eigene
Diagnose. Die Denkspur der simulierten Schüler:in erscheint auch hier nicht; es
gibt weder Eingabefeld noch Sitzungsnavigation. Abschriften sind kontoprivat —
eine fremde ist nicht erreichbar. Aus der Ansicht heraus lässt sich die
Abschrift löschen; dabei verschwinden ihre Teilnahme, die kopierten Sitzungen
und alle Freigaben, während die Daten der Erhebung unberührt bleiben.

Vor dem Löschknopf steht die Sektion „Freigabe“: eine Checkbox-Liste aller
Trainings, denen das Konto beigetreten und aus denen es nicht ausgetreten ist,
angehakt heißt freigegeben, und der Knopf „Freigaben speichern“. Freigegeben
wird immer die ganze Abschrift, für beliebig viele Trainings und unabhängig
davon, ob ihre Vignetten zum Training gehören (ADR-0049). Ein abgewählter Haken
widerruft die Freigabe sofort. Ein Training ohne eigene Trainingsbindung oder
mit ausgetretener wird mit 404 abgewiesen; nach dem Austritt aus einem Training
entsteht so keine neue Freigabe dafür. Der Seitenkopf nennt die Trainings, für
die die Abschrift wirksam freigegeben ist; ohne Freigabe heißt es dort „Ihre
Abschrift — nur Sie lesen sie.“ Einen Hinweis auf bereits gezogene
Trainingsexporte oder zur Wiedererkennung durch Forschende gibt es bewusst
nicht. Wer derzeit keinem Training angehört, liest statt der Liste den Hinweis
„Sie gehören derzeit keinem Training an.“, außer es gibt ruhende Freigaben.

Nach dem Austritt aus einem Training ruht die Freigabe der Abschrift dafür
(ADR-0049): Sie wirkt nicht, bleibt aber bestehen und lebt mit einem
Wiederbeitritt wieder auf. Fremdeinsicht in eine Abschrift gibt es nur, solange
ihr Konto genau dem Training, für das freigegeben ist, aktiv angehört. Unter der
Checkbox-Liste stehen ruhende Freigaben getrennt unter „Ruhende Freigaben“, je
Training mit „ruht (ausgetreten)“ und dem Knopf „Freigabe widerrufen“. Er
widerruft nur diese eine Freigabe (nur per POST, sonst 405) und führt mit der
Meldung „Die ruhende Freigabe für … ist widerrufen.“ zurück auf die Abschrift;
für ein Training ohne ruhende Freigabe antwortet er mit 404. „Freigaben
speichern“ lässt ruhende Freigaben unverändert.

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
Abschlusstext. Die drei Texte stehen im Entwurf zunächst gerendert zum Lesen,
auf wenige Zeilen gekürzt; »Ganz anzeigen« klappt einen langen Text auf. Ein
leerer Text zeigt »Noch kein Text« und statt »Bearbeiten« den Knopf »Text
schreiben«. »Bearbeiten« öffnet nur diesen Text im Markdown-Feld, mit eigenen
Knöpfen »Speichern« und »Abbrechen«. Jeder Speichern-Knopf der Seite, am Text
wie unter den Texten »Konfiguration speichern«, speichert alle drei Texte, auch
die geöffneten. »Abbrechen« verwirft nur die Änderungen an diesem Text. Auch
»Finalisieren« speichert vorher alles, offene Texte eingeschlossen. Wer die
Seite mit ungespeicherten Änderungen verlässt, wird vom Browser gewarnt. Die
drei Texte bleiben optional und sperren das Finalisieren nicht. Unter jedem
Markdown-Feld steht ein kurzer Markdown-Hinweis samt Link-Syntax; der Umschalter
»Bearbeiten | Vorschau« zeigt den ungespeicherten Text so, wie die
Teilnahmeseite ihn rendert. Die Vorschau holt das Fragment vom Endpunkt
`/texte/vorschau/`, der Quelle und Profil (Informations- oder Szenentext)
annimmt, mit derselben Funktion wie die Anzeigeseite rendert und nichts
speichert; er steht nur angemeldeten Autor:innen, Forschenden und
Administrator:innen offen. Finale und archivierte Erhebungen zeigen die drei
Texte gerendert als Leseansicht, ein leerer Text erscheint als »—«. Reine
Entwürfe lassen sich löschen; das Design finaler Erhebungen bleibt
unveränderlich, ihr Eigentümer-Kreis änderbar. Das Finalisieren pinnt die
Modell-Konfiguration der Verwendung Schüler:in sichtbar. Es gelingt nur, wenn
diese eine nicht widerrufene Zero-Retention-Erklärung trägt oder den Anbieter
`fake` hat; sonst bleibt die Erhebung Entwurf, und die Meldung verweist darauf,
dass eine Administrator:in zuerst eine erklärte Konfiguration für Schüler:in
aktivieren muss. Ein Rückzug ist nur ohne nicht-archivierte oder datentragende
Stichprobe möglich. Finale Erhebungen lassen sich archivieren und wieder
entarchivieren, sofern keine Stichprobe läuft und mindestens eine Eigentümerin
eingetragen ist. Eigentümer:innen teilen und übergeben eine Erhebung über die
Detailansicht; auch bei finalen und laufenden Erhebungen bleibt dieser Kreis
änderbar. Unter einer finalen Erhebung lassen sich Stichproben mit Beginn und
Ende anlegen; ein fehlender oder ungültiger Zeitpunkt oder ein Ende vor dem
Beginn führt zurück auf die Detailseite, die den Grund als Meldung zeigt, und
die Eingabe bleibt nicht stehen. Die Detailseite zeigt ihren kopierbaren
Teilnahme-Link, ihre aus dem Zeitraum abgeleitete Phase — geplant, läuft oder
abgeschlossen — und die Zahl ihrer Teilnahmen. Daneben stehen, nach dem
aktuellen Stand der Einwilligungen, die Zahl der Teilnahmen, die die
Verarbeitung durch Sprachmodelle abgelehnt haben, und die Zahl der Teilnahmen
ohne Speicherung. Datenfreie Stichproben lassen sich archivieren; die
Phasenspalte weist sie danach als archiviert aus. Der optionale Fragebogen eines
Entwurfs besteht aus eigenen finalen Items an zwei getrennten Andockpunkten:
nach jeder Vignettensitzung oder am Ende. Eine Fassung kann an beiden Stellen,
je Stelle aber nur einmal vorkommen. Vignetten und beide Andockpunkte sind je
eine Liste; ihre Reihenfolge ist die Reihenfolge der Erhebung, ein eigenes
Positionsfeld gibt es nicht. Über jeder Liste wählt man unter »Hinzufügen …«
eine Fassung und die Stelle, an der sie eingefügt wird (»am Ende«, »am Anfang«
oder »nach …«). Jede Zeile trägt Symbolknöpfe mit Beschriftung für Hilfstechnik:
↑ und ↓ verschieben um eine Stelle, der Papierkorb entfernt; ein Item hat
zusätzlich ⇄ zum Umhängen ans Ende des anderen Andockpunkts, solange es dort
nicht schon hängt. Umsortieren lässt sich auch durch Ziehen am Griff, mit Maus
wie mit Touch, aber nur innerhalb einer Liste; ohne Maus reichen die Knöpfe und
Auswahlfelder. Jede Änderung gilt sofort, beim Entfernen und Umhängen schließt
sich die Reihenfolge. Ist eine Fassung bereits am anderen Andockpunkt gebunden,
kennzeichnet die Auswahl dies, ohne ihre Aufnahme zu verhindern. Der Schalter
»Zufällige Reihenfolge« über der Vignettenliste mischt die Vignetten je
Teilnahme; dann zeigt die Liste keine Nummern, keine Positionswahl und kein
Verschieben. Das Umschalten ändert nur die Regel: Die Reihenfolge der Liste
bleibt gespeichert, beim Wechsel zurück zu fest gilt wieder die zuvor
festgelegte Reihenfolge, neu aufgenommene Vignetten stehen am Ende. Finale und
archivierte Erhebungen zeigen Vignetten und Items weiterhin als Listen, samt
Reihenfolgeregel, ohne Auswahl und Änderungsaktionen; nach einem Rückzug sind
sie wieder bearbeitbar. Trifft eine Änderung dennoch eine Erhebung, die kein
Entwurf mehr ist, etwa über eine veraltete Schaltfläche in einem zweiten Tab,
bleibt alles, wie es war: Die Seite führt zurück auf die Detailseite, beim
Löschen auf die Liste, und die Meldung »Die Erhebung ist kein Entwurf mehr. Es
wurde nichts geändert.« nennt den Grund. Weist die Erhebung eine Änderung aus
einem anderen Grund ab, steht dieser Grund ebenso als Meldung auf der
Detailseite. Eine fremde Erhebung bleibt dabei unauffindbar. Sobald eine
Stichprobe besteht, lässt sich an der Erhebung die Datenspur als ZIP mit
relationalen CSV-Dateien herunterladen, einschließlich der geplanten
Vignettenziehungen, der tatsächlich gelaufenen Sitzungen, Gesprächsschritte,
Fehlversuche und Diagnosen. Jede Tabelle, die eine Teilnahme über ihr Token
ausweist, nennt daneben in der Spalte `teilnahmekennung` deren Teilnahmekennung:
acht Hexzeichen, beim Anlegen der Teilnahme zufällig gezogen und danach
unveränderlich. Jeder Gesprächsschritt und jede Diagnose vermerken dabei den
Eingabemodus: ob der Text getippt, eingesprochen oder aus beidem zusammengesetzt
wurde. Der Wert wird im Browser der Teilnehmer:in bestimmt und ist damit eine
Angabe für die Auswertung, kein Nachweis. Jede Sitzungszeile nennt die
verbrauchte Zeit in Sekunden; bei einer Vignette mit schrittbasiertem Budget
bleibt sie bei null, der Wert ist also zusammen mit dem Budget-Typ der
Vignettenfassung zu lesen. Die verwendeten Vignettenfassungen,
Simulationskern-Fassungen und Modell-Konfigurationen liegen mit ihrem
vollständigen Inhalt als eigene Tabellen bei, damit der Export ohne
Datenbankzugriff interpretierbar bleibt. Jede Modell-Konfiguration nennt dort
ihren Erklärungsstand: ob eine gültige Zero-Retention-Erklärung vorliegt, ihren
Beleg und den Zeitpunkt der Erklärung (ohne Erklärung `NA`) sowie Zeitpunkt und
Grund eines Widerrufs (ohne Widerruf `NA` und leer), so wie er heute ist. Nach
einem Widerruf steht „erklärt“ auf `False`, Beleg und Zeitpunkt der Erklärung
bleiben. Erklärendes und widerrufendes Konto stehen nicht darin. Für den
Fragebogen-Teil gilt dasselbe: Die tatsächlich vorgelegten Fassungen der
Fragebogen-Items liegen mit ihrem vollen Wortlaut bei; eine zugeordnete, aber
nie vorgelegte Fassung erscheint nicht. Eine eigene Tabelle nennt die Kodierung
der Likert-Skala, deren Stufe von 1 »Stimme gar nicht zu« bis 6 »Stimme voll zu«
mit der Zustimmung steigt, und die vorgelegten Itemblöcke stehen mit ihrem
Andockpunkt sowie den Zeitstempeln der Vorlage und der Erledigung darin — ein
übersprungener Block bleibt so als vorgelegt erkennbar. Die Antworten selbst
liegen als eigene Tabelle bei, eine Zeile je vorgelegtem Fragebogen-Item, mit
getrennten Spalten für Freitext und Likert-Stufe. Eine vorgelegte, aber
unbeantwortete Zeile bleibt mit leeren Werten erhalten; nur so unterscheidet die
Auswertung »freiwillig übersprungen« von »nie gesehen«. Flüchtige Teilnahmen
haben Itemblöcke, aber keine Antwortzeilen.

## Einsicht in die Erhebung

Hat eine Erhebung Teilnahmen, die in der Übersicht als Zeile erscheinen, steht
auf ihrer Detailseite neben dem Export der Link „Einsicht“ (ADR-0049). Die
Übersicht ist rein lesend und für den Kreis der Erhebung und die Administration
erreichbar, auch für Teilnahmen von vor der Aufnahme in den Kreis und nach dem
Archivieren von Stichprobe oder Erhebung. Wer aus dem Kreis ausgetreten ist und
fremde Forschende bekommen 404, Konten ohne Forschungsrolle 403.

Je Stichprobe zeigt sie ein Raster wie die Fremdeinsicht im Training: eine Zeile
je Teilnahme, beschriftet mit ihrer Teilnahmekennung und nach Beginn sortiert,
die älteste oben; Teilnahmen aus der Zeit vor dem Beginndatum gelten als die
ältesten. Dazu kommt eine Spalte je Vignette in der Reihenfolge der Erhebung.
Jede Zelle hält höchstens eine Sitzung als runde Bubble mit der gespielten
Position aus der Vignettenziehung; Tooltip und Screenreader nennen ihren Status.
Abgeschlossene Sitzungen erscheinen normal, abgebrochene und gescheiterte in
Warnfarbe, laufende gedimmt. Flüchtige Teilnahmen zeigen nur umrandete Bubbles,
und ihre Zeile trägt den Hinweis „flüchtig, nur Ablaufgerüst“. Eingewilligte
Teilnahmen ohne Sitzung stehen mit „noch keine Sitzung“ in der Liste;
Teilnahmen, die Einwilligung a abgelehnt oder noch nicht gegeben haben, fehlen.
Eine Stichprobe ohne solche Zeilen zeigt „Noch keine Teilnahme mit
Einwilligung.“ Das Teilnahme-Token steht nirgends auf der Seite.

Die Bubbles abgeschlossener, abgebrochener und gescheiterter Sitzungen nicht
flüchtiger Teilnahmen sind Links auf die Sitzungsansicht unter
`eigene/<pk>/einsicht/sitzungen/<sitzung_pk>/`; laufende und flüchtige Bubbles
sind es nicht. Die Sitzungsansicht zeigt im Kopf Teilnahmekennung, Stichprobe,
Vignette und Status und führt zurück zur Übersicht. Darunter steht die Sitzung
rein lesend so, wie die Teilnehmer:in sie gesehen hat: Rahmenhandlung,
Transkript in gespielter Reihenfolge und bei abgeschlossenen Sitzungen Debrief
und abgegebene Diagnose, ohne Diagnose „Keine Diagnose abgegeben.“. Anders als
für die Teilnehmer:in liegt unter jedem Gesprächsschritt die Denkspur,
eingeklappt unter „Denkspur ansehen“ wie im Probelauf, und unter der Sitzung
stehen die Antworten auf den abgeschickten Item-Block nach dieser Sitzung, mit
Skalenpol oder Freitext und einem Strich für unbeantwortete Items. Fehlversuche,
das Teilnahme-Token, Formulare und Aktionen erscheinen nicht. Laufende
Sitzungen, Sitzungen flüchtiger Teilnahmen und Sitzungen, die nicht zur Erhebung
aus der URL gehören, antworten mit 404.

Hinter den Vignetten steht die Spalte „Abschluss“. Hat eine nicht flüchtige
Teilnahme ihren Item-Block am Ende abgeschickt, steht dort eine verlinkte
Bubble; sonst ein Strich. Sie führt auf die Abschlussseite unter
`eigene/<pk>/einsicht/teilnahmen/<teilnahme_pk>/abschluss/`. Die Seite nennt
Teilnahmekennung und Stichprobe, zeigt die Antworten des Blocks rein lesend mit
Skalenpol oder Freitext und einem Strich für unbeantwortete Items und führt
zurück zur Übersicht. Das Teilnahme-Token erscheint auch hier nicht. Flüchtige
Teilnahmen, nicht abgeschickte Blöcke und Teilnahmen, die nicht zur Erhebung aus
der URL gehören, antworten mit 404.

## Fragebogen-Items verwalten

Forschende und Administrator:innen erreichen unter `/fragebogen-items/` die
private Item-Bibliothek. Dort legen sie Freitext- oder Likert-Items zunächst als
Entwurf an und finalisieren sie, sobald ihr Wortlaut feststeht. Finale Fassungen
sind unveränderlich und für Erhebungen einbindbar; eine neue Fassung erzeugt
stattdessen einen bearbeitbaren Folgeentwurf. Eine überholte Fassung, die
bereits eine nicht archivierte Nachfolgerin hat, bietet keine neue Fassung an.
Ein Versuch führt zum offenen Entwurf der Historie, falls es einen gibt, und
sonst mit einer Meldung zurück auf ihre Detailansicht. Finale Fassungen lassen
sich archivieren und bei Bedarf wieder entarchivieren; Entwürfe lassen sich
physisch löschen. Lehnt das Item das Finalisieren oder Archivieren ab, etwa weil
der Wortlaut fehlt, erscheint der Grund als Meldung auf der Detailansicht. Die
Bibliothek zeigt Items aus dem eigenen Eigentümer-Kreis; Administrator:innen
sehen alle Items. Eigentümer:innen lassen sich direkt an der Item-Historie
hinzufügen oder entfernen. Der Kreis bleibt dabei immer besetzt; die eigene
Entfernung übergibt die Historie an die verbleibenden Eigentümer:innen und führt
zurück in die Item-Bibliothek. Likert-Items verwenden die sechs global
festgelegten, nicht editierbaren Skalenstufen von 1 = „Stimme gar nicht zu" bis
6 = „Stimme voll zu".
