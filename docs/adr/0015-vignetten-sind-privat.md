---
status: accepted
---

# Vignetten sind privat; es gibt kein Veröffentlichen

> **Nachgeführt durch ADR-0022 (Ko-Autorschaft):** Eine Vignette gehört inzwischen einem *Kreis* gleichrangiger Eigentümerinnen, nicht einer einzelnen Autor:in. Die Privatheit fällt dadurch nicht, sie verengt sich von „privat für die Autor:in" auf „privat für den Eigentümer-Kreis". Wo dieses ADR „ihre eigenen Vignetten" sagt, lies „die Vignetten ihres Eigentümer-Kreises".

Eine Autor:in sieht und bearbeitet **ausschließlich ihre eigenen Vignetten**. Es gibt keinen Mechanismus, eine Vignette anderen Autor:innen derselben Instanz zugänglich zu machen — und deshalb auch keinen Status *veröffentlicht* im Versions-Lebenszyklus (siehe ADR-0003). Sichtbarkeit ist kein Attribut, sondern eine Konstante.

Rollen sind damit **additiv**: Wer eine Erhebung oder ein Training zusammenstellen will, muss die enthaltenen Vignetten selbst in der Rolle der Autor:in geschrieben haben. Ausbilder:innen und Forschende greifen auf keine fremden Vignetten zu.

Geteilt bleibt allein der **Simulationskern**, der Administrator:innen gehört. Alles Fachliche ist privat.

> **Nachgeführt durch #65 (Vignetten-Editor):** `fach` und `thema` sind eine
> bewusste, eng begrenzte Ausnahme: Als geteiltes Curriculum-Vokabular dürfen
> ihre Bezeichner aus allen finalen Vignetten als unverbindliche Vorschläge im
> Editor erscheinen. Die Vignetteninhalte selbst bleiben privat; insbesondere
> ersetzt dieser Vorschlagspool nicht `sichtbar_fuer`.

## Consequences

- **Zwei Forschende an derselben Studie können sich keine Vignette teilen.** Eine Ausbilder:in kann kein Training aus den Vignetten ihrer Fachkollegin bauen. Das ist der Preis des einfachsten denkbaren Zugriffsmodells, und es ist die Sorte Einschränkung, die nach dem ersten realen Nutzungsversuch fallen könnte. Diese Entscheidung ist ausdrücklich **revidierbar** — sie ist eine Zugriffsregel, kein Datenmodell-Fakt.
- **Der Weggang einer Autor:in wird zum Betriebsproblem.** Ihre Vignetten sind für niemanden erreichbar, auch nicht für die Erhebungen, die auf ihnen laufen. Administrator:innen brauchen eine Übertragung der Eigentümerschaft. Das gehört ins Rollenmodell, ist aber eine Notwendigkeit, kein Komfort.
- Die in ADR-0001 als emergentes Nebenprodukt beschriebene „Bibliothek dokumentierter Fehlvorstellungen" entsteht damit vorerst nur innerhalb des Bestands einer einzelnen Autor:in.
- Die Invariante „höchstens ein Entwurf je Historie" (ADR-0003) folgt hieraus ohne Zusatzannahme: Es gibt keine zweite Person, die parallel an derselben Linie arbeiten könnte.
