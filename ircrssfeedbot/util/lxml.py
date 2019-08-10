import lxml.etree


def sanitize_xml(content: bytes) -> bytes:
    # Ref: https://stackoverflow.com/a/4997458/
    try:
        root = lxml.etree.fromstring(content)
    except lxml.etree.XMLSyntaxError:
        root = lxml.etree.fromstring(content, parser=lxml.etree.XMLParser(recover=True))
        return lxml.etree.tostring(root)
    return content
