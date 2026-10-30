"""Narrow authenticated proxy for the synthetic export experience."""
import ipaddress
from urllib.parse import urlsplit

import httpx
from fastapi import HTTPException
from unison_common.principal import PrincipalKind
from unison_common.principal_middleware import get_bound_principal, get_current_principal_token


def proxy(request, method, path, body, base, transport=None):
    try:
        principal = get_bound_principal(request)
        token = get_current_principal_token()
        url = urlsplit(base)
        if (not token or principal.principal_kind != PrincipalKind.PERSON or "storage" not in principal.audience
                or not ipaddress.ip_address(url.hostname or "").is_loopback or url.scheme != "http"
                or url.username or url.password or url.query or url.fragment or url.path not in {"", "/"}):
            raise ValueError("bounded authenticated transport required")
        with httpx.Client(timeout=10, trust_env=False, follow_redirects=False, transport=transport) as client:
            response = client.request(method, base.rstrip("/")+path, json=body,
                                      headers={"Authorization": "Bearer "+token})
        if response.status_code >= 300:
            raise HTTPException(403, "This workflow is unavailable. Check consent or the supported export format.")
        return response.json()
    except HTTPException:
        raise
    except (ValueError, RuntimeError, httpx.HTTPError):
        raise HTTPException(503, "The private workflow service is unavailable. Nothing was confirmed.") from None
