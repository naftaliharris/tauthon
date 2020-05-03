"""Tests for backported functions in urllib.parse"""

from __future__ import unicode_literals
import urllib.parse
import http.client
import unittest

def hexescape(char):
    """Escape char as RFC 2396 specifies"""
    hex_repr = hex(ord(char))[2:].upper()
    if len(hex_repr) == 1:
        hex_repr = "0%s" % hex_repr
    return "%" + hex_repr

class QuotingTests(unittest.TestCase):
    r"""Tests for urllib.quote() and urllib.quote_plus()

    According to RFC 3986 (Uniform Resource Identifiers), to escape a
    character you write it as '%' + <2 character US-ASCII hex value>.
    The Python code of ``'%' + hex(ord(<character>))[2:]`` escapes a
    character properly. Case does not matter on the hex letters.

    The various character sets specified are:

    Reserved characters : ";/?:@&=+$,"
        Have special meaning in URIs and must be escaped if not being used for
        their special meaning
    Data characters : letters, digits, and "-_.!~*'()"
        Unreserved and do not need to be escaped; can be, though, if desired
    Control characters : 0x00 - 0x1F, 0x7F
        Have no use in URIs so must be escaped
    space : 0x20
        Must be escaped
    Delimiters : '<>#%"'
        Must be escaped
    Unwise : "{}|\^[]`"
        Must be escaped

    """

    def test_never_quote(self):
        # Make sure quote() does not quote letters, digits, and "_,.-"
        do_not_quote = '' .join(["ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                                 "abcdefghijklmnopqrstuvwxyz",
                                 "0123456789",
                                 "_.-"])
        result = urllib.parse.quote(do_not_quote)
        self.assertEqual(do_not_quote, result,
                         "using quote(): %r != %r" % (do_not_quote, result))
        result = urllib.parse.quote_plus(do_not_quote)
        self.assertEqual(do_not_quote, result,
                        "using quote_plus(): %r != %r" % (do_not_quote, result))

    def test_default_safe(self):
        # Test '/' is default value for 'safe' parameter
        self.assertEqual(urllib.parse.quote.__defaults__[0], '/')

    def test_safe(self):
        # Test setting 'safe' parameter does what it should do
        quote_by_default = "<>"
        result = urllib.parse.quote(quote_by_default, safe=quote_by_default)
        self.assertEqual(quote_by_default, result,
                         "using quote(): %r != %r" % (quote_by_default, result))
        result = urllib.parse.quote_plus(quote_by_default,
                                         safe=quote_by_default)
        self.assertEqual(quote_by_default, result,
                         "using quote_plus(): %r != %r" %
                         (quote_by_default, result))
        # Safe expressed as bytes rather than str
        result = urllib.parse.quote(quote_by_default, safe=b"<>")
        self.assertEqual(quote_by_default, result,
                         "using quote(): %r != %r" % (quote_by_default, result))

        # This feature is not implemented in Python 2.
        # TODO: Add a workaround that allows these tests to pass.

        # "Safe" non-ASCII characters should have no effect
        # (Since URIs are not allowed to have non-ASCII characters)
        # result = urllib.parse.quote("a\xfcb", encoding="latin-1", safe="\xfc")
        # expect = urllib.parse.quote("a\xfcb", encoding="latin-1", safe="")
        # self.assertEqual(expect, result,
        #                  "using quote(): %r != %r" %
        #                  (expect, result))
        # Same as above, but using a bytes rather than str
        # result = urllib.parse.quote("a\xfcb", encoding="latin-1", safe=b"\xfc")
        # expect = urllib.parse.quote("a\xfcb", encoding="latin-1", safe="")
        # self.assertEqual(expect, result,
        #                  "using quote(): %r != %r" %
        #                  (expect, result))

    def test_default_quoting(self):
        # Make sure all characters that should be quoted are by default sans
        # space (separate test for that).
        should_quote = [chr(num) for num in range(32)] # For 0x00 - 0x1F
        should_quote.append(r'<>#%"{}|\^[]`')
        should_quote.append(chr(127)) # For 0x7F
        should_quote = ''.join(should_quote)
        for char in should_quote:
            result = urllib.parse.quote(char)
            self.assertEqual(hexescape(char), result,
                             "using quote(): "
                             "%s should be escaped to %s, not %s" %
                             (char, hexescape(char), result))
            result = urllib.parse.quote_plus(char)
            self.assertEqual(hexescape(char), result,
                             "using quote_plus(): "
                             "%s should be escapes to %s, not %s" %
                             (char, hexescape(char), result))
        del should_quote
        partial_quote = "ab[]cd"
        expected = "ab%5B%5Dcd"
        result = urllib.parse.quote(partial_quote)
        self.assertEqual(expected, result,
                         "using quote(): %r != %r" % (expected, result))
        result = urllib.parse.quote_plus(partial_quote)
        self.assertEqual(expected, result,
                         "using quote_plus(): %r != %r" % (expected, result))

    def test_quoting_space(self):
        # Make sure quote() and quote_plus() handle spaces as specified in
        # their unique way
        result = urllib.parse.quote(' ')
        self.assertEqual(result, hexescape(' '),
                         "using quote(): %r != %r" % (result, hexescape(' ')))
        result = urllib.parse.quote_plus(' ')
        self.assertEqual(result, '+',
                         "using quote_plus(): %r != +" % result)
        given = "a b cd e f"
        expect = given.replace(' ', hexescape(' '))
        result = urllib.parse.quote(given)
        self.assertEqual(expect, result,
                         "using quote(): %r != %r" % (expect, result))
        expect = given.replace(' ', '+')
        result = urllib.parse.quote_plus(given)
        self.assertEqual(expect, result,
                         "using quote_plus(): %r != %r" % (expect, result))

    def test_quoting_plus(self):
        self.assertEqual(urllib.parse.quote_plus('alpha+beta gamma'),
                         'alpha%2Bbeta+gamma')
        self.assertEqual(urllib.parse.quote_plus('alpha+beta gamma', '+'),
                         'alpha+beta+gamma')
        # Test with bytes
        self.assertEqual(urllib.parse.quote_plus(b'alpha+beta gamma'),
                         'alpha%2Bbeta+gamma')
        # Test with safe bytes
        self.assertEqual(urllib.parse.quote_plus('alpha+beta gamma', b'+'),
                         'alpha+beta+gamma')

    def test_quote_bytes(self):
        # Bytes should quote directly to percent-encoded values
        given = b"\xa2\xd8ab\xff"
        expect = "%A2%D8ab%FF"
        result = urllib.parse.quote(given)
        self.assertEqual(expect, result,
                         "using quote(): %r != %r" % (expect, result))
        # Encoding argument should raise type error on bytes input
        self.assertRaises(TypeError, urllib.parse.quote, given,
                            encoding="latin-1")
        # quote_from_bytes should work the same
        result = urllib.parse.quote_from_bytes(given)
        self.assertEqual(expect, result,
                         "using quote_from_bytes(): %r != %r"
                         % (expect, result))

    def test_quote_with_unicode(self):
        # Characters in Latin-1 range, encoded by default in UTF-8
        given = "\xa2\xd8ab\xff"
        expect = "%C2%A2%C3%98ab%C3%BF"
        result = urllib.parse.quote(given)
        self.assertEqual(expect, result,
                         "using quote(): %r != %r" % (expect, result))
        # Characters in Latin-1 range, encoded by with None (default)
        result = urllib.parse.quote(given, encoding=None, errors=None)
        self.assertEqual(expect, result,
                         "using quote(): %r != %r" % (expect, result))
        # Characters in Latin-1 range, encoded with Latin-1
        given = "\xa2\xd8ab\xff"
        expect = "%A2%D8ab%FF"
        result = urllib.parse.quote(given, encoding="latin-1")
        self.assertEqual(expect, result,
                         "using quote(): %r != %r" % (expect, result))
        # Characters in BMP, encoded by default in UTF-8
        given = "\u6f22\u5b57"              # "Kanji"
        expect = "%E6%BC%A2%E5%AD%97"
        result = urllib.parse.quote(given)
        self.assertEqual(expect, result,
                         "using quote(): %r != %r" % (expect, result))
        # Characters in BMP, encoded with Latin-1
        given = "\u6f22\u5b57"
        self.assertRaises(UnicodeEncodeError, urllib.parse.quote, given,
                                    encoding="latin-1")
        # Characters in BMP, encoded with Latin-1, with replace error handling
        given = "\u6f22\u5b57"
        expect = "%3F%3F"                   # "??"
        result = urllib.parse.quote(given, encoding="latin-1",
                                    errors="replace")
        self.assertEqual(expect, result,
                         "using quote(): %r != %r" % (expect, result))
        # Characters in BMP, Latin-1, with xmlcharref error handling
        given = "\u6f22\u5b57"
        expect = "%26%2328450%3B%26%2323383%3B"     # "&#28450;&#23383;"
        result = urllib.parse.quote(given, encoding="latin-1",
                                    errors="xmlcharrefreplace")
        self.assertEqual(expect, result,
                         "using quote(): %r != %r" % (expect, result))

    def test_quote_plus_with_unicode(self):
        # Encoding (latin-1) test for quote_plus
        given = "\xa2\xd8 \xff"
        expect = "%A2%D8+%FF"
        result = urllib.parse.quote_plus(given, encoding="latin-1")
        self.assertEqual(expect, result,
                         "using quote_plus(): %r != %r" % (expect, result))
        # Errors test for quote_plus
        given = "ab\u6f22\u5b57 cd"
        expect = "ab%3F%3F+cd"
        result = urllib.parse.quote_plus(given, encoding="latin-1",
                                         errors="replace")
        self.assertEqual(expect, result,
                         "using quote_plus(): %r != %r" % (expect, result))


class UnquotingTests(unittest.TestCase):
    """Tests for unquote() and unquote_plus()

    See the doc string for quoting_Tests for details on quoting and such.

    """

    def test_unquoting(self):
        # Make sure unquoting of all ASCII values works
        escape_list = []
        for num in range(128):
            given = hexescape(chr(num))
            expect = chr(num)
            result = urllib.parse.unquote(given)
            self.assertEqual(expect, result,
                             "using unquote(): %r != %r" % (expect, result))
            result = urllib.parse.unquote_plus(given)
            self.assertEqual(expect, result,
                             "using unquote_plus(): %r != %r" %
                             (expect, result))
            escape_list.append(given)
        escape_string = ''.join(escape_list)
        del escape_list
        result = urllib.parse.unquote(escape_string)
        self.assertEqual(result.count('%'), 1,
                         "using unquote(): not all characters escaped: "
                         "%s" % result)
        self.assertRaises((TypeError, AttributeError), urllib.parse.unquote, None)
        self.assertRaises((TypeError, AttributeError), urllib.parse.unquote, ())

    def test_unquoting_badpercent(self):
        # Test unquoting on bad percent-escapes
        given = '%xab'
        expect = given
        result = urllib.parse.unquote(given)
        self.assertEqual(expect, result, "using unquote(): %r != %r"
                         % (expect, result))
        given = '%x'
        expect = given
        result = urllib.parse.unquote(given)
        self.assertEqual(expect, result, "using unquote(): %r != %r"
                         % (expect, result))
        given = '%'
        expect = given
        result = urllib.parse.unquote(given)
        self.assertEqual(expect, result, "using unquote(): %r != %r"
                         % (expect, result))
        # unquote_to_bytes
        given = '%xab'
        expect = given.encode('ascii')
        result = urllib.parse.unquote_to_bytes(given)
        self.assertEqual(expect, result, "using unquote_to_bytes(): %r != %r"
                         % (expect, result))
        given = '%x'
        expect = given.encode('ascii')
        result = urllib.parse.unquote_to_bytes(given)
        self.assertEqual(expect, result, "using unquote_to_bytes(): %r != %r"
                         % (expect, result))
        given = '%'
        expect = given.encode('ascii')
        result = urllib.parse.unquote_to_bytes(given)
        self.assertEqual(expect, result, "using unquote_to_bytes(): %r != %r"
                         % (expect, result))
        self.assertRaises((TypeError, AttributeError), urllib.parse.unquote_to_bytes, None)
        self.assertRaises((TypeError, AttributeError), urllib.parse.unquote_to_bytes, ())

    def test_unquoting_mixed_case(self):
        # Test unquoting on mixed-case hex digits in the percent-escapes
        given = '%Ab%eA'
        expect = b'\xab\xea'
        result = urllib.parse.unquote_to_bytes(given)
        self.assertEqual(expect, result,
                         "using unquote_to_bytes(): %r != %r"
                         % (expect, result))

    def test_unquoting_parts(self):
        # Make sure unquoting works when have non-quoted characters
        # interspersed
        given = 'ab%sd' % hexescape('c')
        expect = "abcd"
        result = urllib.parse.unquote(given)
        self.assertEqual(expect, result,
                         "using quote(): %r != %r" % (expect, result))
        result = urllib.parse.unquote_plus(given)
        self.assertEqual(expect, result,
                         "using unquote_plus(): %r != %r" % (expect, result))

    def test_unquoting_plus(self):
        # Test difference between unquote() and unquote_plus()
        given = "are+there+spaces..."
        expect = given
        result = urllib.parse.unquote(given)
        self.assertEqual(expect, result,
                         "using unquote(): %r != %r" % (expect, result))
        expect = given.replace('+', ' ')
        result = urllib.parse.unquote_plus(given)
        self.assertEqual(expect, result,
                         "using unquote_plus(): %r != %r" % (expect, result))

    def test_unquote_to_bytes(self):
        given = 'br%C3%BCckner_sapporo_20050930.doc'
        expect = b'br\xc3\xbcckner_sapporo_20050930.doc'
        result = urllib.parse.unquote_to_bytes(given)
        self.assertEqual(expect, result,
                         "using unquote_to_bytes(): %r != %r"
                         % (expect, result))
        # Test on a string with unescaped non-ASCII characters
        # (Technically an invalid URI; expect those characters to be UTF-8
        # encoded).
        result = urllib.parse.unquote_to_bytes("\u6f22%C3%BC")
        expect = b'\xe6\xbc\xa2\xc3\xbc'    # UTF-8 for "\u6f22\u00fc"
        self.assertEqual(expect, result,
                         "using unquote_to_bytes(): %r != %r"
                         % (expect, result))
        # Test with a bytes as input
        given = b'%A2%D8ab%FF'
        expect = b'\xa2\xd8ab\xff'
        result = urllib.parse.unquote_to_bytes(given)
        self.assertEqual(expect, result,
                         "using unquote_to_bytes(): %r != %r"
                         % (expect, result))
        # Test with a bytes as input, with unescaped non-ASCII bytes
        # (Technically an invalid URI; expect those bytes to be preserved)
        given = b'%A2\xd8ab%FF'
        expect = b'\xa2\xd8ab\xff'
        result = urllib.parse.unquote_to_bytes(given)
        self.assertEqual(expect, result,
                         "using unquote_to_bytes(): %r != %r"
                         % (expect, result))

    def test_unquote_with_unicode(self):
        # Characters in the Latin-1 range, encoded with UTF-8
        given = 'br%C3%BCckner_sapporo_20050930.doc'
        expect = 'br\u00fcckner_sapporo_20050930.doc'
        result = urllib.parse.unquote(given)
        self.assertEqual(expect, result,
                         "using unquote(): %r != %r" % (expect, result))
        # Characters in the Latin-1 range, encoded with None (default)
        result = urllib.parse.unquote(given, encoding=None, errors=None)
        self.assertEqual(expect, result,
                         "using unquote(): %r != %r" % (expect, result))

        # Characters in the Latin-1 range, encoded with Latin-1
        result = urllib.parse.unquote('br%FCckner_sapporo_20050930.doc',
                                      encoding="latin-1")
        expect = 'br\u00fcckner_sapporo_20050930.doc'
        self.assertEqual(expect, result,
                         "using unquote(): %r != %r" % (expect, result))

        # Characters in BMP, encoded with UTF-8
        given = "%E6%BC%A2%E5%AD%97"
        expect = "\u6f22\u5b57"             # "Kanji"
        result = urllib.parse.unquote(given)
        self.assertEqual(expect, result,
                         "using unquote(): %r != %r" % (expect, result))

        # Decode with UTF-8, invalid sequence
        given = "%F3%B1"
        expect = "\ufffd"                   # Replacement character
        result = urllib.parse.unquote(given)
        self.assertEqual(expect, result,
                         "using unquote(): %r != %r" % (expect, result))

        # Decode with UTF-8, invalid sequence, replace errors
        result = urllib.parse.unquote(given, errors="replace")
        self.assertEqual(expect, result,
                         "using unquote(): %r != %r" % (expect, result))

        # Decode with UTF-8, invalid sequence, ignoring errors
        given = "%F3%B1"
        expect = ""
        result = urllib.parse.unquote(given, errors="ignore")
        self.assertEqual(expect, result,
                         "using unquote(): %r != %r" % (expect, result))

        # A mix of non-ASCII and percent-encoded characters, UTF-8
        result = urllib.parse.unquote("\u6f22%C3%BC")
        expect = '\u6f22\u00fc'
        self.assertEqual(expect, result,
                         "using unquote(): %r != %r" % (expect, result))

        # A mix of non-ASCII and percent-encoded characters, Latin-1
        # (Note, the string contains non-Latin-1-representable characters)
        result = urllib.parse.unquote("\u6f22%FC", encoding="latin-1")
        expect = '\u6f22\u00fc'
        self.assertEqual(expect, result,
                         "using unquote(): %r != %r" % (expect, result))

    def test_unquoting_with_bytes_input(self):
        # ASCII characters decoded to a string
        given = b'blueberryjam'
        expect = 'blueberryjam'
        result = urllib.parse.unquote(given)
        self.assertEqual(expect, result,
                         "using unquote(): %r != %r" % (expect, result))

        # A mix of non-ASCII hex-encoded characters and ASCII characters
        given = b'bl\xc3\xa5b\xc3\xa6rsyltet\xc3\xb8y'
        expect = 'bl\u00e5b\u00e6rsyltet\u00f8y'
        result = urllib.parse.unquote(given)
        self.assertEqual(expect, result,
                         "using unquote(): %r != %r" % (expect, result))

        # A mix of non-ASCII percent-encoded characters and ASCII characters
        given = b'bl%c3%a5b%c3%a6rsyltet%c3%b8j'
        expect = 'bl\u00e5b\u00e6rsyltet\u00f8j'
        result = urllib.parse.unquote(given)
        self.assertEqual(expect, result,
                         "using unquote(): %r != %r" % (expect, result))


if __name__ == '__main__':
    unittest.main()
