__all__ = ['HTTPServer', 'BaseHTTPRequestHandler', 'SimpleHTTPRequestHandler',
           'CGIHTTPRequestHandler']

from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from CGIHTTPServer import CGIHTTPRequestHandler, executable, nobody_uid
from SimpleHTTPServer import SimpleHTTPRequestHandler, test

if __name__ == '__main__':
    test()
