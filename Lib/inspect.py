# -*- coding: iso-8859-1 -*-
"""Get useful information from live Python objects.

This module encapsulates the interface provided by the internal special
attributes (func_*, co_*, im_*, tb_*, etc.) in a friendlier fashion.
It also provides some help for examining source code and class layout.

Here are some of the useful functions provided by this module:

    ismodule(), isclass(), ismethod(), isfunction(), isgeneratorfunction(),
        iscoroutinefunction(), isgenerator(), iscoroutine(), isawaitable(),
        istraceback(), isframe(), iscode(), isbuiltin(), isroutine()
        - check object types
    getmembers() - get members of an object that satisfy a given condition

    getfile(), getsourcefile(), getsource() - find an object's source code
    getdoc(), getcomments() - get documentation on an object
    getmodule() - determine the module that an object came from
    getclasstree() - arrange classes so as to represent their hierarchy

    getargspec(), getargvalues(), getcallargs() - get info about function arguments
    getfullargspec() - same, with support for Python-3000 features
    formatargspec(), formatargvalues() - format an argument spec
    getouterframes(), getinnerframes() - get info about frames
    currentframe() - get the current stack frame
    stack(), trace() - get info about frames on the stack or in a traceback
"""

# This module is in the public domain.  No warranties.

__author__ = 'Ka-Ping Yee <ping@lfw.org>'
__date__ = '1 Jan 2001'

import sys
import os
import types
import string
import re
import dis
import imp
import itertools
import functools
import tokenize
import linecache
import token
import collections
from operator import attrgetter
from collections import namedtuple, OrderedDict

# These constants are from Include/code.h.
CO_OPTIMIZED, CO_NEWLOCALS, CO_VARARGS, CO_VARKEYWORDS = 0x1, 0x2, 0x4, 0x8
CO_NESTED, CO_GENERATOR, CO_NOFREE = 0x10, 0x20, 0x40
CO_COROUTINE, CO_ITERABLE_COROUTINE = 0x0080, 0x0100
# See Include/object.h
TPFLAGS_IS_ABSTRACT = 1 << 20

# ----------------------------------------------------------- type-checking
def ismodule(object):
    """Return true if the object is a module.

    Module objects provide these attributes:
        __doc__         documentation string
        __file__        filename (missing for built-in modules)"""
    return isinstance(object, types.ModuleType)

def isclass(object):
    """Return true if the object is a class.

    Class objects provide these attributes:
        __doc__         documentation string
        __module__      name of module in which this class was defined"""
    return isinstance(object, (type, types.ClassType))

def ismethod(object):
    """Return true if the object is an instance method.

    Instance method objects provide these attributes:
        __doc__         documentation string
        __name__        name with which this method was defined
        im_class        class object in which this method belongs
        im_func         function object containing implementation of method
        im_self         instance to which this method is bound, or None"""
    return isinstance(object, types.MethodType)

def ismethoddescriptor(object):
    """Return true if the object is a method descriptor.

    But not if ismethod() or isclass() or isfunction() are true.

    This is new in Python 2.2, and, for example, is true of int.__add__.
    An object passing this test has a __get__ attribute but not a __set__
    attribute, but beyond that the set of attributes varies.  __name__ is
    usually sensible, and __doc__ often is.

    Methods implemented via descriptors that also pass one of the other
    tests return false from the ismethoddescriptor() test, simply because
    the other tests promise more -- you can, e.g., count on having the
    im_func attribute (etc) when an object passes ismethod()."""
    return (hasattr(object, "__get__")
            and not hasattr(object, "__set__") # else it's a data descriptor
            and not ismethod(object)           # mutual exclusion
            and not isfunction(object)
            and not isclass(object))

def isdatadescriptor(object):
    """Return true if the object is a data descriptor.

    Data descriptors have both a __get__ and a __set__ attribute.  Examples are
    properties (defined in Python) and getsets and members (defined in C).
    Typically, data descriptors will also have __name__ and __doc__ attributes
    (properties, getsets, and members have both of these attributes), but this
    is not guaranteed."""
    return (hasattr(object, "__set__") and hasattr(object, "__get__"))

if hasattr(types, 'MemberDescriptorType'):
    # CPython and equivalent
    def ismemberdescriptor(object):
        """Return true if the object is a member descriptor.

        Member descriptors are specialized descriptors defined in extension
        modules."""
        return isinstance(object, types.MemberDescriptorType)
else:
    # Other implementations
    def ismemberdescriptor(object):
        """Return true if the object is a member descriptor.

        Member descriptors are specialized descriptors defined in extension
        modules."""
        return False

if hasattr(types, 'GetSetDescriptorType'):
    # CPython and equivalent
    def isgetsetdescriptor(object):
        """Return true if the object is a getset descriptor.

        getset descriptors are specialized descriptors defined in extension
        modules."""
        return isinstance(object, types.GetSetDescriptorType)
else:
    # Other implementations
    def isgetsetdescriptor(object):
        """Return true if the object is a getset descriptor.

        getset descriptors are specialized descriptors defined in extension
        modules."""
        return False

def isfunction(object):
    """Return true if the object is a user-defined function.

    Function objects provide these attributes:
        __doc__         documentation string
        __name__        name with which this function was defined
        func_code       code object containing compiled function bytecode
        func_defaults   tuple of any default values for arguments
        func_doc        (same as __doc__)
        func_globals    global namespace in which this function was defined
        func_name       (same as __name__)"""
    return isinstance(object, types.FunctionType)

def isgeneratorfunction(object):
    """Return true if the object is a user-defined generator function.

    Generator function objects provide the same attributes as functions.
    See help(isfunction) for a list of attributes."""
    return bool((isfunction(object) or ismethod(object)) and
                object.func_code.co_flags & CO_GENERATOR)

def iscoroutinefunction(object):
    """Return true if the object is a coroutine function.

    Coroutine functions are defined with "async def" syntax,
    or generators decorated with "types.coroutine".
    """
    return bool((isfunction(object) or ismethod(object)) and
                object.__code__.co_flags & CO_COROUTINE)

def isgenerator(object):
    """Return true if the object is a generator.

    Generator objects provide these attributes:
        __iter__        defined to support iteration over container
        close           raises a new GeneratorExit exception inside the
                        generator to terminate the iteration
        gi_code         code object
        gi_frame        frame object or possibly None once the generator has
                        been exhausted
        gi_running      set to 1 when generator is executing, 0 otherwise
        next            return the next item from the container
        send            resumes the generator and "sends" a value that becomes
                        the result of the current yield-expression
        throw           used to raise an exception inside the generator"""
    return isinstance(object, types.GeneratorType)

def iscoroutine(object):
    """Return true if the object is a coroutine."""
    return isinstance(object, types.CoroutineType)

def isawaitable(object):
    """Return true is object can be passed to an ``await`` expression."""
    return (isinstance(object, types.CoroutineType) or
            isinstance(object, types.GeneratorType) and
                object.gi_code.co_flags & CO_ITERABLE_COROUTINE or
            isinstance(object, collections.Awaitable))

def istraceback(object):
    """Return true if the object is a traceback.

    Traceback objects provide these attributes:
        tb_frame        frame object at this level
        tb_lasti        index of last attempted instruction in bytecode
        tb_lineno       current line number in Python source code
        tb_next         next inner traceback object (called by this level)"""
    return isinstance(object, types.TracebackType)

def isframe(object):
    """Return true if the object is a frame object.

    Frame objects provide these attributes:
        f_back          next outer frame object (this frame's caller)
        f_builtins      built-in namespace seen by this frame
        f_code          code object being executed in this frame
        f_exc_traceback traceback if raised in this frame, or None
        f_exc_type      exception type if raised in this frame, or None
        f_exc_value     exception value if raised in this frame, or None
        f_globals       global namespace seen by this frame
        f_lasti         index of last attempted instruction in bytecode
        f_lineno        current line number in Python source code
        f_locals        local namespace seen by this frame
        f_restricted    0 or 1 if frame is in restricted execution mode
        f_trace         tracing function for this frame, or None"""
    return isinstance(object, types.FrameType)

def iscode(object):
    """Return true if the object is a code object.

    Code objects provide these attributes:
        co_argcount     number of arguments (not including * or ** args)
        co_code         string of raw compiled bytecode
        co_consts       tuple of constants used in the bytecode
        co_filename     name of file in which this code object was created
        co_firstlineno  number of first line in Python source code
        co_flags        bitmap: 1=optimized | 2=newlocals | 4=*arg | 8=**arg
        co_lnotab       encoded mapping of line numbers to bytecode indices
        co_name         name with which this code object was defined
        co_names        tuple of names of local variables
        co_nlocals      number of local variables
        co_stacksize    virtual machine stack space required
        co_varnames     tuple of names of arguments and local variables"""
    return isinstance(object, types.CodeType)

def isbuiltin(object):
    """Return true if the object is a built-in function or method.

    Built-in functions and methods provide these attributes:
        __doc__         documentation string
        __name__        original name of this function or method
        __self__        instance to which a method is bound, or None"""
    return isinstance(object, types.BuiltinFunctionType)

def isroutine(object):
    """Return true if the object is any kind of function or method."""
    return (isbuiltin(object)
            or isfunction(object)
            or ismethod(object)
            or ismethoddescriptor(object))

def isabstract(object):
    """Return true if the object is an abstract base class (ABC)."""
    return bool(isinstance(object, type) and object.__flags__ & TPFLAGS_IS_ABSTRACT)

def getmembers(object, predicate=None):
    """Return all members of an object as (name, value) pairs sorted by name.
    Optionally, only return members that satisfy a given predicate."""
    results = []
    for key in dir(object):
        try:
            value = getattr(object, key)
        except AttributeError:
            continue
        if not predicate or predicate(value):
            results.append((key, value))
    results.sort()
    return results

Attribute = namedtuple('Attribute', 'name kind defining_class object')

def classify_class_attrs(cls):
    """Return list of attribute-descriptor tuples.

    For each name in dir(cls), the return list contains a 4-tuple
    with these elements:

        0. The name (a string).

        1. The kind of attribute this is, one of these strings:
               'class method'    created via classmethod()
               'static method'   created via staticmethod()
               'property'        created via property()
               'method'          any other flavor of method
               'data'            not a method

        2. The class which defined this attribute (a class).

        3. The object as obtained directly from the defining class's
           __dict__, not via getattr.  This is especially important for
           data attributes:  C.data is just a data object, but
           C.__dict__['data'] may be a data descriptor with additional
           info, like a __doc__ string.
    """

    mro = getmro(cls)
    names = dir(cls)
    result = []
    for name in names:
        # Get the object associated with the name, and where it was defined.
        # Getting an obj from the __dict__ sometimes reveals more than
        # using getattr.  Static and class methods are dramatic examples.
        # Furthermore, some objects may raise an Exception when fetched with
        # getattr(). This is the case with some descriptors (bug #1785).
        # Thus, we only use getattr() as a last resort.
        homecls = None
        for base in (cls,) + mro:
            if name in base.__dict__:
                obj = base.__dict__[name]
                homecls = base
                break
        else:
            obj = getattr(cls, name)
            homecls = getattr(obj, "__objclass__", homecls)

        # Classify the object.
        if isinstance(obj, staticmethod):
            kind = "static method"
        elif isinstance(obj, classmethod):
            kind = "class method"
        elif isinstance(obj, property):
            kind = "property"
        elif ismethoddescriptor(obj):
            kind = "method"
        elif isdatadescriptor(obj):
            kind = "data"
        else:
            obj_via_getattr = getattr(cls, name)
            if (ismethod(obj_via_getattr) or
                ismethoddescriptor(obj_via_getattr)):
                kind = "method"
            else:
                kind = "data"
            obj = obj_via_getattr

        result.append(Attribute(name, kind, homecls, obj))

    return result

# ----------------------------------------------------------- class helpers
def _searchbases(cls, accum):
    # Simulate the "classic class" search order.
    if cls in accum:
        return
    accum.append(cls)
    for base in cls.__bases__:
        _searchbases(base, accum)

def getmro(cls):
    "Return tuple of base classes (including cls) in method resolution order."
    if hasattr(cls, "__mro__"):
        return cls.__mro__
    else:
        result = []
        _searchbases(cls, result)
        return tuple(result)

# -------------------------------------------------------- function helpers

def unwrap(func, *, stop=None):
    """Get the object wrapped by *func*.

   Follows the chain of :attr:`__wrapped__` attributes returning the last
   object in the chain.

   *stop* is an optional callback accepting an object in the wrapper chain
   as its sole argument that allows the unwrapping to be terminated early if
   the callback returns a true value. If the callback never returns a true
   value, the last object in the chain is returned as usual. For example,
   :func:`signature` uses this to stop unwrapping if any object in the
   chain has a ``__signature__`` attribute defined.

   :exc:`ValueError` is raised if a cycle is encountered.

    """
    if stop is None:
        def _is_wrapper(f):
            return hasattr(f, '__wrapped__')
    else:
        def _is_wrapper(f):
            return hasattr(f, '__wrapped__') and not stop(f)
    f = func  # remember the original func for error reporting
    memo = {id(f)} # Memoise by id to tolerate non-hashable objects
    while _is_wrapper(func):
        func = func.__wrapped__
        id_func = id(func)
        if id_func in memo:
            raise ValueError('wrapper loop when unwrapping {!r}'.format(f))
        memo.add(id_func)
    return func

# -------------------------------------------------- source code extraction
def indentsize(line):
    """Return the indent size, in spaces, at the start of a line of text."""
    expline = string.expandtabs(line)
    return len(expline) - len(string.lstrip(expline))

def getdoc(object):
    """Get the documentation string for an object.

    All tabs are expanded to spaces.  To clean up docstrings that are
    indented to line up with blocks of code, any whitespace than can be
    uniformly removed from the second line onwards is removed."""
    try:
        doc = object.__doc__
    except AttributeError:
        return None
    if not isinstance(doc, types.StringTypes):
        return None
    return cleandoc(doc)

def cleandoc(doc):
    """Clean up indentation from docstrings.

    Any whitespace that can be uniformly removed from the second line
    onwards is removed."""
    try:
        lines = string.split(string.expandtabs(doc), '\n')
    except UnicodeError:
        return None
    else:
        # Find minimum indentation of any non-blank lines after first line.
        margin = sys.maxint
        for line in lines[1:]:
            content = len(string.lstrip(line))
            if content:
                indent = len(line) - content
                margin = min(margin, indent)
        # Remove indentation.
        if lines:
            lines[0] = lines[0].lstrip()
        if margin < sys.maxint:
            for i in range(1, len(lines)): lines[i] = lines[i][margin:]
        # Remove any trailing or leading blank lines.
        while lines and not lines[-1]:
            lines.pop()
        while lines and not lines[0]:
            lines.pop(0)
        return string.join(lines, '\n')

def getfile(object):
    """Work out which source or compiled file an object was defined in."""
    if ismodule(object):
        if hasattr(object, '__file__'):
            return object.__file__
        raise TypeError('{!r} is a built-in module'.format(object))
    if isclass(object):
        object = sys.modules.get(object.__module__)
        if hasattr(object, '__file__'):
            return object.__file__
        raise TypeError('{!r} is a built-in class'.format(object))
    if ismethod(object):
        object = object.im_func
    if isfunction(object):
        object = object.func_code
    if istraceback(object):
        object = object.tb_frame
    if isframe(object):
        object = object.f_code
    if iscode(object):
        return object.co_filename
    raise TypeError('{!r} is not a module, class, method, '
                    'function, traceback, frame, or code object'.format(object))

ModuleInfo = namedtuple('ModuleInfo', 'name suffix mode module_type')

def getmoduleinfo(path):
    """Get the module name, suffix, mode, and module type for a given file."""
    filename = os.path.basename(path)
    suffixes = map(lambda info:
                   (-len(info[0]), info[0], info[1], info[2]),
                    imp.get_suffixes())
    suffixes.sort() # try longest suffixes first, in case they overlap
    for neglen, suffix, mode, mtype in suffixes:
        if filename[neglen:] == suffix:
            return ModuleInfo(filename[:neglen], suffix, mode, mtype)

def getmodulename(path):
    """Return the module name for a given file, or None."""
    info = getmoduleinfo(path)
    if info: return info[0]

def getsourcefile(object):
    """Return the filename that can be used to locate an object's source.
    Return None if no way can be identified to get the source.
    """
    filename = getfile(object)
    if string.lower(filename[-4:]) in ('.pyc', '.pyo'):
        filename = filename[:-4] + '.py'
    for suffix, mode, kind in imp.get_suffixes():
        if 'b' in mode and string.lower(filename[-len(suffix):]) == suffix:
            # Looks like a binary file.  We want to only return a text file.
            return None
    if os.path.exists(filename):
        return filename
    # only return a non-existent filename if the module has a PEP 302 loader
    if hasattr(getmodule(object, filename), '__loader__'):
        return filename
    # or it is in the linecache
    if filename in linecache.cache:
        return filename

def getabsfile(object, _filename=None):
    """Return an absolute path to the source or compiled file for an object.

    The idea is for each object to have a unique origin, so this routine
    normalizes the result as much as possible."""
    if _filename is None:
        _filename = getsourcefile(object) or getfile(object)
    return os.path.normcase(os.path.abspath(_filename))

modulesbyfile = {}
_filesbymodname = {}

def getmodule(object, _filename=None):
    """Return the module an object was defined in, or None if not found."""
    if ismodule(object):
        return object
    if hasattr(object, '__module__'):
        return sys.modules.get(object.__module__)
    # Try the filename to modulename cache
    if _filename is not None and _filename in modulesbyfile:
        return sys.modules.get(modulesbyfile[_filename])
    # Try the cache again with the absolute file name
    try:
        file = getabsfile(object, _filename)
    except TypeError:
        return None
    if file in modulesbyfile:
        return sys.modules.get(modulesbyfile[file])
    # Update the filename to module name cache and check yet again
    # Copy sys.modules in order to cope with changes while iterating
    for modname, module in sys.modules.items():
        if ismodule(module) and hasattr(module, '__file__'):
            f = module.__file__
            if f == _filesbymodname.get(modname, None):
                # Have already mapped this module, so skip it
                continue
            _filesbymodname[modname] = f
            f = getabsfile(module)
            # Always map to the name the module knows itself by
            modulesbyfile[f] = modulesbyfile[
                os.path.realpath(f)] = module.__name__
    if file in modulesbyfile:
        return sys.modules.get(modulesbyfile[file])
    # Check the main module
    main = sys.modules['__main__']
    if not hasattr(object, '__name__'):
        return None
    if hasattr(main, object.__name__):
        mainobject = getattr(main, object.__name__)
        if mainobject is object:
            return main
    # Check builtins
    builtin = sys.modules['__builtin__']
    if hasattr(builtin, object.__name__):
        builtinobject = getattr(builtin, object.__name__)
        if builtinobject is object:
            return builtin

def findsource(object):
    """Return the entire source file and starting line number for an object.

    The argument may be a module, class, method, function, traceback, frame,
    or code object.  The source code is returned as a list of all the lines
    in the file and the line number indexes a line in that list.  An IOError
    is raised if the source code cannot be retrieved."""

    file = getfile(object)
    sourcefile = getsourcefile(object)
    if not sourcefile and file[:1] + file[-1:] != '<>':
        raise IOError('source code not available')
    file = sourcefile if sourcefile else file

    module = getmodule(object, file)
    if module:
        lines = linecache.getlines(file, module.__dict__)
    else:
        lines = linecache.getlines(file)
    if not lines:
        raise IOError('could not get source code')

    if ismodule(object):
        return lines, 0

    if isclass(object):
        name = object.__name__
        pat = re.compile(r'^(\s*)class\s*' + name + r'\b')
        # make some effort to find the best matching class definition:
        # use the one with the least indentation, which is the one
        # that's most probably not inside a function definition.
        candidates = []
        for i in range(len(lines)):
            match = pat.match(lines[i])
            if match:
                # if it's at toplevel, it's already the best one
                if lines[i][0] == 'c':
                    return lines, i
                # else add whitespace to candidate list
                candidates.append((match.group(1), i))
        if candidates:
            # this will sort by whitespace, and by line number,
            # less whitespace first
            candidates.sort()
            return lines, candidates[0][1]
        else:
            raise IOError('could not find class definition')

    if ismethod(object):
        object = object.im_func
    if isfunction(object):
        object = object.func_code
    if istraceback(object):
        object = object.tb_frame
    if isframe(object):
        object = object.f_code
    if iscode(object):
        if not hasattr(object, 'co_firstlineno'):
            raise IOError('could not find function definition')
        lnum = object.co_firstlineno - 1
        pat = re.compile(r'^(\s*def\s)|(\s*async\s+def\s)|(.*(?<!\w)lambda(:|\s))|^(\s*@)')
        while lnum > 0:
            if pat.match(lines[lnum]): break
            lnum = lnum - 1
        return lines, lnum
    raise IOError('could not find code object')

def getcomments(object):
    """Get lines of comments immediately preceding an object's source code.

    Returns None when source can't be found.
    """
    try:
        lines, lnum = findsource(object)
    except (IOError, TypeError):
        return None

    if ismodule(object):
        # Look for a comment block at the top of the file.
        start = 0
        if lines and lines[0][:2] == '#!': start = 1
        while start < len(lines) and string.strip(lines[start]) in ('', '#'):
            start = start + 1
        if start < len(lines) and lines[start][:1] == '#':
            comments = []
            end = start
            while end < len(lines) and lines[end][:1] == '#':
                comments.append(string.expandtabs(lines[end]))
                end = end + 1
            return string.join(comments, '')

    # Look for a preceding block of comments at the same indentation.
    elif lnum > 0:
        indent = indentsize(lines[lnum])
        end = lnum - 1
        if end >= 0 and string.lstrip(lines[end])[:1] == '#' and \
            indentsize(lines[end]) == indent:
            comments = [string.lstrip(string.expandtabs(lines[end]))]
            if end > 0:
                end = end - 1
                comment = string.lstrip(string.expandtabs(lines[end]))
                while comment[:1] == '#' and indentsize(lines[end]) == indent:
                    comments[:0] = [comment]
                    end = end - 1
                    if end < 0: break
                    comment = string.lstrip(string.expandtabs(lines[end]))
            while comments and string.strip(comments[0]) == '#':
                comments[:1] = []
            while comments and string.strip(comments[-1]) == '#':
                comments[-1:] = []
            return string.join(comments, '')

class EndOfBlock(Exception): pass

class BlockFinder:
    """Provide a tokeneater() method to detect the end of a code block."""
    def __init__(self):
        self.indent = 0
        self.islambda = False
        self.started = False
        self.passline = False
        self.last = 1

    def tokeneater(self, type, token, srow_scol, erow_ecol, line):
        srow, scol = srow_scol
        erow, ecol = erow_ecol
        if not self.started:
            # look for the first "def", "class" or "lambda"
            if token in ("def", "class", "lambda"):
                if token == "lambda":
                    self.islambda = True
                self.started = True
            self.passline = True    # skip to the end of the line
        elif type == tokenize.NEWLINE:
            self.passline = False   # stop skipping when a NEWLINE is seen
            self.last = srow
            if self.islambda:       # lambdas always end at the first NEWLINE
                raise EndOfBlock
        elif self.passline:
            pass
        elif type == tokenize.INDENT:
            self.indent = self.indent + 1
            self.passline = True
        elif type == tokenize.DEDENT:
            self.indent = self.indent - 1
            # the end of matching indent/dedent pairs end a block
            # (note that this only works for "def"/"class" blocks,
            #  not e.g. for "if: else:" or "try: finally:" blocks)
            if self.indent <= 0:
                raise EndOfBlock
        elif self.indent == 0 and type not in (tokenize.COMMENT, tokenize.NL):
            # any other token on the same indentation level end the previous
            # block as well, except the pseudo-tokens COMMENT and NL.
            raise EndOfBlock

def getblock(lines):
    """Extract the block of code at the top of the given list of lines."""
    blockfinder = BlockFinder()
    try:
        tokenize.tokenize(iter(lines).next, blockfinder.tokeneater)
    except (EndOfBlock, IndentationError):
        pass
    return lines[:blockfinder.last]

def getsourcelines(object):
    """Return a list of source lines and starting line number for an object.

    The argument may be a module, class, method, function, traceback, frame,
    or code object.  The source code is returned as a list of the lines
    corresponding to the object and the line number indicates where in the
    original source file the first line of code was found.  An IOError is
    raised if the source code cannot be retrieved."""
    lines, lnum = findsource(object)

    if istraceback(object):
        object = object.tb_frame

    # for module or frame that corresponds to module, return all source lines
    if (ismodule(object) or
        (isframe(object) and object.f_code.co_name == "<module>")):
        return lines, 0
    else:
        return getblock(lines[lnum:]), lnum + 1

def getsource(object):
    """Return the text of the source code for an object.

    The argument may be a module, class, method, function, traceback, frame,
    or code object.  The source code is returned as a single string.  An
    IOError is raised if the source code cannot be retrieved."""
    lines, lnum = getsourcelines(object)
    return string.join(lines, '')

# --------------------------------------------------- class tree extraction
def walktree(classes, children, parent):
    """Recursive helper function for getclasstree()."""
    results = []
    classes.sort(key=attrgetter('__module__', '__name__'))
    for c in classes:
        results.append((c, c.__bases__))
        if c in children:
            results.append(walktree(children[c], children, c))
    return results

def getclasstree(classes, unique=0):
    """Arrange the given list of classes into a hierarchy of nested lists.

    Where a nested list appears, it contains classes derived from the class
    whose entry immediately precedes the list.  Each entry is a 2-tuple
    containing a class and a tuple of its base classes.  If the 'unique'
    argument is true, exactly one entry appears in the returned structure
    for each class in the given list.  Otherwise, classes using multiple
    inheritance and their descendants will appear multiple times."""
    children = {}
    roots = []
    for c in classes:
        if c.__bases__:
            for parent in c.__bases__:
                if not parent in children:
                    children[parent] = []
                if c not in children[parent]:
                    children[parent].append(c)
                if unique and parent in classes: break
        elif c not in roots:
            roots.append(c)
    for parent in children:
        if parent not in classes:
            roots.append(parent)
    return walktree(roots, children, None)

# ------------------------------------------------ argument list extraction
Arguments = namedtuple('Arguments', 'args varargs keywords')

def getargs(co):
    """Get information about the arguments accepted by a code object.

    Three things are returned: (args, varargs, varkw), where
    'args' is the list of argument names, possibly containing nested
    lists. Keyword-only arguments are appended. 'varargs' and 'varkw'
    are the names of the * and ** arguments or None."""
    args, varargs, kwonlyargs, varkw = _getfullargs(co)
    return args + kwonlyargs, varargs, varkw

def _getfullargs(co):
    """Get information about the arguments accepted by a code object.

    Four things are returned: (args, varargs, kwonlyargs, varkw), where
    'args' and 'kwonlyargs' are lists of argument names (with 'args'
    possibly containing nested lists), and 'varargs' and 'varkw' are the
    names of the * and ** arguments or None."""

    if not iscode(co):
        raise TypeError('{!r} is not a code object'.format(co))

    nargs = co.co_argcount
    names = co.co_varnames
    nkwargs = co.co_kwonlyargcount
    args = list(names[:nargs])
    kwonlyargs = list(names[nargs:nargs+nkwargs])
    step = 0

    # The following acrobatics are for anonymous (tuple) arguments.
    for i in range(nargs):
        if args[i][:1] in ('', '.'):
            stack, remain, count = [], [], []
            while step < len(co.co_code):
                op = ord(co.co_code[step])
                step = step + 1
                if op >= dis.HAVE_ARGUMENT:
                    opname = dis.opname[op]
                    value = ord(co.co_code[step]) + ord(co.co_code[step+1])*256
                    step = step + 2
                    if opname in ('UNPACK_TUPLE', 'UNPACK_SEQUENCE'):
                        remain.append(value)
                        count.append(value)
                    elif opname in ('STORE_FAST', 'STORE_DEREF'):
                        if opname == 'STORE_FAST':
                            stack.append(names[value])
                        else:
                            stack.append(co.co_cellvars[value])

                        # Special case for sublists of length 1: def foo((bar))
                        # doesn't generate the UNPACK_TUPLE bytecode, so if
                        # `remain` is empty here, we have such a sublist.
                        if not remain:
                            stack[0] = [stack[0]]
                            break
                        else:
                            remain[-1] = remain[-1] - 1
                            while remain[-1] == 0:
                                remain.pop()
                                size = count.pop()
                                stack[-size:] = [stack[-size:]]
                                if not remain: break
                                remain[-1] = remain[-1] - 1
                            if not remain: break
            args[i] = stack[0]

    nargs += nkwargs
    varargs = None
    if co.co_flags & CO_VARARGS:
        varargs = co.co_varnames[nargs]
        nargs = nargs + 1
    varkw = None
    if co.co_flags & CO_VARKEYWORDS:
        varkw = co.co_varnames[nargs]
    return args, varargs, kwonlyargs, varkw


ArgSpec = namedtuple('ArgSpec', 'args varargs keywords defaults')

def getargspec(func):
    """Get the names and default values of a function's arguments.

    A tuple of four things is returned: (args, varargs, varkw, defaults).
    'args' is a list of the argument names (it may contain nested lists).
    'args' will include keyword-only argument names.
    'varargs' and 'varkw' are the names of the * and ** arguments or None.
    'defaults' is an n-tuple of the default values of the last n arguments.

    Use the getfullargspec() API for Python-3000 code, as annotations
    and keyword arguments are supported. getargspec() will raise ValueError
    if the func has either annotations or keyword arguments.
    """

    args, varargs, varkw, defaults, kwonlyargs, kwonlydefaults, ann = \
        getfullargspec(func)
    if kwonlyargs or ann:
        raise ValueError, ("Function has keyword-only arguments or annotations"
                           ", use getfullargspec() API which can support them")
    return ArgSpec(args, varargs, varkw, defaults)

def getfullargspec(func):
    """Get the names and default values of a function's arguments.

    A tuple of seven things is returned: (args, varargs, kwonlyargs,
    kwonlydefaults, varkw, defaults, annotations).
    'args' is a list of the argument names (it may contain nested lists).
    'varargs' and 'varkw' are the names of the * and ** arguments or None.
    'defaults' is an n-tuple of the default values of the last n arguments.
    'kwonlyargs' is a list of keyword-only argument names.
    'kwonlydefaults' is a dictionary mapping names from kwonlyargs to defaults.
    'annotations' is a dictionary mapping argument names to annotations.

    The first four items in the tuple correspond to getargspec().
    """

    if ismethod(func):
        func = func.im_func
    if not isfunction(func):
        raise TypeError('arg is not a Python function')
    args, varargs, kwonlyargs, varkw = _getfullargs(func.__code__)
    return (args, varargs, varkw, func.__defaults__,
            kwonlyargs, func.__kwdefaults__, func.__annotations__)

ArgInfo = namedtuple('ArgInfo', 'args varargs keywords locals')

def getargvalues(frame):
    """Get information about arguments passed into a particular frame.

    A tuple of four things is returned: (args, varargs, varkw, locals).
    'args' is a list of the argument names (it may contain nested lists).
    'varargs' and 'varkw' are the names of the * and ** arguments or None.
    'locals' is the locals dictionary of the given frame."""
    args, varargs, varkw = getargs(frame.f_code)
    return ArgInfo(args, varargs, varkw, frame.f_locals)

def joinseq(seq):
    if len(seq) == 1:
        return '(' + seq[0] + ',)'
    else:
        return '(' + string.join(seq, ', ') + ')'

def strseq(object, convert, join=joinseq):
    """Recursively walk a sequence, stringifying each element."""
    if type(object) in (list, tuple):
        return join(map(lambda o, c=convert, j=join: strseq(o, c, j), object))
    else:
        return convert(object)

def formatannotation(annotation, base_module=None):
    if isinstance(annotation, type):
        if annotation.__module__ in ('__builtin__', base_module):
            return annotation.__name__
        return annotation.__module__+'.'+annotation.__name__
    return repr(annotation)

def formatannotationrelativeto(object):
    module = getattr(object, '__module__', None)
    def _formatannotation(annotation):
        return formatannotation(annotation, module)
    return _formatannotation

def formatargspec(args, varargs=None, varkw=None, defaults=None,
                  kwonlyargs=(), kwonlydefaults={}, annotations={},
                  formatarg=str,
                  formatvarargs=lambda name: '*' + name,
                  formatvarkw=lambda name: '**' + name,
                  formatvalue=lambda value: '=' + repr(value),
                  formatreturns=lambda text: ' -> ' + text,
                  formatannotation=formatannotation,
                  join=joinseq):
    """Format an argument spec from the values returned by getargspec
    or getfullargspec.

    The first seven arguments are (args, varargs, varkw, defaults,
    kwonlyargs, kwonlydefaults, annotations).  The other five arguments
    are the corresponding optional formatting functions that are called to
    turn names and values into strings.  The last argument is an optional
    function to format the sequence of arguments."""
    def formatargandannotation(arg):
        result = formatarg(arg)
        if arg in annotations:
            result += ':' + formatannotation(annotations[arg])
        return result
    specs = []
    if defaults:
        firstdefault = len(args) - len(defaults)
    for i in range(len(args)):
        spec = strseq(args[i], formatargandannotation, join)
        if defaults and i >= firstdefault:
            spec = spec + formatvalue(defaults[i - firstdefault])
        specs.append(spec)
    if varargs is not None:
        specs.append(formatvarargs(formatargandannotation(varargs)))
    else:
        if kwonlyargs:
            specs.append('*')
    if kwonlyargs:
        for kwonlyarg in kwonlyargs:
            spec = formatargandannotation(kwonlyarg)
            if kwonlydefaults and kwonlyarg in kwonlydefaults:
                spec += formatvalue(kwonlydefaults[kwonlyarg])
            specs.append(spec)
    if varkw is not None:
        specs.append(formatvarkw(formatargandannotation(varkw)))
    result = '(' + ', '.join(specs) + ')'
    if 'return' in annotations:
        result += formatreturns(formatannotation(annotations['return']))
    return result

def formatargvalues(args, varargs, varkw, locals,
                    formatarg=str,
                    formatvarargs=lambda name: '*' + name,
                    formatvarkw=lambda name: '**' + name,
                    formatvalue=lambda value: '=' + repr(value),
                    join=joinseq):
    """Format an argument spec from the 4 values returned by getargvalues.

    The first four arguments are (args, varargs, varkw, locals).  The
    next four arguments are the corresponding optional formatting functions
    that are called to turn names and values into strings.  The ninth
    argument is an optional function to format the sequence of arguments."""
    def convert(name, locals=locals,
                formatarg=formatarg, formatvalue=formatvalue):
        return formatarg(name) + formatvalue(locals[name])
    specs = []
    for i in range(len(args)):
        specs.append(strseq(args[i], convert, join))
    if varargs:
        specs.append(formatvarargs(varargs) + formatvalue(locals[varargs]))
    if varkw:
        specs.append(formatvarkw(varkw) + formatvalue(locals[varkw]))
    return '(' + ', '.join(specs) + ')'

def getcallargs(func, *positional, **named):
    """Get the mapping of arguments to values.

    A dict is returned, with keys the function argument names (including the
    names of the * and ** arguments, if any), and values the respective bound
    values from 'positional' and 'named'."""
    args, varargs, varkw, defaults = getargspec(func)
    f_name = func.__name__
    arg2value = {}

    # The following closures are basically because of tuple parameter unpacking.
    assigned_tuple_params = []
    def assign(arg, value):
        if isinstance(arg, str):
            arg2value[arg] = value
        else:
            assigned_tuple_params.append(arg)
            value = iter(value)
            for i, subarg in enumerate(arg):
                try:
                    subvalue = next(value)
                except StopIteration:
                    raise ValueError('need more than %d %s to unpack' %
                                     (i, 'values' if i > 1 else 'value'))
                assign(subarg,subvalue)
            try:
                next(value)
            except StopIteration:
                pass
            else:
                raise ValueError('too many values to unpack')
    def is_assigned(arg):
        if isinstance(arg,str):
            return arg in arg2value
        return arg in assigned_tuple_params
    if ismethod(func) and func.im_self is not None:
        # implicit 'self' (or 'cls' for classmethods) argument
        positional = (func.im_self,) + positional
    num_pos = len(positional)
    num_total = num_pos + len(named)
    num_args = len(args)
    num_defaults = len(defaults) if defaults else 0
    for arg, value in zip(args, positional):
        assign(arg, value)
    if varargs:
        if num_pos > num_args:
            assign(varargs, positional[-(num_pos-num_args):])
        else:
            assign(varargs, ())
    elif 0 < num_args < num_pos:
        raise TypeError('%s() takes %s %d %s (%d given)' % (
            f_name, 'at most' if defaults else 'exactly', num_args,
            'arguments' if num_args > 1 else 'argument', num_total))
    elif num_args == 0 and num_total:
        if varkw:
            if num_pos:
                # XXX: We should use num_pos, but Python also uses num_total:
                raise TypeError('%s() takes exactly 0 arguments '
                                '(%d given)' % (f_name, num_total))
        else:
            raise TypeError('%s() takes no arguments (%d given)' %
                            (f_name, num_total))
    for arg in args:
        if isinstance(arg, str) and arg in named:
            if is_assigned(arg):
                raise TypeError("%s() got multiple values for keyword "
                                "argument '%s'" % (f_name, arg))
            else:
                assign(arg, named.pop(arg))
    if defaults:    # fill in any missing values with the defaults
        for arg, value in zip(args[-num_defaults:], defaults):
            if not is_assigned(arg):
                assign(arg, value)
    if varkw:
        assign(varkw, named)
    elif named:
        unexpected = next(iter(named))
        try:
            unicode
        except NameError:
            pass
        else:
            if isinstance(unexpected, unicode):
                unexpected = unexpected.encode(sys.getdefaultencoding(), 'replace')
        raise TypeError("%s() got an unexpected keyword argument '%s'" %
                        (f_name, unexpected))
    unassigned = num_args - len([arg for arg in args if is_assigned(arg)])
    if unassigned:
        num_required = num_args - num_defaults
        raise TypeError('%s() takes %s %d %s (%d given)' % (
            f_name, 'at least' if defaults else 'exactly', num_required,
            'arguments' if num_required > 1 else 'argument', num_total))
    return arg2value

# -------------------------------------------------- stack frame extraction

Traceback = namedtuple('Traceback', 'filename lineno function code_context index')

def getframeinfo(frame, context=1):
    """Get information about a frame or traceback object.

    A tuple of five things is returned: the filename, the line number of
    the current line, the function name, a list of lines of context from
    the source code, and the index of the current line within that list.
    The optional second argument specifies the number of lines of context
    to return, which are centered around the current line."""
    if istraceback(frame):
        lineno = frame.tb_lineno
        frame = frame.tb_frame
    else:
        lineno = frame.f_lineno
    if not isframe(frame):
        raise TypeError('{!r} is not a frame or traceback object'.format(frame))

    filename = getsourcefile(frame) or getfile(frame)
    if context > 0:
        start = lineno - 1 - context//2
        try:
            lines, lnum = findsource(frame)
        except IOError:
            lines = index = None
        else:
            start = max(start, 1)
            start = max(0, min(start, len(lines) - context))
            lines = lines[start:start+context]
            index = lineno - 1 - start
    else:
        lines = index = None

    return Traceback(filename, lineno, frame.f_code.co_name, lines, index)

def getlineno(frame):
    """Get the line number from a frame object, allowing for optimization."""
    # FrameType.f_lineno is now a descriptor that grovels co_lnotab
    return frame.f_lineno

def getouterframes(frame, context=1):
    """Get a list of records for a frame and all higher (calling) frames.

    Each record contains a frame object, filename, line number, function
    name, a list of lines of context, and index within the context."""
    framelist = []
    while frame:
        framelist.append((frame,) + getframeinfo(frame, context))
        frame = frame.f_back
    return framelist

def getinnerframes(tb, context=1):
    """Get a list of records for a traceback's frame and all lower frames.

    Each record contains a frame object, filename, line number, function
    name, a list of lines of context, and index within the context."""
    framelist = []
    while tb:
        framelist.append((tb.tb_frame,) + getframeinfo(tb, context))
        tb = tb.tb_next
    return framelist

if hasattr(sys, '_getframe'):
    currentframe = sys._getframe
else:
    currentframe = lambda _=None: None

def stack(context=1):
    """Return a list of records for the stack above the caller's frame."""
    return getouterframes(sys._getframe(1), context)

def trace(context=1):
    """Return a list of records for the stack below the current exception."""
    return getinnerframes(sys.exc_info()[2], context)


# ------------------------------------------------ generator introspection

GEN_CREATED = 'GEN_CREATED'
GEN_RUNNING = 'GEN_RUNNING'
GEN_SUSPENDED = 'GEN_SUSPENDED'
GEN_CLOSED = 'GEN_CLOSED'

def getgeneratorstate(generator):
    """Get current state of a generator-iterator.

    Possible states are:
      GEN_CREATED: Waiting to start execution.
      GEN_RUNNING: Currently being executed by the interpreter.
      GEN_SUSPENDED: Currently suspended at a yield expression.
      GEN_CLOSED: Execution has completed.
    """
    if generator.gi_running:
        return GEN_RUNNING
    if generator.gi_frame is None:
        return GEN_CLOSED
    if generator.gi_frame.f_lasti == -1:
        return GEN_CREATED
    return GEN_SUSPENDED


def getgeneratorlocals(generator):
    """
    Get the mapping of generator local variables to their current values.

    A dict is returned, with the keys the local variable names and values the
    bound values."""

    if not isgenerator(generator):
        raise TypeError("'{!r}' is not a Python generator".format(generator))

    frame = getattr(generator, "gi_frame", None)
    if frame is not None:
        return generator.gi_frame.f_locals
    else:
        return {}


# ------------------------------------------------ coroutine introspection

CORO_CREATED = 'CORO_CREATED'
CORO_RUNNING = 'CORO_RUNNING'
CORO_SUSPENDED = 'CORO_SUSPENDED'
CORO_CLOSED = 'CORO_CLOSED'

def getcoroutinestate(coroutine):
    """Get current state of a coroutine object.

    Possible states are:
      CORO_CREATED: Waiting to start execution.
      CORO_RUNNING: Currently being executed by the interpreter.
      CORO_SUSPENDED: Currently suspended at an await expression.
      CORO_CLOSED: Execution has completed.
    """
    if coroutine.cr_running:
        return CORO_RUNNING
    if coroutine.cr_frame is None:
        return CORO_CLOSED
    if coroutine.cr_frame.f_lasti == -1:
        return CORO_CREATED
    return CORO_SUSPENDED


def getcoroutinelocals(coroutine):
    """
    Get the mapping of coroutine local variables to their current values.

    A dict is returned, with the keys the local variable names and values the
    bound values."""
    frame = getattr(coroutine, "cr_frame", None)
    if frame is not None:
        return frame.f_locals
    else:
        return {}


###############################################################################
### Function Signature Object (PEP 362)
###############################################################################


_WrapperDescriptor = type(type.__call__)
_MethodWrapper = type(all.__call__)
_ClassMethodWrapper = type(float.__dict__['fromhex'])

_NonUserDefinedCallables = (_WrapperDescriptor,
                            _MethodWrapper,
                            _ClassMethodWrapper,
                            types.BuiltinFunctionType)


class _NEMixin(object):
    __slots__ = ('__weakref__',)

    def __ne__(self, other):
        return not self == other


def _signature_get_user_defined_method(cls, method_name):
    """Private helper. Checks if ``cls`` has an attribute
    named ``method_name`` and returns it only if it is a
    pure python function.
    """
    try:
        meth = getattr(cls, method_name)
    except AttributeError:
        return
    else:
        if not isinstance(meth, _NonUserDefinedCallables):
            # Once '__signature__' will be added to 'C'-level
            # callables, this check won't be necessary
            return meth


def _signature_get_partial(wrapped_sig, partial, extra_args=()):
    """Private helper to calculate how 'wrapped_sig' signature will
    look like after applying a 'functools.partial' object (or alike)
    on it.
    """

    def _move_to_end(od, key):
        od[key] = od.pop(key)

    old_params = wrapped_sig.parameters
    new_params = OrderedDict(old_params.items())

    partial_args = partial.args or ()
    partial_keywords = partial.keywords or {}

    if extra_args:
        partial_args = extra_args + partial_args

    try:
        ba = wrapped_sig.bind_partial(*partial_args, **partial_keywords)
    except TypeError as ex:
        msg = 'partial object {!r} has incorrect arguments'.format(partial)
        raise ValueError(msg)


    transform_to_kwonly = False
    for param_name, param in old_params.items():
        try:
            arg_value = ba.arguments[param_name]
        except KeyError:
            pass
        else:
            if param.kind is _POSITIONAL_ONLY:
                # If positional-only parameter is bound by partial,
                # it effectively disappears from the signature
                new_params.pop(param_name)
                continue

            if param.kind is _POSITIONAL_OR_KEYWORD:
                if param_name in partial_keywords:
                    # This means that this parameter, and all parameters
                    # after it should be keyword-only (and var-positional
                    # should be removed). Here's why. Consider the following
                    # function:
                    #     foo(a, b, *args, c):
                    #         pass
                    #
                    # "partial(foo, a='spam')" will have the following
                    # signature: "(*, a='spam', b, c)". Because attempting
                    # to call that partial with "(10, 20)" arguments will
                    # raise a TypeError, saying that "a" argument received
                    # multiple values.
                    transform_to_kwonly = True
                    # Set the new default value
                    new_params[param_name] = param.replace(default=arg_value)
                else:
                    # was passed as a positional argument
                    new_params.pop(param.name)
                    continue

            if param.kind is _KEYWORD_ONLY:
                # Set the new default value
                new_params[param_name] = param.replace(default=arg_value)

        if transform_to_kwonly:
            assert param.kind is not _POSITIONAL_ONLY

            if param.kind is _POSITIONAL_OR_KEYWORD:
                new_param = new_params[param_name].replace(kind=_KEYWORD_ONLY)
                new_params[param_name] = new_param
                _move_to_end(new_params, param_name)
            elif param.kind in (_KEYWORD_ONLY, _VAR_KEYWORD):
                _move_to_end(new_params, param_name)
            elif param.kind is _VAR_POSITIONAL:
                new_params.pop(param.name)

    return wrapped_sig.replace(parameters=new_params.values())


def _signature_bound_method(sig):
    """Private helper to transform signatures for unbound
    functions to bound methods.
    """

    params = tuple(sig.parameters.values())

    if not params or params[0].kind in (_VAR_KEYWORD, _KEYWORD_ONLY):
        raise ValueError('invalid method signature')

    kind = params[0].kind
    if kind in (_POSITIONAL_OR_KEYWORD, _POSITIONAL_ONLY):
        # Drop first parameter:
        # '(p1, p2[, ...])' -> '(p2[, ...])'
        params = params[1:]
    else:
        if kind is not _VAR_POSITIONAL:
            # Unless we add a new parameter type we never
            # get here
            raise ValueError('invalid argument type')
        # It's a var-positional parameter.
        # Do nothing. '(*args[, ...])' -> '(*args[, ...])'

    return sig.replace(parameters=params)


def _signature_is_builtin(obj):
    """Private helper to test if `obj` is a callable that might
    support Argument Clinic's __text_signature__ protocol.
    """
    return (isbuiltin(obj) or
            ismethoddescriptor(obj) or
            isinstance(obj, _NonUserDefinedCallables) or
            # Can't test 'isinstance(type)' here, as it would
            # also be True for regular python classes
            obj in (type, object))


def _signature_is_functionlike(obj):
    """Private helper to test if `obj` is a duck type of FunctionType.
    A good example of such objects are functions compiled with
    Cython, which have all attributes that a pure Python function
    would have, but have their code statically compiled.
    """

    if not callable(obj) or isclass(obj):
        # All function-like objects are obviously callables,
        # and not classes.
        return False

    name = getattr(obj, '__name__', None)
    code = getattr(obj, '__code__', None)
    defaults = getattr(obj, '__defaults__', _void) # Important to use _void ...
    kwdefaults = getattr(obj, '__kwdefaults__', _void) # ... and not None here
    annotations = getattr(obj, '__annotations__', None)

    return (isinstance(code, types.CodeType) and
            isinstance(name, str) and
            (defaults is None or isinstance(defaults, tuple)) and
            (kwdefaults is None or isinstance(kwdefaults, dict)) and
            isinstance(annotations, dict))


def _signature_get_bound_param(spec):
    """ Private helper to get first parameter name from a
    __text_signature__ of a builtin method, which should
    be in the following format: '($param1, ...)'.
    Assumptions are that the first argument won't have
    a default value or an annotation.
    """

    assert spec.startswith('($')

    pos = spec.find(',')
    if pos == -1:
        pos = spec.find(')')

    cpos = spec.find(':')
    assert cpos == -1 or cpos > pos

    cpos = spec.find('=')
    assert cpos == -1 or cpos > pos

    return spec[2:pos]


def _signature_strip_non_python_syntax(signature):
    """
    Private helper function. Takes a signature in Argument Clinic's
    extended signature format.

    Returns a tuple of three things:
      * that signature re-rendered in standard Python syntax,
      * the index of the "self" parameter (generally 0), or None if
        the function does not have a "self" parameter, and
      * the index of the last "positional only" parameter,
        or None if the signature has no positional-only parameters.
    """

    if not signature:
        return signature, None, None

    self_parameter = None
    last_positional_only = None

    lines = [l.encode('ascii') for l in signature.split('\n')]
    generator = iter(lines).next
    token_stream = tokenize.generate_tokens(generator)

    delayed_comma = False
    skip_next_comma = False
    text = []
    add = text.append

    current_parameter = 0
    OP = token.OP
    ERRORTOKEN = token.ERRORTOKEN

    for t in token_stream:
        type, string = t[0], t[1]

        if type == OP:
            if string == ',':
                if skip_next_comma:
                    skip_next_comma = False
                else:
                    assert not delayed_comma
                    delayed_comma = True
                    current_parameter += 1
                continue

            if string == '/':
                assert not skip_next_comma
                assert last_positional_only is None
                skip_next_comma = True
                last_positional_only = current_parameter - 1
                continue

        if (type == ERRORTOKEN) and (string == '$'):
            assert self_parameter is None
            self_parameter = current_parameter
            continue

        if delayed_comma:
            delayed_comma = False
            if not ((type == OP) and (string == ')')):
                add(', ')
        add(string)
        if (string == ','):
            add(' ')
    clean_signature = ''.join(text)
    return clean_signature, self_parameter, last_positional_only


def _signature_fromstr(cls, obj, s, skip_bound_arg=True):
    """Private helper to parse content of '__text_signature__'
    and return a Signature based on it.
    """

    Parameter = cls._parameter_cls

    clean_signature, self_parameter, last_positional_only = \
        _signature_strip_non_python_syntax(s)

    program = "def foo" + clean_signature + ": pass"

    try:
        module = ast.parse(program)
    except SyntaxError:
        module = None

    if not isinstance(module, ast.Module):
        raise ValueError("{!r} builtin has invalid signature".format(obj))

    f = module.body[0]

    parameters = []
    empty = Parameter.empty
    invalid = object()

    module = None
    module_dict = {}
    module_name = getattr(obj, '__module__', None)
    if module_name:
        module = sys.modules.get(module_name, None)
        if module:
            module_dict = module.__dict__
    sys_module_dict = sys.modules

    def parse_name(node):
        assert isinstance(node, ast.arg)
        if node.annotation != None:
            raise ValueError("Annotations are not currently supported")
        return node.arg

    def wrap_value(s):
        try:
            value = eval(s, module_dict)
        except NameError:
            try:
                value = eval(s, sys_module_dict)
            except NameError:
                raise RuntimeError()

        if isinstance(value, str):
            return ast.Str(value)
        if isinstance(value, (int, float)):
            return ast.Num(value)
        if isinstance(value, bytes):
            return ast.Bytes(value)
        if value in (True, False, None):
            return ast.NameConstant(value)
        raise RuntimeError()

    class RewriteSymbolics(ast.NodeTransformer):
        def visit_Attribute(self, node):
            a = []
            n = node
            while isinstance(n, ast.Attribute):
                a.append(n.attr)
                n = n.value
            if not isinstance(n, ast.Name):
                raise RuntimeError()
            a.append(n.id)
            value = ".".join(reversed(a))
            return wrap_value(value)

        def visit_Name(self, node):
            if not isinstance(node.ctx, ast.Load):
                raise ValueError()
            return wrap_value(node.id)

    def p(name_node, default_node, default=empty):
        name = parse_name(name_node)
        if name is invalid:
            return None
        if default_node and default_node is not _empty:
            try:
                default_node = RewriteSymbolics().visit(default_node)
                o = ast.literal_eval(default_node)
            except ValueError:
                o = invalid
            if o is invalid:
                return None
            default = o if o is not invalid else default
        parameters.append(Parameter(name, kind, default=default, annotation=empty))

    # non-keyword-only parameters
    args = reversed(f.args.args)
    defaults = reversed(f.args.defaults)
    iter = itertools.zip_longest(args, defaults, fillvalue=None)
    if last_positional_only is not None:
        kind = Parameter.POSITIONAL_ONLY
    else:
        kind = Parameter.POSITIONAL_OR_KEYWORD
    for i, (name, default) in enumerate(reversed(list(iter))):
        p(name, default)
        if i == last_positional_only:
            kind = Parameter.POSITIONAL_OR_KEYWORD

    # *args
    if f.args.vararg:
        kind = Parameter.VAR_POSITIONAL
        p(f.args.vararg, empty)

    # keyword-only arguments
    kind = Parameter.KEYWORD_ONLY
    for name, default in zip(f.args.kwonlyargs, f.args.kw_defaults):
        p(name, default)

    # **kwargs
    if f.args.kwarg:
        kind = Parameter.VAR_KEYWORD
        p(f.args.kwarg, empty)

    if self_parameter is not None:
        # Possibly strip the bound argument:
        #    - We *always* strip first bound argument if
        #      it is a module.
        #    - We don't strip first bound argument if
        #      skip_bound_arg is False.
        assert parameters
        _self = getattr(obj, '__self__', None)
        self_isbound = _self is not None
        self_ismodule = ismodule(_self)
        if self_isbound and (self_ismodule or skip_bound_arg):
            parameters.pop(0)
        else:
            # for builtins, self parameter is always positional-only!
            p = parameters[0].replace(kind=Parameter.POSITIONAL_ONLY)
            parameters[0] = p

    return cls(parameters, return_annotation=cls.empty)


def _signature_from_builtin(cls, func, skip_bound_arg=True):
    """Private helper function to get signature for
    builtin callables.
    """

    if not _signature_is_builtin(func):
        raise TypeError("{!r} is not a Python builtin "
                        "function".format(func))

    s = getattr(func, "__text_signature__", None)
    if not s:
        raise ValueError("no signature found for builtin {!r}".format(func))

    return _signature_fromstr(cls, func, s, skip_bound_arg)


def _signature_from_function(cls, func):
    """Private helper: constructs Signature for the given python function."""

    is_duck_function = False
    if not isfunction(func):
        if _signature_is_functionlike(func):
            is_duck_function = True
        else:
            # If it's not a pure Python function, and not a duck type
            # of pure function:
            raise TypeError('{!r} is not a Python function'.format(func))

    Parameter = cls._parameter_cls

    # Parameter information.
    func_code = func.__code__
    pos_count = func_code.co_argcount
    arg_names = func_code.co_varnames
    positional = tuple(arg_names[:pos_count])
    keyword_only_count = func_code.co_kwonlyargcount
    keyword_only = arg_names[pos_count:(pos_count + keyword_only_count)]
    annotations = func.__annotations__
    defaults = func.__defaults__
    kwdefaults = func.__kwdefaults__

    if defaults:
        pos_default_count = len(defaults)
    else:
        pos_default_count = 0

    parameters = []

    # Non-keyword-only parameters w/o defaults.
    non_default_count = pos_count - pos_default_count
    for name in positional[:non_default_count]:
        annotation = annotations.get(name, _empty)
        parameters.append(Parameter(name, annotation=annotation,
                                    kind=_POSITIONAL_OR_KEYWORD))

    # ... w/ defaults.
    for offset, name in enumerate(positional[non_default_count:]):
        annotation = annotations.get(name, _empty)
        parameters.append(Parameter(name, annotation=annotation,
                                    kind=_POSITIONAL_OR_KEYWORD,
                                    default=defaults[offset]))

    # *args
    if func_code.co_flags & CO_VARARGS:
        name = arg_names[pos_count + keyword_only_count]
        annotation = annotations.get(name, _empty)
        parameters.append(Parameter(name, annotation=annotation,
                                    kind=_VAR_POSITIONAL))

    # Keyword-only parameters.
    for name in keyword_only:
        default = _empty
        if kwdefaults is not None:
            default = kwdefaults.get(name, _empty)

        annotation = annotations.get(name, _empty)
        parameters.append(Parameter(name, annotation=annotation,
                                    kind=_KEYWORD_ONLY,
                                    default=default))
    # **kwargs
    if func_code.co_flags & CO_VARKEYWORDS:
        index = pos_count + keyword_only_count
        if func_code.co_flags & CO_VARARGS:
            index += 1

        name = arg_names[index]
        annotation = annotations.get(name, _empty)
        parameters.append(Parameter(name, annotation=annotation,
                                    kind=_VAR_KEYWORD))

    # Is 'func' is a pure Python function - don't validate the
    # parameters list (for correct order and defaults), it should be OK.
    return cls(parameters,
               return_annotation=annotations.get('return', _empty),
               __validate_parameters__=is_duck_function)


def _signature_from_callable(obj, *,
                             follow_wrapper_chains=True,
                             skip_bound_arg=True,
                             sigcls):

    """Private helper function to get signature for arbitrary
    callable objects.
    """

    if not callable(obj):
        raise TypeError('{!r} is not a callable object'.format(obj))

    if isinstance(obj, types.MethodType):
        # In this case we skip the first parameter of the underlying
        # function (usually `self` or `cls`).
        sig = _signature_from_callable(
            obj.__func__,
            follow_wrapper_chains=follow_wrapper_chains,
            skip_bound_arg=skip_bound_arg,
            sigcls=sigcls)

        is_bound_method = (obj.im_self is not None)

        if skip_bound_arg and is_bound_method:
            return _signature_bound_method(sig)
        else:
            return sig

    # Was this function wrapped by a decorator?
    if follow_wrapper_chains:
        obj = unwrap(obj, stop=(lambda f: hasattr(f, "__signature__")))
        if isinstance(obj, types.MethodType):
            # If the unwrapped object is a *method*, we might want to
            # skip its first parameter (self).
            # See test_signature_wrapped_bound_method for details.
            return _signature_from_callable(
                obj,
                follow_wrapper_chains=follow_wrapper_chains,
                skip_bound_arg=skip_bound_arg,
                sigcls=sigcls)

    try:
        sig = obj.__signature__
    except AttributeError:
        pass
    else:
        if sig is not None:
            if not isinstance(sig, Signature):
                raise TypeError(
                    'unexpected object {!r} in __signature__ '
                    'attribute'.format(sig))
            return sig

    if isfunction(obj) or _signature_is_functionlike(obj):
        # If it's a pure Python function, or an object that is duck type
        # of a Python function (Cython functions, for instance), then:
        return _signature_from_function(sigcls, obj)

    if _signature_is_builtin(obj):
        return _signature_from_builtin(sigcls, obj,
                                       skip_bound_arg=skip_bound_arg)

    if isinstance(obj, functools.partial):
        wrapped_sig = _signature_from_callable(
            obj.func,
            follow_wrapper_chains=follow_wrapper_chains,
            skip_bound_arg=skip_bound_arg,
            sigcls=sigcls)
        return _signature_get_partial(wrapped_sig, obj)

    sig = None
    if isinstance(obj, (type, types.ClassType)):
        # obj is a class or a metaclass

        # First, let's see if it has an overloaded __call__ defined
        # in its metaclass
        call = _signature_get_user_defined_method(type(obj), '__call__')
        if call is not None:
            sig = _signature_from_callable(
                call,
                follow_wrapper_chains=follow_wrapper_chains,
                skip_bound_arg=skip_bound_arg,
                sigcls=sigcls)
        else:
            # Now we check if the 'obj' class has a '__new__' method
            new = _signature_get_user_defined_method(obj, '__new__')
            if new is not None:
                sig = _signature_from_callable(
                    new,
                    follow_wrapper_chains=follow_wrapper_chains,
                    skip_bound_arg=skip_bound_arg,
                    sigcls=sigcls)
            else:
                # Finally, we should have at least __init__ implemented
                init = _signature_get_user_defined_method(obj, '__init__')
                if init is not None:
                    sig = _signature_from_callable(
                        init,
                        follow_wrapper_chains=follow_wrapper_chains,
                        skip_bound_arg=skip_bound_arg,
                        sigcls=sigcls)

        if sig is None:
            # At this point we know, that `obj` is a class, with no user-
            # defined '__init__', '__new__', or class-level '__call__'

            for base in obj.__mro__[:-1]:
                # Since '__text_signature__' is implemented as a
                # descriptor that extracts text signature from the
                # class docstring, if 'obj' is derived from a builtin
                # class, its own '__text_signature__' may be 'None'.
                # Therefore, we go through the MRO (except the last
                # class in there, which is 'object') to find the first
                # class with non-empty text signature.
                try:
                    text_sig = base.__text_signature__
                except AttributeError:
                    pass
                else:
                    if text_sig:
                        # If 'obj' class has a __text_signature__ attribute:
                        # return a signature based on it
                        return _signature_fromstr(sigcls, obj, text_sig)

            # No '__text_signature__' was found for the 'obj' class.
            # Last option is to check if its '__init__' is
            # object.__init__ or type.__init__.
            if type not in obj.__mro__:
                # We have a class (not metaclass), but no user-defined
                # __init__ or __new__ for it
                if (obj.__init__ is object.__init__ and
                    obj.__new__ is object.__new__):
                    # Return a signature of 'object' builtin.
                    return signature(object)
                else:
                    raise ValueError(
                        'no signature found for builtin type {!r}'.format(obj))

    elif not isinstance(obj, _NonUserDefinedCallables):
        # An object with __call__
        # We also check that the 'obj' is not an instance of
        # _WrapperDescriptor or _MethodWrapper to avoid
        # infinite recursion (and even potential segfault)
        if isinstance(obj, types.InstanceType):
            call = _signature_get_user_defined_method(obj.__class__, '__call__')
        else:
            call = _signature_get_user_defined_method(type(obj), '__call__')
        if call is not None:
            try:
                sig = _signature_from_callable(
                    call,
                    follow_wrapper_chains=follow_wrapper_chains,
                    skip_bound_arg=skip_bound_arg,
                    sigcls=sigcls)
            except ValueError as ex:
                msg = 'no signature found for {!r}'.format(obj)
                raise ValueError(msg)

    if sig is not None:
        # For classes and objects we skip the first parameter of their
        # __call__, __new__, or __init__ methods
        if skip_bound_arg:
            return _signature_bound_method(sig)
        else:
            return sig

    if isinstance(obj, types.BuiltinFunctionType):
        # Raise a nicer error message for builtins
        msg = 'no signature found for builtin function {!r}'.format(obj)
        raise ValueError(msg)

    raise ValueError('callable {!r} is not supported by signature'.format(obj))


class _void:
    """A private marker - used in Parameter & Signature."""


class _empty:
    """Marker object for Signature.empty and Parameter.empty."""


# This class taken from https://github.com/testing-cabal/funcsigs
class _ParameterKind(int):
    def __new__(self, val, name):
        obj = int.__new__(self, val)
        return obj

    def __init__(self, val, name):
        self._name = name

    def __str__(self):
        return self._name

    def __repr__(self):
        return '<_ParameterKind: {0!r}>'.format(self._name)

    def __getnewargs__(self):
        return (int(self), None)


_POSITIONAL_ONLY        = _ParameterKind(0, name='POSITIONAL_ONLY')
_POSITIONAL_OR_KEYWORD  = _ParameterKind(1, name='POSITIONAL_OR_KEYWORD')
_VAR_POSITIONAL         = _ParameterKind(2, name='VAR_POSITIONAL')
_KEYWORD_ONLY           = _ParameterKind(3, name='KEYWORD_ONLY')
_VAR_KEYWORD            = _ParameterKind(4, name='VAR_KEYWORD')


class Parameter(_NEMixin):
    """Represents a parameter in a function signature.

    Has the following public attributes:

    * name : str
        The name of the parameter as a string.
    * default : object
        The default value for the parameter if specified.  If the
        parameter has no default value, this attribute is set to
        `Parameter.empty`.
    * annotation
        The annotation for the parameter if specified.  If the
        parameter has no annotation, this attribute is set to
        `Parameter.empty`.
    * kind : str
        Describes how argument values are bound to the parameter.
        Possible values: `Parameter.POSITIONAL_ONLY`,
        `Parameter.POSITIONAL_OR_KEYWORD`, `Parameter.VAR_POSITIONAL`,
        `Parameter.KEYWORD_ONLY`, `Parameter.VAR_KEYWORD`.
    """

    __slots__ = ('_name', '_kind', '_default', '_annotation')

    POSITIONAL_ONLY         = _POSITIONAL_ONLY
    POSITIONAL_OR_KEYWORD   = _POSITIONAL_OR_KEYWORD
    VAR_POSITIONAL          = _VAR_POSITIONAL
    KEYWORD_ONLY            = _KEYWORD_ONLY
    VAR_KEYWORD             = _VAR_KEYWORD

    empty = _empty

    def __init__(self, name, kind, *, default=_empty, annotation=_empty):

        if kind not in (_POSITIONAL_ONLY, _POSITIONAL_OR_KEYWORD,
                        _VAR_POSITIONAL, _KEYWORD_ONLY, _VAR_KEYWORD):
            raise ValueError("invalid value for 'Parameter.kind' attribute")
        self._kind = kind

        if default is not _empty:
            if kind in (_VAR_POSITIONAL, _VAR_KEYWORD):
                msg = '{} parameters cannot have default values'.format(kind)
                raise ValueError(msg)
        self._default = default
        self._annotation = annotation

        if name is _empty:
            raise ValueError('name is a required attribute for Parameter')

        if not isinstance(name, str):
            raise TypeError("name must be a str, not a {!r}".format(name))

        if name[0] == '.' and name[1:].isdigit():
            # These are implicit arguments generated by comprehensions. In
            # order to provide a friendlier interface to users, we recast
            # their name as "implicitN" and treat them as positional-only.
            # See issue 19611.
            if kind != _POSITIONAL_OR_KEYWORD:
                raise ValueError(
                    'implicit arguments must be passed in as {}'.format(
                        _POSITIONAL_OR_KEYWORD
                    )
                )
            self._kind = _POSITIONAL_ONLY
            name = 'implicit{}'.format(name[1:])

        identifier = re.compile(r"^[^\d\W]\w*\Z")
        if not identifier.match(name):
            raise ValueError('{!r} is not a valid parameter name'.format(name))

        self._name = name

    def __reduce__(self):
        return (type(self),
                (self._name, self._kind),
                {'_default': self._default,
                 '_annotation': self._annotation})

    def __setstate__(self, state):
        self._default = state['_default']
        self._annotation = state['_annotation']

    @property
    def name(self):
        return self._name

    @property
    def default(self):
        return self._default

    @property
    def annotation(self):
        return self._annotation

    @property
    def kind(self):
        return self._kind

    def replace(self, *, name=_void, kind=_void,
                annotation=_void, default=_void):
        """Creates a customized copy of the Parameter."""

        if name is _void:
            name = self._name

        if kind is _void:
            kind = self._kind

        if annotation is _void:
            annotation = self._annotation

        if default is _void:
            default = self._default

        return type(self)(name, kind, default=default, annotation=annotation)

    def __str__(self):
        kind = self.kind
        formatted = self._name

        # Add annotation and default value
        if self._annotation is not _empty:
            formatted = '{}:{}'.format(formatted,
                                       formatannotation(self._annotation))

        if self._default is not _empty:
            formatted = '{}={}'.format(formatted, repr(self._default))

        if kind == _VAR_POSITIONAL:
            formatted = '*' + formatted
        elif kind == _VAR_KEYWORD:
            formatted = '**' + formatted

        return formatted

    def __repr__(self):
        return '<{} "{}">'.format(self.__class__.__name__, self)

    def __hash__(self):
        return hash((self.name, self.kind, self.annotation, self.default))

    def __eq__(self, other):
        if self is other:
            return True
        if not isinstance(other, Parameter):
            return NotImplemented
        return (self._name == other._name and
                self._kind == other._kind and
                self._default == other._default and
                self._annotation == other._annotation)


class BoundArguments(_NEMixin):
    """Result of `Signature.bind` call.  Holds the mapping of arguments
    to the function's parameters.

    Has the following public attributes:

    * arguments : OrderedDict
        An ordered mutable mapping of parameters' names to arguments' values.
        Does not contain arguments' default values.
    * signature : Signature
        The Signature object that created this instance.
    * args : tuple
        Tuple of positional arguments values.
    * kwargs : dict
        Dict of keyword arguments values.
    """

    __slots__ = ('arguments', '_signature')

    __hash__ = None

    def __init__(self, signature, arguments):
        self.arguments = arguments
        self._signature = signature

    @property
    def signature(self):
        return self._signature

    @property
    def args(self):
        args = []
        for param_name, param in self._signature.parameters.items():
            if param.kind in (_VAR_KEYWORD, _KEYWORD_ONLY):
                break

            try:
                arg = self.arguments[param_name]
            except KeyError:
                # We're done here. Other arguments
                # will be mapped in 'BoundArguments.kwargs'
                break
            else:
                if param.kind == _VAR_POSITIONAL:
                    # *args
                    args.extend(arg)
                else:
                    # plain argument
                    args.append(arg)

        return tuple(args)

    @property
    def kwargs(self):
        kwargs = {}
        kwargs_started = False
        for param_name, param in self._signature.parameters.items():
            if not kwargs_started:
                if param.kind in (_VAR_KEYWORD, _KEYWORD_ONLY):
                    kwargs_started = True
                else:
                    if param_name not in self.arguments:
                        kwargs_started = True
                        continue

            if not kwargs_started:
                continue

            try:
                arg = self.arguments[param_name]
            except KeyError:
                pass
            else:
                if param.kind == _VAR_KEYWORD:
                    # **kwargs
                    kwargs.update(arg)
                else:
                    # plain keyword argument
                    kwargs[param_name] = arg

        return kwargs

    def apply_defaults(self):
        """Set default values for missing arguments.

        For variable-positional arguments (*args) the default is an
        empty tuple.

        For variable-keyword arguments (**kwargs) the default is an
        empty dict.
        """
        arguments = self.arguments
        new_arguments = []
        for name, param in self._signature.parameters.items():
            try:
                new_arguments.append((name, arguments[name]))
            except KeyError:
                if param.default is not _empty:
                    val = param.default
                elif param.kind is _VAR_POSITIONAL:
                    val = ()
                elif param.kind is _VAR_KEYWORD:
                    val = {}
                else:
                    # This BoundArguments was likely produced by
                    # Signature.bind_partial().
                    continue
                new_arguments.append((name, val))
        self.arguments = OrderedDict(new_arguments)

    def __eq__(self, other):
        if self is other:
            return True
        if not isinstance(other, BoundArguments):
            return NotImplemented
        return (self.signature == other.signature and
                self.arguments == other.arguments)

    def __setstate__(self, state):
        self._signature = state['_signature']
        self.arguments = state['arguments']

    def __getstate__(self):
        return {'_signature': self._signature, 'arguments': self.arguments}

    def __repr__(self):
        args = []
        for arg, value in self.arguments.items():
            args.append('{}={!r}'.format(arg, value))
        return '<{} ({})>'.format(self.__class__.__name__, ', '.join(args))


class Signature(_NEMixin):
    """A Signature object represents the overall signature of a function.
    It stores a Parameter object for each parameter accepted by the
    function, as well as information specific to the function itself.

    A Signature object has the following public attributes and methods:

    * parameters : OrderedDict
        An ordered mapping of parameters' names to the corresponding
        Parameter objects (keyword-only arguments are in the same order
        as listed in `code.co_varnames`).
    * return_annotation : object
        The annotation for the return type of the function if specified.
        If the function has no annotation for its return type, this
        attribute is set to `Signature.empty`.
    * bind(*args, **kwargs) -> BoundArguments
        Creates a mapping from positional and keyword arguments to
        parameters.
    * bind_partial(*args, **kwargs) -> BoundArguments
        Creates a partial mapping from positional and keyword arguments
        to parameters (simulating 'functools.partial' behavior.)
    """

    __slots__ = ('_return_annotation', '_parameters')

    _parameter_cls = Parameter
    _bound_arguments_cls = BoundArguments

    empty = _empty

    def __init__(self, parameters=None, *, return_annotation=_empty,
                 __validate_parameters__=True):
        """Constructs Signature from the given list of Parameter
        objects and 'return_annotation'.  All arguments are optional.
        """

        if parameters is None:
            params = OrderedDict()
        else:
            if __validate_parameters__:
                params = OrderedDict()
                top_kind = _POSITIONAL_ONLY
                kind_defaults = False

                for idx, param in enumerate(parameters):
                    kind = param.kind
                    name = param.name

                    if kind < top_kind:
                        msg = 'wrong parameter order: {!r} before {!r}'
                        msg = msg.format(top_kind, kind)
                        raise ValueError(msg)
                    elif kind > top_kind:
                        kind_defaults = False
                        top_kind = kind

                    if kind in (_POSITIONAL_ONLY, _POSITIONAL_OR_KEYWORD):
                        if param.default is _empty:
                            if kind_defaults:
                                # No default for this parameter, but the
                                # previous parameter of the same kind had
                                # a default
                                msg = 'non-default argument follows default ' \
                                      'argument'
                                raise ValueError(msg)
                        else:
                            # There is a default for this parameter.
                            kind_defaults = True

                    if name in params:
                        msg = 'duplicate parameter name: {!r}'.format(name)
                        raise ValueError(msg)

                    params[name] = param
            else:
                params = OrderedDict(((param.name, param)
                                                for param in parameters))

        self._parameters = types.MappingProxyType(params)
        self._return_annotation = return_annotation

    @classmethod
    def from_function(cls, func):
        """Constructs Signature for the given python function."""

        warnings.warn("inspect.Signature.from_function() is deprecated, "
                      "use Signature.from_callable()",
                      DeprecationWarning, stacklevel=2)
        return _signature_from_function(cls, func)

    @classmethod
    def from_builtin(cls, func):
        """Constructs Signature for the given builtin function."""

        warnings.warn("inspect.Signature.from_builtin() is deprecated, "
                      "use Signature.from_callable()",
                      DeprecationWarning, stacklevel=2)
        return _signature_from_builtin(cls, func)

    @classmethod
    def from_callable(cls, obj, *, follow_wrapped=True):
        """Constructs Signature for the given callable object."""
        return _signature_from_callable(obj, sigcls=cls,
                                        follow_wrapper_chains=follow_wrapped)

    @property
    def parameters(self):
        return self._parameters

    @property
    def return_annotation(self):
        return self._return_annotation

    def replace(self, *, parameters=_void, return_annotation=_void):
        """Creates a customized copy of the Signature.
        Pass 'parameters' and/or 'return_annotation' arguments
        to override them in the new copy.
        """

        if parameters is _void:
            parameters = self.parameters.values()

        if return_annotation is _void:
            return_annotation = self._return_annotation

        return type(self)(parameters,
                          return_annotation=return_annotation)

    def _hash_basis(self):
        params = tuple(param for param in self.parameters.values()
                             if param.kind != _KEYWORD_ONLY)

        kwo_params = {param.name: param for param in self.parameters.values()
                                        if param.kind == _KEYWORD_ONLY}

        return params, kwo_params, self.return_annotation

    def __hash__(self):
        params, kwo_params, return_annotation = self._hash_basis()
        kwo_params = frozenset(kwo_params.values())
        return hash((params, kwo_params, return_annotation))

    def __eq__(self, other):
        if self is other:
            return True
        if not isinstance(other, Signature):
            return NotImplemented
        return self._hash_basis() == other._hash_basis()

    def _bind(self, args, kwargs, *, partial=False):
        """Private method. Don't use directly."""

        arguments = OrderedDict()

        parameters = iter(self.parameters.values())
        parameters_ex = ()
        arg_vals = iter(args)

        while True:
            # Let's iterate through the positional arguments and corresponding
            # parameters
            try:
                arg_val = next(arg_vals)
            except StopIteration:
                # No more positional arguments
                try:
                    param = next(parameters)
                except StopIteration:
                    # No more parameters. That's it. Just need to check that
                    # we have no `kwargs` after this while loop
                    break
                else:
                    if param.kind == _VAR_POSITIONAL:
                        # That's OK, just empty *args.  Let's start parsing
                        # kwargs
                        break
                    elif param.name in kwargs:
                        if param.kind == _POSITIONAL_ONLY:
                            msg = '{arg!r} parameter is positional only, ' \
                                  'but was passed as a keyword'
                            msg = msg.format(arg=param.name)
                            raise TypeError(msg)
                        parameters_ex = (param,)
                        break
                    elif (param.kind == _VAR_KEYWORD or
                                                param.default is not _empty):
                        # That's fine too - we have a default value for this
                        # parameter.  So, lets start parsing `kwargs`, starting
                        # with the current parameter
                        parameters_ex = (param,)
                        break
                    else:
                        # No default, not VAR_KEYWORD, not VAR_POSITIONAL,
                        # not in `kwargs`
                        if partial:
                            parameters_ex = (param,)
                            break
                        else:
                            msg = 'missing a required argument: {arg!r}'
                            msg = msg.format(arg=param.name)
                            raise TypeError(msg)
            else:
                # We have a positional argument to process
                try:
                    param = next(parameters)
                except StopIteration:
                    raise TypeError('too many positional arguments')
                else:
                    if param.kind in (_VAR_KEYWORD, _KEYWORD_ONLY):
                        # Looks like we have no parameter for this positional
                        # argument
                        raise TypeError(
                            'too many positional arguments')

                    if param.kind == _VAR_POSITIONAL:
                        # We have an '*args'-like argument, let's fill it with
                        # all positional arguments we have left and move on to
                        # the next phase
                        values = [arg_val]
                        values.extend(arg_vals)
                        arguments[param.name] = tuple(values)
                        break

                    if param.name in kwargs:
                        raise TypeError(
                            'multiple values for argument {arg!r}'.format(
                                arg=param.name))

                    arguments[param.name] = arg_val

        # Now, we iterate through the remaining parameters to process
        # keyword arguments
        kwargs_param = None
        for param in itertools.chain(parameters_ex, parameters):
            if param.kind == _VAR_KEYWORD:
                # Memorize that we have a '**kwargs'-like parameter
                kwargs_param = param
                continue

            if param.kind == _VAR_POSITIONAL:
                # Named arguments don't refer to '*args'-like parameters.
                # We only arrive here if the positional arguments ended
                # before reaching the last parameter before *args.
                continue

            param_name = param.name
            try:
                arg_val = kwargs.pop(param_name)
            except KeyError:
                # We have no value for this parameter.  It's fine though,
                # if it has a default value, or it is an '*args'-like
                # parameter, left alone by the processing of positional
                # arguments.
                if (not partial and param.kind != _VAR_POSITIONAL and
                                                    param.default is _empty):
                    raise TypeError('missing a required argument: {arg!r}'. \
                                    format(arg=param_name))

            else:
                if param.kind == _POSITIONAL_ONLY:
                    # This should never happen in case of a properly built
                    # Signature object (but let's have this check here
                    # to ensure correct behaviour just in case)
                    raise TypeError('{arg!r} parameter is positional only, '
                                    'but was passed as a keyword'. \
                                    format(arg=param.name))

                arguments[param_name] = arg_val

        if kwargs:
            if kwargs_param is not None:
                # Process our '**kwargs'-like parameter
                arguments[kwargs_param.name] = kwargs
            else:
                raise TypeError(
                    'got an unexpected keyword argument {arg!r}'.format(
                        arg=next(iter(kwargs))))

        return self._bound_arguments_cls(self, arguments)

    def bind(*args, **kwargs):
        """Get a BoundArguments object, that maps the passed `args`
        and `kwargs` to the function's signature.  Raises `TypeError`
        if the passed arguments can not be bound.
        """
        return args[0]._bind(args[1:], kwargs)

    def bind_partial(*args, **kwargs):
        """Get a BoundArguments object, that partially maps the
        passed `args` and `kwargs` to the function's signature.
        Raises `TypeError` if the passed arguments can not be bound.
        """
        return args[0]._bind(args[1:], kwargs, partial=True)

    def __reduce__(self):
        return (type(self),
                (tuple(self._parameters.values()),),
                {'_return_annotation': self._return_annotation})

    def __setstate__(self, state):
        self._return_annotation = state['_return_annotation']

    def __repr__(self):
        return '<{} {}>'.format(self.__class__.__name__, self)

    def __str__(self):
        result = []
        render_pos_only_separator = False
        render_kw_only_separator = True
        for param in self.parameters.values():
            formatted = str(param)

            kind = param.kind

            if kind == _POSITIONAL_ONLY:
                render_pos_only_separator = True
            elif render_pos_only_separator:
                # It's not a positional-only parameter, and the flag
                # is set to 'True' (there were pos-only params before.)
                result.append('/')
                render_pos_only_separator = False

            if kind == _VAR_POSITIONAL:
                # OK, we have an '*args'-like parameter, so we won't need
                # a '*' to separate keyword-only arguments
                render_kw_only_separator = False
            elif kind == _KEYWORD_ONLY and render_kw_only_separator:
                # We have a keyword-only parameter to render and we haven't
                # rendered an '*args'-like parameter before, so add a '*'
                # separator to the parameters list ("foo(arg1, *, arg2)" case)
                result.append('*')
                # This condition should be only triggered once, so
                # reset the flag
                render_kw_only_separator = False

            result.append(formatted)

        if render_pos_only_separator:
            # There were only positional-only parameters, hence the
            # flag was not reset to 'False'
            result.append('/')

        rendered = '({})'.format(', '.join(result))

        if self.return_annotation is not _empty:
            anno = formatannotation(self.return_annotation)
            rendered += ' -> {}'.format(anno)

        return rendered


def signature(obj, *, follow_wrapped=True):
    """Get a signature object for the passed callable."""
    return Signature.from_callable(obj, follow_wrapped=follow_wrapped)
