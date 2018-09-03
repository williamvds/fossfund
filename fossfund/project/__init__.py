'''Controllers for /project'''
import os.path as path # pylint: disable = useless-import-alias
from os import makedirs
from urllib.parse import urlencode

from attrdict import AttrDict
from aiohttp.web import Request, HTTPFound as redirect, FileField
from aiohttp_route_decorator import RouteCollector
from aiohttp_jinja2 import template

from .. import database
from ..extends import error

route = RouteCollector(prefix='/project')

_STATIC_DIR = path.join(path.abspath(path.dirname(__file__)),
    '../static/project/')

if not path.exists(_STATIC_DIR):
    makedirs(_STATIC_DIR)

async def updateLogo(projID: int, data: FileField):
    '''Handle a request to update the logo of a project
    Images are stored in /static

    :param projID: ID of project to update logo
    :param data: uploaded file
    '''

    if not data.content_type.startswith('image/'):
        raise TypeError('Invalid image')

    with open(_STATIC_DIR+projID, 'wb') as logoFile:
        logoFile.write(data.file.read())

@route('')
@template('project/list.html')
async def projectList(req: Request):
    '''/project

    :contents:
        * `add project` link (/project/add)
        * list of existing projects, paginated

    todo:: sorting?
    '''
    try:
        page = min(1, int(req.query['page']))
    except (ValueError, KeyError):
        page = 1

    perPage = req.app.config.projectsPerPage
    res = await database.fetch(req.app,
        database.projects.outerjoin(database.organisations) \
        .select(use_labels=True) \
        .limit(perPage) \
        .offset((page -1) *perPage))

    return {'title': 'Projects', 'page': page, 'res': res}

@route('/add')
@template('project/form.html')
async def projectAdd(req: Request):
    '''/project/add

    :contents:
        * project form, empty
        * description of form fields
        * guidelines
    '''
    orgs = await database.fetch(req.app, database.organisations.select())

    return {'title': 'Add a project', 'orgs': orgs}

@route('/add', method='POST')
async def projectAddPost(req: Request):
    '''/project/add (POST)
    Save a new project with the POSTed information
    ``orgID`` field is ignored
    ``logo`` is set conditionally based on whether a file was uploaded

    :redirect: created project's page

    todo::
        * check permissions
        * logging/moderation
    '''
    vals = AttrDict(await req.post())
    if 'orgID' in vals and int(vals.orgID) == 0: vals.orgID = None

    if vals.logo:
        await updateLogo(vals.projID, vals.logo)
        vals.logo = True
    else:
        vals.logo = False

    res = await database.insert(req.app, database.projects, vals,
        database.projects.c.projID)

    return redirect('/project/%s'% res.projID)

@route('/edit/{projID}')
@template('project/form.html')
async def projectEdit(req: Request):
    '''/project/edit

    :contents:
        * project form, filled with existing information
        * description of form fields
        * guidelines

    todo:: logo deletion
    '''
    projID = int(req.match_info['projID'])

    async with req.app.db.acquire() as conn:
        res = await database.fetch(conn,
            database.projects.outerjoin(database.organisations) \
            .select(use_labels=True)
            .where(database.projects.c.projID == projID),
            one=True)
        orgs = await database.fetch(conn, database.organisations.select())

    return {'title': 'Editing '+ res.projects_name, 'res': res, 'orgs': orgs}

@route('/edit', method='POST')
async def projectEditPost(req: Request):
    '''/project/edit (POST)
    Update project using POSTed information
    ``logo``

    :redirect: the edited project's page

    todo::
        * check permissions
        * logging/moderation
        * logo deletion
    '''
    vals = AttrDict(await req.post())
    if 'orgID' in vals and int(vals.orgID) == 0: vals.orgID = None

    if vals.logo:
        await updateLogo(vals.projID, vals.logo)
        vals.logo = True
    else:
        del vals.logo

    # pylint complains about the `dml` parameter being unspecified
    # pylint: disable=no-value-for-parameter
    await database.run(req.app,
        database.projects.update() \
        .where(database.projects.c.projID == vals.projID) \
        .values(database.clean(vals, database.projects)))

    return redirect('/project/%s'% vals.projID)

@route('/remove/{projID}')
async def projectRemove(req: Request):
    '''/project/remove
    Delete project by ID

    :redirect: /project

    todo:: authentication
    '''
    try:
        projID = int(req.match_info['projID'])
    except ValueError:
        return error(req)

    # pylint complains about the `dml` parameter being unspecified
    # pylint: disable=no-value-for-parameter
    await database.run(req.app,
        database.projects.delete() \
        .where(database.projects.c.projID == projID))

    return redirect('/project')

@route('/{projID}')
@template('project/view.html')
async def project(req: Request):
    '''/project/(id)

    :contents:
        * project name, logo, description
        * `edit project` link (/project/edit)
        * `delete project` link (/project/remove)

    todo::
        * only show ID in debug/development mode
        * project website(s)
        * donation links
        * project parent organisation
        * estimated income?
    '''
    try:
        projID = int(req.match_info['projID'])
    except ValueError:
        return error(req)

    try:
        res = await database.fetch(req.app,
            database.projects.outerjoin(database.organisations) \
            .select(use_labels=True)
            .where(database.projects.c.projID == projID),
            one=True)
    except TypeError:
        return error(req)

    return {'title': res.projects_name, 'res': res}
