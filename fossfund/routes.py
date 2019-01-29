'''Handles routing for the application'''
from aiohttp.web import UrlDispatcher

from . import index, user, project, organisation

def addRoutes(router: UrlDispatcher):
    '''Add the :class:`UrlDispatcher` routers of the website submodules to given
    router

    :param router: The router to add all routes to
    '''
    user.route.add_to_router(router)
    project.route.add_to_router(router)
    organisation.route.add_to_router(router)
    index.route.add_to_router(router)
