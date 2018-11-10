'''Controllers for /project'''
import os.path as path # pylint: disable = useless-import-alias
from urllib.parse import urlencode

from attrdict import AttrDict
from aiohttp.web import Request, HTTPFound as redirect, FileField
from aiohttp_route_decorator import RouteCollector
from aiohttp_jinja2 import template

from .. import database
from ..database.model import Project
from ..extends import AppError, error, Config

_config = Config()
route = RouteCollector(prefix='/project')

@route('')
@template('project/list.html')
async def projectList(req: Request):
    '''/project

    :contents:
        * `add project` link (/project/add)
        * list of existing projects, paginated

    todo:: sorting?
    '''
    page = int(req.query.get('page', 1))

    res = await Project.getList(page)

    return {'title': 'Projects', 'page': page, 'res': res}

@route('/add')
@template('project/form.html')
async def projectAddForm(req: Request):
    '''/project/add

    :contents:
        * project form, empty
        * description of form fields
        * guidelines
    '''
    orgs = await database.fetch(req.app, database.organisations.select())

    return {'title': 'Add a project', 'orgs': orgs}

@route('/add', method='POST')
async def projectAdd(req: Request):
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

    project = Project(vals)

    if vals.logo:
        project.setLogo(vals.logo.file.read(), vals.logo.content_type)
    else:
        project.removeLogo()

    await project.save()

    return redirect(f'/project/{project.projID}')

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
        project = await Project.findID(projID)
        orgs = await database.fetch(conn, database.organisations.select())

    return {'title': f'Editing {project.name}',
            'project': project, 'orgs': orgs}

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

    project = Project(vals, True)

    if vals.logo:
        project.setLogo(vals.logo.file.read(), vals.logo.content_type)
    else:
        project.removeLogo()

    # pylint complains about the `dml` parameter being unspecified
    # pylint: disable=no-value-for-parameter
    await project.save()

    return redirect(f'/project/{vals.projID}')

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
        raise AppError('That project does not exist')

    await Project.deleteID(projID)

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

    res = await Project.get(projID)

    if not res:
        return error(req)

    return {'title': res.name, 'project': res}
