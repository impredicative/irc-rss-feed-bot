"""sqlite3 utilities."""
import contextlib
import io
import logging
import sqlite3
import string

from luqum.parser import parser
from luqum.tree import AndOperation
from luqum.utils import LuceneTreeTransformer, UnknownOperationResolver

log = logging.getLogger(__name__)

_SAFE_QUERY_CHARS = set(':()"')  # "-" is not processed to NOT by luqum. ":" is required by luqum for "path:/foo". "()" are used by sqlite3 FTS5. """ is used for quoting.
_UNKNOWN_OP_RESOLVER = UnknownOperationResolver(AndOperation)
_UNSAFE_QUERY_CHARS = set(string.punctuation) - _SAFE_QUERY_CHARS


class _SearchFieldRemover(LuceneTreeTransformer):
    def visit_search_field(self, node, parents):  # pylint: disable=unused-argument,no-self-use
        return None


class SqliteFTS5Matcher:
    """Validate whether a given GitHub code search query matches against the specified text using SQLite FTS5."""

    def __init__(self, query: str) -> None:
        self._query = self._convert_github_query_to_sqlite_fts5_query(query)
        if query != self._query:
            log.info(f"Adjusted the query {query!r} for local validation to {self._query!r}.")

    @staticmethod
    def _convert_github_query_to_sqlite_fts5_query(query: str) -> str:
        """Convert a given GitHub code search query into a SQLite FTS5 query.

        Unsafe characters and search fields are removed.

        For example, 'foo bar -baz path:/##baz' is mapped to 'foo AND bar NOT baz'.
        """
        query = "".join(c for c in query if c not in _UNSAFE_QUERY_CHARS)
        with contextlib.redirect_stdout(io.StringIO()):  # Workaround for https://github.com/jurismarches/luqum/issues/57
            tree = _UNKNOWN_OP_RESOLVER(parser.parse(query))
        tree = _SearchFieldRemover().visit(tree)
        query = str(tree)
        query = query.replace(" AND NOT ", " NOT ")  # Approximate workaround for sqlite3.OperationalError: fts5: syntax error near "NOT"
        return query

    def is_match(self, text: str) -> bool:
        """Return whether the given text string is a match for the query."""
        # Docs: https://www.sqlite.org/fts5.html
        db = sqlite3.connect(":memory:")
        cursor = db.cursor()
        cursor.execute("CREATE VIRTUAL TABLE t USING fts5(c);")
        cursor.execute("INSERT INTO t VALUES(?);", (text,))
        try:
            results_cursor = cursor.execute("SELECT * FROM t WHERE t MATCH ?;", (self._query,))
        except sqlite3.OperationalError as exception:
            raise sqlite3.OperationalError(f"{exception} (with query {self._query!r})")
        return bool(results_cursor.fetchall())
