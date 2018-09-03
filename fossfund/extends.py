'''Utility classes & functions, including extensions to other libraries'''
import os, sys
from http.client import responses
from typing import NewType, Callable

import yaml
from aiohttp.web import Request, HTTPException, middleware
from aiohttp_jinja2 import render_template as render
from aiohttp_session import get_session
from attrdict import AttrDict

from . import database

RequestHandler = NewType('RequestHandler', Callable[[Request], None])

@middleware
async def handleError(req: str, handler: RequestHandler):
    '''Catch raised :class:`~aiohttp.web.HTTPException`s
    Codes 404 and 500 errors are shown to the user, others are raised

    :param req: request being processed
    :param handler: next function to call in the controller chain
    '''
    try: res = await handler(req)
    except HTTPException as ex:
        res = ex
        if res.status not in [404, 500]: raise
    if res.status in [404, 500]:
        return error(req, res.status)

    return res

@middleware
async def attachUser(req: Request, handler: RequestHandler):
    '''An aiohttp request middleware which attaches user information if
    authenticated

    :param req: request being processed
    :param handler: next function to call in the controller chain
    '''
    ses = await get_session(req)
    if 'id' in ses:
        req.user = await database.getUser(req.app, ses['id'])

    return await handler(req)

def error(req: Request, code: int = 404):
    '''Render error.html, giving standard description for the given error code
    from :py:attr:`http.client.responses`

    :param req: The request to handle
    :param code: The HTTP status code to render
    '''
    res = render('templates/error.html', req,
        {'code': code, 'desc': responses[code]})
    res.set_status(code)
    return res

class Singleton():
    '''A singleton metaclass

    :author: Adam Forsyth
    :source: https://stackoverflow.com/a/6798042
    '''
    _instances = {}

    def __new__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__new__(cls, *args, **kwargs)
        return cls._instances[cls]

class Config(Singleton):
    '''A singleton config class from which all configuration values can be
    accessed as attributes
    '''
    #: The internal dictionary which stores the configuration values
    _dict: AttrDict = None

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
