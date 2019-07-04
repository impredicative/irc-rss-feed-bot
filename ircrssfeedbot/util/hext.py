import hext

_HTML_TEXT_RULE = hext.Rule('<html @text:text />')


def html_to_text(text: str) -> str:
    # Ref: https://stackoverflow.com/a/56894409/
    return _HTML_TEXT_RULE.extract(hext.Html(f'<html>{text}</html>'))[0]['text']
