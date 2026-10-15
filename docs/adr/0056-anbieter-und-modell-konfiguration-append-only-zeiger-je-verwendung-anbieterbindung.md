---
status: amended
amended-by: [ADR-0067, "#496"]
---

# Anbieter und Modell-Konfiguration: append-only, ein Zeiger je Verwendung, Anbieterbindung statt Modellliste

> **Nachgeführt durch ADR-0067, #496:** Die Transkriptions-Konfiguration
> ist kein veränderlicher Singleton mehr, sondern append-only wie die
> Modell-Konfiguration: Fassungen werden neu angelegt, nur das Token ist
> rotierbar, genau eine ist aktiv. Jede Sitzung pinnt die aktive Fassung, und
> die referenzierten Fassungen gehen ohne Token in den Export. Beide
> Konfigurationen tragen eine Zero-Retention-Erklärung; für die Verwendung
> *Schüler:in* ist nur eine erklärte Fassung oder `fake` aktivierbar. Der
> Provider-Filter bleibt als technische Sicherung, trägt die Zusage aber nicht
> mehr allein: Der Satz in Regel 3, ein Tor im selben Formular wie die
> Anbieterwahl sei keins, gilt für die Erklärung nicht, denn sie hängt an einer
> unveränderlichen Fassung und ist nur zu widerrufen.

Dieses ADR fasst den Stand von ADR-0013 (samt Nachführung durch ADR-0046),
ADR-0036 und ADR-0038 zusammen und ersetzt sie. Die Transkription als
Auftragsverarbeitung regelt weiterhin ADR-0026; die Evals ADR-0046.

## Die Modell-Konfiguration ist append-only

Eine **Modell-Konfiguration** (Anbieter, Zugangsdaten, Sprachmodell,
Parameter, Bezeichnung) ist unveränderlich, sobald sie existiert. Eine
Änderung legt einen neuen Datensatz an; der alte bleibt. Sie ist **kein
versioniertes Artefakt** im Sinne von ADR-0040: kein Entwurf, kein
Finalisieren, keine benennbare Historie. Der Entwurf/Final-Zyklus existiert,
damit Autor:innen an einem Text arbeiten können, bis er reif ist; an einer
Modell-Konfiguration arbeitet niemand, sie wird gesetzt. Append-only liefert
die Unveränderlichkeit, auf die die Datenspur angewiesen ist, ohne die
Redaktionszeremonie für eine Betriebsentscheidung. Die Modell-Konfiguration
hängt ausdrücklich nicht an der Vignette und nicht am Kern, weil sie eine
Betriebsgröße ist (ADR-0004).

Die **Bezeichnung** wird beim Anlegen vergeben und ist danach so unveränderlich
wie alles an ihr; sie macht die Konfiguration in den Auswahlen und im Export
(ADR-0029) wiederfindbar.

## Das „aktiv" lebt in einer Zeigertabelle, genau eine je Verwendung

„Unveränderlich" und „genau eine ist aktiv" können nicht beide an derselben
Zeile gelten: Ein `aktiv`-Boolean würde beim Umschalten die alte Zeile
mutieren. Das „aktiv" lebt deshalb in einer eigenen Zeigertabelle
(`AktiveModellKonfiguration`), deren Zeilen per Fremdschlüssel auf eine
Konfiguration zeigen. Umschalten bewegt den Zeiger über eine einzige
Manager-Methode; die Konfigurationszeilen behalten kein schreibbares Feld.

Die Zeigertabelle trägt **eine Zeile je Verwendung**, und die Verwendung ist
ihre Unique-Spalte: *Schüler:in* (die Simulation in Sitzung und Probelauf),
*Lehrperson* und *Bewerter* (die Evals, ADR-0046). Die Evals sollen simulierte
Lehrperson und Bewerter mit anderen Modellen und Anbietern betreiben können als
die Simulation; ein Bewerter auf demselben Modell wie die Geprüfte urteilt
befangen. Was sich unterscheidet, ist die Verwendung, nicht das Ding; deshalb
ein Zeiger mehr statt eines neuen Artefakts. Dieselbe Konfiguration darf
mehreren Verwendungen dienen. Eine Verwendung darf unbelegt sein; die
Oberfläche zeigt dann nichts von Evals.

Eine **Historie des Umschaltens** wird nicht aufbewahrt. Die Frage „auf
welchem Modell lief *diese* Erhebung?" beantwortet der Pin, nicht eine globale
Chronik.

## Die Erhebung pinnt, das Training nicht

Die **Erhebung** pinnt beim Finalisieren die aktive Konfiguration der
Verwendung *Schüler:in* per Fremdschlüssel (ADR-0027). Das **Training** pinnt
nichts und läuft auf der jeweils aktiven. Ohne Pin könnte eine Administrator:in
mitten in einer laufenden Erhebung das Modell wechseln; die ersten dreißig
Teilnahmen liefen dann auf einem Modell, die letzten zwanzig auf einem anderen.
Die Datenspur wüsste es, aber die Erhebung wäre zerschnitten. Jede Sitzung
protokolliert zusätzlich die verwendete Konfiguration (ADR-0040).

## Die Anbieterbindung liegt an der Konfiguration

Eine Sitzung läuft über den Anbieter, den die Konfiguration benennt. Dafür
trägt sie eine **Anbieter-Feldgruppe**: `anbieter` aus fester Auswahl,
`anbieter_basis_url` und `anbieter_token`. Die Sprachmodell-Naht reicht Token
und Basis-URL an den Aufruf durch; keine Umgebungsvariable entscheidet mit. Ein
Anbieterwechsel ist damit ein Vorgang in der Anwendung, kein Eingriff ins
Deployment, und Sprachmodell und Transkription kollidieren nicht mehr an einem
geteilten Schlüssel.

**Genau zwei echte Anbieter**, dazu `fake` für den Betrieb ohne Netz:

- **OpenRouter** ist ein Router auf die großen Anbieter und bringt die
  Breite: mehrere hundert Modelle mit Structured Output. Modellname mit Präfix
  `openrouter/`, Token, keine Basis-URL.
- **Infomaniak** bringt die souveräne Alternative: Schweizer Rechenzentren,
  Open-Source-Modelle und eine Datenschutzzusage, die inhaltlich dem
  entspricht, was ADR-0026 für die Transkription verlangt. Modellname mit
  Präfix `openai/`, Basis-URL und Token.
- **`fake`** verlangt den Modellnamen `fake`, kein Token, keine Basis-URL,
  und wählt den deterministischen Adapter; der magische Modellname allein
  tut das nicht mehr.

OpenAI direkt wird nicht aufgenommen: Was es bietet, ist über OpenRouter
erreichbar, und ein dritter Zugangsweg brächte einen dritten Satz Zugangsdaten
ohne eigenen Nutzen. Beide Anbieter sind an echten Konten verifiziert
(`docs/research/2026-09-18-zulaessige-anbieter-und-modelle.md`); Infomaniak
liefert Structured Output mit `strict: true` nachweislich, womit ADR-0005 dort
trägt. **Ein dritter Anbieter ist keine Erweiterung dieses ADR, sondern seine
Revision**: Die Zahl zwei ist eine Entscheidung, keine Schranke der Technik.

Das Token liegt im **Klartext** in der Datenbank. Eine Feldverschlüsselung
unterbleibt bewusst: Der einzige verfügbare Schlüssel wäre `SECRET_KEY`, und
der liegt in derselben Datei-Umgebung wie die SQLite-Datenbank. Wer die
Datenbankdatei hat, hat die Zugangsdaten. In der Oberfläche ist das Token
write-only und maskiert, im Export fehlt es.

## Der Modellname wird nicht gegen eine Liste geprüft

Der Modellname bleibt freier Text. Eine Namens-Whitelist wäre
**Scheinsicherheit**: Bei OpenRouter hängt Structured Output am **Endpunkt**,
nicht am Modell; `supported_parameters` ist auf Modellebene die Vereinigung
über alle Endpunkte, und das Routing kann auf einem Endpunkt landen, der es
nicht kann. Eine harte Prüfung machte zudem das Anlegen einer Konfiguration von
der Erreichbarkeit einer fremden API abhängig und sperrte neu freigeschaltete
Modelle aus, bis die Liste nachzieht.

Drei Tore prüfen stattdessen, in dieser Reihenfolge:

1. **Die Anbieterbindung.** Der Modellname trägt das Präfix des gewählten
   Anbieters, und die verlangten Zugangsdaten sind da. Das fängt den
   vertauschten Anbieter, nicht den Tippfehler. Die Prüfung läuft in `save()`
   über `full_clean()` und damit genau einmal je Objekt, auch für Shell und
   Seeds.
2. **Der Probelauf** (ADR-0014). Ein falsch geschriebenes oder untaugliches
   Modell meldet sich beim ersten echten Aufruf, vor jeder Erhebung. Die
   Meldung des Anbieters benennt den Tippfehler als Anbieterfehler; das ist
   der bewusst gezahlte Preis.
3. **Die Aufrufparameter.** Bei OpenRouter setzt die Naht den
   **Provider-Filter** (`require_parameters`, `data_collection: deny`,
   `zdr`) selbst. Er trägt die datenschutzrechtliche Zusage aus ADR-0026 und
   erzwingt einen Endpunkt mit Structured Output; ein Tor, das im selben
   Formular abschaltbar wäre, in dem man den Anbieter wählt, ist keins. Bei
   Infomaniak ist `json_schema` die einzige unterstützte Form. Der Filter
   folgt eindeutig aus `anbieter` und wird deshalb nicht eigens exportiert.

Das **Modellverzeichnis**, das ein Anbieter auf Knopfdruck liefert, ist eine
Autovervollständigung (#202): ein Vorschlag, nie eine Prüfung.

## `parameter` trägt nur Mikro-Stellschrauben, geprüft per Allowlist

`parameter` wird roh in den SDK-Aufruf gespreizt und vollständig exportiert
(ADR-0029). Es nimmt deshalb ausschließlich Einstellungen auf, die das
Modellverhalten auf Mikroebene steuern: `temperature`, `top_p`, `max_tokens`,
`max_completion_tokens`, `reasoning_effort`, `thinking`, `seed`, `stop`,
`presence_penalty`, `frequency_penalty`, `logit_bias`, `verbosity`. Beim
Anbieter `fake` sind stattdessen genau `skript`, `skript_fortlesen` und
`verzoegerung` erlaubt; bei echten Anbietern sind sie verboten.

Geprüft wird mit einer **Allowlist**, nicht mit einer Denylist der
Verbindungsschlüssel. Eine Denylist reicht nachweislich nicht: Der Aufruf nimmt
beliebige weitere Parameter entgegen, darunter `mock_response`; damit liefe
eine vollständige Erhebung mit erfundenen Antworten durch, ohne Netzaufruf und
ohne Fehlermeldung, und die Datenspur sähe echt aus. `extra_body` steht nicht
in der Allowlist, womit der Provider-Filter nicht überschreibbar ist. In den
Parametern können keine Geheimnisse stehen; ihre Sichtbarkeit in der
Erhebungsansicht ist keine Abwägung.

## Die Transkriptions-Konfiguration ist das Gegenstück

Sprachmodell und Transkription werden getrennt konfiguriert und dürfen an
verschiedenen Anbietern hängen; die datenschutzrechtlich attraktivste
Betriebsvariante (Sprachmodell über OpenRouter wegen der Modellauswahl, Audio
über Infomaniak, weil die Stimme das biometrische Datum ist) ist damit
konfigurierbar. Beide Objekte tragen dieselbe Anbieter-Feldgruppe und bewusst
**entgegengesetzte Lebenszyklen**: Die Modell-Konfiguration ist append-only,
weil die Erhebung sie pinnt; eine Schlüsselrotation ist dort Anlegen plus
Aktivieren. Die Transkriptions-Konfiguration ist ein **veränderlicher
Singleton**: Sie wird nicht gepinnt und nicht exportiert (ADR-0026), also
braucht niemand eine alte Fassung. Der Kontrast ist die Aussage: Was die
Datenspur trägt, ist unveränderlich; was den Auftragsverarbeiter benennt, ist
es nicht.

## Erwogene Optionen

- **Ein `aktiv`-Boolean an der Konfiguration** — verworfen. Umschalten
  mutierte die alte Zeile, und „genau eine" ließe sich nicht als Index
  erklären.
- **Ein neues Artefakt je Eval-Rolle statt eines Zeigers je Verwendung** —
  verworfen (ADR-0046). Was sich unterscheidet, ist die Verwendung.
- **Zeitstempel für die Umschalt-Historie** — verworfen. Der Pin der Erhebung
  beantwortet die einzige Frage, die gestellt wird.
- **Eine erzwungene Liste zulässiger Modelle**, als Auswahlfeld oder als
  Prüfung gegen die Anbieter-API — verworfen; Scheinsicherheit, siehe oben.
- **Ein Rauchtest beim Anlegen** (echter Aufruf) — verworfen: Er kostet einen
  Netzaufruf im Formular und Geld und scheitert genau bei einer Störung.
- **Eine Denylist der Verbindungsschlüssel in `parameter`** — verworfen; sie
  fängt `mock_response` nicht.
- **`skript` als eigenes Feld** — verworfen; die anbieterabhängige Allowlist
  löst den Fall ohne Feld.
- **Feldverschlüsselung des Tokens** — verworfen; der Schlüssel läge neben der
  Datenbank.
- **Der Provider-Filter als Eintrag in `parameter`** — verworfen; sein Fehlen
  wäre lautlos.
- **OpenAI als dritter Anbieter** — verworfen; über OpenRouter erreichbar.
- **Eine gemeinsame Seite für beide Konfigurationen** — verworfen; sie
  stellte „anlegen, nie ändern, dann aktivieren" neben „einfach
  überschreiben".

## Folgen

- Wird ein Modell abgekündigt, während eine Erhebung läuft, muss jemand
  eingreifen und die Erhebung umstellen oder abschließen: ein sichtbarer,
  entscheidbarer Vorgang statt eines stillen Bruchs.
- Administrator:innen erproben eine neue Konfiguration im Probelauf, bevor sie
  sie aktivieren (ADR-0014).
- Der Begriff „Fassung" meint bei der Modell-Konfiguration einen append-only
  Datensatz, bei den versionierten Artefakten eine Fassung mit Lebenszyklus.
- Die Seeds legen `fake`-Konfigurationen an; Entwicklung und Workshop laufen
  ohne Zugangsdaten und ohne Netz. Wer echte Antworten will, legt eine
  Konfiguration mit Anbieter und Token an und aktiviert sie; das ist der
  Betriebsschritt nach dem Deployment und zugleich die Rotationsfolge.
- Die Wahl des Anbieters ist eine datenschutzrechtlich tragende Entscheidung
  (ADR-0026); der Export trägt `anbieter` vor dem Modellnamen, weil derselbe
  Modellstring bei verschiedenen Anbietern Verschiedenes bedeutet (ADR-0029).
