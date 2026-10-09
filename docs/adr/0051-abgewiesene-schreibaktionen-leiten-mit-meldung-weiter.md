---
status: accepted
---

# Abgewiesene Schreibaktionen leiten mit Meldung weiter

Die Schreibaktionen der Forschenden-Ansicht einer Erhebung bewachen dieselbe
Regel: Nur ein eigener **Entwurf** ist veränderbar. Einen Verstoß beantworteten
sie auf zwei Arten (#254): Die Item-Routen und `vignette_verschieben` mit 403,
`vignette_hinzufuegen`, `vignette_entfernen`, `reihenfolge_umschalten`,
`konfiguration_speichern` und `loeschen` mit einer stillen Weiterleitung. Seit
#253 setzt das Modell das Einfrieren selbst durch; die Prüfung in der View ist
nur noch Benutzerführung.

**Entscheidung:** Jede Schreibaktion auf einer Erhebung, die kein Entwurf ist,
leitet auf die Seite weiter, von der die Forschende kam: auf die Detailseite,
bei `loeschen` auf die Liste. Sie zeigt dort über `django.contrib.messages`,
warum nichts geändert wurde. Ein `ValidationError` aus dem Modell, etwa wenn
zwei Tabs dieselbe Erhebung bearbeiten, nimmt denselben Weg. Das ist der Weg,
den die Lebenszyklus-Hüllen schon gehen.

Auch auf dem Erfolgspfad leiten alle Schreibaktionen auf die Detailseite weiter.
Die Item-Routen rendern sie nicht mehr selbst. `zuordnungsliste.js` folgt der
Weiterleitung über `fetch`. Damit liegt kein Rendern mehr in einer Transaktion
(#249).

Eine **fremde** Erhebung bleibt ein 404 über die Sichtbarkeitsauflösung. Wer die
Erhebung nicht sehen darf, erfährt nicht, dass es sie gibt.

## Considered Options

- **Durchgehend 403.** Verworfen: Eine Forschende, die auf eine veraltete
  Schaltfläche klickt, etwa in einem zweiten Tab nach dem Finalisieren, sieht
  dann eine Fehlerseite statt des aktuellen Stands und eines Grundes.
- **Bewusst gemischt, mit dokumentierter Regel.** Verworfen: Kein Fall braucht
  ein anderes Idiom. ADR-0034, das zwei Idiome nebeneinander begründete, ist
  durch ADR-0048 abgelöst.

## Consequences

- Die Sperrtests in `erhebungen/tests/test_forschenden_views.py` erwarten die
  Weiterleitung, die Meldung und die unveränderte Detailseite, nicht mehr 403.
- `docs/verhalten.md`, Abschnitt „Erhebungen verwalten“, nennt die Meldung.
