"""Controllers for /user"""
import sys

import aioauth_client
from aiohttp.web import HTTPFound as redirect
from aiohttp_route_decorator import RouteCollector
from aiohttp_jinja2 import template
from aiohttp_session import get_session

from .. import db
from ..extends import error

route = RouteCollector(prefix='/user')

@route('/login')
@template('user/login.html')
async def login(_):
    """Options to log in with different services"""
    return {'title': 'Log in'}

@route('/login/{provider}')
async def oauth(req):
    """Redirect to OAuth URL or perform OAuth login"""
    if 'user' in req:
        return redirect('/')

    provider = req.match_info['provider']
    if provider not in req.app.config.oauthproviders:
        return error(req)

    info = req.app.config.oauthproviders[provider]
    client = getattr(aioauth_client, info['client'])(**info['options'])
    client.params['redirect_uri'] = '%s://%s%s' \
        %(req.scheme, req.app.config.host, req.path)

    if client.shared_key not in req.query:
        return redirect(client.get_authorize_url())

    await client.get_access_token(req.query)
    user, _ = await client.user_info()
    providerID = str(user.id)
    # print(list((k, getattr(user, k)) for k in user.__slots__))

    user = await db.fetch(req.app, db.users.select() \
        .where((db.users.c.providerUserID == providerID) \
            & (db.users.c.provider == provider)),
        one=True)

    if not user:
        user = await db.insert(req.app, db.users,
            {'provider': provider, 'providerUserID': providerID},
            db.users.c.userID)

    sesID = await db.insert(req.app, db.sessions, {'userID': user.userID},
        db.sessions.c.sesID)
    ses = await get_session(req)
    ses['id'] = sesID.sesID

    return redirect('/')
