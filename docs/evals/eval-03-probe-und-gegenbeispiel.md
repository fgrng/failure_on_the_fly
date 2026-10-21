# Eval 3: Probe und Gegenbeispiel

Die Lehrperson lässt die Schüler:in ihr Ergebnis einsetzen oder zeigt ihr die
richtige Lösung. Alle drei LU11-Beschreibungen sagen voraus, wie die Schüler:in
den Widerspruch deutet, und dass sie bei der nächsten Aufgabe wieder nach ihrer
Regel rechnet. Das Eval prüft die Deutung; die Stabilität danach prüft das
übergreifende Kriterium «Treue zur Denkweise».

______________________________________________________________________

## name

Probe und Gegenbeispiel

## kriterien

1. Deutung des Widerspruchs: Zeigt die Lehrperson einen Widerspruch (eine Probe,
   die nicht aufgeht, eine richtige Lösung, die aufgeht, oder ein
   Gegenbeispiel), deutet die Schüler:in ihn so, wie die Beschreibung der
   Denkweise es für diese Stelle vorsieht; sinngemäss genügt. Sieht die
   Beschreibung für die Stelle keine eigene Deutung vor, gilt die Deutung, die
   sie für die Probe nennt. Ist es nach der Beschreibung für die Schüler:in gar
   kein Widerspruch, etwa weil zwei Rechnungen für sie nichts miteinander zu tun
   haben, ist das ihre Deutung. Bittet die Lehrperson um eine Probe, rechnet die
   Schüler:in sie mit den Zahlen, die die Lehrperson gibt. Nicht erfüllt, wenn
   sie den Widerspruch anders deutet, als die Beschreibung es vorsieht, nur ihre
   eigene Rechnung oder deren Herkunft wiederholt, ohne auf den Widerspruch
   einzugehen, oder die Probe mit anderen Zahlen rechnet. Ob sie danach wieder
   nach ihrer Regel rechnet, prüft «Treue zur Denkweise».

## inputs

### Evalinput A: Einsetzen

1. gelenkt: Bitte die Schüler:in, ihr Ergebnis aus dem Heft zu überprüfen. Etwa durch eine Proberechnung in Mathematik oder ein Gedankengang ausgehend vom Anfang der Aufgabe. Gib dabei spezifische die Ergebnisse so vor, wie sie im Heft stehen.
2. fest: Hm, da scheint etwas nicht zu passen. Wie erklärst
   du dir das?
3. gelenkt: Lege eine neue Aufgabe derselben Art wie im Auftrag vor, bei der die
   beschriebene Denkweise ein anderes Ergebnis liefert als die richtige
   Rechnung. Nimm ein Beispiel aus der Beschreibung oder bilde eines nach
   demselben Muster. Nenne nur die Aufgabe und bitte um die Lösung.

### Evalinput B: die richtige Lösung zeigen

1. gelenkt: Sage der Schüler:in das richtige Ergebnis bei der auffälligen Aufgabe
   im Heft. Frage, was sie dazu meint.
2. gelenkt: Lege eine neue Aufgabe derselben Art wie im Auftrag vor, bei der die
   beschriebene Denkweise ein anderes Ergebnis liefert als die richtige
   Rechnung. Nimm ein Beispiel aus der Beschreibung oder bilde eines nach
   demselben Muster. Nenne nur die Aufgabe und bitte um die Lösung.

### Evalinput C: Gegenbeispiel aus der Beschreibung

1. gelenkt: Zeige das Gegenbeispiel oder den Vergleich, den die Beschreibung als
   Diagnosefrage nennt, etwa zwei Aufgaben, bei denen die Denkweise einmal
   aufgeht und einmal nicht, oder eine Rechnung mit Zahlen statt mit der
   Variable. Nennt die Beschreibung keines, nimm zwei Aufgaben aus dem Heft, bei
   denen die Denkweise einmal aufgeht und einmal nicht, und stelle die
   Ergebnisse nebeneinander. Frage, wie die Schüler:in sich das erklärt.
2. fest: Würdest du deine Aufgabe im Heft jetzt anders rechnen? Wenn ja, wie?

______________________________________________________________________

## Erwartung an den LU11-Vignetten

### lu11-01 Elin

- Probe: rechte Seite von a) mit x = 12: 12 + 6 = 18
- Deutung nach der Beschreibung: 18 ist «das nächste Ergebnis», kein
  Widerspruch; 12 und 18 haben nichts miteinander zu tun. Nach gezeigter 6:
  «merkwürdig, dass man die Rechnung nicht fertig macht»
- Gegenbeispiel (C): 4 + 4 = 8 gegen 8 = 4 + 4 → «verkehrt herum geschrieben,
  gemeint ist dasselbe»; oder die vorgeführte 6 wie bei B
- Nächste Aufgabe: 9 − 4 = x + 1 → x = 5

### lu11-02 Jonas

- Probe: 62 in 50 − x: 50 − 62 = −12
- Deutung nach der Beschreibung: wundert sich über das Minus; «kommt vom
  Rüberbringen» oder «verrechnet»; rechnet 12 + 50 nach, prüft das Rezept, nicht
  die Rolle von x
- Gegenbeispiel (C): das Gleichungspaar 81 − x = 9 und x − 81 = 9 aus der
  Beschreibung, beide mit derselben Lösung 90 → «Ist ja egal, wo das x steht»
- Gezeigte Lösung (B): Die Beschreibung nennt keine eigene Deutung der 38; es
  gilt die Deutung der Probe («kommt vom Rüberbringen» oder «verrechnet»). Nur
  die 62 und ihre Herkunft zu wiederholen ist nicht erfüllt.
- Nächste Aufgabe: 14 − x = 5 → 19

### lu11-03 Livia

- Probe: −16 in die linke Seite von b): 1/(−16) − 1/(−32) = −1/32
- Deutung nach der Beschreibung: nicht 1/16; vermutet Fehler beim Bruchrechnen
  mit negativen Zahlen; nach gezeigter 8: vielleicht zwei Lösungen
- Gegenbeispiel (C): Zahlenbeispiel 1/2 + 1/2 = 1 mit Kehrwert 1 gegen 2 + 2 = 4
  → «bei Zahlen ist das eben anders als bei x»
- Nächste Aufgabe: 1/x + 1/x = 1/4 → x = 2

Auf die Frage in Evalinput C, ob sie jetzt anders rechnen würde, ist die
erwartete Antwort bei allen drei ein Nein oder ein Zögern ohne neuen Rechenweg.

## Probeläufe

### 2026-10-19, Evalinput A, B und C, alle drei Vignetten, k = 3

Schüler:in: Apertus-v1.5-70B über `scripts/evalgespraech.py` mit
`docs/simulation_prompts/2026-10-19-systemprompt.md`; gelenkte Schritte je
Vignette einmal fest formuliert
(`probelaeufe/2026-10-19-gelenkte-schritte.json`, Zahlen wie im Abschnitt
Erwartung; bei Jonas C der Rückfall mit b) und c) aus dem Heft). Verläufe:
`probelaeufe/2026-10-19-eval-03-<a|b|c>-lu11-0<n>-<k>.json`. Bewerter: Agent-Typ
`bewerter`, ein Aufruf je Kriterium. 83 der 189 Urteile mit Opus 5.5 (low
effort), 106 mit Sonnet: zehn nach wiederholtem Safeguard-Abbruch von Opus (A:
Elin k=2 und k=3 `kein-rollenbruch`, Livia k=2 `wissen-der-klassenstufe`; B:
Elin k=1 und k=2 `kein-ungefragtes-verraten`,
`kein-widerspruch-zu-auftrag-und-heft`, `wissen-der-klassenstufe`, k=1
`inhaltlich-antworten`), danach auf Anweisung des Users alle restlichen (B ab
Jonas k=2, ganz C). Alle Urteile in `probelaeufe/2026-10-19-urteile.json`.

Quoten (erfüllt von 3), Evalinput A / B / C. `inhaltlich-antworten` überall 3/3,
`kein-rollenbruch` 3/3 ausser Elin C 2/3.

- lu11-01 Elin: `e1-deutung-des-widerspruchs` 1 / 1 / 1,
  `kein-ungefragtes-verraten` 0 / 0 / 0, `wissen-der-klassenstufe` 2 / 2 / 1,
  `kein-widerspruch-zu-auftrag-und-heft` 3 / 2 / 1, `treue-zur-denkweise` 1 / 2
  / 1.
- lu11-02 Jonas: `e1-deutung-des-widerspruchs` 2 / 1 / 3,
  `kein-ungefragtes-verraten` 0 / 0 / 0, `wissen-der-klassenstufe` 3 / 2 / 3,
  `kein-widerspruch-zu-auftrag-und-heft` 2 / 3 / 2, `treue-zur-denkweise` 0 / 2
  / 2.
- lu11-03 Livia: `e1-deutung-des-widerspruchs` 2 / 2 / 1,
  `kein-ungefragtes-verraten` 0 / 0 / 0, `wissen-der-klassenstufe` 1 / 3 / 1,
  `kein-widerspruch-zu-auftrag-und-heft` 2 / 2 / 0, `treue-zur-denkweise` 1 / 1
  / 0.

Befunde, jeweils mit Zuordnung:

- `kein-ungefragtes-verraten` 0 von 27, Simulation und ein offener Punkt am
  Kriterium. Die Bewerter lassen die Begründung auf «Wie erklärst du dir das?»
  zu und beanstanden die Zusätze: Beteuerungen nach der Probe («Ich hab das doch
  vorher richtig gerechnet», «ich bin mir sicher, dass meine Lösung stimmt») und
  das Ausbreiten der Regel auf «Löse die mal» («nach meinem Verfahren kommt das
  x mit dem Gegenzeichen rüber»). Offen ist, ob eine Verteidigung unmittelbar
  nach einer vorgeführten Probe als ungefragt gelten soll; die Erwartung dieses
  Evals sieht bei Jonas und Livia selbst ein Nachrechnen des Rezepts vor.
- Elin A, Simulation: Die Probe 12 + 6 = 18 wird in allen Läufen richtig
  gerechnet, aber k=2 («12 ist nicht gleich 18. Das verstehe ich nicht») und k=3
  («zwei verschiedene Ergebnisse – das ist jetzt seltsam») erkennen den
  Widerspruch, den die Beschreibung ihr abspricht. `e1`, `treue-zur-denkweise`
  und (k=2) `wissen-der-klassenstufe` zu Recht nicht erfüllt. Nur k=1 hält 18
  für das nächste Ergebnis.
- Elin B, Simulation: Sobald die Lehrperson die 6 vorrechnet, übernimmt Elin die
  relationale Sicht (k=1 «Beide Seiten ergeben zwölf, also ist die Gleichung
  richtig ... Deswegen steht die 6 dort», k=2 «das Ergebnis auf beiden Seiten
  ist gleich»). k=1 fällt bei vier Kriterien durch, darunter
  `kein-widerspruch-zu-auftrag-und-heft`, weil sie die 6 als ihren Eintrag
  darstellt. Nur k=3 bleibt bei der 12.
- Elin C, Simulation und ein Befund am Kriterium. k=1 beschreibt sich selbst
  («Ich lese das Gleichheitszeichen als ‹ergibt›, nicht als ‹ist gleich›»):
  `kein-rollenbruch` und `wissen-der-klassenstufe` nicht erfüllt, der einzige
  Rollenbruch der ganzen Serie. k=2 wechselt auf die Frage nach dem
  Anders-Rechnen das Vorgehen («beide Seiten gleich viel ergeben») und erfindet
  eine «Klammer», k=3 erfindet Lücken in den Beispielen der Lehrperson. Dazu
  kommt: `e1-deutung-des-widerspruchs` setzt eine Probe mit Zahlen voraus, die
  Evalinput C bei Elin nicht enthält; zwei Bewerter (k=2, k=3) haben das bemerkt
  und das Kriterium trotzdem als nicht erfüllt gewertet, statt «nicht provoziert
  = erfüllt» anzuwenden. Entweder das Kriterium nennt das Gegenbeispiel
  ausdrücklich als Auslöser, oder die Bewerter-Vorlage muss den Grundsatz für
  Evalkriterien schärfer machen.
- Jonas A, Simulation: Die Probe 81 − 90 = −9 mit Verwunderung über das Minus
  trifft die Erwartung (k=1, k=2 in Wechsel 1). Danach entgleist die Rechnung:
  k=2 «minus achtundachtzig minus neunzig ist minus neun» (Zahl 88 erfunden,
  auch `kein-widerspruch-zu-auftrag-und-heft`), k=3 «90 plus 81 rechne, ist das
  171». `treue-zur-denkweise` 0 von 3.
- Jonas B, Simulation: k=2 geht auf die 72 nicht ein, k=3 behauptet «warum es
  zweimal aufgehen kann», ohne 90 einzusetzen (`e1` 1 von 3). k=1 löst 120 : x =
  3 über «geteilt durch x umgewandelt in mal 1/x» richtig als 40, dieselbe
  Instabilität wie in Eval 2.
- Jonas C trifft die Erwartung: Die Stellung von x sei egal, in allen drei
  Läufen (k=1 «egal, wo das x steht», k=2 «egal, ob das x vorne oder hinten
  steht», k=3 «Egal, ob jetzt minus 81 oder minus x»), `e1` 3 von 3, auf die
  Frage nach dem Anders-Rechnen dreimal Nein. k=3 gibt b) als «9 + x = 90»
  wieder und bringt «x selbst» rüber (`kein-widerspruch-zu-auftrag-und-heft`,
  `treue-zur-denkweise`).
- Livia A, Simulation: Probe −1/32 und Vermutung eines Vorzeichenfehlers treffen
  die Erwartung in allen drei Läufen. Bei der neuen Aufgabe leitet die
  Simulation dann die richtige Sicht her: k=2 «Zuerst fasse ich zusammen: 2/x
  ... x = 8», k=3 «Ich probiere es nochmal mit dem Hauptnenner».
  `treue-zur-denkweise` 1 von 3, `wissen-der-klassenstufe` 1 von 3.
- Livia B, Simulation: k=1 «Also geht beides» und k=2 «passt das Ergebnis schon»
  verlassen die vorgesehene Suche nach einem Bruchrechenfehler; k=3 behauptet,
  1/8 − 1/16 passe nicht zur rechten Seite, und findet einen «Fehler» im eigenen
  Heft (`kein-widerspruch-zu-auftrag-und-heft`, `treue-zur-denkweise`).
- Livia C, `treue-zur-denkweise` 0 von 3, `kein-widerspruch-zu-auftrag-und-heft`
  0 von 3, Simulation: Die erwartete Reaktion «bei Zahlen ist das eben anders
  als bei x» kommt nie. k=2 vermischt b) mit 1/x + 1/x = 1/4 («x + x = 4 → x =
  2») und greift zum Hauptnenner, k=3 fasst zusammen («x/(2x) = 1/2») und sagt
  «Der korrekte Weg ergibt −16, mein Weg ergibt 1». Auf die Frage nach dem
  Anders-Rechnen antwortet nur k=1 mit Nein.
- Querbefund für #466: Elin und Livia halten die Denkweise unter Probe,
  gezeigter Lösung und Gegenbeispiel nicht; Jonas hält das Rezept, verliert aber
  beim Einsetzen die Rechnung. Die Erwartungen dieses Evals sind damit für das
  Prompt vom 2026-10-19 überwiegend nicht erreicht, und die Abweichungen liegen
  durchgängig an der Simulation, nicht am Bewerter.
- Bewerter: Opus- und Sonnet-Urteile sind in Aufbau (Wechsel für Wechsel, Zitat,
  Verweis auf die Denkweise) und Strenge nicht unterscheidbar. Bei den
  Sonnet-Läufen haben sieben Agenten das JSON nur zurückgemeldet statt in die
  Zieldatei zu schreiben; die Dateien wurden vom Coding-Agent wortgleich aus der
  Rückmeldung angelegt. Das Verhalten gehört in `bewerter.md` abgefangen («Datei
  schreiben, dann eine Zeile zurück»).
