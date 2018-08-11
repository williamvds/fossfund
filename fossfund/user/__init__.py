"""Controllers for /user"""
import sys

from aiohttp.web import HTTPFound as redirect
from aiohttp_route_decorator import RouteCollector
from aiohttp_jinja2 import template
from aiohttp_session import get_session
from aioauth_client import GithubClient, Bitbucket2Client#, GoogleClient

from .. import db
from ..extends import error

sys.path.append('..')

route = RouteCollector(prefix='/user')

clients = {
    'github': {
        'client': GithubClient,
        'init': {
            'client_id': 'a8f697855b0ca120e0e8',
            'client_secret': '0ecd528baefcf83f6157345cfaf0b8fcf7787c62'
        }
    },
    'bitbucket': {
        'client': Bitbucket2Client,
        'init': {
            'client_id': 'pEq8fSwMNAfYNMvXW5',
            'client_secret': 'v3kcd58EWzADtECG5VJy9Mc9FbqqmnUM'
        }
    },
    # 'google': {
    #     'client': GoogleClient,
    #     'init': {'client_key': '', 'client_secret': ''}
    # },
}

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
    if provider not in clients:
        return error(req)

    info = clients[provider]
    client = info['client'](**info['init'])
    client.params['redirect_uri'] = '%s://%s%s' \
        %(req.scheme, req.app.config.host, req.path)

    print(req.query.items())
    if client.shared_key not in req.GET:
        return redirect(client.get_authorize_url())

    await client.get_access_token(req.GET)
    user, _ = await client.user_info()
    providerID = str(user.id)

    user = await db.fetch(req.app, db.users.select() \
        .where((db.users.c.providerUserID == providerID) & (db.users.c.provider == provider)),
        one=True)

    if not user:
        user = await db.insert(req.app, db.users,
            {'provider': provider, 'providerUserID': providerID},
            db.users.c.userID)

    sesID = await db.insert(req.app, db.sessions, {'userID': user.userID}, db.sessions.c.sesID)
    ses = await get_session(req)
    ses['id'] = sesID.sesID

    return redirect('/')
