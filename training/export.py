"""Schreibt den Trainingsexport: die Fremdeinsicht eines Trainings als Markdown.

Der Export ist pseudonym, nicht anonym (ADR-0049): Ordner tragen die
Teilnahmekennung statt Kontodaten, Freitext bleibt ungeschwärzt. Er ist
keine Datenspur und unterliegt nicht dem Exportkontrakt aus ADR-0029.
"""

from collections import Counter
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from django.db.models import Prefetch
from django.utils import timezone
from django.utils.text import slugify

from sitzungen.models import Diagnose, Gespraechsschritt, Sitzung

from .models import Abschrift, Training


def trainingsexport_zip(training: Training) -> bytes:
    """Liefert die einsehbaren Sitzungen eines Trainings als ZIP-Archiv.

    Je Person ein Ordner mit einer Markdown-Datei je abgeschlossener Sitzung;
    freigegebene Abschriften liegen darin als Unterordner mit Erhebungsnamen.
    Wer das Training sehen darf, prüft der Aufrufer. Beispiel::

        teilnehmer-3f9a01c2/01-brüche-addieren.md
        teilnehmer-3f9a01c2/studie-bruchrechnung/01-brüche-kürzen.md
        teilnehmer-3f9a01c2/studie-bruchrechnung-2/01-brüche-kürzen.md
        teilnehmer-a07c5e1b/01-brüche-addieren.md
    """

    sitzungen: list[Sitzung] = list(
        Sitzung.objects.fremd_einsehbar(Training.objects.filter(pk=training.pk))
        .select_related("vignette__historie", "diagnose")
        .prefetch_related(
            Prefetch(
                "gespraechsschritt_set",
                queryset=Gespraechsschritt.objects.order_by("reihenfolge"),
            )
        )
        .in_gespielter_folge()
    )
    ordner_je_teilnahme: dict[int, str] = _ordner_je_teilnahme(
        training, {sitzung.teilnahme_id for sitzung in sitzungen}
    )

    dateien: dict[str, str] = {}
    sitzungen_je_ordner: Counter[str] = Counter()
    for sitzung in sitzungen:
        ordner: str = ordner_je_teilnahme[sitzung.teilnahme_id]
        sitzungen_je_ordner[ordner] += 1
        dateiname: str = (
            f"{ordner}/{sitzungen_je_ordner[ordner]:02d}-"
            f"{_dateiname(sitzung.vignette.anzeigename, 'sitzung')}.md"
        )
        dateien[dateiname] = _markdown(sitzung)

    puffer: BytesIO = BytesIO()
    with ZipFile(puffer, "w", compression=ZIP_DEFLATED) as archiv:
        # Nach Kennung sortiert verrät die Reihenfolge keine Namen.
        for name in sorted(dateien):
            archiv.writestr(name, dateien[name])
    return puffer.getvalue()


def _ordner_je_teilnahme(training: Training, teilnahmen: set[int]) -> dict[int, str]:
    """Ordnet jeder Teilnahme ihren Ordner im Archiv zu.

    Je Konto heißt der Ordner nach der Teilnahmekennung seiner
    Trainingsbindung; gleiche Kennungen werden durchgezählt. Die Konten dienen
    nur der Gruppierung; ins Archiv geht keins davon. Nur Abschriften mit
    einsehbaren Sitzungen belegen einen Unterordnernamen.
    """

    ordner_je_konto: dict[int, str] = {}
    ordner: dict[int, str] = {}
    for teilnahme_id, konto_id, kennung in training.trainingsbindung_set.order_by(
        "pk"
    ).values_list("teilnahme_id", "konto_id", "teilnahme__kennung"):
        ordner_je_konto[konto_id] = _freier_name(
            f"teilnehmer-{kennung}", set(ordner_je_konto.values())
        )
        ordner[teilnahme_id] = ordner_je_konto[konto_id]

    abschriften: list[Abschrift] = list(
        training.freigegebene_abschriften.filter(teilnahme_id__in=teilnahmen).order_by(
            "importiert_am", "pk"
        )
    )
    # Freigeben setzt eine Trainingsbindung voraus, das Konto hat also einen Ordner.
    for abschrift in abschriften:
        ordner[abschrift.teilnahme_id] = _freier_name(
            f"{ordner_je_konto[abschrift.konto_id]}/"
            f"{_dateiname(abschrift.erhebungsname, 'abschrift')}",
            set(ordner.values()),
        )
    return ordner


def _dateiname(text: str, ersatz: str) -> str:
    """Macht aus einem Namen ein lesbares Pfadsegment."""

    return slugify(text, allow_unicode=True) or ersatz


def _freier_name(name: str, vergeben: set[str]) -> str:
    """Hängt eine Zählung an, bis der Name im Ordner frei ist."""

    kandidat: str = name
    zaehler: int = 2
    while kandidat in vergeben:
        kandidat = f"{name}-{zaehler}"
        zaehler += 1
    return kandidat


def _markdown(sitzung: Sitzung) -> str:
    """Schreibt eine Sitzung so, wie die Fremdeinsicht sie zeigt, ohne Denkspur."""

    zeilen: list[str] = [
        f"# {sitzung.vignette.anzeigename}",
        "",
        f"- Ausgang: {sitzung.get_status_display()}",
    ]
    if sitzung.erstellt_am is not None:
        zeilen.append(f"- Datum: {timezone.localtime(sitzung.erstellt_am):%d.%m.%Y}")
    zeilen += ["", "## Transkript", ""]
    for schritt in sitzung.gespraechsschritt_set.all():
        zeilen += [
            f"**Eingabe:** {schritt.eingabe}",
            "",
            f"**Äußerung:** {schritt.aeusserung or '(keine Antwort)'}",
            "",
        ]
    # Eine Sitzung ohne Diagnose hat die Rückwärts-1:1 nicht.
    diagnose: Diagnose | None = getattr(sitzung, "diagnose", None)
    zeilen += [
        "## Diagnose",
        "",
        diagnose.text if diagnose is not None else "(keine Diagnose)",
        "",
    ]
    return "\n".join(zeilen)
