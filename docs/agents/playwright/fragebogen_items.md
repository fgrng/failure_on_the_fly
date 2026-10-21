# Fragebogen-Items

Fragebogen-Items anlegen, bearbeiten, finalisieren, neue Fassung, archivieren; Eintragen aus `docs/erhebung/`. Setzt [README.md](README.md) voraus (Sessions, Anmelden, Formulare füllen, Produktion). Wie Items in eine Erhebung kommen, steht in [erhebungen.md](erhebungen.md).

## Zugang

Bereich **Forschung → Fragebogen-Items** in der Navigation, `/fragebogen-items/` (Prod <https://onthefly.fgrng.de/fragebogen-items/>, Dev <http://127.0.0.1:8000/fragebogen-items/>). Nur Forschende und Administrator:innen; jedes andere Konto bekommt 403 (auf Dev: `studi`).

Die Bibliothek zeigt nur Items, in deren Eigentümer-Kreis das Konto steht; Administrator:innen sehen alle. Eine fremde Fassung per URL ergibt 404 (aus dem Code).

## Ein Item

Ein Item hat genau zwei Felder, beide im selben Formular:

| Feld | `name` | Werte |
|---|---|---|
| Typ | `typ` (Select) | `freitext` (Freitext), `likert` (Likert-Skala) |
| Wortlaut | `wortlaut` (Textarea) | Pflicht; Leerraum am Anfang und Ende wird abgeschnitten |

Was die UI nicht verrät:

- Die Likert-Skala ist global und fest: sechs Stufen von 1 = „Stimme gar nicht zu" bis 6 = „Stimme voll zu", ohne Mitte. Es gibt keine Antwortoptionen, keine Stufenzahl und keine Pol-Beschriftung pro Item; die Detailseite zeigt die Pole nur an.
- Es gibt kein Feld für Namen, Konstrukt, Skala oder Umpolung. Die Liste und die Überschrift der Detailseite zeigen den Wortlaut (der Historienname ist in der UI nicht setzbar). Wer Konstrukt oder Umpolung festhalten will, kann es nicht in der App tun.
- Der Wortlaut ist kein Markdown: keine Vorschau, und die Detailseite zeigt Zeilenumbrüche nicht an (gespeichert bleiben sie).

## Seiten und Aktionen

`<pk>` ist die ID einer **Fassung**, nicht der Historie. Alle Aktionen außer Anlegen und Bearbeiten sind Knöpfe auf der Detailseite (`POST`; ein `GET` auf ihre URL ergibt 405). Keiner der Knöpfe fragt nach, auch **Entwurf löschen** nicht.

| Seite / Aktion | URL (unter `/fragebogen-items`) | Zustand | Ergebnis |
|---|---|---|---|
| Liste | `/` | | je Historie eine Zeile |
| Anlegen | `/anlegen/` | | neuer Entwurf mit neuer Historie, Kreis = anlegendes Konto, weiter auf die Detailseite |
| Detail | `/<pk>/` | alle | Fassung, Eigentümer:innen, bei Likert die Pole |
| Bearbeiten | `/<pk>/bearbeiten/` | nur Entwurf, sonst 404 | Knopf **Änderungen speichern** |
| **Finalisieren** | `/<pk>/finalisieren/` | Entwurf | final, unveränderlich, einbindbar |
| **Entwurf löschen** | `/<pk>/loeschen/` | Entwurf | physisch gelöscht, weiter auf die Liste |
| **Neue Fassung** | `/<pk>/neue-fassung/` | final | Folgeentwurf mit kopiertem Typ und Wortlaut |
| **Archivieren** | `/<pk>/archivieren/` | final | archiviert, nicht mehr einbindbar |
| **Entarchivieren** | `/<pk>/entarchivieren/` | archiviert | wieder final |
| Eigentümer:in hinzufügen / entfernen | `/<pk>/eigentuemerinnen/hinzufuegen/`, `/<pk>/eigentuemerinnen/<konto_pk>/entfernen/` | alle | ändert den Kreis der ganzen Historie |

## Lebenszyklus

Entwurf → final → archiviert, je Fassung. Was dabei gilt und die UI nicht sagt:

- **Finalisieren ist unumkehrbar**: Eine finale Fassung ist nie wieder bearbeitbar; Korrekturen gehen nur über **Neue Fassung** und ergeben eine neue Fassung mit neuem `<pk>`. Vor dem Finalisieren auf Prod den Schritt als unumkehrbar nennen.
- **Entwurf löschen ist unumkehrbar** und hat keine Rückfrage. War es der einzige Entwurf einer Historie ohne weitere Fassung, verschwindet das Item ganz.
- Archivieren ist umkehrbar (**Entarchivieren**), außer in einem Fall: Hat die Vorgängerin inzwischen eine andere nicht archivierte Nachfolgerin, fehlt der Knopf (ein `POST` ergibt 404).
- **Neue Fassung** archiviert die Vorgängerin nicht. Nach dem Finalisieren der Nachfolgerin sind beide Fassungen final und beide einbindbar; die alte archiviert der Agent selbst, wenn sie nicht mehr angeboten werden soll.
- Je Historie gibt es höchstens einen Entwurf. Hat eine finale Fassung schon eine nicht archivierte Nachfolgerin, zeigt sie keinen Knopf **Neue Fassung**; ein `POST` führt zum offenen Entwurf oder, wenn es keinen gibt, mit der Meldung „Diese Fassung hat bereits eine nicht archivierte Nachfolgerin." zurück auf die Detailseite.
- Archivieren einer finalen Fassung lässt einen offenen Folgeentwurf bestehen.
- Im Folgeentwurf erscheint beim Wechsel des Typs der Hinweis „Typwechsel: Antworten der Vorgängerin bleiben beim bisherigen Typ."; gespeichert wird trotzdem.
- Eine archivierte Historie als Ganzes (ADR-0040) gibt es in der UI nicht; archiviert wird nur je Fassung.

## Fassungen finden

Die Liste zeigt je Historie nur die **neueste Fassung** (höchster `<pk>`) mit deren Zustand. Läuft ein Folgeentwurf, steht dort „Entwurf", obwohl die Vorgängerin final ist; ist die neueste Fassung archiviert, steht dort „Archiviert", auch wenn eine ältere final ist (aus dem Code, nicht durchgespielt). Die Detailseite verlinkt weder Vorgängerin noch Nachfolgerin: Den `<pk>` der finalen Fassung notiert der Agent, bevor er **Neue Fassung** drückt, und erreicht sie danach nur per URL.

## Eigentümer:innen

Abschnitt **02 Eigentümer:innen** auf der Detailseite: Auswahl `select[name=konto]` mit Konten der Rolle Forschende:r und Administrator:innen außerhalb des Kreises, Knopf **Hinzufügen**. **Entfernen** und **Mich entfernen** erscheinen nur, solange der Kreis mehr als ein Konto hat; nach **Mich entfernen** landet man auf der Liste und sieht das Item nicht mehr. Auf Dev gibt es außer `autor` kein Forschungskonto, Hinzufügen und Entfernen sind dort nicht durchspielbar (unbelegt).

## Verwendung in Erhebungen

Eine Erhebung bindet nur **finale** Fassungen aus dem eigenen Eigentümer-Kreis ein, je Andockpunkt (nach jeder Vignettensitzung oder am Ende), und pinnt die Fassung: Eine neue Fassung ändert eine bestehende Erhebung nicht. Einbinden, Reihenfolge und Andockpunkte beschreibt [erhebungen.md](erhebungen.md). Ob Archivieren einer eingebundenen Fassung die Erhebung berührt, ist nicht durchgespielt.

## Eintragen aus `docs/erhebung/`

Quelle der Itemtexte ist `docs/erhebung/2026-09-23-erhebungstexte.md`, Abschnitte «Fragebogen zu den einzelnen Vignetten» (Andockpunkt nach jeder Vignettensitzung) und «Fragebogen zur Simulationsumgebung» (am Ende). Jeder Spiegelstrich unter einer `####`-Überschrift ist ein Item: Likert, wo der Abschnitt die 6-stufige Skala nennt; Freitext, wo der Spiegelstrich auf `[Textfeld]` endet.

- `[Textfeld]` gehört nicht in den Wortlaut.
- `(−)` am Ende markiert ein umgepoltes Item und gehört nicht in den Wortlaut; die App kennt keine Umpolung, der Agent meldet die betroffenen Items dem User.
- Ob ein Item schon existiert, zeigt die Liste über den Wortlaut; vor dem Anlegen dort suchen, statt ein Duplikat anzulegen.

Ablauf je Item:

1. Anlegen: `goto …/fragebogen-items/anlegen/`, `select "[name=typ]" likert` (oder `freitext`), `fill "[name=wortlaut]" "…"`, Knopf **Fragebogen-Item anlegen**. Die neue `<pk>` steht danach in `location.pathname`.
2. Zurücklesen: `goto …/fragebogen-items/<pk>/bearbeiten/`, dann `--raw eval "JSON.stringify([document.querySelector('[name=typ]').value, document.querySelector('[name=wortlaut]').value])"` und mit der Quelle vergleichen (typografische Anführungszeichen, Doppelpunkt in „Schüler:in").
3. Abweichung: im selben Formular korrigieren, **Änderungen speichern**, erneut zurücklesen.
4. **Finalisieren** nur nach Freigabe durch den User, auf Prod je Item als unumkehrbaren Schritt genannt. Erst dann ist das Item für Erhebungen sichtbar.

Die Fassung im Repo bleibt die Quelle: Ändert sich ein Itemtext dort, bekommt das Item in der App eine **Neue Fassung**, nicht ein neues Item.
