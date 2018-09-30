'''Implementation of the Record model'''
import asyncio
from typing import Any, Awaitable, Dict, List, Union
from pprint import pformat

from sqlalchemy import Table
from aiopg.sa import Engine, SAConnection

from ...extends import Config, Singleton
from .. import create

config = Config()

class Null(metaclass=Singleton):
    '''Represents the value NULL in a :class:`Record`
    '''
    def __repr__(self):
        return 'NULL'

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

#: A static object representing the value NULL in a :class:`Record`
NULL = Null()

#: The type of a query that can be executed
# TODO: find base class of SQLAlchemy queries, replace Any
Query = Union['str', Any]

class Record:
    '''A representation of a database record
    Uses the given table to dynamically set properties which correspond to the
    fields that are contained by the record.
    :type:`NoneType` is used to indicate a field has not been queried.
    :data:`NULL` is used to represent a field's value is NULL.

    When :meth:`save`ing creates a new record in the database
    (i.e. :attr:`committed` is ``False``)
    does not exist in the database)
    When a record is :meth:`save`ed, any field properties that are
    :type:`NoneType` are set to :data:`NULL`

    '''
    #: Database :class:`~aiopg.sa.Engine` used for queries
    _engine: Engine = None

    #: Name of the primary key column in the table
    _primaryKey: str = None

    #: Table that this record is a part of
    _table: Table = None

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
        '''Find and return an existing record

        :param query: query to execute
        :returns: results of the query, or None if there were no results
        '''
        # TODO: work out how to handle join queries - dicts?
        res = await cls._runQuery(query)

        return [cls(row, True) if row else row async for row in res]

    @classmethod
    async def _findOne(cls: 'Record', query: Query, strict: bool = False) \
        -> Union['Record', None]:
        '''Find and return a single existing record

        :param query: query to execute
        :param strict: if True, fail if more than one result is found

        :returns: results of the query, or None if there were no results
        '''
        res = await cls._find(query)

        if strict and len(res) > 1:
            raise NotUniqueError

        return res[0] if res else None

    @classmethod
    async def _findID(cls: 'Record', value: Any) \
        -> Awaitable[Union['Record', None]]:
        '''Find a single record by primary key value

        :param value: value of primary key to search by
        '''
        return await cls._findOne(
            cls._table.select() \
            .where(cls._table.columns[cls._primaryKey] == value))

    @classmethod
    async def _add(cls, values: Dict[str, Any]) -> int:
        '''Insert a new record into the database

        :param values: Record data to insert
        :returns: primary key of newly inserted record
        '''
        res = await cls._runQuery(
            cls._table.insert() \
            .values(values) \
            .returning(cls._table.columns[cls._primaryKey]))

        return (await res.fetchone())[0]

    @classmethod
    async def updateID(cls: 'Record', value: Any, values: Dict[str, Any]) \
        -> Awaitable:
        '''Update a record by its primary key's value

        :param value: primary key of record to update
        '''
        return await cls._runQuery(
            cls._table.update() \
            .values(values) \
            .where(cls._table.columns[cls._primaryKey] == value))

    @classmethod
    async def deleteID(cls: 'Record', value: Any) -> Awaitable:
        '''Delete a record by its primary key's value

        :param value: value of primary key field to delete by
        '''
        future = asyncio.Future()
        asyncio.ensure_future(
            cls._runQuery(
                cls._table.delete() \
                .where(cls._table.columns[cls._primaryKey] == value)))

        return future

    def __init__(self, data: Dict[str, Any] = None, committed: bool = False):
        '''Create a record object

        :param data: map field names onto the respective values the record
            should use for them.
            Missing fields are left as :type:`NoneType` and will not be sent in
            queries.
            Fields that do not exist in the table are not used.
        :param committed: whether this record already exists in the database
        '''

        #: Whether this record exists in the database
        self.committed = committed

        if data:
            for (name, typ) in [(c.name, c.type) for c in self._table.columns]:
                if name not in data:
                    continue
                val = data[name]
                setattr(self, name, typ.python_type(val) if val else val)

    def __repr__(self):
        return \
            f"{self.__class__.__name__} {self._id} (" \
            f"{'' if self.committed else 'un'}committed):\n\t" \
            + "\n\t".join(f"{key}: {pformat(val)}"
                for key, val in self._data.items())

    @property
    def _data(self) -> dict:
        '''
        :returns: data contained in this record, excluding primary key value
        '''
        data = {}

        for col in [col.name for col in self._table.columns]:
            data[col] = getattr(self, col, None)

        del data[self._primaryKey]

        return data

    @property
    def _id(self) -> Union[int, None]:
        '''
        :returns: primary key value of this record, or :type:`NoneType`
        '''
        return getattr(self, self._primaryKey, None)

    @_id.setter
    def _id(self, value):
        '''Sets the value of the primary key of this record
        '''
        setattr(self, self._primaryKey, value)

    async def save(self):
        '''Save the record represented by this object in the database.
        Existing records are updated, if one already exists it is updated.
        Upon success, :attr:`committed` is set to True, and any fields that are
        None are set to :data:`NULL`

        :returns: Future which performs operation and updates committed status
        '''
        if self._primaryKey is None:
            raise InvalidRecordError

        if self.committed:
            await self.updateID(self._id, self._data)
        else:
            self._id = await self._add(self._data)

        self._saveCallback()

    def _saveCallback(self):
        '''Called after a :meth:`save` operation has been successfully completed
        '''
        for col in self._table.columns:
            if getattr(self, col.name, None) is None:
                setattr(self, col.name, NULL)
        self.committed = True
