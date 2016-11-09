"""
This module defines classes for fine-grained OSError's, which work by
inspecting the current exception to determine if they should catch it or not.
Importing this module also adds the new exceptions to the global namespace.
This module gets imported in Python 2.8's startup process, so it must run
quickly and successfully.
"""

# TODO: Implement this module in C.

import errno
import sys
import __builtin__


class _OSErrorMeta(type):
    def __subclasscheck__(cls, other):
        import select  # Hide import since this module may not be built yet.

        if cls in getattr(other, '__mro__', ()):
            return True

        exc = sys.exc_info()[1]
        if exc is None:
            return False

        errno = getattr(exc, 'errno', None)
        if issubclass(other, EnvironmentError) and errno in cls.errno:
            return True
        elif issubclass(other, select.error) and exc.args[0] in cls.errno:
            return True
        else:
            return False


class _OSError(OSError):
    __metaclass__ = _OSErrorMeta


class BlockingIOError(_OSError):
    errno = (errno.EAGAIN, errno.EALREADY, errno.EWOULDBLOCK,
             errno.EINPROGRESS)


class ChildProcessError(_OSError):
    errno = (errno.ECHILD,)


class ConnectionError(_OSError):
    errno = (errno.EPIPE, errno.ESHUTDOWN, errno.ECONNABORTED,
             errno.ECONNREFUSED, errno.ECONNRESET)


class BrokenPipeError(ConnectionError):
    errno = (errno.EPIPE, errno.ESHUTDOWN)


class ConnectionAbortedError(ConnectionError):
    errno = (errno.ECONNABORTED,)


class ConnectionRefusedError(ConnectionError):
    errno = (errno.ECONNREFUSED,)


class ConnectionResetError(ConnectionError):
    errno = (errno.ECONNRESET,)


class FileExistsError(_OSError):
    errno = (errno.EEXIST,)


class FileNotFoundError(_OSError):
    errno = (errno.ENOENT,)


class InterruptedError(_OSError):
    errno = (errno.EINTR,)


class IsADirectoryError(_OSError):
    errno = (errno.EISDIR,)


class NotADirectoryError(_OSError):
    errno = (errno.ENOTDIR,)


class PermissionError(_OSError):
    errno = (errno.EACCES, errno.EPERM)


class ProcessLookupError(_OSError):
    errno = (errno.ESRCH,)


class TimeoutError(_OSError):
    errno = (errno.ETIMEDOUT,)

__all__ = [x for x in dir() if "Error" in x and not x.startswith("_")]
globs = globals()

for x in __all__:
    __builtin__.__dict__[x] = globs[x]
