"""lxml utilities."""
import lxml.etree


def sanitize_xml(content: bytes) -> bytes:
    """Return valid XML."""
    # Ref: https://stackoverflow.com/a/57450722/
    try:
        lxml.etree.fromstring(content)
    except lxml.etree.XMLSyntaxError:
        root = lxml.etree.fromstring(content, parser=lxml.etree.XMLParser(recover=True))
        return lxml.etree.tostring(root)
    return content
