'''Implementation of the Project model'''
from typing import Awaitable, Union, List
import os

from sqlalchemy import Table

from ...extends import AppError, AppFatalError, Config
from ..schema import projects
from .logo import RecordWithLogo
from .record import Null

class Project(RecordWithLogo):
    '''A free and open source project that is listed on the website
    '''

    _table: Table = projects
    _primaryKey: str = 'projID'
    _logoPathRoot: str = Config.projectLogoDir

    #: Unique ID of the project, primary key
    projID: int = None

    #: Unique ID of the project's organisation, secondary key, optional
    orgID: Union[int, Null] = None

    #: Name
    name: str = None

    #: Description
    desc: str = None

    #: URL to the project's own website
    homepage: str = None

    @classmethod
    async def get(cls, value: int) -> Awaitable[Union['Project', None]]:
        '''Find a project by its ID

        :returns: found project, or :type:`NoneType`
        '''
        return await cls._findID(value)

    @classmethod
    async def getList(cls, page: int) -> List['Project']:
        '''Get the list of projects

        :param page: offset into the projects list to retreive

        todo:: sorting methods
        '''
        if page < 1:
            raise AppFatalError(f'Invalid page: {page}')

        res = await cls._find(
            projects.select() \
            .limit(Config.projectsPerPage) \
            .offset((page -1) *Config.projectsPerPage))

        if not res:
            if page > 1:
                raise AppFatalError(f'Page {page} does not exist')
            else:
                raise AppError('There are no matching projects')

        return res

    @classmethod
    async def findID(cls, value: int) -> Union['Project', None]:
        return await cls._findID(value)

__all__ = [
    'Project',
]
