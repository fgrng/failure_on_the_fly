---
status: accepted
---

# UI-Design-Tokens auf Basis des PHSG Corporate Design

Die Nutzer-Oberfläche soll dem Corporate Design der PHSG (Guidelines 2026) folgen. Das CD ist jedoch für einen **Marketing-Webauftritt** gedacht, während FailureOnTheFly ein **Forschungs- und Trainingsinstrument** mit datendichten Ansichten (Vignetten-Editor, Erhebungs-Management, Transkripte) und einer ruhigen Gesprächssitzung ist. Wir übernehmen das CD deshalb als **CD-konformes, aber eigenständiges Tool-UI**: Farben werden nach Rolle vergeben (semantische Tokens), nicht flächig nach Farbname.

## Festlegungen

- **Farben (semantische Tokens in `static/css/tokens.css`).** Die Primitiv-Tokens (`--phsg-*`) spiegeln die offizielle Palette 1:1; die semantischen Tokens leiten daraus Rollen ab:
  - Lesetext `--color-text` = Grayscale-900 `#383836`.
  - Sekundärtext `--color-text-muted` = Grayscale-700 `#6f7170` (**Option A**, siehe unten).
  - Akzent (Links, Buttons, aktive Nav) = Dark-Grün `#009b56`; Hover = Deep-Grün `#2c512c`; Fokus = Bright-Grün `#1fc070`.
  - Flächen: Weiss `#ffffff`, Muted `#f5f7f6` (Grayscale-050), Rahmen `#d8dad9` (Grayscale-200).
  - Footer = Deep-Mint `#1c3e37`, Text darauf weiss.
  - Text auf Farbflächen stets weiss; farbige Boxen/Kacheln später aus den **Dark**-Tönen der Sekundärpalette.
- **Typografie.** Platypi (Serif) für Überschriften, Albert Sans (Sans-Serif) für alles andere — beides **self-hosted** (`static/fonts/`, `static/css/fonts.css`), kein Google-Fonts-Request.
- **Spacing.** 8×8-Raster als `--space-1 … --space-8` (8px-Schritte).
- **Frontend-Libs.** htmx und Alpine werden **lokal ausgeliefert** (`static/js/`) statt per CDN — gleiche Datenschutz-Begründung wie bei den Fonts.
- **Vorerst nur Light Mode.** Dark Mode ist nicht ausgeschlossen, aber nicht Teil dieser Entscheidung.
- **Logo, Bildwelt, PHSG-Pattern: bewusst weggelassen.** Logo ausgeklammert; Kampagnenbilder und Pattern erfordern Freigabe der Stabsstelle Marketing und Kommunikation; ein Tool-UI braucht keine Bildwelt.

## Considered Options

- **Muted-Text `#666666` (CD-Zusammenfassung) vs. Grayscale-700 `#6f7170` (Option A)** — gewählt: **A**. `#666666` ist im offiziellen neuen Farbsystem gar nicht enthalten; es ist der als „altes CD, unverändert" geführte Alt-Wert. `#6f7170` bleibt vollständig in der aktuellen Grauton-Skala. Der etwas geringere Kontrast (~4,7:1 statt ~5,7:1 auf Weiss) ist vertretbar, da Muted-Text nur Sekundärinfo trägt.
- **Lesetext `#666666` gemäss CD vs. `#383836`** — gewählt: `#383836`. In einem Formular-/Tabellen-Tool ist `#666` als Primärtext auf Dauer zu schwach.
- **Self-hosted Assets vs. Google-Fonts-/unpkg-CDN** — gewählt: self-hosted. Passt zum Datenschutz-Anspruch eines Forschungsinstruments mit Pseudonymisierung und Einzelinstanz-Deployment; keine Fremd-Requests bei jedem Seitenaufruf.
- **Möglichst starke Angleichung an die PHSG-Website vs. eigenständiges Tool-UI** — gewählt: eigenständig, CD-konform. Grossflächige Marketing-Farbflächen schaden der Lesbarkeit datendichter Ansichten.

## Consequences

- Neue Feature-UIs verwenden ausschliesslich die semantischen Tokens, nicht direkt Farb-Hex-Werte oder die `--phsg-*`-Primitive.
- Die Sekundärpalette ist als Primitiv-Tokens angelegt, aber ungenutzt, bis Kategorie-Kacheln o. Ä. gebaut werden (dann Dark-Töne, weisse Schrift).
- Font- und Lib-Dateien liegen im Repo unter `static/`; bei Updates müssen sie neu bezogen werden (keine automatische CDN-Aktualisierung).
- Dark Mode müsste die semantischen Tokens pro Theme überschreiben — die Trennung Primitiv/semantisch ist darauf vorbereitet.
