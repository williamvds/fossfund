"""Routes for /software"""
from attrdict import AttrDict
from aiohttp.web import HTTPFound as redirect
from aiohttp_route_decorator import RouteCollector
from aiohttp_jinja2 import template

import db
from extends import error

route = RouteCollector(prefix='/software')

@route('')
@template('softwareList.html')
async def softwareList(req):
    """List of software, paginated"""
    try:
        page = min(1, int(req.query['page']))
    except (ValueError, KeyError):
        page = 1

    perPage = req.app.config.softwaresPerPage
    res = await db.fetch(req.app,
        db.software.outerjoin(db.orgs) \
        .select(use_labels=True) \
        .limit(perPage) \
        .offset((page -1) *perPage))

    return {'title': 'Software', 'page': page, 'res': res}

@route('/add')
@template('softwareForm.html')
async def softwareAdd(req):
    """Render software form"""
    orgs = await db.fetch(req.app, db.orgs.select())

    return {'title': 'Add software', 'orgs': orgs}

@route('/add', method='POST')
async def softwareAddPost(req):
    """Insert, validate, then redirect to new software's page"""
    vals = AttrDict(await req.post())
    if 'orgID' in vals and int(vals.orgID) == 0: vals.orgID = None
    res = await db.insert(req.app, db.software, vals, db.software.c.softID)

    return redirect('/software/%s'% res.softID)

@route('/edit/{softID}')
@template('softwareForm.html')
async def softwareEdit(req):
    """Render software form with existing info"""
    try:
        softID = int(req.match_info['softID'])
    except ValueError:
        return error(req)

    try:
        async with req.app.db.acquire() as c:
            res = await db.fetch(c,
                db.software.outerjoin(db.orgs) \
                .select(use_labels=True)
                .where(db.software.c.softID == softID),
                one=True)
            orgs = await db.fetch(c, db.orgs.select())
    except TypeError:
        # software record does not exist
        return error(req)

    return {'title': 'Editing '+ res.software_name, 'res': res, 'orgs': orgs}

@route('/edit', method='POST')
async def softwareEditPost(req):
    """Update, validate, then redirect to edited software's page"""
    # TODO auth and edit moderation
    vals = AttrDict(await req.post())
    if 'orgID' in vals and int(vals.orgID) == 0: vals.orgID = None
    res = await db.run(req.app,
        db.software.update() \
        .where(db.software.c.softID == vals.softID) \
        .values(db.clean(vals, db.software)))

    return redirect('/software/%s'% vals.softID)

@route('/remove/{softID}')
async def softwareRemove(req):
    """Delete software, redirect to /software"""
    # TODO authenticate
    try:
        softID = int(req.match_info['softID'])
    except ValueError:
        return error(req)
    await db.run(req.app,
        db.software.delete() \
        .where(db.software.c.softID == softID))

    return redirect('/software')

@route('/{softID}')
@template('software.html')
async def software(req):
    """Individual software page - all info, organisation info, income?"""
    try:
        softID = int(req.match_info['softID'])
    except ValueError:
        return error(req)

    try:
        res = await db.fetch(req.app,
            db.software.outerjoin(db.orgs) \
            .select(use_labels=True)
            .where(db.software.c.softID == softID),
            one=True)
    except TypeError:
        return error(req)

    return {'title': res.software_name, 'res': res}
