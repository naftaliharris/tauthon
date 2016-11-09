import unittest
import select
import signal
import sys
import os
from test.test_support import run_unittest


class OldStyleException:
    pass


class OSErrorTest(unittest.TestCase):
    def assertIsSubclass(self, cl1, cl2):
        self.assertTrue(issubclass(cl1, cl2),
                        "%r is not a subclass of %r" % (cl1, cl2))

    def assertNotIsSubclass(self, cl1, cl2):
        self.assertFalse(issubclass(cl1, cl2),
                         "%r is a subclass of %r" % (cl1, cl2))

    def test_subclass(self):
        # Explicit inheritance
        self.assertIsSubclass(BlockingIOError, object)
        self.assertIsSubclass(BlockingIOError, BaseException)
        self.assertIsSubclass(BlockingIOError, Exception)
        self.assertIsSubclass(BlockingIOError, EnvironmentError)
        self.assertIsSubclass(BlockingIOError, OSError)
        self.assertIsSubclass(BlockingIOError, BlockingIOError)
        self.assertNotIsSubclass(BlockingIOError, int)
        self.assertNotIsSubclass(BlockingIOError, str)

        self.assertNotIsSubclass(object, BlockingIOError)
        self.assertNotIsSubclass(BaseException, BlockingIOError)
        self.assertNotIsSubclass(Exception, BlockingIOError)
        self.assertNotIsSubclass(EnvironmentError, BlockingIOError)
        self.assertNotIsSubclass(OSError, BlockingIOError)
        self.assertNotIsSubclass(int, BlockingIOError)
        self.assertNotIsSubclass(str, BlockingIOError)

        # Subclasses of ConnectionError
        self.assertIsSubclass(ConnectionError, OSError)
        self.assertIsSubclass(BrokenPipeError, ConnectionError)
        self.assertIsSubclass(ConnectionAbortedError, ConnectionError)
        self.assertIsSubclass(ConnectionRefusedError, ConnectionError)
        self.assertIsSubclass(ConnectionResetError, ConnectionError)

    def test_catch(self):
        with self.assertRaises(FileNotFoundError):
            open("this file does not exist")

        try:
            open("this file does not exist")
        except FileNotFoundError:
            pass
        else:
            self.fail("FileNotFoundError didn't catch this")

        try:
            1/0
        except FileNotFoundError:
            self.fail("FileNotFoundError shouldn't have caught this")
        except ZeroDivisionError:
            pass

    def test_catch_multiple(self):
        try:
            open("this file does not exist")
        except ZeroDivisionError:
            self.fail("what?!")
        except ChildProcessError:
            self.fail("ChildProcessError shouldn't have caught this")
        except FileNotFoundError:
            pass
        else:
            self.fail("FileNotFoundError didn't catch this")

    def test_catch_nested(self):
        try:
            1/0
        except ZeroDivisionError:
            try:
                open("this file does not exist")
            except ZeroDivisionError:
                self.fail("what?!")
            except FileNotFoundError:
                pass
            else:
                self.fail("FileNotFoundError didn't catch this")
        else:
            self.fail("what?!")

    def test_old_style(self):
        try:
            raise OldStyleException()
        except FileNotFoundError:
            self.fail("FileNotFoundError shouldn't have caught this")
        except:
            pass

    def test_catch_self(self):
        with self.assertRaises(FileNotFoundError):
            raise FileNotFoundError()

        with self.assertRaises(OSError):
            raise FileNotFoundError()

    @unittest.skipIf(sys.platform == "win32", "No signal.alarm() Windows")
    def test_select(self):
        signal.signal(signal.SIGALRM, lambda x, y: None)
        read, _ = os.pipe()
        signal.alarm(1)
        with self.assertRaises(InterruptedError):
            select.select([read], [], [], 5)


def test_main():
    run_unittest(OSErrorTest)

if __name__ == "__main__":
    test_main()
