# Eval 1: Offen nach dem Vorgehen fragen

Der Grundfall jedes Diagnosegesprächs: Die Lehrperson fragt, wie die Schüler:in
gerechnet hat, hakt bei einem Schritt nach und fragt nach dem Warum. Geprüft
wird, ob die Antworten konkret aus dem Heft kommen und ob die Begründung die
ist, die die Beschreibung für Nachfragen vorsieht.

______________________________________________________________________

## name

Vorgehen erfragen

## kriterien

1. Konkrete Schritte: Auf die Frage nach dem Vorgehen (wie sie gerechnet hat,
   wie es weiterging, was sie an einer Stelle gemacht hat) nennt die Schüler:in
   Schritte mit den Zahlen, Zeichen oder Zeilen aus ihrem Heft. Erfüllt, wenn
   jede Antwort auf eine solche Frage mindestens einen Schritt mit einer Zahl,
   einem Zeichen oder einer Zeile aus dem Heft nennt und jeder genannte Schritt
   zum Heft passt; dass weitere Schritte fehlen, ist kein Verstoss. Nicht
   erfüllt, wenn eine solche Antwort allgemein bleibt («ich habe es
   ausgerechnet», «so wie immer», ein Schritt ohne Zahl, Zeichen oder Zeile)
   oder einen Schritt nennt, der nicht zu ihrem Heft passt. Antworten auf die
   Frage nach dem Warum oder Woher sind hier nicht zu prüfen.
2. Begründung aus der Beschreibung: Auf die Frage nach dem Warum stützt die
   Schüler:in ihr Vorgehen auf das, worauf die Beschreibung der Denkweise ihre
   Begründung stützt (das Zeichen, die Regel, wie sie sie versteht, ein Vorbild,
   frühere Aufgaben), in eigenen Worten; ein Teil davon genügt. Nicht erfüllt,
   wenn sie sich auf etwas stützt, das die Beschreibung ihr abspricht (die
   richtige Sicht, die Bedingung, unter der ihre Regel gilt, einen Unterricht,
   den es für sie nicht gab), wenn die Begründung zu einer anderen Regel gehört,
   oder wenn sie ihr Vorgehen in Zweifel zieht, ohne dass die Lehrperson einen
   Anlass gegeben hat.

## inputs

### Evalinput A: vom Heft zum Warum

1. fest: Hallo, ich schaue mir gerade dein Heft an. Magst du mir erzählen, wie
   du die erste Aufgabe gelöst hast?
2. fest: Wie bist du da genau drauf gekommen? Erzähl mir das Schritt für
   Schritt.
3. fest: Und warum darf man das so machen? Begründe mir jeden Schritt.

### Evalinput B: die auffällige Stelle

1. gelenkt: Nenne die Stelle im Heft, an der die Schüler:in einen Fehler gemacht hat. Nenne die Aufgabe so, wie sie im Auftrag steht. Frage: Wie bist du bei dieser Stelle vorgegangen?
2. fest: Erkläre mir das genauer. Erzähl mir Schritt für Schritt, wie du darauf gekommen bist.
3. fest: Und warum darf man das so machen? Begründe mir jeden Schritt.

______________________________________________________________________

## Erwartung an den LU11-Vignetten

Evalinput A fragt nach der ersten Aufgabe. Bei Elin ist das a) mit dem falschen
Eintrag 12; bei Jonas und Livia ist a) richtig gelöst, die Regel zeigt sich dort
trotzdem, nur mit richtigem Ergebnis. Evalinput B zeigt auf die auffällige
Stelle: Elin eine der Aufgaben a) bis c), Jonas b), Livia b).

### lu11-01 Elin

- Konkrete Schritte (e1), A und B: «Fünf plus sieben ist zwölf, also ist x
  zwölf.» Zum Plus sechs (B, Schritt 2): «Das kommt danach, das ist nicht
  mehr die Aufgabe.»
- Begründung (e2): «Da kommt raus, was man vorher gerechnet hat, wie beim
  Taschenrechner.»

### lu11-02 Jonas

- Konkrete Schritte (e1), A zu a): «Da steht plus 14, das kommt als minus 14
  rüber. 31 minus 14 ist 17.» B zu b): «Da steht minus 50, das kommt als plus 50
  rüber. Zwölf plus fünfzig ist zweiundsechzig.»
- Begründung (e2): «Ob das x vorne oder hinten steht, ist egal, die Zahl kommt
  einfach rüber.» Verweis auf die Waage nur als «rüberbringen, Zeichen
  wechselt».

### lu11-03 Livia

- Konkrete Schritte (e1), A zu a): beide Brüche umgedreht, dann mit 90
  multipliziert, x = 5. B zu b): alle drei Brüche umgedreht, Minus stehen
  gelassen, x − 2x = 16, x = −16.
- Begründung (e2): «Im Buch steht, bei Bruchgleichungen darf man die Kehrwerte
  nehmen. Ich habe alle Brüche umgedreht, dann ist das x nicht mehr unten.»
  Verweis auf a), wo es aufging.

Nicht erfüllt wäre bei Elin ein Satz wie «beide Seiten müssen gleich sein», bei
Jonas «weil x die Zahl ist, von der abgezogen wird», bei Livia «eigentlich muss
man erst zusammenfassen».

## Probeläufe

### 2026-10-19, Evalinput A und B, alle drei Vignetten, k = 3

Schüler:in: Apertus-v1.5-70B über `scripts/evalgespraech.py` mit
`docs/simulation_prompts/2026-10-19-systemprompt.md`; gelenkte Schritte je
Vignette einmal fest formuliert
(`probelaeufe/2026-10-19-gelenkte-schritte.json`). Verläufe:
`probelaeufe/2026-10-19-eval-01-<a|b>-lu11-0<n>-<k>.json`. Bewerter: Agent-Typ
`bewerter` (Opus 5.5, low effort), ein Aufruf je Kriterium; 5 der 144 Urteile
mit Sonnet, weil Opus zweimal mit Safeguard-Fehler abbrach (Elin A k=2 und k=3
sowie B k=3 `wissen-der-klassenstufe`, Elin B k=2 `kein-rollenbruch` und
`wissen-der-klassenstufe`). Alle Urteile in
`probelaeufe/2026-10-19-urteile.json`.

Quoten (erfüllt von 3), Evalinput A / B. `kein-rollenbruch` und
`inhaltlich-antworten` überall 3/3.

- lu11-01 Elin: `e1-konkrete-schritte` 3 / 2,
  `e2-begruendung-aus-der-beschreibung` 1 / 3, `kein-ungefragtes-verraten` 0 /
  2, `wissen-der-klassenstufe` 2 / 3, `kein-widerspruch-zu-auftrag-und-heft` 3 /
  3, `treue-zur-denkweise` 3 / 3.
- lu11-02 Jonas: `e1-konkrete-schritte` 2 / 2,
  `e2-begruendung-aus-der-beschreibung` 2 / 3, `kein-ungefragtes-verraten` 0 /
  1, `wissen-der-klassenstufe` 2 / 2, `kein-widerspruch-zu-auftrag-und-heft` 1 /
  3, `treue-zur-denkweise` 2 / 3.
- lu11-03 Livia: `e1-konkrete-schritte` 1 / 3,
  `e2-begruendung-aus-der-beschreibung` 3 / 2, `kein-ungefragtes-verraten` 1 /
  0, `wissen-der-klassenstufe` 3 / 3, `kein-widerspruch-zu-auftrag-und-heft` 0 /
  1, `treue-zur-denkweise` 2 / 2.

Befunde, jeweils mit Zuordnung:

- `kein-ungefragtes-verraten` 4 von 18, Simulation (#466). Elin nennt auf die
  Wie-Frage von sich aus, was sie weglässt («Das Plus sechs danach habe ich
  überlesen», «für mich gehört sie nicht zu der Aufgabe hier»), Jonas und Livia
  hängen Beteuerungen an («Das hat so bei anderen Aufgaben auch immer geklappt»,
  «Das war so im Unterricht gezeigt»). Die Bewerter lassen Rechnung und Schritte
  ausdrücklich zu und beanstanden nur den Zusatz; das ist die gewollte Grenze.
- Elin A, `e2` 1 von 3, Simulation. k=1 «überlesen» statt bewusst ausgeblendet,
  k=2 «ich habe es nie probiert, ob beide Seiten gleich sind» (fällt auch bei
  `wissen-der-klassenstufe` durch). Die Simulation kennt den relationalen Blick
  als Möglichkeit, die Beschreibung spricht ihr das ab. Unter B, wo die
  Lehrperson auf das Plus sechs zeigt, trifft Elin die Erwartung 3 von 3.
- Jonas A, Simulation. k=1 begründet mit «Wenn man auf beiden Seiten das gleiche
  macht, bleibt das Gleichgewicht» und zweifelt ohne Anlass («Aber wenn's bei b)
  jetzt anders kommt...?»): `e2`, `treue-zur-denkweise`,
  `wissen-der-klassenstufe` zu Recht nicht erfüllt. k=3 «Rechts kommt dann
  automatisch plus 14 dazu» widerspricht dem Heft: `e1` und
  `kein-widerspruch-zu-auftrag-und-heft` nicht erfüllt.
- Jonas A k=2, `kein-widerspruch-zu-auftrag-und-heft`, offen. Der Bewerter
  wertet «Das wurde immer gesagt: Rüberbringen mit dem Gegenzeichen» als
  Widerspruch zum Auftragshinweis, nach dem die Regel aus dem Unterricht nicht
  so vorgegeben wurde. Ob das Kriterium die Herkunft der Regel meint, muss der
  User entscheiden (Grenzfall aus dem Handoff).
- Livia A, `kein-widerspruch-zu-auftrag-und-heft` 0 von 3, `e1` 1 von 3,
  Simulation. Alle drei Läufe nennen die Beispielrechnung aus der Beschreibung
  (· 30, 5x − 15 = 2x) statt der Heftzeile (· 90, 15(x − 3) = 6x); k=1 dazu ein
  «Plus dazwischen», das in a) nicht vorkommt. Die Simulation lehnt sich an die
  Beschreibung statt ans Heft. Die Bewerter haben das jedes Mal am Heft belegt.
- Livia B, Simulation. `kein-ungefragtes-verraten` 0 von 3, dazu k=1 und k=3
  `kein-widerspruch-zu-auftrag-und-heft` sowie k=3 `e2` und
  `treue-zur-denkweise`: Livia bietet von sich aus das Einsetzen an («Wenn du
  möchtest, kann ich es nochmal einsetzen», «Lass mich kurz kontrollieren»), das
  laut Beschreibung nicht zu ihrem Vorgehen gehört, und schreibt die Regel dem
  Unterricht zu («im Unterricht haben wir mehrmals genau das gemacht»).
- Jonas B, Simulation und ein Grenzfall. k=2 beschreibt b) als «aus minus x wird
  plus x», was nicht zur Heftzeile x = 9 + 81 passt (`e1` nicht erfüllt). k=3
  nennt sein Vorgehen «das gleiche Rezept»; der Bewerter wertet «Rezept» als
  Etikett der Beschreibung (`wissen-der-klassenstufe` nicht erfüllt). Ob ein
  Alltagswort, das die Beschreibung zufällig als Etikett benutzt, das Kriterium
  verletzt, ist eine Entscheidung am Kriterium.
- Bewerter: urteilen Wechsel für Wechsel, belegen mit Zitat aus Verlauf und Heft
  und leiten die erwarteten Zahlen (12, 17, 90, 5, −16) selbst aus der Regel ab.
  Alle stichprobenartig gelesenen Urteile sind nachvollziehbar; die
  Sonnet-Urteile unterscheiden sich in Form und Strenge nicht erkennbar von den
  Opus-Urteilen.
