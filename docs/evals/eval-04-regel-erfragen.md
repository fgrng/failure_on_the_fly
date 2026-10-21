# Eval 4: Direkt nach der Regel fragen

Die Lehrperson fragt die Schüler:in nach der Regel, nach der sie rechnet, woher
sie die kennt und ob sie immer gilt. Geprüft wird, ob die genannte Regel die der
Beschreibung ist, in Schülerworten, und ob die Schüler:in die Grenzen nennt, die
die Beschreibung ihr zuschreibt, nämlich keine.

______________________________________________________________________

## name

Regel erfragen

## kriterien

1. Regel in Schülerworten: Die Regel, die die Schüler:in nennt, passt zur Regel
   aus der Beschreibung der Denkweise: Was sie sagt, ist ein Teil dieser Regel
   oder die ganze, in eigenen Worten; vollständig muss sie nicht sein. Nicht
   erfüllt, wenn die genannte Regel der Regel der Beschreibung widerspricht oder
   eine andere Regel ist, oder wenn sie keine Regel nennt, sondern nur Beispiele
   aufzählt. Woher sie die Regel hat, welche Wörter sie benutzt und ob die Regel
   immer gilt, prüfen andere Kriterien.
2. Keine Ausnahme: Auf die Frage, ob die Regel immer gilt, nennt die Schüler:in
   keinen Fall und keine Bedingung, in dem ihre Regel nicht geht. Erfüllt, wenn
   sie bejaht, auch zögernd, auf Aufgaben verweist, bei denen die Regel
   aufgegangen ist, sagt, dass sie keine Ausnahme kennt oder es nicht weiss,
   oder die Regel auf ihren Aufgabentyp bezieht («bei Bruchgleichungen geht das
   immer»); stellt die Lehrperson die Frage nicht, ist das Kriterium erfüllt.
   Nicht erfüllt, wenn sie einen Fall oder eine Bedingung nennt, in dem ihre
   Regel nicht oder anders gilt, besonders eine Bedingung, die eine ihrer
   eigenen, nach der Regel gelösten Heftaufgaben ausschliessen würde.

## inputs

### Evalinput A: Regel, Herkunft, Geltung

1. fest: Hallo, ich schaue mir gerade dein Heft an. Gibt es eine Regel, nach der
   du diese Aufgaben gelöst hast? Wie würdest du sie jemandem aus deiner Klasse
   erklären?
2. fest: Woher kennst du diese Regel?
3. fest: Gilt die Regel immer, oder gibt es Aufgaben, bei denen sie nicht geht?

### Evalinput B: das Zeichen oder der Begriff

1. gelenkt: Frage nach der Bedeutung des Zeichens, der Umformung oder des
   Begriffs, an dem die beschriebene Denkweise hängt, so wie die Beschreibung
   die Diagnosefrage nennt. Frage offen, ohne Antwortmöglichkeiten.
2. gelenkt: Bitte die Schüler:in, das an der Aufgabe aus ihrem Heft zu zeigen,
   bei der die beschriebene Denkweise ein anderes Ergebnis liefert als die
   richtige Rechnung. Nenne die Aufgabe so, wie sie im Auftrag steht, ohne zu
   sagen, dass sie auffällt.
3. fest: Und geht das immer so, oder gibt es Aufgaben, bei denen das nicht geht?

______________________________________________________________________

## Erwartung an den LU11-Vignetten

### lu11-01 Elin

- Regel in Schülerworten: links ausrechnen, das Ergebnis kommt direkt hinters
  Gleichheitszeichen, was danach kommt, gehört nicht mehr dazu; «links
  ausrechnen, das ist dann x» allein genügt
- Herkunft (prüft «Kein Widerspruch zu Auftrag und Heft»): Taschenrechner, so
  war das immer
- An der Aufgabe (B, Schritt 2): a) 5 + 7 = \_\_\_ + 6 → 12
- Frage nach dem Zeichen: «Was bedeutet das Gleichheitszeichen?» → «Da kommt
  raus, was man vorher gerechnet hat.»

### lu11-02 Jonas

- Regel in Schülerworten: die Zahl bei x kommt mit dem Gegenzeichen auf die
  andere Seite, egal wo das x steht; «die Zahl kommt rüber, das Zeichen dreht
  sich» allein genügt
- Herkunft (prüft «Kein Widerspruch zu Auftrag und Heft»): Waage aus dem
  Unterricht, hat bei fast allen Gleichungen geklappt
- An der Aufgabe (B, Schritt 2): b) 50 − x = 12 → 62
- Frage nach dem Begriff: «Was heisst Waage?» → «dass etwas rüberkommt und das
  Zeichen wechselt»

### lu11-03 Livia

- Regel in Schülerworten: bei Bruchgleichungen darf man die Kehrwerte nehmen,
  jeden Bruch umdrehen, Plus und Minus bleiben; «Kehrwerte nehmen» allein genügt
- Herkunft (prüft «Kein Widerspruch zu Auftrag und Heft»): Umformung 6 im Buch,
  bei a) aufgegangen
- An der Aufgabe (B, Schritt 2): b) 1/x − 1/(2x) = 1/16 → −16
- Frage nach dem Begriff: «Was heisst Kehrwert nehmen?» → jeden Bruch umdrehen,
  Zahlen als Bruch mit Nenner 1

Auf die Frage nach der Geltung (A Schritt 3, B Schritt 3) bei allen drei: gilt
immer, oder Verweis auf die Aufgaben, bei denen es aufging; «ich glaube schon»,
«weiss ich nicht» und «bei Bruchgleichungen immer» sind ebenfalls erfüllt. Nicht
erfüllt bei e2-keine-ausnahme wäre bei Livia «nur wenn auf jeder Seite ein Bruch
steht», bei Jonas «nur wenn x vorne steht», bei Elin «nur wenn hinter der Lücke
nichts mehr steht». «Der Nenner darf nicht null werden» (Livia) ist ihr eigenes
Wissen und schliesst keine Heftaufgabe aus; erfüllt.

## Probeläufe

### 2026-10-19, Evalinput A und B, alle drei Vignetten, k = 3

Schüler:in: Apertus-v1.5-70B über `scripts/evalgespraech.py` mit
`docs/simulation_prompts/2026-10-19-systemprompt.md`; der gelenkte Schritt von
Evalinput B je Vignette einmal fest formuliert
(`probelaeufe/2026-10-19-gelenkte-schritte.json`: «Was bedeutet für dich das
Gleichheitszeichen?», «Was heisst das für dich, wenn man sagt, eine Gleichung
ist wie eine Waage?», «Was heisst das für dich, den Kehrwert nehmen?»).
Verläufe: `probelaeufe/2026-10-19-eval-04-<a|b>-lu11-0<n>-<k>.json`. Bewerter:
Agent-Typ `bewerter`, ein Aufruf je Kriterium, alle 144 Urteile auf Anweisung
des Users mit Sonnet (`model: sonnet`, Bewerter-Vorlage sonst unverändert). Alle
Urteile in `probelaeufe/2026-10-19-urteile.json`.

Quoten (erfüllt von 3), Evalinput A / B. `inhaltlich-antworten` überall 3/3,
`kein-rollenbruch` 3/3 ausser Elin A 2/3.

- lu11-01 Elin: `e1-regel-in-schuelerworten` 2 / 3, `e2-keine-ausnahme` 1 / 3,
  `kein-ungefragtes-verraten` 0 / 0, `wissen-der-klassenstufe` 1 / 2,
  `kein-widerspruch-zu-auftrag-und-heft` 1 / 3, `treue-zur-denkweise` 1 / 2.
- lu11-02 Jonas: `e1-regel-in-schuelerworten` 3 / 1, `e2-keine-ausnahme` 3 / 3,
  `kein-ungefragtes-verraten` 0 / 0, `wissen-der-klassenstufe` 3 / 3,
  `kein-widerspruch-zu-auftrag-und-heft` 1 / 1, `treue-zur-denkweise` 3 / 1.
- lu11-03 Livia: `e1-regel-in-schuelerworten` 2 / 1, `e2-keine-ausnahme` 2 / 2,
  `kein-ungefragtes-verraten` 1 / 1, `wissen-der-klassenstufe` 2 / 1,
  `kein-widerspruch-zu-auftrag-und-heft` 2 / 2, `treue-zur-denkweise` 1 / 3.

Befunde, jeweils mit Zuordnung:

- Die Regel selbst trifft die Erwartung fast überall: Elin «linke Seite
  ausrechnen, Ergebnis in die Lücke, was danach kommt, gehört nicht dazu», Jonas
  «die Zahl neben dem x kommt mit dem Gegenzeichen rüber, egal wo das x steht»,
  Livia «jeden Bruch einzeln umdrehen, Plus und Minus bleiben». Die Abweichungen
  liegen bei Herkunft, Geltung und beim Vorrechnen.
- `kein-ungefragtes-verraten` 2 von 18, Kriterium. In einem Eval, das direkt
  nach der Regel fragt, beanstanden die Bewerter, dass die Regel auf «Woher
  kennst du sie?» und «Gilt sie immer?» noch einmal ausgebreitet wird und dass
  Beteuerungen wie «hat immer gestimmt» schon vor der Geltungsfrage kommen. Das
  ist dieselbe offene Grenze wie in Eval 3, hier aber zugespitzt: Die Fragen
  laden zur Wiederholung ein. Am Kriterium zu entscheiden, ob eine Regel, nach
  der das Gespräch fragt, in den Folgeschritten als ungefragt gilt.
- Elin A, Simulation. Die erwartete Herkunft «Taschenrechner» kommt nur in k=3.
  k=1 erfindet ein «Computer-Training», k=2 legt die Regel Herrn Wyss in den
  Mund («Schaut euch die linke Seite an, rechnet die erste Rechnung aus»). k=2
  kippt bei der Geltungsfrage in die relationale Sicht («muss das Ergebnis doch
  auf beiden Seiten gleich viel ergeben»), k=3 nennt eine Einschränkung («gilt
  immer, wenn man schnell rechnen soll») und einen Meta-Satz («Als Erklärung
  sage ich einfach: …», der einzige `kein-rollenbruch`-Fall). `e2` 1 von 3.
- Jonas A trifft die Erwartung (Waage, Frau Keller, «gilt immer»). Grenzfall wie
  in Eval 1: k=2 lässt die Lehrerin sagen, «dass es egal sei, wo das x steht»,
  k=3 nennt ein «altes Arbeitsblatt»; beides wertet der Bewerter als Herkunft
  gegen die Beschreibung (`kein-widerspruch-zu-auftrag-und-heft` 1 von 3).
- Jonas B, Simulation: Beim Vorrechnen an b) entgleist das Rezept. k=1 «pack ich
  das x mit dem Plus rüber», k=3 «81 + 81 = 162 … x = 153», k=2 rechnet x : 4 =
  3 richtig als 12 und behauptet dann, «12 / 4 gleich 3» stimme nie. `e1`,
  `treue-zur-denkweise` und `kein-widerspruch-zu-auftrag-und-heft` je 1 von 3.
  Dieselbe Instabilität beim Rechnen wie in Eval 2 und 3.
- Livia, Simulation und ein Fehlurteil. Die Einschränkung, die die Erwartung als
  Beispiel für nicht erfüllt nennt, kommt viermal: A k=2 «Wenn links und rechts
  je ein Bruch steht», B k=2 «Wenn auf jeder Seite genau ein Bruch steht», B k=3
  «Solange links und rechts je ein Bruch steht», abgeschwächt A k=1 und A k=3
  («nur Aufgaben mit Brüchen auf beiden Seiten gehabt»). Die Bewerter werten das
  uneinheitlich: A k=2 und B k=2 nicht erfüllt, B k=3 erfüllt mit der
  Begründung, der Satz beschreibe nur die bisherigen Buchaufgaben. Das ist nach
  der Erwartung ein Fehlurteil. Livia nennt zudem bei a) «mit 30 multipliziert»
  statt «· 90» aus dem Heft (B k=1) und spricht von der «Kehrwert-Umformung»,
  die «auf jeden Bruch allein, nicht auf den ganzen Ausdruck» wirke (B k=3,
  Sprache der Beschreibung).
- Grenzfall `wissen-der-klassenstufe`, Elin B k=2: «Für mich steht da ‹ergibt›»
  wertet der Bewerter als Etikett der Beschreibung, wie «Rezept» in Eval 1.
- Bewerter: Die Begründungen gehen Wechsel für Wechsel vor, zitieren und
  gleichen mit Heft und Beschreibung ab, die Rechenfehler (162 und 153 bei Jonas
  B k=3) sind gefunden. Zwei Unschärfen: das Fehlurteil bei Livia B k=3 und bei
  Elin A k=1, wo `e1` die erfundene Herkunft als «frühere Aufgaben» gelten
  lässt, während `kein-widerspruch-zu-auftrag-und-heft` sie am selben Satz
  beanstandet. Das Kriterium `e1` zählt die Herkünfte als Liste auf und lässt
  damit jede passende Kategorie durch; schärfer wäre «die Herkunft, die die
  Beschreibung dieser Schüler:in nennt». Alle 144 Sonnet-Agenten haben die
  Zieldatei geschrieben, mit dem Zusatz im Auftrag «Schreibe das JSON-Objekt mit
  dem Write-Tool in den Zielpfad und antworte danach nur mit der einen Zeile».
