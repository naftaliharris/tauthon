from __future__ import absolute_import
__all__ = ['ParseResult', 'SplitResult', 'parse_qs', 'parse_qsl', 'urldefrag',
           'urljoin', 'urlparse', 'urlsplit', 'urlunparse', 'urlunsplit',
           'quote', 'quote_plus', 'unquote', 'unquote_plus',
           'unquote_to_bytes', 'urlencode', 'splitquery', 'splittag',
           'splituser', 'splitvalue', 'uses_fragment', 'uses_netloc',
           'uses_params', 'uses_query', 'uses_relative', 'unwrap']

from urllib import (quote as quote_from_bytes, unquote_plus,
                    unquote as unquote_to_bytes, urlencode, splitattr,
                    splithost,
                    splitpasswd, splitport, splitquery, splittag, splittype,
                    splituser, splitvalue, unwrap)
from urlparse import (__doc__, ParseResult, SplitResult, parse_qs, parse_qsl,
                      urldefrag, urljoin, urlparse, urlsplit, urlunparse,
                      urlunsplit, uses_fragment, uses_netloc, uses_params,
                      uses_query, uses_relative)

# Functions modified from Python 3's urllib.
def to_bytes(url):
    """to_bytes(u"URL") --> 'URL'."""
    # Most URL schemes require ASCII. If that changes, the conversion
    # can be relaxed.
    if isinstance(url, str):
        try:
            url = url.encode("ASCII").decode()
        except UnicodeError:
            raise UnicodeError("URL " + repr(url) +
                               " contains non-ASCII characters")
    return url

def quote(string, safe='/', encoding=None, errors=None):
    if isinstance(string, unicode):
        if not string:
            return string
        if encoding is None:
            encoding = 'utf-8'
        if errors is None:
            errors = 'strict'
        string = string.encode(encoding, errors)
    else:
        if encoding is not None:
            raise TypeError("quote() doesn't support 'encoding' for bytes")
        if errors is not None:
            raise TypeError("quote() doesn't support 'errors' for bytes")
    return quote_from_bytes(string, safe)
quote.__doc__ = quote_from_bytes.__doc__

def quote_plus(string, safe='', encoding=None, errors=None):
    """Like quote(), but also replace ' ' with '+', as required for quoting
    HTML form values. Plus signs in the original string are escaped unless
    they are included in safe. It also does not have safe default to '/'.
    """
    # Check if ' ' in string, where string may either be a str or bytes.  If
    # there are no spaces, the regular quote will produce the right answer.
    if ((isinstance(string, unicode) and u' ' not in string) or
        (isinstance(string, str) and ' ' not in string)):
        return quote(string, safe, encoding, errors)
    if isinstance(safe, str):
        space = ' '
    else:
        space = u' '
    string = quote(string, safe + space, encoding, errors)
    return string.replace(' ', '+')

def unquote(string, encoding='utf-8', errors='replace'):
    """Replace %xx escapes by their single-character equivalent. The optional
    encoding and errors parameters specify how to decode percent-encoded
    sequences into Unicode characters, as accepted by the bytes.decode()
    method.
    By default, percent-encoded sequences are decoded with UTF-8, and invalid
    sequences are replaced by a placeholder character.

    unquote('abc%20def') -> 'abc def'.
    """
    if '%' not in string:
        string.split
        return string
    if encoding is None:
        encoding = 'utf-8'
    if errors is None:
        errors = 'replace'
    if not isinstance(string, str):
        string = string.encode(encoding, errors)
    return unquote_to_bytes(string).decode(encoding, errors)

def unquote_plus(string, encoding='utf-8', errors='replace'):
    """Like unquote(), but also replace plus signs by spaces, as required for
    unquoting HTML form values.

    unquote_plus('%7e/abc+def') -> '~/abc def'
    """
    string = string.replace('+', ' ')
    return unquote(string, encoding, errors)
