---
status: accepted
---

# Transkription läuft über einen externen Auftragsverarbeiter mit Zero-Retention

ADR-0007 macht die Spracheingabe zum primären Eingabeweg und verlangt, dass das Audio **unmittelbar in ein Transkript überführt und verworfen** wird, weil die Stimme ein biometrisches, personenbezogenes Datum ist und die in ADR-0006 gebaute Pseudonymität nicht unterlaufen darf. ADR-0007 lässt offen, **wo** transkribiert wird. Diese Entscheidung schließt die Lücke: Die Transkription läuft über eine **externe API**.

Damit erhält ein Dritter das biometrische Datum — auch wenn wir es nicht speichern. Das ist nur zulässig unter einem **Auftragsverarbeitungsvertrag (AVV)** mit vertraglich zugesichertem **Zero-Retention**: Der Anbieter speichert das Audio nicht, nutzt es nicht zum Training und gibt es nicht weiter. Praktisch heißt das in der EU meist Azure OpenAI Whisper statt OpenAI-Direkt. Fehlt eine solche Zusicherung, ist die externe Transkription **nicht** zulässig; dann bleibt nur clientseitige oder selbst gehostete Transkription.

Die Teilnehmer:in **willigt im Teilnahmefluss ein**, dass ihr Audio zur Transkription an diesen Auftragsverarbeiter geht. Ohne Einwilligung steht ausschließlich die Tastatureingabe zur Verfügung. Der Transport ist verschlüsselt; serverseitig wird das Audio nicht über den Transkriptions-Request hinaus gehalten (ADR-0007).

## Consequences

- Die Pseudonymität aus ADR-0006 hält **vertraglich**, nicht mehr **technisch**: Sie ruht auf dem AVV und der Zero-Retention-Zusage des Auftragsverarbeiters statt darauf, dass das biometrische Datum den kontrollierten Raum nie verlässt. Das ist eine bewusste Absenkung des Schutzniveaus zugunsten von Qualität und Umsetzbarkeit.
- Wechselt der Anbieter oder fällt die Zero-Retention-Zusage weg, ist diese Entscheidung neu zu prüfen. Clientseitige (WASM) oder selbst gehostete Transkription bleiben die Rückfalloptionen und würden den Schutz wieder technisch verankern.
- Der Teilnahmefluss braucht einen zusätzlichen Einwilligungsschritt für die Audioverarbeitung, getrennt von einer etwaigen Audio-Auswertungs-Erweiterung aus ADR-0007.
- Für Erhebungen ist die Wahl des Auftragsverarbeiters Teil der datenschutzrechtlichen Dokumentation, nicht der Datenspur.
