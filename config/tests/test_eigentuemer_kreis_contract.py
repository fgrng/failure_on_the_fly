"""Vertragstest über alle eigentümer-tragenden Modelle (Spec #207).

Geprüft wird die Menge, nicht der Einzelfall: Die zu prüfenden Modelle kommen
aus derselben Modellregistrierung, aus der auch der Konto-Löschpfad seine
Bestände holt. Ein künftiges fünftes Bestandsmodell läuft damit ohne Zutun
mit.

Der Test kennt nur äußeres Verhalten — was im Kreis steht, was ein Konto
sieht, ob gelöscht wird. Auf welcher Klasse eine Methode liegt und wie sie
serialisiert, hält er bewusst nicht fest; das prüfen die Testsätze der Apps.
"""

from collections.abc import Callable

import pytest
from django.apps import apps
from django.contrib.auth.models import Group
from django.db.models import ProtectedError

from konten.eigentuemerschaft import EigentuemerKreis
from konten.models import Konto
from simulation.models import Simulationskern


def eigentuemer_tragende_modelle() -> list[type[EigentuemerKreis]]:
    """Liefert jedes registrierte Modell, das einen Eigentümer-Kreis trägt."""
    return [
        modell for modell in apps.get_models() if issubclass(modell, EigentuemerKreis)
    ]


je_bestandsmodell: Callable[[Callable[..., None]], Callable[..., None]] = (
    pytest.mark.parametrize(
        "modell",
        eigentuemer_tragende_modelle(),
        ids=lambda modell: modell.__name__,
    )
)


def test_der_simulationskern_faellt_nicht_unter_den_vertrag() -> None:
    """Der Kern gehört der Administration und trägt keinen Eigentümer-Kreis."""
    assert Simulationskern not in eigentuemer_tragende_modelle()


@pytest.mark.django_db
@je_bestandsmodell
def test_anlegen_traegt_genau_eine_eigentuemerin_ein(
    modell: type[EigentuemerKreis],
) -> None:
    """Der gemeinsame Anlege-Weg braucht keine modellspezifische Fabrik."""
    ada: Konto = Konto.objects.create_user(username="ada")

    bestand: EigentuemerKreis = modell.objects.anlegen(ada)

    assert list(bestand.eigentuemerinnen.all()) == [ada]


@pytest.mark.django_db
@je_bestandsmodell
def test_austritt_entfernt_solange_eine_eigentuemerin_bleibt(
    modell: type[EigentuemerKreis],
) -> None:
    """Wer geht, während jemand bleibt, wird ausgetragen — und das wird gemeldet."""
    ada: Konto = Konto.objects.create_user(username="ada")
    grace: Konto = Konto.objects.create_user(username="grace")
    bestand: EigentuemerKreis = modell.objects.anlegen(ada)
    bestand.eigentuemerinnen.add(grace)

    assert bestand.austreten(ada.pk)
    assert list(bestand.eigentuemerinnen.all()) == [grace]


@pytest.mark.django_db
@pytest.mark.parametrize("aktiv", [True, False], ids=["aktiv", "stillgelegt"])
@je_bestandsmodell
def test_austritt_der_letzten_eigentuemerin_aendert_nichts(
    modell: type[EigentuemerKreis],
    aktiv: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Der letzte Platz im Kreis bleibt besetzt, auch bei stillgelegtem Bestand.

    Die Invariante am Objekt ist bedingungslos (ADR-0032): Ein stillgelegter
    Bestand ist wiederbelebbar und wäre danach aktiv und eigentümerlos. Weil
    jedes Modell anders stillgelegt wird — Archiv-Kennzeichen, Status, gar
    nicht — setzt der Test allein die Antwort von `ist_aktiv()`.
    """
    monkeypatch.setattr(modell, "ist_aktiv", lambda self: aktiv)
    ada: Konto = Konto.objects.create_user(username="ada")
    bestand: EigentuemerKreis = modell.objects.anlegen(ada)

    assert not bestand.austreten(ada.pk)
    assert list(bestand.eigentuemerinnen.all()) == [ada]


@pytest.mark.django_db
@je_bestandsmodell
def test_sichtbar_sind_die_eigenen_bestaende_und_der_administration_alle(
    modell: type[EigentuemerKreis],
) -> None:
    """Eigentümerin sieht ihres, ein fremdes Konto keines, die Administration alles."""
    ada: Konto = Konto.objects.create_user(username="ada")
    mallory: Konto = Konto.objects.create_user(username="mallory")
    administratorin: Konto = Konto.objects.create_user(
        username="admin", is_superuser=True
    )
    bestand: EigentuemerKreis = modell.objects.anlegen(ada)

    assert list(modell.objects.sichtbar_fuer(ada)) == [bestand]
    assert list(modell.objects.sichtbar_fuer(mallory)) == []
    assert list(modell.objects.sichtbar_fuer(administratorin)) == [bestand]


@pytest.mark.django_db
@je_bestandsmodell
def test_kandidatenliste_nennt_die_rolle_und_die_administration(
    modell: type[EigentuemerKreis],
) -> None:
    """Rolle des Bestands und Administration sind eintragbar, Eingetragene nicht."""
    gruppe: Group = Group.objects.get(name=modell.ROLLENGRUPPE)
    eingetragene: Konto = Konto.objects.create_user(username="ada")
    eingetragene.groups.add(gruppe)
    kandidatin: Konto = Konto.objects.create_user(username="grace")
    kandidatin.groups.add(gruppe)
    administratorin: Konto = Konto.objects.create_user(
        username="admin", is_superuser=True
    )
    # Ohne Rolle und ohne Administration: darf in keiner Liste auftauchen.
    Konto.objects.create_user(username="mallory")
    bestand: EigentuemerKreis = modell.objects.anlegen(eingetragene)

    assert set(bestand.moegliche_ergaenzungen()) == {kandidatin, administratorin}


@pytest.mark.django_db
@je_bestandsmodell
def test_einzige_eigentuemerin_eines_aktiven_bestands_ist_nicht_loeschbar(
    modell: type[EigentuemerKreis],
) -> None:
    """Kein aktiver Bestand wird durch eine Kontolöschung eigentümerlos."""
    ada: Konto = Konto.objects.create_user(username="ada")
    bestand: EigentuemerKreis = modell.objects.anlegen(ada)

    assert bestand.ist_aktiv()

    with pytest.raises(ProtectedError):
        ada.delete()

    assert Konto.objects.filter(pk=ada.pk).exists()


@pytest.mark.django_db
@je_bestandsmodell
def test_eine_von_zwei_eigentuemerinnen_ist_loeschbar(
    modell: type[EigentuemerKreis],
) -> None:
    """Die Sperre hängt an der Eigentümerlosigkeit, nicht am Bestand selbst."""
    ada: Konto = Konto.objects.create_user(username="ada")
    grace: Konto = Konto.objects.create_user(username="grace")
    bestand: EigentuemerKreis = modell.objects.anlegen(ada)
    bestand.eigentuemerinnen.add(grace)

    ada.delete()

    assert list(bestand.eigentuemerinnen.all()) == [grace]
