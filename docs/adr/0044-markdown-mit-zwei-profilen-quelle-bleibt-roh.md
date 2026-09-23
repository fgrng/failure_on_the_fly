---
status: accepted
---

# Markdown mit zwei Profilen, Quelle bleibt roh

Acht Textfelder, die Teilnehmer:innen zu sehen bekommen, werden als basales Markdown gelesen und serverseitig zu HTML gerendert. Das Rendermodul `texte/markdown.py` hat genau zwei Einstiegspunkte, `informationstext(quelle)` und `szenentext(quelle)`, und gleichnamige Template-Filter (`{% load texte %}`). Es liegt in der eigenen App `texte`, die nichts kennt und von allen Apps genutzt werden darf; sie ist ein Blatt wie `fragebogen_items` und keine Naht im Sinne von ADR-0016, denn es gibt nur eine Implementierung.

Der **Informationstext** gilt für Instruktions-, Einwilligungs- und Abschlusstext einer Erhebung und erlaubt Links mit den Schemata `https:`, `http:` und `mailto:`; sie öffnen in neuem Tab (`target="_blank"`, `rel="noopener noreferrer"`) mit sichtbarem Extern-Hinweis und einem Text für Screenreader. Der **Szenentext** gilt für Lernauftrag, Arbeitsheft und Rahmenhandlung und kennt keine Links: Aus der Szene heraus soll niemand die Plattform verlassen. Beide teilen Absätze, erhaltene Zeilenumbrüche (`<br>`), Fett, Kursiv, `#`–`###` als `h3`–`h5` unter Seiten- und Abschnittskopf, Listen und Zitatblock. Alles andere — rohes HTML, Bilder, Tabellen, Codeblöcke, nackte URLs, fremde Link-Schemata — erscheint wörtlich.

**Die Quelle bleibt roh.** Gespeichert wird der Markdown-Text, wie er eingegeben wurde. Das Sprachmodell erhält ihn unverändert, der Datenspur-Export (ADR-0029) ebenso; gerendert wird erst im Template.

## Considered Options

- **`markdown-it-py` mit abgeschalteten Regeln und ohne Sanitizer** — gewählt. Der CommonMark-Parser escaped rohes HTML ab Werk; was nicht gewünscht ist, wird als Regel abgeschaltet. Sicherheit entsteht dadurch, dass unerwünschtes HTML gar nicht erst erzeugt wird, statt dass ein zweites Werkzeug es nachträglich entfernt.
- **Python-Markdown plus Sanitizer (bleach/nh3)** — verworfen. Zwei Werkzeuge, deren Umfänge sich decken müssen; was der Sanitizer entfernt, sähen Forschende in der Vorschau nicht als Text, sondern gar nicht.
- **Ein Profil für alle acht Felder** — verworfen. Links in der Szene führen aus der Simulation heraus, Links in der Einwilligung sind nötig (Datenschutzerklärung).
- **Rendern beim Speichern, HTML in der Datenbank** — verworfen. Prompt und Export bräuchten dann die Quelle zusätzlich, und eine Änderung am Umfang verlangte eine Migration aller Texte.
- **Überschriften so ausgeben, wie sie geschrieben sind** — verworfen. Ein `#` als `h1` bräche die Gliederung der Seite; Forschende sollen die Seitengliederung nicht kennen müssen.

## Consequences

- Wer Schülernotation mit `*`, `_`, führendem `-` oder `1.` wörtlich zeigen will, escaped sie mit Backslash.
- In der Rahmenhandlung werden die Platzhalterwerte der Vignette vor dem Einsetzen (ADR-0020) mit Backslash vor jedem ASCII-Satzzeichen escaped (`texte.markdown.woertlich`); erst der gefüllte Text wird gerendert. So wirkt nur das Markdown des Kerns.
- Leere Quelle ergibt leeres HTML; Platzhalter wie „—" bleiben Sache des Templates.
- Gerenderte Texte stehen in `<div class="markdown-text">` mit eigenem Stylesheet (`static/css/markdown-text.css`), das sich per doppeltem Klassenselektor gegen Seitenregeln wie `.page-field h3` abschirmt.
- `&`-Entitäten werden nicht aufgelöst, sondern erscheinen wörtlich.
- Die Editor-Vorschau holt das Fragment von `texte:vorschau` (POST mit `quelle` und `profil`), statt in JavaScript zu rendern. Für die Rollenprüfung (Autor:in, Forschende:r, Administration) kennt `texte` dafür `konten`, die Infrastruktur aller Apps; Domänen-Apps kennt es weiterhin nicht.
