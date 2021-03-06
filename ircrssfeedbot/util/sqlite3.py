"""sqlite3 utilities."""
import logging
import sqlite3
import string

import luqum
import luqum.parser
import luqum.tree
import luqum.utils
import luqum.visitor

log = logging.getLogger(__name__)

_SAFE_QUERY_CHARS = set('-:()"')
# "-" is safe as it is manually handled after it is ignored by luqum.
# ":" is safe as it is processed by luqum from "path:/foo" and is then removed.
# "()" are safe as they are used by sqlite3 FTS5.
# """ is safe as it is used for quoting.

_UNKNOWN_OP_RESOLVER = luqum.utils.UnknownOperationResolver(luqum.tree.AndOperation)
_UNSAFE_QUERY_CHARS = set(string.punctuation) - _SAFE_QUERY_CHARS


class _QueryTreeTransformer(luqum.visitor.TreeTransformer):
    def visit_search_field(self, node, context):  # pylint: disable=unused-argument,no-self-use
        return ""


class SqliteFTS5Matcher:
    """Validate whether a given GitHub code search query matches against the specified text using SQLite FTS5."""

    def __init__(self, query: str) -> None:
        self._query = self._convert_github_query_to_sqlite_fts5_query(query)
        if query != self._query:
            log.info(f"For the query {query!r}, the corresponding query used for local validation of the search results is {self._query!r}.")

    @staticmethod
    def _convert_github_query_to_sqlite_fts5_query(query: str) -> str:
        """Convert a given GitHub code search query into a SQLite FTS5 query.

        Unsafe characters and search fields are removed.

        For example, 'foo bar -baz path:/##qux' is mapped to 'foo AND bar NOT baz'.
        """
        query = "".join(c for c in query if c not in _UNSAFE_QUERY_CHARS)
        query = query.replace(" -path:", " path:")  # Approximate workaround for luqum raising ValueError. The search field is later removed anyway.
        tree = _UNKNOWN_OP_RESOLVER(luqum.parser.parser.parse(query))
        tree = _QueryTreeTransformer().visit(tree)
        query = str(tree).strip()
        query = query.replace(" -", " NOT ")  # Approximate workaround for luqum ignoring -
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
