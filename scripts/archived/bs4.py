import xml.etree.ElementTree

import bs4


def sanitize_xml(content: bytes) -> bytes:
    # Ref: https://stackoverflow.com/a/57450722/
    try:
        xml.etree.ElementTree.fromstring(content)
    except xml.etree.ElementTree.ParseError:
        return bs4.BeautifulSoup(content, features='lxml-xml').encode()
    return content
