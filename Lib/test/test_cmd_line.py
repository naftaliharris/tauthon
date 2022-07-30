# Tests invocation of the interpreter with various command line arguments
# All tests are executed with environment variables ignored
# See test_cmd_line_script.py for testing of script execution

import test.test_support
import sys
import unittest
from test.script_helper import (
    assert_python_ok, assert_python_failure, spawn_python, kill_python
)


class CmdLineTest(unittest.TestCase):
    def start_python(self, *args):
        p = spawn_python(*args)
        return kill_python(p)

    def test_directories(self):
        assert_python_failure('.')
        assert_python_failure('< .')

    def verify_valid_flag(self, cmd_line):
        data = self.start_python(cmd_line)
        self.assertTrue(data == '' or data.endswith('\n'))
        self.assertNotIn('Traceback', data)

    def test_optimize(self):
        self.verify_valid_flag('-O')
        self.verify_valid_flag('-OO')

    def test_q(self):
        self.verify_valid_flag('-Qold')
        self.verify_valid_flag('-Qnew')
        self.verify_valid_flag('-Qwarn')
        self.verify_valid_flag('-Qwarnall')

    def test_site_flag(self):
        self.verify_valid_flag('-S')

    def test_usage(self):
        self.assertIn('usage', self.start_python('-h'))

    def test_version(self):
        version = 'Python %d.%d' % sys.version_info[:2]
        self.assertTrue(self.start_python('-V').startswith(version))

    def test_run_module(self):
        # Test expected operation of the '-m' switch
        # Switch needs an argument
        assert_python_failure('-m')
        # Check we get an error for a nonexistent module
        assert_python_failure('-m', 'fnord43520xyz')
        # Check the runpy module also gives an error for
        # a nonexistent module
        assert_python_failure('-m', 'runpy', 'fnord43520xyz')
        # All good if module is located and run successfully
        assert_python_ok('-m', 'timeit', '-n', '1')

    def test_run_module_bug1764407(self):
        # -m and -i need to play well together
        # Runs the timeit module and checks the __main__
        # namespace has been populated appropriately
        p = spawn_python('-i', '-m', 'timeit', '-n', '1')
        p.stdin.write('Timer\n')
        p.stdin.write('exit()\n')
        data = kill_python(p)
        self.assertTrue(data.startswith('1 loop'))
        self.assertIn('__main__.Timer', data)

    def test_run_code(self):
        # Test expected operation of the '-c' switch
        # Switch needs an argument
        assert_python_failure('-c')
        # Check we get an error for an uncaught exception
        assert_python_failure('-c', 'raise Exception')
        # All good if execution is successful
        assert_python_ok('-c', 'pass')

    def test_hash_randomization(self):
        # Verify that -R enables hash randomization:
        self.verify_valid_flag('-R')
        hashes = []
        for i in range(2):
            code = 'print(hash("spam"))'
            data = self.start_python('-R', '-c', code)
            hashes.append(data)
        self.assertNotEqual(hashes[0], hashes[1])

        # Verify that sys.flags contains hash_randomization
        code = 'import sys; print sys.flags'
        data = self.start_python('-R', '-c', code)
        self.assertTrue('hash_randomization=1' in data)

    def test_del___main__(self):
        # Issue #15001: PyRun_SimpleFileExFlags() did crash because it kept a
        # borrowed reference to the dict of __main__ module and later modify
        # the dict whereas the module was destroyed
        filename = test.test_support.TESTFN
        self.addCleanup(test.test_support.unlink, filename)
        with open(filename, "w") as script:
            print >>script, "import sys"
            print >>script, "del sys.modules['__main__']"
        assert_python_ok(filename)

    def test_unknown_options(self):
        rc, out, err = assert_python_failure('-E', '-z')
        self.assertIn(b'Unknown option: -z', err)
        self.assertEqual(err.splitlines().count(b'Unknown option: -z'), 1)
        self.assertEqual(b'', out)
        # Add "without='-E'" to prevent _assert_python to append -E
        # to env_vars and change the output of stderr
        rc, out, err = assert_python_failure('-z', without='-E')
        self.assertIn(b'Unknown option: -z', err)
        self.assertEqual(err.splitlines().count(b'Unknown option: -z'), 1)
        self.assertEqual(b'', out)
        rc, out, err = assert_python_failure('-a', '-z', without='-E')
        self.assertIn(b'Unknown option: -a', err)
        # only the first unknown option is reported
        self.assertNotIn(b'Unknown option: -z', err)
        self.assertEqual(err.splitlines().count(b'Unknown option: -a'), 1)
        self.assertEqual(b'', out)


def test_main():
    test.test_support.run_unittest(CmdLineTest)
    test.test_support.reap_children()

if __name__ == "__main__":
    test_main()
