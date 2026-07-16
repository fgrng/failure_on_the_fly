---
status: accepted
---

# Domänenobjekte als Django-Apps, ein azyklischer Graph, genau zwei Nähte

Die Module des Projekts werden entlang der **Domänenobjekte aus `CONTEXT.md`** geschnitten, nicht entlang der Rollen und nicht entlang technischer Schichten. Jede Django-App besitzt die Objekte, deren Namen sie trägt; die Rollen aus dem Glossar erscheinen als Sichtbarkeitsregeln auf diesen Objekten, nicht als eigene Module.

Die App- und Modulnamen sind **deutsch**, weil das Glossar deutsch ist. Ein englischer Verzeichnisname zwänge zu einer Übersetzungstabelle zwischen Glossar und Code, in der genau die Unterscheidungen verschwimmen, die `CONTEXT.md` mühsam aufgestellt hat — `studies` etwa trüge den Begriff, den der Eintrag **Erhebung** ausdrücklich vermeidet.

```
apps/
  konten/            Nutzer, Rollen
  fragebogen_items/  Fragebogen-Item, Fragebogen-Item-Historie
  simulation/        Simulationskern, Modell-Konfiguration
  vignetten/         Vignette, Vignettenhistorie
  sitzungen/         Teilnahme, Sitzung, Gesprächsschritt, Fehlversuch, Diagnose
  training/          Training, Trainingsbindung
  erhebungen/        Erhebung, Stichprobe, Erhebungsbindung, Ablauf, Item-Zuordnung, Item-Antwort
  datenspuren/       Datenspur
```

`sitzungen` heißt nicht `sessions`, weil `django.contrib.sessions` diesen App-Label bereits belegt.

## Der Graph ist azyklisch, und die Richtung ist eine Aussage

`training` und `erhebungen` zeigen auf `sitzungen`; `sitzungen` zeigt auf `vignetten` und `simulation` (die defensive Protokollierung der verwendeten Fassungen aus ADR-0003); `vignetten` zeigt auf `simulation` (der gepinnte Kern aus ADR-0004). `erhebungen` besitzt zusätzlich den Ablauf, der seine Erhebungsbindungen und die daraus entstehenden Sitzungen sequenziert. `fragebogen_items` ist ein **Blatt**: die Item-Bibliothek weiß nicht, wer ihre Items beantwortet. `datenspuren` ist das gegenüberliegende Blatt: Es kennt alles, und nichts kennt es.

Daraus folgt, was `sitzungen` **nicht** darf: Es kennt weder Training noch Erhebung. Eine Sitzung ist laut Glossar die atomare Auswertungseinheit; ein `sitzungen`, das seine beiden Aufrufer kennt, wäre es nicht mehr.

## Genau zwei Nähte

Eine **Naht** ist eine Stelle, an der Verhalten ausgetauscht werden kann, ohne den umgebenden Code zu ändern. Sie wird nur dort eingezogen, wo tatsächlich etwas variiert — ein Adapter bedeutet eine hypothetische Naht, zwei bedeuten eine echte. Es gibt zwei:

Das **Sprachmodell** (`simulation/sprachmodell/`): ein Protokoll mit einer Methode, zwei Adapter — der echte Anbieter und ein deterministischer Fake, ohne den die Fehlversuch-Schreibbahn aus ADR-0011 nicht prüfbar wäre und der Probelauf in der Entwicklung Geld kostete.

Die eine Methode nimmt System-Prompt, User-Prompt und das Ausgabeschema und liefert **zweierlei**: das geparste Structured-Output-Objekt, aus dem Denkspur und Äußerung stammen (ADR-0005), und eine **optionale native Reasoning-Spur**. Letztere reist an dem Schema vorbei, weil sie kein Feld der Modellantwort ist, sondern ein Nebenprodukt des Anbieters. Ein Protokoll, das nur das geparste Objekt zurückgibt, könnte sie nicht durchreichen — und ADR-0005 verlangt, dass sie am Gesprächsschritt aufbewahrt wird, wenn es sie gibt. Ob sie je gefüllt wird, hängt vom Anbieter ab (siehe `docs/open-questions.md`, Frage 7); die Naht muss sie unabhängig davon tragen können.

Der **Sink** (`sitzungen/sink.py`): das Ziel einer Spielorchestrierung, mit zwei Adaptern. `DBSink` persistiert eine Sitzung inkrementell; `ScratchSink` hält einen schreibfreien Probelauf in der Browser-Session. Die Orchestrierung kennt nur den Sink und bleibt damit zwischen regulärer Sitzung und Probelauf austauschbar.

Der Ablauf ist keine Naht: `erhebungen/ablauf.py` sequenziert ausschließlich Erhebungsbindungen, und Training hat keinen entsprechenden Ablauf. `naechster_schritt(teilnahme)` liefert eine Vignetten-Fassung, künftig ein Fragebogen-Item oder das Ende direkt aus dem Erhebungsmodell.

Sonst keine. Kein Repository-Interface, kein Service-Layer, kein framework-freier Domänenkern. Die Datenbank wird nicht hinter einem Interface versteckt, HTTP wird nicht ausgetauscht; Interfaces an Stellen, an denen nichts variiert, kosten Lesbarkeit ohne Gegenwert.

Das Projekt läuft **vorerst auf SQLite**, nicht auf Postgres. Der Wechsel ist billig, solange keine Forschungsdaten existieren, und beißt erst bei gleichzeitigen Teilnehmenden einer Erhebung. Die Schlussfolgerung dieses Abschnitts — kein Repository-Interface, weil die Datenbank nicht variiert — bleibt davon unberührt: Sie hängt daran, dass *eine* Datenbank fest verdrahtet ist, nicht daran, welche. Alle Constraints der Modelle sind so gewählt, dass sie unter SQLite laufen (siehe ADR-0021).

## Das simulationsseitige Interface kennt keine Datenbank

`simulation.antwort_versuchen(vignette, kern, modell_konfiguration, verlauf, eingabe)` gibt einen **Antwortversuch** zurück und schreibt nichts. `sitzungen` persistiert ihn. Damit ist die Aussage aus ADR-0014 — der Probelauf ist eine schreibfreie Funktion über einem Tripel — strukturell wahr statt an einen `dry_run`-Parameter gebunden. Probelauf und Sitzung sind derselbe Aufruf mit verschiedenen Aufrufern.

Der übergebene `verlauf` ist eine Liste sichtbarer Äußerungen. Die Denkspur hat in ihm keinen Platz, womit ADR-0005 („die Denkspur fließt nicht in den Kontext zurück") ebenfalls nicht mehr verletzbar ist.

## Was bindend ist, und was nicht

Bindend sind der Schnitt entlang der Domänenobjekte, die Azyklizität samt Kantenrichtung und die Zahl der Nähte. Eine Abweichung davon ist ein neues ADR, das dieses ablöst.

Nicht bindend sind der konkrete Baum oben und die Ablage von Views, Templates und Tests. Sie folgen aus dem Glossar und dürfen während der Implementierung mit Begründung im Commit angepasst werden, solange der Schnitt erhalten bleibt. Dieses ADR wird dann nachgeführt, nicht abgelöst.

## Considered Options

- **Ein framework-freier Domänenkern mit Ports und Adaptern** — verworfen. Er verlangt Repository-Interfaces, hinter denen genau ein Adapter steht. Die Testbarkeit, die er verspricht, liefert `pytest-django` mit einer Datenbank billiger.
- **Eine App je Persona** (`teilnahme`, `autorenschaft`, `forschung`, `verwaltung`) — verworfen. Vignette und Sitzung würden von mehreren Apps geteilt und landeten in einem `shared`, das den eigentlichen Schnitt trüge. Rollen sind Sichten auf Objekte, keine Objekte.
- **Englische App-Namen mit einer Übersetzungstabelle im Glossar** — verworfen. Die Tabelle wäre ein zweites, stillschweigend driftendes Glossar, und die _Avoid_-Listen aus `CONTEXT.md` verlören im Code ihre Kraft.
- **Der Ablauf liegt in den Views von `training` und `erhebungen`** — verworfen. Er wäre nur über HTTP testbar, und die gezogene Randomisierungsreihenfolge hätte keinen Ort außerhalb einer View, obwohl sie zur Datenspur gehört.

## Consequences

- Der Ablauf führt implizit das Konzept eines Ablauf-Schritts ein: `erhebungen.ablauf.naechster_schritt(teilnahme)` liefert eine Vignette, ein Fragebogen-Item oder das Ende. Das Konzept existiert, aber es hat **keine Tabelle**, und es bekommt keine: Instruktion, Einwilligungstext, Start- und Endseite sind Textfelder an der Erhebung, die der Ablauf an den Rändern ausliefert, ohne sie als Schritte auszugeben. Dasselbe gilt für den Hinweis, **dass** das Gespräch begrenzt ist, den ADR-0012 verlangt. Damit erledigt dieses ADR eine zuvor offene Frage: Ein allgemeiner Ablauf-Schritt als Objekt wird nicht eingeführt. Sollte ein Rand je verzweigen oder wiederholt werden müssen, ist das der Zeitpunkt, ihn zu einem Schritt zu machen — und ein neues ADR.
- **Antwortversuch** ist ein neuer Begriff und nicht dasselbe wie ein Gesprächsschritt: Er ist flüchtig, er darf scheitern, und er trägt die Fehlversuche mit sich, die ein Gesprächsschritt neben sich stellt. Er enthält auch keine Eingabe — die liegt beim Aufruf bereits vor. Er erzeugt die zweite Hälfte eines Gesprächsschritts, nicht den Gesprächsschritt.
- Der Antwortversuch ist **nicht** die Rückgabe der Sprachmodell-Naht. Zwischen beiden sitzt die begrenzte Wiederholung aus ADR-0011: Ein Antwortversuch fasst *n* Modellrückgaben zusammen, von denen *n−1* als Fehlversuche verworfen wurden. Dass die Wiederholung in `simulation` liegt und nicht hinter der Naht, ist der Grund, warum der deterministische Fake die Fehlversuch-Schreibbahn überhaupt prüfen kann.
- Die App heißt `fragebogen_items` und nicht `fragebogen`, weil sie den Fragebogen gerade **nicht** enthält: Er ist laut ADR-0008 der Sammelbegriff für die Items *einer Erhebung* samt ihren Andockpunkten, und Zuordnung, Andockpunkt, Reihenfolge und Item-Antwort liegen alle in `erhebungen`. Ein `fragebogen/`, in dem kein Fragebogen wohnt, schickte jede Suche an den falschen Ort. `items` schied aus, weil das Glossar den Begriff unter _Avoid_ führt.
- **Naht** ist ein neuer Begriff und steht im Glossar unter _Architektur_. Er ist kein Domänenbegriff, sondern ein Architekturbegriff — der einzige, den dieses ADR einführt.
- Deutsche Bezeichner stehen neben Djangos englischem Vokabular (`models.py`, `ForeignKey`, `objects`). Die Grenze verläuft sauber: Was aus dem Glossar stammt, heißt deutsch; was aus dem Framework stammt, bleibt englisch. Gemischte Bezeichner wie `vignette_set` entstehen dort, wo Django sie erzeugt, und werden nicht bekämpft.
- Eine neue Leerstelle im Vertrag zwischen Vignette und Prompt-Vorlagen (ADR-0010) berührt `vignetten` und `simulation`, aber keine dritte App.
- Views und Templates liegen je App (`apps/vignetten/templates/vignetten/`); `templates/base.html` bleibt global. Tests liegen je App und teilen nichts (ADR-0017). Beides folgt aus dem Schnitt, ist aber nicht selbst gegrillt worden.
- `datenspuren` darf als einziges Modul quer durch alle anderen lesen. Das ist der Preis dafür, dass die Datenspur eine Teilnahme vollständig abbildet, und der Grund, warum es ein Blatt bleiben muss.
