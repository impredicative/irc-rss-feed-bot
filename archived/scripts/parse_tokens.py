"""Print a Docker Compose compatible environment variable for Bitly tokens.

Tokens are defined in the variable TOKENS as a list. For example:
01 abcd
02 efgh
03 pqrs
"""

TOKENS = """

"""  # Update value.

# pylint: disable=invalid-name

tokens = [line.split(" ")[-1] for line in TOKENS.split("\n") if line]
print(f"{len(tokens)} tokens were detected.\n")

if tokens:
    tokens_str = ",".join(tokens)
    print(f"BITLY_TOKENS={tokens_str}")
