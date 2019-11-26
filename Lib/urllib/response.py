"""Response classes used by urllib.

The base class, addbase, defines a minimal file-like interface,
including read() and readline().  The typical response object is an
addinfourl instance, which defines an info() method that returns
headers and a geturl() method that returns the url.
"""

from __future__ import absolute_import
__all__ = ['addbase', 'addclosehook', 'addinfo', 'addinfourl']
from urllib import addbase, addclosehook, addinfo, addinfourl
