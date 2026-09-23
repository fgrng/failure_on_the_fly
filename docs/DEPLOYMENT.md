# Deployment auf Uberspace 7

Ein Walkthrough für den ersten Produktivbetrieb. Er führt von einem frischen
Uberspace bis zu einer Instanz, auf der eine Erhebung laufen kann, und beschreibt
danach den Betrieb: Update, Backup, Logs, Stolpersteine.

`isabell` steht überall für den eigenen Uberspace-Benutzernamen, `isabell.uber.space`
für dessen Standarddomain. Das README nennt nur die drei Dinge, die man vor dem
Deployment wissen muss; dieses Dokument ist die vollständige Anleitung mit
Inbetriebnahme und Betriebsteil.

Die Uberspace-Handbuchseiten, auf die sich die einzelnen Schritte stützen, sind
jeweils verlinkt; der Einstieg ist <https://manual.uberspace.de/>.

## 1. Betriebsbild

Was am Ende läuft:

```
Browser ──HTTPS──> Uberspace-Frontend (nginx + Apache, Let's-Encrypt-Zertifikat)
                     ├── /static  ──> Apache liefert Dateien aus ~/html/static
                     ├── /media   ──> Apache liefert Dateien aus ~/html/media
                     └── /        ──> gunicorn auf 0.0.0.0:8000 (nur intern erreichbar)
                                        └── Django (config.wsgi) ──> SQLite-Datei
```

Konsequenzen, die den Rest der Anleitung erklären:

- **Ein Prozess, mehrere Worker.** gunicorn läuft als supervisord-Dienst mit drei
  Workern. Ein Gesprächsschritt wartet synchron auf das Sprachmodell; deshalb das
  großzügige Worker-Timeout.
- **SQLite, kein MySQL.** Die Datenbank ist eine Datei im Home. Sie läuft im
  WAL-Modus mit wartendem Writer (siehe `config/settings.py`), damit mehrere
  gleichzeitige Teilnahmen parallel schreiben können. Das automatische
  MySQL-Backup von Uberspace greift hier folglich **nicht** — siehe Abschnitt 11.
- **Zugangsdaten liegen in der Datenbank, nicht in der Umgebung.** Sprachmodell-
  und Transkriptions-Anbieter werden nach der Installation über die Weboberfläche
  konfiguriert. Eine frisch migrierte Instanz hat kein antwortendes Sprachmodell.
- **TLS endet am Uberspace-Frontend.** gunicorn spricht dahinter HTTP; Django
  erkennt HTTPS am Header `X-Forwarded-Proto`.

## 2. Voraussetzungen

- Ein Uberspace-7-Account mit SSH-Zugang
  (<https://manual.uberspace.de/basics-ssh/>).
- Python 3.14 ist auf Uberspace vorhanden — das Projekt verlangt `>= 3.14`
  (<https://manual.uberspace.de/lang-python/>). Fehlt die Version auf dem
  Host, beschafft `uv python install 3.14` einen eigenen Interpreter ins Home;
  `uv sync` findet ihn dann ohne `--python`-Angabe.
- Zugriff auf das Git-Repository vom Uberspace aus (öffentliches HTTPS-Clone oder
  ein Deploy-Key, siehe Schritt 3).
- Optional eine eigene Domain samt Zugriff auf deren DNS (Schritt 8).
- Die Anbieter-Zugangsdaten für Sprachmodell und, falls gesprochen werden soll,
  für die Transkription — Letztere nur mit vertraglich zugesicherter
  Zero-Retention (ADR-0026).

Alles Folgende passiert in einer SSH-Sitzung auf dem Uberspace:

```bash
ssh isabell@isabell.uber.space
```

## 3. Code holen

Bei einem öffentlichen Repository genügt ein HTTPS-Clone:

```bash
git clone https://github.com/fgrng/failure_on_the_fly.git ~/failure_on_the_fly
cd ~/failure_on_the_fly
```

Ist das Repository privat, wird auf dem Uberspace ein Schlüssel erzeugt und dessen
öffentlicher Teil als **Deploy-Key (nur Lesezugriff)** in den GitHub-Einstellungen
des Repositorys hinterlegt:

```bash
ssh-keygen -t ed25519 -C "uberspace-deploy" -f ~/.ssh/deploy_failure_on_the_fly
cat ~/.ssh/deploy_failure_on_the_fly.pub
git clone git@github.com:fgrng/failure_on_the_fly.git ~/failure_on_the_fly
```

Dafür braucht `~/.ssh/config` den passenden Eintrag:

```
Host github.com
  IdentityFile ~/.ssh/deploy_failure_on_the_fly
  IdentitiesOnly yes
```

`IdentitiesOnly` verhindert, dass ssh zuerst andere Schlüssel aus dem Agenten
anbietet und GitHub die Verbindung nach zu vielen Versuchen abweist.

## 4. Abhängigkeiten installieren

Das Projekt wird mit [uv](https://docs.astral.sh/uv/) installiert; uv landet im
Home und braucht keine Systemrechte:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc          # oder neu einloggen, damit ~/.local/bin im PATH liegt
uv --version
```

Danach die Produktiv-Abhängigkeiten — ohne Entwicklungswerkzeuge, dafür mit
gunicorn, und exakt nach `uv.lock`:

```bash
cd ~/failure_on_the_fly
uv sync --frozen --no-dev --group deploy --python python3.14
```

`--frozen` erzwingt, dass genau die gelockten Versionen installiert werden; schlägt
der Lauf mit einem Hinweis auf eine veraltete Lockdatei fehl, ist das Repository
nicht sauber ausgecheckt — dann nicht mit `uv lock` nachbessern, sondern den
Stand prüfen.

Eine kurze Kontrolle, dass die Umgebung steht:

```bash
.venv/bin/python --version      # 3.14.x
.venv/bin/gunicorn --version
```

## 5. Konfiguration anlegen

Die Instanz liest ihre Umgebung aus `~/failure_on_the_fly/.env`. Zuerst ein
Geheimnis erzeugen:

```bash
.venv/bin/python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Dann die Datei schreiben (Wert von oben einsetzen):

```bash
cat > ~/failure_on_the_fly/.env <<'EOF'
SECRET_KEY=<lange Zufallszeichenkette>
DEBUG=False
ALLOWED_HOSTS=isabell.uber.space
CSRF_TRUSTED_ORIGINS=https://isabell.uber.space
DATABASE_PFAD=/home/isabell/failure_on_the_fly/db.sqlite3
STATIC_ROOT=/home/isabell/html/static
MEDIA_ROOT=/home/isabell/html/media
TIME_ZONE=Europe/Berlin
TRANSKRIPTION_ZERO_RETENTION=False
EOF
chmod 600 ~/failure_on_the_fly/.env
```

Was die Werte bedeuten:

| Variable | Bedeutung |
| --- | --- |
| `SECRET_KEY` | Signiert Sitzungen und CSRF-Token. Ein Wechsel meldet alle Angemeldeten ab. Gehört in kein Git. |
| `DEBUG` | Muss `False` sein. Schaltet HTTPS-Weiterleitung, sichere Cookies und HSTS scharf und verhindert, dass Fehlerseiten interne Details zeigen. |
| `ALLOWED_HOSTS` | Kommaliste aller Hostnamen, unter denen die Instanz erreichbar ist. Fehlt ein Name, antwortet Django mit HTTP 400. |
| `CSRF_TRUSTED_ORIGINS` | Kommaliste mit Schema, also `https://…`. Ohne passenden Eintrag scheitert jedes Formular mit „CSRF verification failed“. |
| `DATABASE_PFAD` | Absoluter Pfad der SQLite-Datei. Explizit gesetzt, damit ein Cronjob oder ein Backup-Skript dieselbe Datei meint wie der Dienst. |
| `STATIC_ROOT` | Zielverzeichnis von `collectstatic`; zeigt ins Apache-Docroot. |
| `MEDIA_ROOT` | Ablage der hochgeladenen Vignettenbilder; zeigt ebenfalls ins Docroot. |
| `TIME_ZONE` | Zeitzone, in der Forschende Zeitpunkte eingeben und angezeigt bekommen — etwa der Erhebungszeitraum einer Stichprobe. Voreingestellt ist `Europe/Berlin`; gespeichert wird unabhängig davon immer in UTC. |
| `TRANSKRIPTION_ZERO_RETENTION` | Schaltet die Audio-Transkription frei. Erst auf `True` setzen, wenn die Zero-Retention des Anbieters vertraglich zugesichert ist. |
| `SECURE_SSL_REDIRECT` | Optional. Nur auf `False` setzen, wenn die Instanz in eine Weiterleitungsschleife läuft (siehe Abschnitt 13). |

Bei einer eigenen Domain (Schritt 8) gehören deren Namen zusätzlich in
`ALLOWED_HOSTS` und `CSRF_TRUSTED_ORIGINS`.

## 6. Datenbank und Dateien vorbereiten

```bash
cd ~/failure_on_the_fly
mkdir -p ~/html/static ~/html/media
uv run python manage.py migrate
uv run python manage.py collectstatic --noinput
```

`migrate` legt nebenbei die drei fachlichen Rollen als Django-Groups an
(`konten/apps.py`, post_migrate) — `Autor:in`, `Ausbilder:in`, `Forschende:r`
müssen also nicht von Hand erzeugt werden. Die Administration ist keine Group,
sondern ein Superuser (ADR-0033).

Eine erste Kontrolle ohne laufenden Dienst:

```bash
uv run python manage.py check --deploy
```

Erwartet wird genau eine Warnung, `security.W021` zu `SECURE_HSTS_PRELOAD`; die
ist bewusst offen gelassen, weil die Preload-Liste ein einseitiges Versprechen
gegenüber allen Browsern ist. Jede andere Warnung — zu `SECRET_KEY`, `DEBUG` oder
den Cookie-Flags — zeigt einen Fehler in der `.env`.

## 7. Dienst einrichten

Siehe <https://manual.uberspace.de/daemons-supervisord/>. Die Dienstdefinition
liegt in `~/etc/services.d/`:

```bash
mkdir -p ~/etc/services.d
cat > ~/etc/services.d/failure-on-the-fly.ini <<'EOF'
[program:failure-on-the-fly]
directory=%(ENV_HOME)s/failure_on_the_fly
command=%(ENV_HOME)s/failure_on_the_fly/.venv/bin/gunicorn --error-logfile - --bind 0.0.0.0:8000 --workers 3 --timeout 180 config.wsgi:application
startsecs=30
autostart=yes
autorestart=yes
EOF
```

Zu den Werten:

- **`--bind 0.0.0.0:8000`** — das Uberspace-Frontend erreicht nur Dienste auf
  `0.0.0.0` oder `::`; `127.0.0.1` funktioniert ausdrücklich nicht. Der Port ist
  frei wählbar zwischen 1024 und 65535, muss aber zum Backend in Schritt 8 passen.
- **`--workers 3`** — drei gleichzeitige Anfragen. Da ein Gesprächsschritt
  synchron auf das Sprachmodell wartet, belegt jede laufende Antwort einen Worker.
  Für eine Erhebung mit vielen parallelen Teilnahmen darf der Wert höher liegen;
  jeder Worker kostet Arbeitsspeicher.
- **`--timeout 180`** — Notbremse, nicht Normalfall. Beide Nähte begrenzen sich
  selbst: Ein Gesprächsschritt wartet über alle Versuche zusammen höchstens 90 s,
  eine Transkription höchstens 120 s. Das Worker-Timeout muss darüber liegen,
  sonst tötet gunicorn eine Anfrage, die noch legitim wartet.
- **`--error-logfile -`** — gunicorn schreibt seine Fehler nach stderr, wo
  supervisord sie einsammelt.

Dienst registrieren und starten:

```bash
supervisorctl reread
supervisorctl update
supervisorctl status failure-on-the-fly
```

Erwartet wird `RUNNING`. Bei `BACKOFF` oder `FATAL` zeigt
`supervisorctl tail -f failure-on-the-fly stderr` den Grund — meist ein fehlender
`SECRET_KEY` in der `.env` oder ein belegter Port.

## 8. Web-Backends und Domain verbinden

Siehe <https://manual.uberspace.de/web-backends/>. Apache liefert die statischen
Dateien und die Vignettenbilder direkt aus, alles Übrige geht an gunicorn:

```bash
uberspace web backend set /static --apache
uberspace web backend set /media --apache
uberspace web backend set / --http --port 8000
uberspace web backend list
```

In der Liste muss der Eintrag für `/` als `http:8000` mit dem Vermerk `OK`
erscheinen. `no service` heißt: Der Dienst läuft nicht oder lauscht auf einem
anderen Port.

Die Vignettenbilder sind nur durch ihre nicht erratbaren Dateinamen geschützt
(Abschnitt 14). Damit Apache die Namen nicht als Verzeichnisliste preisgibt,
bekommt das Medienverzeichnis eine `.htaccess`, die Listing und Skriptausführung
abschaltet:

```bash
cat > ~/html/media/.htaccess <<'EOF'
Options -Indexes -ExecCGI
php_flag engine off
EOF
```

Kontrolle: `https://isabell.uber.space/media/vignettenbilder/` muss mit 403
antworten, nicht mit einer Dateiliste.

Soll die Instanz unter einer eigenen Domain laufen
(<https://manual.uberspace.de/web-domains/>):

```bash
uberspace web domain add erhebung.example.org
```

Der Befehl nennt die einzutragenden A- und AAAA-Records. Sobald das DNS zeigt,
stellt Uberspace automatisch ein Let's-Encrypt-Zertifikat aus; das kann einige
Minuten dauern. Jede Subdomain wird einzeln hinzugefügt, Wildcards gibt es nicht.
Danach den Namen in `.env` unter `ALLOWED_HOSTS` und `CSRF_TRUSTED_ORIGINS`
ergänzen und `supervisorctl restart failure-on-the-fly` ausführen.

## 9. Inbetriebnahme

Die Migration allein macht die Instanz nicht betriebsbereit. Es fehlen die
Administration, der Simulationskern und die Modell-Konfiguration.

1. **Administration anlegen:**

   ```bash
   cd ~/failure_on_the_fly
   uv run python manage.py createsuperuser
   ```

2. **Simulationskern anlegen**, falls noch keine Fassung existiert. Unter
   `/system/kern/verwalten/` stehen dafür zwei Knöpfe: *Neuen Entwurf anlegen*
   legt eine leere erste Fassung an, *Standardkern als Entwurf anlegen* füllt
   sie mit dem Standardkern. Beide erzeugen einen **Entwurf** — er
   wird erst spielbar, wenn Sie ihn auf derselben Seite finalisieren; dazwischen
   können Sie die Vorlagen unter *Bearbeiten* an Ihre Instanz anpassen.

   Für eine unbeaufsichtigte Einrichtung ohne Anmeldung gibt es denselben Weg
   als Befehl. Er legt den Standardkern an und finalisiert ihn in einem Schritt;
   ein wiederholter Aufruf ändert nichts:

   ```bash
   uv run python manage.py kern_initialisieren
   ```

3. **Sprachmodell konfigurieren.** Unter `/system/modell-konfiguration/` eine
   Konfiguration mit Anbieter (`openrouter` oder `infomaniak`), Modellnamen und
   Token anlegen und aktivieren. Konfigurationen sind unveränderlich: Eine
   Schlüsselrotation ist immer *anlegen plus aktivieren*, nie bearbeiten
   (ADR-0013).

4. **Transkription konfigurieren**, falls gesprochen werden soll. Unter
   `/system/transkription/` den Audio-Anbieter eintragen — er darf ein anderer
   sein als der des Sprachmodells. Zusätzlich in der `.env`
   `TRANSKRIPTION_ZERO_RETENTION=True` setzen und den Dienst neu starten; ohne
   diesen Schalter bleibt das Mikrofon bewusst gesperrt.

5. **Konten und Rollen vergeben.** Unter `/admin/` weitere Konten anlegen,
   Passwörter setzen und die Groups `Autor:in`, `Ausbilder:in` und `Forschende:r`
   zuweisen. Konten lassen sich dort bewusst nicht löschen.

Für eine reine Autor:innen-Workshop-Instanz gibt es stattdessen
`uv run python manage.py workshopdaten_anlegen` — der Seed läuft auch mit
`DEBUG=False` und richtet Konten, Kern und eine `fake`-Modell-Konfiguration ein,
also ganz ohne Zugangsdaten. Der Entwicklungs-Seed
`entwicklungsdaten_anlegen` läuft dagegen nur mit `DEBUG=True` und hat auf einer
Produktivinstanz nichts zu suchen.

## 10. Abnahme

Vor der ersten echten Erhebung einmal durchklicken:

- [ ] `https://isabell.uber.space/` zeigt die Startseite, und HTTP leitet auf
      HTTPS um.
- [ ] Die Seite ist vollständig gestylt — sonst stimmt `/static` nicht.
- [ ] Anmeldung unter `/accounts/login/` funktioniert (Formular ohne CSRF-Fehler).
- [ ] `/admin/` ist mit dem Superuser erreichbar.
- [ ] `/system/kern/` zeigt eine finale Kern-Fassung und die aktive
      Modell-Konfiguration.
- [ ] Ein Probelauf über eine Vignette liefert eine echte Modellantwort — das
      prüft Token, Basis-URL und Modellnamen in einem Zug.
- [ ] Ein hochgeladenes Vignettenbild erscheint in der Detailansicht — das prüft
      `/media`.
- [ ] Ein Teilnahme-Link einer Testerhebung führt durch Einwilligung, Instruktion
      und mindestens einen Gesprächsschritt.
- [ ] Der Datenspur-Export lädt als ZIP herunter.
- [ ] `/media/vignettenbilder/` antwortet mit 403, nicht mit einer Dateiliste.
- [ ] `/admin/` ist nicht mit einem geratenen Passwort erreichbar — alle Konten
      tragen lange, zufällige Passwörter.
- [ ] Beim Anbieter ist ein Ausgabenlimit gesetzt.

Testdaten aus der Abnahme gehören anschließend aufgeräumt: Die Teststichprobe
archivieren oder die Erhebung zurückziehen, damit die Auswertung später keine
Probeläufe mitzählt.

## 11. Backup

Uberspace sichert Dateien täglich (7 Tage) und wöchentlich (7 Wochen) nach
`/backup/daily.N/` beziehungsweise `/backup/weekly.N/`
(<https://manual.uberspace.de/basics-backup/>). Das automatische
Datenbank-Backup von Uberspace betrifft nur MySQL — diese Instanz benutzt SQLite
und ist davon **nicht** erfasst.

Eine SQLite-Datei im WAL-Modus darf nicht einfach kopiert werden, solange der
Dienst schreibt: Ein `cp` erwischt womöglich einen inkonsistenten Zwischenstand.
Der richtige Weg ist die Backup-API, die einen konsistenten Auszug zieht, ohne den
Betrieb anzuhalten:

```bash
mkdir -p ~/backups ~/bin
chmod 700 ~/backups
cat > ~/bin/failure-on-the-fly-backup <<'EOF'
#!/bin/bash
set -euo pipefail
# Dieselbe Datei wie der Dienst: DATABASE_PFAD aus der .env lesen.
QUELLE=$(sed -n 's/^DATABASE_PFAD=//p' ~/failure_on_the_fly/.env)
ZIEL=~/backups/db-$(date +%F).sqlite3
~/failure_on_the_fly/.venv/bin/python - "$QUELLE" "$ZIEL" <<'PY'
import sqlite3, sys
quelle = sqlite3.connect(sys.argv[1])
ziel = sqlite3.connect(sys.argv[2])
quelle.backup(ziel)
ziel.close()
quelle.close()
PY
chmod 600 "$ZIEL"
find ~/backups -name 'db-*.sqlite3' -mtime +30 -delete
EOF
chmod +x ~/bin/failure-on-the-fly-backup
~/bin/failure-on-the-fly-backup && ls -l ~/backups
```

Das Skript setzt voraus, dass `DATABASE_PFAD` in der `.env` steht (Schritt 5).
Jede Sicherung enthält die Anbieter-Tokens im Klartext und sämtliche
Forschungsdaten — deshalb die engen Rechte auf Verzeichnis und Datei, und deshalb
gehören die Kopien nirgendwohin, wo die Datenbank selbst nicht liegen dürfte.

Täglich per Cronjob (<https://manual.uberspace.de/daemons-cron/>), `crontab -e`:

```
MAILTO="isabell@example.org"
30 4 * * * /home/isabell/bin/failure-on-the-fly-backup
```

`MAILTO` sorgt dafür, dass ein fehlgeschlagenes Backup auffällt, statt still zu
scheitern. Die Vignettenbilder unter `~/html/media` liegen im täglichen
Uberspace-Dateibackup; wer sie zusätzlich außer Haus sichern will, zieht sie
zusammen mit `~/backups` regelmäßig per `rsync` auf einen eigenen Rechner:

```bash
rsync -avz isabell@isabell.uber.space:~/backups/ ./backups/
rsync -avz isabell@isabell.uber.space:~/html/media/ ./media/
```

Damit verlassen personenbezogene Forschungsdaten den Server. Der Zielrechner
muss im Datenschutzkonzept der Erhebung vorkommen, verschlüsselt sein und die
Löschfristen der Erhebung einhalten.

Vor jedem Update (Abschnitt 12) und vor jedem Eingriff in die Datenbank gehört ein
Backup gezogen — von Hand, nicht auf den nächtlichen Lauf vertrauend.

## 12. Update einspielen

Der Ablauf für eine neue Version:

```bash
~/bin/failure-on-the-fly-backup
cd ~/failure_on_the_fly
supervisorctl stop failure-on-the-fly
git pull
uv sync --frozen --no-dev --group deploy --python python3.14
uv run python manage.py migrate
uv run python manage.py collectstatic --noinput
uv run python manage.py check --deploy
supervisorctl start failure-on-the-fly
supervisorctl status failure-on-the-fly
```

Das ist bewusst eine kurze Auszeit, kein unterbrechungsfreies Deployment: Der
Dienst steht, solange migriert wird, damit kein alter Worker gegen ein neues
Schema schreibt. Laufende Gesprächsschritte brechen ab. Updates gehören deshalb
nicht in ein offenes Teilnahmefenster einer Erhebung. Migrationen sind
unveränderlich (ADR-0031) und laufen vorwärts; ein Rückweg führt über das Backup:
Dienst stoppen, Sicherung an den `DATABASE_PFAD` kopieren, alten Stand
auschecken, Dienst starten.

Unabhängig von neuen Funktionen sollten die Abhängigkeiten regelmäßig auf
bekannte Schwachstellen geprüft werden — auf dem Entwicklungsrechner, nicht auf
dem Server:

```bash
uvx --python 3.14 pip-audit --no-deps -r <(uv export --frozen --no-dev --group deploy --no-hashes)
```

Meldet der Lauf Treffer, ist `uv lock --upgrade` plus Testlauf der Weg, danach
ein Update wie oben.

## 13. Betrieb und Fehlersuche

**Dienst:**

```bash
supervisorctl status
supervisorctl restart failure-on-the-fly
supervisorctl tail -f failure-on-the-fly stderr
```

Die Logs von supervisord liegen unter `~/logs/`.

**Webserver-Logs** sind standardmäßig aus und lassen sich bei Bedarf einschalten
(<https://manual.uberspace.de/web-logs/>):

```bash
uberspace web log access enable
uberspace web log apache_error enable
tail -f ~/logs/webserver/access_log
```

Uberspace kürzt die IP-Adressen in diesen Logs und rotiert sie täglich; nach sieben
Tagen sind sie weg.

Häufige Stolpersteine:

| Symptom | Ursache | Abhilfe |
| --- | --- | --- |
| „Bad Request (400)“ auf jeder Seite | Hostname fehlt in `ALLOWED_HOSTS` | Namen ergänzen, Dienst neu starten |
| „CSRF verification failed“ beim Absenden eines Formulars | `CSRF_TRUSTED_ORIGINS` fehlt oder ohne `https://` | Origin mit Schema eintragen, Dienst neu starten |
| Endlose Weiterleitung | Das Frontend setzt kein `X-Forwarded-Proto` | `SECURE_SSL_REDIRECT=False` in die `.env`, Dienst neu starten |
| Seite ohne Styles | `collectstatic` nicht gelaufen oder `/static`-Backend fehlt | `collectstatic --noinput`, `uberspace web backend set /static --apache` |
| Bilder erscheinen nicht | `MEDIA_ROOT` zeigt nicht ins Docroot | `.env` prüfen, `/media`-Backend setzen |
| `uberspace web backend list` sagt `no service` | Dienst läuft nicht oder falscher Port | `supervisorctl status`, Port in `.ini` und Backend abgleichen |
| `wrong interface (::1)` | gunicorn lauscht auf localhost | `--bind 0.0.0.0:8000` |
| Gesprächsschritt bricht nach ~180 s ab | Worker-Timeout erreicht | Anbieter/Modell prüfen; das Timeout ist die Notbremse, nicht die Ursache |
| 502 nur unter Last | Alle Worker warten auf das Sprachmodell | `--workers` erhöhen, Dienst neu starten |
| Dienst startet nach `supervisorctl update` nicht | `SECRET_KEY` fehlt in der `.env` | `.env` prüfen; Django bricht ohne Schlüssel beim Import ab |

## 14. Was beim Produktivbetrieb zu bedenken ist

- **Vignettenbilder unter `/media/` sind ohne Anmeldung abrufbar**, wer ihre URL
  kennt. Die Dateinamen sind nicht erratbar, die Auslieferung aber ungeschützt.
  Bildmaterial, das das nicht verträgt, gehört nicht in eine Vignette.
- **Die Transkription gibt Audio an einen externen Auftragsverarbeiter.**
  `TRANSKRIPTION_ZERO_RETENTION=True` ist die Zusage der Betreiber:in, nicht eine
  technische Prüfung (ADR-0026). Ohne Vertrag bleibt der Schalter auf `False`; das
  Training ist über die Tastatur uneingeschränkt spielbar.
- **Der Datenspur-Export ist immer UTC**, unabhängig von `TIME_ZONE`. Eingabe und
  Anzeige in der Oberfläche — etwa der Erhebungszeitraum einer Stichprobe — laufen
  dagegen in `TIME_ZONE` (voreingestellt `Europe/Berlin`).
- **Teilnahme-Token sind ablesbar** und trennen die Forschungsdaten vom Konto
  (ADR-0006, ADR-0018). Ein geteilter Teilnahme-Link ist folglich der Zugang zu
  genau dieser Teilnahme — Links gehören nicht in öffentliche Kanäle.
- **Die Anmeldung hat keine Sperre gegen Passwort-Raten.** Weder `/accounts/login/`
  noch `/admin/` begrenzen Fehlversuche. Bis eine Sperre eingebaut ist, sind
  lange, zufällige Passwörter für alle Konten die einzige Verteidigung — auch
  für Workshop-Konten, deren Anmeldenamen (`workshop01`, …) erratbar sind.
- **Die Anwendung begrenzt keine Anbieterkosten.** Wer einen Teilnahme-Link hat,
  kann beliebig viele Gesprächsschritte und Transkriptionen auslösen. Ein
  Ausgabenlimit gehört deshalb in das Konto beim Anbieter, nicht nur in die
  Planung der Erhebung.
- **Passwort-Reset per Mail ist nicht eingerichtet.** Unter `/accounts/` liegen
  Djangos Auth-Routen einschließlich `password_reset`; ohne konfigurierten
  Mailversand läuft dieser Weg ins Leere. Passwörter setzt bis dahin die
  Administration unter `/admin/`.
- **Der Instanzzustand steckt in zwei Dingen:** der SQLite-Datei und
  `~/html/media`. Wer beides hat, kann die Instanz woanders wieder aufbauen; die
  `.env` mit ihrem `SECRET_KEY` gehört an einen dritten, sicheren Ort.
