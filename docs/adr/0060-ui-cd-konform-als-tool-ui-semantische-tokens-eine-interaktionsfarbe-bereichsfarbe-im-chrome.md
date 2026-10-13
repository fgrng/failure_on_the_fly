---
status: accepted
---

# UI: CD-konform als Tool-UI, semantische Tokens, eine Interaktionsfarbe, Bereichsfarbe nur im Chrome

Dieses ADR fasst die Regeln aus ADR-0023 und ADR-0024 (samt Nachführungen
durch #168 und #308) zusammen und ersetzt beide. Die konkreten Werte, die
beide ADRs mitführten (Hex-Werte, Rasterbreiten, Umbruchpunkte,
Sidebar-Zustände, welche Seite in welchem Bereich liegt), stehen nicht mehr in
einem ADR. Ihre Quelle der Wahrheit ist der Code: `static/css/tokens.css` für
Farben und Abstände, die Layout-Stylesheets für das Raster, die Sidebar
(`templates/includes/sidebar.html`) und die Bereichsklasse jeder Seite für die
Zuordnung. `docs/bildsprache/farbpalette.html` visualisiert den Stand.

## CD-konform, aber ein eigenständiges Tool-UI

Die Oberfläche folgt dem Corporate Design der PHSG (Guidelines 2026). Das CD
ist für einen Marketing-Webauftritt gedacht; FailureOnTheFly ist ein
Forschungs- und Trainingsinstrument mit datendichten Ansichten
(Vignetten-Editor, Erhebungs-Management, Transkripte) und einer ruhigen
Gesprächssitzung. Deshalb wird das CD als **CD-konformes, aber eigenständiges
Tool-UI** übernommen: Typografie und Palette stammen aus dem CD, großflächige
Marketing-Farbflächen, Logo, Bildwelt und Pattern bleiben weg. Wo das CD einen
Wert nur für Marketing-Lesbarkeit setzt, darf das Tool-UI aus der aktuellen
CD-Skala einen besser lesbaren wählen (etwa dunklerer Lesetext als `#666`);
Werte außerhalb des aktuellen Farbsystems sind nicht zulässig. Vorerst nur
Light Mode.

## Farben werden nach Rolle vergeben: semantische Tokens

Die Primitiv-Tokens (`--phsg-*`) spiegeln die offizielle Palette 1:1 und sind
nur Quelle. Alles, was eine Oberfläche benutzt, sind **semantische Tokens**
(Lesetext, Sekundärtext, Akzent, Flächen, Rahmen, Bereichsfarben, Gefahr,
Status). Feature-CSS verwendet ausschließlich semantische Tokens, nie
Hex-Werte und nie `--phsg-*`-Primitive. Die Trennung Primitiv/semantisch ist
auch die Vorbereitung auf einen Dark Mode: Er überschriebe die semantischen
Tokens je Theme.

Abstände folgen einem **8-px-Raster** als Tokens; es gilt für `gap`, `margin`,
`padding` und positionierende Abstände, nicht für optische Maße wie
Rahmenbreiten, Radien, Schriftgrößen und Fokus-Offsets. Das Seitenraster
folgt dem Achterraster des CD; Umbruchpunkte und die Aufteilung nummerierter
Abschnitte sind Projektentscheidungen, die in den Stylesheets stehen.

## Eine Interaktionsfarbe, Bereichsfarbe nur im Chrome, Rot nur für Gefahr

- **Grün ist die einzige Interaktionsfarbe**: Links, Buttons, Fokus-Ring,
  überall gleich. Die Aktiv-Markierung der Sidebar ist davon ausgenommen und
  trägt den Ton ihrer Gruppe (#308), weil ein grüner Indikator in einer gelben
  oder violetten Gruppe dissonant wirkt.
- **Jeder Funktionsbereich hat eine Farbfamilie** aus der Sekundärpalette,
  damit Teilnehmende, Autor:innen, Forschende und Administrator:innen auf
  einen Blick erkennen, wo sie sind: Teilnehmen und Trainingspraxis,
  Autor:in und Entwicklung, Forschung und Erhebung, System und
  Administration. Neue Bereiche erben die Farbe ihres Kontexts. Welche Familie
  welchem Bereich gehört und welche Seite in welchem Bereich liegt, sagt der
  Code (Bereichs-Tokens, Sidebar-Gruppen, Bereichsklasse der Seite); ein
  Umzug einer Seite wie die Kern-Verwaltung (#168, #308) ist eine Codeänderung
  und keine Nachführung dieses ADR.
- **Die Bereichsfarbe tönt nur das Chrome**: Bereichs-Header, Kacheln, Badges,
  Kontextmarkierungen. Sie wird nie zum lokalen Button- oder Link-Akzent.
  Durchgängig eingefärbte Bedienelemente je Bereich kosten Konsistenz und
  scheitern am Kontrast.
- **Rot ist keine Bereichsfarbe**, sondern reserviert für Fehler und
  destruktive Aktionen. Als zugleich flächige Bereichsfarbe würde es das
  Signal „Achtung" verwässern.
- **Text auf Farbflächen ist weiß**, aus den Dark-Tönen; ruhige Flächen und
  Badges aus den Light-Tönen. Die Ausnahme ist eine Kontrastregel: Wo ein
  Dark-Ton mit weißer Schrift keinen sicheren Kontrast erreicht (heute Gelb),
  gilt dunkle Schrift auf hellem Ton. Schrift ist nie in Bereichsfarbe; Balken
  und Flächen sind grafische Elemente nach WCAG 1.4.11.

## Keine Fremd-Requests

Schriften (Platypi für Überschriften, Albert Sans für alles andere), htmx und
Alpine werden **self-hosted** ausgeliefert, kein Google-Fonts- oder
CDN-Request. Das passt zum Datenschutzanspruch eines Forschungsinstruments mit
Pseudonymisierung und Einzelinstanz-Deployment. Ein Mono-Token bleibt ein
reiner System-Stack, weil dafür keine Schriftdatei bezogen wird; feste
Laufweite ist Zeichenfolgen vorbehalten, die Zeichen für Zeichen abgetippt
werden (Teilnahme-Token), nicht Fließtext oder Transkripten.

## Erwogene Optionen

- **Möglichst starke Angleichung an die PHSG-Website** — verworfen.
  Großflächige Marketing-Farbflächen schaden der Lesbarkeit datendichter
  Ansichten.
- **Alt-Werte aus der CD-Zusammenfassung (`#666666`)** — verworfen. Sie sind
  im aktuellen Farbsystem nicht enthalten; gewählt wird der nächste Wert der
  aktuellen Grauskala, und für Primärtext ein dunklerer, weil `#666` in
  Formularen und Tabellen auf Dauer zu schwach ist.
- **Google Fonts und unpkg-CDN** — verworfen; Fremd-Requests bei jedem
  Seitenaufruf.
- **Rot als Bereichsfarbe für System** — verworfen; Rot bleibt Warnfarbe,
  System bekommt die letzte freie Sekundärfamilie.
- **Bereichsfarbe als lokaler Akzent** — verworfen; Gelb ist als Button- und
  Linkfarbe praktisch untauglich, Grün bleibt überall gleich lesbar.
- **Die Zuordnung Seite zu Bereich im ADR führen** — so bis ADR-0024;
  verworfen, weil sie sich mit jedem UI-Ticket ändert und zweimal in einem
  Quartal gedriftet ist. Der Code trägt sie.

## Folgen

- Neue Feature-UIs verwenden ausschließlich semantische Tokens; ein Hex-Wert
  oder ein `--phsg-*`-Token in Feature-CSS ist ein Verstoß.
- Font- und Lib-Dateien liegen im Repo unter `static/`; bei Updates werden sie
  neu bezogen.
- Eine neue Seite trägt die Bereichsklasse ihrer Sidebar-Gruppe
  (`konten/tests/test_navigation.py` prüft das); die Überzeile nennt Gruppe und
  Eintrag.
- Wer einen Bereich hinzufügt, braucht eine freie Sekundärfamilie oder eine
  Revision dieses ADR; die Sekundärpalette ist mit vier Bereichen und Rot
  belegt.
- Dark Mode bleibt offen; die Token-Trennung trägt ihn.
