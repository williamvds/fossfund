"""Database related, including schema, setup, attachment"""
from aiopg.sa import create_engine as create
from aiopg.sa.connection import SAConnection
from psycopg2 import IntegrityError
from sqlalchemy import Table, Column, Integer, String, Boolean, Time, Enum, \
    text, ForeignKey, MetaData, CheckConstraint, func
from sqlalchemy.schema import CreateTable
from attrdict import AttrDict

m = MetaData()

projects = Table('projects', m,
    Column('projID', Integer, primary_key=True),
    Column('orgID', Integer, ForeignKey('orgs.orgID', ondelete='SET NULL')),
    Column('name', String(40), nullable=False),
    Column('desc', String(300), CheckConstraint('char_length("desc") > 14')),
    Column('logo', Boolean, default=False))

# Organisations - that back projects, perhaps the author. E.g. GNU, FSF
# 1:1 projects:orgs
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

# Group members - projects that are implied from the group they belong to
# 1:M projects:members
members = Table('members', m,
    Column('projID', Integer, ForeignKey('projects.projID', ondelete='CASCADE'),
        primary_key=True),
    Column('grpID', Integer, ForeignKey('groups.grpID', ondelete='CASCADE'),
        primary_key=True))

# Users
users = Table('users', m,
    Column('userID', Integer, primary_key=True),
    # OAuth provider
    Column('provider', Enum('github', 'bitbucket', 'google',
        name='oauthprovider')),
    Column('providerUserID', String), # User ID given by provider
    Column('joined', Time, default=func.now()))

# Sessions
# 1:M users:sessions
sessions = Table('sessions', m,
    Column('sesID', String, server_default=text("uuid_generate_v4()"),
        primary_key=True),
    Column('userID', ForeignKey('users.userID', ondelete='CASCADE')))

tables = [orgs, groups, projects, members, users, sessions]

# Application related
async def setup(config):
    """Recreate database schema"""
    db = await create(**config)
    async with db.acquire() as conn:
        await conn.execute('DROP TYPE IF EXISTS oauthprovider CASCADE;')
        await conn.execute("CREATE TYPE oauthprovider AS ENUM " \
            "('github', 'bitbucket', 'google');")
        for tab in tables:
            await conn.execute('DROP TABLE IF EXISTS %s CASCADE;' % tab.name)
            await conn.execute(CreateTable(tab))

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
