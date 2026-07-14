---
status: accepted
---

# Farbcodierung nach Funktionsbereich

Erweitert `docs/adr/0023`. Dort ist die Sekundärpalette (Grün, Mint, Blau, Rot, Violett, Gelb × Light/Bright/Dark/Deep) als Primitiv-Token angelegt, aber **ungenutzt** — „bis Kategorie-Kacheln o. Ä. gebaut werden". Diese Entscheidung belegt die Palette: Jeder große Funktionsbereich der Anwendung erhält eine eigene Farbfamilie, damit Teilnehmende, Autor:innen, Forschende und Administrator:innen auf einen Blick erkennen, in welchem Bereich sie sich befinden.

## Festlegungen

- **Bereiche und ihre Farben.**
  - **Grün / Mint** — das Kernerlebnis: die **Teilnehmer:in**-Sicht (Sitzung, Diagnosegespräch, Fragebogen-Items) sowie alle globalen Hauptelemente und die Navigation. Gilt für die Teilnehmer:in unabhängig davon, ob der Zugang über ein **Training** oder eine **Erhebung** erfolgt.
  - **Gelb** — die **Ausbildungspraxis**: der Bereich der **Autor:in** (Vignetten-Editor) und der **Ausbilder:in** (Trainings).
  - **Violett** — **Forschung & Erhebung**: der Bereich der **Forschende:n** (Erhebungs-Management, Fragebogen-Editor, Datenspur / Export).
  - **Blau** — **System & Administration**: der Bereich der **Administrator:in** (Nutzer- und Rollenverwaltung, **Modell-Konfiguration**, **Simulationskern**).
  - **Rot** — **keine Bereichsfarbe**, sondern reserviert als **Warn- und Gefahrenfarbe** (Fehler, destruktive Aktionen wie das Löschen eines Entwurfs).
- **Vererbung.** Neue Bereiche erben die Farbe ihres Kontexts: neue Ausbildungs-Bereiche werden gelb, neue Forschungs-Bereiche violett, neue Systembereiche blau.
- **Manifestation nur im Chrome.** Die Bereichsfarbe tönt ausschließlich das umgebende Chrome — Bereichs-Header, Kacheln, Badges, Kontextmarkierungen. Die **interaktiven Akzente bleiben überall Grün** (Links, Buttons, aktive Navigation, Fokus-Ring), wie in ADR-0023 festgelegt. Die Bereichsfarbe wird nie zum lokalen Button-/Link-Akzent.
- **Anwendung der Töne.** Wie in ADR-0023: farbige Kacheln/Header aus den **Dark**-Tönen mit weisser Schrift, ruhige Flächen/Badges aus den **Light**-Tönen.
- **Sonderregel Gelb.** Bei Gelb trägt nur der **Deep**-Ton sicheren Kontrast mit weisser Schrift; `Dark` (#967231) erreicht auf Weiss nur ~3:1. Für Gelb gilt darum abweichend: **dunkle Schrift auf hellem Gelb** statt „Dark-Ton + weiss".

## Considered Options

- **Rot als Bereichsfarbe (System) vs. Rot als reine Warnfarbe** — gewählt: **Warnfarbe**, System auf **Blau**. Rot ist konventionell die Farbe für Fehler und destruktive Aktionen. Als zugleich flächige Bereichsfarbe würde es das Signal „Achtung, gefährlich" verwässern. Blau war ohnehin die einzige noch freie Sekundärfamilie.
- **Bereichsfarbe als lokaler Akzent (Buttons/Links) vs. nur Chrome tönen** — gewählt: **nur Chrome**. Durchgängig eingefärbte Bedienelemente je Bereich kosten Konsistenz und scheitern am Kontrast — Gelb ist als Button-/Link-Farbe praktisch untauglich. Grün als einzige Interaktionsfarbe bleibt überall gleich lesbar.
- **Blau als Reserve halten vs. für System nutzen** — gewählt: **nutzen**. Das Freimachen von Rot als Warnfarbe verlangte eine Ersatzfarbe für den System-Bereich; Blau ist dafür naheliegend (technisch-neutrale Konnotation).

## Consequences

- Die Sekundärpalette aus ADR-0023 ist damit nicht mehr ungenutzt. `static/css/tokens.css` erhält semantische Bereichs-Tokens (z. B. `--color-area-authoring-*`, `--color-area-research-*`, `--color-area-system-*`), abgeleitet aus den `--phsg-*`-Primitiven — Feature-UIs verwenden diese Tokens, nicht direkt Hex-Werte.
- Ein eigenes Gefahr-Token (aus der Rot-Familie, z. B. `red-dark` / `red-deep`) wird für Fehlerzustände und destruktive Aktionen eingeführt; es ist von jeder Bereichsfarbe getrennt.
- **Kein Widerspruch zu ADR-0023:** „Grün ist die (interaktive) Akzentfarbe" bleibt gültig, weil die Bereichsfarben nur das Chrome tönen. Aufgehoben wird allein die dortige Feststellung, die Sekundärpalette sei „vorerst ungenutzt".
- Die Gelb-Sonderregel ist die einzige Abweichung von der ADR-0023-Regel „Text auf Farbflächen stets weiss"; sie ist auf die Gelb-Familie beschränkt.
- Dark Mode bleibt wie in ADR-0023 offen; die Trennung Primitiv/semantisch trägt die Bereichs-Tokens mit.
