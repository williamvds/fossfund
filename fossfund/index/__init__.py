"""Controllers for the root of the site"""
from aiohttp_route_decorator import RouteCollector
from aiohttp_jinja2 import template

from .. import database

route = RouteCollector()

@route('/')
@template('index/index.html')
async def index(req):
    """Generate index - FAQ, #users, random projects?"""
    res = await database.fetch(req.app,
        database.projects.outerjoin(database.organisations) \
        .select(use_labels=True) \
        .limit(3))

    return {'res': res}
