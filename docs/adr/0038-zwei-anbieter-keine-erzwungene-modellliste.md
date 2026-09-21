---
status: accepted
---

# Zwei Anbieter, und der Modellname wird nicht gegen eine Liste geprüft

Die Anwendung unterstützt genau zwei echte Anbieter — **OpenRouter** und
**Infomaniak** — sowie `fake` für den Betrieb ohne Netz. Der Modellname bleibt
freier Text: Es gibt **keine** erzwungene Modellliste, weder als Auswahlfeld
noch als Prüfung gegen die Anbieter-API. Geprüft wird ausschließlich die
Anbieterbindung (ADR-0036); ein untaugliches Modell fällt im Probelauf auf
(ADR-0014).

Damit ist die offene Frage »Zulässige Anbieter und Modelle« beantwortet, die
ADR-0005 aufgeworfen hat: Wenn die Denkspur immer aus dem Structured Output
kommt, sind nur Anbieter und Modelle zulässig, die das beherrschen — und die
Frage war, wie diese Zulässigkeit sichergestellt wird.

## 1. Warum genau diese zwei

**OpenRouter** ist ein Router auf die großen Anbieter und bringt die Breite:
mehrere hundert Modelle mit Structured Output. **Infomaniak** bringt die
souveräne Alternative: Schweizer Rechenzentren, Open-Source-Modelle und eine
Datenschutzzusage, die inhaltlich genau dem entspricht, was ADR-0026 für die
Transkription verlangt.

Die beiden Nähte wählen ihren Anbieter je für sich (ADR-0036). Die
datenschutzrechtlich attraktivste Betriebsvariante ist damit konfigurierbar:
Sprachmodell über OpenRouter wegen der Modellauswahl, Audio über Infomaniak,
weil die Stimme das biometrische Datum ist (ADR-0007).

Beide Anbieter sind an echten Konten verifiziert (Stand 2026-09-21,
`docs/research/2026-09-18-zulaessige-anbieter-und-modelle.md`). Insbesondere
liefert Infomaniak Structured Output mit unserem `AUSGABE_SCHEMA` und
`strict: true` nachweislich — ADR-0005 trägt dort.

OpenAI-direkt wird **nicht** aufgenommen: Was es bietet, ist über OpenRouter
erreichbar, und ein dritter Zugangsweg brächte einen dritten Satz
Zugangsdaten ohne eigenen Nutzen.

## 2. Warum die Modellliste nicht erzwungen wird

Eine Namens-Whitelist wäre **Scheinsicherheit**. Bei OpenRouter hängt
Structured Output am **Endpunkt**, nicht am Modell: `supported_parameters` ist
auf Modellebene die Vereinigung über alle Endpunkte eines Modells. Verifiziertes
Gegenbeispiel: `deepseek/deepseek-v4.1-flash` steht in der
Structured-Output-Liste, drei seiner acht Endpunkte können es trotzdem nicht.
Eine bestandene Prüfung sagt also nur »mindestens ein Endpunkt kann es« — das
Routing kann dennoch auf einem anderen landen.

Deshalb ist **nicht** die Namensprüfung das Sicherungsmittel, sondern der
erzwungene Provider-Filter in den Aufrufparametern (`require_parameters`), und
bei Infomaniak schlicht der Umstand, dass dort `json_schema` die einzige
unterstützte Form ist.

Eine harte Prüfung hätte zwei weitere Kosten: Sie macht das Anlegen einer
Konfiguration von der Erreichbarkeit einer fremden API abhängig — und schlägt
genau dann fehl, wenn man sie am dringendsten braucht, bei einer Störung. Und
sie sperrt ein neu freigeschaltetes Modell aus, bis die Liste nachzieht. Bei
Infomaniak ist das keine Randbedingung: Sieben der acht Sprachmodelle sind dort
als `coming_soon` geführt und antworten trotzdem, eines davon nachweislich
samt Structured Output.

## 3. Was stattdessen prüft

Drei Tore, in dieser Reihenfolge:

1. **Die Anbieterbindung** (ADR-0036). Der Modellname muss das Präfix des
   gewählten Anbieters tragen, und die verlangten Zugangsdaten müssen da sein.
   Das fängt den vertauschten Anbieter, nicht den Tippfehler im Namen.
2. **Der Probelauf** (ADR-0014). Ein falsch geschriebenes oder untaugliches
   Modell meldet sich beim ersten echten Aufruf — vor jeder Erhebung.
3. **Die Aufrufparameter.** Der Provider-Filter bei OpenRouter ist nicht
   optional; ohne ihn kann das Routing auf einem Endpunkt ohne Structured
   Output landen.

Eine **Autovervollständigung** der Modellnamen aus den Anbieter-APIs ist davon
unberührt und ausdrücklich erlaubt (#202): Sie ist ein Vorschlag, nie eine
Prüfung, und ändert nichts daran, dass das Feld freier Text bleibt.

## 4. Der bewusst gezahlte Preis

Ein Tippfehler im Modellnamen überlebt das Speichern. Er zeigt sich erst im
Probelauf, und die Meldung des Anbieters benennt ihn nicht als Tippfehler,
sondern als Anbieterfehler. Das ist der Preis dafür, dass keine Störung einer
fremden API die Verwaltung der eigenen Instanz blockiert — und er wird durch
die Autovervollständigung gemildert, nicht durch eine Prüfung beseitigt.

Ein dritter Anbieter ist keine Erweiterung dieses ADR, sondern seine Revision:
Die Zahl zwei ist hier eine Entscheidung, keine Schranke der Technik.
