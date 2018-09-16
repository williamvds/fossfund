'''Contains the classes used that provide the data model and interface classes
for interacting with database'''
import asyncio
from typing import Any, Awaitable, Dict, List, Set, Union

import sqlalchemy
from aiopg.sa import Engine, SAConnection

from ..extends import Config, Singleton
from .schema import (
    projects, organisations, urls, groups, memberships, users, sessions
)
from . import create

config = Config()

class Null(Singleton):
    '''Represents the value NULL in a :class:`Record`
    '''
    pass

#: A static object representing the value NULL in a :class:`Record`
NULL = Null()

#: The type of a query that can be executed
# TODO: find base class of SQLAlchemy queries, replace Any
Query = Union['str', Any]

class InvalidRecordError(Exception):
    '''Raised when an instance of a :class:`Record` is invalid, i.e. its primary
    key is None
    '''
    pass

class InvalidStateError(Exception):
    '''Raised when a :class:`Record` is in an invalid state when an operation is
    attempted.
    :meth:`~Record.save` on a record that has not been :attr:`~Record.committed`
    '''
    pass

class NotUniqueError(Exception):
    '''Raised when a strict find-one query (through :meth:`Record._findOne`)
    returns more than one result
    '''
    pass

class OperationPendingError(Exception):
    '''Raised when a :meth:`~Record.save`, :meth:`~Record.update`,
    or :meth:`~Record.delete` is attempted while there is already another
    ongoing operation
    '''
    pass

class Record:
    '''A representation of a database record
    Uses the given table to dynamically set properties which correspond to the
    fields that are contained by the record.
    :type:`None` is used to indicate a field has not been queried.
    :data:`NULL` is used to represent a field's value is NULL.

    When :meth:`save`ing creates a new record in the database
    (i.e. :attr:`committed` is ``False``)
    does not exist in the database)
    When a record is :meth:`save`ed, any field properties that are None are
    set to :data:`NULL`

    '''
    #: Database :class:`~aiopg.sa.Engine` used for queries
    _engine: Engine = None

    #: Name of the primary key column in the table
    _primaryKey: str = None

    #: Table that this record is a part of
    _table: sqlalchemy.Table = None

    @staticmethod
    async def _runQuery(query: Query, conn: SAConnection = None) \
        -> Awaitable[Dict[str, Any]]:
        '''Execute a query

        :param query: query to execute
        :param conn: existing connection to use
        :returns: query results
        '''
        if not Record._engine:
            Record._engine = await create(config.db)

        if conn:
            return await conn.execute(query)

        async with Record._engine.acquire() as conn:
            return await conn.execute(query)

    @classmethod
    async def _find(cls: 'Record', query: Query) \
        -> Awaitable[Union[List['Record'], None]]:
        '''Find and return an existing record by primary key

        :param query: query to execute
        :returns: results of the query, or None if there were no results
        '''
        # TODO: work out how to handle join queries - dicts?
        res = await cls._runQuery(query)

        return [cls(row, True) if row else row async for row in res]

    @classmethod
    async def _findOne(cls: 'Record', query: Query, strict: bool = False) \
        -> Awaitable[Union['Record', None]]:
        '''Find and return a single existing record

        :param query: query to execute
        :param strict: if True, fail if more than one result is found

        :returns: results of the query, or None if there were no results
        '''
        res = await cls._find(query)

        if strict and len(res) > 1:
            raise NotUniqueError

        return res[0]

    def _getData(self, onlyDirty: bool = False) -> dict:
        '''
        :param dirty: whether only modified fields should be returned
        :returns: data contained by this record
        '''
        data = {}
        cols = self._dirtyFields if onlyDirty \
            else [col.name for col in self._table.columns]

        for col in cols:
            data[col] = getattr(self, col, None)

        return data

    @property
    def _data(self) -> dict:
        '''
        :returns: data contained in this record
        '''
        return self._getData()

    @property
    def _dirty(self) -> dict:
        '''
        :returns: modified data contained in this record
        '''
        return self._getData(True)

    async def save(self) -> Awaitable:
        '''Save the record represented by this object in the database.
        Existing records are updated, if one already exists it is updated.
        Upon success, :attr:`committed` is set to True, and any fields that are
        None are set to :data:`NULL`

        :returns: Future which performs operation and updates committed status
        '''
        if self._primaryKey is None:
            raise InvalidRecordError

        elif not self._future is None:
            raise OperationPendingError

        elif self.committed:
            raise InvalidStateError

        self._future = asyncio.Future()
        asyncio.ensure_future(
            self._runQuery(
                self._table.insert(values=self._data) \
                .returning(self._primaryKey)))
        self._future.add_done_callback(self._saveCallback)

        return self._future

    def _saveCallback(self, future: asyncio.Future):
        '''Called after a :meth:`save` operation has been successfully completed
        '''
        for col in self._table.columns:
            if getattr(self, col.name, None) is None:
                setattr(self, col.name, NULL)
        self.committed = True
        self._future = None

    async def update(self) -> Awaitable:
        '''Update the record represented by this object in the database.
        Fails if the record is not already in the database'''
        if self._primaryKey is None:
            raise InvalidRecordError

        elif not self._future is None:
            raise OperationPendingError

        elif not self.committed:
            raise InvalidStateError

        elif not self.dirty:
            return asyncio.Future()

        self._future = asyncio.Future()
        asyncio.ensure_future(
            self._runQuery(
                self._table.update(values=self._dirty) \
                .where(self._table.c[self._primaryKey] \
                    == getattr(self, self._primaryKey))))
        self._future.add_done_callback(self._updateCallback)

        return self._future

    def _updateCallback(self, future: asyncio.Future):
        '''Called after an :meth:`update` operation has successfully completed
        '''
        self._dirtyFields.clear()
        self.dirty = False
        self._future = None

    async def delete(self) -> Awaitable:
        '''Delete the record represented by this object from the database.
        After successful deletion, all fields of this record are set to None
        '''
        if not self.committed:
            raise InvalidStateError

        self._future = asyncio.Future()
        asyncio.ensure_future(
            self._runQuery(
                self._table.delete() \
                .where(self._table.c[self._primaryKey] \
                    == getattr(self, self._primaryKey))))
        self._future.add_done_callback(self._deleteCallback)

        return self._future

    def _deleteCallback(self, future: asyncio.Future):
        '''Called after an :meth:`delete` operation has successfully completed
        '''
        for col in self._table.columns:
            setattr(self, col.name, None)
        self._future = None

    def __init__(self, data: Dict[str, Any] = None, committed: bool = False):
        '''Create a record object

        :param data: map field names onto the respective values the record
            should use for them.
            Missing fields are left as :type:`None` and will not be sent in
            queries.
            Fields that do not exist in the table are not used.
        :param committed: whether this record already exists in the database
        '''
        #: Set of fields that have been modified. Used to only send modified
        #: data upon updating
        self._dirtyFields: Set[str] = set()

        #: Reference to an ongoing asyncio request. Used to prevent simultaneous
        #: queries for the same record object
        self._future: asyncio.Future = None

        #: Whether this record exists in the database
        self.committed = committed

        #: Whether this record has been modified from the one in the database.
        #: Implies :attr:`committed`
        self.dirty = False

        if data:
            for (name, typ) in [(c.name, c.type) for c in self._table.columns]:
                if name not in data:
                    continue
                val = data[name]
                setattr(self, name, typ.python_type(val) if val else val)

class Project(Record):
    '''A free and open source project that is listed on the website
    '''

    _table: sqlalchemy.Table = projects

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

__all__ = [
    'InvalidRecordError',
     'NULL',
     'Project'
]
