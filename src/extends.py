"""Utility classes & functions, including extensions to other libraries"""
from http.client import responses
from aiohttp.web import HTTPException
from aiohttp_jinja2 import render_template as render

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

def error(req, code=404):
    """Render error.html giving standard description"""
    res = render('error.html', req, {'code': code, 'desc': responses[code]})
    res.set_status(code)
    return res
