from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from unison_common.principal import PrincipalKind
import synthetic_intent_bridge as bridge


def test_synthetic_intent_disabled_and_requires_injected_runtime(monkeypatch):
    request=SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))
    monkeypatch.delenv('UNISON_SYNTHETIC_INTENT',raising=False)
    with pytest.raises(HTTPException) as error:bridge.interact(request,{'operation':'start','mechanism':'oauth'})
    assert error.value.status_code==403
    monkeypatch.setenv('UNISON_SYNTHETIC_INTENT','true')
    monkeypatch.setattr(bridge,'get_bound_principal',lambda request:SimpleNamespace(principal_kind=PrincipalKind.PERSON))
    with pytest.raises(HTTPException) as error:bridge.interact(request,{'operation':'start','mechanism':'oauth'})
    assert error.value.status_code==503


def test_bridge_preserves_bound_actor_and_denies_unsupported_input(monkeypatch):
    actor=SimpleNamespace(principal_kind=PrincipalKind.PERSON)
    class Interaction:
        def start(self,principal,mechanism,mode):
            assert principal is actor
            return {'state':'proposed'}
    request=SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(synthetic_intent_interaction=Interaction())))
    monkeypatch.setenv('UNISON_SYNTHETIC_INTENT','true');monkeypatch.setattr(bridge,'get_bound_principal',lambda request:actor)
    assert bridge.interact(request,{'operation':'start','mechanism':'oauth'})=={'state':'proposed'}
    with pytest.raises(HTTPException):bridge.interact(request,{'operation':'start','mechanism':'oauth','person_id':'someone-else'})
