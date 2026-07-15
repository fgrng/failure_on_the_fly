---
status: accepted
---

# Die Erhebung leiht die Statusnamen der Artefakte, ist aber ein einzelnes Objekt mit reversiblem final

Eine **Erhebung** ist ein Untersuchungsdesign, kein versioniertes Artefakt:
Sie hat weder Historie noch Fassungen. Sie verwendet dennoch die bekannten
Statusnamen **Entwurf**, **final** und **archiviert**, weil ihr Design vor einer
Datenerhebung eingefroren werden muss.

Der Übergang `final → entwurf` mutiert dieselbe Zeile und bleibt nur möglich,
solange keine nicht archivierte Stichprobe und keine Daten die finale Erhebung
festhalten. Ein erneutes Finalisieren pinnt die dann aktive Modell-Konfiguration
neu. `archiviert` ist ebenfalls kein physisches Löschen und kann zurück zu
`final` führen, solange keine laufende Stichprobe dem widerspricht.

## Erwogene Optionen

- **Erhebung als versioniertes Artefakt** — verworfen. Eine neue Fassung würde
  Teilnahme-Links und ihre Daten von dem Design trennen, das sie tatsächlich
  verwendet haben.
- **Eigene Statusnamen** — verworfen. Die drei Namen beschreiben die nötige
  Steuerung verständlich, ohne eine Fassungshistorie zu behaupten.

## Folgen

- Die folgenden Lebenszyklus-Methoden bewachen die reversiblen Übergänge; es
  gibt keine Historie und keinen Fassungsklon.
- Das eingebundene Design einer finalen Erhebung darf nicht still geändert
  werden.
- Stichproben und Datenspur entscheiden, wann ein Rückweg nicht mehr zulässig
  ist.
