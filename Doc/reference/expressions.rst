
.. _expressions:

***********
Expressions
***********

.. index:: single: expression

This chapter explains the meaning of the elements of expressions in Python.

.. index:: single: BNF

**Syntax Notes:** In this and the following chapters, extended BNF notation will
be used to describe syntax, not lexical analysis.  When (one alternative of) a
syntax rule has the form

.. productionlist:: *
   name: `othername`

.. index:: single: syntax

and no semantics are given, the semantics of this form of ``name`` are the same
as for ``othername``.


.. _conversions:

Arithmetic conversions
======================

.. index:: pair: arithmetic; conversion

When a description of an arithmetic operator below uses the phrase "the numeric
arguments are converted to a common type," the arguments are coerced using the
coercion rules listed at  :ref:`coercion-rules`.  If both arguments are standard
numeric types, the following coercions are applied:

* If either argument is a complex number, the other is converted to complex;

* otherwise, if either argument is a floating point number, the other is
  converted to floating point;

* otherwise, if either argument is a long integer, the other is converted to
  long integer;

* otherwise, both must be plain integers and no conversion is necessary.

Some additional rules apply for certain operators (e.g., a string left argument
to the '%' operator). Extensions can define their own coercions.


.. _atoms:

Atoms
=====

.. index:: single: atom

Atoms are the most basic elements of expressions.  The simplest atoms are
identifiers or literals.  Forms enclosed in reverse quotes or in parentheses,
brackets or braces are also categorized syntactically as atoms.  The syntax for
atoms is:

.. productionlist::
   atom: `identifier` | `literal` | `enclosure`
   enclosure: `parenth_form` | `list_display`
            : | `generator_expression` | `dict_display` | `set_display`
            : | `string_conversion` | `yield_atom`


.. _atom-identifiers:

Identifiers (Names)
-------------------

.. index::
   single: name
   single: identifier

An identifier occurring as an atom is a name.  See section :ref:`identifiers`
for lexical definition and section :ref:`naming` for documentation of naming and
binding.

.. index:: exception: NameError

When the name is bound to an object, evaluation of the atom yields that object.
When a name is not bound, an attempt to evaluate it raises a :exc:`NameError`
exception.

.. index::
   pair: name; mangling
   pair: private; names

**Private name mangling:** When an identifier that textually occurs in a class
definition begins with two or more underscore characters and does not end in two
or more underscores, it is considered a :dfn:`private name` of that class.
Private names are transformed to a longer form before code is generated for
them.  The transformation inserts the class name, with leading underscores
removed and a single underscore inserted, in front of the name.  For example,
the identifier ``__spam`` occurring in a class named ``Ham`` will be transformed
to ``_Ham__spam``.  This transformation is independent of the syntactical
context in which the identifier is used.  If the transformed name is extremely
long (longer than 255 characters), implementation defined truncation may happen.
If the class name consists only of underscores, no transformation is done.



.. _atom-literals:

Literals
--------

.. index:: single: literal

Python supports string literals and various numeric literals:

.. productionlist::
   literal: `stringliteral` | `integer` | `longinteger`
          : | `floatnumber` | `imagnumber`

Evaluation of a literal yields an object of the given type (string, integer,
long integer, floating point number, complex number) with the given value.  The
value may be approximated in the case of floating point and imaginary (complex)
literals.  See section :ref:`literals` for details.

.. index::
   triple: immutable; data; type
   pair: immutable; object

All literals correspond to immutable data types, and hence the object's identity
is less important than its value.  Multiple evaluations of literals with the
same value (either the same occurrence in the program text or a different
occurrence) may obtain the same object or a different object with the same
value.


.. _parenthesized:

Parenthesized forms
-------------------

.. index:: single: parenthesized form

A parenthesized form is an optional expression list enclosed in parentheses:

.. productionlist::
   parenth_form: "(" [`expression_list`] ")"

A parenthesized expression list yields whatever that expression list yields: if
the list contains at least one comma, it yields a tuple; otherwise, it yields
the single expression that makes up the expression list.

.. index:: pair: empty; tuple

An empty pair of parentheses yields an empty tuple object.  Since tuples are
immutable, the rules for literals apply (i.e., two occurrences of the empty
tuple may or may not yield the same object).

.. index::
   single: comma
   pair: tuple; display

Note that tuples are not formed by the parentheses, but rather by use of the
comma operator.  The exception is the empty tuple, for which parentheses *are*
required --- allowing unparenthesized "nothing" in expressions would cause
ambiguities and allow common typos to pass uncaught.


.. _lists:

List displays
-------------

.. index::
   pair: list; display
   pair: list; comprehensions

A list display is a possibly empty series of expressions enclosed in square
brackets:

.. productionlist::
   list_display: "[" [`expression_list` | `list_comprehension`] "]"
   list_comprehension: `expression` `list_for`
   list_for: "for" `target_list` "in" `old_expression_list` [`list_iter`]
   old_expression_list: `old_expression` [("," `old_expression`)+ [","]]
   old_expression: `or_test` | `old_lambda_expr`
   list_iter: `list_for` | `list_if`
   list_if: "if" `old_expression` [`list_iter`]

.. index::
   pair: list; comprehensions
   object: list
   pair: empty; list

A list display yields a new list object.  Its contents are specified by
providing either a list of expressions or a list comprehension.  When a
comma-separated list of expressions is supplied, its elements are evaluated from
left to right and placed into the list object in that order.  When a list
comprehension is supplied, it consists of a single expression followed by at
least one :keyword:`for` clause and zero or more :keyword:`for` or :keyword:`if`
clauses.  In this case, the elements of the new list are those that would be
produced by considering each of the :keyword:`for` or :keyword:`if` clauses a
block, nesting from left to right, and evaluating the expression to produce a
list element each time the innermost block is reached [#]_.


.. _comprehensions:

Displays for sets and dictionaries
----------------------------------

For constructing a set or a dictionary Python provides special syntax
called "displays", each of them in two flavors:

* either the container contents are listed explicitly, or

* they are computed via a set of looping and filtering instructions, called a
  :dfn:`comprehension`.

Common syntax elements for comprehensions are:

.. productionlist::
   comprehension: `expression` `comp_for`
   comp_for: "for" `target_list` "in" `or_test` [`comp_iter`]
   comp_iter: `comp_for` | `comp_if`
   comp_if: "if" `expression_nocond` [`comp_iter`]

The comprehension consists of a single expression followed by at least one
:keyword:`for` clause and zero or more :keyword:`for` or :keyword:`if` clauses.
In this case, the elements of the new container are those that would be produced
by considering each of the :keyword:`for` or :keyword:`if` clauses a block,
nesting from left to right, and evaluating the expression to produce an element
each time the innermost block is reached.

Note that the comprehension is executed in a separate scope, so names assigned
to in the target list don't "leak" in the enclosing scope.


.. _genexpr:

Generator expressions
---------------------

.. index:: pair: generator; expression
           object: generator

A generator expression is a compact generator notation in parentheses:

.. productionlist::
   generator_expression: "(" `expression` `comp_for` ")"

A generator expression yields a new generator object.  Its syntax is the same as
for comprehensions, except that it is enclosed in parentheses instead of
brackets or curly braces.

Variables used in the generator expression are evaluated lazily when the
:meth:`__next__` method is called for generator object (in the same fashion as
normal generators).  However, the leftmost :keyword:`for` clause is immediately
evaluated, so that an error produced by it can be seen before any other possible
error in the code that handles the generator expression.  Subsequent
:keyword:`for` clauses cannot be evaluated immediately since they may depend on
the previous :keyword:`for` loop. For example: ``(x*y for x in range(10) for y
in bar(x))``.

The parentheses can be omitted on calls with only one argument.  See section
:ref:`calls` for the detail.

.. _dict:

Dictionary displays
-------------------

.. index:: pair: dictionary; display
           key, datum, key/datum pair
           object: dictionary

A dictionary display is a possibly empty series of key/datum pairs enclosed in
curly braces:

.. productionlist::
   dict_display: "{" [`key_datum_list` | `dict_comprehension`] "}"
   key_datum_list: `key_datum` ("," `key_datum`)* [","]
   key_datum: `expression` ":" `expression`
   dict_comprehension: `expression` ":" `expression` `comp_for`

A dictionary display yields a new dictionary object.

If a comma-separated sequence of key/datum pairs is given, they are evaluated
from left to right to define the entries of the dictionary: each key object is
used as a key into the dictionary to store the corresponding datum.  This means
that you can specify the same key multiple times in the key/datum list, and the
final dictionary's value for that key will be the last one given.

A dict comprehension, in contrast to list and set comprehensions, needs two
expressions separated with a colon followed by the usual "for" and "if" clauses.
When the comprehension is run, the resulting key and value elements are inserted
in the new dictionary in the order they are produced.

.. index:: pair: immutable; object
           hashable

Restrictions on the types of the key values are listed earlier in section
:ref:`types`.  (To summarize, the key type should be :term:`hashable`, which excludes
all mutable objects.)  Clashes between duplicate keys are not detected; the last
datum (textually rightmost in the display) stored for a given key value
prevails.


.. _set:

Set displays
------------

.. index:: pair: set; display
           object: set

A set display is denoted by curly braces and distinguishable from dictionary
displays by the lack of colons separating keys and values:

.. productionlist::
   set_display: "{" (`expression_list` | `comprehension`) "}"

A set display yields a new mutable set object, the contents being specified by
either a sequence of expressions or a comprehension.  When a comma-separated
list of expressions is supplied, its elements are evaluated from left to right
and added to the set object.  When a comprehension is supplied, the set is
constructed from the elements resulting from the comprehension.

An empty set cannot be constructed with ``{}``; this literal constructs an empty
dictionary.


.. _string-conversions:

String conversions
------------------

.. index::
   pair: string; conversion
   pair: reverse; quotes
   pair: backward; quotes
   single: back-quotes

A string conversion is an expression list enclosed in reverse (a.k.a. backward)
quotes:

.. productionlist::
   string_conversion: "`" `expression_list` "`"

A string conversion evaluates the contained expression list and converts the
resulting object into a string according to rules specific to its type.

If the object is a string, a number, ``None``, or a tuple, list or dictionary
containing only objects whose type is one of these, the resulting string is a
valid Python expression which can be passed to the built-in function
:func:`eval` to yield an expression with the same value (or an approximation, if
floating point numbers are involved).

(In particular, converting a string adds quotes around it and converts "funny"
characters to escape sequences that are safe to print.)

.. index:: object: recursive

Recursive objects (for example, lists or dictionaries that contain a reference
to themselves, directly or indirectly) use ``...`` to indicate a recursive
reference, and the result cannot be passed to :func:`eval` to get an equal value
(:exc:`SyntaxError` will be raised instead).

.. index::
   builtin: repr
   builtin: str

The built-in function :func:`repr` performs exactly the same conversion in its
argument as enclosing it in parentheses and reverse quotes does.  The built-in
function :func:`str` performs a similar but more user-friendly conversion.


.. _yieldexpr:

Yield expressions
-----------------

.. index::
   keyword: yield
   pair: yield; expression
   pair: generator; function

.. productionlist::
   yield_atom: "(" `yield_expression` ")"
   yield_expression: "yield" [`expression_list`]

.. versionadded:: 2.5

The :keyword:`yield` expression is only used when defining a generator function,
and can only be used in the body of a function definition. Using a
:keyword:`yield` expression in a function definition is sufficient to cause that
definition to create a generator function instead of a normal function.

When a generator function is called, it returns an iterator known as a
generator.  That generator then controls the execution of a generator function.
The execution starts when one of the generator's methods is called.  At that
time, the execution proceeds to the first :keyword:`yield` expression, where it
is suspended again, returning the value of :token:`expression_list` to
generator's caller.  By suspended we mean that all local state is retained,
including the current bindings of local variables, the instruction pointer, and
the internal evaluation stack.  When the execution is resumed by calling one of
the generator's methods, the function can proceed exactly as if the
:keyword:`yield` expression was just another external call. The value of the
:keyword:`yield` expression after resuming depends on the method which resumed
the execution.

.. index:: single: coroutine

All of this makes generator functions quite similar to coroutines; they yield
multiple times, they have more than one entry point and their execution can be
suspended.  The only difference is that a generator function cannot control
where should the execution continue after it yields; the control is always
transferred to the generator's caller.

.. index:: object: generator


Generator-iterator methods
^^^^^^^^^^^^^^^^^^^^^^^^^^

This subsection describes the methods of a generator iterator.  They can
be used to control the execution of a generator function.

Note that calling any of the generator methods below when the generator
is already executing raises a :exc:`ValueError` exception.

.. index:: exception: StopIteration


.. method:: generator.next()

   Starts the execution of a generator function or resumes it at the last executed
   :keyword:`yield` expression.  When a generator function is resumed with a
   :meth:`~generator.next` method, the current :keyword:`yield` expression
   always evaluates to
   :const:`None`.  The execution then continues to the next :keyword:`yield`
   expression, where the generator is suspended again, and the value of the
   :token:`expression_list` is returned to :meth:`~generator.next`'s caller.
   If the generator
   exits without yielding another value, a :exc:`StopIteration` exception is
   raised.

.. method:: generator.send(value)

   Resumes the execution and "sends" a value into the generator function.  The
   ``value`` argument becomes the result of the current :keyword:`yield`
   expression.  The :meth:`send` method returns the next value yielded by the
   generator, or raises :exc:`StopIteration` if the generator exits without
   yielding another value. When :meth:`send` is called to start the generator, it
   must be called with :const:`None` as the argument, because there is no
   :keyword:`yield` expression that could receive the value.


.. method:: generator.throw(type[, value[, traceback]])

   Raises an exception of type ``type`` at the point where generator was paused,
   and returns the next value yielded by the generator function.  If the generator
   exits without yielding another value, a :exc:`StopIteration` exception is
   raised.  If the generator function does not catch the passed-in exception, or
   raises a different exception, then that exception propagates to the caller.

.. index:: exception: GeneratorExit


.. method:: generator.close()

   Raises a :exc:`GeneratorExit` at the point where the generator function was
   paused.  If the generator function then raises :exc:`StopIteration` (by exiting
   normally, or due to already being closed) or :exc:`GeneratorExit` (by not
   catching the exception), close returns to its caller.  If the generator yields a
   value, a :exc:`RuntimeError` is raised.  If the generator raises any other
   exception, it is propagated to the caller.  :meth:`close` does nothing if the
   generator has already exited due to an exception or normal exit.

Here is a simple example that demonstrates the behavior of generators and
generator functions::

   >>> def echo(value=None):
   ...     print "Execution starts when 'next()' is called for the first time."
   ...     try:
   ...         while True:
   ...             try:
   ...                 value = (yield value)
   ...             except Exception, e:
   ...                 value = e
   ...     finally:
   ...         print "Don't forget to clean up when 'close()' is called."
   ...
   >>> generator = echo(1)
   >>> print generator.next()
   Execution starts when 'next()' is called for the first time.
   1
   >>> print generator.next()
   None
   >>> print generator.send(2)
   2
   >>> generator.throw(TypeError, "spam")
   TypeError('spam',)
   >>> generator.close()
   Don't forget to clean up when 'close()' is called.


.. seealso::

   :pep:`342` - Coroutines via Enhanced Generators
      The proposal to enhance the API and syntax of generators, making them usable as
      simple coroutines.


.. _primaries:

Primaries
=========

.. index:: single: primary

Primaries represent the most tightly bound operations of the language. Their
syntax is:

.. productionlist::
   primary: `atom` | `attributeref` | `subscription` | `slicing` | `call`


.. _attribute-references:

Attribute references
--------------------

.. index:: pair: attribute; reference

An attribute reference is a primary followed by a period and a name:

.. productionlist::
   attributeref: `primary` "." `identifier`

.. index::
   exception: AttributeError
   object: module
   object: list

The primary must evaluate to an object of a type that supports attribute
references, e.g., a module, list, or an instance.  This object is then asked to
produce the attribute whose name is the identifier.  If this attribute is not
available, the exception :exc:`AttributeError` is raised. Otherwise, the type
and value of the object produced is determined by the object.  Multiple
evaluations of the same attribute reference may yield different objects.


.. _subscriptions:

Subscriptions
-------------

.. index:: single: subscription

.. index::
   object: sequence
   object: mapping
   object: string
   object: tuple
   object: list
   object: dictionary
   pair: sequence; item

A subscription selects an item of a sequence (string, tuple or list) or mapping
(dictionary) object:

.. productionlist::
   subscription: `primary` "[" `expression_list` "]"

The primary must evaluate to an object of a sequence or mapping type.

If the primary is a mapping, the expression list must evaluate to an object
whose value is one of the keys of the mapping, and the subscription selects the
value in the mapping that corresponds to that key.  (The expression list is a
tuple except if it has exactly one item.)

If the primary is a sequence, the expression (list) must evaluate to a plain
integer.  If this value is negative, the length of the sequence is added to it
(so that, e.g., ``x[-1]`` selects the last item of ``x``.)  The resulting value
must be a nonnegative integer less than the number of items in the sequence, and
the subscription selects the item whose index is that value (counting from
zero).

.. index::
   single: character
   pair: string; item

A string's items are characters.  A character is not a separate data type but a
string of exactly one character.


.. _slicings:

Slicings
--------

.. index::
   single: slicing
   single: slice

.. index::
   object: sequence
   object: string
   object: tuple
   object: list

A slicing selects a range of items in a sequence object (e.g., a string, tuple
or list).  Slicings may be used as expressions or as targets in assignment or
:keyword:`del` statements.  The syntax for a slicing:

.. productionlist::
   slicing: `simple_slicing` | `extended_slicing`
   simple_slicing: `primary` "[" `short_slice` "]"
   extended_slicing: `primary` "[" `slice_list` "]"
   slice_list: `slice_item` ("," `slice_item`)* [","]
   slice_item: `expression` | `proper_slice` | `ellipsis`
   proper_slice: `short_slice` | `long_slice`
   short_slice: [`lower_bound`] ":" [`upper_bound`]
   long_slice: `short_slice` ":" [`stride`]
   lower_bound: `expression`
   upper_bound: `expression`
   stride: `expression`
   ellipsis: "..."

.. index:: pair: extended; slicing

There is ambiguity in the formal syntax here: anything that looks like an
expression list also looks like a slice list, so any subscription can be
interpreted as a slicing.  Rather than further complicating the syntax, this is
disambiguated by defining that in this case the interpretation as a subscription
takes priority over the interpretation as a slicing (this is the case if the
slice list contains no proper slice nor ellipses).  Similarly, when the slice
list has exactly one short slice and no trailing comma, the interpretation as a
simple slicing takes priority over that as an extended slicing.

The semantics for a simple slicing are as follows.  The primary must evaluate to
a sequence object.  The lower and upper bound expressions, if present, must
evaluate to plain integers; defaults are zero and the ``sys.maxint``,
respectively.  If either bound is negative, the sequence's length is added to
it.  The slicing now selects all items with index *k* such that ``i <= k < j``
where *i* and *j* are the specified lower and upper bounds.  This may be an
empty sequence.  It is not an error if *i* or *j* lie outside the range of valid
indexes (such items don't exist so they aren't selected).

.. index::
   single: start (slice object attribute)
   single: stop (slice object attribute)
   single: step (slice object attribute)

The semantics for an extended slicing are as follows.  The primary must evaluate
to a mapping object, and it is indexed with a key that is constructed from the
slice list, as follows.  If the slice list contains at least one comma, the key
is a tuple containing the conversion of the slice items; otherwise, the
conversion of the lone slice item is the key.  The conversion of a slice item
that is an expression is that expression.  The conversion of an ellipsis slice
item is the built-in ``Ellipsis`` object.  The conversion of a proper slice is a
slice object (see section :ref:`types`) whose :attr:`~slice.start`,
:attr:`~slice.stop` and :attr:`~slice.step` attributes are the values of the
expressions given as lower bound, upper bound and stride, respectively,
substituting ``None`` for missing expressions.


.. index::
   object: callable
   single: call
   single: argument; call semantics

.. _calls:

Calls
-----

A call calls a callable object (e.g., a :term:`function`) with a possibly empty
series of :term:`arguments <argument>`:

.. productionlist::
   call: `primary` "(" [`argument_list` [","]
       : | `expression` `genexpr_for`] ")"
   argument_list: `positional_arguments` ["," `keyword_arguments`]
                :   ["," "*" `expression`] ["," `keyword_arguments`]
                :   ["," "**" `expression`]
                : | `keyword_arguments` ["," "*" `expression`]
                :   ["," "**" `expression`]
                : | "*" `expression` ["," `keyword_arguments`] ["," "**" `expression`]
                : | "**" `expression`
   positional_arguments: `expression` ("," `expression`)*
   keyword_arguments: `keyword_item` ("," `keyword_item`)*
   keyword_item: `identifier` "=" `expression`

A trailing comma may be present after the positional and keyword arguments but
does not affect the semantics.

.. index::
   single: parameter; call semantics

The primary must evaluate to a callable object (user-defined functions, built-in
functions, methods of built-in objects, class objects, methods of class
instances, and certain class instances themselves are callable; extensions may
define additional callable object types).  All argument expressions are
evaluated before the call is attempted.  Please refer to section :ref:`function`
for the syntax of formal :term:`parameter` lists.

If keyword arguments are present, they are first converted to positional
arguments, as follows.  First, a list of unfilled slots is created for the
formal parameters.  If there are N positional arguments, they are placed in the
first N slots.  Next, for each keyword argument, the identifier is used to
determine the corresponding slot (if the identifier is the same as the first
formal parameter name, the first slot is used, and so on).  If the slot is
already filled, a :exc:`TypeError` exception is raised. Otherwise, the value of
the argument is placed in the slot, filling it (even if the expression is
``None``, it fills the slot).  When all arguments have been processed, the slots
that are still unfilled are filled with the corresponding default value from the
function definition.  (Default values are calculated, once, when the function is
defined; thus, a mutable object such as a list or dictionary used as default
value will be shared by all calls that don't specify an argument value for the
corresponding slot; this should usually be avoided.)  If there are any unfilled
slots for which no default value is specified, a :exc:`TypeError` exception is
raised.  Otherwise, the list of filled slots is used as the argument list for
the call.

.. impl-detail::

   An implementation may provide built-in functions whose positional parameters
   do not have names, even if they are 'named' for the purpose of documentation,
   and which therefore cannot be supplied by keyword.  In CPython, this is the
   case for functions implemented in C that use :c:func:`PyArg_ParseTuple` to
   parse their arguments.

If there are more positional arguments than there are formal parameter slots, a
:exc:`TypeError` exception is raised, unless a formal parameter using the syntax
``*identifier`` is present; in this case, that formal parameter receives a tuple
containing the excess positional arguments (or an empty tuple if there were no
excess positional arguments).

If any keyword argument does not correspond to a formal parameter name, a
:exc:`TypeError` exception is raised, unless a formal parameter using the syntax
``**identifier`` is present; in this case, that formal parameter receives a
dictionary containing the excess keyword arguments (using the keywords as keys
and the argument values as corresponding values), or a (new) empty dictionary if
there were no excess keyword arguments.

.. index::
   single: *; in function calls

If the syntax ``*expression`` appears in the function call, ``expression`` must
evaluate to an iterable.  Elements from this iterable are treated as if they
were additional positional arguments; if there are positional arguments
*x1*, ..., *xN*, and ``expression`` evaluates to a sequence *y1*, ..., *yM*, this
is equivalent to a call with M+N positional arguments *x1*, ..., *xN*, *y1*,
..., *yM*.

A consequence of this is that although the ``*expression`` syntax may appear
*after* some keyword arguments, it is processed *before* the keyword arguments
(and the ``**expression`` argument, if any -- see below).  So::

   >>> def f(a, b):
   ...     print a, b
   ...
   >>> f(b=1, *(2,))
   2 1
   >>> f(a=1, *(2,))
   Traceback (most recent call last):
     File "<stdin>", line 1, in <module>
   TypeError: f() got multiple values for keyword argument 'a'
   >>> f(1, *(2,))
   1 2

It is unusual for both keyword arguments and the ``*expression`` syntax to be
used in the same call, so in practice this confusion does not arise.

.. index::
   single: **; in function calls

If the syntax ``**expression`` appears in the function call, ``expression`` must
evaluate to a mapping, the contents of which are treated as additional keyword
arguments.  In the case of a keyword appearing in both ``expression`` and as an
explicit keyword argument, a :exc:`TypeError` exception is raised.

Formal parameters using the syntax ``*identifier`` or ``**identifier`` cannot be
used as positional argument slots or as keyword argument names.  Formal
parameters using the syntax ``(sublist)`` cannot be used as keyword argument
names; the outermost sublist corresponds to a single unnamed argument slot, and
the argument value is assigned to the sublist using the usual tuple assignment
rules after all other parameter processing is done.

A call always returns some value, possibly ``None``, unless it raises an
exception.  How this value is computed depends on the type of the callable
object.

If it is---

a user-defined function:
   .. index::
      pair: function; call
      triple: user-defined; function; call
      object: user-defined function
      object: function

   The code block for the function is executed, passing it the argument list.  The
   first thing the code block will do is bind the formal parameters to the
   arguments; this is described in section :ref:`function`.  When the code block
   executes a :keyword:`return` statement, this specifies the return value of the
   function call.

a built-in function or method:
   .. index::
      pair: function; call
      pair: built-in function; call
      pair: method; call
      pair: built-in method; call
      object: built-in method
      object: built-in function
      object: method
      object: function

   The result is up to the interpreter; see :ref:`built-in-funcs` for the
   descriptions of built-in functions and methods.

a class object:
   .. index::
      object: class
      pair: class object; call

   A new instance of that class is returned.

a class instance method:
   .. index::
      object: class instance
      object: instance
      pair: class instance; call

   The corresponding user-defined function is called, with an argument list that is
   one longer than the argument list of the call: the instance becomes the first
   argument.

a class instance:
   .. index::
      pair: instance; call
      single: __call__() (object method)

   The class must define a :meth:`__call__` method; the effect is then the same as
   if that method was called.


.. _power:

The power operator
==================

The power operator binds more tightly than unary operators on its left; it binds
less tightly than unary operators on its right.  The syntax is:

.. productionlist::
   power: `primary` ["**" `u_expr`]

Thus, in an unparenthesized sequence of power and unary operators, the operators
are evaluated from right to left (this does not constrain the evaluation order
for the operands): ``-1**2`` results in ``-1``.

The power operator has the same semantics as the built-in :func:`pow` function,
when called with two arguments: it yields its left argument raised to the power
of its right argument.  The numeric arguments are first converted to a common
type.  The result type is that of the arguments after coercion.

With mixed operand types, the coercion rules for binary arithmetic operators
apply. For int and long int operands, the result has the same type as the
operands (after coercion) unless the second argument is negative; in that case,
all arguments are converted to float and a float result is delivered. For
example, ``10**2`` returns ``100``, but ``10**-2`` returns ``0.01``. (This last
feature was added in Python 2.2. In Python 2.1 and before, if both arguments
were of integer types and the second argument was negative, an exception was
raised).

Raising ``0.0`` to a negative power results in a :exc:`ZeroDivisionError`.
Raising a negative number to a fractional power results in a :exc:`ValueError`.


.. _unary:

Unary arithmetic and bitwise operations
=======================================

.. index::
   triple: unary; arithmetic; operation
   triple: unary; bitwise; operation

All unary arithmetic and bitwise operations have the same priority:

.. productionlist::
   u_expr: `power` | "-" `u_expr` | "+" `u_expr` | "~" `u_expr`

.. index::
   single: negation
   single: minus

The unary ``-`` (minus) operator yields the negation of its numeric argument.

.. index:: single: plus

The unary ``+`` (plus) operator yields its numeric argument unchanged.

.. index:: single: inversion

The unary ``~`` (invert) operator yields the bitwise inversion of its plain or
long integer argument.  The bitwise inversion of ``x`` is defined as
``-(x+1)``.  It only applies to integral numbers.

.. index:: exception: TypeError

In all three cases, if the argument does not have the proper type, a
:exc:`TypeError` exception is raised.


.. _binary:

Binary arithmetic operations
============================

.. index:: triple: binary; arithmetic; operation

The binary arithmetic operations have the conventional priority levels.  Note
that some of these operations also apply to certain non-numeric types.  Apart
from the power operator, there are only two levels, one for multiplicative
operators and one for additive operators:

.. productionlist::
   m_expr: `u_expr` | `m_expr` "*" `u_expr` | `m_expr` "@" `m_expr` |
         : `m_expr` "//" `u_expr`| `m_expr` "/" `u_expr` |
         : `m_expr` "%" `u_expr`
   a_expr: `m_expr` | `a_expr` "+" `m_expr` | `a_expr` "-" `m_expr`

.. index:: single: multiplication

The ``*`` (multiplication) operator yields the product of its arguments.  The
arguments must either both be numbers, or one argument must be an integer (plain
or long) and the other must be a sequence. In the former case, the numbers are
converted to a common type and then multiplied together.  In the latter case,
sequence repetition is performed; a negative repetition factor yields an empty
sequence.

.. index:: single: matrix multiplication

The ``@`` (at) operator is intended to be used for matrix multiplication.  No
builtin Python types implement this operator.

.. versionadded:: 2.8

.. index::
   exception: ZeroDivisionError
   single: division

The ``/`` (division) and ``//`` (floor division) operators yield the quotient of
their arguments.  The numeric arguments are first converted to a common type.
Plain or long integer division yields an integer of the same type; the result is
that of mathematical division with the 'floor' function applied to the result.
Division by zero raises the :exc:`ZeroDivisionError` exception.

.. index:: single: modulo

The ``%`` (modulo) operator yields the remainder from the division of the first
argument by the second.  The numeric arguments are first converted to a common
type.  A zero right argument raises the :exc:`ZeroDivisionError` exception.  The
arguments may be floating point numbers, e.g., ``3.14%0.7`` equals ``0.34``
(since ``3.14`` equals ``4*0.7 + 0.34``.)  The modulo operator always yields a
result with the same sign as its second operand (or zero); the absolute value of
the result is strictly smaller than the absolute value of the second operand
[#]_.

The integer division and modulo operators are connected by the following
identity: ``x == (x/y)*y + (x%y)``.  Integer division and modulo are also
connected with the built-in function :func:`divmod`: ``divmod(x, y) == (x/y,
x%y)``.  These identities don't hold for floating point numbers; there similar
identities hold approximately where ``x/y`` is replaced by ``floor(x/y)`` or
``floor(x/y) - 1`` [#]_.

In addition to performing the modulo operation on numbers, the ``%`` operator is
also overloaded by string and unicode objects to perform string formatting (also
known as interpolation). The syntax for string formatting is described in the
Python Library Reference, section :ref:`string-formatting`.

.. deprecated:: 2.3
   The floor division operator, the modulo operator, and the :func:`divmod`
   function are no longer defined for complex numbers.  Instead, convert to a
   floating point number using the :func:`abs` function if appropriate.

.. index:: single: addition

The ``+`` (addition) operator yields the sum of its arguments. The arguments
must either both be numbers or both sequences of the same type.  In the former
case, the numbers are converted to a common type and then added together.  In
the latter case, the sequences are concatenated.

.. index:: single: subtraction

The ``-`` (subtraction) operator yields the difference of its arguments.  The
numeric arguments are first converted to a common type.


.. _shifting:

Shifting operations
===================

.. index:: pair: shifting; operation

The shifting operations have lower priority than the arithmetic operations:

.. productionlist::
   shift_expr: `a_expr` | `shift_expr` ( "<<" | ">>" ) `a_expr`

These operators accept plain or long integers as arguments.  The arguments are
converted to a common type.  They shift the first argument to the left or right
by the number of bits given by the second argument.

.. index:: exception: ValueError

A right shift by *n* bits is defined as division by ``pow(2, n)``.  A left shift
by *n* bits is defined as multiplication with ``pow(2, n)``.  Negative shift
counts raise a :exc:`ValueError` exception.

.. note::

   In the current implementation, the right-hand operand is required
   to be at most :attr:`sys.maxsize`.  If the right-hand operand is larger than
   :attr:`sys.maxsize` an :exc:`OverflowError` exception is raised.

.. _bitwise:

Binary bitwise operations
=========================

.. index:: triple: binary; bitwise; operation

Each of the three bitwise operations has a different priority level:

.. productionlist::
   and_expr: `shift_expr` | `and_expr` "&" `shift_expr`
   xor_expr: `and_expr` | `xor_expr` "^" `and_expr`
   or_expr: `xor_expr` | `or_expr` "|" `xor_expr`

.. index:: pair: bitwise; and

The ``&`` operator yields the bitwise AND of its arguments, which must be plain
or long integers.  The arguments are converted to a common type.

.. index::
   pair: bitwise; xor
   pair: exclusive; or

The ``^`` operator yields the bitwise XOR (exclusive OR) of its arguments, which
must be plain or long integers.  The arguments are converted to a common type.

.. index::
   pair: bitwise; or
   pair: inclusive; or

The ``|`` operator yields the bitwise (inclusive) OR of its arguments, which
must be plain or long integers.  The arguments are converted to a common type.


.. _augassign:

Augmented assignment expressions
================================

.. index::
   pair: augmented; assignment
   single: +=; augmented assignment
   single: -=; augmented assignment
   single: *=; augmented assignment
   single: @=; augmented assignment
   single: /=; augmented assignment
   single: %=; augmented assignment
   single: &=; augmented assignment
   single: ^=; augmented assignment
   single: |=; augmented assignment
   single: **=; augmented assignment
   single: //=; augmented assignment
   single: >>=; augmented assignment
   single: <<=; augmented assignment
   single: :=; augmented assignment

Augmented assignment is the combination, in a single expression, of a binary
operation and an assignment operation:

.. productionlist::
   augmented_assignment: `augtarget` `augop` (`expression_list` | `yield_expression`)
   augtarget: `identifier` | `attributeref` | `subscription` | `slicing`
   augop: "+=" | "-=" | "*=" | "@=" | "/=" | "//=" | "%=" | "**="
        : | ">>=" | "<<=" | "&=" | "^=" | "|=" | ":="

(See section :ref:`primaries` for the syntax definitions for the last three
symbols.)

An augmented assignment evaluates the target (which, unlike normal assignment
statements, cannot be an unpacking) and the expression list, performs the binary
operation specific to the type of assignment on the two operands, and assigns
the result to the original target.  The target is only evaluated once.
The value of the expression is the value stored to the target.

As a special case, the ``:=`` operation does not use the target's
original value, and can thus be used to introduce a new variable.

An augmented assignment expression like ``x += 1`` can
be rewritten as ``x := x + 1``
to achieve a similar, but not exactly equal effect. In the former
version, ``x`` is only evaluated once. Also, when possible, the actual operation
is performed *in-place*, meaning that rather than creating a new object and
assigning that to the target, the old object is modified instead.

With the exception of assigning to tuples and multiple targets in a single
statement, the assignment done by augmented assignment expressions
is handled the
same way as normal assignments. Similarly, with the exception of the possible
*in-place* behavior, the binary operation performed by augmented assignment is
the same as the normal binary operations.

For targets which are attribute references, the same :ref:`caveat about class
and instance attributes <attr-target-note>` applies as for regular assignments.

For compatibility with existing scripts, augmented assignment
expressions do *not* auto-print their value when evaluated as
the top-level expression of an interactive script.  Use the
``print`` statement if you desire the resulting value to
be printed.


.. _comparisons:

Comparisons
===========

.. index:: single: comparison

.. index:: pair: C; language

Unlike C, all comparison operations in Python have the same priority, which is
lower than that of any arithmetic, shifting or bitwise operation.  Also unlike
C, expressions like ``a < b < c`` have the interpretation that is conventional
in mathematics:

.. productionlist::
   comparison: `or_expr` ( `comp_operator` `or_expr` )*
   comp_operator: "<" | ">" | "==" | ">=" | "<=" | "<>" | "!="
                : | "is" ["not"] | ["not"] "in"

Comparisons yield boolean values: ``True`` or ``False``.

.. index:: pair: chaining; comparisons

Comparisons can be chained arbitrarily, e.g., ``x < y <= z`` is equivalent to
``x < y and y <= z``, except that ``y`` is evaluated only once (but in both
cases ``z`` is not evaluated at all when ``x < y`` is found to be false).

Formally, if *a*, *b*, *c*, ..., *y*, *z* are expressions and *op1*, *op2*, ...,
*opN* are comparison operators, then ``a op1 b op2 c ... y opN z`` is equivalent
to ``a op1 b and b op2 c and ... y opN z``, except that each expression is
evaluated at most once.

Note that ``a op1 b op2 c`` doesn't imply any kind of comparison between *a* and
*c*, so that, e.g., ``x < y > z`` is perfectly legal (though perhaps not
pretty).

The forms ``<>`` and ``!=`` are equivalent; for consistency with C, ``!=`` is
preferred; where ``!=`` is mentioned below ``<>`` is also accepted.  The ``<>``
spelling is considered obsolescent.

Value comparisons
-----------------

The operators ``<``, ``>``, ``==``, ``>=``, ``<=``, and ``!=`` compare the
values of two objects.  The objects do not need to have the same type.

Chapter :ref:`objects` states that objects have a value (in addition to type
and identity).  The value of an object is a rather abstract notion in Python:
For example, there is no canonical access method for an object's value.  Also,
there is no requirement that the value of an object should be constructed in a
particular way, e.g. comprised of all its data attributes. Comparison operators
implement a particular notion of what the value of an object is.  One can think
of them as defining the value of an object indirectly, by means of their
comparison implementation.

Types can customize their comparison behavior by implementing
a :meth:`__cmp__` method or
:dfn:`rich comparison methods` like :meth:`__lt__`, described in
:ref:`customization`.

The default behavior for equality comparison (``==`` and ``!=``) is based on
the identity of the objects.  Hence, equality comparison of instances with the
same identity results in equality, and equality comparison of instances with
different identities results in inequality.  A motivation for this default
behavior is the desire that all objects should be reflexive (i.e. ``x is y``
implies ``x == y``).

The default order comparison (``<``, ``>``, ``<=``, and ``>=``) gives a
consistent but arbitrary order.

(This unusual definition of comparison was used to simplify the definition of
operations like sorting and the :keyword:`in` and :keyword:`not in` operators.
In the future, the comparison rules for objects of different types are likely to
change.)

The behavior of the default equality comparison, that instances with different
identities are always unequal, may be in contrast to what types will need that
have a sensible definition of object value and value-based equality.  Such
types will need to customize their comparison behavior, and in fact, a number
of built-in types have done that.

The following list describes the comparison behavior of the most important
built-in types.

* Numbers of built-in numeric types (:ref:`typesnumeric`) and of the standard
  library types :class:`fractions.Fraction` and :class:`decimal.Decimal` can be
  compared within and across their types, with the restriction that complex
  numbers do not support order comparison.  Within the limits of the types
  involved, they compare mathematically (algorithmically) correct without loss
  of precision.

* Strings (instances of :class:`str` or :class:`unicode`)
  compare lexicographically using the numeric equivalents (the
  result of the built-in function :func:`ord`) of their characters. [#]_
  When comparing an 8-bit string and a Unicode string, the 8-bit string
  is converted to Unicode.  If the conversion fails, the strings
  are considered unequal.

* Instances of :class:`tuple` or :class:`list` can be compared only
  within each of their types.  Equality comparison across these types
  results in unequality, and ordering comparison across these types
  gives an arbitrary order.

  These sequences compare lexicographically using comparison of corresponding
  elements, whereby reflexivity of the elements is enforced.

  In enforcing reflexivity of elements, the comparison of collections assumes
  that for a collection element ``x``, ``x == x`` is always true.  Based on
  that assumption, element identity is compared first, and element comparison
  is performed only for distinct elements.  This approach yields the same
  result as a strict element comparison would, if the compared elements are
  reflexive.  For non-reflexive elements, the result is different than for
  strict element comparison.

  Lexicographical comparison between built-in collections works as follows:

  - For two collections to compare equal, they must be of the same type, have
    the same length, and each pair of corresponding elements must compare
    equal (for example, ``[1,2] == (1,2)`` is false because the type is not the
    same).

  - Collections are ordered the same as their
    first unequal elements (for example, ``cmp([1,2,x], [1,2,y])`` returns the
    same as ``cmp(x,y)``).  If a corresponding element does not exist, the
    shorter collection is ordered first (for example, ``[1,2] < [1,2,3]`` is
    true).

* Mappings (instances of :class:`dict`) compare equal if and only if they have
  equal `(key, value)` pairs. Equality comparison of the keys and values
  enforces reflexivity.

  Outcomes other than equality are resolved
  consistently, but are not otherwise defined. [#]_

* Most other objects of built-in types compare unequal unless they are the same
  object; the choice whether one object is considered smaller or larger than
  another one is made arbitrarily but consistently within one execution of a
  program.

User-defined classes that customize their comparison behavior should follow
some consistency rules, if possible:

* Equality comparison should be reflexive.
  In other words, identical objects should compare equal:

    ``x is y`` implies ``x == y``

* Comparison should be symmetric.
  In other words, the following expressions should have the same result:

    ``x == y`` and ``y == x``

    ``x != y`` and ``y != x``

    ``x < y`` and ``y > x``

    ``x <= y`` and ``y >= x``

* Comparison should be transitive.
  The following (non-exhaustive) examples illustrate that:

    ``x > y and y > z`` implies ``x > z``

    ``x < y and y <= z`` implies ``x < z``

* Inverse comparison should result in the boolean negation.
  In other words, the following expressions should have the same result:

    ``x == y`` and ``not x != y``

    ``x < y`` and ``not x >= y`` (for total ordering)

    ``x > y`` and ``not x <= y`` (for total ordering)

  The last two expressions apply to totally ordered collections (e.g. to
  sequences, but not to sets or mappings). See also the
  :func:`~functools.total_ordering` decorator.

* The :func:`hash` result should be consistent with equality.
  Objects that are equal should either have the same hash value,
  or be marked as unhashable.

Python does not enforce these consistency rules.


.. _in:
.. _not in:
.. _membership-test-details:

Membership test operations
--------------------------

The operators :keyword:`in` and :keyword:`not in` test for membership.  ``x in
s`` evaluates to ``True`` if *x* is a member of *s*, and ``False`` otherwise.
``x not in s`` returns the negation of ``x in s``.  All built-in sequences and
set types support this as well as dictionary, for which :keyword:`in` tests
whether the dictionary has a given key. For container types such as list, tuple,
set, frozenset, dict, or collections.deque, the expression ``x in y`` is equivalent
to ``any(x is e or x == e for e in y)``.

For the string and bytes types, ``x in y`` is ``True`` if and only if *x* is a
substring of *y*.  An equivalent test is ``y.find(x) != -1``.  Empty strings are
always considered to be a substring of any other string, so ``"" in "abc"`` will
return ``True``.

For user-defined classes which define the :meth:`__contains__` method, ``x in
y`` returns ``True`` if ``y.__contains__(x)`` returns a true value, and
``False`` otherwise.

For user-defined classes which do not define :meth:`__contains__` but do define
:meth:`__iter__`, ``x in y`` is ``True`` if some value ``z`` with ``x == z`` is
produced while iterating over ``y``.  If an exception is raised during the
iteration, it is as if :keyword:`in` raised that exception.

Lastly, the old-style iteration protocol is tried: if a class defines
:meth:`__getitem__`, ``x in y`` is ``True`` if and only if there is a non-negative
integer index *i* such that ``x == y[i]``, and all lower integer indices do not
raise :exc:`IndexError` exception. (If any other exception is raised, it is as
if :keyword:`in` raised that exception).

.. index::
   operator: in
   operator: not in
   pair: membership; test
   object: sequence

The operator :keyword:`not in` is defined to have the inverse true value of
:keyword:`in`.

.. index::
   operator: is
   operator: is not
   pair: identity; test


.. _is:
.. _is not:

Identity comparisons
--------------------

The operators :keyword:`is` and :keyword:`is not` test for object identity: ``x
is y`` is true if and only if *x* and *y* are the same object.  ``x is not y``
yields the inverse truth value. [#]_


.. _booleans:
.. _and:
.. _or:
.. _not:

Boolean operations
==================

.. index::
   pair: Conditional; expression
   pair: Boolean; operation

.. productionlist::
   or_test: `and_test` | `or_test` "or" `and_test`
   and_test: `not_test` | `and_test` "and" `not_test`
   not_test: `comparison` | "not" `not_test`

In the context of Boolean operations, and also when expressions are used by
control flow statements, the following values are interpreted as false:
``False``, ``None``, numeric zero of all types, and empty strings and containers
(including strings, tuples, lists, dictionaries, sets and frozensets).  All
other values are interpreted as true.  (See the :meth:`~object.__nonzero__`
special method for a way to change this.)

.. index:: operator: not

The operator :keyword:`not` yields ``True`` if its argument is false, ``False``
otherwise.

.. index:: operator: and

The expression ``x and y`` first evaluates *x*; if *x* is false, its value is
returned; otherwise, *y* is evaluated and the resulting value is returned.

.. index:: operator: or

The expression ``x or y`` first evaluates *x*; if *x* is true, its value is
returned; otherwise, *y* is evaluated and the resulting value is returned.

(Note that neither :keyword:`and` nor :keyword:`or` restrict the value and type
they return to ``False`` and ``True``, but rather return the last evaluated
argument. This is sometimes useful, e.g., if ``s`` is a string that should be
replaced by a default value if it is empty, the expression ``s or 'foo'`` yields
the desired value.  Because :keyword:`not` has to invent a value anyway, it does
not bother to return a value of the same type as its argument, so e.g., ``not
'foo'`` yields ``False``, not ``''``.)


Conditional Expressions
=======================

.. versionadded:: 2.5

.. index::
   pair: conditional; expression
   pair: ternary; operator

.. productionlist::
   conditional_expression: `or_test` ["if" `or_test` "else" `expression`]
   expression: `conditional_expression` | `lambda_expr`

Conditional expressions (sometimes called a "ternary operator") have the lowest
priority of all Python operations.

The expression ``x if C else y`` first evaluates the condition, *C* (*not* *x*);
if *C* is true, *x* is evaluated and its value is returned; otherwise, *y* is
evaluated and its value is returned.

See :pep:`308` for more details about conditional expressions.


.. _lambdas:
.. _lambda:

Lambdas
=======

.. index::
   pair: lambda; expression
   pair: anonymous; function

.. productionlist::
   lambda_expr: "lambda" [`parameter_list`]: `expression`
   old_lambda_expr: "lambda" [`parameter_list`]: `old_expression`

Lambda expressions (sometimes called lambda forms) have the same syntactic position as
expressions.  They are a shorthand to create anonymous functions; the expression
``lambda arguments: expression`` yields a function object.  The unnamed object
behaves like a function object defined with ::

   def name(arguments):
       return expression

See section :ref:`function` for the syntax of parameter lists.  Note that
functions created with lambda expressions cannot contain statements.


.. _exprlists:

Expression lists
================

.. index:: pair: expression; list

.. productionlist::
   expression_list: `expression` ( "," `expression` )* [","]

.. index:: object: tuple

An expression list containing at least one comma yields a tuple.  The length of
the tuple is the number of expressions in the list.  The expressions are
evaluated from left to right.

.. index:: pair: trailing; comma

The trailing comma is required only to create a single tuple (a.k.a. a
*singleton*); it is optional in all other cases.  A single expression without a
trailing comma doesn't create a tuple, but rather yields the value of that
expression. (To create an empty tuple, use an empty pair of parentheses:
``()``.)


.. _evalorder:

Evaluation order
================

.. index:: pair: evaluation; order

Python evaluates expressions from left to right. Notice that while evaluating an
assignment, the right-hand side is evaluated before the left-hand side.

In the following lines, expressions will be evaluated in the arithmetic order of
their suffixes::

   expr1, expr2, expr3, expr4
   (expr1, expr2, expr3, expr4)
   {expr1: expr2, expr3: expr4}
   expr1 + expr2 * (expr3 - expr4)
   expr1(expr2, expr3, *expr4, **expr5)
   expr3, expr4 = expr1, expr2


.. _operator-summary:

Operator precedence
===================

.. index:: pair: operator; precedence

The following table summarizes the operator precedences in Python, from lowest
precedence (least binding) to highest precedence (most binding). Operators in
the same box have the same precedence.  Unless the syntax is explicitly given,
operators are binary.  Operators in the same box group left to right (except for
comparisons, including tests, which all have the same precedence and chain from
left to right --- see section :ref:`comparisons` --- and exponentiation, which
groups from right to left).

+-----------------------------------------------+-------------------------------------+
| Operator                                      | Description                         |
+===============================================+=====================================+
| :keyword:`lambda`                             | Lambda expression                   |
+-----------------------------------------------+-------------------------------------+
| :keyword:`if` -- :keyword:`else`              | Conditional expression              |
+-----------------------------------------------+-------------------------------------+
| :keyword:`or`                                 | Boolean OR                          |
+-----------------------------------------------+-------------------------------------+
| :keyword:`and`                                | Boolean AND                         |
+-----------------------------------------------+-------------------------------------+
| :keyword:`not` ``x``                          | Boolean NOT                         |
+-----------------------------------------------+-------------------------------------+
| :keyword:`in`, :keyword:`not in`,             | Comparisons, including membership   |
| :keyword:`is`, :keyword:`is not`, ``<``,      | tests and identity tests            |
| ``<=``, ``>``, ``>=``, ``<>``, ``!=``, ``==`` |                                     |
+-----------------------------------------------+-------------------------------------+
| ``|``                                         | Bitwise OR                          |
+-----------------------------------------------+-------------------------------------+
| ``^``                                         | Bitwise XOR                         |
+-----------------------------------------------+-------------------------------------+
| ``&``                                         | Bitwise AND                         |
+-----------------------------------------------+-------------------------------------+
| ``<<``, ``>>``                                | Shifts                              |
+-----------------------------------------------+-------------------------------------+
| ``+``, ``-``                                  | Addition and subtraction            |
+-----------------------------------------------+-------------------------------------+
| ``*``, ``@``, ``/``, ``//``, ``%``            | Multiplication, matrix              |
|                                               | multiplication division,            |
|                                               | remainder [#]_                      |
+-----------------------------------------------+-------------------------------------+
| ``+x``, ``-x``, ``~x``                        | Positive, negative, bitwise NOT     |
+-----------------------------------------------+-------------------------------------+
| ``**``                                        | Exponentiation [#]_                 |
+-----------------------------------------------+-------------------------------------+
| ``x[index]``, ``x[index:index]``,             | Subscription, slicing,              |
| ``x(arguments...)``, ``x.attribute``          | call, attribute reference           |
+-----------------------------------------------+-------------------------------------+
| ``(expressions...)``,                         | Binding or tuple display,           |
| ``[expressions...]``,                         | list display,                       |
| ``{key: value...}``,                          | dictionary display,                 |
| ```expressions...```                          | string conversion                   |
+-----------------------------------------------+-------------------------------------+

.. rubric:: Footnotes

.. [#] In Python 2.3 and later releases, a list comprehension "leaks" the control
   variables of each ``for`` it contains into the containing scope.  However, this
   behavior is deprecated, and relying on it will not work in Python 3.

.. [#] While ``abs(x%y) < abs(y)`` is true mathematically, for floats it may not be
   true numerically due to roundoff.  For example, and assuming a platform on which
   a Python float is an IEEE 754 double-precision number, in order that ``-1e-100 %
   1e100`` have the same sign as ``1e100``, the computed result is ``-1e-100 +
   1e100``, which is numerically exactly equal to ``1e100``.  The function
   :func:`math.fmod` returns a result whose sign matches the sign of the
   first argument instead, and so returns ``-1e-100`` in this case. Which approach
   is more appropriate depends on the application.

.. [#] If x is very close to an exact integer multiple of y, it's possible for
   ``floor(x/y)`` to be one larger than ``(x-x%y)/y`` due to rounding.  In such
   cases, Python returns the latter result, in order to preserve that
   ``divmod(x,y)[0] * y + x % y`` be very close to ``x``.

.. [#] The Unicode standard distinguishes between :dfn:`code points`
   (e.g. U+0041) and :dfn:`abstract characters` (e.g. "LATIN CAPITAL LETTER A").
   While most abstract characters in Unicode are only represented using one
   code point, there is a number of abstract characters that can in addition be
   represented using a sequence of more than one code point.  For example, the
   abstract character "LATIN CAPITAL LETTER C WITH CEDILLA" can be represented
   as a single :dfn:`precomposed character` at code position U+00C7, or as a
   sequence of a :dfn:`base character` at code position U+0043 (LATIN CAPITAL
   LETTER C), followed by a :dfn:`combining character` at code position U+0327
   (COMBINING CEDILLA).

   The comparison operators on unicode strings compare at the level of Unicode code
   points. This may be counter-intuitive to humans.  For example,
   ``u"\u00C7" == u"\u0043\u0327"`` is ``False``, even though both strings
   represent the same abstract character "LATIN CAPITAL LETTER C WITH CEDILLA".

   To compare strings at the level of abstract characters (that is, in a way
   intuitive to humans), use :func:`unicodedata.normalize`.

.. [#] Earlier versions of Python used lexicographic comparison of the sorted (key,
   value) lists, but this was very expensive for the common case of comparing for
   equality.  An even earlier version of Python compared dictionaries by identity
   only, but this caused surprises because people expected to be able to test a
   dictionary for emptiness by comparing it to ``{}``.

.. [#] Due to automatic garbage-collection, free lists, and the dynamic nature of
   descriptors, you may notice seemingly unusual behaviour in certain uses of
   the :keyword:`is` operator, like those involving comparisons between instance
   methods, or constants.  Check their documentation for more info.

.. [#] The ``%`` operator is also used for string formatting; the same
   precedence applies.

.. [#] The power operator ``**`` binds less tightly than an arithmetic or
   bitwise unary operator on its right, that is, ``2**-1`` is ``0.5``.
