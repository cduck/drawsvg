import base64
import urllib.parse
import re


STRIP_CHARS = ('\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f\x10\x11'
               '\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f')

def bytes_as_data_uri(data, strip_chars=STRIP_CHARS, mime='image/svg+xml'):
    '''Return a data URI with base64 encoding.'''
    b64 = base64.b64encode(data)
    return f'data:{mime};base64,{b64.decode(encoding="ascii")}'

def svg_as_data_uri(txt, strip_chars=STRIP_CHARS, mime='image/svg+xml'):
    '''Return a data URI with base64 encoding, stripping unsafe chars for SVG.
    '''
    search = re.compile('|'.join(strip_chars))
    data_safe = search.sub(lambda m: '', txt)
    return bytes_as_data_uri(data_safe.encode(encoding='utf-8'), mime=mime)

def svg_as_utf8_data_uri(txt, unsafe_chars='"', strip_chars=STRIP_CHARS,
                         mime='image/svg+xml'):
    '''Returns a data URI without base64 encoding.

    The characters '#&%' are always escaped.  '#' and '&' break parsing of
    the data URI.  If '%' is not escaped, plain text like '%50' will be
    incorrectly decoded to 'P'.  The characters in `strip_chars` cause the
    SVG not to render even if they are escaped.
    '''
    unsafe_chars = (unsafe_chars or '') + '#&%'
    replacements = {
        char: urllib.parse.quote(char, safe='')
        for char in unsafe_chars
    }
    replacements.update({
        char: ''
        for char in strip_chars
    })
    search = re.compile('|'.join(map(re.escape, replacements.keys())))
    data_safe = search.sub(lambda m: replacements[m.group(0)], txt)
    return f'data:{mime};utf8,{data_safe}'
