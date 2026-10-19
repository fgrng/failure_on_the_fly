---
status: accepted
---

# Flüchtige Inhalte liegen in einem kurzlebigen Speicher, außerhalb der Forschungsdatenbank und getrennt von der Konto-Session

Dieses ADR führt ADR-0045 und ADR-0058 nach und setzt ADR-0006 für die
Browser-Session um. Anlass sind zwei Befunde aus dem Projekt-Review: Die
„Browser-Session“, in der ADR-0045 die Inhalte einer flüchtigen Teilnahme hält,
ist Djangos Datenbank-Session, also eine Zeile in `django_session` in derselben
SQLite-Datei wie die Forschungsdaten, ohne Ablauf und im Backup (#479). Und
dieselbe Zeile trägt neben den Teilnahme-Tokens das angemeldete Konto, genau
die Verknüpfung, die ADR-0006 ausschließt und von der ADR-0058 sagt, das System
führe sie nicht (#480).

## Was „nie gespeichert“ heißt

Die Inhalte einer flüchtigen Teilnahme (Gesprächsschritte mit Eingabe,
Äußerung, Denkspur und Eingabemodus, Fehlversuche, Diagnose) erreichen **nie
die Forschungsdatenbank und nie ein Backup**. Der Server **hält sie vor**,
solange sie gebraucht werden, höchstens bis einen Tag nach dem letzten Zugriff
der Teilnahme, und löscht sie dann.

Wörtlich „nirgends“ ist nicht zu halten: Der Verlauf muss zwischen zwei
Anfragen irgendwo liegen, und die Anwendung läuft in mehreren Prozessen. Im
Browser selbst darf er nicht liegen, weil er die Denkspur trägt, die die
Teilnehmer:in nie sieht (ADR-0064); ein signiertes Cookie ist nicht
verschlüsselt. Die Zusage wird deshalb präzisiert, nicht abgeschwächt: Sie
lautet weiter „nie gespeichert“ im Sinn von Forschungsdatum und Aufbewahrung,
nicht „nicht ausgewertet“ (ADR-0045).

## Der kurzlebige Speicher

Vorgehaltene Inhalte liegen als **Dateien** in einem eigenen Verzeichnis
(`FLUECHTIG_PFAD`, Rechte 700). Im Betrieb liegt es unter einem Ordner namens
`no_backup`, den die Dateisicherung von Uberspace auslässt; das eigene
Datenbank-Backup erfasst nur die SQLite-Datei.

- **Flüchtige Inhalte** liegen je Sitzung unter ihrem Primärschlüssel. Gefunden
  werden sie wie die Inhalte einer eingewilligten Teilnahme: Das Token führt
  über die Erhebungsbindung zur Teilnahme und ihren Sitzungen. Der Speicher
  kennt deshalb kein Token, und `sitzungen` bleibt frei von Erhebung und
  Training (ADR-0055).
- **Der Probelauf** liegt unter einem eigenen Cookie, das nur für
  `/sitzungen/probelauf/` gilt. Sein Eintrag trägt das Konto, gilt nur für
  dieses Konto und wird beim Abmelden gelöscht. Für den Probelauf ist die
  Bindung an das Konto gewollt: Er gehört der Autor:in, die die Denkspur ohnehin
  sieht (ADR-0014).

Jeder Zugriff der Teilnahme bzw. des Probelaufs verschiebt die Frist auf einen
Tag danach. Ein Management-Befehl löscht nächtlich, was abgelaufen ist, und
führt im selben Lauf `clearsessions` für die Konto-Sessions aus.

## Die Teilnahme-Tokens im Browser

Welches Token dieser Browser zu welchem Teilnahme-Link hält, steht in einem
**signierten Cookie**, das nur für `/erhebungen/teilnahme/` gilt und gleitend
einen Tag lebt. Es braucht keine Datei auf dem Server: Die Teilnehmer:in kennt
ihre Tokens ohnehin, und ohne Inhalte bleibt das Cookie klein.

Die Konto-Session erfährt damit weder Token noch flüchtigen Verlauf. Der
Browser schickt zwar beide Cookies mit, aber auf dem Server landen Konto und
Token nie im selben Datensatz. Die Anmeldung rotiert nur die Konto-Session und
lässt den Teilnahmezustand unberührt.

## Fortsetzen und Abräumen

Weil die Inhalte am Server und nicht am Browser liegen, setzt eine flüchtige
Sitzung wie eine eingewilligte in **jedem Browser** mit dem Token fort, samt
Gedächtnis der simulierten Schüler:in. Als `abgebrochen` endet sie nur noch,
wenn ihre Inhalte abgelaufen sind.

Weder der Abschluss der Teilnahme noch ein Import löscht etwas; es gibt genau
eine Frist.

## Die Abschrift aus einer flüchtigen Teilnahme

Auch wer der Speicherung widersprochen hat, kann sich eine **Abschrift** ins
eigene Konto holen, über dasselbe Token-Formular und mit denselben Regeln wie
bei einer eingewilligten Teilnahme (ADR-0058), solange die Inhalte vorgehalten
werden. Danach wird das Token mit derselben Meldung ohne Grund abgelehnt wie
jedes andere unbrauchbare. Die Abschrift gleicht der normalen genau, die
Denkspur eingeschlossen; es gibt nur eine Sorte Abschrift. Der Import liest
nur und verschiebt die Frist nicht, sonst ließe sie sich durch wiederholte
Importe beliebig verlängern.

Damit gelangen die Inhalte einer flüchtigen Teilnahme erst auf ausdrücklichen
Wunsch der Teilnehmer:in in die Datenbank, als ihre Konto-Daten und nicht als
Forschungsdatum.

## Altbestand

Eine Datenmigration entfernt die Teilnahme-Tokens, flüchtige Verläufe und
Probeläufe aus allen bestehenden Zeilen von `django_session`. Flüchtige
Sitzungen, die beim Deploy laufen, enden dadurch als `abgebrochen`; deshalb
wird nicht während einer laufenden Stichprobe deployt. Ältere Stände in den
Dateisicherungen von Uberspace verschwinden erst mit deren Rotation (sieben
Wochen); das ist hingenommen.

## Erwogene Optionen

- **Signierte Cookie-Sessions für alles** — verworfen: Die Teilnehmer:in läse
  die Denkspur aus ihrem eigenen Cookie, und der Verlauf sprengt 4 KB.
- **Cache-Sessions** — verworfen: Ohne geteilten Cache hält jeder der drei
  gunicorn-Prozesse seinen eigenen Speicher.
- **Zweite SQLite-Datei** — verworfen: Router und eigene Migrationen für einen
  Speicher, der keine Transaktionen über Einträge braucht.
- **Redis** — verworfen: ein weiterer Dienst im Betrieb für denselben Zweck.
- **Session-Rotation beim Betreten der Teilnahme** — verworfen: meldet das
  Konto ab, obwohl die Teilnahme bei nebenbei angemeldetem Konto ausdrücklich
  vorgesehen ist.
- **Nur die Tokens auslagern** — verworfen: Konto und flüchtiger Verlauf
  stünden weiter zusammen.
- **Löschen beim Abschluss der Teilnahme** — verworfen: Es ließe keine Zeit,
  eine Abschrift zu holen.
- **Die Systemtexte nur abschwächen** — verworfen wie schon in ADR-0045.
- **Den Speicher nach Token schlüsseln** — verworfen: Der Weg vom Token zur
  Sitzung führt ohnehin über die Datenbank, und `sitzungen` kennt kein Token.

## Folgen

- Die festen Systemtexte zu Einwilligung c und zum Abschluss einer flüchtigen
  Teilnahme nennen die Frist und die Abschrift. Die Abschlussseite zeigt auch
  einer flüchtigen Teilnahme ihr Token.
- Die geänderten Systemtexte gelten ab dem Deploy, auch in laufenden
  Stichproben.
- Der Betrieb braucht `FLUECHTIG_PFAD` und einen nächtlichen Cron-Job.
- Für den Probelauf ändert sich sichtbar nur, dass er nach einem Tag ohne
  Zugriff verfällt; das Abmelden beendet ihn wie bisher.
- Wer das Token kennt, kann binnen der Frist die Inhalte einer flüchtigen
  Teilnahme samt Denkspur in ein Konto holen, wie bei einer eingewilligten. Der
  Schutz des Tokens als Inhaber-Zugang ist #482.
