"""Set up all routes for app"""
from attrdict import AttrDict
from aiohttp.web import HTTPFound as redirect
from aiohttp_route_decorator import RouteCollector
from aiohttp_jinja2 import template

from . import index, user, project
from .extends import error

route = RouteCollector()

def addRoutes(router):
    """Add all RouteCollectors to the given router"""
    user.route.add_to_router(router)
    project.route.add_to_router(router)
    index.route.add_to_router(router)
    route.add_to_router(router)
