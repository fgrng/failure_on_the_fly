# Evallauf-Durchspielprobe

Die Probe spielt den Evallauf-Dienst (#421, ADR-0047) lokal ohne Zugangsdaten durch: Start in der Oberfläche, Browser schließen, Verarbeitung im separaten Prozess, Ergebnis nach Rückkehr und erhaltene Teilstände nach einem Prozessneustart. Sie braucht drei `fake`-Konfigurationen und einen eigens angelegten finalen Testkatalog. Der Testkatalog gehört nur in die Wegwerf-Datenbank dieser Probe und ist kein Standardkatalog im Produkt; den ersten echten Katalog liefert #300.

## Vorbereitung

Eine eigene Datenbank und Sperrdatei, damit die Probe die Entwicklungsdatenbank nicht berührt. Beide Terminals brauchen dieselben Variablen:

```bash
export DATABASE_PFAD=/tmp/evalprobe/db.sqlite3 EVALLAEUFE_SPERRE=/tmp/evalprobe/evallaeufe.lock DEBUG=True
mkdir -p /tmp/evalprobe
uv run python manage.py migrate
uv run python manage.py entwicklungsdaten_anlegen
```

Dann die drei Fakes und den Testkatalog. Die Fakes lesen ihr Skript über den Lauf fort und warten je Aufruf drei Sekunden (`verzoegerung`), damit sich der Prozess mitten im Lauf neu starten lässt. Ein Gespräch macht fünf Aufrufe (zwei Antworten der Schüler:in, eine gelenkte Frage, zwei Urteile), ein Lauf mit *k* = 3 also rund 45 Sekunden. Jeder vierte Bewerter-Eintrag ist *nicht erfüllt*, damit die Übersicht beide Ausgänge zeigt.

Die Verzögerung hält die Anfragefrist ein: Erreicht sie die Frist, endet der
Aufruf mit einem Anbieterfehler und verbraucht seinen Skripteintrag. Drei
Sekunden liegen darunter. Für eine gezielte Fristprobe kann die Verzögerung
größer als die gemeinsame Frist von 90 Sekunden gewählt werden; ein Aufruf
wartet dann höchstens bis zu seiner Anfragefrist. Die Fehlversuche sind auch
bei Lehrperson und Bewerter im Gespräch aufklappbar, ebenso nach einer später
erfolgreichen Wiederholung.

```bash
uv run python manage.py shell <<'PY'
from simulation.models import Evalinput, Evalkatalog, Inputschritt, ModellKonfiguration, Verwendung

def fake(verwendung, skript):
    ModellKonfiguration.objects.aktivieren(
        ModellKonfiguration.objects.create(
            bezeichnung=f"Probe {verwendung.label}",
            sprachmodell="fake",
            parameter={"skript": skript, "skript_fortlesen": True, "verzoegerung": 3},
        ),
        verwendung,
    )

fake(Verwendung.SCHUELERIN, [{"denkspur": f"D{n}", "aeusserung": f"Antwort {n}"} for n in range(1, 13)])
fake(Verwendung.LEHRPERSON, [{"aeusserung": f"Gelenkte Frage {n}"} for n in range(1, 7)])
fake(Verwendung.BEWERTER, [{"begruendung": f"B{n}", "erfuellt": n % 4 != 0} for n in range(1, 13)])

katalog = Evalkatalog.objects.anlegen()
katalog.k = 3
katalog.lehrperson_vorlage = "Frag $schuelerin_name nach: $inputstrategie. Bisher: $verlauf"
katalog.bewerter_vorlage = "Prüfe $kriterium am Verlauf $verlauf."
katalog.save()
katalog.kriterium_anlegen("Bleibt in der Rolle")
eval_ = katalog.eval_anlegen("Probe")
eval_.kriterium_anlegen("Zeigt das Fehlermuster")
evalinput = Evalinput.anhaengen(eval_)
evalinput.schritt_anlegen(text="Wie hast du gerechnet?")
evalinput.schritt_anlegen(Inputschritt.Art.GELENKT, "Nach dem Rechenweg fragen")
katalog.finalisieren()
PY
```

## Ablauf

1. **Oberfläche starten** (Terminal 1): `uv run python manage.py runserver`, als `autor` / `entwicklung` anmelden, eine finale Vignette öffnen, „Evals ansehen“, „Evallauf starten“. Der Lauf steht auf „Wartet“. **Browser schließen.**
2. **Dienst starten** (Terminal 2): `uv run python manage.py evallaeufe_abarbeiten --intervall 2`. Das Log meldet „Hintergrundprozess gestartet“ und „Evallauf 1 gestartet.“
3. **Prozess hart beenden**, etwa nach 20 Sekunden: `pkill -9 -f evallaeufe_abarbeiten`. Kein Abschluss im Log; der Lauf steht weiter auf „Läuft“.
4. **Dienst neu starten** wie in Schritt 2. Das Log meldet zuerst „1 verwaiste Evalläufe abgebrochen.“ Im Browser zeigt die Ansicht „Abgebrochen“ mit den fertigen Gesprächen und Urteilen und „noch nicht ausgeführt“ für den Rest; das Gesamtergebnis bleibt „—“.
5. **Stopp mitten im Lauf:** einen neuen Lauf starten und den laufenden Dienst mit Strg+C (oder `kill -TERM`, wie supervisord) stoppen. Das Log nennt „Evallauf 2 abgebrochen.“ und „Hintergrundprozess beendet.“; der Lauf ist sofort „Abgebrochen“, ohne Neustart.
6. **Vollständiger Lauf:** noch einmal starten, den Dienst laufen lassen und nach knapp einer Minute zurückkehren. Die Ansicht zeigt „Fertig“, die Quoten und das Gesamtergebnis.

Während des Laufs bleibt die Oberfläche in Terminal 1 bedienbar: Der Dienst belegt keinen Web-Thread, und kein Modellaufruf hält eine Schreibsperre.

## Ergebnis (2026-10-09)

Durchgespielt auf dem Stand von #421, der Start in der Oberfläche als POST über den Django-Testclient:

| Schritt               | Beobachtet                                                                                                               |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| 2–3: hart beendet     | Lauf 1 „läuft“ mit 2 Gesprächen und 3 Urteilen                                                                           |
| 4: Neustart           | Warnung „1 verwaiste Evalläufe abgebrochen.“; Lauf 1 „abgebrochen“, 2 Gespräche und 3 Urteile erhalten                  |
| 5: SIGTERM im Lauf    | Lauf 2 „abgebrochen“ nach 19 s, Log „Evallauf 2 abgebrochen.“ und „Hintergrundprozess beendet.“                         |
| 6: vollständiger Lauf | Lauf 3 „fertig“ nach 46 s, 3 Gespräche, 6 Urteile; Ansicht: „3 von 3 · bestanden“, „2 von 3 · nicht bestanden“, Gesamtergebnis „Nicht bestanden“ |

Nicht geprüft: der Betrieb unter supervisord auf Uberspace selbst; die Dienstdefinition steht in `docs/DEPLOYMENT.md`, Abschnitt 7.

### Ergänzende Browserprüfung der Fehlerdetails (2026-10-09)

Mit Chromium und einer eigenen Wegwerf-Datenbank geprüft: Anmeldung als
Autor:in, Start per POST in der Oberfläche, Schließen der Seite, Verarbeitung
durch einen separat gestarteten Einmal-Prozess und Rückkehr zum Ergebnis.
Lehrperson und Bewerter lieferten in der ersten Wiederholung nach Fehlversuchen
gültige Ausgaben; in der zweiten scheiterte die Lehrperson in Schritt 2.

Bei 1440 Pixeln stehen die Spalten nebeneinander, bei 390 Pixeln untereinander.
Die zunächst eingeklappten Fehlversuche lassen sich mit der Tastatur öffnen.
Auch eine lange Rohantwort mit einem `<script>`-Tag erscheint ausschließlich
als Text und verursacht keinen horizontalen Überlauf. Der endgültige
Lehrpersonenfehler nennt Schritt 2 und erhält den vorherigen Wechsel, ohne eine
gescheiterte Schüler:innen-Antwort vorzutäuschen. Es gab keine JavaScript-Fehler.
Diese Zusatzprobe prüft die neue Fehleranzeige; die Prozessneustartprobe oben
bleibt davon getrennt.
