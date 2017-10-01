"""Functions for running the application"""
import sys
from base64 import urlsafe_b64decode

import yaml
from aiohttp import web
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from aiohttp_session import setup as sessionSetup
from aiohttp_jinja2 import setup as jinjaSetup, request_processor
from jinja2 import FileSystemLoader as jinjaLoader
from attrdict import AttrDict

import db, routes
from extends import handleError, attachUser

def run(conf='../config.yaml'):
    """Start server and setup"""

    global app
    app = web.Application(middlewares=[handleError])
    app.config = loadConfig(conf)

    routes.addRoutes(app.router)

    jinjaSetup(app, loader=jinjaLoader('templates'), context_processors=[request_processor],
        **app.config.jinja)

    sessionSetup(app, EncryptedCookieStorage(
        urlsafe_b64decode(app.config.sessionSecret),
        cookie_name='session'))

    app.middlewares.append(attachUser)
    app.on_startup.append(db.attach)
    app.on_shutdown.append(db.destroy)

def setup(conf='../config.yaml'):
    """Rebuild database tables"""
    import asyncio
    asyncio.get_event_loop().run_until_complete(
        db.setup(loadConfig(conf).db))


def loadConfig(conf='../config.yaml'):
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
