---
status: accepted
---

# Versionierte Artefakte: Entwurf → final, gruppiert durch eine Historie, ohne „veröffentlicht"

Als Forschungsinstrument muss FailureOnTheFly reproduzierbar sein: Eine abgeschlossene Sitzung muss auf exakt die Fassung zeigen, die damals gespielt wurde. Vignette, Simulationskern und Fragebogen-Item folgen deshalb demselben Lebenszyklus: Ein **Entwurf** ist veränderlich, eine **finale** Fassung ist unveränderlich. Das Bearbeiten einer finalen Fassung erzeugt einen neuen Entwurf, der die Vorgängerin referenziert; die alte Fassung bleibt erhalten. Eine **Historie** gruppiert die sequenziell entstandenen Fassungen, entsteht automatisch und wird erst ab der zweiten Fassung sichtbar und benennbar.

Trainings und Erhebungen dürfen nur **finale** Fassungen einbinden. Jede Sitzung protokolliert zusätzlich die tatsächlich verwendete Vignettenfassung, Simulationskern-Fassung und Modell-Konfiguration — defensiv, damit die Datenspur auch dann vollständig bleibt, wenn ein Artefakt später doch mutiert oder gelöscht wird.

Die **Modell-Konfiguration ist kein versioniertes Artefakt**. Sie kennt keinen Entwurf, kein Finalisieren und keine Historie, sondern ist unveränderlich und append-only (siehe ADR-0013). Das **Gesprächsbudget** ist ebenfalls keines: Es ist ein Feld der Vignette, wird mit ihr eingefroren und von niemandem überschrieben (siehe ADR-0012).

Ein Status **„veröffentlicht" existiert nicht**, weil es nichts zu veröffentlichen gibt: Vignetten sind privat (siehe ADR-0015).

## Die Historie bleibt linear

Je Historie existiert **höchstens ein Entwurf**. Zwei gleichzeitig offene Entwürfe wären eine Verzweigung, und dann wäre „die neueste Fassung" nicht mehr eindeutig. Ein neuer Entwurf entsteht immer aus der **neuesten nicht-archivierten** Fassung.

**Entwürfe dürfen physisch gelöscht werden.** Sie waren nie final, nie eingebunden, und keine Datenspur zeigt auf sie. Wer den falschen Weg eingeschlagen hat, verwirft und beginnt neu.

## Archivierung statt Löschen

Eine finale Fassung kann **archiviert** werden — das logische Löschen. Physisches Löschen finaler Fassungen gibt es nicht, denn Datenspuren müssen sie noch Jahre später darstellen können. Auch eine ganze **Vignettenhistorie** ist archivierbar; sie archiviert dann alle ihre Fassungen und löscht den offenen Entwurf. Eine vollständig archivierte Historie ist eine tote Linie: Es gibt keine nicht-archivierte Fassung mehr, von der aus ein Entwurf entstehen könnte.

Was Archivierung bewirkt:

- **Neu einbinden:** unmöglich. Die Fassung verschwindet aus jeder Auswahl für Trainings und Erhebungen.
- **Training:** Die Fassung ist sofort nicht mehr spielbar; das Training verliert sie, als wäre sie entfernt worden. Bereits gespielte Sitzungen bleiben vollständig einsehbar.
- **Erhebung:** Eine laufende Erhebung **ignoriert die Archivierung**. Sie hat die Fassung gepinnt, Teilnehmende spielen sie zu Ende, die Datenspur bleibt geschlossen.
- **Datenspur:** Archivierte Fassungen bleiben aus jeder Sitzung heraus lesbar und darstellbar, für immer.

Die Asymmetrie zwischen Training und Erhebung folgt derselben Linie wie das Austauschen von Vignetten im laufenden Betrieb: Ein Training ist ein Übungsangebot, eine laufende Erhebung ist eine Messung. Der Preis: Eine Autor:in, die eine fehlerhafte Vignette archiviert, stoppt sie im Training sofort, nicht aber in der Erhebung, in der sie gerade Schaden anrichtet. Dort muss die Forschende:r die Erhebung selbst anhalten — eine Forschungsentscheidung, keine Autorenentscheidung.

**Archivierung ist umkehrbar**, solange sie keine Verzweigung erzeugt. Wurde die archivierte Fassung inzwischen dadurch überholt, dass aus einer ihrer Vorgängerinnen eine neue finale Fassung entstanden ist, bliebe sie nach dem Entarchivieren als Schwester mit derselben Vorgängerin zurück — das ist ausgeschlossen. Gelöschte Entwürfe kehren nie zurück.

## Consequences

- Autor:innen zahlen mit einem Entwurf/Final-Zyklus; dafür ist „welche Fassung lief in Erhebung X?" trivial beantwortbar.
- Das Wort **Vignette** bezeichnet die konkrete Fassung, nicht die Identität über Fassungen hinweg — Letztere heißt **Vignettenhistorie**. Diese Benennung folgt dem Sprachgebrauch: „Vignette" ist das, was man anlegt, spielt und einbindet.
- Trainings dürfen im laufenden Betrieb Vignetten austauschen. Alte Sitzungen zeigen weiterhin die damals gespielte Fassung an.
- Das Archivieren der Spitze macht die vorletzte Fassung wieder zur Basis für neue Entwürfe. Archivieren ist damit auch das Werkzeug, um eine misslungene Fassung zurückzunehmen.
- Ein irreversibles Archivieren wäre ein physisches Löschen mit besserer Presse. Deshalb die Umkehrbarkeit.
