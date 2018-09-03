'''Controllers for /'''
from aiohttp_route_decorator import RouteCollector
from aiohttp_jinja2 import template
from aiohttp.web import Request

from .. import database

route = RouteCollector()

@route('/')
@template('index/index.html')
async def index(req: Request):
    '''Website index

    :contents:
        * short introduction and description of the service
        * some screenshots or graphics
        * link to `about` page
        * a list of random projects
    '''
    res = await database.fetch(req.app,
        database.projects.outerjoin(database.organisations) \
        .select(use_labels=True) \
        .limit(3))

    return {'res': res}
