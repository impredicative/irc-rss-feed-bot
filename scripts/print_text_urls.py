"""Print the unique URLs found in the given text."""

# Populate:
TEXT = """
"""

urls = list(set(w for w in TEXT.split() if w.startswith("https://")))
for url in urls:
    print(url)
