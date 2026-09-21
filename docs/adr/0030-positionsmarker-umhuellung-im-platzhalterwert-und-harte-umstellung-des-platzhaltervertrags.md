---
status: accepted
---

# Positionsmarker im Text, Umhüllung im Platzhalterwert und harter Schnitt am Platzhaltervertrag

Der Aufgabenkontext einer Vignette besteht aus zwei gleich gebauten Teilen:
Lernauftrag und Arbeitsheft. Beide Teile tragen jeweils vier Angaben: Text, ein
optionales Bild, eine Bildbeschreibung und Simulationshinweise. Drei
wesentliche Architekturentscheidungen prägen dieses Modell:

## 1. Positionsmarker im Text anstelle eines separaten Layout-Feldes

Autor:innen bestimmen das Verhältnis von Text und Bild über den Positionsmarker
`[bild]` direkt im jeweiligen Textfeld (`lernauftrag_text` bzw.
`arbeitsheft_text`). Was vor dem Marker steht, erscheint über dem Bild; was
danach steht, darunter. Ein separates Layout-Feld (z. B. ein Dropdown „Bild vor
oder nach dem Text") oder ein block-basierter Editor wurden verworfen:

- **Einfachheit der Oberfläche:** Die Textfelder bleiben Klartext ohne
  zusätzliche Auswahlelemente oder Layout-Metadaten. Der Marker wird im
  Hilfetext des Textfeldes erklärt.
- **Fehlertoleranz:** Ohne Marker steht das Bild standardmäßig unter dem Text.
  Enthält der Text einen `[bild]`-Marker, ohne dass ein Bild hochgeladen ist,
  wird der Marker ersatzlos entfernt, ohne dass ein Validierungsfehler den
  Entwurf blockiert. Gibt es mehrere Marker, gewinnt der erste und alle weiteren
  werden entfernt.
- **Zentrale Zerlegung:** Dieselbe Modellfunktion zerlegt den Text in die Teile
  vor und nach dem Marker. Sie wird synchron für die Webansicht (Einsetzen des
  Bildes) und den Prompt (Einsetzen der Bildbeschreibung) verwendet.

## 2. Umhüllung als Eigenschaft des Platzhalterwerts anstelle der Kern-Vorlage

Die Werte der langen Inhaltsfelder (`$fehlermuster_beschreibung`, `$lernauftrag`,
`$arbeitsheft`, `$lernauftrag_simulationshinweise`,
`$arbeitsheft_simulationshinweise`) werden bei der Ersetzung in XML-artige Tags
`<feldname>...</feldname>` gefasst. Diese Umhüllung geschieht in der
Platzhalter-Funktion der Vignette und ist damit eine Eigenschaft des
eingesetzten *Wertes*, nicht der Kern-Vorlage:

- **Schlanke Kern-Vorlagen:** Die Kern-Vorlage enthält nur noch den nackten
  Platzhalter (z. B. `$lernauftrag`) und bleibt frei von manuell gepflegten
  XML-Umgebungen.
- **Keine leeren Umgebungen:** Ist ein Feld leer, erzeugt es keine Umgebung
  (leerer String). Stünden die Tags in der Vorlage, blieben leere Hüllen wie
  `<lernauftrag_simulationshinweise></lernauftrag_simulationshinweise>` im
  Prompt stehen, die das Sprachmodell als fehlende Information fehldeuten
  könnte.
- **Erhalt der Positionsinformation:** Steht der Marker mitten im Text,
  erzeugt die Platzhalter-Funktion zwei `<..._text>`-Umgebungen um die
  `<..._bildbeschreibung>` herum. Damit bleibt die Positionsinformation des
  Markers für das Modell präzise erhalten.

## 3. Harter Schnitt am Platzhaltervertrag

Der Prompt-Platzhaltervertrag (ADR-0010) wurde ohne Rückwärtskompatibilität neu
gefasst. Der alte Platzhalter `$arbeitsheft_beschreibung` entfällt ersatzlos;
an seine Stelle treten die komponierten Platzhalter `$lernauftrag` und
`$arbeitsheft` sowie die getrennten `$lernauftrag_simulationshinweise` und
`$arbeitsheft_simulationshinweise`:

- **Bewusste Entscheidung:** Dieser harte Schnitt wurde unter der expliziten
  Zusicherung getroffen, dass **keine Produktivdaten** existieren.
- **Strikte Substitution:** Da die Prompt-Substitution strikt ist, hätten alte
  gepinnte Kern-Fassungen mit dem alten Platzhalter zur Laufzeit gefehlt. Durch
  die Umschreibung des Standardkerns und die Anpassung der Tests wird
  Kompatibilitätsballast im Code vermieden.

## Folgen

- Das Vignettenmodell ist die alleinige Quelle der Wahrheit für die
  Marker-Zerlegung und Umhüllung.
- Kern-Vorlagen arbeiten mit nackten Platzhaltern und überlassen die Strukturierung
  dem Platzhalterwert.
- Nutzereingaben werden nicht escaped, da es sich um Prompts und nicht um XML
  handelt.
