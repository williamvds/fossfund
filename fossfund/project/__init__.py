"""Controllers for /project"""
import os.path as path
from os import makedirs
from urllib.parse import urlencode

from attrdict import AttrDict
from aiohttp.web import HTTPFound as redirect
from aiohttp_route_decorator import RouteCollector
from aiohttp_jinja2 import template

from .. import db
from ..extends import error

route = RouteCollector(prefix='/project')

_STATIC_DIR = path.join(path.abspath(path.dirname(__file__)),
    '../static/project/')

if not path.exists(_STATIC_DIR):
    makedirs(_STATIC_DIR)

async def updateLogo(projID, data):
    """Create/update the logo, storing it in /static"""

    if not data.content_type.startswith('image/'):
        raise TypeError('Invalid image')

    with open(_STATIC_DIR+projID, 'wb') as logoFile:
        logoFile.write(data.file.read())

@route('')
@template('project/list.html')
async def projectList(req):
    """List of projects, paginated"""
    try:
        page = min(1, int(req.query['page']))
    except (ValueError, KeyError):
        page = 1

    perPage = req.app.config.projectsPerPage
    res = await db.fetch(req.app,
        db.projects.outerjoin(db.orgs) \
        .select(use_labels=True) \
        .limit(perPage) \
        .offset((page -1) *perPage))

    return {'title': 'Projects', 'page': page, 'res': res}

@route('/add')
@template('project/form.html')
async def projectAdd(req):
    """Render project form"""
    orgs = await db.fetch(req.app, db.orgs.select())

    return {'title': 'Add a project', 'orgs': orgs}

@route('/add', method='POST')
async def projectAddPost(req):
    """Insert, validate, then redirect to new project's page"""
    vals = AttrDict(await req.post())
    if 'orgID' in vals and int(vals.orgID) == 0: vals.orgID = None
    res = await db.insert(req.app, db.projects, vals, db.projects.c.projID)

    return redirect('/project/%s'% res.projID)

@route('/edit/{projID}')
@template('project/form.html')
async def projectEdit(req):
    """Render project form with existing info"""
    try:
        projID = int(req.match_info['projID'])
    except ValueError:
        return error(req)

    try:
        async with req.app.db.acquire() as conn:
            res = await db.fetch(conn,
                db.projects.outerjoin(db.orgs) \
                .select(use_labels=True)
                .where(db.projects.c.projID == projID),
                one=True)
            orgs = await db.fetch(conn, db.orgs.select())
    except TypeError:
        # project record does not exist
        return error(req)

    return {'title': 'Editing '+ res.projects_name, 'res': res, 'orgs': orgs}

@route('/edit', method='POST')
async def projectEditPost(req):
    """Update, validate, then redirect to edited project's page"""
    # TODO auth and edit moderation
    vals = AttrDict(await req.post())
    if 'orgID' in vals and int(vals.orgID) == 0: vals.orgID = None

    if vals.logo:
        try:
            await updateLogo(vals.projID, vals.logo)
            vals.logo = True
        except Exception as exc:
            error(req)

    # pylint complains about the `dml` parameter being unspecified
    # pylint: disable=no-value-for-parameter
    await db.run(req.app,
        db.projects.update() \
        .where(db.projects.c.projID == vals.projID) \
        .values(db.clean(vals, db.projects)))

    return redirect('/project/%s'% vals.projID)

@route('/remove/{projID}')
async def projectRemove(req):
    """Delete project, redirect to /projects"""
    # TODO authenticate
    try:
        projID = int(req.match_info['projID'])
    except ValueError:
        return error(req)

    # pylint complains about the `dml` parameter being unspecified
    # pylint: disable=no-value-for-parameter
    await db.run(req.app,
        db.projects.delete() \
        .where(db.projects.c.projID == projID))

    return redirect('/project')

@route('/{projID}')
@template('project/view.html')
async def project(req):
    """Individual project page - all info, organisation info, income?"""
    try:
        projID = int(req.match_info['projID'])
    except ValueError:
        return error(req)

    try:
        res = await db.fetch(req.app,
            db.projects.outerjoin(db.orgs) \
            .select(use_labels=True)
            .where(db.projects.c.projID == projID),
            one=True)
    except TypeError:
        return error(req)

    return {'title': res.projects_name, 'res': res}
