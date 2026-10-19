---
status: accepted
---

# Die Kantenrichtung gilt auch für Templates, Links sind frei, und `texte` ist Querschnitt für alle Apps

Dieses ADR führt ADR-0055 nach. Dessen Kantentabelle bewacht
`config/tests/test_importgraph.py`, und der Wächter liest nur Python. In den
Templates zeigen Includes und Tag-Bibliotheken deshalb gegen die Richtung,
ohne dass ein Test bricht: `simulation` bindet ein Formularfeld aus
`vignetten` und ein Icon aus `erhebungen` ein, die unterste Domänen-App hängt
also an der obersten; `fragebogen_items` bindet dasselbe Formularfeld ein;
`simulation` und `vignetten` laden die Tag-Bibliothek und die Lesefelder von
`texte`. Seit dem Review kamen weitere solche Includes hinzu (#474, B-8 aus
#458).

## Was als Kante zählt

Die Kantenrichtung aus ADR-0055 gilt für Templates genauso wie für Python. Ein
Template zeigt auf eine App, wenn es

- per `{% include %}` oder `{% extends %}` ein Template dieser App einbindet,
- per `{% load %}` eine Tag-Bibliothek dieser App lädt.

Ein Template gehört der App, deren Namen der erste Teil seines Template-Namens
trägt (`vignetten/detail.html` gehört `vignetten`). Das ist die Ablage, die
Django mit `<app>/templates/<app>/` ohnehin nahelegt, und sie wird damit zur
Regel. Eine Tag-Bibliothek gehört der App, in deren `templatetags` sie liegt.

Die globalen Templates unter `templates/` gehören keiner App und liegen unter
allen: Jede App darf sie einbinden, sie selbst binden kein App-Template ein und
laden keine App-Bibliothek. Sonst würden sie zur Waschanlage, über die eine
verbotene Kante doch entsteht.

## Was nicht als Kante zählt

Ein **Link per URL-Name** (`{% url %}`) ist Navigation, keine Abhängigkeit
beim Rendern. Er bleibt in jede Richtung frei, wie ADR-0046 es für
`vignetten → evals` schon hält. Die Vignetten-Detailseite darf einen Probelauf
in `sitzungen` starten, die Abschlussseite einer Erhebung auf die Abschriften
in `training` verweisen. Ein Verbot verlangte, dass Views fertige URLs an ihre
Templates durchreichen, nur um eine Navigation zu verbergen, die fachlich
gewollt ist.

Der Preis ist bewusst: Wer einen URL-Namen umbenennt oder seine Argumente
ändert, bricht auch die Templates anderer Apps, die ihn verlinken. Djangos
`NoReverseMatch` macht das beim Rendern sichtbar, und die View-Tests fangen es.

## `texte` ist Querschnitt für alle Apps

ADR-0055 nennt `texte` Querschnitt, lässt aber nur `sitzungen`, `erhebungen`
und `training` darauf zeigen. Ab jetzt darf **jede App außer `konten`** auf
`texte` zeigen, in Python wie in Templates. `texte` selbst zeigt weiter nur auf
`konten`; eine Kante nach `texte` kann deshalb keinen Zyklus schließen, außer
aus `konten`.

Die Lesefelder bleiben in `texte`. Sie laden die Tag-Bibliothek von `texte`
und schicken die Vorschau an die Route `texte:vorschau`; global abgelegt,
hingen sie genauso an `texte`, nur dass der Wächter es nicht mehr sähe.

## Generische Bausteine liegen global

Ein Baustein ohne Domänenbezug, etwa ein Formularfeld oder ein Icon, liegt
unter `templates/includes/`, neben `eigentuemerinnen.html` und
`sidebar.html`. In einer App liegt ein Baustein nur, wenn er deren
Domänenobjekte zeigt. Dass ein generischer Baustein zuerst in einer App
gebraucht wurde, ist kein Grund, ihn dort zu lassen.

## Der Wächter

Neben dem Importgraphen prüft ein Test die Templates gegen **dieselbe**
Kantentabelle: jedes `{% include %}`, `{% extends %}` und `{% load %}` in den
Templates jeder App, dazu die Regel für die globalen Templates. Eine Kante
hinzuzufügen bleibt eine Aussage über die Architektur und gehört in ein ADR
(ADR-0055).

Der Wächter liest Template-Namen als Text. Ein Include, dessen Name erst zur
Laufzeit in einer Variable steht, sieht er nicht. Solche Includes gibt es
heute nicht; über App-Grenzen hinweg sind sie zu vermeiden.

## Erwogene Optionen

- **Nur Python bewachen, Templates frei lassen** — verworfen. Ein Template,
  das ein Partial einer anderen App einbindet, bricht bei deren Umbau genauso
  wie ein Import; „`simulation` kennt keine Vignette“ wäre nur halb wahr.
- **Auch Links per URL-Name binden** — verworfen. Siehe oben: Die Navigation
  ist fachlich gewollt, und der Umweg über durchgereichte URLs verbirgt sie
  nur.
- **Die Lesefelder von `texte` global ablegen** — verworfen. Sie blieben über
  Tag-Bibliothek und Vorschau-Route an `texte` gebunden; die Kante wäre nur
  versteckt.
- **`texte` nur für Templates freigeben** — verworfen. Templates von
  `simulation` dürften dann Markdown rendern, ihr Python-Code nicht, obwohl
  beide dieselbe App sind.
- **Den Wächter weglassen und die Regel nur festschreiben** — verworfen.
  Zwischen Review und Triage kamen zwei weitere Includes gegen die Richtung
  hinzu; ohne Test driftet die Regel.

## Folgen

- Formularfeld und Icon ziehen nach `templates/includes/`, alle Includes
  werden umgestellt.
- Die Kantentabelle in `config/tests/test_importgraph.py` erlaubt `texte` für
  `fragebogen_items`, `simulation`, `vignetten` und `evals`, und ein zweiter
  Test wendet sie auf Templates an.
- Die Ablage der Templates innerhalb einer App bleibt frei (ADR-0055); bindend
  ist nur, worauf ein Template über App-Grenzen zeigt.
