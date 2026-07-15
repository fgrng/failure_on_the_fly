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

## Bereichs-Farbcodierung (Entscheidung)

Erweitert ADR-0023 (Sekundärpalette war „angelegt, aber ungenutzt"). Belegt jetzt:

| Bereich | Farbe |
|---|---|
| Teilnehmende & Kern (Sitzung, Fragebogen, Hauptelemente) | **Grün / Mint** |
| Ausbildungspraxis (Autor:innen, Trainings; neue Ausbildungs-Bereiche) | **Gelb** |
| Forschung & Erhebung (Erhebungs-Management, Export; neue Forschungs-Bereiche) | **Violett** |
| System & Administration (Nutzerverwaltung, Modell-Konfiguration, Simulationskern; neue Systembereiche) | **Blau** |
| *(Rot)* | **Warn-/Gefahrenfarbe** — kein Bereich (Fehler, destruktive Aktionen) |

**Entschieden:** Bereichsfarbe tönt nur das **Chrome** (Header, Kacheln, Badges); interaktive
Grün-Akzente (Buttons, Links) bleiben überall konsistent. Visualisiert in `farbpalette.html`.

**Rest-Punkt (vor ADR-Formalisierung):**
- **Gelb + weisse Schrift:** Nur der Deep-Ton trägt sicheren Kontrast; ADR-Regel „Dark-Ton + weiss"
  greift bei Gelb nicht. Sonderregel nötig (dunkle Schrift auf hellem Gelb).

## Herstellung

Generiert mit `agy` (Nano Banana 2 / Google-Bildmodell), Prompt je Stil identisch bis auf die
Stil-Direktive. Die nicht gewählten Varianten bleiben Wegwerf-Material zur Stilentscheidung.

## Verdict

**Aquarell** gewählt, verwischter Brushstroke-Look, **Erste-Person-POV** (Teilnehmer:in = Nutzerin,
nie im Bild).

**Erzähllogik (3 Beats):**
1. **Hospitation / Einstieg** — Blick aus der hinteren Reihe nach vorne; ganzer Klassenraum,
   Lehrperson vorne läutet die Arbeitsphase ein. **Gewählt: Variante B (Schulklasse, luftig)**
   → `originale/hospitation-einstieg-b.png`.
2. **Gesprächsanlass** — über die Schulter aufs Arbeitsheft (Fehlermuster). **Gewählt: pov-a
   (klar & mittig)** → `originale/hospitation-pov-a.png`. Heft-Inhalt bewusst abstrakt, ohne
   Mathe-Symbole.
3. **Debrief** — erfahrene Lehrperson fragt nach der Diagnose. **Gewählt: Version 1 (frontal,
   aufgelöstes Gesicht)** → `originale/szene-debrief.png`.

**Drei Kern-Bilder gesetzt:** Einstieg B · Gesprächsanlass pov-a · Debrief V1.
Die 1024²-Originale bleiben unter `originale/`. Für die Sitzungsansicht liegen
auf 800² skalierte WebP-Exporte unter `static/images/session/`:

- `rahmenhandlung-einstieg.webp`
- `gespraechsanlass.webp`
- `rahmenhandlung-debrief.webp`

Nächster Block: restliche Bildsprache (Buttons, Rahmungen, Icons, abstrakter Sprecher-Anker im Gespräch).
