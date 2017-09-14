"""Routes for OAuth login /login"""
from aiohttp.web import HTTPFound as redirect, Response # TODO remove Response
from aiohttp_route_decorator import RouteCollector
from aiohttp_jinja2 import template
from aioauth_client import GithubClient#, Bitbucket2Client, GoogleClient

from extends import error
route = RouteCollector(prefix='/login')

clients = {
    'github': {
        'client': GithubClient,
        'init': {
            'client_id': 'a8f697855b0ca120e0e8',
            'client_secret': '0ecd528baefcf83f6157345cfaf0b8fcf7787c62'
        }
    },
    # 'bitbucket': {
    #     'client': Bitbucket2Client,
    #     'init': {'consumer_key': '', 'consumer_secret': ''}
    # },
    # 'google': {
    #     'client': GoogleClient,
    #     'init': {'client_key': '', 'client_secret': ''}
    # },
}

@route('')
@template('login.html')
async def login(_):
    """Options to log in with different services"""
    return {'title': 'Log in'}

@route('/{provider}')
async def oauth(req):
    """Perform OAuth login"""
    provider = req.match_info['provider']
    if provider not in clients:
        return error(req)

    info = clients[provider]
    client = info['client'](**info['init'])
    client.params['redirect_uri'] = 'http://lvh.me%s' %req.path

    if client.shared_key not in req.GET:
        return redirect(client.get_authorize_url())

    await client.get_access_token(req.GET)
    user, _ = await client.user_info()
    text = (
        "<a href='/'>back</a><br/><br/>"
        "<ul>"
        "<li>ID: %(id)s</li>"
        "<li>Username: %(username)s</li>"
        "<li>First, last name: %(first_name)s, %(last_name)s</li>"
        "<li>Gender: %(gender)s</li>"
        "<li>Email: %(email)s</li>"
        "<li>Link: %(link)s</li>"
        "<li>Picture: %(picture)s</li>"
        "<li>Country, city: %(country)s, %(city)s</li>"
        "</ul>"
    ) % user.__dict__

    return Response(text=text, content_type='text/html')
