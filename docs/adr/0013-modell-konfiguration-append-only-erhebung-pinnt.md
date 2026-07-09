---
status: accepted
---

# Die Modell-Konfiguration ist append-only; die Erhebung pinnt sie bei Aktivierung

Eine **Modell-Konfiguration** ist unveränderlich, sobald sie existiert. Eine Änderung legt einen neuen Datensatz an, der alte bleibt; genau eine ist aktiv. Sie ist **kein versioniertes Artefakt** im Sinne von ADR-0003: kein Entwurf, kein Finalisieren, keine benennbare Historie.

Der Entwurf/Final-Zyklus existiert, damit Autor:innen an einem Text arbeiten können, bis er reif ist. An einer Modellkonfiguration arbeitet niemand — sie wird gesetzt. Append-only liefert die Unveränderlichkeit, auf die die Datenspur angewiesen ist, ohne die Redaktionszeremonie für eine Betriebsentscheidung.

## Die Erhebung pinnt, das Training nicht

Die **Erhebung** pinnt die aktive Modell-Konfiguration bei ihrer Aktivierung. Das **Training** pinnt nichts und läuft auf der jeweils aktiven.

Der Kern kann diesen Pin nicht tragen: Die Modell-Konfiguration hängt ausdrücklich **nicht** an der Vignette, weil sie eine Betriebsgröße ist (ADR-0004). Ohne Pin an der Erhebung würde sie beim Sitzungsstart aufgelöst, und eine Administrator:in könnte mitten in einer laufenden Erhebung das Modell wechseln, weil der Anbieter das alte abkündigt oder es zu teuer wird. Die ersten dreißig Teilnahmen liefen dann auf einem Modell, die letzten zwanzig auf einem anderen. Die Datenspur wüsste es, aber die Erhebung wäre zerschnitten.

## Consequences

- Wird ein Modell abgekündigt, während eine Erhebung läuft, muss jemand eingreifen und die Erhebung umstellen oder abschließen. Ein sichtbarer, entscheidbarer Vorgang statt eines stillen Bruchs.
- Die Frage „welche Konfigurationen gab es je?" bleibt beantwortbar, und zwei Sitzungen sind über Fremdschlüssel vergleichbar statt über einen Textvergleich eingebetteter Werte.
- Der Begriff „Fassung" aus dem Glossar meint bei der Modell-Konfiguration einen append-only Datensatz, bei den drei versionierten Artefakten eine Fassung mit Lebenszyklus.
