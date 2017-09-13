"""Database related, including schema, setup, attachment"""
from attrdict import AttrDict
from psycopg2 import IntegrityError
from aiopg.sa import create_engine as create
from aiopg.sa.connection import SAConnection
from sqlalchemy import Table, Column, Integer, String, Boolean, \
    ForeignKey, MetaData, CheckConstraint
from sqlalchemy.schema import CreateTable

m = MetaData()

software = Table('software', m,
    Column('softID', Integer, primary_key=True),
    Column('orgID', Integer, ForeignKey('orgs.orgID', ondelete='SET NULL')),
    Column('name', String(40), nullable=False),
    Column('desc', String(300), CheckConstraint('char_length("desc") > 14')),
    Column('logo', Boolean, default=False))

# Organisations - that back software, perhaps the author. E.g. GNU, FSF
# 1:1 software:orgs
orgs = Table('orgs', m,
    Column('orgID', Integer, primary_key=True),
    Column('name', String(40), nullable=False),
    Column('desc', String(300), CheckConstraint('char_length("desc") > 14')),
    Column('logo', Boolean, default=False))

# Groups - e.g. operating systems or distros
# 1:M groups:members
groups = Table('groups', m,
    Column('grpID', Integer, primary_key=True),
    Column('name', String(40), nullable=False),
    Column('desc', String(300), CheckConstraint('char_length("desc") > 14')),
    Column('logo', Boolean, default=False))

# Group members - softwares that are implied from the group they belong to
# 1:M software:members
members = Table('members', m,
    Column('softID', Integer, ForeignKey('software.softID', ondelete='CASCADE'), primary_key=True),
    Column('grpID', Integer, ForeignKey('groups.grpID', ondelete='CASCADE'), primary_key=True))

tables = [orgs, groups, software, members]

# Application related
async def setup(config):
    """Recreate database tables"""
    db = await create(**config)
    async with db.acquire() as c:
        for tab in tables:
            await c.execute('DROP TABLE IF EXISTS %s CASCADE' % tab.name)
            await c.execute(CreateTable(tab))

async def attach(app):
    """Create an engine and attach it to app as db"""
    app.db = await create(**app.config.db)

async def destroy(app):
    """Disconnect the engine"""
    app.db.close()
    await app.db.wait_closed()

# Action utilities
def clean(data, table):
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
    """Run a query using given connection or creating a new one, return awaited query"""
    if isinstance(app, SAConnection): return await app.execute(query)

    async with app.db.acquire() as conn:
        return await conn.execute(query)

async def fetch(app, query, one=False):
    """Run query, return list of dicts, for each row"""
    q = await run(app, query)
    if one:
        return AttrDict(await q.fetchone())
    return [AttrDict(r) async for r in q]

async def insert(app, table, data, res):
    """Insert dictionary of data into given table, returning field res"""
    data = clean(data, table)

    try:
        q = await run(app, table.insert(values=data) \
            .returning(res))
        return AttrDict(await q.fetchone())
    except IntegrityError: # Row already exists
        return None # TODO? Redirect with error
