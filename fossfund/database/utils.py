'''Utilities for the database submodule'''
from typing import Union, List

from sqlalchemy.schema import DDLElement
from sqlalchemy.ext.compiler import compiles

class DropQuery(DDLElement):
    '''A generic PostgreSQL DROP query

    :param target: object(s) to drop
    :param check: whether to prepend 'IF EXISTS' to query
    '''
    #: The database object to drop, e.g. TABLE, TYPE, ...
    subject: str = None
    def __init__(self, target: Union[str, List[str]], check: bool = False):
        self.target = ', '.join(target) if isinstance(target, list) else target
        self.check = 'IF EXISTS ' if check else ''

class DropQueryWithDependents(DropQuery):
    '''A generic PostgreSQL DROP query for an object which has dependent
    objects, i.e. it has [ CASCADE | RESTRICT ] in its syntax

    :param target: object(s) to drop
    :param check: whether to prepend 'IF EXISTS' to query
    :param cascade: whether to append 'CASCADE' to query
    '''
    def __init__(self,
            target: Union[str, List[str]],
            check: bool = False,
            cascade: bool = False):
        super().__init__(target, check)
        self.cascade = ' CASCADE' if cascade else ''

class DropTable(DropQueryWithDependents):
    '''A PostgreSQL DROP TABLE query[1]

    [1]: https://www.postgresql.org/docs/devel/static/sql-droptable.html
    '''
    subject: str = 'TABLE'

class DropType(DropQueryWithDependents):
    '''A PostgreSQL DROP TYPE query[1]

    [1]: https://www.postgresql.org/docs/devel/static/sql-droptype.html
    '''
    subject: str = 'TYPE'

@compiles(DropQueryWithDependents, 'postgresql')
def visit_drop_table(element: DropQueryWithDependents, compiler, **kwargs):
    '''Compile a PostgreSQL DROP query from a :class:`DropQueryWithDependents`
    '''
    return 'DROP %s %s%s%s;' % (element.subject, element.check,
        element.target, element.cascade)
