:mod:`xml.dom.pulldom` --- Support for building partial DOM trees
=================================================================

.. module:: xml.dom.pulldom
   :synopsis: Support for building partial DOM trees from SAX events.
.. moduleauthor:: Paul Prescod <paul@prescod.net>


.. versionadded:: 2.0

**Source code:** :source:`Lib/xml/dom/pulldom.py`

--------------

:mod:`xml.dom.pulldom` allows building only selected portions of a Document
Object Model representation of a document from SAX events.


.. warning::

   The :mod:`xml.dom.pulldom` module is not secure against
   maliciously constructed data.  If you need to parse untrusted or
   unauthenticated data see :ref:`xml-vulnerabilities`.

.. versionchanged:: 2.8.3

   The SAX parser no longer processes general external entities by default to
   increase security by default. To enable processing of external entities,
   pass a custom parser instance in::

      from xml.dom.pulldom import parse
      from xml.sax import make_parser
      from xml.sax.handler import feature_external_ges

      parser = make_parser()
      parser.setFeature(feature_external_ges, True)
      parse(filename, parser=parser)


.. class:: PullDOM([documentFactory])

   :class:`xml.sax.handler.ContentHandler` implementation that ...


.. class:: DOMEventStream(stream, parser, bufsize)

   ...


.. class:: SAX2DOM([documentFactory])

   :class:`xml.sax.handler.ContentHandler` implementation that ...


.. function:: parse(stream_or_string[, parser[, bufsize]])

   ...


.. function:: parseString(string[, parser])

   ...


.. data:: default_bufsize

   Default value for the *bufsize* parameter to :func:`parse`.

   .. versionchanged:: 2.1
      The value of this variable can be changed before calling :func:`parse` and the
      new value will take effect.


.. _domeventstream-objects:

DOMEventStream Objects
----------------------


.. method:: DOMEventStream.getEvent()

   ...


.. method:: DOMEventStream.expandNode(node)

   ...


.. method:: DOMEventStream.reset()

   ...

