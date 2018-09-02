"""Functions for running the application"""
import sys, os, asyncio
from base64 import urlsafe_b64decode

from aiohttp import web
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from aiohttp_session import setup as sessionSetup
from aiohttp_jinja2 import setup as jinjaSetup, request_processor
from jinja2 import FileSystemLoader as jinjaLoader

from . import database, routes
from .extends import handleError, attachUser, Config

_config = Config()

async def databaseSetup():
    '''Run database setup'''
    db = await database.create(_config.db)
    await database.setup(await db.acquire())
    await database.destroy(db)

if len(sys.argv) > 1 and sys.argv[1] == 'setup':
    asyncio.get_event_loop().run_until_complete(databaseSetup())

app = web.Application(middlewares=[handleError])
app.config = _config

routes.addRoutes(app.router)

jinjaSetup(app, loader=jinjaLoader(os.path.dirname(__file__)),
    context_processors=[request_processor],
    **app.config.jinja)

sessionSetup(app, EncryptedCookieStorage(
    urlsafe_b64decode(app.config.sessionSecret),
    cookie_name='session'))

async def attachDatabase(target: web.Application):
    '''Attach a database engine to the given application

    :param target: application to attach database to
    '''
    target.db = await database.create(_config.db)

app.middlewares.append(attachUser)
app.on_startup.append(attachDatabase)
app.on_shutdown.append(lambda app: database.destroy(app.db))
