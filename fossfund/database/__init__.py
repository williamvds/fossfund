"""Database related, including schema, setup, attachment"""
import enum

from aiopg.sa import create_engine, Engine
from aiopg.sa.connection import SAConnection
from psycopg2 import IntegrityError
from sqlalchemy import Table, Column, Integer, String, Boolean, Time, Enum, \
    text, ForeignKey, MetaData, CheckConstraint, func
from attrdict import AttrDict

from ..extends import Config
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
    """Clean dictionary data for table
    Invalid keys are removed - if not in the table or a PK
    Values with empty strings are replaced with None
    Strings are .strip()ed"""
    cleanData = {}
    for k, val in data.items():
        if k in table.c and not table.c[k].primary_key:
            cleanData[k] = None if (isinstance(val, str) and not val) else \
                val.strip() if isinstance(val, str) else val
    return cleanData

async def run(app, query):
    """Run a query using given connection or creating a new one.
    Returns awaited query"""
    if isinstance(app, SAConnection): return await app.execute(query)

    async with app.db.acquire() as conn:
        return await conn.execute(query)

async def fetch(app, query, one=False):
    """Run query, return list of dicts, for each row"""
    qry = await run(app, query)
    if one:
        one = await qry.fetchone()
        return AttrDict(one) if one else one
    return [AttrDict(row) if row else row async for row in qry]

async def insert(app, table, data, res):
    """Insert dictionary of data into given table, returning field res"""
    data = clean(data, table)

    try:
        qry = await run(app, table.insert(values=data) \
            .returning(res))
        return AttrDict(await qry.fetchone())
    except IntegrityError: # Row already exists
        return None # TODO? Redirect with error

async def getUser(app, sesID):
    """Get a single user from a session"""
    return await fetch(app, users.join(sessions).select(use_labels=True) \
        .where(sessions.c.sesID == sesID),
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
