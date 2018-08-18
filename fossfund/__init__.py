"""Functions for running the application"""
import sys, os, asyncio
from base64 import urlsafe_b64decode

from aiohttp import web
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from aiohttp_session import setup as sessionSetup
from aiohttp_jinja2 import setup as jinjaSetup, request_processor
from jinja2 import FileSystemLoader as jinjaLoader

from . import db, routes
from .extends import handleError, attachUser, Config

_config = Config()

if len(sys.argv) > 1 and sys.argv[1] == 'setup':
    asyncio.get_event_loop().run_until_complete(
        db.setup(_config.db))

app = web.Application(middlewares=[handleError])
app.config = _config

routes.addRoutes(app.router)

jinjaSetup(app, loader=jinjaLoader(os.path.dirname(__file__)),
    context_processors=[request_processor],
    **app.config.jinja)

sessionSetup(app, EncryptedCookieStorage(
    urlsafe_b64decode(app.config.sessionSecret),
    cookie_name='session'))

app.middlewares.append(attachUser)
app.on_startup.append(db.attach)
app.on_shutdown.append(db.destroy)
