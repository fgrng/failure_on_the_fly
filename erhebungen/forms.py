"""Das Formular, über das Teilnehmende einen Itemblock beantworten."""

from typing import Any

from django import forms
from django.db import transaction

from fragebogen_items.models import FragebogenItem, LikertSkalenpol

from .models import ItemAntwort, Itemblock


def _feldname(antwort: ItemAntwort) -> str:
    # Trägt die Antwortzeile im Feldnamen; gelesen wird er nur hier.

    return f"item_{antwort.pk}"


def _likert_wahlmoeglichkeiten() -> list[tuple[int, str]]:
    # Gespeichert wird die Stufe, dargeboten der global festgelegte Pol.

    return [(LikertSkalenpol.stufe_fuer(pol), pol.label) for pol in LikertSkalenpol]


def _feld(antwort: ItemAntwort) -> forms.Field:
    # Wählt das Feld nach dem Typ der gepinnten Item-Fassung.

    wortlaut: str = antwort.erhebungsitem.item.wortlaut
    if antwort.erhebungsitem.item.typ == FragebogenItem.Typ.LIKERT:
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


class ItemblockFormular(forms.Form):
    """Nimmt die freiwilligen Antworten eines vorgelegten Blocks entgegen.

    Jede Antwortzeile des Blocks bekommt ein Feld; keines ist Pflicht, weil
    Fragebogen-Items freiwillig sind. Ein abgeschickter Block trägt immer alle
    Felder — ein fehlendes Feld ist eine leere Antwort, keine ausgelassene.
    """

    def __init__(self, block: Itemblock, *args: Any, **kwargs: Any) -> None:
        """Baut die Felder aus den Antwortzeilen des vorgelegten Blocks."""

        super().__init__(*args, **kwargs)
        self.antworten: list[ItemAntwort] = block.antwortzeilen()
        for antwort in self.antworten:
            self.fields[_feldname(antwort)] = _feld(antwort)

    def speichern(self) -> None:
        """Schreibt die Antwortzeilen des Blocks in einem Rutsch."""

        with transaction.atomic():
            for antwort in self.antworten:
                wert: object = self.cleaned_data[_feldname(antwort)]
                if antwort.erhebungsitem.item.typ == FragebogenItem.Typ.LIKERT:
                    antwort.likert_stufe = wert
                else:
                    antwort.freitext = wert or None
                antwort.save()
