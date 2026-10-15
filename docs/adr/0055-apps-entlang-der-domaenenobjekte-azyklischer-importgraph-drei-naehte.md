---
status: amended
amended-by: [ADR-0064]
---

# Apps entlang der Domänenobjekte, ein azyklischer Importgraph, drei benannte Nähte

> **Nachgeführt durch ADR-0064:** Die Domänenseite übergibt der
> Sprachmodell-Naht Paare aus Eingabe und Inhalt. Bei der simulierten
> Schüler:in ist der Inhalt jede frühere Antwort so, wie das Modell sie nach
> dem Ausgabeschema ausgegeben hat, also Denkspur und Äußerung; die Denkspur
> reist im Verlauf mit (ADR-0064). Für „keine native Reasoning-Spur“ gilt
> ADR-0064 statt ADR-0005. „`erhebungen` weiß nichts von Konten“ meint die
> Datenspur: Der Export von `erhebungen` kennt keine Konten; Views und Modelle
> von `erhebungen` nutzen Konto und Eigentümer-Kreis über die Kante nach
> `konten`.

Dieses ADR fasst den Stand von ADR-0016 und seinen Nachführungen durch
ADR-0037, ADR-0041, ADR-0042, ADR-0044, ADR-0045, ADR-0046 und ADR-0052
zusammen und ersetzt ADR-0016. Die Einzelentscheidungen gelten fort; hier steht
der Graph, wie er heute ist.

## Der Schnitt folgt dem Glossar

Die Module des Projekts werden entlang der **Domänenobjekte aus `GLOSSARY.md`**
geschnitten, nicht entlang der Rollen und nicht entlang technischer Schichten.
Jede Django-App besitzt die Objekte, deren Namen sie trägt; die Rollen aus dem
Glossar erscheinen als Sichtbarkeitsregeln auf diesen Objekten (ADR-0039),
nicht als eigene Module.

Die App- und Modulnamen sind **deutsch**, weil das Glossar deutsch ist. Ein
englischer Verzeichnisname zwänge zu einer Übersetzungstabelle zwischen Glossar
und Code, in der genau die Unterscheidungen verschwimmen, die `GLOSSARY.md`
aufgestellt hat. Deutsche Bezeichner stehen neben Djangos englischem Vokabular
(`models.py`, `ForeignKey`, `objects`): Was aus dem Glossar stammt, heißt
deutsch; was aus dem Framework stammt, bleibt englisch. Gemischte Bezeichner wie
`vignette_set` entstehen dort, wo Django sie erzeugt, und werden nicht bekämpft.

```
konten/            Konto, Rollen, Eigentümer-Kreis als Basis (ADR-0037)
texte/             Markdown-Rendering, Querschnitt ohne Domänenobjekt (ADR-0044)
fragebogen_items/  Fragebogen-Item, Fragebogen-Item-Historie
simulation/        Simulationskern, Evalkatalog, Modell-Konfiguration,
                   Transkriptions-Konfiguration, Sprachmodell- und Transkriptions-Naht
vignetten/         Vignette, Vignettenhistorie
sitzungen/         Teilnahme, Sitzung, Gesprächsschritt, Fehlversuch, Diagnose,
                   Vignettenposition, Sink, Durchlauf, Probelauf
evals/             Evallauf, Evalgespräch, Urteil
training/          Training, Trainingsbindung, Abschrift
erhebungen/        Erhebung, Stichprobe, Erhebungsbindung, Ablauf, Vignettenziehung,
                   Item-Zuordnung, Itemblock, Item-Antwort, Export der Datenspur
```

`sitzungen` heißt nicht `sessions`, weil `django.contrib.sessions` diesen
App-Label belegt. `fragebogen_items` heißt nicht `fragebogen`, weil der
Fragebogen laut ADR-0008 der Sammelbegriff für die Items *einer Erhebung* samt
Andockpunkten ist und Zuordnung, Reihenfolge, Itemblock und Item-Antwort alle in
`erhebungen` liegen. Daneben stehen `config` (Projektkonfiguration, Wächter) und
`seeds` (Entwicklungsdaten); beide sind keine Domänen-Apps.

## Der Graph ist azyklisch, und die Richtung ist eine Aussage

Wohin der Produktionscode jeder App zeigen darf, hält
`config/tests/test_importgraph.py` als Kantentabelle fest. Er liest die Quellen
und zählt jeden absoluten Import, auch funktionslokale und solche nur zur
Typprüfung. Eine Kante hinzuzufügen ist eine Aussage über die Architektur und
gehört in ein ADR, nicht nur in die Tabelle.

| App | darf zeigen auf |
| --- | --- |
| `konten` | nichts |
| `texte` | `konten` |
| `fragebogen_items` | `konten` |
| `simulation` | `konten` |
| `vignetten` | `konten`, `simulation` |
| `sitzungen` | `konten`, `texte`, `simulation`, `vignetten` |
| `evals` | `konten`, `simulation`, `vignetten` |
| `erhebungen` | `config`, `konten`, `texte`, `fragebogen_items`, `simulation`, `vignetten`, `sitzungen` |
| `training` | `config`, `konten`, `texte`, `simulation`, `vignetten`, `sitzungen`, `erhebungen` |

Was die Richtung sagt:

- **`konten` ist die Basis.** Alle Bestands-Apps zeigen auf `konten`, das dort
  den Eigentümer-Kreis als abstrakte Basis stellt; `konten` zeigt auf keine von
  ihnen (ADR-0037). Den Konto-Löschpfad trägt deshalb Djangos
  Modellregistrierung, kein Import.
- **`texte` ist Querschnitt**, kein Domänenobjekt: Es rendert Markdown
  (ADR-0044), kennt für die Rollenprüfung seiner Vorschau nur `konten` und
  sonst nichts.
- **`fragebogen_items` ist ein Blatt.** Die Item-Bibliothek weiß nicht, wer
  ihre Items beantwortet.
- **`sitzungen` kennt weder Training noch Erhebung.** Eine Sitzung ist laut
  Glossar die atomare Auswertungseinheit; ein `sitzungen`, das seine beiden
  Aufrufer kennt, wäre es nicht mehr. Deshalb liegt die **Vignettenposition**
  (welche Sitzung die wievielte einer Teilnahme war) bei `sitzungen` an der
  Teilnahme, während die *geplante* Folge samt Randomisierung als
  `Vignettenziehung` in `erhebungen` bleibt. Deshalb liegen auch die beiden
  **Bindungen** einer Teilnahme bei `training` und `erhebungen` und zeigen nach
  `sitzungen`, nie umgekehrt (ADR-0058).
- **`simulation` kennt keine Vignette.** `antwort_versuchen` nimmt die
  Prompt-Platzhalter als fertiges Mapping; nähme es die Vignette, hätte der
  Graph einen Zyklus (#378).
- **Auf `evals` zeigt nichts.** `vignetten` liest den Stand eines Evallaufs
  allein über den Reverse-Accessor und verlinkt per URL-Name (ADR-0046). Der
  Evalkatalog kennt keine Vignette und liegt deshalb in `simulation`.
- **`erhebungen` ist die Wurzel des Exports.** Der Export der Datenspur
  (`erhebungen/export.py`) darf als einzige Stelle quer durch alle anderen
  Apps lesen; das ist der Preis dafür, dass die Datenspur eine Teilnahme
  vollständig abbildet. `training` zeigt auf `erhebungen` nur für die
  Abschrift, die eine Erhebungsbindung liest (ADR-0058); `erhebungen` weiß
  nichts von Konten.

**Die Views eines Anlasses liegen bei der App dieses Anlasses**: die
Trainings-Views bei `training`, die Erhebungs-Views bei `erhebungen`, die
Probelauf-Views bei `sitzungen`, jede mit eigenen Routen. Views, die
`sitzungen` für einen seiner Aufrufer hielte, zwängen es, diesen Aufrufer zu
kennen. Views und Templates liegen je App, `templates/base.html` bleibt
global; Tests liegen je App.

## Drei benannte Nähte

Eine **Naht** ist eine Stelle, an der Verhalten ausgetauscht werden kann, ohne
den umgebenden Code zu ändern. Sie wird nur dort eingezogen, wo tatsächlich
etwas variiert: Ein Adapter bedeutet eine hypothetische Naht, zwei bedeuten
eine echte. Naht ist ein Architekturbegriff, kein Domänenbegriff, und steht
deshalb nicht im Glossar, sondern ist hier definiert. Vermeide: Seam, Port,
Interface, Abstraktionsschicht.

ADR-0016 zählte zwei Nähte, das Sprachmodell und den Sink. Die Transkription
kam später hinzu (ADR-0026, ADR-0036) und erfüllt dieselbe Definition: ein
Protokoll, ein Fake und je ein Adapter je Anbieter. ADR-0038 und ADR-0050
nennen sie bereits eine Naht. Dieses ADR zählt deshalb **drei**, und bindend
ist nicht die Zahl, sondern die Regel: Jede Naht ist hier benannt, hat
mindestens zwei echte Adapter, und eine weitere ist ein neues ADR.

### Das Sprachmodell

`simulation/sprachmodell/`: ein Protokoll mit einer Methode und zwei Adaptern,
`LiteLLMSprachmodell` für die echten Anbieter und `FakeSprachmodell`, ohne den
die Fehlversuch-Schreibbahn aus ADR-0061 nicht prüfbar wäre und der Probelauf
in der Entwicklung Geld kostete. Der Adapter wird über das Anbieterfeld der
Modell-Konfiguration gewählt (ADR-0056).

```python
def antworten(self, system_prompt, verlauf, eingabe, ausgabe_schema, timeout) -> dict
```

Die Methode liefert **eines**: das geparste Structured-Output-Objekt *des
übergebenen Schemas*. Nichts reist an dem Schema vorbei; eine native
Reasoning-Spur des Anbieters wird nicht durchgereicht (ADR-0005). Einen
gesonderten User-Prompt gibt es nicht: Der Arbeitskontext steht im
System-Prompt, jede `user`-Nachricht stammt vom Gegenüber der Rolle
(ADR-0052). Dass der **Verlauf hinter die Naht** reicht, statt davor zu einem
Prompt-String zusammengeklebt zu werden, hat denselben Grund: Wie eine
Konversation gegenüber einem Anbieter dargestellt wird, ist Adapter-Wissen. Die
Domänenseite übergibt Paare aus Eingabe und sichtbarer Äußerung; die Denkspur
hat darin keinen Platz. `timeout` ist die Restzeit der Frist, die sich alle
Versuche eines Gesprächsschritts teilen.

Die Naht hat **drei Aufrufer** mit je eigenem Ausgabeschema: die simulierte
Schüler:in, die simulierte Lehrperson und den Bewerter der Evals (ADR-0046).
Sie bekommt dafür keine Schwester; der Rückgabewert ist immer das geparste
Objekt des übergebenen Schemas.

### Die Transkription

`simulation/transkription/`: ein Protokoll mit einer Methode
`transkribieren(audio) -> str` und drei Adaptern, `FakeTranskription`,
`OpenAITranskription` (OpenRouter) und `InfomaniakTranskription`. Der Adapter
wird über das Anbieterfeld der Transkriptions-Konfiguration gewählt
(ADR-0056); Audio wird nicht aufbewahrt (ADR-0007, ADR-0026). Sie ist die
schmalste der drei Nähte: Bytes hinein, Text heraus.

### Der Sink

`sitzungen/sink.py`: das Ziel eines Sitzungslaufs, mit **drei Adaptern**.
`DBSink` persistiert eine Sitzung vollständig; `FluechtigerSink` schreibt das
Ablaufgerüst in die Datenbank und hält die Inhalte in der Browser-Session
(ADR-0045); `ScratchSink` hält einen schreibfreien Probelauf ganz in der
Browser-Session (ADR-0014). `DBSink` und `FluechtigerSink` teilen Gerüst und
Uhr über die Basis `GeruestSink`. Der Lauf (`sitzungen/durchlauf.py`) kennt nur
den Sink und bleibt damit zwischen Sitzung, flüchtiger Sitzung und Probelauf
austauschbar; die Wahl des Adapters hängt an der Einwilligung und an der Rolle,
nicht an einem Flag im Lauf.

Der Sink ist **mehr als Persistenz**. Er trägt den Start über dem Tripel aus
Vignette, Kern und Modell-Konfiguration, den lesenden Zugriff auf die
bisherigen Gesprächsschritte, die Budget-Uhr über `zug_beginnen` und
`zug_beenden` (ADR-0057), die Budgeterschöpfung als Rückgabe des angehängten
Schritts, und die beiden Stellen, an denen die Anlässe auseinandergehen: ob ein
endgültig gescheiterter Schritt neben dem Transkript stehen bleibt (ADR-0061:
die persistierte Sitzung behält ihn, der Probelauf verwirft ihn) und ob das
erschöpfte Budget die Sitzung abschließt. Der Budgetstand selbst ist ein
speicherloses Wertobjekt mit einer Implementierung; seine Speicher sind die
Adapter. Damit existiert der Ablauf eines Gesprächsschritts **einmal**, und
„der Probelauf unterscheidet sich allein in der Persistierung" (ADR-0014) ist
strukturell wahr statt behauptet.

Was der Lauf zurückgibt, ist der **Ausgang** des Gesprächsschritts:
fortgesetzt, gescheitert oder Budget erschöpft. Er ist ein Rückgabewert und
kein Gegenstand mit Eigenleben; deshalb steht er nicht im Glossar.

### Was keine Naht ist

Der **Ablauf** einer Erhebung (`erhebungen/ablauf.py`) hat genau eine
Implementierung; dass Tests ohne HTTP an ihm ansetzen, macht ihn nicht zu einer
Naht (ADR-0041). Ein Trainingsablauf existiert nicht: Ein Training ist ein
Vorrat in freier Reihenfolge. Der **Evallauf** hat nur einen Speicherort und
braucht keinen Sink. Das **Markdown-Rendering** hat eine Implementierung
(ADR-0044). Der **Eigentümer-Kreis** ist eine Basis, kein Austauschpunkt
(ADR-0037).

Sonst keine. Kein Repository-Interface, kein Service-Layer, kein
framework-freier Domänenkern. Die Datenbank wird nicht hinter einem Interface
versteckt, HTTP wird nicht ausgetauscht; Interfaces an Stellen, an denen nichts
variiert, kosten Lesbarkeit ohne Gegenwert. Das Projekt läuft auf SQLite
(ADR-0059); die Schlussfolgerung hängt daran, dass *eine* Datenbank fest
verdrahtet ist, nicht daran, welche.

## Das simulationsseitige Interface kennt keine Datenbank

```python
simulation.antwort_versuchen(platzhalter, kern, modell_konfiguration, verlauf, eingabe) -> Antwortversuch
```

gibt einen **Antwortversuch** zurück und schreibt nichts; `sitzungen`
persistiert ihn über den Sink. Der Antwortversuch ist nicht dasselbe wie ein
Gesprächsschritt: Er ist flüchtig, darf scheitern und trägt die Fehlversuche
mit sich, die ein Gesprächsschritt neben sich stellt. Er ist auch **nicht** die
Rückgabe der Sprachmodell-Naht: Zwischen beiden sitzt die begrenzte
Wiederholung aus ADR-0061 (`MAX_VERSUCHE`). Dass sie in `simulation` liegt und
nicht hinter der Naht, ist der Grund, warum der Fake die Fehlversuch-Schreibbahn
prüfen kann.

## Was bindend ist, und was nicht

Bindend sind der Schnitt entlang der Domänenobjekte, die Azyklizität samt
Kantenrichtung und die Liste der Nähte. Eine Abweichung davon ist ein neues
ADR, das dieses ablöst.

Nicht bindend sind der konkrete Baum oben und die Ablage von Views, Templates
und Tests. Eine neue App oder Kante innerhalb des Schnitts führt dieses ADR
nach; die Kantentabelle im Wächter wächst mit.

## Erwogene Optionen

- **Ein framework-freier Domänenkern mit Ports und Adaptern** — verworfen. Er
  verlangt Repository-Interfaces, hinter denen genau ein Adapter steht. Die
  Testbarkeit, die er verspricht, liefert `pytest-django` mit einer Datenbank
  billiger.
- **Eine App je Persona** (`teilnahme`, `autorenschaft`, `forschung`,
  `verwaltung`) — verworfen. Vignette und Sitzung würden von mehreren Apps
  geteilt und landeten in einem `shared`, das den eigentlichen Schnitt trüge.
  Rollen sind Sichten auf Objekte, keine Objekte.
- **Englische App-Namen mit einer Übersetzungstabelle im Glossar** —
  verworfen. Die Tabelle wäre ein zweites, stillschweigend driftendes Glossar.
- **Der Ablauf in den Views von `training` und `erhebungen`** — verworfen. Er
  wäre nur über HTTP testbar, und die gezogene Randomisierungsreihenfolge hätte
  keinen Ort außerhalb einer View, obwohl sie zur Datenspur gehört.
- **Der Budgetstand oder der Evallauf als eigene Naht** — verworfen (ADR-0042,
  ADR-0046). Beides hat eine Implementierung; ein Speicher je Adapter ist keine
  Naht.
- **Eine Schwester-Naht je Eval-Rolle** — verworfen (ADR-0046). Die Naht nimmt
  das Schema als Parameter; drei Aufrufer brauchen keine drei Protokolle.

## Folgen

- Eine neue Leerstelle im Vertrag zwischen Vignette und Vorlagen (ADR-0054)
  berührt `vignetten` und `simulation`, aber keine dritte App.
- Wer eine Kante braucht, die die Tabelle nicht hat, schreibt ein ADR und erst
  dann den Import. Der Wächter wird rot, bevor der Zyklus entsteht.
- Ein weiterer Adapter an einer der drei Nähte erweitert sie und ist eine
  Nachführung; eine vierte Naht ist ein neues ADR.
- Der Evallauf-Prozess (ADR-0059) läuft im selben Importgraphen: `evals` zeigt
  auf `simulation` und `vignetten`, nichts zeigt auf `evals`.
