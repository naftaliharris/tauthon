import sys
import os
from StringIO import StringIO
import textwrap

from distutils.core import Extension, Distribution
from distutils.command.build_ext import build_ext
from distutils import sysconfig
from distutils.tests import support
from distutils.errors import (DistutilsSetupError, CompileError,
                              DistutilsPlatformError)

import unittest
from test import test_support

# http://bugs.python.org/issue4373
# Don't load the xx module more than once.
ALREADY_TESTED = False


class BuildExtTestCase(support.TempdirManager,
                       support.LoggingSilencer,
                       support.EnvironGuard,
                       unittest.TestCase):
    def setUp(self):
        super(BuildExtTestCase, self).setUp()
        self.tmp_dir = self.mkdtemp()
        self.xx_created = False
        sys.path.append(self.tmp_dir)
        self.addCleanup(sys.path.remove, self.tmp_dir)
        if sys.version > "2.6":
            import site
            self.old_user_base = site.USER_BASE
            site.USER_BASE = self.mkdtemp()
            from distutils.command import build_ext
            build_ext.USER_BASE = site.USER_BASE

    def tearDown(self):
        if self.xx_created:
            test_support.unload('xx')
            # XXX on Windows the test leaves a directory
            # with xx module in TEMP
        super(BuildExtTestCase, self).tearDown()

    def test_build_ext(self):
        global ALREADY_TESTED
        support.copy_xxmodule_c(self.tmp_dir)
        self.xx_created = True
        xx_c = os.path.join(self.tmp_dir, 'xxmodule.c')
        xx_ext = Extension('xx', [xx_c])
        dist = Distribution({'name': 'xx', 'ext_modules': [xx_ext]})
        dist.package_dir = self.tmp_dir
        cmd = build_ext(dist)
        support.fixup_build_ext(cmd)
        cmd.build_lib = self.tmp_dir
        cmd.build_temp = self.tmp_dir

        old_stdout = sys.stdout
        if not test_support.verbose:
            # silence compiler output
            sys.stdout = StringIO()
        try:
            cmd.ensure_finalized()
            cmd.run()
        finally:
            sys.stdout = old_stdout

        if ALREADY_TESTED:
            self.skipTest('Already tested in %s' % ALREADY_TESTED)
        else:
            ALREADY_TESTED = type(self).__name__

        import xx

        for attr in ('error', 'foo', 'new', 'roj'):
            self.assertTrue(hasattr(xx, attr))

        self.assertEqual(xx.foo(2, 5), 7)
        self.assertEqual(xx.foo(13,15), 28)
        self.assertEqual(xx.new().demo(), None)
        if test_support.HAVE_DOCSTRINGS:
            doc = 'This is a template module just for instruction.'
            self.assertEqual(xx.__doc__, doc)
        self.assertIsInstance(xx.Null(), xx.Null)
        self.assertIsInstance(xx.Str(), xx.Str)

    def test_solaris_enable_shared(self):
        dist = Distribution({'name': 'xx'})
        cmd = build_ext(dist)
        old = sys.platform

        sys.platform = 'sunos' # fooling finalize_options
        from distutils.sysconfig import  _config_vars
        old_var = _config_vars.get('Py_ENABLE_SHARED')
        _config_vars['Py_ENABLE_SHARED'] = 1
        try:
            cmd.ensure_finalized()
        finally:
            sys.platform = old
            if old_var is None:
                del _config_vars['Py_ENABLE_SHARED']
            else:
                _config_vars['Py_ENABLE_SHARED'] = old_var

        # make sure we get some library dirs under solaris
        self.assertGreater(len(cmd.library_dirs), 0)

    @unittest.skipIf(sys.version < '2.6',
                     'site.USER_SITE was introduced in 2.6')
    def test_user_site(self):
        import site
        dist = Distribution({'name': 'xx'})
        cmd = build_ext(dist)

        # making sure the user option is there
        options = [name for name, short, label in
                   cmd.user_options]
        self.assertIn('user', options)

        # setting a value
        cmd.user = 1

        # setting user based lib and include
        lib = os.path.join(site.USER_BASE, 'lib')
        incl = os.path.join(site.USER_BASE, 'include')
        os.mkdir(lib)
        os.mkdir(incl)

        cmd.ensure_finalized()

        # see if include_dirs and library_dirs were set
        self.assertIn(lib, cmd.library_dirs)
        self.assertIn(lib, cmd.rpath)
        self.assertIn(incl, cmd.include_dirs)

    def test_finalize_options(self):
        # Make sure Python's include directories (for Python.h, pyconfig.h,
        # etc.) are in the include search path.
        modules = [Extension('foo', ['xxx'])]
        dist = Distribution({'name': 'xx', 'ext_modules': modules})
        cmd = build_ext(dist)
        cmd.finalize_options()

        py_include = sysconfig.get_python_inc()
        self.assertIn(py_include, cmd.include_dirs)

        plat_py_include = sysconfig.get_python_inc(plat_specific=1)
        self.assertIn(plat_py_include, cmd.include_dirs)

        # make sure cmd.libraries is turned into a list
        # if it's a string
        cmd = build_ext(dist)
        cmd.libraries = 'my_lib, other_lib lastlib'
        cmd.finalize_options()
        self.assertEqual(cmd.libraries, ['my_lib', 'other_lib', 'lastlib'])

        # make sure cmd.library_dirs is turned into a list
        # if it's a string
        cmd = build_ext(dist)
        cmd.library_dirs = 'my_lib_dir%sother_lib_dir' % os.pathsep
        cmd.finalize_options()
        self.assertIn('my_lib_dir', cmd.library_dirs)
        self.assertIn('other_lib_dir', cmd.library_dirs)

        # make sure rpath is turned into a list
        # if it's a string
        cmd = build_ext(dist)
        cmd.rpath = 'one%stwo' % os.pathsep
        cmd.finalize_options()
        self.assertEqual(cmd.rpath, ['one', 'two'])

        # make sure cmd.link_objects is turned into a list
        # if it's a string
        cmd = build_ext(dist)
        cmd.link_objects = 'one two,three'
        cmd.finalize_options()
        self.assertEqual(cmd.link_objects, ['one', 'two', 'three'])

        # XXX more tests to perform for win32

        # make sure define is turned into 2-tuples
        # strings if they are ','-separated strings
        cmd = build_ext(dist)
        cmd.define = 'one,two'
        cmd.finalize_options()
        self.assertEqual(cmd.define, [('one', '1'), ('two', '1')])

        # make sure undef is turned into a list of
        # strings if they are ','-separated strings
        cmd = build_ext(dist)
        cmd.undef = 'one,two'
        cmd.finalize_options()
        self.assertEqual(cmd.undef, ['one', 'two'])

        # make sure swig_opts is turned into a list
        cmd = build_ext(dist)
        cmd.swig_opts = None
        cmd.finalize_options()
        self.assertEqual(cmd.swig_opts, [])

        cmd = build_ext(dist)
        cmd.swig_opts = '1 2'
        cmd.finalize_options()
        self.assertEqual(cmd.swig_opts, ['1', '2'])

    def test_check_extensions_list(self):
        dist = Distribution()
        cmd = build_ext(dist)
        cmd.finalize_options()

        #'extensions' option must be a list of Extension instances
        self.assertRaises(DistutilsSetupError, cmd.check_extensions_list, 'foo')

        # each element of 'ext_modules' option must be an
        # Extension instance or 2-tuple
        exts = [('bar', 'foo', 'bar'), 'foo']
        self.assertRaises(DistutilsSetupError, cmd.check_extensions_list, exts)

        # first element of each tuple in 'ext_modules'
        # must be the extension name (a string) and match
        # a python dotted-separated name
        exts = [('foo-bar', '')]
        self.assertRaises(DistutilsSetupError, cmd.check_extensions_list, exts)

        # second element of each tuple in 'ext_modules'
        # must be a dictionary (build info)
        exts = [('foo.bar', '')]
        self.assertRaises(DistutilsSetupError, cmd.check_extensions_list, exts)

        # ok this one should pass
        exts = [('foo.bar', {'sources': [''], 'libraries': 'foo',
                             'some': 'bar'})]
        cmd.check_extensions_list(exts)
        ext = exts[0]
        self.assertIsInstance(ext, Extension)

        # check_extensions_list adds in ext the values passed
        # when they are in ('include_dirs', 'library_dirs', 'libraries'
        # 'extra_objects', 'extra_compile_args', 'extra_link_args')
        self.assertEqual(ext.libraries, 'foo')
        self.assertFalse(hasattr(ext, 'some'))

        # 'macros' element of build info dict must be 1- or 2-tuple
        exts = [('foo.bar', {'sources': [''], 'libraries': 'foo',
                'some': 'bar', 'macros': [('1', '2', '3'), 'foo']})]
        self.assertRaises(DistutilsSetupError, cmd.check_extensions_list, exts)

        exts[0][1]['macros'] = [('1', '2'), ('3',)]
        cmd.check_extensions_list(exts)
        self.assertEqual(exts[0].undef_macros, ['3'])
        self.assertEqual(exts[0].define_macros, [('1', '2')])

    def test_get_source_files(self):
        modules = [Extension('foo', ['xxx'])]
        dist = Distribution({'name': 'xx', 'ext_modules': modules})
        cmd = build_ext(dist)
        cmd.ensure_finalized()
        self.assertEqual(cmd.get_source_files(), ['xxx'])

    def test_compiler_option(self):
        # cmd.compiler is an option and
        # should not be overridden by a compiler instance
        # when the command is run
        dist = Distribution()
        cmd = build_ext(dist)
        cmd.compiler = 'unix'
        cmd.ensure_finalized()
        cmd.run()
        self.assertEqual(cmd.compiler, 'unix')

    def test_get_outputs(self):
        tmp_dir = self.mkdtemp()
        c_file = os.path.join(tmp_dir, 'foo.c')
        self.write_file(c_file, 'void initfoo(void) {};\n')
        ext = Extension('foo', [c_file])
        dist = Distribution({'name': 'xx',
                             'ext_modules': [ext]})
        cmd = build_ext(dist)
        support.fixup_build_ext(cmd)
        cmd.ensure_finalized()
        self.assertEqual(len(cmd.get_outputs()), 1)

        cmd.build_lib = os.path.join(self.tmp_dir, 'build')
        cmd.build_temp = os.path.join(self.tmp_dir, 'tempt')

        # issue #5977 : distutils build_ext.get_outputs
        # returns wrong result with --inplace
        other_tmp_dir = os.path.realpath(self.mkdtemp())
        old_wd = os.getcwd()
        os.chdir(other_tmp_dir)
        try:
            cmd.inplace = 1
            cmd.run()
            so_file = cmd.get_outputs()[0]
        finally:
            os.chdir(old_wd)
        self.assertTrue(os.path.exists(so_file))
        self.assertEqual(os.path.splitext(so_file)[-1],
                         sysconfig.get_config_var('SO'))
        so_dir = os.path.dirname(so_file)
        self.assertEqual(so_dir, other_tmp_dir)
        cmd.compiler = None
        cmd.inplace = 0
        cmd.run()
        so_file = cmd.get_outputs()[0]
        self.assertTrue(os.path.exists(so_file))
        self.assertEqual(os.path.splitext(so_file)[-1],
                         sysconfig.get_config_var('SO'))
        so_dir = os.path.dirname(so_file)
        self.assertEqual(so_dir, cmd.build_lib)

        # inplace = 0, cmd.package = 'bar'
        build_py = cmd.get_finalized_command('build_py')
        build_py.package_dir = {'': 'bar'}
        path = cmd.get_ext_fullpath('foo')
        # checking that the last directory is the build_dir
        path = os.path.split(path)[0]
        self.assertEqual(path, cmd.build_lib)

        # inplace = 1, cmd.package = 'bar'
        cmd.inplace = 1
        other_tmp_dir = os.path.realpath(self.mkdtemp())
        old_wd = os.getcwd()
        os.chdir(other_tmp_dir)
        try:
            path = cmd.get_ext_fullpath('foo')
        finally:
            os.chdir(old_wd)
        # checking that the last directory is bar
        path = os.path.split(path)[0]
        lastdir = os.path.split(path)[-1]
        self.assertEqual(lastdir, 'bar')

    def test_ext_fullpath(self):
        ext = sysconfig.get_config_vars()['SO']
        dist = Distribution()
        cmd = build_ext(dist)
        cmd.inplace = 1
        cmd.distribution.package_dir = {'': 'src'}
        cmd.distribution.packages = ['lxml', 'lxml.html']
        curdir = os.getcwd()
        wanted = os.path.join(curdir, 'src', 'lxml', 'etree' + ext)
        path = cmd.get_ext_fullpath('lxml.etree')
        self.assertEqual(wanted, path)

        # building lxml.etree not inplace
        cmd.inplace = 0
        cmd.build_lib = os.path.join(curdir, 'tmpdir')
        wanted = os.path.join(curdir, 'tmpdir', 'lxml', 'etree' + ext)
        path = cmd.get_ext_fullpath('lxml.etree')
        self.assertEqual(wanted, path)

        # building twisted.runner.portmap not inplace
        build_py = cmd.get_finalized_command('build_py')
        build_py.package_dir = {}
        cmd.distribution.packages = ['twisted', 'twisted.runner.portmap']
        path = cmd.get_ext_fullpath('twisted.runner.portmap')
        wanted = os.path.join(curdir, 'tmpdir', 'twisted', 'runner',
                              'portmap' + ext)
        self.assertEqual(wanted, path)

        # building twisted.runner.portmap inplace
        cmd.inplace = 1
        path = cmd.get_ext_fullpath('twisted.runner.portmap')
        wanted = os.path.join(curdir, 'twisted', 'runner', 'portmap' + ext)
        self.assertEqual(wanted, path)

    def test_build_ext_inplace(self):
        etree_c = os.path.join(self.tmp_dir, 'lxml.etree.c')
        etree_ext = Extension('lxml.etree', [etree_c])
        dist = Distribution({'name': 'lxml', 'ext_modules': [etree_ext]})
        cmd = build_ext(dist)
        cmd.ensure_finalized()
        cmd.inplace = 1
        cmd.distribution.package_dir = {'': 'src'}
        cmd.distribution.packages = ['lxml', 'lxml.html']
        curdir = os.getcwd()
        ext = sysconfig.get_config_var("SO")
        wanted = os.path.join(curdir, 'src', 'lxml', 'etree' + ext)
        path = cmd.get_ext_fullpath('lxml.etree')
        self.assertEqual(wanted, path)

    def test_setuptools_compat(self):
        import distutils.core, distutils.extension, distutils.command.build_ext
        saved_ext = distutils.extension.Extension
        try:
            # on some platforms, it loads the deprecated "dl" module
            test_support.import_module('setuptools_build_ext', deprecated=True)

            # theses import patch Distutils' Extension class
            from setuptools_build_ext import build_ext as setuptools_build_ext
            from setuptools_extension import Extension

            etree_c = os.path.join(self.tmp_dir, 'lxml.etree.c')
            etree_ext = Extension('lxml.etree', [etree_c])
            dist = Distribution({'name': 'lxml', 'ext_modules': [etree_ext]})
            cmd = setuptools_build_ext(dist)
            cmd.ensure_finalized()
            cmd.inplace = 1
            cmd.distribution.package_dir = {'': 'src'}
            cmd.distribution.packages = ['lxml', 'lxml.html']
            curdir = os.getcwd()
            ext = sysconfig.get_config_var("SO")
            wanted = os.path.join(curdir, 'src', 'lxml', 'etree' + ext)
            path = cmd.get_ext_fullpath('lxml.etree')
            self.assertEqual(wanted, path)
        finally:
            # restoring Distutils' Extension class otherwise its broken
            distutils.extension.Extension = saved_ext
            distutils.core.Extension = saved_ext
            distutils.command.build_ext.Extension = saved_ext

    def test_build_ext_path_with_os_sep(self):
        dist = Distribution({'name': 'UpdateManager'})
        cmd = build_ext(dist)
        cmd.ensure_finalized()
        ext = sysconfig.get_config_var("SO")
        ext_name = os.path.join('UpdateManager', 'fdsend')
        ext_path = cmd.get_ext_fullpath(ext_name)
        wanted = os.path.join(cmd.build_lib, 'UpdateManager', 'fdsend' + ext)
        self.assertEqual(ext_path, wanted)

    @unittest.skipUnless(sys.platform == 'win32', 'these tests require Windows')
    def test_build_ext_path_cross_platform(self):
        dist = Distribution({'name': 'UpdateManager'})
        cmd = build_ext(dist)
        cmd.ensure_finalized()
        ext = sysconfig.get_config_var("SO")
        # this needs to work even under win32
        ext_name = 'UpdateManager/fdsend'
        ext_path = cmd.get_ext_fullpath(ext_name)
        wanted = os.path.join(cmd.build_lib, 'UpdateManager', 'fdsend' + ext)
        self.assertEqual(ext_path, wanted)

    @unittest.skipUnless(sys.platform == 'darwin', 'test only relevant for MacOSX')
    def test_deployment_target_default(self):
        # Issue 9516: Test that, in the absence of the environment variable,
        # an extension module is compiled with the same deployment target as
        #  the interpreter.
        self._try_compile_deployment_target('==', None)

    @unittest.skipUnless(sys.platform == 'darwin', 'test only relevant for MacOSX')
    def test_deployment_target_too_low(self):
        # Issue 9516: Test that an extension module is not allowed to be
        # compiled with a deployment target less than that of the interpreter.
        self.assertRaises(DistutilsPlatformError,
            self._try_compile_deployment_target, '>', '10.1')

    @unittest.skipUnless(sys.platform == 'darwin', 'test only relevant for MacOSX')
    def test_deployment_target_higher_ok(self):
        # Issue 9516: Test that an extension module can be compiled with a
        # deployment target higher than that of the interpreter: the ext
        # module may depend on some newer OS feature.
        deptarget = sysconfig.get_config_var('MACOSX_DEPLOYMENT_TARGET')
        if deptarget:
            # increment the minor version number (i.e. 10.6 -> 10.7)
            deptarget = [int(x) for x in deptarget.split('.')]
            deptarget[-1] += 1
            deptarget = '.'.join(str(i) for i in deptarget)
            self._try_compile_deployment_target('<', deptarget)

    def _try_compile_deployment_target(self, operator, target):
        orig_environ = os.environ
        os.environ = orig_environ.copy()
        self.addCleanup(setattr, os, 'environ', orig_environ)

        if target is None:
            if os.environ.get('MACOSX_DEPLOYMENT_TARGET'):
                del os.environ['MACOSX_DEPLOYMENT_TARGET']
        else:
            os.environ['MACOSX_DEPLOYMENT_TARGET'] = target

        deptarget_c = os.path.join(self.tmp_dir, 'deptargetmodule.c')

        with open(deptarget_c, 'w') as fp:
            fp.write(textwrap.dedent('''\
                #include <AvailabilityMacros.h>

                int dummy;

                #if TARGET %s MAC_OS_X_VERSION_MIN_REQUIRED
                #else
                #error "Unexpected target"
                #endif

            ''' % operator))

        # get the deployment target that the interpreter was built with
        target = sysconfig.get_config_var('MACOSX_DEPLOYMENT_TARGET')
        target = tuple(map(int, target.split('.')[0:2]))
        # format the target value as defined in the Apple
        # Availability Macros.  We can't use the macro names since
        # at least one value we test with will not exist yet.
        if target[:2] < (10, 10):
            # for 10.1 through 10.9.x -> "10n0"
            target = '%02d%01d0' % target
        else:
            # for 10.10 and beyond -> "10nn00"
            target = '%02d%02d00' % target
        deptarget_ext = Extension(
            'deptarget',
            [deptarget_c],
            extra_compile_args=['-DTARGET=%s'%(target,)],
        )
        dist = Distribution({
            'name': 'deptarget',
            'ext_modules': [deptarget_ext]
        })
        dist.package_dir = self.tmp_dir
        cmd = build_ext(dist)
        cmd.build_lib = self.tmp_dir
        cmd.build_temp = self.tmp_dir

        try:
            cmd.ensure_finalized()
            cmd.run()
        except CompileError:
            self.fail("Wrong deployment target during compilation")

def test_suite():
    return unittest.makeSuite(BuildExtTestCase)

if __name__ == '__main__':
    test_support.run_unittest(test_suite())
