"""Set up all routes for app"""
from aiohttp_route_decorator import RouteCollector

from . import index, user, project

route = RouteCollector()

def addRoutes(router):
    """Add all RouteCollectors to the given router"""
    user.route.add_to_router(router)
    project.route.add_to_router(router)
    index.route.add_to_router(router)
    route.add_to_router(router)
