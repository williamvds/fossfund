'''Functions for running the application'''
import sys, os, asyncio, yaml
from base64 import urlsafe_b64decode

from aiohttp import web
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from aiohttp_session import setup as sessionSetup
from aiohttp_jinja2 import setup as jinjaSetup, request_processor
from jinja2 import FileSystemLoader as jinjaLoader

from . import database, routes
from .extends import handleError, attachUser, Config

async def databaseSetup():
    '''Run database setup'''
    db = await database.create(Config.db)
    await database.setup(await db.acquire())
    await database.destroy(db)

async def attachDatabase(target: web.Application):
    '''Attach a database engine to the given application

    :param target: application to attach database to
    '''
    target.db = await database.create(Config.db)

if len(sys.argv) > 1 and sys.argv[1] == 'setup':
    asyncio.get_event_loop().run_until_complete(databaseSetup())

# TODO extend web.Application
app = web.Application()
app.middlewares.append(handleError)

jinjaEnv = jinjaSetup(app, loader=jinjaLoader(os.path.dirname(__file__)),
    context_processors=[request_processor],
    **Config.jinja)

jinjaEnv.globals['Config'] = Config

sessionSetup(app, EncryptedCookieStorage(
    urlsafe_b64decode(Config.sessionSecret),
    cookie_name='session'))

app.middlewares.append(attachUser)
app.on_startup.append(attachDatabase)
app.on_shutdown.append(lambda app: database.destroy(app.db))
routes.addRoutes(app.router)
