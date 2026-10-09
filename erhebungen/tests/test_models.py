"""ORM-Tests für Erhebungen und Stichproben."""

from datetime import datetime, timedelta
import re
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.db.models.deletion import ProtectedError
from django.utils import timezone

from config.tests.aufbau import (
    aktive_modell_konfiguration,
    finale_vignette,
    finaler_kern,
    vignetten_entwurf,
)
from erhebungen.models import (
    Erhebung,
    Erhebungsbindung,
    Erhebungsitem,
    Erhebungsvignette,
    ItemAntwort,
    Itemblock,
    Stichprobe,
)
from konten.models import Konto
from fragebogen_items.models import FragebogenItem
from simulation.models import Anbieter, ModellKonfiguration, Verwendung
from sitzungen.models import Sitzung, Teilnahme
from vignetten.models import Vignette


def _erhebungsbindung_anlegen(konto: Konto, teilnahme: Teilnahme) -> Erhebungsbindung:
    """Erstellt eine Erhebungsbindung mit der kleinsten gültigen Umgebung."""

    erhebung: Erhebung = Erhebung.objects.anlegen(konto, name="Brüche")
    stichprobe: Stichprobe = Stichprobe.objects.create(
        erhebung=erhebung,
        beginn=timezone.now(),
        ende=timezone.now(),
    )
    return Erhebungsbindung.objects.create(
        stichprobe=stichprobe,
        teilnahme=teilnahme,
        token="2345-6789",
    )


@pytest.mark.django_db
def test_erhebung_haelt_finale_vignetten_in_fester_reihenfolge() -> None:
    """Eine feste Erhebung bewahrt ihre finalen Vignetten eindeutig geordnet."""

    konto: Konto = Konto.objects.create_user(username="ada")
    erhebung: Erhebung = Erhebung.objects.anlegen(konto, name="Brüche")
    erste: Vignette = finale_vignette(konto)
    zweite: Vignette = finale_vignette(konto)

    Erhebungsvignette.objects.create(erhebung=erhebung, vignette=zweite, position=2)
    Erhebungsvignette.objects.create(erhebung=erhebung, vignette=erste, position=1)

    assert list(
        erhebung.vignettenzugehoerigkeiten.values_list("vignette_id", flat=True)
    ) == [erste.pk, zweite.pk]


@pytest.mark.django_db
def test_erhebungsvignette_lehnt_entwurf_auch_per_bulk_insert_ab() -> None:
    """Die Mitgliedschaft schützt die Finale-Invariante auch vor Bulk-Inserts."""

    ada: Konto = Konto.objects.create_user(username="ada")
    erhebung: Erhebung = Erhebung.objects.anlegen(ada, name="Brüche")
    entwurf: Vignette = vignetten_entwurf(ada)

    with pytest.raises(IntegrityError, match="finale"), transaction.atomic():
        Erhebungsvignette.objects.bulk_create(
            [Erhebungsvignette(erhebung=erhebung, vignette=entwurf, position=1)]
        )


@pytest.mark.django_db
def test_erhebungsvignette_lehnt_fremde_finale_fassung_ab() -> None:
    """Die Mitgliedschaft beschränkt die Auswahl auf den eigenen Eigentümer-Kreis."""

    ada: Konto = Konto.objects.create_user(username="ada")
    grace: Konto = Konto.objects.create_user(username="grace")
    erhebung: Erhebung = Erhebung.objects.anlegen(ada, name="Brüche")
    fremde_finale: Vignette = finale_vignette(grace)

    with pytest.raises(IntegrityError, match="eigene"), transaction.atomic():
        Erhebungsvignette.objects.bulk_create(
            [Erhebungsvignette(erhebung=erhebung, vignette=fremde_finale, position=1)]
        )


@pytest.mark.django_db
def test_erhebung_bindet_material_ueber_eine_kreis_schnittmenge_ein() -> None:
    """Eine Ko-Forschende genügt für Vignetten und Items der gemeinsamen Erhebung."""

    ada: Konto = Konto.objects.create_user(username="ada")
    grace: Konto = Konto.objects.create_user(username="grace")
    linus: Konto = Konto.objects.create_user(username="linus")
    erhebung: Erhebung = Erhebung.objects.anlegen(ada, name="Brüche")
    erhebung.eigentuemerinnen.add(grace)
    vignette: Vignette = finale_vignette(grace)
    item: FragebogenItem = FragebogenItem.objects.anlegen(
        grace, wortlaut="Wie sicher fühlten Sie sich?"
    )
    item.finalisieren()

    Erhebungsvignette.objects.create(erhebung=erhebung, vignette=vignette, position=1)
    Erhebungsitem.objects.create(
        erhebung=erhebung,
        item=item,
        andockpunkt=Erhebungsitem.Andockpunkt.NACH_SITZUNG,
        position=1,
    )
    erhebung.eigentuemerinnen.add(linus)

    assert list(erhebung.vignetten.all()) == [vignette]
    assert list(erhebung.itemzugehoerigkeiten.values_list("item", flat=True)) == [
        item.pk
    ]


@pytest.mark.django_db
def test_erhebungsvignette_braucht_eine_position() -> None:
    """Ohne Position lässt sich keine Vignettenbindung speichern."""

    ada: Konto = Konto.objects.create_user(username="ada")
    erhebung: Erhebung = Erhebung.objects.anlegen(
        ada, name="Brüche", randomisierung=Erhebung.Randomisierung.ZUFAELLIG
    )
    finale: Vignette = finale_vignette(ada)

    with pytest.raises(IntegrityError), transaction.atomic():
        Erhebungsvignette.objects.create(erhebung=erhebung, vignette=finale)
    with pytest.raises(ValidationError, match="position"):
        Erhebungsvignette(erhebung=erhebung, vignette=finale).full_clean()


@pytest.mark.django_db
def test_vignettenposition_ist_je_erhebung_eindeutig() -> None:
    """Zwei Vignetten einer Erhebung teilen sich keine Position."""

    ada: Konto = Konto.objects.create_user(username="ada")
    erhebung: Erhebung = Erhebung.objects.anlegen(
        ada, name="Brüche", randomisierung=Erhebung.Randomisierung.ZUFAELLIG
    )
    Erhebungsvignette.objects.create(
        erhebung=erhebung, vignette=finale_vignette(ada), position=1
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        Erhebungsvignette.objects.create(
            erhebung=erhebung, vignette=finale_vignette(ada), position=1
        )


@pytest.mark.django_db
def test_erhebungsvignette_bewahrt_die_menge_je_erhebung_eindeutig() -> None:
    """Eine finale Vignetten-Fassung ist nur einmal Mitglied derselben Erhebung."""

    ada: Konto = Konto.objects.create_user(username="ada")
    erhebung: Erhebung = Erhebung.objects.anlegen(ada, name="Brüche")
    finale: Vignette = finale_vignette(ada)
    Erhebungsvignette.objects.create(erhebung=erhebung, vignette=finale, position=1)

    with pytest.raises(IntegrityError), transaction.atomic():
        Erhebungsvignette.objects.bulk_create(
            [Erhebungsvignette(erhebung=erhebung, vignette=finale, position=2)]
        )


@pytest.mark.django_db
def test_erhebungsitem_darf_an_beide_andockpunkte_aber_je_nur_einmal() -> None:
    """Die Zuordnung, nicht die Fassung, ist je Andockpunkt eindeutig."""

    ada: Konto = Konto.objects.create_user(username="ada")
    erhebung: Erhebung = Erhebung.objects.anlegen(ada, name="Brüche")
    item: FragebogenItem = FragebogenItem.objects.anlegen(
        ada, wortlaut="Wie sicher fühlten Sie sich?"
    )
    item.finalisieren()

    Erhebungsitem.objects.create(
        erhebung=erhebung,
        item=item,
        andockpunkt=Erhebungsitem.Andockpunkt.NACH_SITZUNG,
        position=1,
    )
    Erhebungsitem.objects.create(
        erhebung=erhebung,
        item=item,
        andockpunkt=Erhebungsitem.Andockpunkt.AM_ENDE,
        position=1,
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        Erhebungsitem.objects.bulk_create(
            [
                Erhebungsitem(
                    erhebung=erhebung,
                    item=item,
                    andockpunkt=Erhebungsitem.Andockpunkt.NACH_SITZUNG,
                    position=2,
                )
            ]
        )


@pytest.mark.django_db
def test_abschlussantwort_ist_je_block_eindeutig_und_nonresponse_ist_gueltig() -> None:
    """Die Eindeutigkeit der Antwortzeilen hängt am vorgelegten Itemblock."""

    ada = Konto.objects.create_user(username="ada")
    bindung = _erhebungsbindung_anlegen(ada, Teilnahme.objects.create())
    item = FragebogenItem.objects.anlegen(ada, wortlaut="Wie war es?")
    item.finalisieren()
    erhebungsitem = Erhebungsitem.objects.create(
        erhebung=bindung.stichprobe.erhebung,
        item=item,
        andockpunkt=Erhebungsitem.Andockpunkt.AM_ENDE,
        position=1,
    )
    block = Itemblock.objects.create(
        erhebungsbindung=bindung,
        andockpunkt=Erhebungsitem.Andockpunkt.AM_ENDE,
    )

    ItemAntwort.objects.create(
        itemblock=block, erhebungsbindung=bindung, erhebungsitem=erhebungsitem
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        ItemAntwort.objects.bulk_create(
            [
                ItemAntwort(
                    itemblock=block,
                    erhebungsbindung=bindung,
                    erhebungsitem=erhebungsitem,
                )
            ]
        )


@pytest.mark.django_db
def test_itemantwort_braucht_ihren_itemblock() -> None:
    """Ohne vorgelegten Block entsteht keine Antwortzeile."""

    ada = Konto.objects.create_user(username="ada")
    bindung = _erhebungsbindung_anlegen(ada, Teilnahme.objects.create())
    item = FragebogenItem.objects.anlegen(ada, wortlaut="Wie war es?")
    item.finalisieren()
    erhebungsitem = Erhebungsitem.objects.create(
        erhebung=bindung.stichprobe.erhebung,
        item=item,
        andockpunkt=Erhebungsitem.Andockpunkt.AM_ENDE,
        position=1,
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        ItemAntwort.objects.create(
            erhebungsbindung=bindung, erhebungsitem=erhebungsitem
        )


@pytest.mark.django_db
def test_itemantwort_erlaubt_hoechstens_eine_wertspalte() -> None:
    """Freitext und Likert-Stufe können nicht zugleich persistiert werden."""

    ada = Konto.objects.create_user(username="ada")
    bindung = _erhebungsbindung_anlegen(ada, Teilnahme.objects.create())
    item = FragebogenItem.objects.anlegen(ada, wortlaut="Wie war es?")
    item.finalisieren()
    erhebungsitem = Erhebungsitem.objects.create(
        erhebung=bindung.stichprobe.erhebung,
        item=item,
        andockpunkt=Erhebungsitem.Andockpunkt.AM_ENDE,
        position=1,
    )

    block = Itemblock.objects.create(
        erhebungsbindung=bindung,
        andockpunkt=Erhebungsitem.Andockpunkt.AM_ENDE,
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        ItemAntwort.objects.bulk_create(
            [
                ItemAntwort(
                    itemblock=block,
                    erhebungsbindung=bindung,
                    erhebungsitem=erhebungsitem,
                    freitext="Hilfreich",
                    likert_stufe=6,
                )
            ]
        )


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("typ", "werte"),
    [
        (FragebogenItem.Typ.FREITEXT, {"likert_stufe": 6}),
        (FragebogenItem.Typ.LIKERT, {"freitext": "Hilfreich"}),
    ],
)
def test_itemantwort_wert_passt_zum_itemtyp(typ: str, werte: dict[str, object]) -> None:
    """Die Antwortspalte folgt dem Typ der gepinnten Item-Fassung."""

    ada = Konto.objects.create_user(username=f"ada-{typ}")
    bindung = _erhebungsbindung_anlegen(ada, Teilnahme.objects.create())
    item = FragebogenItem.objects.anlegen(ada, typ=typ, wortlaut="Wie war es?")
    item.finalisieren()
    erhebungsitem = Erhebungsitem.objects.create(
        erhebung=bindung.stichprobe.erhebung,
        item=item,
        andockpunkt=Erhebungsitem.Andockpunkt.AM_ENDE,
        position=1,
    )

    with pytest.raises(ValidationError):
        ItemAntwort.objects.create(
            erhebungsbindung=bindung,
            erhebungsitem=erhebungsitem,
            **werte,
        )


@pytest.mark.django_db
def test_itemantwort_sitzung_und_andockpunkt_passen_zur_teilnahme() -> None:
    """Ein Sitzungs-Item braucht die Sitzung derselben Teilnahme."""

    ada = Konto.objects.create_user(username="ada")
    bindung = _erhebungsbindung_anlegen(ada, Teilnahme.objects.create())
    item = FragebogenItem.objects.anlegen(ada, wortlaut="Wie war es?")
    item.finalisieren()
    erhebungsitem = Erhebungsitem.objects.create(
        erhebung=bindung.stichprobe.erhebung,
        item=item,
        andockpunkt=Erhebungsitem.Andockpunkt.NACH_SITZUNG,
        position=1,
    )
    kern = finaler_kern()
    fremde_sitzung = Sitzung.objects.create(
        teilnahme=Teilnahme.objects.create(),
        vignette=finale_vignette(ada),
        simulationskern=kern,
        modell_konfiguration=ModellKonfiguration.objects.create(
            bezeichnung="Test", sprachmodell="fake"
        ),
    )

    with pytest.raises(ValidationError, match="anderen Teilnahme"):
        ItemAntwort.objects.create(
            erhebungsbindung=bindung,
            erhebungsitem=erhebungsitem,
            sitzung=fremde_sitzung,
        )
    with pytest.raises(ValidationError, match="nach_sitzung"):
        ItemAntwort.objects.create(
            erhebungsbindung=bindung,
            erhebungsitem=erhebungsitem,
        )


@pytest.mark.django_db
def test_itemposition_ist_je_andockpunkt_eindeutig() -> None:
    """Gleiche Positionen sind nur in unterschiedlichen Andockpunkten zulässig."""

    ada: Konto = Konto.objects.create_user(username="ada")
    erhebung: Erhebung = Erhebung.objects.anlegen(ada, name="Brüche")
    erstes_item: FragebogenItem = FragebogenItem.objects.anlegen(ada, wortlaut="Erstes")
    zweites_item: FragebogenItem = FragebogenItem.objects.anlegen(
        ada, wortlaut="Zweites"
    )
    for item in (erstes_item, zweites_item):
        item.finalisieren()

    Erhebungsitem.objects.create(
        erhebung=erhebung,
        item=erstes_item,
        andockpunkt=Erhebungsitem.Andockpunkt.NACH_SITZUNG,
        position=1,
    )
    Erhebungsitem.objects.create(
        erhebung=erhebung,
        item=zweites_item,
        andockpunkt=Erhebungsitem.Andockpunkt.AM_ENDE,
        position=1,
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        Erhebungsitem.objects.bulk_create(
            [
                Erhebungsitem(
                    erhebung=erhebung,
                    item=zweites_item,
                    andockpunkt=Erhebungsitem.Andockpunkt.NACH_SITZUNG,
                    position=1,
                )
            ]
        )


@pytest.mark.django_db
def test_erhebungsitem_schuetzt_finalitaet_eigentum_und_item_fassung() -> None:
    """Auch Bulk-Inserts umgehen weder Bibliotheksgrenzen noch Löschschutz."""

    ada: Konto = Konto.objects.create_user(username="ada")
    grace: Konto = Konto.objects.create_user(username="grace")
    erhebung: Erhebung = Erhebung.objects.anlegen(ada, name="Brüche")
    entwurf: FragebogenItem = FragebogenItem.objects.anlegen(ada, wortlaut="Entwurf")
    fremdes_item: FragebogenItem = FragebogenItem.objects.anlegen(
        grace, wortlaut="Fremd"
    )
    fremdes_item.finalisieren()

    for item in (entwurf, fremdes_item):
        with pytest.raises(IntegrityError), transaction.atomic():
            Erhebungsitem.objects.bulk_create(
                [
                    Erhebungsitem(
                        erhebung=erhebung,
                        item=item,
                        andockpunkt=Erhebungsitem.Andockpunkt.NACH_SITZUNG,
                        position=1,
                    )
                ]
            )

    eigenes_item: FragebogenItem = FragebogenItem.objects.anlegen(ada, wortlaut="Eigen")
    eigenes_item.finalisieren()
    Erhebungsitem.objects.create(
        erhebung=erhebung,
        item=eigenes_item,
        andockpunkt=Erhebungsitem.Andockpunkt.NACH_SITZUNG,
        position=1,
    )

    with pytest.raises(ProtectedError):
        models.Model.delete(eigenes_item)


_ZUORDNUNGSARTEN: tuple[str, str] = (
    "vignettenzugehoerigkeiten",
    "itemzugehoerigkeiten",
)


def _zuordnung_anlegen(erhebung: Erhebung, konto: Konto, art: str) -> models.Model:
    """Bindet eine frische finale Fassung der jeweiligen Art in die Erhebung ein."""

    position: int = getattr(erhebung, art).count() + 1
    if art == "vignettenzugehoerigkeiten":
        return Erhebungsvignette.objects.create(
            erhebung=erhebung,
            vignette=finale_vignette(konto),
            position=position,
        )
    item: FragebogenItem = FragebogenItem.objects.anlegen(
        konto, wortlaut=f"Wie sicher fühlten Sie sich? ({position})"
    )
    item.finalisieren()
    return Erhebungsitem.objects.create(
        erhebung=erhebung,
        item=item,
        andockpunkt=Erhebungsitem.Andockpunkt.NACH_SITZUNG,
        position=position,
    )


def _entwurf_mit_zuordnungen(konto: Konto) -> Erhebung:
    """Legt einen finalisierbaren Entwurf mit je einer Vignette und einem Item an."""

    erhebung: Erhebung = Erhebung.objects.anlegen(konto, name="Brüche")
    aktive_modell_konfiguration(Verwendung.SCHUELERIN)
    for art in _ZUORDNUNGSARTEN:
        _zuordnung_anlegen(erhebung, konto, art)
    return erhebung


@pytest.mark.django_db
@pytest.mark.parametrize("art", _ZUORDNUNGSARTEN)
def test_finale_erhebung_weist_jede_zuordnungsaenderung_ab(art: str) -> None:
    """Das eingebundene Design einer finalen Erhebung ist auf jedem Weg gesperrt."""

    ada: Konto = Konto.objects.create_user(username="ada")
    erhebung: Erhebung = _entwurf_mit_zuordnungen(ada)
    erhebung.finalisieren()
    zuordnungen: models.Manager = getattr(erhebung, art)
    zuordnung: models.Model = zuordnungen.get()

    with pytest.raises(ValidationError, match="eingefroren"):
        _zuordnung_anlegen(erhebung, ada, art)
    zuordnung.position = 9
    with pytest.raises(ValidationError, match="eingefroren"):
        zuordnung.save()
    with pytest.raises(ValidationError, match="eingefroren"):
        zuordnungen.update(position=9)
    with pytest.raises(ValidationError, match="eingefroren"):
        zuordnungen.delete()


@pytest.mark.django_db
@pytest.mark.parametrize("art", _ZUORDNUNGSARTEN)
def test_archivierte_erhebung_weist_jede_zuordnungsaenderung_ab(art: str) -> None:
    """Das Ablegen einer Erhebung macht ihr Design nicht wieder angreifbar."""

    ada: Konto = Konto.objects.create_user(username="ada")
    erhebung: Erhebung = _entwurf_mit_zuordnungen(ada)
    erhebung.finalisieren()
    erhebung.archivieren()
    zuordnungen: models.Manager = getattr(erhebung, art)

    with pytest.raises(ValidationError, match="eingefroren"):
        _zuordnung_anlegen(erhebung, ada, art)
    with pytest.raises(ValidationError, match="eingefroren"):
        zuordnungen.update(position=9)
    with pytest.raises(ValidationError, match="eingefroren"):
        zuordnungen.delete()


@pytest.mark.django_db
@pytest.mark.parametrize("art", _ZUORDNUNGSARTEN)
def test_entwurf_bleibt_in_seinen_zuordnungen_frei(art: str) -> None:
    """Vor dem Finalisieren behindert die Sperre das Zusammenstellen nicht."""

    ada: Konto = Konto.objects.create_user(username="ada")
    erhebung: Erhebung = _entwurf_mit_zuordnungen(ada)
    zuordnungen: models.Manager = getattr(erhebung, art)

    zweite: models.Model = _zuordnung_anlegen(erhebung, ada, art)
    zweite.position = 9
    zweite.save()
    zuordnungen.filter(pk=zweite.pk).update(position=8)
    zuordnungen.filter(pk=zweite.pk).delete()

    assert zuordnungen.count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize("art", _ZUORDNUNGSARTEN)
def test_zurueckgezogene_erhebung_erlaubt_zuordnungen_wieder(art: str) -> None:
    """Der Rückweg in den Entwurf gibt das Design vollständig wieder frei."""

    ada: Konto = Konto.objects.create_user(username="ada")
    erhebung: Erhebung = _entwurf_mit_zuordnungen(ada)
    erhebung.finalisieren()
    erhebung.zurueckziehen()
    zuordnungen: models.Manager = getattr(erhebung, art)

    zweite: models.Model = _zuordnung_anlegen(erhebung, ada, art)
    zuordnungen.filter(pk=zweite.pk).update(position=9)
    zuordnungen.filter(pk=zweite.pk).delete()

    assert zuordnungen.count() == 1


@pytest.mark.django_db
def test_entwurf_laesst_sich_mitsamt_seinen_zuordnungen_loeschen() -> None:
    """Die Sperre blockiert den erlaubten Löschpfad samt Kaskade nicht."""

    ada: Konto = Konto.objects.create_user(username="ada")
    erhebung: Erhebung = _entwurf_mit_zuordnungen(ada)

    erhebung.delete()

    assert not Erhebungsvignette.objects.exists()
    assert not Erhebungsitem.objects.exists()


@pytest.mark.django_db
def test_finalisieren_pinnt_die_aktive_modell_konfiguration() -> None:
    """Finalisieren friert die aktive Modell-Konfiguration an der Erhebung ein."""

    erhebung: Erhebung = Erhebung.objects.anlegen(
        Konto.objects.create_user(username="ada"), name="Brüche"
    )
    konfiguration: ModellKonfiguration = aktive_modell_konfiguration(
        Verwendung.SCHUELERIN
    )

    erhebung.finalisieren()

    assert erhebung.status == Erhebung.Status.FINAL
    assert erhebung.modell_konfiguration == konfiguration


@pytest.mark.django_db
def test_finalisieren_pinnt_die_schuelerin_nicht_lehrperson_oder_bewerter() -> None:
    """Ein Wechsel der Eval-Verwendungen ändert am Pin der Erhebung nichts."""

    erhebung: Erhebung = Erhebung.objects.anlegen(
        Konto.objects.create_user(username="ada"), name="Brüche"
    )
    schuelerin: ModellKonfiguration = ModellKonfiguration.objects.create(
        bezeichnung="Schüler:in", sprachmodell="fake"
    )
    andere: ModellKonfiguration = ModellKonfiguration.objects.create(
        bezeichnung="Andere", sprachmodell="fake"
    )
    ModellKonfiguration.objects.aktivieren(schuelerin, Verwendung.SCHUELERIN)
    ModellKonfiguration.objects.aktivieren(andere, Verwendung.LEHRPERSON)
    ModellKonfiguration.objects.aktivieren(andere, Verwendung.BEWERTER)

    erhebung.finalisieren()

    assert erhebung.modell_konfiguration == schuelerin


@pytest.mark.django_db
def test_zurueckziehen_und_erneutes_finalisieren_pinnt_aktuelle_konfiguration() -> None:
    """Ein zulässiger Rückweg macht das Design wieder bearbeitbar und pinnt neu."""

    erhebung: Erhebung = Erhebung.objects.anlegen(
        Konto.objects.create_user(username="ada"), name="Brüche"
    )
    erste: ModellKonfiguration = ModellKonfiguration.objects.create(
        bezeichnung="Test",
        anbieter=Anbieter.OPENROUTER,
        sprachmodell="openrouter/erste",
        anbieter_token="sk-or-geheim",
    )
    zweite: ModellKonfiguration = ModellKonfiguration.objects.create(
        bezeichnung="Test",
        anbieter=Anbieter.OPENROUTER,
        sprachmodell="openrouter/zweite",
        anbieter_token="sk-or-geheim",
    )
    ModellKonfiguration.objects.aktivieren(erste, Verwendung.SCHUELERIN)
    erhebung.finalisieren()

    erhebung.zurueckziehen()
    ModellKonfiguration.objects.aktivieren(zweite, Verwendung.SCHUELERIN)
    erhebung.finalisieren()

    assert erhebung.status == Erhebung.Status.FINAL
    assert erhebung.modell_konfiguration == zweite


@pytest.mark.django_db
def test_zurueckziehen_ist_mit_nicht_archivierter_stichprobe_gesperrt() -> None:
    """Eine aktive Stichprobe hält die finale Erhebung fest."""

    erhebung: Erhebung = Erhebung.objects.anlegen(
        Konto.objects.create_user(username="ada"), name="Brüche"
    )
    aktive_modell_konfiguration(Verwendung.SCHUELERIN)
    erhebung.finalisieren()
    Stichprobe.objects.create(
        erhebung=erhebung,
        beginn=timezone.now(),
        ende=timezone.now(),
    )

    with pytest.raises(ValidationError, match="nicht archivierten Stichproben"):
        erhebung.zurueckziehen()


@pytest.mark.django_db
def test_archivieren_ist_waehrend_laufender_stichprobe_gesperrt() -> None:
    """Eine laufende Stichprobe verhindert das Archivieren ihrer Erhebung."""

    erhebung: Erhebung = Erhebung.objects.anlegen(
        Konto.objects.create_user(username="ada"), name="Brüche"
    )
    aktive_modell_konfiguration(Verwendung.SCHUELERIN)
    erhebung.finalisieren()
    jetzt: datetime = timezone.now()
    Stichprobe.objects.create(
        erhebung=erhebung,
        beginn=jetzt - timedelta(minutes=1),
        ende=jetzt + timedelta(minutes=1),
    )

    with pytest.raises(ValidationError, match="laufenden Stichproben"):
        erhebung.archivieren()


@pytest.mark.django_db
def test_archivieren_akzeptiert_nur_finale_erhebungen() -> None:
    """Ein Entwurf folgt beim Archivieren seinem Lebenszyklus-Guard."""

    erhebung: Erhebung = Erhebung.objects.anlegen(
        Konto.objects.create_user(username="ada"), name="Brüche"
    )

    with pytest.raises(ValidationError, match="Nur finale Erhebungen"):
        erhebung.archivieren()


@pytest.mark.django_db
def test_archivieren_in_zweitem_tab_lehnt_den_uebergang_ab() -> None:
    """Eine inzwischen archivierte Erhebung meldet den abgelehnten Übergang."""

    erster_tab: Erhebung = Erhebung.objects.anlegen(
        Konto.objects.create_user(username="ada"), name="Brüche"
    )
    aktive_modell_konfiguration(Verwendung.SCHUELERIN)
    erster_tab.finalisieren()
    zweiter_tab: Erhebung = Erhebung.objects.get(pk=erster_tab.pk)
    erster_tab.archivieren()

    with pytest.raises(ValidationError, match="Nur finale Erhebungen"):
        zweiter_tab.archivieren()


@pytest.mark.django_db
def test_archivieren_und_entarchivieren_bewahren_den_finalen_pin() -> None:
    """Eine archivierte Erhebung kann mit ihrem unveränderten Design zurückkehren."""

    erhebung: Erhebung = Erhebung.objects.anlegen(
        Konto.objects.create_user(username="ada"), name="Brüche"
    )
    konfiguration: ModellKonfiguration = aktive_modell_konfiguration(
        Verwendung.SCHUELERIN
    )
    erhebung.finalisieren()

    erhebung.archivieren()
    erhebung.entarchivieren()

    assert erhebung.status == Erhebung.Status.FINAL
    assert erhebung.modell_konfiguration == konfiguration


@pytest.mark.django_db
def test_eigentuemerlose_erhebung_kann_nicht_entarchiviert_werden() -> None:
    """Eine archivierte Erhebung braucht vor der Rückkehr eine Eigentümerin."""

    erhebung: Erhebung = Erhebung.objects.anlegen(
        Konto.objects.create_user(username="ada"), name="Brüche"
    )
    aktive_modell_konfiguration(Verwendung.SCHUELERIN)
    erhebung.finalisieren()
    erhebung.archivieren()
    erhebung.eigentuemerinnen.clear()

    with pytest.raises(ValidationError, match="Eigentümerin"):
        erhebung.entarchivieren()


@pytest.mark.django_db
def test_finale_erhebung_ist_eingefroren_und_nicht_physisch_loeschbar() -> None:
    """Finale Erhebungen können weder still geändert noch gelöscht werden."""

    erhebung: Erhebung = Erhebung.objects.anlegen(
        Konto.objects.create_user(username="ada"), name="Brüche"
    )
    aktive_modell_konfiguration(Verwendung.SCHUELERIN)
    erhebung.finalisieren()

    erhebung.name = "Addition"
    with pytest.raises(ValidationError, match="eingefroren"):
        erhebung.save()
    with pytest.raises(ValidationError, match="Nur Entwürfe"):
        erhebung.delete()


@pytest.mark.django_db
def test_laufende_erhebung_behaelt_aenderbaren_eigentuemerinnenkreis() -> None:
    """Auch laufende Erhebungen können ihre Verantwortung übertragen."""

    ada: Konto = Konto.objects.create_user(username="ada")
    grace: Konto = Konto.objects.create_user(username="grace")
    erhebung: Erhebung = Erhebung.objects.anlegen(ada, name="Brüche")
    aktive_modell_konfiguration(Verwendung.SCHUELERIN)
    erhebung.finalisieren()
    erhebung.eigentuemerinnen.add(grace)
    Stichprobe.objects.create(
        erhebung=erhebung,
        beginn=timezone.now() - timedelta(minutes=1),
        ende=timezone.now() + timedelta(minutes=1),
    )
    erhebung.eigentuemerinnen.remove(ada)

    assert list(erhebung.eigentuemerinnen.all()) == [grace]
    assert erhebung.hat_laufende_stichprobe


@pytest.mark.django_db
def test_archivierte_erhebung_ist_auch_per_bulk_update_eingefroren() -> None:
    """Archivierte Erhebungen behalten ihr finales Design unverändert."""

    erhebung: Erhebung = Erhebung.objects.anlegen(
        Konto.objects.create_user(username="ada"), name="Brüche"
    )
    aktive_modell_konfiguration(Verwendung.SCHUELERIN)
    erhebung.finalisieren()
    erhebung.archivieren()

    with pytest.raises(ValidationError, match="eingefroren"):
        Erhebung.objects.filter(pk=erhebung.pk).update(name="Addition")


@pytest.mark.django_db
def test_stichprobe_archivieren_schaltet_nur_ueber_ihre_lebenszyklus_methode() -> None:
    """Eine Stichprobe wird logisch statt physisch aus der Arbeit genommen."""

    erhebung: Erhebung = Erhebung.objects.anlegen(
        Konto.objects.create_user(username="ada"), name="Brüche"
    )
    stichprobe: Stichprobe = Stichprobe.objects.create(
        erhebung=erhebung,
        beginn=timezone.now(),
        ende=timezone.now(),
    )

    neu_geladen: Stichprobe = Stichprobe.objects.get(pk=stichprobe.pk)
    neu_geladen.archiviert = True

    with pytest.raises(ValidationError, match="Lebenszyklus-Methode"):
        neu_geladen.save()

    stichprobe.archivieren()

    assert Stichprobe.objects.get(pk=stichprobe.pk).archiviert is True
    with pytest.raises(ValidationError, match="bereits archiviert"):
        stichprobe.archivieren()


@pytest.mark.django_db
def test_stichprobe_laesst_sich_nicht_per_bulk_update_archivieren() -> None:
    """Die Archivierungs-Guards einer Stichprobe sind nicht umgehbar."""

    erhebung: Erhebung = Erhebung.objects.anlegen(
        Konto.objects.create_user(username="ada"), name="Brüche"
    )
    stichprobe: Stichprobe = Stichprobe.objects.create(
        erhebung=erhebung,
        beginn=timezone.now(),
        ende=timezone.now(),
    )

    with pytest.raises(ValidationError, match="Lebenszyklus-Methode"):
        Stichprobe.objects.filter(pk=stichprobe.pk).update(archiviert=True)


@pytest.mark.django_db
def test_anlegen_vergibt_lesbare_eindeutige_teilnahme_tokens() -> None:
    """Neue Erhebungsteilnahmen erhalten unterscheidbare Tokens ohne 0, 1, I oder O."""

    erhebung: Erhebung = Erhebung.objects.anlegen(
        Konto.objects.create_user(username="ada"), name="Brüche"
    )
    stichprobe: Stichprobe = Stichprobe.objects.create(
        erhebung=erhebung,
        beginn=timezone.now(),
        ende=timezone.now(),
    )

    erste: Erhebungsbindung = Erhebungsbindung.objects.anlegen(stichprobe)
    zweite: Erhebungsbindung = Erhebungsbindung.objects.anlegen(stichprobe)

    assert re.fullmatch(
        r"[23456789ABCDEFGHJKMNPQRSTVWXYZ]{4}-[23456789ABCDEFGHJKMNPQRSTVWXYZ]{4}",
        erste.token,
    )
    assert erste.token != zweite.token


@pytest.mark.django_db
def test_anlegen_wiederholt_token_nach_kollision() -> None:
    """Eine vorhandene Tokenfolge wird nie einer zweiten Teilnahme zugeordnet."""

    erhebung: Erhebung = Erhebung.objects.anlegen(
        Konto.objects.create_user(username="ada"), name="Brüche"
    )
    stichprobe: Stichprobe = Stichprobe.objects.create(
        erhebung=erhebung,
        beginn=timezone.now(),
        ende=timezone.now(),
    )
    Erhebungsbindung.objects.create(
        stichprobe=stichprobe,
        teilnahme=Teilnahme.objects.create(),
        token="2345-6789",
    )

    with patch(
        "erhebungen.models.choice",
        side_effect=[*"23456789", *"ABCDEFGH"],
    ):
        bindung: Erhebungsbindung = Erhebungsbindung.objects.anlegen(stichprobe)

    assert bindung.token == "ABCD-EFGH"


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("zeitpunkt", "erwartete_phase"),
    [
        (datetime(2026, 7, 16, 8, 59), Stichprobe.Phase.VOR),
        (datetime(2026, 7, 16, 9), Stichprobe.Phase.LAUFEND),
        (datetime(2026, 7, 16, 17, 1), Stichprobe.Phase.NACH),
    ],
)
def test_phase_leitet_sich_aus_zeitraum_und_systemzeit_ab(
    zeitpunkt: datetime,
    erwartete_phase: str,
) -> None:
    """Eine Stichprobe ist vor, während oder nach ihrem Erhebungszeitraum."""

    erhebung: Erhebung = Erhebung.objects.anlegen(
        Konto.objects.create_user(username="ada"), name="Brüche"
    )
    stichprobe: Stichprobe = Stichprobe.objects.create(
        erhebung=erhebung,
        beginn=timezone.make_aware(datetime(2026, 7, 16, 9)),
        ende=timezone.make_aware(datetime(2026, 7, 16, 17)),
    )

    with patch(
        "erhebungen.models.timezone.now",
        return_value=timezone.make_aware(zeitpunkt),
    ):
        assert stichprobe.phase == erwartete_phase
