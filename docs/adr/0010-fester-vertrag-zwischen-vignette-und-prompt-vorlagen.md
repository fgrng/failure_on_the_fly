---
status: accepted
---

# Fester Vertrag zwischen Vignette und Prompt-Vorlagen

Die Prompt-Vorlagen des Simulationskerns haben Leerstellen, die die Vignette füllt. Welche Leerstellen es gibt, ist **im Code festgelegt** und nicht vom Kern deklarierbar. Der Kern ist laut ADR-0004 ausdrücklich fach-agnostisch; damit ist die Menge der Leerstellen konstant, und ihre Konstanz ist eine Aussage über die Domäne, keine Bequemlichkeit.

Autor:innen beschreiben **wer** und **was falsch läuft**. Dass die simulierte Schüler:in ihrem Fehlermuster konsequent folgt und auch unter Nachfragen nicht aus der Rolle fällt, leistet die Prompt-Vorlage. Prompt-Engineering ist Sache der Administrator:in.

## Der Vertrag

| Vignettenfeld | Prompt | Nutzeransicht |
|---|---|---|
| Fehlermuster-Beschreibung | ja | nein |
| Lernauftrag | ja | ja |
| Arbeitsheft-Beschreibung | ja | nein |
| Arbeitsheft-Inhalt | nein | ja |
| Simulierte Schüler:in (Name, Geschlecht) | ja | ja |
| Erfahrene Lehrperson (Name, Geschlecht) | nein | ja |
| Unterrichtskontext (Fach, Thema, Klassenstufe) | ja | ja |
| Referenzdiagnose | nein | nein |

Der Arbeitsheft-Inhalt bleibt aus dem Prompt heraus, weil er ein Bild sein kann; dafür existiert die Arbeitsheft-Beschreibung (ADR-0005). Die erfahrene Lehrperson bleibt heraus, weil eine simulierte Schüler:in, die weiß, dass ihre Lehrerin zuhört, einen Grund hat, weniger freimütig über ihren Rechenweg zu sprechen — eine Störvariable, die niemand kontrolliert und die pro Vignette anders ausfällt. Die Referenzdiagnose bleibt heraus, weil sie eine Notiz ist (ADR-0009).

**Beide Akteure sind Vignettenfelder**, nicht Kernfelder: Dieselbe Schüler:in dürfte sonst in jeder Klassenstufe und jedem Fach dieselbe sein, und dasselbe gilt eine Rolle weiter für die Lehrperson. Namen und Geschlechter werden im Anlegen-Formular zufällig vorbelegt und sind überschreibbar — der Zufall ist eine Freundlichkeit der Oberfläche, keine Eigenschaft der Domäne. Sie werden mit der Vignette versioniert und beim Finalisieren eingefroren; ein Entwurf aus einer finalen Fassung erbt sie.

Die **Rahmenhandlung ist ebenfalls eine Vorlage**, schöpft aber nicht aus demselben Vertrag: Prompt-Vorlagen und Rahmenhandlung berühren sich nie (ADR-0004) und ziehen aus verschiedenen Spalten obiger Tabelle. Der Vertrag ist deshalb **zwei benannte Mengen, nicht eine**:

- `VERTRAG_PROMPT` — die Felder der Prompt-Spalte, als rohe Werte. System-Prompt- und User-Prompt-Vorlage teilen sich diese Menge; die Tabelle unterscheidet die beiden nicht.
- `VERTRAG_RAHMEN` — die Felder der Nutzeransicht-Spalte, plus abgeleitete grammatische Formen (siehe unten). Aus ihr schöpfen Hospitationseinleitung, Gesprächseinleitung und Debrief.

Eine einzige Menge wäre falsch: Sie erlaubte die Fehlermuster-Beschreibung in der Einleitung, die sie nie sehen darf, und den Namen der erfahrenen Lehrperson im System-Prompt, wo er eine Störvariable wäre.

## Die Nutzeransicht-Spalte ist keine reine Platzhalterliste

Nicht jedes Feld der Nutzeransicht-Spalte wird in die Rahmenhandlung substituiert. Der **Lernauftrag** und der **Arbeitsheft-Inhalt** sind **Ansichtsbausteine**, die die View neben der Rahmenhandlung rendert — der Arbeitsheft-Inhalt kann ein Bild sein und lässt sich nicht in einen `string.Template`-Platzhalter füllen. Substituiert werden nur die kurzen, satzfähigen Werte: die Namen und Geschlechter der Akteure und der Unterrichtskontext.

Weil die Rahmenhandlung Fließtext für Menschen ist, braucht sie Grammatik, die rohe Feldwerte nicht liefern. Der Code berechnet aus dem Geschlecht **abgeleitete grammatische Formen** und stellt sie als eigene Platzhalter in `VERTRAG_RAHMEN` bereit (Anrede, Pronomen, Possessiv). `VERTRAG_RAHMEN` hat damit mehr Einträge als die Nutzeransicht-Spalte Zeilen. Jede neue grammatische Form ist eine Code-Änderung — dieselbe Aussage wie unten über neue Leerstellen, nur über Ableitungen statt über Felder.

## Consequences

- Eine Kern-Fassung lässt sich nur finalisieren, wenn jede ihrer Vorlagen ausschließlich Platzhalter *ihrer* Menge verwendet — Prompt-Vorlagen aus `VERTRAG_PROMPT`, Rahmenhandlungs-Vorlagen aus `VERTRAG_RAHMEN`. Die Prüfung ist ein Teilmengen-Test (`get_identifiers()` ⊆ Menge) und ruft **kein** Modell auf — eine Invariante, die vom Wohlwollen eines externen Anbieters abhinge, wäre keine. Der Vertrag ist eine Obergrenze: Eine Vorlage darf jede Teilmenge verwenden; kein Platzhalter ist verpflichtend.
- Jede der beiden Mengen steht an zwei Orten: im Code, der die Platzhalter bereitstellt, und in der Validierung, die sie prüft. Das sind zwei Listen an je zwei Orten, und jede muss eine bleiben.
- Ein **freies Profilfeld** für die simulierte Schüler:in gibt es nicht. Es wäre die Hintertür, durch die Prompt-Engineering unkuratiert zurückkehrt, und es machte Auskunftsfreude und Ausweichverhalten zwischen Vignetten unvergleichbar. Sollten diese Dimensionen gebraucht werden, gehören sie als benannte Stufen in den Kern — eine additive Änderung.
- **Namenskollisionen werden nirgends geprüft**, auch nicht beim Zusammenstellen einer Erhebung oder eines Trainings. Zwei gleichnamige simulierte Schüler:innen in einer Teilnahme sind ein Darstellungsproblem, kein Datenfehler.
- Eine neue Leerstelle bedeutet ein neues Vignettenfeld, eine Migration und eine Code-Änderung. Ein vom Kern deklarierter Vertrag wurde verworfen: Er hätte das Vorspulen eines Vignettenentwurfs auf einen neueren Kern (ADR-0004) scheitern lassen können, womit der Entwurf auf einem alten Kern gefangen wäre.

## Nachführung (Grilling, Issue #3): Geschlecht, abgeleitete Formen, Lehrperson-Pflicht

Drei Präzisierungen, die die abgeleiteten Formen und die Akteure konkretisieren — keine Widersprüche zum Obigen.

- **Geschlecht ist zweiwertig** (`männlich`/`weiblich`), als benannte Stufen (`TextChoices`). Das ist eine bewusste Domänenaussage, kein Versäumnis: Jede abgeleitete grammatische Form muss eine im Code festgeschriebene, kanonische Fassung haben, und `divers` besitzt im Deutschen keine neutral-etablierte. Der Erweiterungspfad bleibt additiv — eine neue Stufe *plus* ihre kanonische Ableitung, dieselbe Bewegung wie jede neue Leerstelle oben.

- **`VERTRAG_RAHMEN` — konkreter Katalog der abgeleiteten Formen.** `string.Template` dekliniert nicht (ADR-0020), deshalb ist der Katalog bewusst sparsam, und der Vorlagentext formuliert um die Grenzen herum. Je Akteur berechnet der Code aus `{name, geschlecht}`:
  - `$..._pronomen` — **nur Nominativ** (`sie`/`er`),
  - `$..._possessiv` — **unflektierte Grundform** (`ihr`/`sein`); die Deklination nach dem Bezugswort trägt der Vorlagentext,
  - `$..._anrede` — **nur für die Lehrperson** (`Frau`/`Herr`); eine Schüler:in wird beim Vornamen genannt. „Frau Müller" schreibt die Vorlage als `$lehrperson_anrede $lehrperson_name`.

  `VERTRAG_RAHMEN` ist damit: die rohen Nutzeransicht-Werte (`$schuelerin_name`, `$schuelerin_geschlecht`, `$lehrperson_name`, `$lehrperson_geschlecht`, `$fach`, `$thema`, `$klassenstufe`) **plus** `$schuelerin_pronomen`, `$schuelerin_possessiv`, `$lehrperson_pronomen`, `$lehrperson_possessiv`, `$lehrperson_anrede`. `$lernauftrag` und `$arbeitsheft_*` sind **nicht** enthalten (Ansichtsbausteine).

- **Beide Akteure sind Pflicht zum Finalisieren.** Weil eine Rahmenhandlung `$lehrperson_*` verwenden darf, hielte eine leere Lehrperson stille Leerstellen im Fließtext offen; deshalb werden Name und Geschlecht beider Akteure beim Finalisieren verlangt (die Pflichtprüfung selbst lebt in `finalisieren()`, ADR-0021-Nachführung).
