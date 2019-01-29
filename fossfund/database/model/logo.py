'''Implementation of RecordWithLogo model'''
import os

from .record import Record
from ...extends import AppError, AppFatalError, Config

class RecordWithLogo(Record):
    '''An extended Record which provides methods for storing and deleting logos
    '''

    #: Filesystem path under which to store logos
    _logoPathRoot: str = None

    @classmethod
    def saveLogo(cls, _id: int, logo: bytes, mime: str):
        '''Save the logo image of a project

        :param _id: ID of project to set logo of
        :param logo: Logo data to store
        :param mime: MIME type of the image
        '''
        if not mime.startswith('image/'):
            raise AppError('Logo is not an image')

        if len(logo) > Config.maxLogoSize:
            raise AppError(
                f'Logo too large - max allowed is {Config.maxLogoSize/1024}KB')

        logoPath = os.path.join(cls._logoPathRoot, str(_id))
        try:
            fd = os.open(logoPath, os.O_WRONLY|os.O_CREAT|os.O_TRUNC, 0o660)
            with os.fdopen(fd, 'wb') as logoFile:
                logoFile.write(logo)
        except IOError:
            raise AppError('Couldn\'t save logo image')

    @classmethod
    async def setLogoID(cls, _id: int, logo: bytes, mime: str):
        '''Save the logo image of a record, then update the record accordingly

        :param _id: ID of record to set logo of
        :param logo: Logo data to store
        :param mime: MIME type of the image
        '''

        cls.saveLogo(_id, logo, mime)
        await cls.updateID(_id, {'logo': True})

    @property
    def _logoPath(self):
        return os.path.join(self._logoPathRoot, str(self._id))

    def _saveCallback(self):
        '''Save the logo image once the record has been successfully saved
        '''
        super()._saveCallback()

        if self.logo and self._logoData:
            self.saveLogo(self._id, self._logoData, self._logoMime)
        elif not self.logo and os.path.isfile(self._logoPath):
            try:
                os.remove(self._logoPath)
            except OSError:
                AppFatalError('Failed to remove logo')

        self._logoData = None
        self._logoMime = None

    def setLogo(self, logo: bytes, mime: str):
        '''Save a logo image for this record

        :param logo: Logo data to store
        :param mime: MIME type of the image
        '''
        self._logoData = logo
        self._logoMime = mime
        self.logo = True

    def removeLogo(self):
        '''Remove the logo image of a record
        '''
        self.logo = False

    def __init__(self, data: dict, committed: bool = False):
        #: Whether this record has an uploaded logo
        self.logo: bool = None

        #: Logo data that will be written once this record is saved or updated
        self._logoData = None

        #: MIME type of the record's logo data
        self._logoMime = None

        super().__init__(data, committed)
