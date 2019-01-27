"""Database related, including schema, setup, attachment"""
import enum
from typing import Union, Any, List

from aiohttp.web import Application
from aiopg.sa import create_engine, Engine
from aiopg.sa.connection import SAConnection
from psycopg2 import IntegrityError
from sqlalchemy import Table, Column, Integer, String, Boolean, Time, Enum, \
    text, ForeignKey, MetaData, CheckConstraint, func
from attrdict import AttrDict

from .schema import (
    setup, projects, organisations, urls, groups, memberships, users, sessions
)

async def create(config: dict) -> Engine:
    '''Create database engine using :func:`~aiopg.sa.create_engine`

    :param config: `dict` of options used for the database connection
    '''
    return await create_engine(**config)

async def destroy(engine: Engine):
    '''Close the given database engine, waiting until it is complete

    :param engine: the database engine to destroy
    '''
    engine.terminate()
    await engine.wait_closed()

# Action utilities
def clean(data: dict, table: Table) -> dict:
    '''Clean dictionary data for table
    Invalid keys are removed - if not in the table or a PK
    Values with empty strings are replaced with :type:`NoneType`
    Strings are :func:`str.strip`ped

    :param data: The dictionary of field:value to clean
    :param table: The table for which to clean the data

    todo::
        Remove entirely. Handle the exceptions raised from psycopg2 or
        SQLAlchemy to inform the user and log when data in queries is invalid
    '''
    cleanData = {}
    for k, val in data.items():
        if k in table.c and not table.c[k].primary_key:
            cleanData[k] = None if (isinstance(val, str) and not val) else \
                val.strip() if isinstance(val, str) else val
    return cleanData

async def run(app: Union[Application, SAConnection], query: Any) -> dict:
    '''Run a query using given connection or creating a new one

    :param app: database engine provider or existing connection
    :param query: query to perform, must be convertible to :class:`str`
    :returns: awaited query
    '''
    if isinstance(app, SAConnection): return await app.execute(query)

    async with app.db.acquire() as conn:
        return await conn.execute(query)

async def fetch(app: Application, query: Any, one: bool = False) \
        -> Union[None, AttrDict, List[AttrDict]]:
    '''Run query which expects results
    Results are converted into (list of) :class:`AttrDict`

    :param app: database engine provider
    :param query: query to perform, must be convertible to :class:`str`
    :param one: whether a single row is expected, in which case the result is
        not a list

    :returns: query results
    '''
    qry = await run(app, query)
    if one:
        one = await qry.fetchone()
        return AttrDict(one) if one else one
    return [AttrDict(row) if row else row async for row in qry]

async def insert(app: Application, table: Table, data: dict, res: Column) \
        -> Any:
    '''Insert data into the database

    :param app: database engine provider
    :param table: table to insert into
    :param data: values to insert
    :param res: field of newly created record to return

    :returns: the value of the selected field in the new record
    '''
    data = clean(data, table)

    try:
        qry = await run(app, table.insert(values=data) \
            .returning(res))
        return AttrDict(await qry.fetchone())
    except IntegrityError: # Row already exists
        return None # TODO? Redirect with error

async def getUser(app: Application, sessionID: int) -> Union[None, AttrDict]:
    '''Get a user record

    :param app: database engine provider
    :param sessionID: session ID (primary key) to search for

    :returns: user record (or None)
    '''
    return await fetch(app, users.join(sessions).select(use_labels=True) \
        .where(sessions.c.sesID == sessionID),
        one=True)

__all__ = [
    'setup',
    'projects',
    'organisations',
    'urls',
    'groups',
    'memberships',
    'users',
    'sessions',
    'create',
    'destroy',
    'clean',
    'run',
    'fetch',
    'insert',
    'getUser',
]
