---
status: accepted
---

# Rollen sind Groups, Eigentümerschaft ist ein Fremdschlüssel, die Sichtbarkeitsregel lebt am QuerySet

Die fünf Rollen aus `CONTEXT.md` — Teilnehmer:in, Autor:in, Ausbilder:in, Forschende:r, Administrator:in — werden als **Django-Groups** geführt, nicht als Feld am Nutzer. Rollen sind **additiv**: Dieselbe Person schreibt Vignetten und leitet eine Erhebung. ADR-0015 macht das sogar zur Pflicht — wer eine Erhebung zusammenstellen will, muss ihre Vignetten selbst als Autor:in geschrieben haben. Ein einzelnes `rolle`-Feld zwänge diese Person zu zwei Konten und damit zu zwei getrennten Vignettenbeständen, was den Zweck vereitelt.

`konten` definiert von Anfang an ein **eigenes Nutzer-Modell**. Das ist keine Vorratshaltung, sondern eine Frist: Ein Wechsel des User-Modells nach der ersten Migration ist in Django schmerzhaft, und die Entscheidung fällt vor dem ersten `migrate` oder gar nicht.

## Eigentümerschaft ist eine Abfrage, kein Recht

Zwei Rollen tragen Sichtbarkeitsregeln, die an einzelnen Objekten hängen statt am Nutzer: Die Autor:in sieht ausschließlich ihre eigenen Vignetten (ADR-0015), die Ausbilder:in sieht die Sitzungen der Teilnehmenden ihrer eigenen Trainings. Das sind Eigentümerschafts-**Abfragen**, keine Berechtigungen. Sie werden nicht geprüft, sondern gefiltert: Was einem nicht gehört, existiert nicht.

Der Eigentümer ist ein Fremdschlüssel auf dem Objekt. Bei der Vignette trägt ihn die **Vignettenhistorie**, nicht die einzelne Fassung — eine finale Fassung ist unveränderlich, ein Eigentümerwechsel an ihr wäre eine Mutation.

> **Nachgeführt durch ADR-0022 (Ko-Autorschaft):** Aus dem einzelnen Fremdschlüssel ist ein Many-to-Many gleichrangiger Eigentümerinnen an der Vignettenhistorie geworden. `sichtbar_fuer` prüft dann Mengenzugehörigkeit statt Fremdschlüssel-Gleichheit; die Stelle und die Regel bleiben. Die guardian-Verwerfung unten gilt weiter — Eigentümerschaft ist uniform, kein Rechte-Gitter.

Die Regel selbst lebt als benannte Methode am QuerySet:

```python
Vignette.objects.sichtbar_fuer(request.user)
```

Ein kleines Interface über einer Regel, die sonst in jeder View erneut geschrieben würde. Sie ist ohne HTTP testbar, sie ist an einer Stelle korrigierbar, und eine View kann sie nicht versehentlich umgehen, weil das ungefilterte QuerySet in keiner View vorkommt.

## Considered Options

- **Ein `rolle`-Enum am Nutzer, geprüft in View-Decorators** — verworfen. Es erlaubt genau eine Rolle je Person und wiederholt die Sichtbarkeitsregel in jeder View.
- **Objektbezogene Rechte (`django-guardian`)** — verworfen. Eine Dependency und eine Rechte-Tabelle für einen Fall, den ADR-0015 gerade ausgeschlossen hat: Vignetten sind privat, es gibt nichts zu teilen. Sollte die Privatheit fallen — ADR-0015 nennt sie ausdrücklich revidierbar —, ist das der Zeitpunkt, diese Option erneut zu prüfen.

## Consequences

- Die Administrator:in ist in `sichtbar_fuer` ein Sonderfall: Sie sieht alles. Der Sonderfall steht damit an genau einer Stelle.
- Die Teilnehmer:in ist die einzige Rolle, die **ohne Konto** auftreten kann — in einer Erhebung ist sie ein Teilnahme-Token (ADR-0006, ADR-0018). Sie ist deshalb keine Group, sondern die Abwesenheit jeder anderen Rolle.
- Groups tragen keine Django-Permissions. Wer eine Rolle prüft, prüft Gruppenmitgliedschaft, nicht `user.has_perm`. Beide Mechanismen nebeneinander zu benutzen, wäre der Anfang von zwei Wahrheiten.
- Was mit Vignetten, Trainings und Erhebungen einer weggegangenen Autor:in geschieht, bleibt offen (siehe `docs/open-questions.md`, Frage 1). Dieser ADR legt nur fest, **wo** der Eigentümer sitzt, nicht wie er wechselt.
- Fällt die Privatheit aus ADR-0015, bleibt der Fremdschlüssel an der Historie richtig, ist aber nicht mehr die ganze Antwort: Aus Eigentümerschaft würde eine Zugriffsregel mit mehreren Beteiligten, und `sichtbar_fuer` wäre die Stelle, an der sie einzöge.
