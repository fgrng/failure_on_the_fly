---
status: accepted
---

# Ko-Autorschaft: Eigentümerschaft ist ein M2M gleichrangiger Eigentümerinnen

Eine Vignettenhistorie gehört **einer oder mehreren** Autor:innen, alle gleichrangig. Das führt ADR-0019 (Eigentümer als einzelner Fremdschlüssel) und ADR-0015 (eine Autor:in sieht ausschließlich ihre eigenen Vignetten) an einem Punkt fort: Aus dem Fremdschlüssel wird ein Many-to-Many `eigentuemerinnen` an der Vignettenhistorie, und die Privatheit verengt sich, statt zu fallen.

## Was sich ändert

- **Eigentümerschaft ist ein M2M** an der Vignettenhistorie (nicht an der Fassung — eine finale Fassung ist unveränderlich, ADR-0019). Kein Through-Model, keine Urheberin-Rolle: Alle Ko-Eigentümerinnen dürfen dasselbe — sehen, bearbeiten, finalisieren, weitere hinzufügen oder entfernen, die Vignette in eine eigene Erhebung oder ein eigenes Training ziehen.
- **Die Privatheit fällt nicht, sie verengt sich.** Aus „privat für die Autor:in" wird „privat für den Eigentümer-Kreis". Eine Vignette ist weiterhin nicht öffentlich; sie ist sichtbar für ihre Ko-Eigentümerinnen und sonst niemanden außer der Administrator:in. `sichtbar_fuer` (ADR-0019) wandert von Fremdschlüssel-Gleichheit zu Mengenzugehörigkeit.
- **ADR-0015s „muss die Vignetten selbst geschrieben haben"** wird zu „muss Ko-Eigentümerin sein". Weil alle gleichrangig sind, darf jede Ko-Eigentümerin die Vignette in ihre Erhebung aufnehmen.

## Warum kein django-guardian

ADR-0019 verwarf `django-guardian` mit dem Hinweis, das sei der Zeitpunkt, es erneut zu prüfen, sollte die Privatheit fallen. Sie fällt jetzt teilweise — und `guardian` bleibt trotzdem verworfen: Es kauft eine per-Objekt-, per-Nutzer-, per-Permission-Matrix für einen Fall, der **uniform** ist. Eigentümerschaft ist alles-oder-nichts je Vignette, kein Rechte-Gitter. Ein schlichtes M2M trägt das vollständig; eine Rechte-Tabelle wäre Struktur ohne Ertrag. Sollte je eine *ungleiche* Beteiligung gebraucht werden (Leserecht ohne Schreibrecht), ist das M2M über ein `through=`-Model nachrüstbar — und dann erst wäre `guardian` wieder eine Frage.

## Der Weggang einer Autor:in

Konten tragen personenbezogene Daten und müssen physisch löschbar sein (DSGVO). Beim Löschen wird die Autor:in aus dem M2M entfernt. Solange andere Ko-Eigentümerinnen bleiben, überlebt die Vignette ohne Zutun.

Die Invariante lautet: **Eine nicht-archivierte Vignettenhistorie hat mindestens eine Eigentümerin.** Wer alleinige Eigentümerin einer aktiven Historie ist, kann nicht gelöscht werden, bevor sie überträgt oder eine Ko-Autorin hinzufügt. **Archivierte** Historien dürfen dagegen eigentümerlos werden: Sie sind aus der Arbeitsansicht genommen, über Erhebungs-Pins und die Administrator:in weiter lesbar, und ihr Forschungswert hängt am gepinnten Fassungs-Fremdschlüssel, nicht an der Eigentümerschaft. So muss niemand ein neues Zuhause für etwas suchen, das er längst archiviert — als „gelöscht" empfunden — hat.

Diese Invariante ist eine Zählung über die Zeilen einer Through-Tabelle und lässt sich nicht billig als Datenbank-Constraint ausdrücken. Sie lebt deshalb im **Konto-Löschpfad** (App `konten`, App-Ebene), nicht im Schema. Kontolöschung ist selten; Effizienz ist hier kein Argument.

## Considered Options

- **Einzelner Eigentümer-Fremdschlüssel plus reine Übertragung** — verworfen. Er löst das Weggang-Problem, aber die Domäne will echte Ko-Autorschaft: zwei Menschen, die dieselbe Vignette gemeinsam verantworten, nicht eine, die der anderen Leserechte gibt.
- **Through-Model mit ausgezeichneter Urheberin** — verworfen, solange kein Fall verlangt, dass eine Eingeladene weniger darf als die Urheberin. Später additiv nachrüstbar.
- **django-guardian** — verworfen (oben).

## Consequences

- **ADR-0015 ist nachgeführt:** Der Satz „ausschließlich ihre eigenen Vignetten" gilt nur noch für den Eigentümer-Kreis. Die Privatheit bleibt revidierbar, ist aber nicht mehr die ganze Antwort — aus Eigentümerschaft ist eine Zugriffsregel mit mehreren Beteiligten geworden.
- **ADR-0019 ist nachgeführt:** „Der Eigentümer ist ein Fremdschlüssel" wird zu „die Eigentümerinnen sind ein M2M". Die Stelle bleibt die Vignettenhistorie, die Regel bleibt an `sichtbar_fuer`.
- ADR-0003s Konsequenz, dass „höchstens ein Entwurf je Historie" ohne Zusatzannahme aus der Privatheit folgt, gilt nicht mehr automatisch: Zwei Ko-Eigentümerinnen könnten gleichzeitig bearbeiten wollen. Der partielle Unique-Index (ADR-0021) trägt die Invariante weiterhin — sie ist jetzt aber eine echte Schranke, nicht bloß eine unmögliche Situation.
