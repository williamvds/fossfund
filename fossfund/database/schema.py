'''Definitions for the database schema using SQLAlchemy's declarative system'''
import enum

from aiopg.sa import SAConnection
from sqlalchemy import (
    Table, Column, Integer, String, Boolean, Time, Enum, text, ForeignKey,
    MetaData, CheckConstraint, func
)
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects.postgresql import CreateEnumType

from ..extends import Config
from .utils import DropType, DropTable

_config = Config()
_m = MetaData()

#: A type of a donation URL, identifying the primary payment service provider
#: e.g. PayPal, Patreon
URLType = enum.Enum('URLType', list(_config.urlTypes.keys()))

#: An OAuth provider enum, identifying which one authenticated a user
#: e.g. Google, GitHub
OAuthProvider = enum.Enum('OAuthProvider', list(_config.oauthProviders.keys()))

#: The internal representation for the :py:attr:`URLType` enum
urlType = Enum(URLType, name='urltype', metadata=_m)

#: The internal representation for the :py:attr:`OAuthProvider` enum
oauthProvider = Enum(OAuthProvider, name='oauthprovider', metadata=_m)

#: :class:`~sqlalchemy.schema.Table` for projects
projects = Table('projects', _m,
    Column('projID', Integer, primary_key=True),
    Column('orgID', Integer,
        ForeignKey('organisations.orgID', ondelete='SET NULL')),
    Column('name', String(40), nullable=False),
    Column('desc', String(300), CheckConstraint('char_length("desc") > 14')),
    Column('homepage', String),
    Column('logo', Boolean, default=False))

#: :class:`~sqlalchemy.schema.Table` for organisations
#: Relationship: 1:many project:organisations
organisations = Table('organisations', _m,
    Column('orgID', Integer, primary_key=True),
    Column('name', String(40), nullable=False),
    Column('desc', String(300), CheckConstraint('char_length("desc") > 14')),
    Column('logo', Boolean, default=False))

#: :class:`~sqlalchemy.schema.Table` for project donation links
#: Relationship: 1:many project:urls
urls = Table('urls', _m,
    Column('urlID', Integer, primary_key=True),
    Column('name', String(40), nullable=False),
    Column('url', String),
    Column('type', urlType))

#: :class:`~sqlalchemy.schema.Table` for project groups
#: Relationship: 1:many group:memberships
groups = Table('groups', _m,
    Column('grpID', Integer, primary_key=True),
    Column('name', String(40), nullable=False),
    Column('desc', String(300), CheckConstraint('char_length("desc") > 14')),
    Column('logo', Boolean, default=False))

#: :class:`~sqlalchemy.schema.Table` for project group memberships
#: Relationship: 1:many project:memberships
memberships = Table('memberships', _m,
    Column('projID', Integer, ForeignKey('projects.projID', ondelete='CASCADE'),
        primary_key=True),
    Column('grpID', Integer, ForeignKey('groups.grpID', ondelete='CASCADE'),
        primary_key=True))

#: :class:`~sqlalchemy.schema.Table` for users
users = Table('users', _m,
    Column('userID', Integer, primary_key=True),
    # OAuth provider
    Column('provider', oauthProvider),
    Column('providerUserID', String), # User ID given by provider
    Column('joined', Time, default=func.now()))

#: :class:`~sqlalchemy.schema.Table` for user sessions
#: Relationship: 1:many user:sessions
sessions = Table('sessions', _m,
    Column('sesID', String, server_default=text('uuid_generate_v4()'),
        primary_key=True),
    Column('userID', ForeignKey('users.userID', ondelete='CASCADE')))

#: :class:`list` of all :class:`~sqlalchemy.schema.Table`s in the schema
tables = [organisations, groups, projects, memberships, users, sessions]

#: :class:`list` of all :class:`~sqlalchemy.Enum`s in the schema
enums = [urlType, oauthProvider]

async def setup(conn: SAConnection):
    ''' Create tables for the database schema.
    All existing tables and types are dropped with CASCADE.
    Finally, all tables and types are created.
    All of this is performed in a transaction

    :param conn: the connection to use when performing the query
    '''
    existingTables = [tab[0] for tab in await conn.execute(
        "SELECT table_name FROM information_schema.tables \
        WHERE table_schema='public' AND table_type='BASE TABLE';")]

    async with conn.begin() as trans: # pylint: disable=unused-variable
        for enm in enums:
            await conn.execute(DropType(enm.name, check=True, cascade=True))
            await conn.execute(CreateEnumType(enm))
        for tab in existingTables:
            # Drop all existing tables
            await conn.execute(DropTable(tab, cascade=True))
        for tab in tables:
            # Create the tables in the schema
            await conn.execute(CreateTable(tab))

__all__ = [
    'URLType',
    'OAuthProvider',
    'organisations',
    'projects',
    'memberships',
    'users',
    'sessions',
    'setup',
]
