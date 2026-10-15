"""Antwortversuche gegen den deterministischen Sprachmodell-Fake."""

from unittest import mock

import pytest

from simulation import (
    Antwortversuch,
    Ausfuehrung,
    Ausgabeversuch,
    antwort_versuchen,
    ausgabe_versuchen,
)
from simulation.models import ModellKonfiguration, Simulationskern
from simulation.sprachmodell import BEWERTER_SCHEMA, LEHRPERSON_SCHEMA


def test_antwort_versuchen_liefert_denkspur_und_aeusserung_des_fakes() -> None:
    """Ein geglückter Modellaufruf wird als Antwortversuch zurückgegeben."""

    antwortversuch = antwort_versuchen(
        {
            "fehlermuster_beschreibung": "Brüche werden addiert.",
            "lernauftrag": "Addiere zwei Brüche.",
        },
        Simulationskern(
            system_prompt_vorlage="$fehlermuster_beschreibung",
            user_prompt_vorlage="$lernauftrag",
        ),
        ModellKonfiguration(
            sprachmodell="fake",
            parameter={
                "skript": [
                    {"denkspur": "Ich addiere Zähler und Nenner.", "aeusserung": "2/5."}
                ]
            },
        ),
        verlauf=[],
        eingabe="Wie hast du gerechnet?",
    )

    assert antwortversuch.antwort.denkspur == "Ich addiere Zähler und Nenner."
    assert antwortversuch.antwort.aeusserung == "2/5."
    assert antwortversuch.fehlversuche == []


def test_antwort_versuchen_haelt_formatbruch_neben_der_antwort_fest() -> None:
    """Ein Formatbruch wird verworfen und der nächste Versuch wird genutzt."""

    antwortversuch = antwort_versuchen(
        {"lernauftrag": "Addiere zwei Brüche."},
        Simulationskern(user_prompt_vorlage="$lernauftrag"),
        ModellKonfiguration(
            sprachmodell="fake",
            parameter={
                "skript": [
                    {"fehler": "formatbruch", "rohantwort": "keine JSON-Antwort"},
                    {"denkspur": "Ich addiere.", "aeusserung": "2/5."},
                ]
            },
        ),
        verlauf=[],
        eingabe="Wie hast du gerechnet?",
    )

    assert antwortversuch.antwort is not None
    assert antwortversuch.fehlversuche[0].grund == "Formatbruch"
    assert antwortversuch.fehlversuche[0].rohantwort == "keine JSON-Antwort"


def test_antwort_versuchen_haelt_anbieterfehler_neben_der_antwort_fest() -> None:
    """Ein Anbieterfehler wird verworfen und der nächste Versuch wird genutzt."""

    antwortversuch = antwort_versuchen(
        {"lernauftrag": "Addiere zwei Brüche."},
        Simulationskern(user_prompt_vorlage="$lernauftrag"),
        ModellKonfiguration(
            sprachmodell="fake",
            parameter={
                "skript": [
                    {"fehler": "anbieterfehler"},
                    {"denkspur": "Ich addiere.", "aeusserung": "2/5."},
                ]
            },
        ),
        verlauf=[],
        eingabe="Wie hast du gerechnet?",
    )

    assert antwortversuch.antwort is not None
    assert antwortversuch.fehlversuche[0].grund == "Anbieterfehler"


def test_antwort_versuchen_kennzeichnet_drei_verworfene_versuche() -> None:
    """Nach dem begrenzten Wiederholen bleibt kein halber Gesprächsschritt zurück."""

    antwortversuch = antwort_versuchen(
        {"lernauftrag": "Addiere zwei Brüche."},
        Simulationskern(user_prompt_vorlage="$lernauftrag"),
        ModellKonfiguration(
            sprachmodell="fake",
            parameter={"skript": [{"fehler": "anbieterfehler"}] * 4},
        ),
        verlauf=[],
        eingabe="Wie hast du gerechnet?",
    )

    assert antwortversuch.antwort is None
    assert [fehlversuch.grund for fehlversuch in antwortversuch.fehlversuche] == [
        "Anbieterfehler",
        "Anbieterfehler",
        "Anbieterfehler",
    ]


def _schuelerin_versuchen(skript: list[dict[str, object]]) -> Antwortversuch:
    # Ein Antwortversuch der simulierten Schüler:in gegen ein Fake-Skript.

    return antwort_versuchen(
        {"lernauftrag": "Addiere zwei Brüche."},
        Simulationskern(user_prompt_vorlage="$lernauftrag"),
        _fake_konfiguration(skript),
        verlauf=[],
        eingabe="Wie hast du gerechnet?",
    )


@pytest.mark.parametrize(
    "leer",
    [
        {"denkspur": "", "aeusserung": "x"},
        {"denkspur": "Ich addiere.", "aeusserung": ""},
        {"denkspur": "Ich addiere.", "aeusserung": "\n"},
        {"denkspur": "  ", "aeusserung": "2/5."},
    ],
)
def test_antwort_versuchen_verwirft_leere_denkspur_oder_aeusserung(
    leer: dict[str, str],
) -> None:
    """Ein leeres Pflichtfeld ist ein Formatbruch, kein geglückter Schritt (ADR-0061)."""

    antwortversuch = _schuelerin_versuchen(
        [leer, {"denkspur": "Ich addiere.", "aeusserung": "2/5."}]
    )

    assert antwortversuch.antwort is not None
    assert antwortversuch.antwort.aeusserung == "2/5."
    assert [fehlversuch.grund for fehlversuch in antwortversuch.fehlversuche] == [
        "Formatbruch"
    ]


def test_antwort_versuchen_scheitert_an_anhaltend_leerer_ausgabe() -> None:
    """Bleibt die Ausgabe in allen Versuchen leer, entsteht kein Gesprächsschritt."""

    antwortversuch = _schuelerin_versuchen([{"denkspur": "", "aeusserung": ""}] * 3)

    assert antwortversuch.antwort is None
    assert [fehlversuch.grund for fehlversuch in antwortversuch.fehlversuche] == [
        "Formatbruch"
    ] * 3


def test_antwort_versuchen_laesst_leerraum_um_den_inhalt_unveraendert() -> None:
    """Nur ein leeres Feld bricht das Format; umgebender Leerraum bleibt stehen."""

    antwortversuch = _schuelerin_versuchen(
        [{"denkspur": " Ich addiere.\n", "aeusserung": "\n2/5. "}]
    )

    assert antwortversuch.antwort is not None
    assert antwortversuch.antwort.denkspur == " Ich addiere.\n"
    assert antwortversuch.antwort.aeusserung == "\n2/5. "
    assert antwortversuch.fehlversuche == []


def _fake_konfiguration(
    skript: list[dict[str, object]], **parameter: object
) -> ModellKonfiguration:
    # Eine ungespeicherte Fake-Konfiguration; weitere Parameter kommen dazu.

    return ModellKonfiguration(
        sprachmodell="fake", parameter={"skript": skript, **parameter}
    )


def _lehrperson_versuchen(
    modell_konfiguration: ModellKonfiguration,
    ausfuehrung: Ausfuehrung | None = None,
) -> Ausgabeversuch:
    # Ein Aufruf mit dem Schema der simulierten Lehrperson.

    return ausgabe_versuchen(
        "Du bist Lehrperson.",
        modell_konfiguration,
        verlauf=[],
        eingabe="Frag nach.",
        ausgabe_schema=LEHRPERSON_SCHEMA,
        ausfuehrung=ausfuehrung,
    )


def test_ausgabe_versuchen_liefert_die_ausgabe_der_lehrperson() -> None:
    """Das geparste Objekt trägt genau die Felder des übergebenen Schemas."""

    ausgabeversuch = _lehrperson_versuchen(
        _fake_konfiguration([{"aeusserung": "Wie hast du gerechnet?"}])
    )

    assert ausgabeversuch.ausgabe == {"aeusserung": "Wie hast du gerechnet?"}
    assert ausgabeversuch.fehlversuche == []


def test_ausgabe_versuchen_liefert_die_ausgabe_des_bewerters() -> None:
    """Der Bewerter liefert Begründung und booleschen Befund."""

    ausgabeversuch = ausgabe_versuchen(
        "Du bewertest.",
        _fake_konfiguration([{"begruendung": "Muster gezeigt.", "erfuellt": True}]),
        verlauf=[],
        eingabe="Kriterium",
        ausgabe_schema=BEWERTER_SCHEMA,
    )

    assert ausgabeversuch.ausgabe == {
        "begruendung": "Muster gezeigt.",
        "erfuellt": True,
    }


@pytest.mark.parametrize(
    "eintrag",
    [
        {"begruendung": "Muster gezeigt."},
        {"begruendung": "Muster gezeigt.", "erfuellt": "ja"},
        {"begruendung": "Muster gezeigt.", "erfuellt": True, "note": 1},
        {"denkspur": "Ich addiere.", "aeusserung": "2/5."},
        {"begruendung": "", "erfuellt": True},
        {"begruendung": " \n", "erfuellt": False},
    ],
)
def test_ausgabe_versuchen_verwirft_eine_ausgabe_neben_dem_schema(
    eintrag: dict[str, object],
) -> None:
    """Fehlende, falsch typisierte, zusätzliche oder leere Felder sind ein Formatbruch."""

    ausgabeversuch = ausgabe_versuchen(
        "Du bewertest.",
        _fake_konfiguration([eintrag] * 3),
        verlauf=[],
        eingabe="Kriterium",
        ausgabe_schema=BEWERTER_SCHEMA,
    )

    assert ausgabeversuch.ausgabe is None
    assert [fehlversuch.grund for fehlversuch in ausgabeversuch.fehlversuche] == [
        "Formatbruch"
    ] * 3


@pytest.mark.parametrize("leer", ["", "  ", "\n"])
def test_ausgabe_versuchen_verwirft_eine_leere_aeusserung_der_lehrperson(
    leer: str,
) -> None:
    """Auch die Lehrperson muss etwas sagen; sonst folgt der nächste Versuch."""

    ausgabeversuch = _lehrperson_versuchen(
        _fake_konfiguration([{"aeusserung": leer}, {"aeusserung": "Warum?"}])
    )

    assert ausgabeversuch.ausgabe == {"aeusserung": "Warum?"}
    assert [fehlversuch.grund for fehlversuch in ausgabeversuch.fehlversuche] == [
        "Formatbruch"
    ]


def test_ausgabe_versuchen_wiederholt_hoechstens_max_versuche_mal() -> None:
    """Auch Lehrperson und Bewerter bekommen keine zusätzlichen Versuche."""

    ausgabeversuch = _lehrperson_versuchen(
        _fake_konfiguration(
            [{"fehler": "content_filter"}] * 3 + [{"aeusserung": "Zu spät."}]
        )
    )

    assert ausgabeversuch.ausgabe is None
    assert len(ausgabeversuch.fehlversuche) == 3


def test_der_fake_beginnt_ohne_opt_in_bei_jedem_aufruf_von_vorn() -> None:
    """Ohne `skript_fortlesen` bleibt das bisherige Neustarten erhalten."""

    konfiguration = _fake_konfiguration(
        [{"aeusserung": "Erste."}, {"aeusserung": "Zweite."}]
    )
    ausfuehrung = Ausfuehrung()

    ausgaben = [
        _lehrperson_versuchen(konfiguration, ausfuehrung).ausgabe for _ in range(2)
    ]

    assert ausgaben == [{"aeusserung": "Erste."}, {"aeusserung": "Erste."}]


def test_der_fake_liest_sein_skript_mit_opt_in_ueber_aufrufe_fort() -> None:
    """Fehlversuche und Antworten verschiedener Aufrufe teilen sich ein Skript."""

    konfiguration = _fake_konfiguration(
        [
            {"aeusserung": "Erste."},
            {"fehler": "anbieterfehler"},
            {"aeusserung": "Zweite."},
        ],
        skript_fortlesen=True,
    )
    ausfuehrung = Ausfuehrung()

    erster = _lehrperson_versuchen(konfiguration, ausfuehrung)
    zweiter = _lehrperson_versuchen(konfiguration, ausfuehrung)

    assert erster.ausgabe == {"aeusserung": "Erste."}
    assert zweiter.ausgabe == {"aeusserung": "Zweite."}
    assert [fehlversuch.grund for fehlversuch in zweiter.fehlversuche] == [
        "Anbieterfehler"
    ]


def test_der_fake_beginnt_ohne_ausfuehrung_trotz_opt_in_von_vorn() -> None:
    """Sitzungen und Probeläufe kennen keine Ausführung und bleiben unverändert."""

    konfiguration = _fake_konfiguration(
        [
            {"denkspur": "D1.", "aeusserung": "Erste."},
            {"denkspur": "D2.", "aeusserung": "Zweite."},
        ],
        skript_fortlesen=True,
    )

    aeusserungen = [
        antwort_versuchen(
            {}, Simulationskern(), konfiguration, verlauf=[], eingabe="Und?"
        ).antwort.aeusserung
        for _ in range(2)
    ]

    assert aeusserungen == ["Erste.", "Erste."]


def test_der_fortschritt_des_fakes_ist_je_ausfuehrung_isoliert() -> None:
    """Eine neue Ausführung beginnt vorn und lässt die alte unberührt."""

    konfiguration = _fake_konfiguration(
        [{"aeusserung": "Erste."}, {"aeusserung": "Zweite."}],
        skript_fortlesen=True,
    )
    alte = Ausfuehrung()
    _lehrperson_versuchen(konfiguration, alte)

    neu = _lehrperson_versuchen(konfiguration, Ausfuehrung())
    alt = _lehrperson_versuchen(konfiguration, alte)

    assert neu.ausgabe == {"aeusserung": "Erste."}
    assert alt.ausgabe == {"aeusserung": "Zweite."}


@pytest.mark.django_db
def test_der_fortschritt_des_fakes_ist_je_konfiguration_isoliert() -> None:
    """Zwei Verwendungen derselben Ausführung lesen je ihr eigenes Skript."""

    lehrperson = ModellKonfiguration.objects.create(
        bezeichnung="Lehrperson",
        sprachmodell="fake",
        parameter={
            "skript": [{"aeusserung": "L1."}, {"aeusserung": "L2."}],
            "skript_fortlesen": True,
        },
    )
    schuelerin = ModellKonfiguration.objects.create(
        bezeichnung="Schüler:in",
        sprachmodell="fake",
        parameter={
            "skript": [
                {"denkspur": "D1.", "aeusserung": "S1."},
                {"denkspur": "D2.", "aeusserung": "S2."},
            ],
            "skript_fortlesen": True,
        },
    )
    ausfuehrung = Ausfuehrung()

    verlauf: list[str] = []
    for _ in range(2):
        frage = _lehrperson_versuchen(
            ModellKonfiguration.objects.get(pk=lehrperson.pk), ausfuehrung
        ).ausgabe["aeusserung"]
        antwort = antwort_versuchen(
            {},
            Simulationskern(),
            ModellKonfiguration.objects.get(pk=schuelerin.pk),
            verlauf=[],
            eingabe=frage,
            ausfuehrung=ausfuehrung,
        ).antwort
        verlauf += [frage, antwort.aeusserung]

    assert verlauf == ["L1.", "S1.", "L2.", "S2."]


def test_der_fake_liest_nur_mit_eingeschaltetem_opt_in_fort() -> None:
    """Ein als Text getipptes „false“ schaltet das Fortlesen nicht ein."""

    konfiguration = _fake_konfiguration(
        [{"aeusserung": "Erste."}, {"aeusserung": "Zweite."}],
        skript_fortlesen="false",
    )
    ausfuehrung = Ausfuehrung()

    ausgaben = [
        _lehrperson_versuchen(konfiguration, ausfuehrung).ausgabe for _ in range(2)
    ]

    assert ausgaben == [{"aeusserung": "Erste."}, {"aeusserung": "Erste."}]


@pytest.mark.parametrize(
    ("verzoegerung", "wartezeiten"),
    [
        (2.5, [2.5, 2.5]),
        ("2", []),
        (True, []),
        (-1, []),
        (float("nan"), []),
        (float("inf"), []),
    ],
)
def test_der_fake_wartet_nur_mit_einer_zahl_als_verzoegerung(
    verzoegerung: object, wartezeiten: list[float]
) -> None:
    """Die Verzögerung spielt ein langsames Modell; nur endliche Zahlen ab 0 zählen."""

    konfiguration = _fake_konfiguration(
        [{"aeusserung": "Erste."}, {"aeusserung": "Zweite."}],
        skript_fortlesen=True,
        verzoegerung=verzoegerung,
    )
    ausfuehrung = Ausfuehrung()
    gewartet: list[float] = []

    with mock.patch("time.sleep", gewartet.append):
        for _ in range(2):
            _lehrperson_versuchen(konfiguration, ausfuehrung)

    assert gewartet == wartezeiten
