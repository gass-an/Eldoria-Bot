import pytest

from eldoria.app.services import Services


def test_services_len_is_number_of_fields():
    s = Services(
        duel=object(),
        role=object(),
        save=object(),
        temp_voice=object(),
        welcome=object(),
        xp=object(),
    )
    assert len(s) == 6


def test_services_stores_attributes():
    duel = object()
    role = object()
    save = object()
    temp_voice = object()
    welcome = object()
    xp = object()

    s = Services(
        duel=duel,
        role=role,
        save=save,
        temp_voice=temp_voice,
        welcome=welcome,
        xp=xp,
    )

    assert s.duel is duel
    assert s.role is role
    assert s.save is save
    assert s.temp_voice is temp_voice
    assert s.welcome is welcome
    assert s.xp is xp


def test_services_is_slots_dataclass_no_dict_and_no_new_attrs():
    s = Services(
        duel=object(),
        role=object(),
        save=object(),
        temp_voice=object(),
        welcome=object(),
        xp=object(),
    )

    # slots => pas de __dict__
    assert not hasattr(s, "__dict__")

    # on ne peut pas ajouter un attribut arbitraire
    with pytest.raises(AttributeError):
        s.new_attr = 123  # type: ignore[attr-defined]
