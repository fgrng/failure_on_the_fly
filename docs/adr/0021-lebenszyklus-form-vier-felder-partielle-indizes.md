---
status: accepted
---

# Die Lebenszyklus-Form: vier Felder, partielle Unique-Indizes statt Prüfungen, eifrige Historie

ADR-0017 verbietet die gemeinsame Basisklasse, nicht die gemeinsame **Form**. Jedes versionierte Artefakt (ADR-0003) implementiert denselben Lebenszyklus eigenständig — aber es implementiert *dieselbe* Form. Dieses ADR fixiert sie, damit die drei Apps nicht drei verschiedene Formen erfinden.

## Die vier Felder jeder Fassung

| Feld | Zweck |
|---|---|
| `zustand` | `TextChoices`: `entwurf`, `final`, `archiviert` |
| `finalisiert_am` | nullbar, einmal gesetzt, **nie zurückgesetzt** |
| `historie` | Fremdschlüssel, **NOT NULL** |
| `vorgaengerin` | selbstreferenzierend, nullbar |

Der Automat hat drei Kanten: `entwurf → final`, `final → archiviert`, `archiviert → final`. Ein Entwurf wird nie archiviert, sondern physisch gelöscht (ADR-0003). Deshalb impliziert `archiviert` immer „war einmal final", und `finalisiert_am` überlebt das Entarchivieren.

## Die Invarianten sind partielle Unique-Indizes, keine Prüfungen

Die beiden Invarianten aus ADR-0003 leben in der Datenbank, in derselben Bewegung, mit der ADR-0018 die Pseudonymität ins Schema legt:

```python
UniqueConstraint(fields=['historie'],     condition=Q(zustand='entwurf'))
UniqueConstraint(fields=['vorgaengerin'], condition=~Q(zustand='archiviert'))
```

Der erste erzwingt „höchstens ein Entwurf je Historie". Der zweite ist die Umformulierung von ADR-0003s „bliebe sie als Schwester mit derselben Vorgängerin zurück": Zwei nicht-archivierte Fassungen mit derselben Vorgängerin sind verboten, womit das Entarchivieren gar nicht erst falsch ausgehen kann. Dazu ein `CheckConstraint`: `zustand='entwurf'` genau dann, wenn `finalisiert_am IS NULL`. Beide Indizes und der Check laufen unter SQLite (ADR-0016).

## Die Historie entsteht eifrig

Die Historie-Zeile entsteht in derselben Transaktion wie die **erste** Fassung, nicht erst bei der zweiten. Das ist erzwungen, nicht Geschmack: Bei fauler Entstehung hätte die erste Fassung zunächst `historie = NULL`, und beim Erscheinen der zweiten Fassung müsste der `historie`-Fremdschlüssel an der bereits **finalen** ersten Fassung nachgetragen werden — ein Schreibzugriff auf eine unveränderliche Zeile, den ADR-0003 verbietet. Zudem beißt der Entwurf-Index nur über eine Nicht-NULL-Spalte (NULLs sind in SQL distinkt), weshalb `historie` NOT NULL ist.

„Sichtbar und benennbar erst ab der zweiten Fassung" (ADR-0003) ist damit eine **Präsentationsregel**, keine Entstehungsregel: Die Historie existiert ab Fassung 1, aber die Oberfläche zeigt und benennt sie erst ab Fassung 2.

## Warum eine Form-ADR neben ADR-0017

ADR-0017 sagt „jede App implementiert selbst" und begründet, warum es keine geteilte Klasse gibt. Es sagt nicht, *welche* Form implementiert wird. Ohne dieses ADR wählte jede App ihre eigene Mechanik — die eine ein `CheckConstraint`, die andere eine `full_clean()`-Prüfung, die dritte einen Signal-Handler —, und ADR-0017s eigene Warnung vor auseinanderlaufenden Invarianten würde wahr, bevor die erste Zeile Code steht. Dieses ADR ist eine Spezifikation, die drei Apps unabhängig erfüllen, keine gemeinsame Implementierung.

## Considered Options

- **Die Invarianten als Modell-Prüfungen (`clean()`)** — verworfen. Sie hingen am Aufruf von `full_clean()` und ließen sich per direktem `save()` oder Bulk-Write umgehen; ein Datenbank-Index kann das nicht.
- **Faule Historie-Entstehung** — verworfen, weil sie eine finale Fassung mutieren müsste (oben).

## Consequences

- Die Form ist an drei Stellen implementiert und kann auseinanderlaufen (ADR-0017). Dieses ADR macht die Form explizit, damit eine Abweichung als Abweichung erkennbar ist und nicht als eine von drei gleichberechtigten Auslegungen.
- Der Simulationskern braucht eine Historie, obwohl er konzeptionell eine einzige Linie ist (ADR-0004) — sonst hätte der Entwurf-Index keine Spalte. Seine Historie ist ein namenloser Singleton ohne Sprachfeld.
- Vollständigkeit (welche Felder ein Entwurf zum Finalisieren gefüllt haben muss) gehört **nicht** in diese Form. Sie ist je Artefakt verschieden und lebt in dessen `finalisieren()`. Diese ADR regelt nur den Zustandsautomaten und seine zwei Invarianten.
