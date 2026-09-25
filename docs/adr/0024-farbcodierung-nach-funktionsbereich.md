---
status: accepted
---

# Farbcodierung nach Funktionsbereich

Erweitert `docs/adr/0023`. Dort ist die Sekundärpalette (Grün, Mint, Blau, Rot, Violett, Gelb × Light/Bright/Dark/Deep) als Primitiv-Token angelegt, aber **ungenutzt** — „bis Kategorie-Kacheln o. Ä. gebaut werden". Diese Entscheidung belegt die Palette: Jeder große Funktionsbereich der Anwendung erhält eine eigene Farbfamilie, damit Teilnehmende, Autor:innen, Forschende und Administrator:innen auf einen Blick erkennen, in welchem Bereich sie sich befinden.

## Festlegungen

- **Bereiche und ihre Farben.**
  - **Grün / Mint** — **Teilnehmen & Trainingspraxis**: die **Teilnehmer:in**-Sicht (Sitzung, Diagnosegespräch, Fragebogen-Items) *und* die **Trainings** (Kataloge, Training starten, eigene Trainings kuratieren), zusammengefasst als das durchgängige Übungserlebnis rund um die Sitzung. Dazu alle globalen Hauptelemente und die Navigation. Gilt unabhängig davon, ob der Zugang über ein **Training** oder eine **Erhebung** erfolgt.
  - **Gelb** — **Autor:in & Entwicklung**: der Aufbau der Simulationsinhalte — der **Vignetten-Editor** und die Verwaltung des **Simulationskerns**.
  - **Violett** — **Forschung & Erhebung**: der Bereich der **Forschende:n** (Erhebungs-Management, Fragebogen-Editor, Datenspur / Export).
  - **Blau** — **System & Administration**: der Bereich der **Administrator:in** (Nutzer- und Rollenverwaltung, **Modell-Konfiguration**).
  - **Rot** — **keine Bereichsfarbe**, sondern reserviert als **Warn- und Gefahrenfarbe** (Fehler, destruktive Aktionen wie das Löschen eines Entwurfs).
- **Vererbung.** Neue Bereiche erben die Farbe ihres Kontexts: neue Teilnahme-/Übungs-Bereiche werden grün, neue Autoren-/Entwicklungs-Bereiche gelb, neue Forschungs-Bereiche violett, neue Systembereiche blau.
- **Manifestation nur im Chrome.** Die Bereichsfarbe tönt ausschließlich das umgebende Chrome — Bereichs-Header, Kacheln, Badges, Kontextmarkierungen. Die **interaktiven Akzente bleiben überall Grün** (Links, Buttons, aktive Navigation, Fokus-Ring), wie in ADR-0023 festgelegt. Die Bereichsfarbe wird nie zum lokalen Button-/Link-Akzent.
- **Anwendung der Töne.** Wie in ADR-0023: farbige Kacheln/Header aus den **Dark**-Tönen mit weisser Schrift, ruhige Flächen/Badges aus den **Light**-Tönen.
- **Sonderregel Gelb.** Bei Gelb trägt nur der **Deep**-Ton sicheren Kontrast mit weisser Schrift; `Dark` (#967231) erreicht auf Weiss nur ~3:1. Für Gelb gilt darum abweichend: **dunkle Schrift auf hellem Gelb** statt „Dark-Ton + weiss".

## Nachtrag: Die aktive Navigation trägt die Bereichsfarbe

Der Aktiv-Indikator der Sidebar war grün, auch in gelb, violett oder blau gekennzeichneten Gruppen. Neben der gelben Gruppe »Entwicklung« und der grünen »Ausbildung« darunter wirkte das dissonant (#287). Die **aktive Navigation fällt deshalb aus den grünen Akzenten heraus**. Buttons, Links und der Fokus-Ring bleiben grün (ADR-0023).

- **Aktiv:** Fläche im Tint-Ton der Gruppe (`--color-area-*-tint`), 3-px-Balken links im Solid-Ton (`--color-area-*-solid`), Schrift neutral dunkel (`--color-text`).
- **Hover:** halbe Tint-Fläche, Balken im aufgehellten Solid-Ton, dunkle Schrift, keine Unterstreichung.
- **Kontrast:** Die Schrift ist nie in Bereichsfarbe; dunkle Schrift erreicht auf allen Tints mindestens 8:1. Der Balken ist ein grafisches Element (WCAG 1.4.11, 3:1). Gelb-Dark erreicht auf Weiss 4,42:1, auf Gelb-Light 4,2:1; beides genügt dafür. Die Gelb-Sonderregel bleibt dadurch unberührt.
- **Zuordnung:** »Simulationskern verwalten« wandert in der Sidebar von »System« nach »Entwicklung«, wie die Seiten des Simulationskerns schon oben festgelegt. Jede Seite trägt die Bereichsklasse ihrer Sidebar-Gruppe; die Überzeile nennt Gruppe und Eintrag (»Entwicklung / Simulationskern«).

## Considered Options

- **Rot als Bereichsfarbe (System) vs. Rot als reine Warnfarbe** — gewählt: **Warnfarbe**, System auf **Blau**. Rot ist konventionell die Farbe für Fehler und destruktive Aktionen. Als zugleich flächige Bereichsfarbe würde es das Signal „Achtung, gefährlich" verwässern. Blau war ohnehin die einzige noch freie Sekundärfamilie.
- **Bereichsfarbe als lokaler Akzent (Buttons/Links) vs. nur Chrome tönen** — gewählt: **nur Chrome**. Durchgängig eingefärbte Bedienelemente je Bereich kosten Konsistenz und scheitern am Kontrast — Gelb ist als Button-/Link-Farbe praktisch untauglich. Grün als einzige Interaktionsfarbe bleibt überall gleich lesbar.
- **Blau als Reserve halten vs. für System nutzen** — gewählt: **nutzen**. Das Freimachen von Rot als Warnfarbe verlangte eine Ersatzfarbe für den System-Bereich; Blau ist dafür naheliegend (technisch-neutrale Konnotation).

## Consequences

- **Verfeinerte Zuordnung gegenüber der ersten Fassung.** Die **Trainings** wandern vom Autoren-Bereich (Gelb) in den Teilnahme-/Übungs-Bereich (**Grün**), weil Katalog, Trainingsstart und Sitzung ein zusammenhängendes Übungserlebnis bilden. Der **Simulationskern** wandert vom System-Bereich (Blau) in den Autoren-/Entwicklungs-Bereich (**Gelb**), weil er zum Aufbau der Simulationsinhalte gehört. **Modell-Konfiguration** und **Administration** bleiben System (Blau). Die Sidebar-Navigation (`static/css/navigation.css`, `templates/includes/sidebar.html`) setzt genau diese Zuordnung um.
- Die Sekundärpalette aus ADR-0023 ist damit nicht mehr ungenutzt. `static/css/tokens.css` erhält semantische Bereichs-Tokens (z. B. `--color-area-authoring-*`, `--color-area-research-*`, `--color-area-system-*`), abgeleitet aus den `--phsg-*`-Primitiven — Feature-UIs verwenden diese Tokens, nicht direkt Hex-Werte.
- Ein eigenes Gefahr-Token (aus der Rot-Familie, z. B. `red-dark` / `red-deep`) wird für Fehlerzustände und destruktive Aktionen eingeführt; es ist von jeder Bereichsfarbe getrennt.
- **Kein Widerspruch zu ADR-0023:** „Grün ist die (interaktive) Akzentfarbe" bleibt gültig, weil die Bereichsfarben nur das Chrome tönen. Aufgehoben wird allein die dortige Feststellung, die Sekundärpalette sei „vorerst ungenutzt".
- Die Gelb-Sonderregel ist die einzige Abweichung von der ADR-0023-Regel „Text auf Farbflächen stets weiss"; sie ist auf die Gelb-Familie beschränkt.
- Dark Mode bleibt wie in ADR-0023 offen; die Trennung Primitiv/semantisch trägt die Bereichs-Tokens mit.
