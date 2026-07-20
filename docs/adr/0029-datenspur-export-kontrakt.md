---
status: accepted
---

# Die Datenspur wird long-relational, selbsttragend und pro Erhebung exportiert

Der Export ist ein veröffentlichter Datenformatvertrag: Änderungen daran können
Analyseskripte und bereits ausgegebene Datensätze brechen. Er liefert einen
ZIP-Download mit relationalen CSV-Dateien nach RFC 4180. Jede Entität hat eine
eigene Tabelle; es gibt keinen Wide-Pivot und kein Einebnen. Das Pivotieren
bleibt der Forschenden und ihrer Auswertungssoftware überlassen.

Die Erhebung ist die Exporteinheit, über alle ihre Stichproben hinweg. Die
Stichprobe ist als Spalte an der Teilnahme enthalten und bildet damit die in
`CONTEXT.md` gemeinte Gruppenstruktur im Export ab. Ein Export je Stichprobe
wäre kein Abbild des Untersuchungsdesigns, sondern ein willkürlicher Ausschnitt.

Der Export ist selbsttragend: Die tatsächlich verwendeten Vignetten- und
Simulationskern-Fassungen sowie Modell-Konfigurationen werden mit vollständigem
Inhalt in eigenen Tabellen ausgeliefert und per ID referenziert. Kein
exportierter Fremdschlüssel zeigt ins Leere. So bleibt der Datensatz ohne
Datenbankzugriff interpretierbar, ohne denselben Fassungstext in jeder
Sitzungszeile zu wiederholen.

Die CSV schreibt `NA` für `NULL`; ein Leerstring bleibt leer. Ein
leeres CSV-Feld würde beide Werte einebnen. Das Ausgabeschema der
Sprachmodell-Naht prüft Denkspur und Äußerung nicht auf Nichtleere: Eine
inhaltsleere, aber erfolgreiche Antwort ist daher möglich. Der antwortlose
Gesprächsschritt nach ADR-0011 trägt dagegen `NULL`. Nur `NA` bewahrt diesen
Abbruch als unterscheidbaren Befund.

Historien-Tabellen werden nicht exportiert. Sie enthalten über ihre
Eigentümerinnen Klarnamen und gehören deshalb nicht in den pseudonymen
Datensatz. Die Historie bleibt allein als Gruppierungsschlüssel der verwendeten
Fassungen erhalten.

Transkribierte Eingaben sind im Export derzeit nicht erkennbar: Nach der
Transkription wird nur ihr Text als gewöhnliche Eingabe gespeichert. Diese
bekannte Grenze wird in #122 behandelt und blockiert den Export nicht.

## Dateiformat

Der ZIP-Download enthält **elf Dateien**, auch wenn eine von ihnen keine
Datenzeilen hat; sie enthält dann dennoch ihre Kopfzeile. Alle CSVs folgen RFC
4180: Sie verwenden Kommas, UTF-8 ohne BOM und doppelte Anführungszeichen;
Zeilenumbrüche innerhalb von Zellen bleiben erhalten. Wahrheitswerte erscheinen
als `True` oder `False`, Zeitstempel als ISO 8601 in UTC, sekundengenau und mit
`+00:00`. JSON-Felder stehen als gequoteter JSON-Text in einer Zelle, Bilder als
Pfade statt als Inhalt.

| Datei | Spalten |
| --- | --- |
| `erhebung.csv` | `id`, `name`, `randomisierung`, `instruktionstext`, `einwilligungstext`, `abschlusstext`, `modell_konfiguration_id` |
| `stichproben.csv` | `id`, `beginn`, `ende`, `archiviert` |
| `teilnahmen.csv` | `token`, `stichprobe_id`, `einwilligung_erteilt`, `audioverarbeitung_eingewilligt`, `randomisierungs_seed`, `erstellt_am` |
| `vignettenziehungen.csv` | `token`, `vignette_id`, `position` |
| `sitzungen.csv` | `id`, `token`, `position`, `status`, `vignette_id`, `simulationskern_id`, `modell_konfiguration_id`, `erstellt_am` |
| `gespraechsschritte.csv` | `id`, `sitzung_id`, `reihenfolge`, `eingabe`, `denkspur`, `aeusserung`, `native_reasoning_spur`, `erstellt_am` |
| `fehlversuche.csv` | `gespraechsschritt_id`, `grund`, `rohantwort` |
| `diagnosen.csv` | `sitzung_id`, `text`, `erstellt_am` |
| `vignettenfassungen.csv` | `id`, `historie_id`, `finalisiert_am`, `fehlermuster_beschreibung`, `lernauftrag`, `arbeitsheft_beschreibung`, `arbeitsheft_text`, `arbeitsheft_bild`, `schuelerin_name`, `schuelerin_geschlecht`, `lehrperson_name`, `lehrperson_geschlecht`, `fach`, `thema`, `klassenstufe`, `referenzdiagnose`, `budget_typ`, `budget_wert` |
| `simulationskerne.csv` | `id`, `historie_id`, `finalisiert_am`, `system_prompt_vorlage`, `user_prompt_vorlage`, `rahmenhandlung_einleitung`, `rahmenhandlung_gespraechseinleitung`, `rahmenhandlung_debrief` |
| `modellkonfigurationen.csv` | `id`, `sprachmodell`, `parameter` |

## Erwogene Optionen

- **Wide-Export mit einer Zeile je Teilnahme oder Sitzung** — verworfen. Er
  würde Gesprächsschritte, Fehlversuche und verwendete Fassungen entweder
  vervielfachen oder verlieren.
- **Leere Felder für `NULL`** — verworfen. Sie unterschieden einen Abbruch
  nicht mehr von einer erfolgreichen, inhaltsleeren Modellantwort.
- **Historien mit Eigentümerinnen exportieren** — verworfen. Sie würden die
  Pseudonymität des Forschungsdatensatzes brechen.

## Folgen

- CSV-Dateien, Schlüsselspalten und die Bedeutung von `NA` sind Teil des
  stabilen Datenformatvertrags.
- Auswertungen können alle Stichproben einer Erhebung gemeinsam lesen und bei
  Bedarf über die Stichprobenspalte gruppieren.
- Die vollständige Datenspur bleibt ohne Zugriff auf die Anwendungsdatenbank
  nachvollziehbar; Identitäten von Forschenden bleiben außerhalb des Exports.
