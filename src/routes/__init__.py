"""Set up all routes for app"""
from attrdict import AttrDict
from aiohttp.web import HTTPFound as redirect
from aiohttp_route_decorator import RouteCollector
from aiohttp_jinja2 import template

import db
from extends import error
from . import software

route = RouteCollector()

@route('/')
@template('index.html')
async def index(req):
    """Generate index - FAQ, #users, random projects?"""
    res = await db.fetch(req.app,
        db.software.outerjoin(db.orgs) \
        .select(use_labels=True) \
        .limit(3))

    return {'res': res}

def addRoutes(router):
    """Add all RouteCollectors to the given router"""
    software.route.add_to_router(router)
    route.add_to_router(router)
