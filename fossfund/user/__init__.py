'''Controllers for /user'''
import sys

import aioauth_client
from aiohttp.web import Request, HTTPFound as redirect
from aiohttp_route_decorator import RouteCollector
from aiohttp_jinja2 import template
from aiohttp_session import get_session

from .. import database
from ..extends import error

route = RouteCollector(prefix='/user')

@route('/login')
@template('user/login.html')
async def login(req: Request):
    '''/user/login

    :contents: list of OAuth providers to log in with, linking to the respective
        /user/login/(provider) URL

    todo:: OAuth provider logos
    '''
    return {'title': 'Log in'}

@route('/login/{provider}')
async def oauth(req):
    '''/login/(provider)
    Perform authentication with given `provider`

    :redirect: external OAuth URL if unauthenticated, else /
    '''
    if 'user' in req:
        return redirect('/')

    provider = req.match_info['provider']
    if provider not in req.app.config.oauthProviders:
        return error(req)

    info = req.app.config.oauthProviders[provider]
    client = getattr(aioauth_client, info['client'])(**info['options'])
    client.params['redirect_uri'] = '%s://%s%s' \
        %(req.scheme, req.app.config.host, req.path)

    if client.shared_key not in req.query:
        return redirect(client.get_authorize_url())

    await client.get_access_token(req.query)
    user, _ = await client.user_info()
    providerID = str(user.id)

    user = await database.fetch(req.app, database.users.select() \
        .where((database.users.c.providerUserID == providerID) \
            & (database.users.c.provider == provider)),
        one=True)

    if not user:
        user = await database.insert(req.app, database.users,
            {'provider': provider, 'providerUserID': providerID},
            database.users.c.userID)

    sesID = await database.insert(req.app, database.sessions,
        {'userID': user.userID}, database.sessions.c.sesID)
    ses = await get_session(req)
    ses['id'] = sesID.sesID

    return redirect('/')
