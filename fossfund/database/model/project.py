'''Implementation of the Project model'''
import asyncio
from typing import Awaitable, Union, List
import os

from sqlalchemy import Table

from ...extends import AppError, AppFatalError, Config
from ..schema import projects
from .record import Record, Null

_config = Config()

class Project(Record):
    '''A free and open source project that is listed on the website
    '''

    _table: Table = projects
    _primaryKey: str = 'projID'

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

    #: Whether this project has an uploaded logo
    logo: bool = None

    @staticmethod
    def saveLogo(_id: int, logo: bytes, mime: str):
        '''Save the logo image of a project

        :param _id: ID of project to set logo of
        :param logo: Logo data to store
        :param mime: MIME type of the image
        '''
        if not mime.startswith('image/'):
            raise AppError('Logo is not an image')

        if len(logo) > _config.maxLogoSize:
            raise AppError(
                f'Logo too large - max allowed is {_config.maxLogoSize/1024}KB')

        logoPath = os.path.join(_config.projectLogoDir, str(_id))
        try:
            fd = os.open(logoPath, os.O_WRONLY|os.O_CREAT|os.O_TRUNC, 0o660)
            with os.fdopen(fd, 'wb') as logoFile:
                logoFile.write(logo)
        except IOError:
            raise AppError('Couldn\'t save logo image')

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
            .limit(_config.projectsPerPage) \
            .offset((page -1) *_config.projectsPerPage))

        if not res:
            if page > 1:
                raise AppFatalError(f'Page {page} does not exist')
            else:
                raise AppError('There are no matching projects')

        return res

    @classmethod
    async def setLogoID(cls, _id: int, logo: bytes, mime: str):
        '''Save the logo image of a project, then update the record accordingly

        :param _id: ID of project to set logo of
        :param logo: Logo data to store
        :param mime: MIME type of the image
        '''

        cls.saveLogo(_id, logo, mime)
        await cls.updateID(_id, {'logo': True})

    def __init__(self, data: dict, committed: bool = False):
        super().__init__(data, committed)

        #: Logo data that will be written once this project is saved or updated
        self._logoData = None

        #: MIME type of the project logo data
        self._logoMime = None

    @property
    def _logoPath(self):
        return os.path.join(_config.projectLogoDir, str(self._id))

    def _saveCallback(self):
        '''Save the logo image once the project has been successfully saved
        '''
        super()._saveCallback()

        if self.logo and self._logoData:
            self.saveLogo(self._id, self._logoData, self._logoMime)
        elif not self.logo and os.path.isfile(self._logoPath):
            try:
                os.remove(self._logoPath)
            except OSError:
                AppFatalError('Failed to remove project logo')

        self._logoData = None
        self._logoMime = None

    def setLogo(self, logo: bytes, mime: str):
        '''Save a logo image for this project

        :param logo: Logo data to store
        :param mime: MIME type of the image
        '''
        self._logoData = logo
        self._logoMime = mime
        self.logo = True

    def removeLogo(self):
        '''Remove the logo image of a project
        '''
        self.logo = False

    @classmethod
    async def findID(cls, value: int) -> Union['Project', None]:
        return await cls._findID(value)

__all__ = [
    'Project',
]
