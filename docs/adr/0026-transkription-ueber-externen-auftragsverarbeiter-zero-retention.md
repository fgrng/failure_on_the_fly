---
status: accepted
---

# Transkription läuft über einen externen Auftragsverarbeiter mit Zero-Retention

ADR-0007 macht die Spracheingabe zum primären Eingabeweg und verlangt, dass das Audio **unmittelbar in ein Transkript überführt und verworfen** wird, weil die Stimme ein biometrisches, personenbezogenes Datum ist und die in ADR-0006 gebaute Pseudonymität nicht unterlaufen darf. ADR-0007 lässt offen, **wo** transkribiert wird. Diese Entscheidung schließt die Lücke: Die Transkription läuft über eine **externe API**.

Damit erhält ein Dritter das biometrische Datum — auch wenn wir es nicht speichern. Das ist nur zulässig unter einem **Auftragsverarbeitungsvertrag (AVV)** mit vertraglich zugesichertem **Zero-Retention**: Der Anbieter speichert das Audio nicht, nutzt es nicht zum Training und gibt es nicht weiter. Praktisch heißt das in der EU meist Azure OpenAI Whisper statt OpenAI-Direkt. Fehlt eine solche Zusicherung, ist die externe Transkription **nicht** zulässig; dann bleibt nur clientseitige oder selbst gehostete Transkription.

Die Teilnehmer:in **willigt im Teilnahmefluss ein**, dass ihr Audio zur Transkription an diesen Auftragsverarbeiter geht. Ohne Einwilligung steht ausschließlich die Tastatureingabe zur Verfügung. Der Transport ist verschlüsselt; serverseitig wird das Audio nicht über den Transkriptions-Request hinaus gehalten (ADR-0007).

Der **Probelauf** ist von der Einwilligungsstufe ausgenommen. Dort spricht die angemeldete Autor:in über ihr eigenes Material — nicht die pseudonyme Teilnehmer:in, deren Schutz aus ADR-0006 diese Stufe überhaupt trägt. Ein Probelauf ist schreibfrei und hat weder Teilnahme noch Sitzung, die einwilligen könnten; die Spracheingabe steht deshalb ohne vorgeschalteten Einwilligungsschritt bereit. Das Zero-Retention-Tor gilt unverändert auch hier: Ohne die vertragliche Zusicherung transkribiert auch der Probelauf nicht.

## Nachtrag: Bei OpenRouter trägt die Zusage die Betreiber:in

Die Anwendung lässt für die Transkription neben Infomaniak auch **OpenRouter**
zu. Für dessen Transkriptionsroute lässt sich die Zero-Retention-Zusage
technisch **nicht erzwingen**: Die Recherche zu #166 hält fest, dass die
Routing-Präferenzen `order`, `only` und `ignore` auf Transkriptionsanfragen
ausdrücklich nicht angewendet werden, und lässt offen, ob die Datenschutz-Filter
`zdr` und `data_collection` dort überhaupt greifen. Die Frage ist bei OpenRouter
zu erfragen und bleibt bis dahin offen.

Die Entscheidung fällt bewusst **zugunsten der Betreiberverantwortung**: Die
Zulässigkeit hängt weiterhin an einer zugesicherten Zero-Retention, aber wer sie
sicherstellt, ist die Betreiber:in bei der Wahl des Anbieters — nicht ein Schalter
im Aufruf. Damit wird das Tor dieser ADR von einer **technischen** zu einer
**organisatorischen** Kontrolle. Das ist dieselbe Bewegung, die unten unter
„Consequences" bereits für die Pseudonymität beschrieben ist, und es ist eine
**Absenkung des Schutzniveaus**.

`TRANSKRIPTION_ZERO_RETENTION` bleibt das eine Tor, hinter dem jede externe
Transkription steht. Es bedeutet nach diesem Nachtrag: Die Betreiber:in erklärt,
dass für den in der Transkriptions-Konfiguration gewählten Anbieter eine
Zero-Retention-Zusage vorliegt. Fehlt sie, bleibt der Schalter aus.

## Consequences

- Die Pseudonymität aus ADR-0006 hält **vertraglich**, nicht mehr **technisch**: Sie ruht auf dem AVV und der Zero-Retention-Zusage des Auftragsverarbeiters statt darauf, dass das biometrische Datum den kontrollierten Raum nie verlässt. Das ist eine bewusste Absenkung des Schutzniveaus zugunsten von Qualität und Umsetzbarkeit.
- Wechselt der Anbieter oder fällt die Zero-Retention-Zusage weg, ist diese Entscheidung neu zu prüfen. Clientseitige (WASM) oder selbst gehostete Transkription bleiben die Rückfalloptionen und würden den Schutz wieder technisch verankern.
- Der Teilnahmefluss braucht einen zusätzlichen Einwilligungsschritt für die Audioverarbeitung, getrennt von einer etwaigen Audio-Auswertungs-Erweiterung aus ADR-0007.
- Die Berechtigung zur Transkription hat zwei Quellen: die Audio-Einwilligung einer Teilnahme oder einen laufenden Probelauf einer angemeldeten Autor:in. Beide münden in dasselbe Zero-Retention-Tor.
- Die Wahl des Anbieters wird damit zur datenschutzrechtlich tragenden
  Entscheidung: Sie entscheidet, ob die Zusage vertraglich erzwingbar ist
  (Infomaniak: inhaltlich zugesagt, AVV offen) oder allein organisatorisch
  getragen wird (OpenRouter).
- Für Erhebungen ist die Wahl des Auftragsverarbeiters Teil der datenschutzrechtlichen Dokumentation, nicht der Datenspur.
