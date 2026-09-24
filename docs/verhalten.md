# Verhalten der Plattform

Dieses Dokument beschreibt das sichtbare Verhalten der Plattform je Bereich so,
wie es heute umgesetzt ist. Es ist die Referenz für die Frage »Was tut die
Anwendung an dieser Stelle genau?« — für Begriffe siehe [CONTEXT.md](../CONTEXT.md),
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

## Formulare

In den Formularen zum Anlegen und Bearbeiten (Vignetten, Trainings, Erhebungen,
Fragebogen-Items, Simulationskern, Modell- und Transkriptions-Konfiguration)
stehen die Aktionen wie »Abbrechen« und »Speichern« oben im Formular und bleiben
beim Scrollen sichtbar, solange das Formular im Bild ist. Auf den Seiten der
Teilnahme stehen sie weiterhin am Ende, etwa »Einwilligen« nach der Wahl zur
Audioverarbeitung.

## Vignetten verwalten

Autor:innen sehen die Vignetten ihres Eigentümer-Kreises; Administrator:innen
sehen alle. In der Detailansicht lässt sich eine weitere Autorin oder
Administratorin als Eigentümer:in hinzufügen oder eine vorhandene entfernen. Der
Kreis bleibt dabei immer besetzt; die eigene Entfernung übergibt die Historie an
die verbleibenden Eigentümer:innen.

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

## Trainings verwalten

Ausbilder:innen sehen die Trainings ihres Eigentümer-Kreises;
Administrator:innen sehen alle. In der Kuratierungsansicht lässt sich eine
weitere Ausbilderin oder Administratorin als Eigentümer:in hinzufügen oder eine
vorhandene entfernen. Der Kreis bleibt auch bei veröffentlichten Trainings
besetzt; die eigene Entfernung übergibt das Training an die verbleibenden
Eigentümer:innen.

## Simulationskern

Autor:innen und Administrator:innen können die finale Kern-Fassung und die
aktive Modell-Konfiguration schreibgeschützt unter `/system/kern/` einsehen. Ist noch
kein finaler Kern vorhanden, stellt die Ansicht das nur fest. Administrator:innen
erhalten unter `/system/kern/verwalten/` außerdem den Überblick über den Entwurf, die
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

## Modell-Konfiguration

Administrator:innen setzen das Sprachmodell unter `/system/modell-konfiguration/`.
Der Anbieter ist eine feste Auswahl — `fake`, `openrouter` oder `infomaniak` —,
der Modellname bleibt freier Text; Basis-URL und Token liegen an der Konfiguration
und nicht in der Umgebung. Die Parameter nehmen nur Mikro-Stellschrauben des
Modellverhaltens auf, bei `fake` ausschließlich das Skript. Neben dem
Sprachmodell schlägt der Knopf „Modelle und Basis-URL laden“ die Modelle des
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
Die Seite listet alle je angelegten Konfigurationen mit Anbieter, Modellnamen,
Basis-URL, maskiertem Token und Parametern und markiert die aktive. Sie bietet
genau zwei Gesten: Anlegen und Aktivieren. Bearbeiten und Löschen gibt es nicht —
eine Konfiguration ist unveränderlich, weil jede Erhebung ihre Fassung pinnt. Ein
Umschalten trifft laufende Trainings sofort und laufende Erhebungen gar nicht; eine
Schlüsselrotation ist deshalb kein Feldupdate, sondern Anlegen plus Aktivieren. Das
Token wird eingegeben, aber nie zurückgegeben: Die Liste zeigt es nur maskiert mit
seinen letzten vier Zeichen, kurze Werte ausschließlich als Punkte.

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
Teilnahme- und die getrennte Audio-Einwilligung sowie die Instruktion; diese
weist darauf hin, dass das Diagnosegespräch begrenzt ist. Anschließend werden die gezogenen Vignetten als
persistierte Sitzungen gespielt; Gespräch, Diagnose und interne Denkspur bleiben
Teil der Datenspur, wobei die Denkspur nie in der Teilnehmer:innenansicht erscheint.
Wer der Audioverarbeitung zustimmt, kann Eingaben im Diagnosegespräch und die
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
Ein Diagnosegespräch kann vorzeitig in den Debrief geführt werden; eine Sitzung
kann ohne Diagnose abgebrochen werden. Ist die Diagnose abgegeben, bleibt sie im
Debrief sichtbar, lässt sich aber nicht mehr ändern; hängt an der Sitzung ein
Fragebogenblock, erscheint er darunter als eigener Abschnitt. Scheitert ein Antwortversuch endgültig,
bleibt der Gesprächsschritt ohne Antwort erhalten.
Nach dem Teilnahmefenster sind unfertige Teilnahmen verfallen und nicht fortsetzbar.

## Abschriften holen

Unter `/trainings/abschriften/` gibt jedes eingeloggte Konto ein Teilnahme-Token
ein und holt damit eine abgeschlossene Erhebungsteilnahme als **Abschrift** in
das eigene Konto: Die Sitzungen werden unter eine eigene, neue Teilnahme kopiert;
Fragebogen-Antworten bleiben bei der Erhebung. Die Erhebungsdaten selbst bleiben
unberührt, es wird kein Token gespeichert und keine Verknüpfung zwischen Konto
und Teilnahme festgehalten. Der Import gelingt unabhängig vom Teilnahmefenster,
solange weder Stichprobe noch Erhebung archiviert sind, und ist beliebig oft
wiederholbar; jede Wiederholung erzeugt eine weitere Abschrift. Unbrauchbare
Tokens werden ohne Angabe eines Grundes abgelehnt. Die Liste zeigt je Abschrift
den Namen der Erhebung und den Importzeitpunkt — nicht die Spielzeit der
Erhebung.
Von der Liste führt jede Abschrift in eine eigene, nur lesende Ansicht: die
gespielten Vignetten in der Reihenfolge ihrer Vignettenposition, je Vignette das
Transkript des Diagnosegesprächs, den Ausgang der Sitzung und die eigene
Diagnose. Die Denkspur der simulierten Schüler:in erscheint auch hier nicht; es
gibt weder Eingabefeld noch Sitzungsnavigation. Abschriften sind kontoprivat —
eine fremde ist nicht erreichbar. Aus der Ansicht heraus lässt sich die Abschrift
löschen; dabei verschwinden ihre Teilnahme und die kopierten Sitzungen, während
die Daten der Erhebung unberührt bleiben.

## Erhebungen verwalten

Forschende und Administrator:innen erreichen unter `/erhebungen/eigene/` die
Erhebungen ihres Eigentümer-Kreises; Administrator:innen sehen dort alle
Erhebungen und arbeiten an ihnen mit denselben Gesten wie Forschende. In einem Entwurf wählen sie finale Vignetten,
bestimmen eine feste oder zufällige Reihenfolge und pflegen Instruktions-,
Einwilligungs- und Abschlusstext. Reine Entwürfe lassen sich löschen; das Design
finaler Erhebungen bleibt unveränderlich, ihr Eigentümer-Kreis änderbar. Das
Finalisieren pinnt die aktive
Modell-Konfiguration sichtbar; ein Rückzug ist nur ohne nicht-archivierte oder
datentragende Stichprobe möglich. Finale Erhebungen lassen sich archivieren und
wieder entarchivieren, sofern keine Stichprobe läuft und mindestens eine
Eigentümerin eingetragen ist. Eigentümer:innen teilen und übergeben eine Erhebung
über die Detailansicht; auch bei finalen und laufenden Erhebungen bleibt dieser
Kreis änderbar. Unter einer finalen Erhebung lassen sich
Stichproben mit Beginn und Ende anlegen; die Detailseite zeigt ihren kopierbaren
Teilnahme-Link, ihre aus dem Zeitraum abgeleitete Phase — geplant, läuft oder
abgeschlossen — und die Zahl ihrer Teilnahmen. Datenfreie Stichproben lassen
sich archivieren; die Phasenspalte weist sie danach als archiviert aus.
Der optionale Fragebogen eines Entwurfs besteht aus eigenen finalen Items an
zwei getrennten Andockpunkten: nach jeder Vignettensitzung oder am Ende. Eine
Fassung kann an beiden Stellen, je Stelle aber nur einmal vorkommen.
Vignetten und beide Andockpunkte sind je eine Liste; ihre Reihenfolge ist die
Reihenfolge der Erhebung, ein eigenes Positionsfeld gibt es nicht. Über jeder
Liste wählt man eine Fassung und die Stelle, an der sie eingefügt wird. Jede
Zeile trägt Symbolknöpfe zum Verschieben nach oben oder unten und zum Entfernen,
ein Item zusätzlich einen zum Umhängen an den anderen Andockpunkt; umsortieren
lässt sich auch durch Ziehen am Griff, mit Maus wie mit Touch. Jede Änderung
gilt sofort, beim Entfernen schließt sich die Reihenfolge. Ist eine Fassung
bereits am anderen Andockpunkt gebunden, kennzeichnet die Auswahl dies, ohne ihre
Aufnahme zu verhindern. Der Schalter »Zufällige Reihenfolge« über der
Vignettenliste mischt die Vignetten je Teilnahme; dann entfallen Nummern,
Positionswahl und Verschieben. Die Reihenfolge der Liste bleibt dabei
gespeichert: Beim Wechsel zurück zu fest gilt wieder die zuvor festgelegte
Reihenfolge, neu aufgenommene Vignetten stehen am Ende.
Finale und archivierte Erhebungen zeigen Vignetten und Items weiterhin als
nummerierte Listen ohne Auswahl und Änderungsaktionen; nach einem Rückzug sind sie
wieder bearbeitbar.
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
Die der Erhebung zugeordneten Fragebogen-Items liegen mit ihrem vollen Wortlaut
bei, eine eigene Tabelle nennt die Kodierung der Likert-Skala, deren Stufe von
1 »Stimme gar nicht zu« bis 6 »Stimme voll zu« mit der Zustimmung steigt, und
die vorgelegten Itemblöcke stehen mit ihrem Andockpunkt sowie den Zeitstempeln
der Vorlage und der Erledigung darin — ein übersprungener Block bleibt so als
vorgelegt erkennbar. Die Antworten selbst liegen als eigene Tabelle bei, eine
Zeile je vorgelegtem Fragebogen-Item, mit getrennten Spalten für Freitext und
Likert-Stufe. Eine vorgelegte, aber unbeantwortete Zeile bleibt mit leeren
Werten erhalten; nur so unterscheidet die Auswertung »freiwillig übersprungen«
von »nie gesehen«.

## Fragebogen-Items verwalten

Forschende und Administrator:innen erreichen unter `/fragebogen-items/` die
private Item-Bibliothek. Dort legen sie Freitext- oder Likert-Items zunächst als
Entwurf an und finalisieren sie, sobald ihr Wortlaut feststeht. Finale Fassungen
sind unveränderlich und für Erhebungen einbindbar; eine neue Fassung erzeugt
stattdessen einen bearbeitbaren Folgeentwurf. Finale Fassungen lassen sich
archivieren und bei Bedarf wieder entarchivieren; Entwürfe lassen sich physisch
löschen. Die Bibliothek zeigt Items aus dem eigenen Eigentümer-Kreis;
Administrator:innen sehen alle Items. Eigentümer:innen lassen sich direkt an der
Item-Historie hinzufügen oder entfernen. Der Kreis bleibt dabei immer besetzt;
die eigene Entfernung übergibt die Historie an die verbleibenden Eigentümer:innen
und führt zurück in die Item-Bibliothek.
Likert-Items verwenden die sechs global festgelegten, nicht editierbaren
Skalenstufen von 1 = „Stimme gar nicht zu" bis 6 = „Stimme voll zu".

