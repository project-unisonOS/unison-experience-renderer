from types import SimpleNamespace

import httpx
import pytest
from fastapi import HTTPException
from unison_common.principal import PrincipalKind
import health_workflow_proxy as proxy


@pytest.mark.parametrize('base',['https://outside.example','http://localhost:8082','http://127.0.0.1:8082/path','http://person:pass@127.0.0.1:8082','file:///tmp/data'])
def test_proxy_rejects_unqualified_destinations(monkeypatch,base):
    monkeypatch.setattr(proxy,'get_bound_principal',lambda request:SimpleNamespace(principal_kind=PrincipalKind.PERSON,audience=['storage']))
    monkeypatch.setattr(proxy,'get_current_principal_token',lambda:'synthetic')
    with pytest.raises(HTTPException): proxy.proxy(None,'GET','/v1/health-workflows/test',None,base)


def test_proxy_forwards_only_bound_token_and_denies_redirect(monkeypatch):
    monkeypatch.setattr(proxy,'get_bound_principal',lambda request:SimpleNamespace(principal_kind=PrincipalKind.PERSON,audience=['storage']))
    monkeypatch.setattr(proxy,'get_current_principal_token',lambda:'synthetic')
    def handler(request):
        assert request.headers['Authorization']=='Bearer synthetic'
        return httpx.Response(307,headers={'Location':'http://outside.example'})
    with pytest.raises(HTTPException):
        proxy.proxy(None,'GET','/v1/health-workflows/test',None,'http://127.0.0.1:8082',httpx.MockTransport(handler))


def test_proxy_requires_storage_audience(monkeypatch):
    monkeypatch.setattr(proxy,'get_bound_principal',lambda request:SimpleNamespace(principal_kind=PrincipalKind.PERSON,audience=['renderer']))
    monkeypatch.setattr(proxy,'get_current_principal_token',lambda:'synthetic')
    with pytest.raises(HTTPException): proxy.proxy(None,'GET','/v1/health-workflows/test',None,'http://127.0.0.1:8082')

