---
status: accepted
---

# Die Anbieterbindung liegt an der Konfiguration

Eine Sitzung läuft über den Anbieter, den die aktive Modell-Konfiguration
benennt. Die Konfiguration trägt dafür eine Feldgruppe: `anbieter` aus fester
Auswahl (`fake`, `openrouter`, `infomaniak`, Vorgabe `fake`),
`anbieter_basis_url` und `anbieter_token`. Die Sprachmodell-Naht reicht Token
und Basis-URL an den Aufruf durch; keine Umgebungsvariable entscheidet mehr
mit.

Vier Entscheidungen hängen daran zusammen.

## 1. Zugangsdaten an der Konfiguration statt in der Umgebung

Bisher zog die Naht den Schlüssel für `openai/`-Modelle aus `OPENAI_API_KEY` —
denselben, den die Transkription benutzt. Sobald Sprachmodell und Transkription
an verschiedenen Anbietern hängen, kollidiert das, und ein Anbieterwechsel ist
ein Eingriff ins Deployment statt ein Vorgang in der Anwendung.

Der Modellname bleibt freier Text und wird **nicht** gegen eine Liste geprüft:
Bei OpenRouter hängt Structured Output am Endpunkt, nicht am Modell, eine
Namensliste wäre Scheinsicherheit. Geprüft wird stattdessen die Bindung an den
Anbieter — `fake` verlangt den Modellnamen `fake` ohne Endpunkt und ohne Token,
`openrouter` das Präfix `openrouter/` und ein Token, `infomaniak` das Präfix
`openai/` sowie Basis-URL und Token. Ein Modell ohne Structured Output fällt im
Probelauf auf, das ist die Rolle, die ADR-0014 ihm gibt.

Das Token liegt im Klartext in der Datenbank. Eine Feldverschlüsselung
unterbleibt bewusst: Der einzige verfügbare Schlüssel wäre `SECRET_KEY`, und
der liegt in derselben Datei-Umgebung wie die SQLite-Datenbank. Das Restrisiko
ist ausdrücklich festgehalten: Wer die Datenbankdatei hat — etwa aus einem
Backup oder einer Entwicklungskopie —, hat die Zugangsdaten.

## 2. `parameter` trägt nur Mikro-Stellschrauben, geprüft per Allowlist

`parameter` wird roh in den SDK-Aufruf gespreizt und vollständig in die
Datenspur exportiert (ADR-0029). Es nimmt deshalb ausschließlich
Einstellungen auf, die das Modellverhalten auf Mikroebene steuern:
`temperature`, `top_p`, `max_tokens`, `max_completion_tokens`,
`reasoning_effort`, `thinking`, `seed`, `stop`, `presence_penalty`,
`frequency_penalty`, `logit_bias`, `verbosity`. Beim Anbieter `fake` ist genau
`skript` erlaubt und sonst nichts; bei echten Anbietern ist `skript` verboten.

Geprüft wird mit einer **Allowlist**, nicht mit einer Denylist der
Verbindungsschlüssel. Eine Denylist reicht nachweislich nicht: Der Aufruf nimmt
neben den benannten Parametern beliebige weitere entgegen, darunter
`mock_response` — damit liefe eine vollständige Erhebung mit erfundenen
Antworten durch, ohne Netzaufruf, ohne gültigen Schlüssel und ohne
Fehlermeldung, und die Datenspur sähe echt aus. Der Fake-Sonderfall, an dem
eine naive Allowlist bricht, löst sich durch die Anbieterabhängigkeit: `skript`
ist der Konfigurationskanal des zweiten Adapters und braucht weder ein eigenes
Feld noch einen Ausweg aus `parameter`.

Damit können in den Parametern keine Geheimnisse mehr stehen; ihre Sichtbarkeit
in der Erhebungsansicht ist keine Abwägung mehr.

## 3. Zwei Konfigurationsobjekte mit entgegengesetztem Lebenszyklus

Sprachmodell und Transkription werden getrennt konfiguriert und dürfen an
verschiedenen Anbietern hängen. Beide Objekte tragen dieselbe Anbieter-
Feldgruppe und bewusst entgegengesetzte Lebenszyklen: Die Modell-Konfiguration
bleibt append-only und unveränderlich, weil die Erhebung ihre Fassung pinnt
(ADR-0013); eine Schlüsselrotation ist dort Anlegen plus Aktivieren, kein
Feldupdate. Die Transkriptions-Konfiguration ist ein veränderlicher Singleton:
Sie wird nicht gepinnt und nicht exportiert (ADR-0026), also braucht niemand
eine alte Fassung. Der Kontrast ist die Aussage: Was die Datenspur trägt, ist
unveränderlich; was den Auftragsverarbeiter benennt, ist es nicht.

## 4. Der Provider-Filter ist abgeleitet, nicht konfigurierbar

Bei `anbieter == "openrouter"` setzt die Naht den Provider-Filter
(`require_parameters: true`, `data_collection: "deny"`, `zdr: true`) selbst;
`extra_body` steht nicht in der Allowlist und ist damit gesperrt. Er trägt die
datenschutzrechtliche Zusage aus ADR-0026, und ein Tor, das im selben Formular
abschaltbar wäre, in dem man den Anbieter wählt, ist keins — beim
Zero-Retention-Tor merkt man das Fehlen, beim Provider-Filter nicht. Eigens
exportiert wird er nicht: Er folgt eindeutig aus `anbieter`, den der Export
trägt.

## Erwogene Optionen

- **Eine erzwungene Liste zulässiger Modelle** — verworfen; siehe (1).
- **Ein Rauchtest beim Anlegen** (echter Aufruf gegen das Modell) — verworfen:
  Er kostet einen Netzaufruf im Formular und Geld.
- **Eine Denylist der Verbindungsschlüssel in `parameter`** — verworfen; sie
  fängt `mock_response` nachweislich nicht.
- **`skript` als eigenes Feld neben `parameter`** — verworfen; die
  Anbieterabhängigkeit der Allowlist löst denselben Fall ohne Feld.
- **Feldverschlüsselung des Tokens** — verworfen; der Schlüssel läge neben der
  Datenbank, das Geheimnis wäre verschoben statt geschützt.
- **Der Provider-Filter als Eintrag in `parameter`** — verworfen; sein Fehlen
  wäre lautlos.
- **Eine gemeinsame Seite für beide Konfigurationen** — verworfen; sie stellte
  „anlegen, nie ändern, dann aktivieren" neben „einfach überschreiben".

## Folgen

- Die Prüfung greift am Modell: `save()` ruft beim Anlegen `full_clean()`. Da
  die Modell-Konfiguration append-only ist, läuft sie genau einmal je Objekt —
  und gilt damit auch für Shell und Seeds, nicht nur für das Formular.
  Migrationen arbeiten auf historischen Modellen ohne dieses `save()`;
  ADR-0031 bleibt unberührt.
- Der deterministische Adapter wird über das Anbieterfeld gewählt, nicht mehr
  über den magischen Modellnamen `fake`.
- Die Seeds legen `fake`-Konfigurationen an; Entwicklung und Workshop laufen
  ohne Zugangsdaten und ohne Netz.
- Nach der Migration trägt jede Bestandszeile den Vorgabewert `fake`, ohne dass
  ein Modellname umgeschrieben wird. Eine solche Zeile ist inhaltlich überholt:
  Wer echte Antworten will, legt eine Konfiguration mit Anbieter und Token an
  und aktiviert sie. Das ist der Betriebsschritt nach dem Deployment und
  zugleich die Rotationsfolge.
- Neu ist, dass das Token grundsätzlich auch über die Oberfläche erreichbar
  wäre. Deshalb ist es dort write-only, in der Anzeige maskiert und nicht Teil
  des Exports.
