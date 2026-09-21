---
status: accepted
---

# Fester Vertrag zwischen Vignette und Vorlagen: zwei benannte Platzhaltermengen im Code

Dieses ADR fasst ADR-0010 und seine Nachführung aus #3 zusammen und ersetzt
ADR-0010.

## Die Leerstellen liegen im Code, nicht im Kern

Die Vorlagen des Simulationskerns haben Leerstellen, die die Vignette füllt.
Welche Leerstellen es gibt, ist **im Code festgelegt** und nicht vom Kern
deklarierbar. Der Kern ist laut ADR-0004 fach-agnostisch; damit ist die Menge
der Leerstellen konstant, und ihre Konstanz ist eine Aussage über die Domäne,
keine Bequemlichkeit.

Autor:innen beschreiben **wer** und **was falsch läuft**. Dass die simulierte
Schüler:in ihrem Fehlermuster konsequent folgt und unter Nachfragen nicht aus
der Rolle fällt, leistet die Prompt-Vorlage. Prompt-Engineering ist Sache der
Administrator:in.

Eine neue Leerstelle bedeutet ein neues Vignettenfeld, eine Migration und eine
Code-Änderung. Ein vom Kern deklarierter Vertrag hätte das Vorspulen eines
Vignettenentwurfs auf einen neueren Kern (ADR-0004) scheitern lassen können,
womit der Entwurf auf einem alten Kern gefangen wäre.

## Welches Vignettenfeld wohin fließt

| Vignettenfeld | Prompt | Rahmenhandlung und Nutzeransicht |
|---|---|---|
| Fehlermuster-Beschreibung | ja | nein |
| Lernauftrag (Text und Bildbeschreibung) | ja | als Ansichtsbaustein |
| Arbeitsheft (Text und Bildbeschreibung) | ja | als Ansichtsbaustein |
| Lernauftrag-Simulationshinweise | ja | nein |
| Arbeitsheft-Simulationshinweise | ja | nein |
| Simulierte Schüler:in (Name, Geschlecht) | ja | ja |
| Erfahrene Lehrperson (Name, Geschlecht) | nein | ja |
| Unterrichtskontext (Fach, Thema, Klassenstufe) | ja | ja |
| Referenzdiagnose | nein | nein |

Die **Bilder** selbst erreichen den Prompt nie; die Simulation bekommt die
Bildbeschreibung an der Stelle des Bildes. Die **erfahrene Lehrperson** bleibt
aus dem Prompt heraus, weil eine simulierte Schüler:in, die weiß, dass ihre
Lehrerin zuhört, einen Grund hat, weniger freimütig über ihren Rechenweg zu
sprechen: eine Störvariable, die niemand kontrolliert und die pro Vignette
anders ausfiele. Die **Referenzdiagnose** bleibt aus beidem heraus, weil sie
eine Notiz ist (ADR-0009).

**Lernauftrag und Arbeitsheft** sind in der Nutzeransicht Ansichtsbausteine,
die die View neben der Rahmenhandlung rendert. In die Rahmenhandlung
substituiert werden nur die kurzen, satzfähigen Werte: die Akteure und der
Unterrichtskontext.

## Beide Akteure sind Vignettenfelder

Simulierte Schüler:in und erfahrene Lehrperson tragen je Name und Geschlecht
an der Vignette, nicht am Kern. Dieselbe Schüler:in dürfte sonst in jeder
Klassenstufe und jedem Fach dieselbe sein, und dasselbe gilt eine Rolle weiter
für die Lehrperson. Das Anlegen-Formular belegt Namen und Geschlechter zufällig
vor; die Werte sind überschreibbar. Der Zufall ist eine Freundlichkeit der
Oberfläche, keine Eigenschaft der Domäne. Sie werden mit der Vignette
versioniert und beim Finalisieren eingefroren; ein Entwurf aus einer finalen
Fassung erbt sie.

**Beide Akteure sind Pflicht.** Weil eine Rahmenhandlung `$lehrperson_*`
verwenden darf, hielte eine leere Lehrperson stille Leerstellen im Fließtext
offen. Die Geschlechter sind darum schon im Entwurf nie leer, weil der
Probelauf aus ihnen Rahmenhandlung und Illustration ableitet; die Namen werden
spätestens beim Finalisieren verlangt (ADR-0040).

**Geschlecht ist zweiwertig** (`männlich`, `weiblich`) als benannte Stufen.
Das ist eine bewusste Domänenaussage, kein Versäumnis: Jede abgeleitete
grammatische Form braucht eine im Code festgeschriebene, kanonische Fassung,
und `divers` besitzt im Deutschen keine neutral etablierte. Der
Erweiterungspfad ist additiv: eine neue Stufe plus ihre kanonische Ableitung,
dieselbe Bewegung wie jede neue Leerstelle.

## Der Vertrag sind zwei benannte Mengen

Prompt-Vorlagen und Rahmenhandlung berühren sich nie (ADR-0004) und ziehen aus
verschiedenen Spalten der Tabelle. Deshalb ist der Vertrag **zwei Mengen, nicht
eine**. Eine einzige Menge erlaubte die Fehlermuster-Beschreibung in der
Einleitung, die sie nie sehen darf, und den Namen der Lehrperson im
System-Prompt, wo er eine Störvariable wäre.

### `VERTRAG_PROMPT`

Die Felder der Prompt-Spalte. System-Prompt- und User-Prompt-Vorlage teilen
sich diese Menge:

`$fehlermuster_beschreibung`, `$lernauftrag`, `$arbeitsheft`,
`$lernauftrag_simulationshinweise`, `$arbeitsheft_simulationshinweise`,
`$schuelerin_name`, `$schuelerin_geschlecht`, `$fach`, `$thema`,
`$klassenstufe`.

Die kurzen Skalare bleiben bei der Ersetzung roh. Die fünf langen Inhalte
werden, wenn sie nicht leer sind, von der Platzhalterfunktion der Vignette in
gleichnamige XML-artige Umgebungen gefasst. `$lernauftrag` und `$arbeitsheft`
enthalten darin die nichtleeren, einzeln gefassten Stücke `*_text` und
`*_bildbeschreibung` in der Reihenfolge, die der Positionsmarker vorgibt
(ADR-0030). Die Vorlage enthält nur den nackten Platzhalter. Nutzereingaben
werden nicht escaped.

### `VERTRAG_RAHMEN`

Die satzfähigen Felder der Nutzeransicht-Spalte plus abgeleitete grammatische
Formen. Aus ihr schöpfen Hospitationseinleitung, Gesprächseinleitung und
Debrief:

- roh: `$schuelerin_name`, `$schuelerin_geschlecht`, `$lehrperson_name`,
  `$lehrperson_geschlecht`, `$fach`, `$thema`, `$klassenstufe`;
- abgeleitet: `$schuelerin_pronomen`, `$schuelerin_possessiv`,
  `$lehrperson_pronomen`, `$lehrperson_possessiv`, `$lehrperson_anrede`.

`$lernauftrag` und `$arbeitsheft` sind **nicht** enthalten; sie sind
Ansichtsbausteine.

Die Rahmenhandlung ist Fließtext für Menschen und braucht Grammatik, die rohe
Feldwerte nicht liefern. Weil `string.Template` nicht dekliniert (ADR-0020),
ist der Katalog der abgeleiteten Formen bewusst sparsam, und der Vorlagentext
formuliert um seine Grenzen herum. Je Akteur berechnet der Code aus Name und
Geschlecht:

- `$..._pronomen`: nur Nominativ (`sie`, `er`);
- `$..._possessiv`: unflektierte Grundform (`ihr`, `sein`), die Deklination
  nach dem Bezugswort trägt der Vorlagentext;
- `$lehrperson_anrede`: nur für die Lehrperson (`Frau`, `Herr`). Eine
  Schüler:in wird beim Vornamen genannt. „Frau Müller“ schreibt die Vorlage
  als `$lehrperson_anrede $lehrperson_name`.

Jede neue grammatische Form ist eine Code-Änderung, dieselbe Aussage wie über
neue Leerstellen, nur über Ableitungen statt über Felder.

## Der Vertrag ist eine statisch geprüfte Obergrenze

Eine Kern-Fassung lässt sich nur finalisieren, wenn jede ihrer Vorlagen
ausschließlich Platzhalter *ihrer* Menge verwendet: Prompt-Vorlagen aus
`VERTRAG_PROMPT`, Rahmenhandlungs-Vorlagen aus `VERTRAG_RAHMEN`. Die Prüfung
ist ein Teilmengen-Test über die Bezeichner der Vorlage und ruft **kein**
Modell auf. Eine Invariante, die vom Wohlwollen eines externen Anbieters
abhinge, wäre keine. Der Vertrag ist eine Obergrenze: Eine Vorlage darf jede
Teilmenge verwenden, kein Platzhalter ist verpflichtend.

Jede der beiden Mengen steht an zwei Orten: im Code, der die Platzhalter
bereitstellt, und in der Validierung, die sie prüft. Das sind zwei Listen an
je zwei Orten, und jede muss eine bleiben.

## Erwogene Optionen

- **Ein vom Kern deklarierter Vertrag** — verworfen. Er hätte das Vorspulen
  eines Vignettenentwurfs scheitern lassen können und den Entwurf auf einem
  alten Kern gefangen.
- **Eine einzige Platzhaltermenge für Prompt und Rahmenhandlung** —
  verworfen. Sie erlaubte die Fehlermuster-Beschreibung in der Einleitung und
  die Lehrperson im System-Prompt.
- **Akteure als Kernfelder** — verworfen. Dieselbe Schüler:in in jedem Fach
  und jeder Klassenstufe.
- **Ein freies Profilfeld für die simulierte Schüler:in** — verworfen. Es wäre
  die Hintertür, durch die Prompt-Engineering unkuratiert zurückkehrt, und es
  machte Auskunftsfreude und Ausweichverhalten zwischen Vignetten
  unvergleichbar. Werden solche Dimensionen gebraucht, gehören sie als
  benannte Stufen in den Kern, eine additive Änderung.
- **Eine dritte Geschlechtsstufe ohne kanonische Ableitung** — verworfen.
  Jede Stufe muss ihre Grammatik im Code mitbringen.
- **Vollständige Deklination der abgeleiteten Formen** — verworfen. Der
  Katalog bleibt sparsam; was `string.Template` nicht kann, formuliert der
  Vorlagentext um.

## Folgen

- Eine Prüfung des Vertrags braucht keinen Modellaufruf und ist ohne Netz
  testbar.
- **Namenskollisionen werden nirgends geprüft**, auch nicht beim
  Zusammenstellen einer Erhebung oder eines Trainings. Zwei gleichnamige
  simulierte Schüler:innen in einer Teilnahme sind ein Darstellungsproblem,
  kein Datenfehler.
- Jede neue Leerstelle und jede neue grammatische Form berührt `vignetten` und
  `simulation`, aber keine dritte App (ADR-0016).
- Eine Vorlage, die um die Grenzen des Katalogs herum formuliert, ist Teil des
  Prompt-Engineerings der Administrator:in, nicht ein Mangel des Codes.
