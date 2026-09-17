import json
import pytest
from pydantic import ValidationError

from deviation_protocol.application.public_run_protocol import (
    FiveObjectives, PublicNativeRunContext, project_native_context, project_entry_options,
)
from deviation_protocol.api.demo_composition import build_demo_runtime, build_dynamic_demo_runtime
from tests.unit.test_native_run_admission import native_service_fixture, command


def test_discovery_exact_authoritative_catalogue_and_unavailable_graph():
    runtime=build_demo_runtime()
    options=project_entry_options(runtime.services.session_service,runtime.services.session_service.native_view_coordinator).model_dump(mode="json")
    assert set(options)=={"schema_version","native_entry_available","profiles","entry_worlds","presentation_options"}
    assert [list(p["defaults"].values()) for p in options["profiles"]]==[[95,10,95,90,90],[60,45,65,60,60],[25,70,35,30,35]]
    assert [[(r["minimum"],r["maximum"],r["step"]) for r in p["override_rules"]] for p in options["profiles"]]==[
        [(80,100,5),(0,25,5),(80,100,5),(75,100,5),(75,100,5)],
        [(40,75,5),(30,65,5),(45,80,5),(40,75,5),(40,75,5)],
        [(10,40,5),(55,85,5),(20,50,5),(15,45,5),(20,50,5)]]
    assert [p["label"] for p in options["profiles"]]==["Extreme — Silent Hunting Ground","Standard — Fragile Alliance","Easier — Open Expedition"]
    world=options["entry_worlds"][0]
    assert set(world)=={"entry_world","scenario_id","scenario_content_version","title","hook","eligible_profiles"}
    assert world["entry_world"]=={"entry_world_id":"world.death_certificate","entry_world_version":1}
    assert world["eligible_profiles"]==[p["profile_ref"] for p in options["profiles"]]
    public=runtime.services.session_service.scenario_catalog.scenarios[0].public_client
    assert (world["title"],world["hook"])==(public.title,public.hook)
    dynamic=build_dynamic_demo_runtime(environ={})
    unavailable=project_entry_options(dynamic.services.session_service,None)
    assert not unavailable.native_entry_available and unavailable.profiles==unavailable.entry_worlds==()


def test_corrupt_discovery_association_cannot_silently_become_unavailable():
    from types import SimpleNamespace
    runtime=build_demo_runtime()
    with pytest.raises(ValueError,match="discovery association"):
        project_entry_options(runtime.services.session_service,SimpleNamespace(catalogue=()))


async def test_projection_is_closed_detached_and_excludes_internal_values():
    service,_,_,legacy=native_service_fixture([])
    result=await service.enter(legacy.PRINCIPAL,command=command(legacy.REFERENCE.player_character_id))
    context=project_native_context(result)
    data=context.model_dump(mode="json")
    assert set(data)=={"schema_version","run_id","player_character","entry_world","profile_ref","objectives","presentation","resource_pressure_label"}
    assert set(data["player_character"])=={"player_character_id","contract_version","record_revision","lifecycle"}
    assert set(data["presentation"])=={"world_tone","reality_boundary","relationship_overlay"}
    serialized=json.dumps(data)
    for value in (result.continuous_story_line_id.value,result.resolved_protocol.fingerprint.value,"source.","controller.","selected_result","resolution_input"):
        assert value not in serialized
    data["objectives"]["resource_pressure"]=0
    assert context.objectives.resource_pressure==result.resolved_protocol.final_values.resource_pressure.value==60


@pytest.mark.parametrize("value",[31,34,66,69,True,1.0,"35",None,-5,105])
def test_exact_public_lattice(value):
    with pytest.raises(ValidationError):
        FiveObjectives(resource_pressure=value,social_trust=50,consequence_severity=50,information_opacity=50,conflict_intensity=50)


@pytest.mark.parametrize("value,label",[(30,"Generous"),(35,"Fluid"),(65,"Fluid"),(70,"Scarce")])
async def test_exact_pressure_bands(value,label):
    service,_,_,legacy=native_service_fixture([])
    result=await service.enter(legacy.PRINCIPAL,command=command(legacy.REFERENCE.player_character_id))
    data=project_native_context(result).model_dump(mode="json")
    data["objectives"]["resource_pressure"]=value; data["resource_pressure_label"]=label
    assert PublicNativeRunContext.model_validate_json(json.dumps(data)).objectives.resource_pressure==value
    data["resource_pressure_label"]="Scarce" if label!="Scarce" else "Generous"
    with pytest.raises(ValidationError): PublicNativeRunContext.model_validate_json(json.dumps(data))
