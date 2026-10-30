"""Default-disabled bridge to an injected synthetic intent interaction only."""
import os
from fastapi import HTTPException
from unison_common.principal import PrincipalKind
from unison_common.principal_middleware import get_bound_principal


def interact(request, body):
    if os.getenv('UNISON_SYNTHETIC_INTENT') != 'true':raise HTTPException(403,'Synthetic intent disabled')
    principal=get_bound_principal(request)
    if principal.principal_kind!=PrincipalKind.PERSON:raise HTTPException(403,'Authenticated person required')
    interaction=getattr(request.app.state,'synthetic_intent_interaction',None)
    if interaction is None:raise HTTPException(503,'Synthetic interaction unavailable')
    try:
        mode=body.get('mode','visual')
        if body.get('operation')=='start' and set(body)<={'operation','mechanism','mode'}:
            return interaction.start(principal,body['mechanism'],mode)
        if body.get('operation')=='current' and set(body)<={'operation','collection','resource','mode'}:
            return interaction.current(principal,body['collection'],body['resource'],mode)
        if body.get('operation')=='respond' and set(body)<={'operation','frame','command','mode'}:
            return interaction.reply(principal,body['frame'],body['command'],mode)
        raise ValueError('unsupported interaction')
    except PermissionError:
        raise HTTPException(403,'The choice is stale or unavailable. Refresh current state before continuing.') from None
    except (ValueError,KeyError,TypeError):
        raise HTTPException(400,'Unsupported synthetic intent choice.') from None
