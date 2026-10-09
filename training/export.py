"""Schreibt den Trainingsexport: die Fremdeinsicht eines Trainings als Markdown.

Der Export ist pseudonym, nicht anonym (ADR-0049): Ordner tragen je Export neu
gezogene Kennzeichen statt Kontodaten, Freitext bleibt ungeschwärzt. Er ist
keine Datenspur und unterliegt nicht dem Exportkontrakt aus ADR-0029.
"""

import secrets
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from django.db.models import Prefetch
from django.utils import timezone
from django.utils.text import slugify

from sitzungen.models import Diagnose, Gespraechsschritt, Sitzung

from .abschriften import GESPIELTE_FOLGE
from .models import Training


def trainingsexport_zip(training: Training) -> bytes:
    """Liefert die einsehbaren Sitzungen eines Trainings als ZIP-Archiv.

    Je Person ein Ordner mit einer Markdown-Datei je abgeschlossener Sitzung;
    freigegebene Abschriften liegen darin als Unterordner mit Erhebungsnamen.
    Wer das Training sehen darf, prüft der Aufrufer.
    """

    # Die Konten dienen nur der Gruppierung; ins Archiv geht keins davon.
    konto_je_teilnahme: dict[int, int] = dict(
        training.trainingsbindung_set.values_list("teilnahme_id", "konto_id")
    )
    unterordner_je_teilnahme: dict[int, str] = {}
    for abschrift in training.freigegebene_abschriften.order_by("importiert_am", "pk"):
        konto_je_teilnahme[abschrift.teilnahme_id] = abschrift.konto_id
        unterordner_je_teilnahme[abschrift.teilnahme_id] = _freier_name(
            _dateiname(abschrift.erhebungsname, "abschrift"),
            {
                name
                for teilnahme_id, name in unterordner_je_teilnahme.items()
                if konto_je_teilnahme[teilnahme_id] == abschrift.konto_id
            },
        )

    kennzeichen_je_konto: dict[int, str] = {}
    dateien: dict[str, str] = {}
    sitzungen_je_ordner: dict[str, int] = {}
    for sitzung in (
        Sitzung.objects.fremd_einsehbar(Training.objects.filter(pk=training.pk))
        .select_related("vignette__historie", "diagnose")
        .prefetch_related(
            Prefetch(
                "gespraechsschritt_set",
                queryset=Gespraechsschritt.objects.order_by("reihenfolge"),
            )
        )
        .order_by(*GESPIELTE_FOLGE)
    ):
        konto_id: int = konto_je_teilnahme[sitzung.teilnahme_id]
        if konto_id not in kennzeichen_je_konto:
            kennzeichen_je_konto[konto_id] = _kennzeichen(
                set(kennzeichen_je_konto.values())
            )
        ordner: str = "/".join(
            teil
            for teil in (
                kennzeichen_je_konto[konto_id],
                unterordner_je_teilnahme.get(sitzung.teilnahme_id),
            )
            if teil
        )
        sitzungen_je_ordner[ordner] = sitzungen_je_ordner.get(ordner, 0) + 1
        dateiname: str = (
            f"{ordner}/{sitzungen_je_ordner[ordner]:02d}-"
            f"{_dateiname(sitzung.vignette.anzeigename, 'sitzung')}.md"
        )
        dateien[dateiname] = _markdown(sitzung)

    puffer: BytesIO = BytesIO()
    with ZipFile(puffer, "w", compression=ZIP_DEFLATED) as archiv:
        # Nach Kennzeichen sortiert verrät die Reihenfolge keine Namen.
        for name in sorted(dateien):
            archiv.writestr(name, dateien[name])
    return puffer.getvalue()


def _kennzeichen(vergeben: set[str]) -> str:
    """Zieht ein zufälliges, in diesem Export noch freies Kennzeichen."""

    while True:
        kennzeichen: str = f"teilnehmer-{secrets.token_hex(4)}"
        if kennzeichen not in vergeben:
            return kennzeichen


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
