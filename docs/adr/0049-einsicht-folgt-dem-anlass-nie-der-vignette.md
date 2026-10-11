______________________________________________________________________

## status: accepted

# Einsicht folgt dem Anlass, nie der Vignette

Wer eine persistierte Sitzung nachträglich lesen darf, ergibt sich allein aus
dem **Anlass**, unter dem sie gespielt wurde: aus der Trainingsbindung, aus
einer für ein Training freigegebenen Abschrift oder aus der Erhebung. Die
Vignette, der Simulationskern oder die Modell-Konfiguration begründen nie
Einsicht. Einsicht ist immer rein lesend; das Glossar unterscheidet
**Selbsteinsicht** und **Fremdeinsicht** (#264).

Der Grund liegt im Training selbst: Es koppelt Vignettenauswahl,
Trainingsteilnehmende und Eigentümer-Kreis. Ein Kreis soll sehen, was seine
Trainingsteilnehmenden *in diesem Training* gespielt hat, nicht alles, was
dieselben Personen mit denselben Vignetten anderswo gespielt haben. Eine Kante
über die Vignette zöge Sitzungen fremder Trainings, pseudonyme
Erhebungssitzungen und private Abschriften mit herein.

## Die Matrix

|               | Selbsteinsicht                        | Fremdeinsicht                                                                     |
| ------------- | ------------------------------------- | --------------------------------------------------------------------------------- |
| **Training**  | alle eigenen Sitzungen, ohne Denkspur | Kreis und Administration, namentlich, nur abgeschlossene Sitzungen, ohne Denkspur |
| **Abschrift** | nur das eigene Konto                  | nur nach Freigabe für ein Training, dem die Teilnehmer:in beigetreten ist         |
| **Erhebung**  | nur über die Abschrift                | Kreis der Erhebung, pseudonym, mit Denkspur — erlaubt, noch nicht gebaut          |

- **Ausbilder:innen sehen, was die Teilnehmer:in sieht.** Die Denkspur bleibt
  der Forschenden und dem Probelauf vorbehalten.
- **Einsicht folgt der aktuellen Eigentümerschaft**, auch rückwirkend: Wer in
  den Kreis aufgenommen wird, sieht ältere Sitzungen; wer aus dem Kreis
  austritt, nichts mehr. Spiegelbildlich folgt sie der aktuellen
  Trainingsteilnahme (siehe
  [Austritt aus dem Training](#austritt-aus-dem-training)).
- **Die Autor:in hat aus ihrer Vignette keinen Anspruch.** Für die Qualität
  ihrer Vignette hat sie Probelauf und Evals.

## Das Training ist geschlossen

Namentliche Fremdeinsicht ist nur vertretbar, wenn die Trainingsteilnehmenden
gewollt beigetreten sind. Ein Training ist deshalb nur für Konten sichtbar und
spielbar, die ihm über einen Trainings-Link beigetreten sind; der Beitritt legt
die Trainingsbindung an. Teilnehmende sehen auf der Trainingsseite einen festen
Hinweis, dass der Kreis ihre Sitzungen einsieht. Ein Training darf leer sein und
dient dann allein als Anlass, unter dem Trainingsteilnehmende Abschriften
freigeben.

## Abschriften werden für ein Training freigegeben

Die Freigabe hängt am Training, nicht an einer eigenen Seminar-Ebene und nicht
an einzelnen Konten. Sie umfasst die ganze Abschrift, unabhängig von den
Vignetten des Trainings, und ist jederzeit widerrufbar.

## Austritt aus dem Training

Eine Trainingsteilnehmer:in kann aus einem Training austreten, und jede
Eigentümer:in des Trainings sowie die Administration kann sie aus ihm
**entfernen** (#357). Beide Wege führen in denselben Zustand; gespeichert wird
nur, *dass* sie ausgetreten ist, nicht wer es ausgelöst hat.

- **Kein Löschen.** Die Trainingsbindung bleibt mit ihrer Teilnahme bestehen und
  erhält einen Zustand. Löschen eigener Daten und des Kontos ist eine eigene
  Frage (#155, #156).
- **Selbsteinsicht bleibt.** Die Ausgetretene sieht das Training unter „Frühere
  Trainings“ rein lesend mit allen eigenen Sitzungen, auch laufenden. Sie
  startet keine neuen Sitzungen und erteilt keine neuen Freigaben.
- **Fremdeinsicht endet vollständig und rückwirkend.** Die Person verschwindet
  mit allen Sitzungen aus Tabelle, Beigetretenen-Zahl und Trainingsexport; der
  Kreis behält keine Spur von ihr. Bereits gezogene Exporte bleiben draußen.
- **Freigaben ruhen.** Ihre Abschrift-Freigaben für dieses Training wirken nicht
  mehr, bleiben aber bestehen. Sie sieht sie als ruhend und kann sie widerrufen.
- **Wiederbeitritt reaktiviert.** Über den Trainings-Link tritt sie wieder bei,
  nach Austritt wie nach Entfernen; dieselbe Bindung lebt wieder auf, mit allen
  alten Sitzungen, einer fortsetzbaren laufenden Sitzung und den ruhenden
  Freigaben. Ein gesperrter Beitritt hält auch Ausgetretene fern.

Entfernen ist damit **kein Ausschluss**, sondern Aufräumen der Liste. Wer
jemanden fernhalten will, sperrt den Beitritt; eine Sperre gegen Einzelne wäre
eine neue Anfrage.

## Trainingsexport

Der Kreis kann die Fremdeinsicht eines Trainings als Archiv menschenlesbarer
Markdown-Dateien ziehen, eine je abgeschlossener Sitzung. Er ist pseudonym,
nicht anonym: Kennzeichen werden je Export neu gezogen, Kontodaten fehlen,
Freitext wird nicht geschwärzt. Er ist keine Datenspur; deren Definition bleibt
Erhebungssache.

## Considered Options

- **Kante über die Vignette** — verworfen: zieht fremde Anlässe herein.
- **Eigene Seminar-Ebene über Trainings** — verworfen für jetzt: ein zweites
  Aggregat mit Kreis, Beitritt und Lebenszyklus für dieselbe Kopplung, die das
  Training schon trägt. Sie lässt sich später über Trainings legen, ohne die
  Freigabe-Kante umzubauen.
- **Freigabe direkt an einzelne Ausbilder:innen** — verworfen: Der Anlass ginge
  verloren; niemand wüsste mehr, warum Trainingsteilnehmende teilen.
- **Freigabe nur für Abschriften mit Vignetten des Trainings** — verworfen: Die
  Abschrift kennt ihre Erhebung bewusst nicht (ADR-0043), und fremde
  Erhebungsvignetten kann kein Kreis in sein Training aufnehmen (ADR-0015).

## Consequences

- **Eine freigegebene Abschrift ist für Dritte mit dem Erhebungsexport
  abgleichbar.** Ist eine Ausbilder:in zugleich Forschende der Erhebung, erkennt
  sie die Person am Transkripttext. Das System kann die Überschneidung nicht
  prüfen, weil die Abschrift keinen Rückzeiger hat. Das ist bewusst hingenommen;
  die Freigabe trägt keinen eigenen Warnhinweis.
- **Die Fremdeinsicht zeigt die Szene fremder Vignetten**, wenn eine Abschrift
  freigegeben ist — als dritte Ausnahme von ADR-0015.
- Die Trainingsbindung trägt einen Zustand: Fremdeinsicht, Trainingsexport,
  Zutritt und Freigabe-Auswahl fragen nach aktiven Bindungen, die Selbsteinsicht
  nach allen.
