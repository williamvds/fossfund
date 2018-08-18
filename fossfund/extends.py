"""Utility classes & functions, including extensions to other libraries"""
import yaml, os, sys
from http.client import responses

from aiohttp.web import HTTPException
from aiohttp_jinja2 import render_template as render
from aiohttp_session import get_session
from attrdict import AttrDict

from . import db

async def handleError(_, handle):
    """Catch 404 and 500 errors, render error.html"""
    async def middleware(req):
        """Middleware function"""
        try: res = await handle(req)
        except HTTPException as ex:
            res = ex
            if res.status not in [404, 500]: raise
        if res.status in [404, 500]:
            return error(req, res.status)

        return res

    return middleware

async def attachUser(_, handle):
    """Attach user information to requests if request is authenticated"""
    async def middleware(req):
        """Middleware function"""
        ses = await get_session(req)
        if 'id' in ses:
            req.user = await db.getUser(req.app, ses['id'])

        return await handle(req)

    return middleware

def error(req, code=404):
    """Render error.html giving standard description"""
    res = render('templates/error.html', req,
        {'code': code, 'desc': responses[code]})
    res.set_status(code)
    return res

class Singleton(object):
    """A singleton metaclass, using agf's solution from
    https://stackoverflow.com/a/6798042"""
    _instances = {}

    def __new__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__new__(cls, *args, **kwargs)
        return cls._instances[cls]

class Config(Singleton):
    _dict = None

    def __init__(self):
        fname = os.path.join(os.path.dirname(__file__), '../config.yaml')

        try:
            self._dict = AttrDict(yaml.load(open(fname)))
        except IOError:
            print('Execption: %s\nFailed to load configuration file %s' \
                % (sys.exc_info()[0], fname))
            sys.exit(1)

    def __getattr__(self, name):
        return getattr(self._dict, name)
