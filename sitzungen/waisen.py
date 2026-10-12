"""Auflösung liegen gebliebener laufender Sitzungen (Waisen)."""

from django.db.models import F, OuterRef, QuerySet, Subquery


def waisen_aufloesen(sitzungen: QuerySet) -> int:
    """Bricht je Teilnahme alle laufenden Sitzungen außer der jüngsten ab.

    Jüngste heißt nach `erstellt_am`, bei Gleichstand die höchste pk. Nimmt
    die Sitzungen als QuerySet, damit die Migration ihr historisches Modell
    übergeben kann. Liefert die Zahl der abgebrochenen Sitzungen.
    """

    laufende: QuerySet = sitzungen.filter(status="laufend")
    juengste: QuerySet = (
        laufende.filter(teilnahme=OuterRef("teilnahme"))
        .order_by(F("erstellt_am").desc(nulls_last=True), "-pk")
        .values("pk")[:1]
    )
    return laufende.exclude(pk=Subquery(juengste)).update(status="abgebrochen")
