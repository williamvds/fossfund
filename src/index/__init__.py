"""Controllers for the root of the site"""
from aiohttp_route_decorator import RouteCollector
from aiohttp_jinja2 import template

from .. import db

route = RouteCollector()

@route('/')
@template('index/index.html')
async def index(req):
    """Generate index - FAQ, #users, random projects?"""
    res = await db.fetch(req.app,
        db.projects.outerjoin(db.orgs) \
        .select(use_labels=True) \
        .limit(3))

    return {'res': res}
