import re
import sys
import types
import unittest
import inspect
import linecache
import datetime
import textwrap
import warnings
import collections
import pickle
import functools
from contextlib import contextmanager
from UserList import UserList
from UserDict import UserDict

from test.support import (
    run_unittest, check_py3k_warnings, have_unicode, cpython_only
)

with check_py3k_warnings(
        ("tuple parameter unpacking has been removed", SyntaxWarning),
        quiet=True):
    from test import inspect_fodder as mod
    from test import inspect_fodder2 as mod2

MISSING_C_DOCSTRINGS = True

# C module for test_findsource_binary
try:
    import unicodedata
except ImportError:
    unicodedata = None

# Functions tested in this suite:
# ismodule, isclass, ismethod, isfunction, istraceback, isframe, iscode,
# isbuiltin, isroutine, isgenerator, isgeneratorfunction, getmembers,
# getdoc, getfile, getmodule, getsourcefile, getcomments, getsource,
# getclasstree, getargspec, getargvalues, formatargspec, formatargvalues,
# currentframe, stack, trace, isdatadescriptor

# NOTE: There are some additional tests relating to interaction with
#       zipimport in the test_zipimport_support test module.

modfile = mod.__file__
if modfile.endswith(('c', 'o')):
    modfile = modfile[:-1]

import __builtin__

try:
    1 // 0
except:
    tb = sys.exc_traceback

git = mod.StupidGit()

class IsTestBase(unittest.TestCase):
    predicates = set([inspect.isbuiltin, inspect.isclass, inspect.iscode,
                      inspect.isframe, inspect.isfunction, inspect.ismethod,
                      inspect.ismodule, inspect.istraceback,
                      inspect.isgenerator, inspect.isgeneratorfunction,
                      inspect.iscoroutine, inspect.iscoroutinefunction])


    def istest(self, predicate, exp):
        obj = eval(exp)
        self.assertTrue(predicate(obj), '%s(%s)' % (predicate.__name__, exp))

        for other in self.predicates - set([predicate]):
            if (predicate == inspect.isgeneratorfunction or \
               predicate == inspect.iscoroutinefunction) and \
               other == inspect.isfunction:
                continue
            self.assertFalse(other(obj), 'not %s(%s)' % (other.__name__, exp))

def generator_function_example(self):
    for i in xrange(2):
        yield i

async def coroutine_function_example(self):
    return 'spam'

@types.coroutine
def gen_coroutine_function_example(self):
    yield
    return 'spam'

class EqualsToAll:
    def __eq__(self, other):
        return True

class TestPredicates(IsTestBase):

    def test_excluding_predicates(self):
        self.istest(inspect.isbuiltin, 'sys.exit')
        self.istest(inspect.isbuiltin, '[].append')
        self.istest(inspect.iscode, 'mod.spam.func_code')
        self.istest(inspect.isframe, 'tb.tb_frame')
        self.istest(inspect.isfunction, 'mod.spam')
        self.istest(inspect.ismethod, 'mod.StupidGit.abuse')
        self.istest(inspect.ismethod, 'git.argue')
        self.istest(inspect.ismodule, 'mod')
        self.istest(inspect.istraceback, 'tb')
        self.istest(inspect.isdatadescriptor, '__builtin__.file.closed')
        self.istest(inspect.isdatadescriptor, '__builtin__.file.softspace')
        self.istest(inspect.isgenerator, '(x for x in xrange(2))')
        self.istest(inspect.isgeneratorfunction, 'generator_function_example')

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.istest(inspect.iscoroutine, 'coroutine_function_example(1)')
            self.istest(inspect.iscoroutinefunction, 'coroutine_function_example')

        if hasattr(types, 'GetSetDescriptorType'):
            self.istest(inspect.isgetsetdescriptor,
                        'type(tb.tb_frame).f_locals')
        else:
            self.assertFalse(inspect.isgetsetdescriptor(type(tb.tb_frame).f_locals))
        if hasattr(types, 'MemberDescriptorType'):
            self.istest(inspect.ismemberdescriptor, 'datetime.timedelta.days')
        else:
            self.assertFalse(inspect.ismemberdescriptor(datetime.timedelta.days))

    def test_iscoroutine(self):
        gen_coro = gen_coroutine_function_example(1)
        coro = coroutine_function_example(1)

        self.assertFalse(
            inspect.iscoroutinefunction(gen_coroutine_function_example))
        self.assertFalse(inspect.iscoroutine(gen_coro))

        self.assertTrue(
            inspect.isgeneratorfunction(gen_coroutine_function_example))
        self.assertTrue(inspect.isgenerator(gen_coro))

        self.assertTrue(
            inspect.iscoroutinefunction(coroutine_function_example))
        self.assertTrue(inspect.iscoroutine(coro))

        self.assertFalse(
            inspect.isgeneratorfunction(coroutine_function_example))
        self.assertFalse(inspect.isgenerator(coro))

        coro.close(); gen_coro.close() # silence warnings

    def test_isawaitable(self):
        def gen(): yield
        self.assertFalse(inspect.isawaitable(gen()))

        coro = coroutine_function_example(1)
        gen_coro = gen_coroutine_function_example(1)

        self.assertTrue(inspect.isawaitable(coro))
        self.assertTrue(inspect.isawaitable(gen_coro))

        class Future:
            def __await__():
                pass
        self.assertTrue(inspect.isawaitable(Future()))
        self.assertFalse(inspect.isawaitable(Future))

        class NotFuture: pass
        not_fut = NotFuture()
        not_fut.__await__ = lambda: None
        self.assertFalse(inspect.isawaitable(not_fut))

        coro.close(); gen_coro.close() # silence warnings

    def test_isroutine(self):
        self.assertTrue(inspect.isroutine(mod.spam))
        self.assertTrue(inspect.isroutine([].count))

    def test_isclass(self):
        self.istest(inspect.isclass, 'mod.StupidGit')
        self.assertTrue(inspect.isclass(list))

        class newstyle(object): pass
        self.assertTrue(inspect.isclass(newstyle))

        class CustomGetattr(object):
            def __getattr__(self, attr):
                return None
        self.assertFalse(inspect.isclass(CustomGetattr()))

    def test_get_slot_members(self):
        class C(object):
            __slots__ = ("a", "b")

        x = C()
        x.a = 42
        members = dict(inspect.getmembers(x))
        self.assertIn('a', members)
        self.assertNotIn('b', members)

    def test_isabstract(self):
        from abc import ABCMeta, abstractmethod

        class AbstractClassExample(object):
            __metaclass__ = ABCMeta

            @abstractmethod
            def foo(self):
                pass

        class ClassExample(AbstractClassExample):
            def foo(self):
                pass

        a = ClassExample()

        # Test general behaviour.
        self.assertTrue(inspect.isabstract(AbstractClassExample))
        self.assertFalse(inspect.isabstract(ClassExample))
        self.assertFalse(inspect.isabstract(a))
        self.assertFalse(inspect.isabstract(int))
        self.assertFalse(inspect.isabstract(5))


class TestInterpreterStack(IsTestBase):
    def __init__(self, *args, **kwargs):
        unittest.TestCase.__init__(self, *args, **kwargs)

        git.abuse(7, 8, 9)

    def test_abuse_done(self):
        self.istest(inspect.istraceback, 'git.ex[2]')
        self.istest(inspect.isframe, 'mod.fr')

    def test_stack(self):
        self.assertTrue(len(mod.st) >= 5)
        self.assertEqual(mod.st[0][1:],
             (modfile, 16, 'eggs', ['    st = inspect.stack()\n'], 0))
        self.assertEqual(mod.st[1][1:],
             (modfile, 9, 'spam', ['    eggs(b + d, c + f)\n'], 0))
        self.assertEqual(mod.st[2][1:],
             (modfile, 43, 'argue', ['            spam(a, b, c)\n'], 0))
        self.assertEqual(mod.st[3][1:],
             (modfile, 39, 'abuse', ['        self.argue(a, b, c)\n'], 0))

    def test_trace(self):
        self.assertEqual(len(git.tr), 3)
        self.assertEqual(git.tr[0][1:], (modfile, 43, 'argue',
                                         ['            spam(a, b, c)\n'], 0))
        self.assertEqual(git.tr[1][1:], (modfile, 9, 'spam',
                                         ['    eggs(b + d, c + f)\n'], 0))
        self.assertEqual(git.tr[2][1:], (modfile, 18, 'eggs',
                                         ['    q = y // 0\n'], 0))

    def test_frame(self):
        args, varargs, varkw, locals = inspect.getargvalues(mod.fr)
        self.assertEqual(args, ['x', 'y'])
        self.assertEqual(varargs, None)
        self.assertEqual(varkw, None)
        self.assertEqual(locals, {'x': 11, 'p': 11, 'y': 14})
        self.assertEqual(inspect.formatargvalues(args, varargs, varkw, locals),
                         '(x=11, y=14)')

    def test_previous_frame(self):
        args, varargs, varkw, locals = inspect.getargvalues(mod.fr.f_back)
        self.assertEqual(args, ['a', 'b', 'c', 'd', ['e', ['f']]])
        self.assertEqual(varargs, 'g')
        self.assertEqual(varkw, 'h')
        self.assertEqual(inspect.formatargvalues(args, varargs, varkw, locals),
             '(a=7, b=8, c=9, d=3, (e=4, (f=5,)), *g=(), **h={})')

class GetSourceBase(unittest.TestCase):
    # Subclasses must override.
    fodderFile = None

    def setUp(self):
        with open(inspect.getsourcefile(self.fodderFile)) as fp:
            self.source = fp.read()

    def sourcerange(self, top, bottom):
        lines = self.source.split("\n")
        return "\n".join(lines[top-1:bottom]) + ("\n" if bottom else "")

    def assertSourceEqual(self, obj, top, bottom):
        self.assertEqual(inspect.getsource(obj),
                         self.sourcerange(top, bottom))

class TestRetrievingSourceCode(GetSourceBase):
    fodderFile = mod

    def test_getclasses(self):
        classes = inspect.getmembers(mod, inspect.isclass)
        self.assertEqual(classes,
                         [('FesteringGob', mod.FesteringGob),
                          ('MalodorousPervert', mod.MalodorousPervert),
                          ('ParrotDroppings', mod.ParrotDroppings),
                          ('StupidGit', mod.StupidGit),
                          ('Tit', mod.MalodorousPervert),
                         ])
        tree = inspect.getclasstree([cls[1] for cls in classes])
        self.assertEqual(tree,
                         [(mod.ParrotDroppings, ()),
                          [(mod.FesteringGob, (mod.MalodorousPervert,
                                                  mod.ParrotDroppings))
                           ],
                          (mod.StupidGit, ()),
                          [(mod.MalodorousPervert, (mod.StupidGit,)),
                           [(mod.FesteringGob, (mod.MalodorousPervert,
                                                   mod.ParrotDroppings))
                            ]
                           ]
                          ])
        tree = inspect.getclasstree([cls[1] for cls in classes], True)
        self.assertEqual(tree,
                         [(mod.ParrotDroppings, ()),
                          (mod.StupidGit, ()),
                          [(mod.MalodorousPervert, (mod.StupidGit,)),
                           [(mod.FesteringGob, (mod.MalodorousPervert,
                                                   mod.ParrotDroppings))
                            ]
                           ]
                          ])

    def test_getfunctions(self):
        functions = inspect.getmembers(mod, inspect.isfunction)
        self.assertEqual(functions, [('eggs', mod.eggs),
                                     ('lobbest', mod.lobbest),
                                     ('spam', mod.spam)])

    @unittest.skipIf(sys.flags.optimize >= 2,
                     "Docstrings are omitted with -O2 and above")
    def test_getdoc(self):
        self.assertEqual(inspect.getdoc(mod), 'A module docstring.')
        self.assertEqual(inspect.getdoc(mod.StupidGit),
                         'A longer,\n\nindented\n\ndocstring.')
        self.assertEqual(inspect.getdoc(git.abuse),
                         'Another\n\ndocstring\n\ncontaining\n\ntabs')

    def test_cleandoc(self):
        self.assertEqual(inspect.cleandoc('An\n    indented\n    docstring.'),
                         'An\nindented\ndocstring.')

    def test_getcomments(self):
        self.assertEqual(inspect.getcomments(mod), '# line 1\n')
        self.assertEqual(inspect.getcomments(mod.StupidGit), '# line 20\n')

    def test_getmodule(self):
        # Check actual module
        self.assertEqual(inspect.getmodule(mod), mod)
        # Check class (uses __module__ attribute)
        self.assertEqual(inspect.getmodule(mod.StupidGit), mod)
        # Check a method (no __module__ attribute, falls back to filename)
        self.assertEqual(inspect.getmodule(mod.StupidGit.abuse), mod)
        # Do it again (check the caching isn't broken)
        self.assertEqual(inspect.getmodule(mod.StupidGit.abuse), mod)
        # Check a builtin
        self.assertEqual(inspect.getmodule(str), sys.modules["__builtin__"])
        # Check filename override
        self.assertEqual(inspect.getmodule(None, modfile), mod)

    def test_getsource(self):
        self.assertSourceEqual(git.abuse, 29, 39)
        self.assertSourceEqual(mod.StupidGit, 21, 46)
        self.assertSourceEqual(mod.lobbest, 60, 61)

    def test_getsourcefile(self):
        self.assertEqual(inspect.getsourcefile(mod.spam), modfile)
        self.assertEqual(inspect.getsourcefile(git.abuse), modfile)
        fn = "_non_existing_filename_used_for_sourcefile_test.py"
        co = compile("None", fn, "exec")
        self.assertEqual(inspect.getsourcefile(co), None)
        linecache.cache[co.co_filename] = (1, None, "None", co.co_filename)
        self.assertEqual(inspect.getsourcefile(co), fn)

    def test_getfile(self):
        self.assertEqual(inspect.getfile(mod.StupidGit), mod.__file__)

    def test_getmodule_recursion(self):
        from types import ModuleType
        name = '__inspect_dummy'
        m = sys.modules[name] = ModuleType(name)
        m.__file__ = "<string>" # hopefully not a real filename...
        m.__loader__ = "dummy"  # pretend the filename is understood by a loader
        exec "def x(): pass" in m.__dict__
        self.assertEqual(inspect.getsourcefile(m.x.func_code), '<string>')
        del sys.modules[name]
        inspect.getmodule(compile('a=10','','single'))

    def test_proceed_with_fake_filename(self):
        '''doctest monkeypatches linecache to enable inspection'''
        fn, source = '<test>', 'def x(): pass\n'
        getlines = linecache.getlines
        def monkey(filename, module_globals=None):
            if filename == fn:
                return source.splitlines(True)
            else:
                return getlines(filename, module_globals)
        linecache.getlines = monkey
        try:
            ns = {}
            exec compile(source, fn, 'single') in ns
            inspect.getsource(ns["x"])
        finally:
            linecache.getlines = getlines

class TestGettingSourceOfToplevelFrames(GetSourceBase):
    fodderFile = mod

    def test_range_toplevel_frame(self):
        self.maxDiff = None
        self.assertSourceEqual(mod.currentframe, 1, None)

    def test_range_traceback_toplevel_frame(self):
        self.assertSourceEqual(mod.tb, 1, None)

class TestDecorators(GetSourceBase):
    fodderFile = mod2

    def test_wrapped_decorator(self):
        self.assertSourceEqual(mod2.wrapped, 14, 17)

    def test_replacing_decorator(self):
        self.assertSourceEqual(mod2.gone, 9, 10)

class TestOneliners(GetSourceBase):
    fodderFile = mod2
    def test_oneline_lambda(self):
        # Test inspect.getsource with a one-line lambda function.
        self.assertSourceEqual(mod2.oll, 25, 25)

    def test_threeline_lambda(self):
        # Test inspect.getsource with a three-line lambda function,
        # where the second and third lines are _not_ indented.
        self.assertSourceEqual(mod2.tll, 28, 30)

    def test_twoline_indented_lambda(self):
        # Test inspect.getsource with a two-line lambda function,
        # where the second line _is_ indented.
        self.assertSourceEqual(mod2.tlli, 33, 34)

    def test_onelinefunc(self):
        # Test inspect.getsource with a regular one-line function.
        self.assertSourceEqual(mod2.onelinefunc, 37, 37)

    def test_manyargs(self):
        # Test inspect.getsource with a regular function where
        # the arguments are on two lines and _not_ indented and
        # the body on the second line with the last arguments.
        self.assertSourceEqual(mod2.manyargs, 40, 41)

    def test_twolinefunc(self):
        # Test inspect.getsource with a regular function where
        # the body is on two lines, following the argument list and
        # continued on the next line by a \\.
        self.assertSourceEqual(mod2.twolinefunc, 44, 45)

    def test_lambda_in_list(self):
        # Test inspect.getsource with a one-line lambda function
        # defined in a list, indented.
        self.assertSourceEqual(mod2.a[1], 49, 49)

    def test_anonymous(self):
        # Test inspect.getsource with a lambda function defined
        # as argument to another function.
        self.assertSourceEqual(mod2.anonymous, 55, 55)

class TestBuggyCases(GetSourceBase):
    fodderFile = mod2

    def test_with_comment(self):
        self.assertSourceEqual(mod2.with_comment, 58, 59)

    def test_multiline_sig(self):
        self.assertSourceEqual(mod2.multiline_sig[0], 63, 64)

    def test_nested_class(self):
        self.assertSourceEqual(mod2.func69().func71, 71, 72)

    def test_one_liner_followed_by_non_name(self):
        self.assertSourceEqual(mod2.func77, 77, 77)

    def test_one_liner_dedent_non_name(self):
        self.assertSourceEqual(mod2.cls82.func83, 83, 83)

    def test_with_comment_instead_of_docstring(self):
        self.assertSourceEqual(mod2.func88, 88, 90)

    def test_method_in_dynamic_class(self):
        self.assertSourceEqual(mod2.method_in_dynamic_class, 95, 97)

    @unittest.skipIf(
        not hasattr(unicodedata, '__file__') or
            unicodedata.__file__[-4:] in (".pyc", ".pyo"),
        "unicodedata is not an external binary module")
    def test_findsource_binary(self):
        self.assertRaises(IOError, inspect.getsource, unicodedata)
        self.assertRaises(IOError, inspect.findsource, unicodedata)

    def test_findsource_code_in_linecache(self):
        lines = ["x=1"]
        co = compile(lines[0], "_dynamically_created_file", "exec")
        self.assertRaises(IOError, inspect.findsource, co)
        self.assertRaises(IOError, inspect.getsource, co)
        linecache.cache[co.co_filename] = (1, None, lines, co.co_filename)
        self.assertEqual(inspect.findsource(co), (lines,0))
        self.assertEqual(inspect.getsource(co), lines[0])

    def test_findsource_without_filename(self):
        for fname in ['', '<string>']:
            co = compile('x=1', fname, "exec")
            self.assertRaises(IOError, inspect.findsource, co)
            self.assertRaises(IOError, inspect.getsource, co)


class _BrokenDataDescriptor(object):
    """
    A broken data descriptor. See bug #1785.
    """
    def __get__(*args):
        raise AssertionError("should not __get__ data descriptors")

    def __set__(*args):
        raise RuntimeError

    def __getattr__(*args):
        raise AssertionError("should not __getattr__ data descriptors")


class _BrokenMethodDescriptor(object):
    """
    A broken method descriptor. See bug #1785.
    """
    def __get__(*args):
        raise AssertionError("should not __get__ method descriptors")

    def __getattr__(*args):
        raise AssertionError("should not __getattr__ method descriptors")


# Helper for testing classify_class_attrs.
def attrs_wo_objs(cls):
    return [t[:3] for t in inspect.classify_class_attrs(cls)]


class TestClassesAndFunctions(unittest.TestCase):
    def test_classic_mro(self):
        # Test classic-class method resolution order.
        class A:    pass
        class B(A): pass
        class C(A): pass
        class D(B, C): pass

        expected = (D, B, A, C)
        got = inspect.getmro(D)
        self.assertEqual(expected, got)

    def test_newstyle_mro(self):
        # The same w/ new-class MRO.
        class A(object):    pass
        class B(A): pass
        class C(A): pass
        class D(B, C): pass

        expected = (D, B, C, A, object)
        got = inspect.getmro(D)
        self.assertEqual(expected, got)

    def assertArgSpecEquals(self, routine, args_e, varargs_e = None,
                            varkw_e = None, defaults_e = None,
                            formatted = None):
        args, varargs, varkw, defaults = inspect.getargspec(routine)
        self.assertEqual(args, args_e)
        self.assertEqual(varargs, varargs_e)
        self.assertEqual(varkw, varkw_e)
        self.assertEqual(defaults, defaults_e)
        if formatted is not None:
            self.assertEqual(inspect.formatargspec(args, varargs, varkw, defaults),
                             formatted)

    def test_getargspec(self):
        self.assertArgSpecEquals(mod.eggs, ['x', 'y'], formatted = '(x, y)')

        self.assertArgSpecEquals(mod.spam,
                                 ['a', 'b', 'c', 'd', ['e', ['f']]],
                                 'g', 'h', (3, (4, (5,))),
                                 '(a, b, c, d=3, (e, (f,))=(4, (5,)), *g, **h)')

        with check_py3k_warnings(("tuple parameter unpacking has been removed",
                                  SyntaxWarning),
                                 quiet=True):
            exec(textwrap.dedent('''
                def spam_deref(a, b, c, d=3, (e, (f,))=(4, (5,)), *g, **h):
                    def eggs():
                        return a + b + c + d + e + f + g + h
                    return eggs
            '''))
        self.assertArgSpecEquals(spam_deref,
                                 ['a', 'b', 'c', 'd', ['e', ['f']]],
                                 'g', 'h', (3, (4, (5,))),
                                 '(a, b, c, d=3, (e, (f,))=(4, (5,)), *g, **h)')

    def test_getargspec_method(self):
        class A(object):
            def m(self):
                pass
        self.assertArgSpecEquals(A.m, ['self'])

    def test_getargspec_sublistofone(self):
        with check_py3k_warnings(
                ("tuple parameter unpacking has been removed", SyntaxWarning),
                ("parenthesized argument names are invalid", SyntaxWarning)):
            exec 'def sublistOfOne((foo,)): return 1'
            self.assertArgSpecEquals(sublistOfOne, [['foo']])

            exec 'def sublistOfOne((foo,)): return (lambda: foo)'
            self.assertArgSpecEquals(sublistOfOne, [['foo']])

            exec 'def fakeSublistOfOne((foo)): return 1'
            self.assertArgSpecEquals(fakeSublistOfOne, ['foo'])

            exec 'def sublistOfOne((foo)): return (lambda: foo)'
            self.assertArgSpecEquals(sublistOfOne, ['foo'])


    def _classify_test(self, newstyle):
        """Helper for testing that classify_class_attrs finds a bunch of
        different kinds of attributes on a given class.
        """
        if newstyle:
            base = object
        else:
            class base:
                pass

        class A(base):
            def s(): pass
            s = staticmethod(s)

            def c(cls): pass
            c = classmethod(c)

            def getp(self): pass
            p = property(getp)

            def m(self): pass

            def m1(self): pass

            datablob = '1'

            dd = _BrokenDataDescriptor()
            md = _BrokenMethodDescriptor()

        attrs = attrs_wo_objs(A)
        self.assertIn(('s', 'static method', A), attrs, 'missing static method')
        self.assertIn(('c', 'class method', A), attrs, 'missing class method')
        self.assertIn(('p', 'property', A), attrs, 'missing property')
        self.assertIn(('m', 'method', A), attrs, 'missing plain method')
        self.assertIn(('m1', 'method', A), attrs, 'missing plain method')
        self.assertIn(('datablob', 'data', A), attrs, 'missing data')
        self.assertIn(('md', 'method', A), attrs, 'missing method descriptor')
        self.assertIn(('dd', 'data', A), attrs, 'missing data descriptor')

        class B(A):
            def m(self): pass

        attrs = attrs_wo_objs(B)
        self.assertIn(('s', 'static method', A), attrs, 'missing static method')
        self.assertIn(('c', 'class method', A), attrs, 'missing class method')
        self.assertIn(('p', 'property', A), attrs, 'missing property')
        self.assertIn(('m', 'method', B), attrs, 'missing plain method')
        self.assertIn(('m1', 'method', A), attrs, 'missing plain method')
        self.assertIn(('datablob', 'data', A), attrs, 'missing data')
        self.assertIn(('md', 'method', A), attrs, 'missing method descriptor')
        self.assertIn(('dd', 'data', A), attrs, 'missing data descriptor')


        class C(A):
            def m(self): pass
            def c(self): pass

        attrs = attrs_wo_objs(C)
        self.assertIn(('s', 'static method', A), attrs, 'missing static method')
        self.assertIn(('c', 'method', C), attrs, 'missing plain method')
        self.assertIn(('p', 'property', A), attrs, 'missing property')
        self.assertIn(('m', 'method', C), attrs, 'missing plain method')
        self.assertIn(('m1', 'method', A), attrs, 'missing plain method')
        self.assertIn(('datablob', 'data', A), attrs, 'missing data')
        self.assertIn(('md', 'method', A), attrs, 'missing method descriptor')
        self.assertIn(('dd', 'data', A), attrs, 'missing data descriptor')

        class D(B, C):
            def m1(self): pass

        attrs = attrs_wo_objs(D)
        self.assertIn(('s', 'static method', A), attrs, 'missing static method')
        if newstyle:
            self.assertIn(('c', 'method', C), attrs, 'missing plain method')
        else:
            self.assertIn(('c', 'class method', A), attrs, 'missing class method')
        self.assertIn(('p', 'property', A), attrs, 'missing property')
        self.assertIn(('m', 'method', B), attrs, 'missing plain method')
        self.assertIn(('m1', 'method', D), attrs, 'missing plain method')
        self.assertIn(('datablob', 'data', A), attrs, 'missing data')
        self.assertIn(('md', 'method', A), attrs, 'missing method descriptor')
        self.assertIn(('dd', 'data', A), attrs, 'missing data descriptor')


    def test_classify_oldstyle(self):
        """classify_class_attrs finds static methods, class methods,
        properties, normal methods, and data attributes on an old-style
        class.
        """
        self._classify_test(False)


    def test_classify_newstyle(self):
        """Just like test_classify_oldstyle, but for a new-style class.
        """
        self._classify_test(True)

    def test_classify_builtin_types(self):
        # Simple sanity check that all built-in types can have their
        # attributes classified.
        for name in dir(__builtin__):
            builtin = getattr(__builtin__, name)
            if isinstance(builtin, type):
                inspect.classify_class_attrs(builtin)

    def test_classify_overrides_bool(self):
        class NoBool(object):
            def __eq__(self, other):
                return NoBool()

            def __bool__(self):
                raise NotImplementedError(
                    "This object does not specify a boolean value")

        class HasNB(object):
            dd = NoBool()

        should_find_attr = inspect.Attribute('dd', 'data', HasNB, HasNB.dd)
        self.assertIn(should_find_attr, inspect.classify_class_attrs(HasNB))

    def test_getmembers_method(self):
        # Old-style classes
        class B:
            def f(self):
                pass

        self.assertIn(('f', B.f), inspect.getmembers(B))
        # contrary to spec, ismethod() is also True for unbound methods
        # (see #1785)
        self.assertIn(('f', B.f), inspect.getmembers(B, inspect.ismethod))
        b = B()
        self.assertIn(('f', b.f), inspect.getmembers(b))
        self.assertIn(('f', b.f), inspect.getmembers(b, inspect.ismethod))

        # New-style classes
        class B(object):
            def f(self):
                pass

        self.assertIn(('f', B.f), inspect.getmembers(B))
        self.assertIn(('f', B.f), inspect.getmembers(B, inspect.ismethod))
        b = B()
        self.assertIn(('f', b.f), inspect.getmembers(b))
        self.assertIn(('f', b.f), inspect.getmembers(b, inspect.ismethod))


class TestGetcallargsFunctions(unittest.TestCase):

    # tuple parameters are named '.1', '.2', etc.
    is_tuplename = re.compile(r'^\.\d+$').match

    def assertEqualCallArgs(self, func, call_params_string, locs=None):
        locs = dict(locs or {}, func=func)
        r1 = eval('func(%s)' % call_params_string, None, locs)
        r2 = eval('inspect.getcallargs(func, %s)' % call_params_string, None,
                  locs)
        self.assertEqual(r1, r2)

    def assertEqualException(self, func, call_param_string, locs=None):
        locs = dict(locs or {}, func=func)
        try:
            eval('func(%s)' % call_param_string, None, locs)
        except Exception, ex1:
            pass
        else:
            self.fail('Exception not raised')
        try:
            eval('inspect.getcallargs(func, %s)' % call_param_string, None,
                 locs)
        except Exception, ex2:
            pass
        else:
            self.fail('Exception not raised')
        self.assertIs(type(ex1), type(ex2))
        self.assertEqual(str(ex1), str(ex2))

    def makeCallable(self, signature):
        """Create a function that returns its locals(), excluding the
        autogenerated '.1', '.2', etc. tuple param names (if any)."""
        with check_py3k_warnings(
            ("tuple parameter unpacking has been removed", SyntaxWarning),
            quiet=True):
            code = ("lambda %s: dict(i for i in locals().items() "
                    "if not is_tuplename(i[0]))")
            return eval(code % signature, {'is_tuplename' : self.is_tuplename})

    def test_plain(self):
        f = self.makeCallable('a, b=1')
        self.assertEqualCallArgs(f, '2')
        self.assertEqualCallArgs(f, '2, 3')
        self.assertEqualCallArgs(f, 'a=2')
        self.assertEqualCallArgs(f, 'b=3, a=2')
        self.assertEqualCallArgs(f, '2, b=3')
        # expand *iterable / **mapping
        self.assertEqualCallArgs(f, '*(2,)')
        self.assertEqualCallArgs(f, '*[2]')
        self.assertEqualCallArgs(f, '*(2, 3)')
        self.assertEqualCallArgs(f, '*[2, 3]')
        self.assertEqualCallArgs(f, '**{"a":2}')
        self.assertEqualCallArgs(f, 'b=3, **{"a":2}')
        self.assertEqualCallArgs(f, '2, **{"b":3}')
        self.assertEqualCallArgs(f, '**{"b":3, "a":2}')
        # expand UserList / UserDict
        self.assertEqualCallArgs(f, '*UserList([2])')
        self.assertEqualCallArgs(f, '*UserList([2, 3])')
        self.assertEqualCallArgs(f, '**UserDict(a=2)')
        self.assertEqualCallArgs(f, '2, **UserDict(b=3)')
        self.assertEqualCallArgs(f, 'b=2, **UserDict(a=3)')
        # unicode keyword args
        self.assertEqualCallArgs(f, '**{u"a":2}')
        self.assertEqualCallArgs(f, 'b=3, **{u"a":2}')
        self.assertEqualCallArgs(f, '2, **{u"b":3}')
        self.assertEqualCallArgs(f, '**{u"b":3, u"a":2}')

    def test_varargs(self):
        f = self.makeCallable('a, b=1, *c')
        self.assertEqualCallArgs(f, '2')
        self.assertEqualCallArgs(f, '2, 3')
        self.assertEqualCallArgs(f, '2, 3, 4')
        self.assertEqualCallArgs(f, '*(2,3,4)')
        self.assertEqualCallArgs(f, '2, *[3,4]')
        self.assertEqualCallArgs(f, '2, 3, *UserList([4])')

    def test_varkw(self):
        f = self.makeCallable('a, b=1, **c')
        self.assertEqualCallArgs(f, 'a=2')
        self.assertEqualCallArgs(f, '2, b=3, c=4')
        self.assertEqualCallArgs(f, 'b=3, a=2, c=4')
        self.assertEqualCallArgs(f, 'c=4, **{"a":2, "b":3}')
        self.assertEqualCallArgs(f, '2, c=4, **{"b":3}')
        self.assertEqualCallArgs(f, 'b=2, **{"a":3, "c":4}')
        self.assertEqualCallArgs(f, '**UserDict(a=2, b=3, c=4)')
        self.assertEqualCallArgs(f, '2, c=4, **UserDict(b=3)')
        self.assertEqualCallArgs(f, 'b=2, **UserDict(a=3, c=4)')
        # unicode keyword args
        self.assertEqualCallArgs(f, 'c=4, **{u"a":2, u"b":3}')
        self.assertEqualCallArgs(f, '2, c=4, **{u"b":3}')
        self.assertEqualCallArgs(f, 'b=2, **{u"a":3, u"c":4}')

    def test_varkw_only(self):
        # issue11256:
        f = self.makeCallable('**c')
        self.assertEqualCallArgs(f, '')
        self.assertEqualCallArgs(f, 'a=1')
        self.assertEqualCallArgs(f, 'a=1, b=2')
        self.assertEqualCallArgs(f, 'c=3, **{"a": 1, "b": 2}')
        self.assertEqualCallArgs(f, '**UserDict(a=1, b=2)')
        self.assertEqualCallArgs(f, 'c=3, **UserDict(a=1, b=2)')

    def test_tupleargs(self):
        f = self.makeCallable('(b,c), (d,(e,f))=(0,[1,2])')
        self.assertEqualCallArgs(f, '(2,3)')
        self.assertEqualCallArgs(f, '[2,3]')
        self.assertEqualCallArgs(f, 'UserList([2,3])')
        self.assertEqualCallArgs(f, '(2,3), (4,(5,6))')
        self.assertEqualCallArgs(f, '(2,3), (4,[5,6])')
        self.assertEqualCallArgs(f, '(2,3), [4,UserList([5,6])]')

    def test_multiple_features(self):
        f = self.makeCallable('a, b=2, (c,(d,e))=(3,[4,5]), *f, **g')
        self.assertEqualCallArgs(f, '2, 3, (4,[5,6]), 7')
        self.assertEqualCallArgs(f, '2, 3, *[(4,[5,6]), 7], x=8')
        self.assertEqualCallArgs(f, '2, 3, x=8, *[(4,[5,6]), 7]')
        self.assertEqualCallArgs(f, '2, x=8, *[3, (4,[5,6]), 7], y=9')
        self.assertEqualCallArgs(f, 'x=8, *[2, 3, (4,[5,6])], y=9')
        self.assertEqualCallArgs(f, 'x=8, *UserList([2, 3, (4,[5,6])]), '
                                 '**{"y":9, "z":10}')
        self.assertEqualCallArgs(f, '2, x=8, *UserList([3, (4,[5,6])]), '
                                 '**UserDict(y=9, z=10)')

    def test_errors(self):
        f0 = self.makeCallable('')
        f1 = self.makeCallable('a, b')
        f2 = self.makeCallable('a, b=1')
        # f0 takes no arguments
        self.assertEqualException(f0, '1')
        self.assertEqualException(f0, 'x=1')
        self.assertEqualException(f0, '1,x=1')
        # f1 takes exactly 2 arguments
        self.assertEqualException(f1, '')
        self.assertEqualException(f1, '1')
        self.assertEqualException(f1, 'a=2')
        self.assertEqualException(f1, 'b=3')
        # f2 takes at least 1 argument
        self.assertEqualException(f2, '')
        self.assertEqualException(f2, 'b=3')
        for f in f1, f2:
            # f1/f2 takes exactly/at most 2 arguments
            self.assertEqualException(f, '2, 3, 4')
            self.assertEqualException(f, '1, 2, 3, a=1')
            self.assertEqualException(f, '2, 3, 4, c=5')
            self.assertEqualException(f, '2, 3, 4, a=1, c=5')
            # f got an unexpected keyword argument
            self.assertEqualException(f, 'c=2')
            self.assertEqualException(f, '2, c=3')
            self.assertEqualException(f, '2, 3, c=4')
            self.assertEqualException(f, '2, c=4, b=3')
            if have_unicode:
                self.assertEqualException(f, '**{u"\u03c0\u03b9": 4}')
            # f got multiple values for keyword argument
            self.assertEqualException(f, '1, a=2')
            self.assertEqualException(f, '1, **{"a":2}')
            self.assertEqualException(f, '1, 2, b=3')
            # XXX: Python inconsistency
            # - for functions and bound methods: unexpected keyword 'c'
            # - for unbound methods: multiple values for keyword 'a'
            #self.assertEqualException(f, '1, c=3, a=2')
        f = self.makeCallable('(a,b)=(0,1)')
        self.assertEqualException(f, '1')
        self.assertEqualException(f, '[1]')
        self.assertEqualException(f, '(1,2,3)')
        # issue11256:
        f3 = self.makeCallable('**c')
        self.assertEqualException(f3, '1, 2')
        self.assertEqualException(f3, '1, 2, a=1, b=2')


class TestGetcallargsFunctionsCellVars(TestGetcallargsFunctions):

    def makeCallable(self, signature):
        """Create a function that returns its locals(), excluding the
        autogenerated '.1', '.2', etc. tuple param names (if any)."""
        with check_py3k_warnings(
            ("tuple parameter unpacking has been removed", SyntaxWarning),
            quiet=True):
            code = """lambda %s: (
                    (lambda: a+b+c+d+d+e+f+g+h), # make parameters cell vars
                    dict(i for i in locals().items()
                         if not is_tuplename(i[0]))
                )[1]"""
            return eval(code % signature, {'is_tuplename' : self.is_tuplename})


class TestGetcallargsMethods(TestGetcallargsFunctions):

    def setUp(self):
        class Foo(object):
            pass
        self.cls = Foo
        self.inst = Foo()

    def makeCallable(self, signature):
        assert 'self' not in signature
        mk = super(TestGetcallargsMethods, self).makeCallable
        self.cls.method = mk('self, ' + signature)
        return self.inst.method

class TestGetcallargsUnboundMethods(TestGetcallargsMethods):

    def makeCallable(self, signature):
        super(TestGetcallargsUnboundMethods, self).makeCallable(signature)
        return self.cls.method

    def assertEqualCallArgs(self, func, call_params_string, locs=None):
        return super(TestGetcallargsUnboundMethods, self).assertEqualCallArgs(
            *self._getAssertEqualParams(func, call_params_string, locs))

    def assertEqualException(self, func, call_params_string, locs=None):
        return super(TestGetcallargsUnboundMethods, self).assertEqualException(
            *self._getAssertEqualParams(func, call_params_string, locs))

    def _getAssertEqualParams(self, func, call_params_string, locs=None):
        assert 'inst' not in call_params_string
        locs = dict(locs or {}, inst=self.inst)
        return (func, 'inst,' + call_params_string, locs)


class TestGetGeneratorState(unittest.TestCase):

    def setUp(self):
        def number_generator():
            for number in range(5):
                yield number
        self.generator = number_generator()

    def _generatorstate(self):
        return inspect.getgeneratorstate(self.generator)

    def test_created(self):
        self.assertEqual(self._generatorstate(), inspect.GEN_CREATED)

    def test_suspended(self):
        next(self.generator)
        self.assertEqual(self._generatorstate(), inspect.GEN_SUSPENDED)

    def test_closed_after_exhaustion(self):
        for i in self.generator:
            pass
        self.assertEqual(self._generatorstate(), inspect.GEN_CLOSED)

    def test_closed_after_immediate_exception(self):
        with self.assertRaises(RuntimeError):
            self.generator.throw(RuntimeError)
        self.assertEqual(self._generatorstate(), inspect.GEN_CLOSED)

    def test_running(self):
        # As mentioned on issue #10220, checking for the RUNNING state only
        # makes sense inside the generator itself.
        # The following generator checks for this by using the closure's
        # reference to self and the generator state checking helper method
        def running_check_generator():
            for number in range(5):
                self.assertEqual(self._generatorstate(), inspect.GEN_RUNNING)
                yield number
                self.assertEqual(self._generatorstate(), inspect.GEN_RUNNING)
        self.generator = running_check_generator()
        # Running up to the first yield
        next(self.generator)
        # Running after the first yield
        next(self.generator)

    def test_easy_debugging(self):
        # repr() and str() of a generator state should contain the state name
        names = 'GEN_CREATED GEN_RUNNING GEN_SUSPENDED GEN_CLOSED'.split()
        for name in names:
            state = getattr(inspect, name)
            self.assertIn(name, repr(state))
            self.assertIn(name, str(state))

    def test_getgeneratorlocals(self):
        def each(lst, a=None):
            b=(1, 2, 3)
            for v in lst:
                if v == 3:
                    c = 12
                yield v

        numbers = each([1, 2, 3])
        self.assertEqual(inspect.getgeneratorlocals(numbers),
                         {'a': None, 'lst': [1, 2, 3]})
        next(numbers)
        self.assertEqual(inspect.getgeneratorlocals(numbers),
                         {'a': None, 'lst': [1, 2, 3], 'v': 1,
                          'b': (1, 2, 3)})
        next(numbers)
        self.assertEqual(inspect.getgeneratorlocals(numbers),
                         {'a': None, 'lst': [1, 2, 3], 'v': 2,
                          'b': (1, 2, 3)})
        next(numbers)
        self.assertEqual(inspect.getgeneratorlocals(numbers),
                         {'a': None, 'lst': [1, 2, 3], 'v': 3,
                          'b': (1, 2, 3), 'c': 12})
        try:
            next(numbers)
        except StopIteration:
            pass
        self.assertEqual(inspect.getgeneratorlocals(numbers), {})

    def test_getgeneratorlocals_empty(self):
        def yield_one():
            yield 1
        one = yield_one()
        self.assertEqual(inspect.getgeneratorlocals(one), {})
        try:
            next(one)
        except StopIteration:
            pass
        self.assertEqual(inspect.getgeneratorlocals(one), {})

    def test_getgeneratorlocals_error(self):
        self.assertRaises(TypeError, inspect.getgeneratorlocals, 1)
        self.assertRaises(TypeError, inspect.getgeneratorlocals, lambda x: True)
        self.assertRaises(TypeError, inspect.getgeneratorlocals, set)
        self.assertRaises(TypeError, inspect.getgeneratorlocals, (2,3))


class TestGetCoroutineState(unittest.TestCase):

    def setUp(self):
        @types.coroutine
        def number_coroutine():
            for number in range(5):
                yield number
        async def coroutine():
            await number_coroutine()
        self.coroutine = coroutine()

    def tearDown(self):
        self.coroutine.close()

    def _coroutinestate(self):
        return inspect.getcoroutinestate(self.coroutine)

    def test_created(self):
        self.assertEqual(self._coroutinestate(), inspect.CORO_CREATED)

    def test_suspended(self):
        self.coroutine.send(None)
        self.assertEqual(self._coroutinestate(), inspect.CORO_SUSPENDED)

    def test_closed_after_exhaustion(self):
        while True:
            try:
                self.coroutine.send(None)
            except StopIteration:
                break

        self.assertEqual(self._coroutinestate(), inspect.CORO_CLOSED)

    def test_closed_after_immediate_exception(self):
        with self.assertRaises(RuntimeError):
            self.coroutine.throw(RuntimeError)
        self.assertEqual(self._coroutinestate(), inspect.CORO_CLOSED)

    def test_easy_debugging(self):
        # repr() and str() of a coroutine state should contain the state name
        names = 'CORO_CREATED CORO_RUNNING CORO_SUSPENDED CORO_CLOSED'.split()
        for name in names:
            state = getattr(inspect, name)
            self.assertIn(name, repr(state))
            self.assertIn(name, str(state))

    def test_getcoroutinelocals(self):
        @types.coroutine
        def gencoro():
            yield

        gencoro = gencoro()
        async def func(a=None):
            b = 'spam'
            await gencoro

        coro = func()
        self.assertEqual(inspect.getcoroutinelocals(coro),
                         {'a': None, 'gencoro': gencoro})
        coro.send(None)
        self.assertEqual(inspect.getcoroutinelocals(coro),
                         {'a': None, 'gencoro': gencoro, 'b': 'spam'})


class MySignature(inspect.Signature):
    # Top-level to make it picklable;
    # used in test_signature_object_pickle
    pass

class MyParameter(inspect.Parameter):
    # Top-level to make it picklable;
    # used in test_signature_object_pickle
    pass



class TestSignatureObject(unittest.TestCase):
    @staticmethod
    def signature(func, **kw):
        sig = inspect.signature(func, **kw)
        return (tuple((param.name,
                       (Ellipsis if param.default is param.empty else param.default),
                       (Ellipsis if param.annotation is param.empty
                                                        else param.annotation),
                       str(param.kind).lower())
                                    for param in sig.parameters.values()),
                (Ellipsis if sig.return_annotation is sig.empty
                                            else sig.return_annotation))

    def test_signature_object(self):
        S = inspect.Signature
        P = inspect.Parameter

        self.assertEqual(str(S()), '()')

        def test(po, pk, pod=42, pkd=100, *args, ko, **kwargs):
            pass
        sig = inspect.signature(test)
        po = sig.parameters['po'].replace(kind=P.POSITIONAL_ONLY)
        pod = sig.parameters['pod'].replace(kind=P.POSITIONAL_ONLY)
        pk = sig.parameters['pk']
        pkd = sig.parameters['pkd']
        args = sig.parameters['args']
        ko = sig.parameters['ko']
        kwargs = sig.parameters['kwargs']

        S((po, pk, args, ko, kwargs))

        with self.assertRaisesRegexp(ValueError, 'wrong parameter order'):
            S((pk, po, args, ko, kwargs))

        with self.assertRaisesRegexp(ValueError, 'wrong parameter order'):
            S((po, args, pk, ko, kwargs))

        with self.assertRaisesRegexp(ValueError, 'wrong parameter order'):
            S((args, po, pk, ko, kwargs))

        with self.assertRaisesRegexp(ValueError, 'wrong parameter order'):
            S((po, pk, args, kwargs, ko))

        kwargs2 = kwargs.replace(name='args')
        with self.assertRaisesRegexp(ValueError, 'duplicate parameter name'):
            S((po, pk, args, kwargs2, ko))

        with self.assertRaisesRegexp(ValueError, 'follows default argument'):
            S((pod, po))

        with self.assertRaisesRegexp(ValueError, 'follows default argument'):
            S((po, pkd, pk))

        with self.assertRaisesRegexp(ValueError, 'follows default argument'):
            S((pkd, pk))

        self.assertTrue(repr(sig).startswith('<Signature'))
        self.assertTrue('(po, pk' in repr(sig))

    def test_signature_object_pickle(self):
        def foo(a, b, *, c:1={}, **kw) -> {42:'ham'}: pass
        foo_partial = functools.partial(foo, a=1)

        sig = inspect.signature(foo_partial)

        for ver in range(pickle.HIGHEST_PROTOCOL + 1):
            sig_pickled = pickle.loads(pickle.dumps(sig, ver))
            self.assertEqual(sig, sig_pickled)

        # Test that basic sub-classing works
        sig = inspect.signature(foo)
        myparam = MyParameter(name='z', kind=inspect.Parameter.POSITIONAL_ONLY)
        myparams = collections.OrderedDict(sig.parameters, a=myparam)
        mysig = MySignature().replace(parameters=myparams.values(),
                                      return_annotation=sig.return_annotation)
        self.assertTrue(isinstance(mysig, MySignature))
        self.assertTrue(isinstance(mysig.parameters['z'], MyParameter))

        for ver in range(pickle.HIGHEST_PROTOCOL + 1):
            sig_pickled = pickle.loads(pickle.dumps(mysig, ver))
            self.assertEqual(mysig, sig_pickled)
            self.assertTrue(isinstance(sig_pickled, MySignature))
            self.assertTrue(isinstance(sig_pickled.parameters['z'],
                                       MyParameter))

    def test_signature_immutability(self):
        def test(a):
            pass
        sig = inspect.signature(test)

        with self.assertRaises(AttributeError):
            sig.foo = 'bar'

        with self.assertRaises(TypeError):
            sig.parameters['a'] = None

    def test_signature_on_noarg(self):
        def test():
            pass
        self.assertEqual(self.signature(test), ((), Ellipsis))

    def test_signature_on_wargs(self):
        def test(a, b:'foo') -> 123:
            pass
        self.assertEqual(self.signature(test),
                         ((('a', Ellipsis, Ellipsis, "positional_or_keyword"),
                           ('b', Ellipsis, 'foo', "positional_or_keyword")),
                          123))

    def test_signature_on_wkwonly(self):
        def test(*, a:float, b:str) -> int:
            pass
        self.assertEqual(self.signature(test),
                         ((('a', Ellipsis, float, "keyword_only"),
                           ('b', Ellipsis, str, "keyword_only")),
                           int))

    def test_signature_on_complex_args(self):
        def test(a, b:'foo'=10, *args:'bar', spam:'baz', ham=123, **kwargs:int):
            pass
        self.assertEqual(self.signature(test),
                         ((('a', Ellipsis, Ellipsis, "positional_or_keyword"),
                           ('b', 10, 'foo', "positional_or_keyword"),
                           ('args', Ellipsis, 'bar', "var_positional"),
                           ('spam', Ellipsis, 'baz', "keyword_only"),
                           ('ham', 123, Ellipsis, "keyword_only"),
                           ('kwargs', Ellipsis, int, "var_keyword")),
                          Ellipsis))

    @cpython_only
    @unittest.skipIf(MISSING_C_DOCSTRINGS,
                     "Signature information for builtins requires docstrings")
    def test_signature_on_builtins(self):
        import _testcapi

        def test_unbound_method(o):
            """Use this to test unbound methods (things that should have a self)"""
            signature = inspect.signature(o)
            self.assertTrue(isinstance(signature, inspect.Signature))
            self.assertEqual(list(signature.parameters.values())[0].name, 'self')
            return signature

        def test_callable(o):
            """Use this to test bound methods or normal callables (things that don't expect self)"""
            signature = inspect.signature(o)
            self.assertTrue(isinstance(signature, inspect.Signature))
            if signature.parameters:
                self.assertNotEqual(list(signature.parameters.values())[0].name, 'self')
            return signature

        signature = test_callable(_testcapi.docstring_with_signature_with_defaults)
        def p(name): return signature.parameters[name].default
        self.assertEqual(p('s'), 'avocado')
        self.assertEqual(p('b'), b'bytes')
        self.assertEqual(p('d'), 3.14)
        self.assertEqual(p('i'), 35)
        self.assertEqual(p('n'), None)
        self.assertEqual(p('t'), True)
        self.assertEqual(p('f'), False)
        self.assertEqual(p('local'), 3)
        self.assertEqual(p('sys'), sys.maxsize)
        self.assertEqual(p('exp'), sys.maxsize - 1)

        test_callable(object)

        # normal method
        # (PyMethodDescr_Type, "method_descriptor")
        test_unbound_method(_pickle.Pickler.dump)
        d = _pickle.Pickler(io.StringIO())
        test_callable(d.dump)

        # static method
        test_callable(str.maketrans)
        test_callable('abc'.maketrans)

        # class method
        test_callable(dict.fromkeys)
        test_callable({}.fromkeys)

        # wrapper around slot (PyWrapperDescr_Type, "wrapper_descriptor")
        test_unbound_method(type.__call__)
        test_unbound_method(int.__add__)
        test_callable((3).__add__)

        # _PyMethodWrapper_Type
        # support for 'method-wrapper'
        test_callable(min.__call__)

        # This doesn't work now.
        # (We don't have a valid signature for "type" in 3.4)
        with self.assertRaisesRegexp(ValueError, "no signature found"):
            class ThisWorksNow:
                __call__ = type
            test_callable(ThisWorksNow())

        # Regression test for issue #20786
        test_unbound_method(dict.__delitem__)
        test_unbound_method(property.__delete__)

        # Regression test for issue #20586
        test_callable(_testcapi.docstring_with_signature_but_no_doc)

    @cpython_only
    @unittest.skipIf(MISSING_C_DOCSTRINGS,
                     "Signature information for builtins requires docstrings")
    def test_signature_on_decorated_builtins(self):
        import _testcapi
        func = _testcapi.docstring_with_signature_with_defaults

        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> int:
                return func(*args, **kwargs)
            return wrapper

        decorated_func = decorator(func)

        self.assertEqual(inspect.signature(func),
                         inspect.signature(decorated_func))

        def wrapper_like(*args, **kwargs) -> int: pass
        self.assertEqual(inspect.signature(decorated_func,
                                           follow_wrapped=False),
                         inspect.signature(wrapper_like))

    @cpython_only
    def test_signature_on_builtins_no_signature(self):
        with self.assertRaisesRegexp(ValueError,
                                    'no signature found for builtin'):
            inspect.signature(str)

    def test_signature_on_non_function(self):
        with self.assertRaisesRegexp(TypeError, 'is not a callable object'):
            inspect.signature(42)

    def test_signature_from_functionlike_object(self):
        def func(a,b, *args, kwonly=True, kwonlyreq, **kwargs):
            pass

        class funclike:
            # Has to be callable, and have correct
            # __code__, __annotations__, __defaults__, __name__,
            # and __kwdefaults__ attributes

            def __init__(self, func):
                self.__name__ = func.__name__
                self.__code__ = func.__code__
                self.__annotations__ = func.__annotations__
                self.__defaults__ = func.__defaults__
                self.__kwdefaults__ = func.__kwdefaults__
                self.func = func

            def __call__(self, *args, **kwargs):
                return self.func(*args, **kwargs)

        sig_func = inspect.Signature.from_callable(func)

        sig_funclike = inspect.Signature.from_callable(funclike(func))
        self.assertEqual(sig_funclike, sig_func)

        sig_funclike = inspect.signature(funclike(func))
        self.assertEqual(sig_funclike, sig_func)

        # If object is not a duck type of function, then
        # signature will try to get a signature for its '__call__'
        # method
        fl = funclike(func)
        del fl.__defaults__
        self.assertEqual(self.signature(fl),
                         ((('args', Ellipsis, Ellipsis, "var_positional"),
                           ('kwargs', Ellipsis, Ellipsis, "var_keyword")),
                           Ellipsis))

        # Test with cython-like builtins:
        _orig_isdesc = inspect.ismethoddescriptor
        def _isdesc(obj):
            if hasattr(obj, '_builtinmock'):
                return True
            return _orig_isdesc(obj)

        # TODO/RSI for when we have mocks
        #with unittest.mock.patch('inspect.ismethoddescriptor', _isdesc):
        #    builtin_func = funclike(func)
        #    # Make sure that our mock setup is working
        #    self.assertFalse(inspect.ismethoddescriptor(builtin_func))
        #    builtin_func._builtinmock = True
        #    self.assertTrue(inspect.ismethoddescriptor(builtin_func))
        #    self.assertEqual(inspect.signature(builtin_func), sig_func)

    def test_signature_functionlike_class(self):
        # We only want to duck type function-like objects,
        # not classes.

        def func(a,b, *args, kwonly=True, kwonlyreq, **kwargs):
            pass

        class funclike:
            def __init__(self, marker):
                pass

            __name__ = func.__name__
            __code__ = func.__code__
            __annotations__ = func.__annotations__
            __defaults__ = func.__defaults__
            __kwdefaults__ = func.__kwdefaults__

        self.assertEqual(str(inspect.signature(funclike)), '(marker)')

    def test_signature_on_method(self):
        class Test:
            def __init__(*args):
                pass
            def m1(self, arg1, arg2=1) -> int:
                pass
            def m2(*args):
                pass
            def __call__(*, a):
                pass

        self.assertEqual(self.signature(Test().m1),
                         ((('arg1', Ellipsis, Ellipsis, "positional_or_keyword"),
                           ('arg2', 1, Ellipsis, "positional_or_keyword")),
                          int))

        self.assertEqual(self.signature(Test().m2),
                         ((('args', Ellipsis, Ellipsis, "var_positional"),),
                          Ellipsis))

        self.assertEqual(self.signature(Test),
                         ((('args', Ellipsis, Ellipsis, "var_positional"),),
                          Ellipsis))

        with self.assertRaisesRegexp(ValueError, 'invalid method signature'):
            self.signature(Test())

    def test_signature_wrapped_bound_method(self):
        # Issue 24298
        class Test:
            def m1(self, arg1, arg2=1) -> int:
                pass
        @functools.wraps(Test().m1)
        def m1d(*args, **kwargs):
            pass
        self.assertEqual(self.signature(m1d),
                         ((('arg1', Ellipsis, Ellipsis, "positional_or_keyword"),
                           ('arg2', 1, Ellipsis, "positional_or_keyword")),
                          int))

    def test_signature_on_classmethod(self):
        class Test:
            @classmethod
            def foo(cls, arg1, *, arg2=1):
                pass

        meth = Test().foo
        self.assertEqual(self.signature(meth),
                         ((('arg1', Ellipsis, Ellipsis, "positional_or_keyword"),
                           ('arg2', 1, Ellipsis, "keyword_only")),
                          Ellipsis))

        meth = Test.foo
        self.assertEqual(self.signature(meth),
                         ((('arg1', Ellipsis, Ellipsis, "positional_or_keyword"),
                           ('arg2', 1, Ellipsis, "keyword_only")),
                          Ellipsis))

    def test_signature_on_staticmethod(self):
        class Test:
            @staticmethod
            def foo(cls, *, arg):
                pass

        meth = Test().foo
        self.assertEqual(self.signature(meth),
                         ((('cls', Ellipsis, Ellipsis, "positional_or_keyword"),
                           ('arg', Ellipsis, Ellipsis, "keyword_only")),
                          Ellipsis))

        meth = Test.foo
        self.assertEqual(self.signature(meth),
                         ((('cls', Ellipsis, Ellipsis, "positional_or_keyword"),
                           ('arg', Ellipsis, Ellipsis, "keyword_only")),
                          Ellipsis))

    def test_signature_on_partial(self):
        from functools import partial

        Parameter = inspect.Parameter

        def test():
            pass

        self.assertEqual(self.signature(partial(test)), ((), Ellipsis))

        with self.assertRaisesRegexp(ValueError, "has incorrect arguments"):
            inspect.signature(partial(test, 1))

        with self.assertRaisesRegexp(ValueError, "has incorrect arguments"):
            inspect.signature(partial(test, a=1))

        def test(a, b, *, c, d):
            pass

        self.assertEqual(self.signature(partial(test)),
                         ((('a', Ellipsis, Ellipsis, "positional_or_keyword"),
                           ('b', Ellipsis, Ellipsis, "positional_or_keyword"),
                           ('c', Ellipsis, Ellipsis, "keyword_only"),
                           ('d', Ellipsis, Ellipsis, "keyword_only")),
                          Ellipsis))

        self.assertEqual(self.signature(partial(test, 1)),
                         ((('b', Ellipsis, Ellipsis, "positional_or_keyword"),
                           ('c', Ellipsis, Ellipsis, "keyword_only"),
                           ('d', Ellipsis, Ellipsis, "keyword_only")),
                          Ellipsis))

        self.assertEqual(self.signature(partial(test, 1, c=2)),
                         ((('b', Ellipsis, Ellipsis, "positional_or_keyword"),
                           ('c', 2, Ellipsis, "keyword_only"),
                           ('d', Ellipsis, Ellipsis, "keyword_only")),
                          Ellipsis))

        self.assertEqual(self.signature(partial(test, b=1, c=2)),
                         ((('a', Ellipsis, Ellipsis, "positional_or_keyword"),
                           ('b', 1, Ellipsis, "keyword_only"),
                           ('c', 2, Ellipsis, "keyword_only"),
                           ('d', Ellipsis, Ellipsis, "keyword_only")),
                          Ellipsis))

        self.assertEqual(self.signature(partial(test, 0, b=1, c=2)),
                         ((('b', 1, Ellipsis, "keyword_only"),
                           ('c', 2, Ellipsis, "keyword_only"),
                           ('d', Ellipsis, Ellipsis, "keyword_only")),
                          Ellipsis))

        self.assertEqual(self.signature(partial(test, a=1)),
                         ((('a', 1, Ellipsis, "keyword_only"),
                           ('b', Ellipsis, Ellipsis, "keyword_only"),
                           ('c', Ellipsis, Ellipsis, "keyword_only"),
                           ('d', Ellipsis, Ellipsis, "keyword_only")),
                          Ellipsis))

        def test(a, *args, b, **kwargs):
            pass

        self.assertEqual(self.signature(partial(test, 1)),
                         ((('args', Ellipsis, Ellipsis, "var_positional"),
                           ('b', Ellipsis, Ellipsis, "keyword_only"),
                           ('kwargs', Ellipsis, Ellipsis, "var_keyword")),
                          Ellipsis))

        self.assertEqual(self.signature(partial(test, a=1)),
                         ((('a', 1, Ellipsis, "keyword_only"),
                           ('b', Ellipsis, Ellipsis, "keyword_only"),
                           ('kwargs', Ellipsis, Ellipsis, "var_keyword")),
                          Ellipsis))

        self.assertEqual(self.signature(partial(test, 1, 2, 3)),
                         ((('args', Ellipsis, Ellipsis, "var_positional"),
                           ('b', Ellipsis, Ellipsis, "keyword_only"),
                           ('kwargs', Ellipsis, Ellipsis, "var_keyword")),
                          Ellipsis))

        self.assertEqual(self.signature(partial(test, 1, 2, 3, test=True)),
                         ((('args', Ellipsis, Ellipsis, "var_positional"),
                           ('b', Ellipsis, Ellipsis, "keyword_only"),
                           ('kwargs', Ellipsis, Ellipsis, "var_keyword")),
                          Ellipsis))

        self.assertEqual(self.signature(partial(test, 1, 2, 3, test=1, b=0)),
                         ((('args', Ellipsis, Ellipsis, "var_positional"),
                           ('b', 0, Ellipsis, "keyword_only"),
                           ('kwargs', Ellipsis, Ellipsis, "var_keyword")),
                          Ellipsis))

        self.assertEqual(self.signature(partial(test, b=0)),
                         ((('a', Ellipsis, Ellipsis, "positional_or_keyword"),
                           ('args', Ellipsis, Ellipsis, "var_positional"),
                           ('b', 0, Ellipsis, "keyword_only"),
                           ('kwargs', Ellipsis, Ellipsis, "var_keyword")),
                          Ellipsis))

        self.assertEqual(self.signature(partial(test, b=0, test=1)),
                         ((('a', Ellipsis, Ellipsis, "positional_or_keyword"),
                           ('args', Ellipsis, Ellipsis, "var_positional"),
                           ('b', 0, Ellipsis, "keyword_only"),
                           ('kwargs', Ellipsis, Ellipsis, "var_keyword")),
                          Ellipsis))

        def test(a, b, c:int) -> 42:
            pass

        sig = test.__signature__ = inspect.signature(test)

        self.assertEqual(self.signature(partial(partial(test, 1))),
                         ((('b', Ellipsis, Ellipsis, "positional_or_keyword"),
                           ('c', Ellipsis, int, "positional_or_keyword")),
                          42))

        self.assertEqual(self.signature(partial(partial(test, 1), 2)),
                         ((('c', Ellipsis, int, "positional_or_keyword"),),
                          42))

        psig = inspect.signature(partial(partial(test, 1), 2))

        def foo(a):
            return a
        _foo = partial(partial(foo, a=10), a=20)
        self.assertEqual(self.signature(_foo),
                         ((('a', 20, Ellipsis, "keyword_only"),),
                          Ellipsis))
        # check that we don't have any side-effects in signature(),
        # and the partial object is still functioning
        self.assertEqual(_foo(), 20)

        def foo(a, b, c):
            return a, b, c
        _foo = partial(partial(foo, 1, b=20), b=30)

        self.assertEqual(self.signature(_foo),
                         ((('b', 30, Ellipsis, "keyword_only"),
                           ('c', Ellipsis, Ellipsis, "keyword_only")),
                          Ellipsis))
        self.assertEqual(_foo(c=10), (1, 30, 10))

        def foo(a, b, c, *, d):
            return a, b, c, d
        _foo = partial(partial(foo, d=20, c=20), b=10, d=30)
        self.assertEqual(self.signature(_foo),
                         ((('a', Ellipsis, Ellipsis, "positional_or_keyword"),
                           ('b', 10, Ellipsis, "keyword_only"),
                           ('c', 20, Ellipsis, "keyword_only"),
                           ('d', 30, Ellipsis, "keyword_only"),
                           ),
                          Ellipsis))
        ba = inspect.signature(_foo).bind(a=200, b=11)
        self.assertEqual(_foo(*ba.args, **ba.kwargs), (200, 11, 20, 30))

        def foo(a=1, b=2, c=3):
            return a, b, c
        _foo = partial(foo, c=13) # (a=1, b=2, *, c=13)

        ba = inspect.signature(_foo).bind(a=11)
        self.assertEqual(_foo(*ba.args, **ba.kwargs), (11, 2, 13))

        ba = inspect.signature(_foo).bind(11, 12)
        self.assertEqual(_foo(*ba.args, **ba.kwargs), (11, 12, 13))

        ba = inspect.signature(_foo).bind(11, b=12)
        self.assertEqual(_foo(*ba.args, **ba.kwargs), (11, 12, 13))

        ba = inspect.signature(_foo).bind(b=12)
        self.assertEqual(_foo(*ba.args, **ba.kwargs), (1, 12, 13))

        _foo = partial(_foo, b=10, c=20)
        ba = inspect.signature(_foo).bind(12)
        self.assertEqual(_foo(*ba.args, **ba.kwargs), (12, 10, 20))


        def foo(a, b, c, d, **kwargs):
            pass
        sig = inspect.signature(foo)
        params = sig.parameters.copy()
        params['a'] = params['a'].replace(kind=Parameter.POSITIONAL_ONLY)
        params['b'] = params['b'].replace(kind=Parameter.POSITIONAL_ONLY)
        foo.__signature__ = inspect.Signature(params.values())
        sig = inspect.signature(foo)
        self.assertEqual(str(sig), '(a, b, /, c, d, **kwargs)')

        self.assertEqual(self.signature(partial(foo, 1)),
                         ((('b', Ellipsis, Ellipsis, 'positional_only'),
                           ('c', Ellipsis, Ellipsis, 'positional_or_keyword'),
                           ('d', Ellipsis, Ellipsis, 'positional_or_keyword'),
                           ('kwargs', Ellipsis, Ellipsis, 'var_keyword')),
                         Ellipsis))

        self.assertEqual(self.signature(partial(foo, 1, 2)),
                         ((('c', Ellipsis, Ellipsis, 'positional_or_keyword'),
                           ('d', Ellipsis, Ellipsis, 'positional_or_keyword'),
                           ('kwargs', Ellipsis, Ellipsis, 'var_keyword')),
                         Ellipsis))

        self.assertEqual(self.signature(partial(foo, 1, 2, 3)),
                         ((('d', Ellipsis, Ellipsis, 'positional_or_keyword'),
                           ('kwargs', Ellipsis, Ellipsis, 'var_keyword')),
                         Ellipsis))

        self.assertEqual(self.signature(partial(foo, 1, 2, c=3)),
                         ((('c', 3, Ellipsis, 'keyword_only'),
                           ('d', Ellipsis, Ellipsis, 'keyword_only'),
                           ('kwargs', Ellipsis, Ellipsis, 'var_keyword')),
                         Ellipsis))

        self.assertEqual(self.signature(partial(foo, 1, c=3)),
                         ((('b', Ellipsis, Ellipsis, 'positional_only'),
                           ('c', 3, Ellipsis, 'keyword_only'),
                           ('d', Ellipsis, Ellipsis, 'keyword_only'),
                           ('kwargs', Ellipsis, Ellipsis, 'var_keyword')),
                         Ellipsis))

    def test_signature_on_decorated(self):
        import functools

        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> int:
                return func(*args, **kwargs)
            return wrapper

        class Foo:
            @decorator
            def bar(self, a, b):
                pass

        self.assertEqual(self.signature(Foo.bar),
                         ((('self', Ellipsis, Ellipsis, "positional_or_keyword"),
                           ('a', Ellipsis, Ellipsis, "positional_or_keyword"),
                           ('b', Ellipsis, Ellipsis, "positional_or_keyword")),
                          Ellipsis))

        self.assertEqual(self.signature(Foo().bar),
                         ((('a', Ellipsis, Ellipsis, "positional_or_keyword"),
                           ('b', Ellipsis, Ellipsis, "positional_or_keyword")),
                          Ellipsis))

        self.assertEqual(self.signature(Foo.bar, follow_wrapped=False),
                         ((('args', Ellipsis, Ellipsis, "var_positional"),
                           ('kwargs', Ellipsis, Ellipsis, "var_keyword")),
                          Ellipsis)) # functools.wraps will copy __annotations__
                                # from "func" to "wrapper", hence no
                                # return_annotation

        # Test that we handle method wrappers correctly
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> int:
                return func(42, *args, **kwargs)
            sig = inspect.signature(func)
            new_params = tuple(sig.parameters.values())[1:]
            wrapper.__signature__ = sig.replace(parameters=new_params)
            return wrapper

        class Foo:
            @decorator
            def __call__(self, a, b):
                pass

        self.assertEqual(self.signature(Foo.__call__),
                         ((('a', Ellipsis, Ellipsis, "positional_or_keyword"),
                           ('b', Ellipsis, Ellipsis, "positional_or_keyword")),
                          Ellipsis))

        self.assertEqual(self.signature(Foo().__call__),
                         ((('b', Ellipsis, Ellipsis, "positional_or_keyword"),),
                          Ellipsis))

        # Test we handle __signature__ partway down the wrapper stack
        def wrapped_foo_call():
            pass
        wrapped_foo_call.__wrapped__ = Foo.__call__

        self.assertEqual(self.signature(wrapped_foo_call),
                         ((('a', Ellipsis, Ellipsis, "positional_or_keyword"),
                           ('b', Ellipsis, Ellipsis, "positional_or_keyword")),
                          Ellipsis))


    def test_signature_on_class(self):
        class C:
            def __init__(self, a):
                pass

        self.assertEqual(self.signature(C),
                         ((('a', Ellipsis, Ellipsis, "positional_or_keyword"),),
                          Ellipsis))

        class CM(type):
            def __call__(cls, a):
                pass
        class C(object):
            __metaclass__ = CM
            def __init__(self, b):
                pass

        self.assertEqual(self.signature(C),
                         ((('a', Ellipsis, Ellipsis, "positional_or_keyword"),),
                          Ellipsis))

        class CM(type):
            def __new__(mcls, name, bases, dct, *, foo=1):
                return super(CM, mcls).__new__(mcls, name, bases, dct)
        class C(object):
            __metaclass__ = CM
            def __init__(self, b):
                pass

        self.assertEqual(self.signature(C),
                         ((('b', Ellipsis, Ellipsis, "positional_or_keyword"),),
                          Ellipsis))

        self.assertEqual(self.signature(CM),
                         ((('name', Ellipsis, Ellipsis, "positional_or_keyword"),
                           ('bases', Ellipsis, Ellipsis, "positional_or_keyword"),
                           ('dct', Ellipsis, Ellipsis, "positional_or_keyword"),
                           ('foo', 1, Ellipsis, "keyword_only")),
                          Ellipsis))

        class CMM(type):
            def __new__(mcls, name, bases, dct, *, foo=1):
                return super(CMM, mcls).__new__(mcls, name, bases, dct)
            def __call__(cls, nm, bs, dt):
                return type(nm, bs, dt)
        class CM(type):
            __metaclass__ = CMM
            def __new__(mcls, name, bases, dct, *, bar=2):
                return super(CM, mcls).__new__(mcls, name, bases, dct)
        class C(object):
            __metaclass__ = CM
            def __init__(self, b):
                pass

        self.assertEqual(self.signature(CMM),
                         ((('name', Ellipsis, Ellipsis, "positional_or_keyword"),
                           ('bases', Ellipsis, Ellipsis, "positional_or_keyword"),
                           ('dct', Ellipsis, Ellipsis, "positional_or_keyword"),
                           ('foo', 1, Ellipsis, "keyword_only")),
                          Ellipsis))

        self.assertEqual(self.signature(CM),
                         ((('nm', Ellipsis, Ellipsis, "positional_or_keyword"),
                           ('bs', Ellipsis, Ellipsis, "positional_or_keyword"),
                           ('dt', Ellipsis, Ellipsis, "positional_or_keyword")),
                          Ellipsis))

        self.assertEqual(self.signature(C),
                         ((('b', Ellipsis, Ellipsis, "positional_or_keyword"),),
                          Ellipsis))

        class CM(type):
            def __init__(cls, name, bases, dct, *, bar=2):
                return super(CM, cls).__init__(name, bases, dct)
        class C(object):
            __metaclass__ = CM
            def __init__(self, b):
                pass

        self.assertEqual(self.signature(CM),
                         ((('name', Ellipsis, Ellipsis, "positional_or_keyword"),
                           ('bases', Ellipsis, Ellipsis, "positional_or_keyword"),
                           ('dct', Ellipsis, Ellipsis, "positional_or_keyword"),
                           ('bar', 2, Ellipsis, "keyword_only")),
                          Ellipsis))

    @unittest.skipIf(MISSING_C_DOCSTRINGS,
                     "Signature information for builtins requires docstrings")
    def test_signature_on_class_without_init(self):
        # Test classes without user-defined __init__ or __new__
        class C: pass
        self.assertEqual(str(inspect.signature(C)), '()')
        class D(C): pass
        self.assertEqual(str(inspect.signature(D)), '()')

        # Test meta-classes without user-defined __init__ or __new__
        class C(type): pass
        class D(C): pass
        with self.assertRaisesRegexp(ValueError, "callable.*is not supported"):
            self.assertEqual(inspect.signature(C), None)
        with self.assertRaisesRegexp(ValueError, "callable.*is not supported"):
            self.assertEqual(inspect.signature(D), None)

    @unittest.skipIf(MISSING_C_DOCSTRINGS,
                     "Signature information for builtins requires docstrings")
    def test_signature_on_builtin_class(self):
        self.assertEqual(str(inspect.signature(_pickle.Pickler)),
                         '(file, protocol=None, fix_imports=True)')

        class P(_pickle.Pickler): pass
        class EmptyTrait: pass
        class P2(EmptyTrait, P): pass
        self.assertEqual(str(inspect.signature(P)),
                         '(file, protocol=None, fix_imports=True)')
        self.assertEqual(str(inspect.signature(P2)),
                         '(file, protocol=None, fix_imports=True)')

        class P3(P2):
            def __init__(self, spam):
                pass
        self.assertEqual(str(inspect.signature(P3)), '(spam)')

        class MetaP(type):
            def __call__(cls, foo, bar):
                pass
        class P4(P2):
            __metaclass__ = MetaP
            pass
        self.assertEqual(str(inspect.signature(P4)), '(foo, bar)')

    def test_signature_on_callable_objects(self):
        class Foo:
            def __call__(self, a):
                pass

        self.assertEqual(self.signature(Foo()),
                         ((('a', Ellipsis, Ellipsis, "positional_or_keyword"),),
                          Ellipsis))

        class Spam:
            pass
        with self.assertRaisesRegexp(TypeError, "is not a callable object"):
            inspect.signature(Spam())

        class Bar(Spam, Foo):
            pass

        self.assertEqual(self.signature(Bar()),
                         ((('a', Ellipsis, Ellipsis, "positional_or_keyword"),),
                          Ellipsis))

        class Wrapped:
            pass
        Wrapped.__wrapped__ = lambda a: None
        self.assertEqual(self.signature(Wrapped),
                         ((('a', Ellipsis, Ellipsis, "positional_or_keyword"),),
                          Ellipsis))
        # wrapper loop:
        Wrapped.__wrapped__ = Wrapped
        with self.assertRaisesRegexp(ValueError, 'wrapper loop'):
            self.signature(Wrapped)

    def test_signature_on_lambdas(self):
        self.assertEqual(self.signature((lambda a=10: a)),
                         ((('a', 10, Ellipsis, "positional_or_keyword"),),
                          Ellipsis))

    def test_signature_equality(self):
        def foo(a, *, b:int) -> float: pass
        self.assertFalse(inspect.signature(foo) == 42)
        self.assertTrue(inspect.signature(foo) != 42)
        self.assertTrue(inspect.signature(foo) == EqualsToAll())
        self.assertFalse(inspect.signature(foo) != EqualsToAll())

        def bar(a, *, b:int) -> float: pass
        self.assertTrue(inspect.signature(foo) == inspect.signature(bar))
        self.assertFalse(inspect.signature(foo) != inspect.signature(bar))
        self.assertEqual(
            hash(inspect.signature(foo)), hash(inspect.signature(bar)))

        def bar(a, *, b:int) -> int: pass
        self.assertFalse(inspect.signature(foo) == inspect.signature(bar))
        self.assertTrue(inspect.signature(foo) != inspect.signature(bar))
        self.assertNotEqual(
            hash(inspect.signature(foo)), hash(inspect.signature(bar)))

        def bar(a, *, b:int): pass
        self.assertFalse(inspect.signature(foo) == inspect.signature(bar))
        self.assertTrue(inspect.signature(foo) != inspect.signature(bar))
        self.assertNotEqual(
            hash(inspect.signature(foo)), hash(inspect.signature(bar)))

        def bar(a, *, b:int=42) -> float: pass
        self.assertFalse(inspect.signature(foo) == inspect.signature(bar))
        self.assertTrue(inspect.signature(foo) != inspect.signature(bar))
        self.assertNotEqual(
            hash(inspect.signature(foo)), hash(inspect.signature(bar)))

        def bar(a, *, c) -> float: pass
        self.assertFalse(inspect.signature(foo) == inspect.signature(bar))
        self.assertTrue(inspect.signature(foo) != inspect.signature(bar))
        self.assertNotEqual(
            hash(inspect.signature(foo)), hash(inspect.signature(bar)))

        def bar(a, b:int) -> float: pass
        self.assertFalse(inspect.signature(foo) == inspect.signature(bar))
        self.assertTrue(inspect.signature(foo) != inspect.signature(bar))
        self.assertNotEqual(
            hash(inspect.signature(foo)), hash(inspect.signature(bar)))
        def spam(b:int, a) -> float: pass
        self.assertFalse(inspect.signature(spam) == inspect.signature(bar))
        self.assertTrue(inspect.signature(spam) != inspect.signature(bar))
        self.assertNotEqual(
            hash(inspect.signature(spam)), hash(inspect.signature(bar)))

        def foo(*, a, b, c): pass
        def bar(*, c, b, a): pass
        self.assertTrue(inspect.signature(foo) == inspect.signature(bar))
        self.assertFalse(inspect.signature(foo) != inspect.signature(bar))
        self.assertEqual(
            hash(inspect.signature(foo)), hash(inspect.signature(bar)))

        def foo(*, a=1, b, c): pass
        def bar(*, c, b, a=1): pass
        self.assertTrue(inspect.signature(foo) == inspect.signature(bar))
        self.assertFalse(inspect.signature(foo) != inspect.signature(bar))
        self.assertEqual(
            hash(inspect.signature(foo)), hash(inspect.signature(bar)))

        def foo(pos, *, a=1, b, c): pass
        def bar(pos, *, c, b, a=1): pass
        self.assertTrue(inspect.signature(foo) == inspect.signature(bar))
        self.assertFalse(inspect.signature(foo) != inspect.signature(bar))
        self.assertEqual(
            hash(inspect.signature(foo)), hash(inspect.signature(bar)))

        def foo(pos, *, a, b, c): pass
        def bar(pos, *, c, b, a=1): pass
        self.assertFalse(inspect.signature(foo) == inspect.signature(bar))
        self.assertTrue(inspect.signature(foo) != inspect.signature(bar))
        self.assertNotEqual(
            hash(inspect.signature(foo)), hash(inspect.signature(bar)))

        def foo(pos, *args, a=42, b, c, **kwargs:int): pass
        def bar(pos, *args, c, b, a=42, **kwargs:int): pass
        self.assertTrue(inspect.signature(foo) == inspect.signature(bar))
        self.assertFalse(inspect.signature(foo) != inspect.signature(bar))
        self.assertEqual(
            hash(inspect.signature(foo)), hash(inspect.signature(bar)))

    def test_signature_hashable(self):
        S = inspect.Signature
        P = inspect.Parameter

        def foo(a): pass
        foo_sig = inspect.signature(foo)

        manual_sig = S(parameters=[P('a', P.POSITIONAL_OR_KEYWORD)])

        self.assertEqual(hash(foo_sig), hash(manual_sig))
        self.assertNotEqual(hash(foo_sig),
                            hash(manual_sig.replace(return_annotation='spam')))

        def bar(a) -> 1: pass
        self.assertNotEqual(hash(foo_sig), hash(inspect.signature(bar)))

        def foo(a={}): pass
        with self.assertRaisesRegexp(TypeError, 'unhashable type'):
            hash(inspect.signature(foo))

        def foo(a) -> {}: pass
        with self.assertRaisesRegexp(TypeError, 'unhashable type'):
            hash(inspect.signature(foo))

    def test_signature_str(self):
        def foo(a:int=1, *, b, c=None, **kwargs) -> 42:
            pass
        self.assertEqual(str(inspect.signature(foo)),
                         '(a:int=1, *, b, c=None, **kwargs) -> 42')

        def foo(a:int=1, *args, b, c=None, **kwargs) -> 42:
            pass
        self.assertEqual(str(inspect.signature(foo)),
                         '(a:int=1, *args, b, c=None, **kwargs) -> 42')

        def foo():
            pass
        self.assertEqual(str(inspect.signature(foo)), '()')

    def test_signature_str_positional_only(self):
        P = inspect.Parameter
        S = inspect.Signature

        def test(a_po, *, b, **kwargs):
            return a_po, kwargs

        sig = inspect.signature(test)
        new_params = list(sig.parameters.values())
        new_params[0] = new_params[0].replace(kind=P.POSITIONAL_ONLY)
        test.__signature__ = sig.replace(parameters=new_params)

        self.assertEqual(str(inspect.signature(test)),
                         '(a_po, /, *, b, **kwargs)')

        self.assertEqual(str(S(parameters=[P('foo', P.POSITIONAL_ONLY)])),
                         '(foo, /)')

        self.assertEqual(str(S(parameters=[
                                P('foo', P.POSITIONAL_ONLY),
                                P('bar', P.VAR_KEYWORD)])),
                         '(foo, /, **bar)')

        self.assertEqual(str(S(parameters=[
                                P('foo', P.POSITIONAL_ONLY),
                                P('bar', P.VAR_POSITIONAL)])),
                         '(foo, /, *bar)')

    def test_signature_replace_anno(self):
        def test() -> 42:
            pass

        sig = inspect.signature(test)
        sig = sig.replace(return_annotation=None)
        self.assertIs(sig.return_annotation, None)
        sig = sig.replace(return_annotation=sig.empty)
        self.assertIs(sig.return_annotation, sig.empty)
        sig = sig.replace(return_annotation=42)
        self.assertEqual(sig.return_annotation, 42)
        self.assertEqual(sig, inspect.signature(test))

    def test_signature_on_mangled_parameters(self):
        class Spam:
            def foo(self, __p1:1=2, *, __p2:2=3):
                pass
        class Ham(Spam):
            pass

        self.assertEqual(self.signature(Spam.foo),
                         ((('self', Ellipsis, Ellipsis, "positional_or_keyword"),
                           ('_Spam__p1', 2, 1, "positional_or_keyword"),
                           ('_Spam__p2', 3, 2, "keyword_only")),
                          Ellipsis))

        self.assertEqual(self.signature(Spam.foo),
                         self.signature(Ham.foo))

    def test_signature_from_callable_python_obj(self):
        class MySignature(inspect.Signature): pass
        def foo(a, *, b:1): pass
        foo_sig = MySignature.from_callable(foo)
        self.assertTrue(isinstance(foo_sig, MySignature))

    @unittest.skipIf(MISSING_C_DOCSTRINGS,
                     "Signature information for builtins requires docstrings")
    def test_signature_from_callable_builtin_obj(self):
        class MySignature(inspect.Signature): pass
        sig = MySignature.from_callable(_pickle.Pickler)
        self.assertTrue(isinstance(sig, MySignature))


class TestParameterObject(unittest.TestCase):
    def test_signature_parameter_kinds(self):
        P = inspect.Parameter
        self.assertTrue(P.POSITIONAL_ONLY < P.POSITIONAL_OR_KEYWORD < \
                        P.VAR_POSITIONAL < P.KEYWORD_ONLY < P.VAR_KEYWORD)

        self.assertEqual(str(P.POSITIONAL_ONLY), 'POSITIONAL_ONLY')
        self.assertTrue('POSITIONAL_ONLY' in repr(P.POSITIONAL_ONLY))

    def test_signature_parameter_object(self):
        p = inspect.Parameter('foo', default=10,
                              kind=inspect.Parameter.POSITIONAL_ONLY)
        self.assertEqual(p.name, 'foo')
        self.assertEqual(p.default, 10)
        self.assertIs(p.annotation, p.empty)
        self.assertEqual(p.kind, inspect.Parameter.POSITIONAL_ONLY)

        with self.assertRaisesRegexp(ValueError, 'invalid value'):
            inspect.Parameter('foo', default=10, kind='123')

        with self.assertRaisesRegexp(ValueError, 'not a valid parameter name'):
            inspect.Parameter('1', kind=inspect.Parameter.VAR_KEYWORD)

        with self.assertRaisesRegexp(TypeError, 'name must be a str'):
            inspect.Parameter(None, kind=inspect.Parameter.VAR_KEYWORD)

        with self.assertRaisesRegexp(ValueError,
                                    'is not a valid parameter name'):
            inspect.Parameter('$', kind=inspect.Parameter.VAR_KEYWORD)

        with self.assertRaisesRegexp(ValueError,
                                    'is not a valid parameter name'):
            inspect.Parameter('.a', kind=inspect.Parameter.VAR_KEYWORD)

        with self.assertRaisesRegexp(ValueError, 'cannot have default values'):
            inspect.Parameter('a', default=42,
                              kind=inspect.Parameter.VAR_KEYWORD)

        with self.assertRaisesRegexp(ValueError, 'cannot have default values'):
            inspect.Parameter('a', default=42,
                              kind=inspect.Parameter.VAR_POSITIONAL)

        p = inspect.Parameter('a', default=42,
                              kind=inspect.Parameter.POSITIONAL_OR_KEYWORD)
        with self.assertRaisesRegexp(ValueError, 'cannot have default values'):
            p.replace(kind=inspect.Parameter.VAR_POSITIONAL)

        self.assertTrue(repr(p).startswith('<Parameter'))
        self.assertTrue('"a=42"' in repr(p))

    def test_signature_parameter_hashable(self):
        P = inspect.Parameter
        foo = P('foo', kind=P.POSITIONAL_ONLY)
        self.assertEqual(hash(foo), hash(P('foo', kind=P.POSITIONAL_ONLY)))
        self.assertNotEqual(hash(foo), hash(P('foo', kind=P.POSITIONAL_ONLY,
                                              default=42)))
        self.assertNotEqual(hash(foo),
                            hash(foo.replace(kind=P.VAR_POSITIONAL)))

    def test_signature_parameter_equality(self):
        P = inspect.Parameter
        p = P('foo', default=42, kind=inspect.Parameter.KEYWORD_ONLY)

        self.assertTrue(p == p)
        self.assertFalse(p != p)
        self.assertFalse(p == 42)
        self.assertTrue(p != 42)
        self.assertTrue(p == EqualsToAll())
        self.assertFalse(p != EqualsToAll())

        self.assertTrue(p == P('foo', default=42,
                               kind=inspect.Parameter.KEYWORD_ONLY))
        self.assertFalse(p != P('foo', default=42,
                                kind=inspect.Parameter.KEYWORD_ONLY))

    def test_signature_parameter_replace(self):
        p = inspect.Parameter('foo', default=42,
                              kind=inspect.Parameter.KEYWORD_ONLY)

        self.assertIsNot(p, p.replace())
        self.assertEqual(p, p.replace())

        p2 = p.replace(annotation=1)
        self.assertEqual(p2.annotation, 1)
        p2 = p2.replace(annotation=p2.empty)
        self.assertEqual(p, p2)

        p2 = p2.replace(name='bar')
        self.assertEqual(p2.name, 'bar')
        self.assertNotEqual(p2, p)

        with self.assertRaisesRegexp(ValueError,
                                    'name is a required attribute'):
            p2 = p2.replace(name=p2.empty)

        p2 = p2.replace(name='foo', default=None)
        self.assertIs(p2.default, None)
        self.assertNotEqual(p2, p)

        p2 = p2.replace(name='foo', default=p2.empty)
        self.assertIs(p2.default, p2.empty)


        p2 = p2.replace(default=42, kind=p2.POSITIONAL_OR_KEYWORD)
        self.assertEqual(p2.kind, p2.POSITIONAL_OR_KEYWORD)
        self.assertNotEqual(p2, p)

        with self.assertRaisesRegexp(ValueError, 'invalid value for'):
            p2 = p2.replace(kind=p2.empty)

        p2 = p2.replace(kind=p2.KEYWORD_ONLY)
        self.assertEqual(p2, p)

    def test_signature_parameter_positional_only(self):
        with self.assertRaisesRegexp(TypeError, 'name must be a str'):
            inspect.Parameter(None, kind=inspect.Parameter.POSITIONAL_ONLY)

    @cpython_only
    def test_signature_parameter_implicit(self):
        with self.assertRaisesRegexp(ValueError,
                                    'implicit arguments must be passed in as'):
            inspect.Parameter('.0', kind=inspect.Parameter.POSITIONAL_ONLY)

        param = inspect.Parameter(
            '.0', kind=inspect.Parameter.POSITIONAL_OR_KEYWORD)
        self.assertEqual(param.kind, inspect.Parameter.POSITIONAL_ONLY)
        self.assertEqual(param.name, 'implicit0')

    def test_signature_parameter_immutability(self):
        p = inspect.Parameter('spam', kind=inspect.Parameter.KEYWORD_ONLY)

        with self.assertRaises(AttributeError):
            p.foo = 'bar'

        with self.assertRaises(AttributeError):
            p.kind = 123


class TestSignatureBind(unittest.TestCase):
    @staticmethod
    def call(func, *args, **kwargs):
        sig = inspect.signature(func)
        ba = sig.bind(*args, **kwargs)
        return func(*ba.args, **ba.kwargs)

    def test_signature_bind_empty(self):
        def test():
            return 42

        self.assertEqual(self.call(test), 42)
        with self.assertRaisesRegexp(TypeError, 'too many positional arguments'):
            self.call(test, 1)
        with self.assertRaisesRegexp(TypeError, 'too many positional arguments'):
            self.call(test, 1, spam=10)
        with self.assertRaisesRegexp(
            TypeError, "got an unexpected keyword argument 'spam'"):

            self.call(test, spam=1)

    def test_signature_bind_var(self):
        def test(*args, **kwargs):
            return args, kwargs

        self.assertEqual(self.call(test), ((), {}))
        self.assertEqual(self.call(test, 1), ((1,), {}))
        self.assertEqual(self.call(test, 1, 2), ((1, 2), {}))
        self.assertEqual(self.call(test, foo='bar'), ((), {'foo': 'bar'}))
        self.assertEqual(self.call(test, 1, foo='bar'), ((1,), {'foo': 'bar'}))
        self.assertEqual(self.call(test, args=10), ((), {'args': 10}))
        self.assertEqual(self.call(test, 1, 2, foo='bar'),
                         ((1, 2), {'foo': 'bar'}))

    def test_signature_bind_just_args(self):
        def test(a, b, c):
            return a, b, c

        self.assertEqual(self.call(test, 1, 2, 3), (1, 2, 3))

        with self.assertRaisesRegexp(TypeError, 'too many positional arguments'):
            self.call(test, 1, 2, 3, 4)

        with self.assertRaisesRegexp(TypeError,
                                    "missing a required argument: 'b'"):
            self.call(test, 1)

        with self.assertRaisesRegexp(TypeError,
                                    "missing a required argument: 'a'"):
            self.call(test)

        def test(a, b, c=10):
            return a, b, c
        self.assertEqual(self.call(test, 1, 2, 3), (1, 2, 3))
        self.assertEqual(self.call(test, 1, 2), (1, 2, 10))

        def test(a=1, b=2, c=3):
            return a, b, c
        self.assertEqual(self.call(test, a=10, c=13), (10, 2, 13))
        self.assertEqual(self.call(test, a=10), (10, 2, 3))
        self.assertEqual(self.call(test, b=10), (1, 10, 3))

    def test_signature_bind_varargs_order(self):
        def test(*args):
            return args

        self.assertEqual(self.call(test), ())
        self.assertEqual(self.call(test, 1, 2, 3), (1, 2, 3))

    def test_signature_bind_args_and_varargs(self):
        def test(a, b, c=3, *args):
            return a, b, c, args

        self.assertEqual(self.call(test, 1, 2, 3, 4, 5), (1, 2, 3, (4, 5)))
        self.assertEqual(self.call(test, 1, 2), (1, 2, 3, ()))
        self.assertEqual(self.call(test, b=1, a=2), (2, 1, 3, ()))
        self.assertEqual(self.call(test, 1, b=2), (1, 2, 3, ()))

        with self.assertRaisesRegexp(TypeError,
                                     "multiple values for argument 'c'"):
            self.call(test, 1, 2, 3, c=4)

    def test_signature_bind_just_kwargs(self):
        def test(**kwargs):
            return kwargs

        self.assertEqual(self.call(test), {})
        self.assertEqual(self.call(test, foo='bar', spam='ham'),
                         {'foo': 'bar', 'spam': 'ham'})

    def test_signature_bind_args_and_kwargs(self):
        def test(a, b, c=3, **kwargs):
            return a, b, c, kwargs

        self.assertEqual(self.call(test, 1, 2), (1, 2, 3, {}))
        self.assertEqual(self.call(test, 1, 2, foo='bar', spam='ham'),
                         (1, 2, 3, {'foo': 'bar', 'spam': 'ham'}))
        self.assertEqual(self.call(test, b=2, a=1, foo='bar', spam='ham'),
                         (1, 2, 3, {'foo': 'bar', 'spam': 'ham'}))
        self.assertEqual(self.call(test, a=1, b=2, foo='bar', spam='ham'),
                         (1, 2, 3, {'foo': 'bar', 'spam': 'ham'}))
        self.assertEqual(self.call(test, 1, b=2, foo='bar', spam='ham'),
                         (1, 2, 3, {'foo': 'bar', 'spam': 'ham'}))
        self.assertEqual(self.call(test, 1, b=2, c=4, foo='bar', spam='ham'),
                         (1, 2, 4, {'foo': 'bar', 'spam': 'ham'}))
        self.assertEqual(self.call(test, 1, 2, 4, foo='bar'),
                         (1, 2, 4, {'foo': 'bar'}))
        self.assertEqual(self.call(test, c=5, a=4, b=3),
                         (4, 3, 5, {}))

    def test_signature_bind_kwonly(self):
        def test(*, foo):
            return foo
        with self.assertRaisesRegexp(TypeError,
                                     'too many positional arguments'):
            self.call(test, 1)
        self.assertEqual(self.call(test, foo=1), 1)

        def test(a, *, foo=1, bar):
            return foo
        with self.assertRaisesRegexp(TypeError,
                                     "missing a required argument: 'bar'"):
            self.call(test, 1)

        def test(foo, *, bar):
            return foo, bar
        self.assertEqual(self.call(test, 1, bar=2), (1, 2))
        self.assertEqual(self.call(test, bar=2, foo=1), (1, 2))

        with self.assertRaisesRegexp(
            TypeError, "got an unexpected keyword argument 'spam'"):

            self.call(test, bar=2, foo=1, spam=10)

        with self.assertRaisesRegexp(TypeError,
                                     'too many positional arguments'):
            self.call(test, 1, 2)

        with self.assertRaisesRegexp(TypeError,
                                     'too many positional arguments'):
            self.call(test, 1, 2, bar=2)

        with self.assertRaisesRegexp(
            TypeError, "got an unexpected keyword argument 'spam'"):

            self.call(test, 1, bar=2, spam='ham')

        with self.assertRaisesRegexp(TypeError,
                                     "missing a required argument: 'bar'"):
            self.call(test, 1)

        def test(foo, *, bar, **bin):
            return foo, bar, bin
        self.assertEqual(self.call(test, 1, bar=2), (1, 2, {}))
        self.assertEqual(self.call(test, foo=1, bar=2), (1, 2, {}))
        self.assertEqual(self.call(test, 1, bar=2, spam='ham'),
                         (1, 2, {'spam': 'ham'}))
        self.assertEqual(self.call(test, spam='ham', foo=1, bar=2),
                         (1, 2, {'spam': 'ham'}))
        with self.assertRaisesRegexp(TypeError,
                                    "missing a required argument: 'foo'"):
            self.call(test, spam='ham', bar=2)
        self.assertEqual(self.call(test, 1, bar=2, bin=1, spam=10),
                         (1, 2, {'bin': 1, 'spam': 10}))

    def test_signature_bind_arguments(self):
        def test(a, *args, b, z=100, **kwargs):
            pass
        sig = inspect.signature(test)
        ba = sig.bind(10, 20, b=30, c=40, args=50, kwargs=60)
        # we won't have 'z' argument in the bound arguments object, as we didn't
        # pass it to the 'bind'
        self.assertEqual(tuple(ba.arguments.items()),
                         (('a', 10), ('args', (20,)), ('b', 30),
                          ('kwargs', {'c': 40, 'args': 50, 'kwargs': 60})))
        self.assertEqual(ba.kwargs,
                         {'b': 30, 'c': 40, 'args': 50, 'kwargs': 60})
        self.assertEqual(ba.args, (10, 20))

    def test_signature_bind_positional_only(self):
        P = inspect.Parameter

        def test(a_po, b_po, c_po=3, foo=42, *, bar=50, **kwargs):
            return a_po, b_po, c_po, foo, bar, kwargs

        sig = inspect.signature(test)
        new_params = collections.OrderedDict(tuple(sig.parameters.items()))
        for name in ('a_po', 'b_po', 'c_po'):
            new_params[name] = new_params[name].replace(kind=P.POSITIONAL_ONLY)
        new_sig = sig.replace(parameters=new_params.values())
        test.__signature__ = new_sig

        self.assertEqual(self.call(test, 1, 2, 4, 5, bar=6),
                         (1, 2, 4, 5, 6, {}))

        self.assertEqual(self.call(test, 1, 2),
                         (1, 2, 3, 42, 50, {}))

        self.assertEqual(self.call(test, 1, 2, foo=4, bar=5),
                         (1, 2, 3, 4, 5, {}))

        with self.assertRaisesRegexp(TypeError, "but was passed as a keyword"):
            self.call(test, 1, 2, foo=4, bar=5, c_po=10)

        with self.assertRaisesRegexp(TypeError, "parameter is positional only"):
            self.call(test, 1, 2, c_po=4)

        with self.assertRaisesRegexp(TypeError, "parameter is positional only"):
            self.call(test, a_po=1, b_po=2)

    def test_signature_bind_with_self_arg(self):
        # Issue #17071: one of the parameters is named "self
        def test(a, self, b):
            pass
        sig = inspect.signature(test)
        ba = sig.bind(1, 2, 3)
        self.assertEqual(ba.args, (1, 2, 3))
        ba = sig.bind(1, self=2, b=3)
        self.assertEqual(ba.args, (1, 2, 3))

    def test_signature_bind_vararg_name(self):
        def test(a, *args):
            return a, args
        sig = inspect.signature(test)

        with self.assertRaisesRegexp(
            TypeError, "got an unexpected keyword argument 'args'"):

            sig.bind(a=0, args=1)

        def test(*args, **kwargs):
            return args, kwargs
        self.assertEqual(self.call(test, args=1), ((), {'args': 1}))

        sig = inspect.signature(test)
        ba = sig.bind(args=1)
        self.assertEqual(ba.arguments, {'kwargs': {'args': 1}})

    @cpython_only
    def test_signature_bind_implicit_arg(self):
        # Issue #19611: getcallargs should work with set comprehensions
        def make_set():
            return {z * z for z in range(5)}
        setcomp_code = make_set.__code__.co_consts[1]
        setcomp_func = types.FunctionType(setcomp_code, {})

        iterator = iter(range(5))
        self.assertEqual(self.call(setcomp_func, iterator), {0, 1, 4, 9, 16})


class TestBoundArguments(unittest.TestCase):
    def test_signature_bound_arguments_unhashable(self):
        def foo(a): pass
        ba = inspect.signature(foo).bind(1)

        with self.assertRaisesRegexp(TypeError, 'unhashable type'):
            hash(ba)

    def test_signature_bound_arguments_equality(self):
        def foo(a): pass
        ba = inspect.signature(foo).bind(1)
        self.assertTrue(ba == ba)
        self.assertFalse(ba != ba)
        self.assertTrue(ba == EqualsToAll())
        self.assertFalse(ba != EqualsToAll())

        ba2 = inspect.signature(foo).bind(1)
        self.assertTrue(ba == ba2)
        self.assertFalse(ba != ba2)

        ba3 = inspect.signature(foo).bind(2)
        self.assertFalse(ba == ba3)
        self.assertTrue(ba != ba3)
        ba3.arguments['a'] = 1
        self.assertTrue(ba == ba3)
        self.assertFalse(ba != ba3)

        def bar(b): pass
        ba4 = inspect.signature(bar).bind(1)
        self.assertFalse(ba == ba4)
        self.assertTrue(ba != ba4)

        def foo(*, a, b): pass
        sig = inspect.signature(foo)
        ba1 = sig.bind(a=1, b=2)
        ba2 = sig.bind(b=2, a=1)
        self.assertTrue(ba1 == ba2)
        self.assertFalse(ba1 != ba2)

    def test_signature_bound_arguments_pickle(self):
        def foo(a, b, *, c:1={}, **kw) -> {42:'ham'}: pass
        sig = inspect.signature(foo)
        ba = sig.bind(20, 30, z={})

        for ver in range(pickle.HIGHEST_PROTOCOL + 1):
            ba_pickled = pickle.loads(pickle.dumps(ba, ver))
            self.assertEqual(ba, ba_pickled)

    def test_signature_bound_arguments_repr(self):
        def foo(a, b, *, c:1={}, **kw) -> {42:'ham'}: pass
        sig = inspect.signature(foo)
        ba = sig.bind(20, 30, z={})
        self.assertRegexpMatches(repr(ba), r'<BoundArguments \(a=20,.*\}\}\)>')

    def test_signature_bound_arguments_apply_defaults(self):
        def foo(a, b=1, *args, c:1={}, **kw): pass
        sig = inspect.signature(foo)

        ba = sig.bind(20)
        ba.apply_defaults()
        self.assertEqual(
            list(ba.arguments.items()),
            [('a', 20), ('b', 1), ('args', ()), ('c', {}), ('kw', {})])

        # Make sure that we preserve the order:
        # i.e. 'c' should be *before* 'kw'.
        ba = sig.bind(10, 20, 30, d=1)
        ba.apply_defaults()
        self.assertEqual(
            list(ba.arguments.items()),
            [('a', 10), ('b', 20), ('args', (30,)), ('c', {}), ('kw', {'d':1})])

        # Make sure that BoundArguments produced by bind_partial()
        # are supported.
        def foo(a, b): pass
        sig = inspect.signature(foo)
        ba = sig.bind_partial(20)
        ba.apply_defaults()
        self.assertEqual(
            list(ba.arguments.items()),
            [('a', 20)])

        # Test no args
        def foo(): pass
        sig = inspect.signature(foo)
        ba = sig.bind()
        ba.apply_defaults()
        self.assertEqual(list(ba.arguments.items()), [])

        # Make sure a no-args binding still acquires proper defaults.
        def foo(a='spam'): pass
        sig = inspect.signature(foo)
        ba = sig.bind()
        ba.apply_defaults()
        self.assertEqual(list(ba.arguments.items()), [('a', 'spam')])


class TestSignaturePrivateHelpers(unittest.TestCase):
    def test_signature_get_bound_param(self):
        getter = inspect._signature_get_bound_param

        self.assertEqual(getter('($self)'), 'self')
        self.assertEqual(getter('($self, obj)'), 'self')
        self.assertEqual(getter('($cls, /, obj)'), 'cls')

    def _strip_non_python_syntax(self, input,
        clean_signature, self_parameter, last_positional_only):
        computed_clean_signature, \
            computed_self_parameter, \
            computed_last_positional_only = \
            inspect._signature_strip_non_python_syntax(input)
        self.assertEqual(computed_clean_signature, clean_signature)
        self.assertEqual(computed_self_parameter, self_parameter)
        self.assertEqual(computed_last_positional_only, last_positional_only)

    def test_signature_strip_non_python_syntax(self):
        self._strip_non_python_syntax(
            "($module, /, path, mode, *, dir_fd=None, " +
                "effective_ids=False,\n       follow_symlinks=True)",
            "(module, path, mode, *, dir_fd=None, " +
                "effective_ids=False, follow_symlinks=True)",
            0,
            0)

        self._strip_non_python_syntax(
            "($module, word, salt, /)",
            "(module, word, salt)",
            0,
            2)

        self._strip_non_python_syntax(
            "(x, y=None, z=None, /)",
            "(x, y=None, z=None)",
            None,
            2)

        self._strip_non_python_syntax(
            "(x, y=None, z=None)",
            "(x, y=None, z=None)",
            None,
            None)

        self._strip_non_python_syntax(
            "(x,\n    y=None,\n      z = None  )",
            "(x, y=None, z=None)",
            None,
            None)

        self._strip_non_python_syntax(
            "",
            "",
            None,
            None)

        self._strip_non_python_syntax(
            None,
            None,
            None,
            None)

class TestSignatureDefinitions(unittest.TestCase):
    # This test case provides a home for checking that particular APIs
    # have signatures available for introspection

    @cpython_only
    @unittest.skipIf(MISSING_C_DOCSTRINGS,
                     "Signature information for builtins requires docstrings")
    def test_builtins_have_signatures(self):
        # This checks all builtin callables in CPython have signatures
        # A few have signatures Signature can't yet handle, so we skip those
        # since they will have to wait until PEP 457 adds the required
        # introspection support to the inspect module
        # Some others also haven't been converted yet for various other
        # reasons, so we also skip those for the time being, but design
        # the test to fail in order to indicate when it needs to be
        # updated.
        no_signature = set()
        # These need PEP 457 groups
        needs_groups = {"range", "slice", "dir", "getattr",
                        "next", "iter", "vars"}
        no_signature |= needs_groups
        # These need PEP 457 groups or a signature change to accept None
        needs_semantic_update = {"round"}
        no_signature |= needs_semantic_update
        # These need *args support in Argument Clinic
        needs_varargs = {"min", "max", "print", "__build_class__"}
        no_signature |= needs_varargs
        # These simply weren't covered in the initial AC conversion
        # for builtin callables
        not_converted_yet = {"open", "__import__"}
        no_signature |= not_converted_yet
        # These builtin types are expected to provide introspection info
        types_with_signatures = set()
        # Check the signatures we expect to be there
        ns = vars(builtins)
        for name, obj in sorted(ns.items()):
            if not callable(obj):
                continue
            # The builtin types haven't been converted to AC yet
            if isinstance(obj, type) and (name not in types_with_signatures):
                # Note that this also skips all the exception types
                no_signature.add(name)
            if (name in no_signature):
                # Not yet converted
                continue
            self.assertIsNotNone(inspect.signature(obj))
        # Check callables that haven't been converted don't claim a signature
        # This ensures this test will start failing as more signatures are
        # added, so the affected items can be moved into the scope of the
        # regression test above
        for name in no_signature:
            self.assertIsNone(obj.__text_signature__)


class TestUnwrap(unittest.TestCase):

    def test_unwrap_one(self):
        def func(a, b):
            return a + b
        wrapper = contextmanager(func)  # Any wrapper would work
        self.assertIs(inspect.unwrap(wrapper), func)

    def test_unwrap_several(self):
        def func(a, b):
            return a + b
        wrapper = func
        for __ in range(10):
            @functools.wraps(wrapper)
            def wrapper():
                pass
        self.assertIsNot(wrapper.__wrapped__, func)
        self.assertIs(inspect.unwrap(wrapper), func)

    def test_stop(self):
        def func1(a, b):
            return a + b
        @functools.wraps(func1)
        def func2():
            pass
        @functools.wraps(func2)
        def wrapper():
            pass
        func2.stop_here = 1
        unwrapped = inspect.unwrap(wrapper,
                                   stop=(lambda f: hasattr(f, "stop_here")))
        self.assertIs(unwrapped, func2)

    def test_cycle(self):
        def func1(): pass
        func1.__wrapped__ = func1
        with self.assertRaisesRegexp(ValueError, 'wrapper loop'):
            inspect.unwrap(func1)

        def func2(): pass
        func2.__wrapped__ = func1
        func1.__wrapped__ = func2
        with self.assertRaisesRegexp(ValueError, 'wrapper loop'):
            inspect.unwrap(func1)
        with self.assertRaisesRegexp(ValueError, 'wrapper loop'):
            inspect.unwrap(func2)

    def test_unhashable(self):
        def func(): pass
        func.__wrapped__ = None
        class C:
            __hash__ = None
            __wrapped__ = func
        self.assertIsNone(inspect.unwrap(C()))

def test_main():
    run_unittest(
        TestDecorators, TestRetrievingSourceCode, TestOneliners, TestBuggyCases,
        TestInterpreterStack, TestClassesAndFunctions, TestPredicates,
        TestGetcallargsFunctions, TestGetcallargsFunctionsCellVars,
        TestGetcallargsMethods, TestGetcallargsUnboundMethods,
        TestGetGeneratorState, TestGetCoroutineState, TestSignatureObject,
        TestParameterObject, TestSignatureBind, TestBoundArguments,
        TestSignaturePrivateHelpers, TestSignatureDefinitions, TestUnwrap,
        TestGettingSourceOfToplevelFrames)

if __name__ == "__main__":
    test_main()
