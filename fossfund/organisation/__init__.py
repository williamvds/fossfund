'''Controllers for /organisation'''
from attrdict import AttrDict
from aiohttp.web import Request, HTTPFound as redirect
from aiohttp_route_decorator import RouteCollector
from aiohttp_jinja2 import template

from .. import database
from ..database.model import Organisation
from ..extends import AppError, error, Config

route = RouteCollector(prefix='/organisation')

@route('')
@template('organisation/list.html')
async def projectList(req: Request):
    '''/organisation

    :contents:
        * `add organisation` link (/organisation/add)
        * list of existing organisations, paginated

    todo:: sorting?
    '''
    page = int(req.query.get('page', 1))

    res = await Organisation.getList(page)

    return {'title': 'Organisations', 'page': page, 'res': res}

@route('/add')
@template('organisation/form.html')
async def projectAddForm(req: Request):
    '''/organisation/add

    :contents:
        * organisation form, empty
    '''
    return {'title': 'Add an organisation'}

@route('/add', method='POST')
async def projectAdd(req: Request):
    '''/organisation/add (POST)
    Save a new organisation with the POSTed information
    ``orgID`` field is ignored
    ``logo`` is set conditionally based on whether a file was uploaded

    :redirect: created organisation's page

    todo::
        * check permissions
        * logging/moderation
    '''
    vals = AttrDict(await req.post())
    if 'orgID' in vals and int(vals.orgID) == 0: vals.orgID = None

    org = Organisation(vals)

    if vals.logo:
        org.setLogo(vals.logo.file.read(), vals.logo.content_type)
    else:
        org.removeLogo()

    await org.save()

    return redirect(f'/organisation/{org.orgID}')

@route('/edit/{orgID}')
@template('organisation/form.html')
async def projectEditForm(req: Request):
    '''/organisation/edit

    :contents:
        * organisation form, filled with existing information
        * description of form fields
        * guidelines

    todo:: logo deletion
    '''
    orgID = int(req.match_info['orgID'])
    org = await Organisation.get(orgID)

    return {'title': f'Editing {org.name}',
            'org': org}

@route('/edit', method='POST')
async def projectEdit(req: Request):
    '''/organisation/edit (POST)
    Update organisation using POSTed information
    ``logo``

    :redirect: the edited organisation's page

    todo::
        * check permissions
        * logging/moderation
        * logo deletion
    '''
    vals = AttrDict(await req.post())
    if 'orgID' in vals and int(vals.orgID) == 0: vals.orgID = None

    org = Organisation(vals, True)

    if 'removeLogo' in vals:
        org.removeLogo()
    elif vals.logo:
        org.setLogo(vals.logo.file.read(), vals.logo.content_type)
    else:
        org.logo = None

    # pylint complains about the `dml` parameter being unspecified
    # pylint: disable=no-value-for-parameter
    await org.save()

    return redirect(f'/organisation/{vals.orgID}')

@route('/remove/{orgID}')
async def projectRemove(req: Request):
    '''/organisation/remove
    Delete organisation by ID

    :redirect: /organisation

    todo:: authentication
    '''
    try:
        orgID = int(req.match_info['orgID'])
    except ValueError:
        raise AppError('That organisation does not exist')

    await Organisation.deleteID(orgID)

    return redirect('/organisation')

@route('/{orgID}')
@template('organisation/view.html')
async def organisation(req: Request):
    '''/organisation/(id)

    :contents:
        * organisation name, logo, description
        * `edit organisation` link (/organisation/edit)
        * `delete organisation` link (/organisation/remove)

    todo::
        * only show ID in debug/development mode
        * organisation website(s)
        * donation links
        * estimated income?
    '''
    try:
        orgID = int(req.match_info['orgID'])
    except ValueError:
        return error(req)

    res = await Organisation.get(orgID)

    if not res:
        return error(req)

    return {'title': res.name, 'org': res}
