"""Datenbankinvarianten des Simulationskerns."""

from datetime import datetime

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.db.models.deletion import ProtectedError
from django.utils import timezone

from simulation.models import KernHistorie, ModellKonfiguration, Simulationskern


def _direkt_einfuegen(**werte: object) -> Simulationskern:
    # Umgeht die öffentliche Schreibnaht ausschließlich für Constraint-Tests.

    return models.QuerySet(model=Simulationskern).bulk_create(
        [Simulationskern(**werte)],
    )[0]


@pytest.mark.django_db
def test_anlegen_legt_entwurf_mit_eifriger_historie_an() -> None:
    """Ein neuer Kern beginnt als Entwurf in der Singleton-Historie."""

    kern: Simulationskern = Simulationskern.objects.anlegen(
        system_prompt_vorlage="$fehlermuster_beschreibung",
    )

    assert kern.zustand == Simulationskern.Zustand.ENTWURF
    assert kern.historie == KernHistorie.objects.get()


@pytest.mark.django_db
def test_anlegen_laesst_keine_lebenszyklusfelder_ueberschreiben() -> None:
    """Die Anlege-Naht erzeugt unabhängig von Aufruferdaten immer einen Entwurf."""

    with pytest.raises(TypeError):
        Simulationskern.objects.anlegen(zustand=Simulationskern.Zustand.FINAL)


@pytest.mark.django_db
def test_direktes_anlegen_einer_kern_fassung_wird_abgelehnt() -> None:
    """Neue Kern-Fassungen entstehen ausschließlich über die Anlege-Naht."""

    kern: Simulationskern = Simulationskern.objects.anlegen()

    with pytest.raises(RuntimeError, match="Anlege-Naht"):
        Simulationskern.objects.create(historie=kern.historie)


@pytest.mark.django_db
def test_direktes_aktualisieren_einer_kern_fassung_wird_abgelehnt() -> None:
    """Kern-Fassungen ändern sich ausschließlich über Lebenszyklus-Methoden."""

    kern: Simulationskern = Simulationskern.objects.anlegen()

    with pytest.raises(RuntimeError, match="Lebenszyklus-Methoden"):
        Simulationskern.objects.filter(pk=kern.pk).update(system_prompt_vorlage="x")


@pytest.mark.django_db
def test_finale_fassung_kann_nicht_gesammelt_geloescht_werden() -> None:
    """Gesammeltes Löschen bewahrt finale Kern-Fassungen."""

    kern: Simulationskern = Simulationskern.objects.anlegen()
    kern.finalisieren()

    with pytest.raises(RuntimeError, match="gelöscht"):
        Simulationskern.objects.filter(pk=kern.pk).delete()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("vorlagenfeld", "platzhalter"),
    [
        ("system_prompt_vorlage", "$lehrperson_name"),
        ("user_prompt_vorlage", "$lehrperson_name"),
        ("rahmenhandlung_einleitung", "$fehlermuster_beschreibung"),
        ("rahmenhandlung_debrief", "$fehlermuster_beschreibung"),
    ],
)
def test_finalisieren_lehnt_vertragsfremde_platzhalter_je_feld_ab(
    vorlagenfeld: str,
    platzhalter: str,
) -> None:
    """Jede Vorlage wird beim Finalisieren gegen ihren Vertrag geprüft."""

    kern: Simulationskern = Simulationskern.objects.anlegen(
        **{vorlagenfeld: platzhalter},
    )

    with pytest.raises(ValidationError):
        kern.finalisieren()


@pytest.mark.django_db
def test_finalisieren_speichert_den_geprueften_entwurf() -> None:
    """Die finale Fassung enthält die Vorlagen, die beim Finalisieren geprüft wurden."""

    kern: Simulationskern = Simulationskern.objects.anlegen(
        system_prompt_vorlage="$lehrperson_name",
    )
    kern.system_prompt_vorlage = "$fehlermuster_beschreibung"

    kern.finalisieren()

    kern.refresh_from_db()
    assert kern.system_prompt_vorlage == "$fehlermuster_beschreibung"


@pytest.mark.django_db
def test_bearbeiten_einer_finalen_fassung_erzeugt_einen_neuen_entwurf() -> None:
    """Bearbeiten erhält die finale Fassung und verknüpft den neuen Entwurf."""

    finale_fassung: Simulationskern = Simulationskern.objects.anlegen(
        system_prompt_vorlage="$fehlermuster_beschreibung",
    )
    finale_fassung.finalisieren()

    entwurf: Simulationskern = finale_fassung.bearbeiten()

    finale_fassung.refresh_from_db()
    assert entwurf.zustand == Simulationskern.Zustand.ENTWURF
    assert entwurf.historie == finale_fassung.historie
    assert entwurf.vorgaengerin == finale_fassung
    assert finale_fassung.zustand == Simulationskern.Zustand.FINAL


@pytest.mark.django_db
def test_finale_fassung_ist_ausserhalb_des_lebenszyklus_unveraenderlich() -> None:
    """Nach dem Finalisieren ist nur ein neuer Entwurf veränderlich."""

    kern: Simulationskern = Simulationskern.objects.anlegen()
    kern.finalisieren()
    kern.system_prompt_vorlage = "$fehlermuster_beschreibung"

    with pytest.raises(RuntimeError, match="unveränderlich"):
        kern.save()


@pytest.mark.django_db
def test_entwurf_kann_physisch_geloescht_werden() -> None:
    """Ein Kern-Entwurf kann vollständig entfernt werden."""

    kern: Simulationskern = Simulationskern.objects.anlegen()
    kern_id: int = kern.pk

    kern.delete()

    assert not Simulationskern.objects.filter(pk=kern_id).exists()


@pytest.mark.django_db
def test_anlegen_ist_nach_loeschen_des_einzigen_entwurfs_wieder_moeglich() -> None:
    """Ein verworfener erster Entwurf blockiert die Kern-Historie nicht."""

    Simulationskern.objects.anlegen().delete()

    neuer_entwurf: Simulationskern = Simulationskern.objects.anlegen()

    assert neuer_entwurf.zustand == Simulationskern.Zustand.ENTWURF


@pytest.mark.django_db
def test_finale_fassung_kann_nicht_physisch_geloescht_werden() -> None:
    """Finale Kern-Fassungen bleiben für spätere Datenspuren erhalten."""

    kern: Simulationskern = Simulationskern.objects.anlegen()
    kern.finalisieren()

    with pytest.raises(RuntimeError, match="gelöscht"):
        kern.delete()


@pytest.mark.django_db
def test_archivierte_fassung_kann_nicht_physisch_geloescht_werden() -> None:
    """Archivierte Kern-Fassungen bleiben für spätere Datenspuren erhalten."""

    kern: Simulationskern = Simulationskern.objects.anlegen()
    kern.finalisieren()
    kern.archivieren()

    with pytest.raises(RuntimeError, match="gelöscht"):
        kern.delete()


@pytest.mark.django_db
def test_lebenszyklus_akzeptiert_keine_veraltete_fassung() -> None:
    """Jeder Übergang prüft den in der Datenbank gespeicherten Zustand."""

    veraltet: Simulationskern = Simulationskern.objects.anlegen()
    veraltet.finalisieren()
    aktuell: Simulationskern = Simulationskern.objects.get(pk=veraltet.pk)
    aktuell.archivieren()

    with pytest.raises(ValueError, match="inzwischen geändert"):
        veraltet.archivieren()


@pytest.mark.django_db
def test_finale_fassung_kann_archiviert_und_entarchiviert_werden() -> None:
    """Archivierung bewahrt den Finalisierungszeitstempel beim Rückweg."""

    kern: Simulationskern = Simulationskern.objects.anlegen()
    kern.finalisieren()
    finalisiert_am: datetime | None = kern.finalisiert_am

    kern.archivieren()

    assert kern.zustand == Simulationskern.Zustand.ARCHIVIERT
    assert kern.finalisiert_am == finalisiert_am

    kern.entarchivieren()

    assert kern.zustand == Simulationskern.Zustand.FINAL
    assert kern.finalisiert_am == finalisiert_am


@pytest.mark.django_db
def test_vertragsfremder_prompt_platzhalter_wird_abgelehnt() -> None:
    """Prompt-Vorlagen dürfen nur die vereinbarten Vignettenfelder ansprechen."""

    kern: Simulationskern = Simulationskern(system_prompt_vorlage="$lehrperson_name")

    with pytest.raises(ValidationError):
        kern.full_clean(exclude=["historie"])


@pytest.mark.django_db
def test_ungueltige_vorlagen_syntax_wird_abgelehnt() -> None:
    """Eine Vorlage muss ein gültiges string.Template sein."""

    kern: Simulationskern = Simulationskern(system_prompt_vorlage="$")

    with pytest.raises(ValidationError):
        kern.full_clean(exclude=["historie"])


@pytest.mark.django_db
def test_vertragstreue_teilmengen_und_leere_vorlagen_werden_akzeptiert() -> None:
    """Alle vier Vorlagen dürfen ihren Vertrag auch nur teilweise ausschöpfen."""

    kern: Simulationskern = Simulationskern(
        system_prompt_vorlage="$fehlermuster_beschreibung",
        rahmenhandlung_einleitung="$lehrperson_anrede $lehrperson_name",
    )

    kern.full_clean(exclude=["historie"])


@pytest.mark.django_db
def test_kern_historie_ist_ein_singleton() -> None:
    """Eine abweichende ID kann keine zweite Kern-Historie erzeugen."""

    KernHistorie.objects.create()

    with pytest.raises(IntegrityError), transaction.atomic():
        KernHistorie.objects.create(id=2)


@pytest.mark.django_db
def test_historie_hat_hoechstens_einen_entwurf() -> None:
    """Eine Kern-Historie nimmt keinen zweiten Entwurf an."""

    historie: KernHistorie = KernHistorie.objects.create()
    _direkt_einfuegen(historie=historie)

    with pytest.raises(IntegrityError), transaction.atomic():
        _direkt_einfuegen(historie=historie)


@pytest.mark.django_db
def test_entarchivieren_zu_einer_schwester_wird_verhindert() -> None:
    """Eine archivierte Schwester kann über die Lebenszyklus-Naht nicht final werden."""

    vorgaengerin: Simulationskern = Simulationskern.objects.anlegen()
    vorgaengerin.finalisieren()
    archivierte_schwester: Simulationskern = vorgaengerin.bearbeiten()
    archivierte_schwester.finalisieren()
    archivierte_schwester.archivieren()
    neue_schwester: Simulationskern = vorgaengerin.bearbeiten()
    neue_schwester.finalisieren()

    with pytest.raises(IntegrityError), transaction.atomic():
        archivierte_schwester.entarchivieren()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("zustand", "finalisiert_am"),
    [
        (Simulationskern.Zustand.ENTWURF, timezone.now()),
        (Simulationskern.Zustand.FINAL, None),
    ],
)
def test_finalisiert_am_muss_genau_dem_zustand_entsprechen(
    zustand: str,
    finalisiert_am: datetime | None,
) -> None:
    """Entwürfe und finalisierte Fassungen tragen passende Zeitstempel."""

    historie: KernHistorie = KernHistorie.objects.create()

    with pytest.raises(IntegrityError), transaction.atomic():
        _direkt_einfuegen(
            historie=historie,
            zustand=zustand,
            finalisiert_am=finalisiert_am,
        )


@pytest.mark.django_db
def test_aktivieren_bewegt_den_zeiger_ohne_zweite_aktive_konfiguration() -> None:
    """Erneutes Aktivieren ersetzt die aktive Konfiguration statt sie zu ergänzen."""

    erste: ModellKonfiguration = ModellKonfiguration.objects.create(
        sprachmodell="erstes-modell",
        parameter={},
    )
    zweite: ModellKonfiguration = ModellKonfiguration.objects.create(
        sprachmodell="zweites-modell",
        parameter={},
    )

    ModellKonfiguration.objects.aktivieren(erste)
    ModellKonfiguration.objects.aktivieren(zweite)

    assert ModellKonfiguration.objects.aktive() == zweite


@pytest.mark.django_db
def test_modell_konfiguration_ist_nach_dem_anlegen_unveraenderlich() -> None:
    """Eine angelegte Modell-Konfiguration bleibt unveränderlich."""

    konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
        sprachmodell="erstes-modell",
        parameter={"temperatur": 0.2},
    )
    konfiguration.sprachmodell = "zweites-modell"

    with pytest.raises(RuntimeError, match="append-only"):
        konfiguration.save()


@pytest.mark.django_db
def test_modell_konfiguration_kann_nicht_per_queryset_mutiert_werden() -> None:
    """Die Append-only-Garantie gilt auch für die QuerySet-Schreibroute."""

    konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
        sprachmodell="erstes-modell",
        parameter={},
    )

    with pytest.raises(RuntimeError, match="append-only"):
        ModellKonfiguration.objects.filter(pk=konfiguration.pk).update(
            sprachmodell="zweites-modell",
        )


@pytest.mark.django_db
def test_aktive_modell_konfiguration_kann_nicht_geloescht_werden() -> None:
    """Der aktive Zeiger schützt seine Konfiguration vor dem Löschen."""

    konfiguration: ModellKonfiguration = ModellKonfiguration.objects.create(
        sprachmodell="erstes-modell",
        parameter={},
    )
    ModellKonfiguration.objects.aktivieren(konfiguration)

    with pytest.raises(ProtectedError):
        konfiguration.delete()
