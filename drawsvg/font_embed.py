import urllib.request, urllib.parse
import re

from . import url_encode


def download_url(url):
    with urllib.request.urlopen(url) as r:
        return r.read()

def download_url_to_data_uri(url, mime='application/octet-stream'):
    data = download_url(url)
    return url_encode.bytes_as_data_uri(data, strip_chars='', mime=mime)

def embed_css_resources(css):
    '''Replace all URLs in the CSS string with downloaded data URIs.'''
    regex = re.compile(r'url\((https?://[^)]*)\)')
    def repl(match):
        url = match[1]
        uri = download_url_to_data_uri(url)
        return f'url({uri})'
    embedded, _ = regex.subn(repl, css)
    return embedded

def download_google_font_css(family, text=None, display='swap', **kwargs):
    '''Download SVG-embeddable CSS from Google fonts.

    Args:
        family: Name of font family or list of font families.
        text: The set of characters required from the font.  Only a font subset
            with these characters will be downloaded.
        display: The font-display CSS value.
        **kwargs: Other URL parameters sent to
            https://fonts.googleapis.com/css?...
    '''
    if not isinstance(family, str):
        family = '|'.join(family)  # Request a list of families
    args = dict(family=family, display=display)
    if text is not None:
        if not isinstance(text, str):
            text = ''.join(text)
        args['text'] = text
    args.update(kwargs)
    params = urllib.parse.urlencode(args)
    url = f'https://fonts.googleapis.com/css?{params}'
    with urllib.request.urlopen(url) as r:
        css = r.read().decode('utf-8')
    return embed_css_resources(css)
