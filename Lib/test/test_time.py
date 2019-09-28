from test import test_support
import time
import unittest
import sys
import sysconfig
import platform
import threading


# Max year is only limited by the size of C int.
SIZEOF_INT = sysconfig.get_config_var('SIZEOF_INT') or 4
TIME_MAXYEAR = (1 << 8 * SIZEOF_INT - 1) - 1

def busy_wait(duration):
    deadline = time.monotonic() + duration
    while time.monotonic() < deadline:
        pass
    return

class TimeTestCase(unittest.TestCase):

    def setUp(self):
        self.t = time.time()

    def test_data_attributes(self):
        time.altzone
        time.daylight
        time.timezone
        time.tzname

    def test_clock(self):
        time.clock()

    def test_time_ns_type(self):
        def check_ns(sec, ns):
            self.assertIsInstance(ns, long)

            sec_ns = int(sec * 1e9)
            # tolerate a difference of 50 ms
            self.assertLess((sec_ns - ns), 50 ** 6, (sec, ns))

        check_ns(time.time(),
                 time.time_ns())
        check_ns(time.monotonic(),
                 time.monotonic_ns())
        check_ns(time.perf_counter(),
                 time.perf_counter_ns())
        check_ns(time.process_time(),
                 time.process_time_ns())

        if hasattr(time, 'thread_time'):
            check_ns(time.thread_time(),
                     time.thread_time_ns())

        if hasattr(time, 'clock_gettime'):
            check_ns(time.clock_gettime(time.CLOCK_REALTIME),
                     time.clock_gettime_ns(time.CLOCK_REALTIME))

    @unittest.skipUnless(hasattr(time, 'clock_gettime'),
                         'need time.clock_gettime()')
    def test_clock_realtime(self):
        t = time.clock_gettime(time.CLOCK_REALTIME)
        self.assertIsInstance(t, float)

    @unittest.skipUnless(hasattr(time, 'clock_gettime'),
                         'need time.clock_gettime()')
    @unittest.skipUnless(hasattr(time, 'CLOCK_MONOTONIC'),
                         'need time.CLOCK_MONOTONIC')
    def test_clock_monotonic(self):
        a = time.clock_gettime(time.CLOCK_MONOTONIC)
        b = time.clock_gettime(time.CLOCK_MONOTONIC)
        self.assertLessEqual(a, b)

    @unittest.skipUnless(hasattr(time, 'pthread_getcpuclockid'),
                         'need time.pthread_getcpuclockid()')
    @unittest.skipUnless(hasattr(time, 'clock_gettime'),
                         'need time.clock_gettime()')
    def test_pthread_getcpuclockid(self):
        clk_id = time.pthread_getcpuclockid(threading.get_ident())
        self.assertTrue(type(clk_id) is int)
        self.assertNotEqual(clk_id, time.CLOCK_THREAD_CPUTIME_ID)
        t1 = time.clock_gettime(clk_id)
        t2 = time.clock_gettime(clk_id)
        self.assertLessEqual(t1, t2)

    @unittest.skipUnless(hasattr(time, 'clock_getres'),
                         'need time.clock_getres()')
    def test_clock_getres(self):
        res = time.clock_getres(time.CLOCK_REALTIME)
        self.assertGreater(res, 0.0)
        self.assertLessEqual(res, 1.0)

    @unittest.skipUnless(hasattr(time, 'clock_settime'),
                         'need time.clock_settime()')
    def test_clock_settime(self):
        t = time.clock_gettime(time.CLOCK_REALTIME)
        try:
            time.clock_settime(time.CLOCK_REALTIME, t)
        except PermissionError:
            pass

        if hasattr(time, 'CLOCK_MONOTONIC'):
            self.assertRaises(OSError,
                              time.clock_settime, time.CLOCK_MONOTONIC, 0)
    def test_conversions(self):
        self.assertTrue(time.ctime(self.t)
                     == time.asctime(time.localtime(self.t)))
        self.assertTrue(long(time.mktime(time.localtime(self.t)))
                     == long(self.t))

    def test_sleep(self):
        time.sleep(1.2)

    def test_strftime(self):
        tt = time.gmtime(self.t)
        for directive in ('a', 'A', 'b', 'B', 'c', 'd', 'H', 'I',
                          'j', 'm', 'M', 'p', 'S',
                          'U', 'w', 'W', 'x', 'X', 'y', 'Y', 'Z', '%'):
            format = ' %' + directive
            try:
                time.strftime(format, tt)
            except ValueError:
                self.fail('conversion specifier: %r failed.' % format)

        # Issue #10762: Guard against invalid/non-supported format string
        # so that Python don't crash (Windows crashes when the format string
        # input to [w]strftime is not kosher.
        if sys.platform.startswith('win'):
            with self.assertRaises(ValueError):
                time.strftime('%f')

    def _bounds_checking(self, func):
        # Make sure that strftime() checks the bounds of the various parts
        # of the time tuple (0 is valid for *all* values).

        # The year field is tested by other test cases above

        # Check month [1, 12] + zero support
        func((1900, 0, 1, 0, 0, 0, 0, 1, -1))
        func((1900, 12, 1, 0, 0, 0, 0, 1, -1))
        self.assertRaises(ValueError, func,
                            (1900, -1, 1, 0, 0, 0, 0, 1, -1))
        self.assertRaises(ValueError, func,
                            (1900, 13, 1, 0, 0, 0, 0, 1, -1))
        # Check day of month [1, 31] + zero support
        func((1900, 1, 0, 0, 0, 0, 0, 1, -1))
        func((1900, 1, 31, 0, 0, 0, 0, 1, -1))
        self.assertRaises(ValueError, func,
                            (1900, 1, -1, 0, 0, 0, 0, 1, -1))
        self.assertRaises(ValueError, func,
                            (1900, 1, 32, 0, 0, 0, 0, 1, -1))
        # Check hour [0, 23]
        func((1900, 1, 1, 23, 0, 0, 0, 1, -1))
        self.assertRaises(ValueError, func,
                            (1900, 1, 1, -1, 0, 0, 0, 1, -1))
        self.assertRaises(ValueError, func,
                            (1900, 1, 1, 24, 0, 0, 0, 1, -1))
        # Check minute [0, 59]
        func((1900, 1, 1, 0, 59, 0, 0, 1, -1))
        self.assertRaises(ValueError, func,
                            (1900, 1, 1, 0, -1, 0, 0, 1, -1))
        self.assertRaises(ValueError, func,
                            (1900, 1, 1, 0, 60, 0, 0, 1, -1))
        # Check second [0, 61]
        self.assertRaises(ValueError, func,
                            (1900, 1, 1, 0, 0, -1, 0, 1, -1))
        # C99 only requires allowing for one leap second, but Python's docs say
        # allow two leap seconds (0..61)
        func((1900, 1, 1, 0, 0, 60, 0, 1, -1))
        func((1900, 1, 1, 0, 0, 61, 0, 1, -1))
        self.assertRaises(ValueError, func,
                            (1900, 1, 1, 0, 0, 62, 0, 1, -1))
        # No check for upper-bound day of week;
        #  value forced into range by a ``% 7`` calculation.
        # Start check at -2 since gettmarg() increments value before taking
        #  modulo.
        self.assertEqual(func((1900, 1, 1, 0, 0, 0, -1, 1, -1)),
                         func((1900, 1, 1, 0, 0, 0, +6, 1, -1)))
        self.assertRaises(ValueError, func,
                            (1900, 1, 1, 0, 0, 0, -2, 1, -1))
        # Check day of the year [1, 366] + zero support
        func((1900, 1, 1, 0, 0, 0, 0, 0, -1))
        func((1900, 1, 1, 0, 0, 0, 0, 366, -1))
        self.assertRaises(ValueError, func,
                            (1900, 1, 1, 0, 0, 0, 0, -1, -1))
        self.assertRaises(ValueError, func,
                            (1900, 1, 1, 0, 0, 0, 0, 367, -1))

    def test_strftime_bounding_check(self):
        self._bounds_checking(lambda tup: time.strftime('', tup))

    def test_strftime_bounds_checking(self):
        # Make sure that strftime() checks the bounds of the various parts
        #of the time tuple (0 is valid for *all* values).

        # Check year [1900, max(int)]
        self.assertRaises(ValueError, time.strftime, '',
                            (1899, 1, 1, 0, 0, 0, 0, 1, -1))
        if time.accept2dyear:
            self.assertRaises(ValueError, time.strftime, '',
                                (-1, 1, 1, 0, 0, 0, 0, 1, -1))
            self.assertRaises(ValueError, time.strftime, '',
                                (100, 1, 1, 0, 0, 0, 0, 1, -1))
        # Check month [1, 12] + zero support
        self.assertRaises(ValueError, time.strftime, '',
                            (1900, -1, 1, 0, 0, 0, 0, 1, -1))
        self.assertRaises(ValueError, time.strftime, '',
                            (1900, 13, 1, 0, 0, 0, 0, 1, -1))
        # Check day of month [1, 31] + zero support
        self.assertRaises(ValueError, time.strftime, '',
                            (1900, 1, -1, 0, 0, 0, 0, 1, -1))
        self.assertRaises(ValueError, time.strftime, '',
                            (1900, 1, 32, 0, 0, 0, 0, 1, -1))
        # Check hour [0, 23]
        self.assertRaises(ValueError, time.strftime, '',
                            (1900, 1, 1, -1, 0, 0, 0, 1, -1))
        self.assertRaises(ValueError, time.strftime, '',
                            (1900, 1, 1, 24, 0, 0, 0, 1, -1))
        # Check minute [0, 59]
        self.assertRaises(ValueError, time.strftime, '',
                            (1900, 1, 1, 0, -1, 0, 0, 1, -1))
        self.assertRaises(ValueError, time.strftime, '',
                            (1900, 1, 1, 0, 60, 0, 0, 1, -1))
        # Check second [0, 61]
        self.assertRaises(ValueError, time.strftime, '',
                            (1900, 1, 1, 0, 0, -1, 0, 1, -1))
        # C99 only requires allowing for one leap second, but Python's docs say
        # allow two leap seconds (0..61)
        self.assertRaises(ValueError, time.strftime, '',
                            (1900, 1, 1, 0, 0, 62, 0, 1, -1))
        # No check for upper-bound day of week;
        #  value forced into range by a ``% 7`` calculation.
        # Start check at -2 since gettmarg() increments value before taking
        #  modulo.
        self.assertRaises(ValueError, time.strftime, '',
                            (1900, 1, 1, 0, 0, 0, -2, 1, -1))
        # Check day of the year [1, 366] + zero support
        self.assertRaises(ValueError, time.strftime, '',
                            (1900, 1, 1, 0, 0, 0, 0, -1, -1))
        self.assertRaises(ValueError, time.strftime, '',
                            (1900, 1, 1, 0, 0, 0, 0, 367, -1))

    def test_default_values_for_zero(self):
        # Make sure that using all zeros uses the proper default values.
        # No test for daylight savings since strftime() does not change output
        # based on its value.
        expected = "2000 01 01 00 00 00 1 001"
        result = time.strftime("%Y %m %d %H %M %S %w %j", (0,)*9)
        self.assertEqual(expected, result)

    def test_strptime(self):
        # Should be able to go round-trip from strftime to strptime without
        # raising an exception.
        tt = time.gmtime(self.t)
        for directive in ('a', 'A', 'b', 'B', 'c', 'd', 'H', 'I',
                          'j', 'm', 'M', 'p', 'S',
                          'U', 'w', 'W', 'x', 'X', 'y', 'Y', 'Z', '%'):
            format = '%' + directive
            strf_output = time.strftime(format, tt)
            try:
                time.strptime(strf_output, format)
            except ValueError:
                self.fail("conversion specifier %r failed with '%s' input." %
                          (format, strf_output))

    def test_asctime(self):
        time.asctime(time.gmtime(self.t))
        self.assertRaises(TypeError, time.asctime, 0)
        self.assertRaises(TypeError, time.asctime, ())

        # Max year is only limited by the size of C int.
        asc = time.asctime((TIME_MAXYEAR, 6, 1) + (0,) * 6)
        self.assertEqual(asc[-len(str(TIME_MAXYEAR)):], str(TIME_MAXYEAR))
        self.assertRaises(OverflowError, time.asctime,
                          (TIME_MAXYEAR + 1,) + (0,) * 8)
        self.assertRaises(TypeError, time.asctime, 0)
        self.assertRaises(TypeError, time.asctime, ())
        self.assertRaises(TypeError, time.asctime, (0,) * 10)

    @unittest.skipIf(not hasattr(time, "tzset"),
        "time module has no attribute tzset")
    def test_tzset(self):

        from os import environ

        # Epoch time of midnight Dec 25th 2002. Never DST in northern
        # hemisphere.
        xmas2002 = 1040774400.0

        # These formats are correct for 2002, and possibly future years
        # This format is the 'standard' as documented at:
        # http://www.opengroup.org/onlinepubs/007904975/basedefs/xbd_chap08.html
        # They are also documented in the tzset(3) man page on most Unix
        # systems.
        eastern = 'EST+05EDT,M4.1.0,M10.5.0'
        victoria = 'AEST-10AEDT-11,M10.5.0,M3.5.0'
        utc='UTC+0'

        org_TZ = environ.get('TZ',None)
        try:
            # Make sure we can switch to UTC time and results are correct
            # Note that unknown timezones default to UTC.
            # Note that altzone is undefined in UTC, as there is no DST
            environ['TZ'] = eastern
            time.tzset()
            environ['TZ'] = utc
            time.tzset()
            self.assertEqual(
                time.gmtime(xmas2002), time.localtime(xmas2002)
                )
            self.assertEqual(time.daylight, 0)
            self.assertEqual(time.timezone, 0)
            self.assertEqual(time.localtime(xmas2002).tm_isdst, 0)

            # Make sure we can switch to US/Eastern
            environ['TZ'] = eastern
            time.tzset()
            self.assertNotEqual(time.gmtime(xmas2002), time.localtime(xmas2002))
            self.assertEqual(time.tzname, ('EST', 'EDT'))
            self.assertEqual(len(time.tzname), 2)
            self.assertEqual(time.daylight, 1)
            self.assertEqual(time.timezone, 18000)
            self.assertEqual(time.altzone, 14400)
            self.assertEqual(time.localtime(xmas2002).tm_isdst, 0)
            self.assertEqual(len(time.tzname), 2)

            # Now go to the southern hemisphere.
            environ['TZ'] = victoria
            time.tzset()
            self.assertNotEqual(time.gmtime(xmas2002), time.localtime(xmas2002))

            # Issue #11886: Australian Eastern Standard Time (UTC+10) is called
            # "EST" (as Eastern Standard Time, UTC-5) instead of "AEST" on some
            # operating systems (e.g. FreeBSD), which is wrong. See for example
            # this bug: http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=93810
            self.assertIn(time.tzname[0], ('AEST' 'EST'), time.tzname[0])
            self.assertTrue(time.tzname[1] == 'AEDT', str(time.tzname[1]))
            self.assertEqual(len(time.tzname), 2)
            self.assertEqual(time.daylight, 1)
            self.assertEqual(time.timezone, -36000)
            self.assertEqual(time.altzone, -39600)
            self.assertEqual(time.localtime(xmas2002).tm_isdst, 1)

        finally:
            # Repair TZ environment variable in case any other tests
            # rely on it.
            if org_TZ is not None:
                environ['TZ'] = org_TZ
            elif environ.has_key('TZ'):
                del environ['TZ']
            time.tzset()

    def test_insane_timestamps(self):
        # It's possible that some platform maps time_t to double,
        # and that this test will fail there.  This test should
        # exempt such platforms (provided they return reasonable
        # results!).
        for func in time.ctime, time.gmtime, time.localtime:
            for unreasonable in -1e200, 1e200:
                self.assertRaises(ValueError, func, unreasonable)

    def test_ctime_without_arg(self):
        # Not sure how to check the values, since the clock could tick
        # at any time.  Make sure these are at least accepted and
        # don't raise errors.
        time.ctime()
        time.ctime(None)

    def test_gmtime_without_arg(self):
        gt0 = time.gmtime()
        gt1 = time.gmtime(None)
        t0 = time.mktime(gt0)
        t1 = time.mktime(gt1)
        self.assertTrue(0 <= (t1-t0) < 0.2)

    def test_localtime_without_arg(self):
        lt0 = time.localtime()
        lt1 = time.localtime(None)
        t0 = time.mktime(lt0)
        t1 = time.mktime(lt1)
        self.assertTrue(0 <= (t1-t0) < 0.2)

    def test_mktime(self):
        # Issue #1726687
        for t in (-2, -1, 0, 1):
            try:
                tt = time.localtime(t)
            except ValueError:
                pass
            else:
                self.assertEqual(time.mktime(tt), t)

    # Issue #13309: passing extreme values to mktime() or localtime()
    # borks the glibc's internal timezone data.
    @unittest.skipUnless(platform.libc_ver()[0] != 'glibc',
                         "disabled because of a bug in glibc. Issue #13309")
    def test_mktime_error(self):
        # It may not be possible to reliably make mktime return error
        # on all platfom.  This will make sure that no other exception
        # than OverflowError is raised for an extreme value.
        tt = time.gmtime(self.t)
        tzname = time.strftime('%Z', tt)
        self.assertNotEqual(tzname, 'LMT')
        try:
            time.mktime((-1, 1, 1, 0, 0, 0, -1, -1, -1))
        except ValueError:
            pass
        self.assertEqual(time.strftime('%Z', tt), tzname)

    def test_monotonic(self):
        # monotonic() should not go backward
        times = [time.monotonic() for n in range(100)]
        t1 = times[0]
        for t2 in times[1:]:
            self.assertGreaterEqual(t2, t1, "times=%s" % times)
            t1 = t2

        # monotonic() includes time elapsed during a sleep
        t1 = time.monotonic()
        time.sleep(0.5)
        t2 = time.monotonic()
        dt = t2 - t1
        self.assertGreater(t2, t1)
        # Issue #20101: On some Windows machines, dt may be slightly low
        self.assertTrue(0.45 <= dt <= 1.0, dt)

    def test_perf_counter(self):
        time.perf_counter()

    def test_process_time(self):
        # process_time() should not include time spend during a sleep
        start = time.process_time()
        time.sleep(0.100)
        stop = time.process_time()
        # use 20 ms because process_time() has usually a resolution of 15 ms
        # on Windows
        self.assertLess(stop - start, 0.020)

        # bpo-33723: A busy loop of 100 ms should increase process_time()
        # by at least 15 ms
        min_time = 0.015
        busy_time = 0.100

        # process_time() should include CPU time spent in any thread
        start = time.process_time()
        busy_wait(busy_time)
        stop = time.process_time()
        self.assertGreaterEqual(stop - start, min_time)

        t = threading.Thread(target=busy_wait, args=(busy_time,))
        start = time.process_time()
        t.start()
        t.join()
        stop = time.process_time()
        self.assertGreaterEqual(stop - start, min_time)

    def test_thread_time(self):
        if not hasattr(time, 'thread_time'):
            if sys.platform.startswith(('linux', 'win')):
                self.fail("time.thread_time() should be available on %r"
                          % (sys.platform,))
            else:
                self.skipTest("need time.thread_time")

        # thread_time() should not include time spend during a sleep
        start = time.thread_time()
        time.sleep(0.100)
        stop = time.thread_time()
        # use 20 ms because thread_time() has usually a resolution of 15 ms
        # on Windows
        self.assertLess(stop - start, 0.020)

        # bpo-33723: A busy loop of 100 ms should increase thread_time()
        # by at least 15 ms
        min_time = 0.015
        busy_time = 0.100

        # thread_time() should include CPU time spent in current thread...
        start = time.thread_time()
        busy_wait(busy_time)
        stop = time.thread_time()
        self.assertGreaterEqual(stop - start, min_time)

        # ...but not in other threads
        t = threading.Thread(target=busy_wait, args=(busy_time,))
        start = time.thread_time()
        t.start()
        t.join()
        stop = time.thread_time()
        self.assertLess(stop - start, min_time)

    @unittest.skipUnless(hasattr(time, 'clock_settime'),
                         'need time.clock_settime')
    def test_monotonic_settime(self):
        t1 = time.monotonic()
        realtime = time.clock_gettime(time.CLOCK_REALTIME)
        # jump backward with an offset of 1 hour
        try:
            time.clock_settime(time.CLOCK_REALTIME, realtime - 3600)
        except PermissionError as err:
            self.skipTest(err)
        t2 = time.monotonic()
        time.clock_settime(time.CLOCK_REALTIME, realtime)
        # monotonic must not be affected by system clock updates
        self.assertGreaterEqual(t2, t1)

    def test_localtime_failure(self):
        # Issue #13847: check for localtime() failure
        invalid_time_t = None
        for time_t in (-1, 2**30, 2**33, 2**60):
            try:
                time.localtime(time_t)
            except (ValueError, OverflowError):
                self.skipTest("need 64-bit time_t")
            except OSError:
                invalid_time_t = time_t
                break
        if invalid_time_t is None:
            self.skipTest("unable to find an invalid time_t value")

        self.assertRaises(OSError, time.localtime, invalid_time_t)
        self.assertRaises(OSError, time.ctime, invalid_time_t)

        # Issue #26669: check for localtime() failure
        self.assertRaises(ValueError, time.localtime, float("nan"))
        self.assertRaises(ValueError, time.ctime, float("nan"))

def test_main():
    test_support.run_unittest(TimeTestCase)


if __name__ == "__main__":
    test_main()
