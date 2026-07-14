"""Formulare für die Ausbilder-UI."""

from django.forms import ModelForm

from .models import Training


class TrainingForm(ModelForm):
    """Erfasst den Namen eines neuen Trainings."""

    class Meta:
        """Beschränkt das Formular auf den kuratierbaren Namen."""

        model = Training
        fields = ["name"]
