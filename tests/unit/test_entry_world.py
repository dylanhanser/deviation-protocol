from copy import deepcopy

import pytest
from deviation_protocol.domain import entry_world as w


def reference():
    return w.EntryWorldRefV1(entry_world_id=w.EntryWorldId(value="world.death_certificate"),
                            entry_world_version=w.EntryWorldVersion(value=1))


def test_authored_identity_and_association():
    world = w.lookup_entry_world(reference())
    assert world is w.AUTHORED_ENTRY_WORLDS_V1[0]
    assert (world.scenario_id, world.scenario_content_version, world.default_character_definition_id) == (
        "death_certificate", "death-certificate-1.1.0", "character.death_certificate.investigator")
    assert world.entry_world_id.value != world.scenario_id
    with pytest.raises(w.EntryWorldValidationError):
        w.lookup_entry_world(world)


@pytest.mark.parametrize("value", [True, False, 0, -1, 2**63, 1.0, "1", None])
def test_version_exact(value):
    with pytest.raises(ValueError):
        w.EntryWorldVersion(value=value)


@pytest.mark.parametrize("value", ["", "x" * 129, "世界", "x/y", " x", ".x", "x\n", None, 1])
def test_id_exact(value):
    with pytest.raises(ValueError):
        w.EntryWorldId(value=value)


@pytest.mark.parametrize("mutate", ["extra", "nested", "missing", "version"])
def test_original_state_and_serialization(mutate):
    ref = reference()
    if mutate == "extra":
        ref.__dict__["scenario"] = "forged"
    elif mutate == "nested":
        ref.entry_world_id.__dict__["invisible"] = True
    elif mutate == "missing":
        del ref.__dict__["entry_world_version"]
    else:
        ref.entry_world_version.__dict__["value"] = True
    with pytest.raises(w.EntryWorldValidationError):
        w.lookup_entry_world(ref)
    with pytest.raises((ValueError, TypeError)):
        ref.model_dump()


def test_unknown_and_corrupted_catalogue(monkeypatch):
    with pytest.raises(w.EntryWorldLookupError):
        w.lookup_entry_world(reference().model_copy(update={"entry_world_version": w.EntryWorldVersion(value=2)}))
    entry = deepcopy(w.AUTHORED_ENTRY_WORLDS_V1[0])
    entry.__dict__["unapproved"] = True
    monkeypatch.setattr(w, "AUTHORED_ENTRY_WORLDS_V1", (entry,))
    with pytest.raises(w.EntryWorldCatalogueIntegrityError):
        w.lookup_entry_world(reference())
