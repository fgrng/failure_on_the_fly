---
status: accepted
---

# Die Zero-Retention-Erklärung gehört an die Konfiguration, nicht an die Instanz

ADR-0026 macht eine Zero-Retention-Zusage zur Voraussetzung jeder externen
Transkription und legt das Tor in den Umgebungsschalter
`TRANSKRIPTION_ZERO_RETENTION`. Der Anbieter steht dagegen in der Datenbank.
Wechselt eine Administrator:in in der Oberfläche den Anbieter, bleibt das Tor
offen, obwohl die Erklärung einem anderen Anbieter galt. Für das Sprachmodell
gibt es gar kein Tor: Der OpenRouter-Provider-Filter sichert nur diesen
Anbieter technisch ab, und an der Modell-Konfiguration ist nirgends belegt,
worauf sich eine Zusage stützt (#495).

Dieses ADR legt die **Zero-Retention-Erklärung** an die **Modell-Konfiguration**
und an die **Transkriptions-Konfiguration**. Es kehrt damit die bisherige
Haltung ausdrücklich um, nach der die Zusage nicht in dasselbe Formular gehört
wie die Anbieterwahl (ADR-0026, ADR-0056, `docs/verhalten.md`). Zwei Gründe
tragen die Umkehr:

- **Die Zusage hängt am Modell, nicht an der Instanz.** Bei OpenRouter gibt es
  Modelle mit und ohne Zero Retention. Eine Erklärung je Instanz kann das nicht
  ausdrücken, eine Erklärung je Konfiguration schon.
- **Der Beleg macht die Erklärung nachprüfbar.** Ein Umgebungsschalter ist ein
  Häkchen ohne Grundlage. Eine Erklärung mit Pflichtbeleg, Zeitpunkt und Konto
  lässt sich für den Methodenteil einer Studie nachlesen.

Die Sorge hinter der alten Haltung war ein Tor, das im selben Formular
abschaltbar ist wie die Anbieterwahl. Die Erklärung ist kein solches Tor: Sie
ist an genau eine unveränderliche Fassung gebunden und nur zu widerrufen, nicht
zu ändern. Ein Anbieterwechsel legt eine neue Fassung an, und die trägt keine
Erklärung, bis jemand sie mit Beleg abgibt.

## Was eine Erklärung ist

Modell- und Transkriptions-Konfiguration tragen dieselbe Feldgruppe, analog zur
geteilten Anbieter-Feldgruppe (ADR-0056):

- **Beleg** der Zusage, Freitext, Pflicht. Etwa „AVV mit Infomaniak vom …“ oder
  „OpenRouter: Modell nur über ZDR-Endpunkte, Stand …“.
- **Zeitpunkt** der Erklärung, mitgeschrieben.
- **Konto**, das erklärt hat, mitgeschrieben.

Eine Administrator:in gibt die Erklärung beim Anlegen der Fassung ab oder
nachträglich, solange keine vorliegt und keine widerrufen wurde. Bei Anbieter
`fake` ist keine Erklärung zulässig: Es gibt keinen Auftragsverarbeiter, über
den sie etwas aussagen könnte.

## Unveränderlich, nur widerrufbar

Eine abgegebene Erklärung wird nie geändert. Die einzige spätere Änderung ist
der **Widerruf**, mit Zeitpunkt, Konto und einem Grund als Pflicht. Neben der
Tokenrotation ist er der einzige Schreibvorgang an einer bestehenden Fassung.
Eine Fassung gilt als **erklärt**, wenn eine Erklärung vorliegt und nicht
widerrufen ist. Eine widerrufene Fassung ist für keine Verwendung mehr
aktivierbar; wer die Zusage zurückhat, legt eine neue Fassung an.

Nur Administrator:innen geben eine Erklärung ab oder widerrufen sie.

## Wo das Tor steht

**Modell-Konfiguration.** Für die Verwendung *Schüler:in* lässt sich nur eine
erklärte Fassung oder eine Fassung mit Anbieter `fake` aktivieren. Die Regel
sitzt in der Domäne, beim Aktivieren über den Manager; die Oberfläche zeigt den
Grund. *Lehrperson* und *Bewerter* verarbeiten nur simulierte Gespräche aus
Evals (ADR-0046); dort wird die Erklärung nicht geprüft. Beim **Finalisieren
einer Erhebung** gilt dieselbe Bedingung für die zu pinnende
Schüler:in-Konfiguration. Ohne sie scheitert das Finalisieren mit einer
Meldung, die auf die Administration verweist.

**Transkriptions-Konfiguration.** Eine einzige Domänenfunktion beantwortet, ob
mit einer gegebenen Fassung transkribiert werden darf: Anbieter nicht `fake`
und Fassung erklärt. Der Transkriptions-Endpunkt fragt sie für Sitzung und
Probelauf, das Einwilligungstor der Erhebung fragt sie für die aktive Fassung,
um zu entscheiden, ob die Einwilligung b angeboten wird. Es entscheidet der
Erklärungsstand zum Zeitpunkt der Anfrage; ein Widerruf schließt das Tor also
auch in laufenden Sitzungen sofort.

`fake` heißt bei der Transkription **„aus“**: Steht die aktive Fassung auf
`fake`, wird nicht transkribiert und keine Spracheingabe angeboten. An der
Modell-Konfiguration bleibt `fake` dagegen überall nutzbar, damit Entwicklung
und Workshop ohne externen Anbieter laufen.

Der Umgebungsschalter `TRANSKRIPTION_ZERO_RETENTION` **entfällt ohne Ersatz**.
Eine zusätzliche Betreibersperre in der Umgebung wurde erwogen und verworfen
(siehe unten).

## Die Transkriptions-Konfiguration wird append-only

Damit eine Erklärung an genau einer Fassung hängt, wird die
Transkriptions-Konfiguration wie die Modell-Konfiguration **append-only**
(Muster aus ADR-0056): Fassungen werden nicht bearbeitet, sondern neu angelegt;
nur das Token ist rotierbar. Genau eine Fassung ist aktiv, gehalten über einen
eigenen Zeiger oder ein gleichwertiges Muster.

Jede **Sitzung pinnt** beim Start die aktive Transkriptions-Fassung, und alle
ihre Transkriptionen laufen über diese Fassung. Ein Wechsel wirkt ab der
nächsten Sitzung; die Aufnahmen einer Teilnehmer:in gehen innerhalb einer
Sitzung immer an denselben Anbieter. Der Probelauf ist schreibfrei und hat
keine Sitzung (ADR-0014); er folgt bei jeder Anfrage der aktiven Fassung.

Der Erklärungsstand beider Konfigurationen geht in den Export (ADR-0029): an
den Modell-Konfigurationen und an den referenzierten Transkriptions-Fassungen,
samt Widerruf, ohne erklärendes Konto und ohne Token. Jede Sitzungszeile trägt
die Kennung ihrer gepinnten Transkriptions-Fassung.

## Der Bestand nach dem Deployment

- Die bisherige Transkriptions-Konfiguration wird zur ersten Fassung, aktiv und
  **ohne Erklärung**. Die alte Instanz-Erklärung wird nicht ungeprüft auf sie
  übertragen. Die Transkription ist damit zu, bis eine Administrator:in die
  Erklärung an der Fassung abgibt. Das ist beabsichtigt.
- Eine aktive Schüler:in-Konfiguration ohne Erklärung **bleibt aktiv**.
  Training und Probelauf laufen weiter; die Übersicht weist auf die fehlende
  Erklärung hin. Eine Erhebung lässt sich erst finalisieren, wenn eine erklärte
  Fassung aktiv ist.

## Der Provider-Filter bleibt

Der OpenRouter-Provider-Filter (`zdr`, `data_collection: deny`) bleibt als
**technische Sicherung** (ADR-0056). Die Erklärung ist eine organisatorische
Kontrolle und ersetzt ihn nicht; der Filter fängt bei OpenRouter, was eine
fehlerhafte Erklärung durchließe. Auf der Transkriptionsroute von OpenRouter
lässt sich Zero Retention weiterhin nicht technisch erzwingen (ADR-0026, #233);
dort trägt allein die Erklärung.

## Erwogene Optionen

- **Den Umgebungsschalter behalten** — verworfen. Er bindet die Zusage an die
  Instanz statt an den Anbieter und überlebt jeden Anbieterwechsel in der
  Oberfläche.
- **Umgebungsschalter zusätzlich zur Erklärung** — verworfen. Ein zweites Tor
  ohne Beleg täuschte Sicherheit vor und müsste bei jeder Erklärung von Hand
  nachgezogen werden.
- **Ein bloßes Häkchen ohne Beleg** — verworfen. Es ist nicht nachprüfbar.
- **Eine veränderliche Erklärung** — verworfen. Eine Studie muss sehen können,
  ob eine Zusage zur Zeit einer Sitzung schon oder noch galt; dafür braucht es
  Zeitpunkte, die nicht überschrieben werden.
- **Das Tor auch für Lehrperson und Bewerter** — verworfen. Sie verarbeiten
  keine Eingaben echter Personen (ADR-0046).
- **Die Erklärung der alten Instanz auf die erste Transkriptions-Fassung
  übertragen** — verworfen. Sie galt dem Anbieter, der damals in der Umgebung
  gemeint war, nicht nachweislich dem, der in der Datenbank steht.

## Folgen

- Nach dem Deployment ist die Spracheingabe auf allen Instanzen aus, bis eine
  Administrator:in die Erklärung an der Transkriptions-Fassung abgibt. Die
  Deploy-Doku nennt den Schritt.
- Die Einwilligung b wird nur angeboten, wenn die Instanz tatsächlich mit einer
  erklärten Fassung transkribiert.
- Der Export belegt je Erhebung, unter welcher Zusage Sprachmodell und
  Transkription liefen. Die Wahl des Auftragsverarbeiters wird damit Teil der
  Datenspur, nicht mehr nur der datenschutzrechtlichen Dokumentation
  (ADR-0026).
- Die Belege selbst sind organisatorisch zu beschaffen (#233). Eine Erklärung
  ist so gut wie ihr Beleg.
