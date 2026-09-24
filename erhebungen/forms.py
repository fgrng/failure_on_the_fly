"""Das Formular, über das Teilnehmende einen Itemblock beantworten."""

from typing import Any

from django import forms
from django.db import transaction

from fragebogen_items.models import FragebogenItem, LikertSkalenpol

from .models import ItemAntwort, Itemblock


def _feldname(antwort: ItemAntwort) -> str:
    # Bindet ein Feld an das Item der Antwortzeile, das im Block nur einmal steht.

    return f"item_{antwort.erhebungsitem_id}"


def _ist_likert(antwort: ItemAntwort) -> bool:
    # Entscheidet an der gepinnten Item-Fassung, nicht am Abgeschickten.

    return antwort.erhebungsitem.item.typ == FragebogenItem.Typ.LIKERT


def _likert_wahlmoeglichkeiten() -> list[tuple[int, str]]:
    # Gespeichert wird die Stufe, dargeboten der global festgelegte Pol.

    return [(LikertSkalenpol.stufe_fuer(pol), pol.label) for pol in LikertSkalenpol]


def _feld(antwort: ItemAntwort) -> forms.Field:
    # Baut das Feld zu einer Antwortzeile samt ihrem bisherigen Stand.

    wortlaut: str = antwort.erhebungsitem.item.wortlaut
    if _ist_likert(antwort):
        return forms.TypedChoiceField(
            label=wortlaut,
            choices=_likert_wahlmoeglichkeiten(),
            coerce=int,
            empty_value=None,
            widget=forms.RadioSelect,
            required=False,
            initial=antwort.likert_stufe,
        )
    return forms.CharField(
        label=wortlaut,
        widget=forms.Textarea,
        required=False,
        initial=antwort.freitext,
    )


def _leere_antwortzeilen(block: Itemblock) -> list[ItemAntwort]:
    # Stellt die Items des Blocks als ungespeicherte, leere Antwortzeilen dar.

    erhebung = block.erhebungsbindung.stichprobe.erhebung
    erhebungsitems = (
        erhebung.itemzugehoerigkeiten.filter(andockpunkt=block.andockpunkt)
        .select_related("item")
        .order_by("position")
    )
    return [
        ItemAntwort(itemblock=block, erhebungsitem=erhebungsitem)
        for erhebungsitem in erhebungsitems
    ]


class ItemblockFormular(forms.Form):
    """Nimmt die freiwilligen Antworten eines vorgelegten Blocks entgegen.

    Jede Antwortzeile des Blocks bekommt ein Feld; keines ist Pflicht, weil
    Fragebogen-Items freiwillig sind. Ein abgeschickter Block trägt immer alle
    Felder — ein fehlendes Feld ist eine leere Antwort, keine ausgelassene.
    """

    def __init__(self, block: Itemblock, *args: Any, **kwargs: Any) -> None:
        """Baut die Felder aus den Antwortzeilen des vorgelegten Blocks."""

        super().__init__(*args, **kwargs)
        self.speichert: bool = not block.erhebungsbindung.teilnahme.ist_fluechtig
        self.antworten: list[ItemAntwort] = (
            block.antwortzeilen() if self.speichert else _leere_antwortzeilen(block)
        )
        for antwort in self.antworten:
            self.fields[_feldname(antwort)] = _feld(antwort)

    def speichern(self) -> None:
        """Schreibt die Antwortzeilen des Blocks in einem Rutsch.

        Eine flüchtige Teilnahme hat keine Antwortzeilen; ihre Antworten werden
        verworfen.
        """

        if not self.speichert:
            return
        with transaction.atomic():
            for antwort in self.antworten:
                wert: int | str | None = self.cleaned_data[_feldname(antwort)]
                if _ist_likert(antwort):
                    antwort.likert_stufe = wert
                else:
                    antwort.freitext = wert or None
                antwort.save()
