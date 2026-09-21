---
status: accepted
---

# Der Eigentümer-Kreis ist eine gemeinsame Basis in `konten`

Der Eigentümer-Kreis aus ADR-0022 und ADR-0032 wird **ein** Gegenstand: ein
abstraktes Modell `EigentuemerKreis` samt einem QuerySet-Mixin im Modul
`konten/eigentuemerschaft.py`. Von ihm erben die vier eigentümer-tragenden
Bestände — Vignettenhistorie, Fragebogen-Item-Historie, Training und Erhebung.

Die Basis trägt das M2M-Feld auf `konten.Konto`, den Austritt, die
Kandidatenliste, die Aufnahmeregel `ROLLENGRUPPE` und `ist_aktiv()`; das Mixin
trägt die Sichtbarkeitsregel `sichtbar_fuer()` und das Anlegen mit erster
Eigentümerin. Mehr nicht.

Fachlich ändert sich nichts: Alle Eigentümerinnen bleiben gleichrangig,
Eigentümerschaft bleibt alles-oder-nichts je Objekt, eine Übertragungs-Operation
entsteht nicht (ADR-0032).

## Die Abgrenzung gegen ADR-0017

ADR-0017 verwirft eine gemeinsame Basis über die versionierten Artefakte und
sagt voraus: „Ein späterer Architektur-Review wird die gemeinsame Basis erneut
vorschlagen … Dieser ADR ist die Antwort darauf." Genau so ein Review hat dieses
Vorhaben ausgelöst. Es ist trotzdem nicht der Vorschlag, den ADR-0017 abgelehnt
hat — und der Unterschied liegt in der Achse.

**Die Basis trägt den Eigentümer-Kreis und nichts sonst. Sie spannt quer zur
Lebenszyklus-Achse — zwei Historien und zwei Objekte, die gar keinen
Lebenszyklus haben —, weshalb aus ihr niemals eine Lebenszyklus-Basis erwachsen
kann.**

ADR-0017 hätte drei Artefakte zusammengespannt, deren Zustandsautomaten sich
absehbar auseinanderentwickeln; jede Abweichung wäre später als Flaggenfeld
durch die Basis gepresst worden. Hier ist es umgekehrt: Die vier
Felddeklarationen sind heute **zeichengleich**, und ihre Erbinnen haben
miteinander nichts gemein außer dem Kreis. Der Simulationskern — das dritte
Artefakt aus ADR-0017 — erbt nicht: Er gehört der Administration und trägt
keinen Eigentümer-Kreis. Wer diese Basis um einen Zustand, ein `finalisiert_am`
oder eine Vorgängerin erweitern wollte, müsste sie zwei Erbinnen aufzwingen, die
keine Fassungen sind. ADR-0017 bleibt unangetastet und gilt für seine Achse
fort.

Für den Rückweg gilt, was ADR-0017 selbst ausrechnet: Abstrakt geerbte Felder
landen in denselben Spalten derselben Tabellen. Die Extraktion hat keine
Migration erzeugt (`makemigrations --check`: keine Änderungen), und das
Zurücknehmen kostete ebenso wenig.

Das Wort **Naht** wird hier bewusst vermieden. Nach ADR-0016 ist eine Naht ein
Austauschpunkt mit mindestens zwei Adaptern; davon gibt es weiterhin genau zwei,
das Sprachmodell und den Sink. Hier wird nichts ausgetauscht.

## Der Ort ist `konten`

Die Basis wohnt in `konten`, weil der Eigentümer-Kreis ein Kreis von Konten ist
und alle vier Bestands-Apps ohnehin auf `konten` zeigen. Die Kantenrichtung aus
ADR-0016 lautet Apps → `konten`; die Basis fügt keine neue Kante hinzu, sie
benutzt die vorhandene.

Damit führt dieser ADR **ADR-0016 in einem Punkt nach**: Die Gegenkante
entfällt. `konten` importiert keine Modelle der vier Bestands-Apps mehr (siehe
den Löschpfad unten), womit der Graph wieder azyklisch ist, wie ADR-0016 ihn
beschreibt.

## Zwei Invarianten für zwei Anlässe

Die Regel „nie eigentümerlos" existiert in zwei bewusst verschiedenen Fassungen.
Sie werden **nicht** zusammengeführt, bekommen verschiedene Namen und
verschiedene Aufrufer; es entsteht kein Parameter, der zwischen ihnen umschaltet.

- **Austritt am Objekt** — die Aktion auf der Detailseite — ist
  **bedingungslos**: Der letzte Platz im Kreis kann nicht geräumt werden, auch
  nicht bei einem archivierten Bestand. Ein archivierter Bestand ist
  entarchivierbar und wäre danach aktiv und eigentümerlos.
- **Kontolöschung** ist **archivierungsabhängig**: Ein archivierter Bestand
  blockiert die Löschung eines Kontos nicht. ADR-0032 erlaubt eigentümerlose
  archivierte Erhebungen ausdrücklich — und muss es, denn sonst gäbe es für die
  letzte Eigentümerin überhaupt keinen Weg: Austragen kann sie sich nicht.

`ist_aktiv()` ist die Stelle, an der ein Bestand sagt, welcher Seite er
angehört. Sie steht auf `True`; die Vignettenhistorie überschreibt sie über
`archiviert`, die Erhebung über `Status.ARCHIVIERT`. Training und
Fragebogen-Item-Historie kennen keine Stilllegung und erben das Ja — für
Training hält ADR-0032 das ausdrücklich fest.

## Der Löschpfad läuft über die Modellregistrierung

`Konto.delete` fragt nicht mehr drei importierte Modelle ab, sondern iteriert
über Djangos **Modellregistrierung** (`apps.get_models()`) und nimmt jedes
registrierte Modell, das von `EigentuemerKreis` erbt. Ein Bestand blockiert die
Löschung, wenn `ist_aktiv()` wahr ist und das zu löschende Konto seine einzige
Eigentümerin ist; die `ProtectedError`-Meldung steht als
`LOESCHSPERRE_MELDUNG` am blockierenden Modell und behält den Hinweis, vorher
eine Nachfolgerin einzutragen. Sie wird nicht aus dem `verbose_name`
abgeleitet — der ergäbe »fragebogen item historie«; jede Erbin schreibt ihren
Bestand deshalb selbst aus, die Basis hält nur einen neutralen Fallback.

Das ist **bewusste Django-Introspektion, kein Trick**. Es wird hier und im Code
benannt, weil eine Registry-Iteration sonst als Zauberei gelesen wird. Sie kauft
dreierlei: Die Gegenkante nach ADR-0016 verschwindet, die bisher vergessene
Fragebogen-Item-Historie ist ohne eigenen Handgriff abgedeckt, und ein künftiges
fünftes eigentümer-tragendes Modell ist am Tag seiner Einführung mitgeschützt —
statt am Tag, an dem jemand den Fehler bemerkt.

Derselbe Weg trägt den Vertragstest über alle Erbinnen: Er iteriert über
dieselbe Registrierung. Eine neue Abweichung wird rot, statt still zu entstehen.

### Bekannte Grenze: der Schutz hängt an `Konto.delete`

Der Löschschutz sitzt auf der Instanzmethode. Er wird deshalb **umgangen, wenn
ein Konto per QuerySet gelöscht wird** — `Konto.objects.filter(...).delete()`
ruft `Model.delete()` nicht auf. Im Produktivcode existiert dafür heute keine
Aufrufstelle, und die Kontolöschung ist ohnehin Shell-Arbeit (#156). Die Grenze
wird benannt, nicht geschlossen. Falls sie je beißt, ist ein `pre_delete`-
Empfänger auf dem Konto der Weg.

## Nebenläufigkeit: `atomic()`, kein `select_for_update()`

Das Projekt läuft auf SQLite (ADR-0016). Djangos SQLite-Backend meldet
`has_select_for_update = False`, und der SQL-Compiler erzeugt die Klausel nur,
wenn das Backend sie unterstützt: **`select_for_update()` erzeugt hier kein SQL
und keinen Fehler — es tut schlicht nichts.** Serialisiert wird über die
Verbindungsoption `transaction_mode: IMMEDIATE` in `config/settings.py`: Jedes
`atomic()` öffnet mit `BEGIN IMMEDIATE` und nimmt die Schreibsperre sofort.

Der gemeinsame Austritt kapselt sich deshalb in `transaction.atomic()`, und die
`select_for_update()`-Aufrufe rund um den Eigentümer-Kreis entfallen ersatzlos.
Eine Sperre, die auf dem eingesetzten Backend wirkungslos ist, darf nicht im
Code stehen: Die nächste Leserin hielte sie für die tragende Sicherung. Ein
Kommentar am Austritt hält fest, worauf die Serialisierung tatsächlich beruht.

**Diese Entscheidung wird mit einem Backend-Wechsel zurückgenommen.** Kommt ein
Backend mit Sperrunterstützung, ist `select_for_update()` wieder das richtige
Mittel — dann ist es eine Zeile an einer Stelle, weil der Austritt nur noch
einmal existiert.

## Erwogene Optionen

- **Vier weiterhin eigenständige Implementierungen** — verworfen. Der Preis war
  bereits fällig: Die Fragebogen-Item-Historie fehlte im Löschschutz, ihr
  Austritt lief ohne Transaktion und ohne Redirect. Anders als bei ADR-0017 gibt
  es hier keine absehbare Divergenz, die die Duplikation aufwöge.
- **Ein konkretes Modell mit `GenericForeignKey` für die Eigentümerschaft** —
  verworfen, aus demselben Grund wie in ADR-0017: echte Fremdschlüssel gegen
  polymorphen Zugriff einzutauschen, kostet Integrität und eine schwer
  umkehrbare Datenmigration.
- **`django-guardian`** — bereits von ADR-0032 verworfen: Die Eigentümerschaft
  ist kein Rechte-Gitter, sondern uniform und alles-oder-nichts.
- **Die Aufnahmeregel als Datenbank-Constraint oder `m2m_changed`-Signal** —
  verworfen. Die Rollenzugehörigkeit ist eine Regel an der Tür, kein
  Systemzustand: Ein Rollenentzug lässt eine bestehende Eigentümerschaft
  unberührt und muss das auch, sonst verwaisen Bestände. Eine Regel am Eingang,
  die eine Minute später nicht mehr gilt, als Invariante auszugeben, wäre
  irreführend.
- **Der Löschschutz über eine gepflegte Liste der Modelle** — verworfen. Sie ist
  genau die Liste, die die Fragebogen-Item-Historie vergessen hat.
- **Ein `aufnehmen()` neben dem Austritt** — verworfen. Die Aufnahme bleibt ein
  `add()` in der View; die Prüfung sitzt im `get_object_or_404` über die
  Kandidatenliste und liefert dort zugleich das 404. Die Asymmetrie ist gewollt:
  Der Austritt trägt eine Invariante und eine Transaktion, die Aufnahme trägt
  nichts.

## Folgen

- ADR-0039 ist fortgeführt: Der Kreis gleichrangiger Eigentümerinnen ist nun
  nicht nur überall derselbe Begriff, sondern derselbe Code. Die
  Sichtbarkeitsregel wohnt weiter am QuerySet, nur an einer Stelle statt an
  vier.
- ADR-0016 ist in einem Punkt nachgeführt: Die Gegenkante von `konten` in die
  Bestands-Apps entfällt. Die Zahl der Nähte bleibt zwei.
- Die eigenständige Implementierung je Artefakt aus ADR-0040 bleibt in Kraft.
  Diese Basis ist kein Präzedenzfall für eine Lebenszyklus-Basis; wer eine
  vorschlägt, argumentiert gegen ADR-0040, nicht mit diesem ADR.
- Der Austritt schweigt, wenn die Invariante greift, und meldet über seinen
  Rückgabewert nur, ob entfernt wurde. Die Oberfläche zeigt die
  Entfernen-Schaltfläche ohnehin erst ab zwei Eigentümerinnen; der Fall entsteht
  nur bei einem handgebauten POST oder im Wettlauf, und dort ist die unveränderte
  Detailseite die verständlichere Antwort als eine Fehlermeldung.
- Wer ein fünftes eigentümer-tragendes Modell einführt, erbt von
  `EigentuemerKreis`, setzt `ROLLENGRUPPE` und ist damit in Sichtbarkeit,
  Löschschutz und Vertragstest aufgenommen. Wer stattdessen ein eigenes M2M-Feld
  deklariert, fällt aus allen dreien heraus, ohne dass etwas rot wird — das ist
  die verbleibende Bruchstelle.
