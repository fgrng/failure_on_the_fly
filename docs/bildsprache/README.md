# Bildsprache — Exploration

**Frage:** Welchen Illustrationsstil soll die Bildsprache der App tragen? Ausgangspunkt
sind drei feste Rahmenhandlungs-Bilder (Einstieg, Hospitation, Debrief) — laut
`CONTEXT.md` gehört die Rahmenhandlung dem Simulationskern, nicht der einzelnen Vignette,
also sind es *wenige feste* Bilder, kein pro-Vignette-Bedarf.

**Stand:** offen. Erste Vergleichsrunde an *einer* Szene (der Hospitation) generiert.

## Kandidaten

`moodboard.html` (self-contained, im Browser öffnen) stellt drei Stile derselben Szene
gegenüber:

- **Line-and-Wash** (Synthese) — grüne Aquarell-Lasur + feine Tuschelinie. Vorläufige Empfehlung.
- **Aquarell** — Entkonkretisierung durch Verschwimmen; am wärmsten, am meisten Beiwerk.
- **Line-Art** — Entkonkretisierung durch Weglassen; am nächsten am bestehenden Line-Icon-UI.

Originale (1024²) in `originale/`.

## Vorgaben an alle Bilder

- Möglichst abstrakt, **keine** Geschlechts-, Alters- oder Herkunftshinweise; kein Gesicht
  (vgl. `CONTEXT.md`, _Avoid: Avatar_).
- PHSG-Palette aus `static/css/tokens.css`; Grün als einzige Akzentfarbe, warmer Papier-Grund.
- Keine lesbare Schrift im Bild (verhunzen Bildmodelle).

## Offener Vorbehalt

Das Bildmodell gibt der stehenden Figur hartnäckig ein Gesichtsprofil + Frisur. Nächste Runde:
strikt von hinten, nur Hinterköpfe erzwingen.

## Herstellung

Generiert mit `agy` (Nano Banana 2 / Google-Bildmodell), Prompt je Stil identisch bis auf die
Stil-Direktive. Wegwerf-Material zur Stilentscheidung — **nicht** die finalen Assets.

## Verdict

> _(offen — hier eintragen, sobald die Stilrichtung gewählt ist)_
