---
status: accepted
---

# Die Vorlagen des Simulationskerns sind `string.Template`, nicht Django-Templates

Die vier Vorlagen einer Kern-Fassung — System-Prompt, User-Prompt, Rahmenhandlungs-Einleitung und Debrief — verwenden `string.Template` aus der Standardbibliothek mit `$name`-Platzhaltern. Das ist eine bewusste Abweichung vom Naheliegenden: In einem Django-Projekt würde man Django-Templates erwarten.

## Warum nicht Django-Templates

Die statische Vertragsprüfung aus ADR-0010 — „verwendet die Vorlage nur Platzhalter des Vertrags?" — ist mit `string.Template` ein Einzeiler ohne Abhängigkeit und ohne Parser:

```python
set(vorlage.get_identifiers()) <= VERTRAG
```

`Template.get_identifiers()` und `Template.is_valid()` sind in der Standardbibliothek und auf Python 3.14 (Projektversion) verifiziert vorhanden. Mit Django-Templates verlangte dieselbe Prüfung einen Lauf durch die kompilierte Nodelist und ein aktives Verbot von `{% %}`-Tags.

Vor allem aber schriebe Djangos **Autoescaping** ein Apostroph im Lernauftrag als `&#x27;` in den System-Prompt — für Menschen unsichtbar, für ein Sprachmodell nicht. Der Prompt ist kein HTML; die Vorlagensprache darf ihn nicht wie HTML behandeln.

## Das Fehlen von Logik ist die Aussage, nicht der Preis

`string.Template` kennt keine Bedingungen und keine Schleifen. Das ist gewollt: Eine Vorlage mit `{% if %}` könnte Leerstellen bedingt verwenden, womit die Menge der tatsächlich benutzten Platzhalter nicht mehr konstant wäre — und ADR-0010 nennt genau diese Konstanz „eine Aussage über die Domäne". Logikfreiheit hält den Vertrag statisch prüfbar.

## Considered Options

- **Django-Templates** — verworfen: Autoescaping beschädigt den Prompt, und die Vertragsprüfung wird zum Nodelist-Lauf mit Tag-Verbot.
- **Jinja2** — verworfen als unnötige Abhängigkeit; bringt dieselbe Logik-Mächtigkeit, die wir gerade nicht wollen.

## Consequences

- Grammatische Formen, die Fließtext braucht, kann die Vorlage nicht selbst bilden. Der Code berechnet sie und reicht sie als eigene Platzhalter in `VERTRAG_RAHMEN` (ADR-0010).
- Der Kern ist deutschsprachig (ADR-0004); die abgeleiteten Formen sind deutsche Grammatik im Code, keine Vorlagensache.
