from __future__ import absolute_import
__all__ = ['urlopen', 'install_opener', 'build_opener', 'pathname2url',
           'url2pathname', 'getproxies', 'Request', 'OpenerDirector',
           'HTTPDefaultErrorHandler', 'HTTPRedirectHandler',
           'HTTPCookieProcessor', 'ProxyHandler', 'BaseHandler',
           'HTTPPasswordMgr', 'HTTPPasswordMgrWithDefaultRealm',
           'AbstractBasicAuthHandler', 'HTTPBasicAuthHandler',
           'ProxyBasicAuthHandler', 'AbstractDigestAuthHandler',
           'HTTPDigestAuthHandler', 'ProxyDigestAuthHandler', 'HTTPHandler',
           'HTTPSHandler', 'FileHandler', 'FTPHandler', 'CacheFTPHandler',
           'UnknownHandler', 'HTTPErrorProcessor', 'urlretrieve', 'urlcleanup',
           'URLopener', 'FancyURLopener', 'proxy_bypass', 'parse_http_list',
           'parse_keqv_list']

from urllib import (pathname2url, url2pathname, getproxies, urlretrieve,
                    urlcleanup, URLopener, FancyURLopener, proxy_bypass)
from urllib2 import (__doc__, urlopen, install_opener, build_opener, Request,
                     OpenerDirector, HTTPDefaultErrorHandler,
                     HTTPRedirectHandler, HTTPCookieProcessor, ProxyHandler,
                     BaseHandler, HTTPPasswordMgr,
                     HTTPPasswordMgrWithDefaultRealm, AbstractBasicAuthHandler,
                     HTTPBasicAuthHandler, ProxyBasicAuthHandler,
                     AbstractDigestAuthHandler, HTTPDigestAuthHandler,
                     ProxyDigestAuthHandler, HTTPHandler, HTTPSHandler,
                     FileHandler, FTPHandler, CacheFTPHandler, UnknownHandler,
                     HTTPErrorProcessor, parse_http_list, parse_keqv_list,
                     AbstractHTTPHandler)

# Not strictly part of urllib.request, however here for compatibility with bad
# code that thinks they are.
from urllib.error import URLError, HTTPError, ContentTooShortError
from urllib.parse import (
    urlparse, urlsplit, urljoin, unwrap, quote, unquote,
    splittype, splithost, splitport, splituser, splitpasswd,
    splitattr, splitquery, splitvalue, splittag, to_bytes,
    unquote_to_bytes, urlunparse)

__doc__ = __doc__.replace('urllib2', __name__)
