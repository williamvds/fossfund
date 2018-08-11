"""Functions for running the application"""
import sys, os
from base64 import urlsafe_b64decode

import yaml
from aiohttp import web
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from aiohttp_session import setup as sessionSetup
from aiohttp_jinja2 import setup as jinjaSetup, request_processor
from jinja2 import FileSystemLoader as jinjaLoader
from attrdict import AttrDict

from . import db, routes
from .extends import handleError, attachUser

configFile = os.path.join(os.path.dirname(__file__), '../config.yaml')
def run(conf=configFile):
    """Start server and setup"""

    global app
    app = web.Application(middlewares=[handleError])
    app.config = loadConfig(conf)

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

def setup(conf=configFile):
    """Rebuild database tables"""
    import asyncio
    asyncio.get_event_loop().run_until_complete(
        db.setup(loadConfig(conf).db))


def loadConfig(conf):
    """Load the config from given file or default"""
    try:
        return AttrDict(yaml.load(open(conf)))
    except IOError:
        print('Execption: %s\nFailed to load conf file %s' % (sys.exc_info()[0], conf))
        sys.exit(1)

if __name__ == '__main__':
    try:
        method = locals()[sys.argv[1]]
    except (NameError, IndexError):
        method = run
    method()
else:
    run()
