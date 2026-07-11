---
status: accepted
---

# Die Modell-Konfiguration ist append-only; die Erhebung pinnt sie bei Aktivierung

Eine **Modell-Konfiguration** ist unveränderlich, sobald sie existiert. Eine Änderung legt einen neuen Datensatz an, der alte bleibt; genau eine ist aktiv. Sie ist **kein versioniertes Artefakt** im Sinne von ADR-0003: kein Entwurf, kein Finalisieren, keine benennbare Historie.

## Wo das „aktiv" lebt

„Unveränderlich" und „genau eine ist aktiv" können nicht beide wörtlich an derselben Zeile gelten: Ein `aktiv`-Boolean an der Konfiguration würde beim Umschalten die alte Zeile mutieren — genau die Mutation, die Append-only ausschließt —, und es gäbe kein Feld, über das man „genau eine im ganzen Bestand" als Datenbank-Index erklären könnte.

Das „aktiv" lebt deshalb **nicht an der Konfiguration, sondern in einer eigenen Zeigertabelle** mit garantiert genau einer Zeile, die per Fremdschlüssel auf die aktive Konfiguration zeigt. Die Ein-Zeilen-Garantie trägt ein konstantes, eindeutiges Feld. Umschalten bewegt diesen Zeiger; die Konfigurationszeilen behalten **kein einziges schreibbares Feld** und sind wirklich Append-only. „Genau eine ist aktiv" wird damit von einer Invariante, die man prüfen müsste, zu einer Tatsache über eine Tabelle. Das Umschalten läuft über eine einzige Schreibnaht (eine Manager-Methode); kein Aufrufer fasst die Zeigertabelle direkt an.

Eine **Historie des Umschaltens** — „welche Konfiguration war im Juni aktiv?" — wird bewusst **nicht** aufbewahrt (keine `aktiviert_am`/`deaktiviert_am`-Zeitstempel). Sie wird nicht gebraucht: Jede Erhebung pinnt ihre Konfiguration bei Aktivierung per Fremdschlüssel, und das Training ist keine Datenspur (ADR-0002). Die Frage „auf welchem Modell lief *diese* Erhebung?" beantwortet der Pin, nicht eine globale Chronik.

Der Entwurf/Final-Zyklus existiert, damit Autor:innen an einem Text arbeiten können, bis er reif ist. An einer Modellkonfiguration arbeitet niemand — sie wird gesetzt. Append-only liefert die Unveränderlichkeit, auf die die Datenspur angewiesen ist, ohne die Redaktionszeremonie für eine Betriebsentscheidung.

## Die Erhebung pinnt, das Training nicht

Die **Erhebung** pinnt die aktive Modell-Konfiguration bei ihrer Aktivierung. Das **Training** pinnt nichts und läuft auf der jeweils aktiven.

Der Kern kann diesen Pin nicht tragen: Die Modell-Konfiguration hängt ausdrücklich **nicht** an der Vignette, weil sie eine Betriebsgröße ist (ADR-0004). Ohne Pin an der Erhebung würde sie beim Sitzungsstart aufgelöst, und eine Administrator:in könnte mitten in einer laufenden Erhebung das Modell wechseln, weil der Anbieter das alte abkündigt oder es zu teuer wird. Die ersten dreißig Teilnahmen liefen dann auf einem Modell, die letzten zwanzig auf einem anderen. Die Datenspur wüsste es, aber die Erhebung wäre zerschnitten.

## Consequences

- Wird ein Modell abgekündigt, während eine Erhebung läuft, muss jemand eingreifen und die Erhebung umstellen oder abschließen. Ein sichtbarer, entscheidbarer Vorgang statt eines stillen Bruchs.
- Die Frage „welche Konfigurationen gab es je?" bleibt beantwortbar, und zwei Sitzungen sind über Fremdschlüssel vergleichbar statt über einen Textvergleich eingebetteter Werte.
- Der Begriff „Fassung" aus dem Glossar meint bei der Modell-Konfiguration einen append-only Datensatz, bei den drei versionierten Artefakten eine Fassung mit Lebenszyklus.
