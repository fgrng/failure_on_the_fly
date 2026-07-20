"""Formulare des Fragebogen-Item-Editors."""

from django import forms

from .models import FragebogenItem


class FragebogenItemForm(forms.Form):
    """Erfasst die beim Anlegen einer Item-Fassung erlaubten Felder."""

    typ = forms.ChoiceField(choices=FragebogenItem.Typ.choices, label="Typ")
    wortlaut = forms.CharField(widget=forms.Textarea, label="Wortlaut")
