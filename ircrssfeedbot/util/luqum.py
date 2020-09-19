"""luqum utilities."""
from luqum.parser import parser
from luqum.tree import AndOperation
from luqum.utils import UnknownOperationResolver

_UNKNOWN_OP_RESOLVER = UnknownOperationResolver(AndOperation)


def resolve_unknown_op_to_and(query: str) -> str:
    """Resolve unknown operations to AND.

    For example, 'foo bar' is resolved to 'foo AND bar'.
    """
    return str(_UNKNOWN_OP_RESOLVER(parser.parse(query)))
