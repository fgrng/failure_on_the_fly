---
status: accepted
---
# Eigentümerschaft: Privatheit, Kreis gleichrangiger Eigentümer:innen, Sichtbarkeit am QuerySet

Dieses ADR fasst den Stand von ADR-0015, ADR-0019, ADR-0022 und ADR-0032
zusammen und ersetzt sie. 

## Rollen sind additive Groups, Administration ist der Superuser

Autor:in, Ausbilder:in und Forschende:r sind permissionfreie **Django-Groups**
am eigenen Nutzer-Modell `konten.Konto`. Rollen sind **additiv**: Dieselbe
Person schreibt Vignetten und leitet eine Erhebung. Ein einzelnes `rolle`-Feld
zwänge sie zu zwei Konten und damit zu zwei getrennten Beständen.

Die Administrator:in ist keine Group, sondern `Konto.is_superuser`
(ADR-0033). Die Teilnehmer:in ist ebenfalls keine Group: In einer Erhebung ist
sie ein Teilnahme-Token ohne Konto (ADR-0006, ADR-0018), in einem Training unabhängig jeder anderen Rolle.

Groups tragen keine Django-Permissions. Wer eine Rolle prüft, prüft
Gruppenmitgliedschaft oder Superuser-Status, nie `has_perm`. Zwei Mechanismen
nebeneinander wären der Anfang von zwei Wahrheiten.

## Fachliche Bestände gehören einem Eigentümer-Kreis

Vignettenhistorie, Fragebogen-Item-Historie, Training und Erhebung tragen je
ein Many-to-Many `eigentuemerinnen` auf `Konto`: den **Eigentümer-Kreis**. Bei
Vignette und Fragebogen-Item hängt er an der **Historie**, nicht an der
Fassung, weil eine finale Fassung unveränderlich ist und ein Wechsel an ihr eine
Mutation wäre. Training und Erhebung tragen ihn am Objekt selbst.

Alle Eigentümer:innen sind **gleichrangig**, Eigentümerschaft ist
**alles-oder-nichts** je Objekt: sehen, bearbeiten, finalisieren, weitere
aufnehmen oder austreten, den Bestand in ein eigenes Training oder eine eigene
Erhebung ziehen. Es gibt kein Through-Model, keine ausgezeichnete Urheberin,
kein Leserecht ohne Schreibrecht. Wer Ko-Autor:in ist, ist Mitglied des
Kreises; Ko-Autorschaft ist der Weg hinein, der Kreis ist das Gebilde.

Keinen Eigentümer-Kreis tragen der Simulationskern, die Modell-Konfiguration
und die Transkriptions-Konfiguration. Sie gehören der Administration, gelten
instanzweit und sind die einzigen geteilten fachlichen Bestände. Der Kern ist
davon das einzige versionierte Artefakt.

Die technische Basis dieser vier Kreise ist in ADR-0037 festgelegt.

## Privat heißt: sichtbar für den Kreis und die Administration

Es gibt kein Veröffentlichen und deshalb keinen Status *veröffentlicht* im
Lebenszyklus. Sichtbarkeit ist kein Attribut, sondern eine Konstante: Ein
Bestand ist sichtbar für seinen Eigentümer-Kreis und für die Administration,
für niemanden sonst.

Zwei bewusste Ausnahmen:

- **Die Erhebung teilt ihren Bestand.** Eine Vignette oder ein
  Fragebogen-Item lässt sich in eine Erhebung einbinden, wenn sich ihr
  Eigentümer-Kreis mit dem der Erhebung schneidet. Jede Ko-Forschende sieht
  über Detailansicht und Export der gemeinsamen Erhebung auch Inhalte, an denen
  sie nicht Ko-Autor:in ist. Privatheit regelt den Zugriff auf den Bestand,
  nicht die Unsichtbarkeit jedes Inhalts in einer gemeinsam verantworteten
  Erhebung.
- **`fach` und `thema`** sind geteiltes Curriculum-Vokabular. Ihre Bezeichner
  aus allen finalen Vignetten dürfen als unverbindliche Vorschläge im Editor
  erscheinen (#65). Die Vignetteninhalte bleiben privat.

## Die Sichtbarkeitsregel lebt am QuerySet

Eigentümerschaft ist eine **Abfrage**, kein Recht. Sie wird nicht geprüft,
sondern gefiltert: Was einem nicht gehört, existiert nicht. Die Regel ist eine
benannte QuerySet-Methode,

```python
Vignette.objects.sichtbar_fuer(request.user)
```

die Mengenzugehörigkeit im Kreis prüft und für die Administration ungefiltert
liefert. Sie ist ohne HTTP testbar, an einer Stelle korrigierbar, und eine View
kann sie nicht umgehen, weil das ungefilterte QuerySet in keiner View vorkommt.
Der Sonderfall Administration steht damit an genau einer Stelle.

Analog liegt die Rolle-oder-Administration-Regel als benannte
Konto-QuerySet-Methode vor (ADR-0033).

## Verantwortung bleibt beweglich, wird aber nie leer

Jeder **aktive** Bestand hat mindestens eine Eigentümer:in. Eine
Übertragungs-Operation gibt es nicht: Übertragung ist die Änderung des Kreises,
Nachfolger:in aufnehmen und dann selbst austreten. Ein zweiter Weg zu demselben
Zustand wäre eine zweite Wahrheit.

Konten tragen personenbezogene Daten und müssen physisch löschbar sein. Der
Konto-Löschpfad in `konten` prüft die Invariante: Wer allein einen aktiven
Bestand hält, kann nicht gelöscht werden, bevor eine Nachfolger:in im Kreis
steht. Archivierte Vignettenhistorien und archivierte Erhebungen dürfen
eigentümerlos werden; ihr Forschungswert hängt am gepinnten
Fassungs-Fremdschlüssel, nicht an der Eigentümerschaft. Training hat bewusst
keinen Archiv-Zustand. Die Invariante ist eine Zählung über Through-Zeilen und
lebt deshalb auf App-Ebene, nicht im Schema (Details in ADR-0037).

Der Kreis einer finalisierten Erhebung und eines veröffentlichten Trainings
bleibt änderbar. Eingefroren ist das Design, nicht die Verantwortung.

## Erwogene Optionen

- **Ein `rolle`-Enum am Nutzer, geprüft in View-Decorators** — verworfen.
  Genau eine Rolle je Person, und die Sichtbarkeitsregel in jeder View erneut.
- **Django-Permissions an den Groups** — verworfen. Eine zweite
  Rechtewahrheit neben der Gruppenmitgliedschaft.
- **Einzelner Eigentümer-Fremdschlüssel plus Übertragung** — verworfen. Die
  Domäne will echte Ko-Autorschaft, nicht eine Person, die einer anderen
  Leserechte gibt. War der Ausgangszustand (ADR-0019) und wurde durch das M2M
  abgelöst (ADR-0022).
- **Through-Model mit ausgezeichneter Urheberin** — verworfen, solange kein
  Fall verlangt, dass eine Eingeladene weniger darf. Additiv nachrüstbar.
- **`django-guardian`** — verworfen, zweimal. Eine per-Objekt-, per-Nutzer-,
  per-Permission-Matrix für einen Fall, der uniform ist. Wird erst dann wieder
  eine Frage, wenn ungleiche Beteiligung gebraucht wird.
- **Ein Status *veröffentlicht*** — verworfen. Es gibt nichts zu
  veröffentlichen; Teilen läuft über den Kreis oder die gemeinsame Erhebung.

## Folgen

- Zwei Forschende an derselben Studie teilen Vignetten, indem sie beide in den
  Kreis eintreten oder eine gemeinsame Erhebung verantworten. Eine
  Ausbilder:in baut kein Training aus Vignetten, an denen sie nicht beteiligt
  ist.
- „Höchstens ein Entwurf je Historie" (ADR-0040) folgt nicht mehr aus der
  Privatheit, weil zwei Ko-Autor:innen gleichzeitig bearbeiten wollen könnten.
  Der partielle Unique-Index trägt die Invariante als echte Schranke.
- Die „Bibliothek dokumentierter Fehlvorstellungen" aus ADR-0001 entsteht je
  Kreis, nicht instanzweit.
- Der Weggang einer Eigentümer:in bleibt ein menschlicher Übergang; nichts
  wird automatisch übertragen, nichts wird automatisch eigentümerlos, solange
  es aktiv ist.
- Fiele die Privatheit weiter, bliebe der Kreis richtig, wäre aber nicht mehr
  die ganze Antwort. `sichtbar_fuer` ist die Stelle, an der eine Zugriffsregel
  mit mehreren Beteiligten einzöge.
