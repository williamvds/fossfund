'''Implementation of the Organisation model'''
from typing import Awaitable, Union, List

from sqlalchemy import Table

from ...extends import AppError, AppFatalError, Config
from ..schema import organisations
from .logo import RecordWithLogo

class Organisation(RecordWithLogo):
    '''A sponsoring organisation that supports the development of projects
    '''

    _table: Table = organisations
    _primaryKey: str = 'orgID'
    _logoPathRoot: str = Config.organisationLogoDir

    @classmethod
    async def get(cls, value: int) -> Awaitable[Union['Organisation', None]]:
        '''Find a record by its ID

        :returns: found record, or :type:`NoneType`
        '''
        return await cls._findID(value)

    @classmethod
    async def getList(cls, page: int) -> List['Organisation']:
        '''Get the list of organisations

        :param page: offset into the organisations list to retreive

        todo:: sorting methods
        '''
        if page < 1:
            raise AppFatalError(f'Invalid page: {page}')

        res = await cls._find(
            cls._table.select() \
            .limit(Config.projectsPerPage) \
            .offset((page - 1) * Config.organisationsPerPage))

        if not res:
            if page > 1:
                raise AppFatalError(f'Page {page} does not exist')
            else:
                raise AppError('There are no matching organisations')

        return res

    def __init__(self, data: dict, committed: bool = False):
        #: Unique ID
        self.orgID: int = None

        #: Name
        self.name: str = None

        #: Description
        self.desc: str = None

        super().__init__(data, committed)
