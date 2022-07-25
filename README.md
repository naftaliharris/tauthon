Tauthon
=======

Tauthon is a backwards-compatible fork of the Python 2.7.18 interpreter with new
syntax, builtins, and libraries backported from Python 3.x. Python code and
C-extensions targeting Python 2.7 or below are expected to run unmodified on
Tauthon and produce the same output. [But with Tauthon, that code can now use
some of the new features from Python
3.x.](https://www.naftaliharris.com/blog/why-making-python-2.8/)


[![CI](https://github.com/naftaliharris/tauthon/actions/workflows/ci.yml/badge.svg)](https://github.com/naftaliharris/tauthon/actions/workflows/ci.yml)

What's new in Tauthon
-------------------------

* ### Function Annotations

    ```python
    >>> def f(a:int, b:str) -> list:
    ...     pass
    ...
    >>> f.__annotations__
    {'a': <type 'int'>, 'b': <type 'str'>, 'return': <type 'list'>}
    ```

    *More info: [PEP 3107](https://www.python.org/dev/peps/pep-3107/)*


* ### Keyword-Only Arguments

    ```python
    >>> def f(a, *, b):
    ...     pass
    ...
    >>> f(1, 2)
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
    TypeError: f() takes exactly 1 positional argument (2 given)
    >>> f(1, b=2)
    >>>
    ```

    *More info: [PEP 3102](https://www.python.org/dev/peps/pep-3102/)*


* ### "async" and "await" Syntax

    ```python
    >>> import types
    >>> @types.coroutine
    ... def delayed_print():
    ...     printme = yield
    ...     print printme
    ...
    >>> async def main():
    ...     while True:
    ...         await delayed_print()
    ...
    >>> coro = main()
    >>> coro.send(None)
    >>> coro.send("hello")
    hello
    >>> coro.send("there")
    there
    >>> coro.send("friend")
    friend
    ```

    *More info: [PEP 492](https://www.python.org/dev/peps/pep-0492/),
                [Tutorial](http://www.snarky.ca/how-the-heck-does-async-await-work-in-python-3-5)*


* ### Argument-less "super"

    ```python
    >>> class MyList(list):
    ...     def __repr__(self):
    ...             return "MyList" + super().__repr__()
    ...
    >>> MyList(range(3))
    MyList[0, 1, 2]
    ```

    *More info: [PEP 3135](https://www.python.org/dev/peps/pep-3135/),
                [API Docs](https://docs.python.org/3/library/functions.html#super)*


* ### New Metaclass Syntax

    ```python
    >>> from collections import OrderedDict
    >>> class Meta(type):
    ...     @staticmethod
    ...     def __prepare__(name, bases, **kwds):
    ...             return OrderedDict()
    ...     def __new__(cls, name, bases, namespace, **kwds):
    ...             namespace.update(kwds)
    ...             res = type.__new__(cls, name, bases, dict(namespace))
    ...             res._namespace = namespace
    ...             return res
    ...     def __init__(*args, **kwds):
    ...             pass
    ...
    >>> class MyClass(metaclass=Meta, foo="bar"):
    ...     def first(self): pass
    ...     def second(self): pass
    ...     def third(self): pass
    ...
    >>> MyClass.foo
    'bar'
    >>> MyClass._namespace
    OrderedDict([('__module__', '__main__'), ('first', <function first at 0x1007ef568>), ('second', <function second at 0x10131b060>), ('third', <function third at 0x10131b118>), ('foo', 'bar')])
    ```

    *More info: [PEP 3115](https://www.python.org/dev/peps/pep-3115/),
                [Introduction to Metaclasses (in Python 2.x)](http://stackoverflow.com/a/6581949),
                [API Docs (Python 3.x)](https://docs.python.org/3/reference/datamodel.html#metaclasses)*


* ### "nonlocal"

    ```python
    >>> x = 0
    >>> def f():
    ...     x = 1
    ...     def g():
    ...         nonlocal x
    ...         x = 2
    ...     print x
    ...     g()
    ...     print x
    ...
    >>> print x; f(); print x
    0
    1
    2
    0
    >>> nonlocal = True; print nonlocal
    True
    ```

    Caveat: As you can see, to maintain backwards compatibility nonlocal is not
    a keyword, unlike in Python 3.x. So it can still be used as an identifier.

    *More info: [PEP 3104](https://www.python.org/dev/peps/pep-3104/),
                [API Docs](https://docs.python.org/3/reference/simple_stmts.html#nonlocal)*


* ### "yield from" Syntax

    ```python
    >>> def generator():
    ...     yield from range(3)
    ...     yield from ['a', 'b', 'c']
    ...
    >>> [x for x in generator()]
    [0, 1, 2, 'a', 'b', 'c']
    ```

    *More info: [PEP 380](https://www.python.org/dev/peps/pep-0380/)*


* ### "typing" Module

    ```python
    >>> from typing import List, Dict
    >>> List[Dict[str, int]]
    typing.List[typing.Dict[str, int]]
    >>> def wordcount(words:List[str]) -> Dict[str, int]:
    ...     return collections.Counter(words)
    ```

    *More info: [PEP 483](https://www.python.org/dev/peps/pep-0483/),
                [PEP 484](https://www.python.org/dev/peps/pep-0484/),
                [API Docs](https://docs.python.org/3/library/typing.html)*


* ### Function Signatures in "inspect"

    ```python
    >>> import inspect
    >>> def f(a:int, b, *args, c:str="foo", **kwds) -> list: pass
    ...
    >>> inspect.signature(f)
    <Signature (a:int, b, *args, c:str='foo', **kwds) -> list>
    >>> inspect.signature(f).parameters['c'].default
    'foo'
    ```

    *More info: [PEP 362](https://www.python.org/dev/peps/pep-0362/),
                [API Docs](https://docs.python.org/3/library/inspect.html#introspecting-callables-with-the-signature-object)*


* ### Matrix Multiplication Operator

    ```python
    >>> import numpy as np
    >>> class Matrix(np.matrix):
    ...     def __matmul__(self, other):
    ...         return np.dot(self, other)
    ...
    >>> X = Matrix([[1, 2], [3, 4]])
    >>> Y = Matrix([[4, 3], [2, 1]])
    >>> print X
    [[1 2]
     [3 4]]
    >>> print Y
    [[4 3]
     [2 1]]
    >>> print X @ Y
    [[ 8  5]
     [20 13]]
    >>> X @= Y
    >>> X
    matrix([[ 8,  5],
            [20, 13]])
    ```

    *More info: [PEP 465](https://www.python.org/dev/peps/pep-0465/)*


* ### Fine-grained OSErrors

    ```python
    >>> open("not a file")
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
    IOError: [Errno 2] No such file or directory: 'not a file'
    >>> try:
    ...     open("not a file")
    ... except FileNotFoundError:
    ...     pass
    ...
    >>>
    ```

    Caveat: As you can see from the example, to maintain full backwards
    compatibility Tauthon does not raise these new OSErrors. Rather it gives
    you fine-grained OSErrors that you can catch them with, as an alternative to
    checking errno.

    *More info: [PEP 3151](https://www.python.org/dev/peps/pep-3151/),
                [API Docs](https://docs.python.org/3/library/exceptions.html#os-exceptions)*


* ### Underscores in Numeric Literals

    ```python
    >>> 1_234_567
    1234567
    >>> 0xBEEF_CAFE
    3203386110
    >>> 0b1111_0000
    240
    >>>
    ```

    *More info: [PEP 515](https://www.python.org/dev/peps/pep-0515/)*


* ### "concurrent.futures" Module

    ```python
    >>> from concurrent.futures import ThreadPoolExecutor
    >>> from datetime import datetime
    >>> import time
    >>> def snooze(seconds):
    ...     print "It's now %s, snoozing for %d seconds." % (datetime.now(), seconds)
    ...     time.sleep(seconds)
    ...     print "BEEP BEEP BEEP it's %s, time to get up!" % datetime.now()
    ...
    >>> def snooze_again(future):
    ...     print "Going back to sleep"
    ...     snooze(3)
    ...
    >>> pool = ThreadPoolExecutor()
    >>> future = pool.submit(snooze, 60)
    It's now 2016-11-17 12:09:41.822658, snoozing for 60 seconds.
    >>> print future
    <Future at 0x1040b7b10 state=running>
    >>> future.add_done_callback(snooze_again)
    >>> print datetime.now()
    2016-11-17 12:10:11.189143
    >>> BEEP BEEP BEEP it's 2016-11-17 12:10:41.824054, time to get up!
    Going back to sleep
    It's now 2016-11-17 12:10:41.824206, snoozing for 3 seconds.
    BEEP BEEP BEEP it's 2016-11-17 12:10:44.829196, time to get up!
    ```

    *More info: [PEP 3148](https://www.python.org/dev/peps/pep-3148/),
                [API Docs](https://docs.python.org/3/library/concurrent.futures.html)*


* ### "types.MappingProxyType"

    ```python
    >>> import types
    >>> original = {'a': 1}
    >>> read_only_view = types.MappingProxyType(original)
    >>> read_only_view['a']
    1
    >>> read_only_view['b'] = 2
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
    TypeError: 'dict_proxy' object does not support item assignment
    >>> original['c'] = 3
    >>> original
    {'a': 1, 'c': 3}
    >>> read_only_view['c']
    3
    ```

    *More info: [API Docs](https://docs.python.org/3.5/library/types.html#types.MappingProxyType)*


* ### "selectors" Module

    ```python
    >>> import selectors
    ```

    *More info: [API Docs](https://docs.python.org/3/library/selectors.html)*

* ### UTF-8 as the default source encoding

    *More info: [PEP 3120](https://www.python.org/dev/peps/pep-3120/)*

* ### monotonic time, performance counter, and process time functions

    *More info: [PEP 418](https://www.python.org/dev/peps/pep-0418/)*

* ### tab completion enabled by default in the interactive interpreter

    *More info: [BPO 5845](https://bugs.python.org/issue5845)*

* ### module/function aliases and wrappers matching Python3's module renaming and reorganization

    *More info: [PR #128](https://github.com/naftaliharris/tauthon/pull/128)*

Building and Installation
-------------------------

Linux:

```
$ ./configure
$ make
```

OSX:

```
$ brew install openssl xz
$ CPPFLAGS="-I$(brew --prefix openssl)/include" LDFLAGS="-L$(brew --prefix openssl)/lib" MACOSX_DEPLOYMENT_TARGET=10.6 ./configure
$ make
```

You can then run Tauthon with `./tauthon` or `./tauthon.exe`.

Install with
```
$ make install
```


Backwards-incompatibilities
---------------------------

There are a small handful of backwards incompatibilities introduced by
Tauthon. Triggering these involves checking the Python version, introspection of
Python internals (including the AST), or depending on errors being raised from
nonexistent new features.


License
-------

Tauthon is licensed under the Python Software License, (see the LICENSE file
for details). This is not an official Python release; see [PEP
404](https://www.python.org/dev/peps/pep-0404/).
