
/* Time module */

#include "Python.h"
#include "structseq.h"
#include "pytime.h"

#ifdef __APPLE__
#if defined(HAVE_GETTIMEOFDAY) && defined(HAVE_FTIME)
  /*
   * floattime falls back to ftime when getttimeofday fails because the latter
   * might fail on some platforms. This fallback is unwanted on MacOSX because
   * that makes it impossible to use a binary build on OSX 10.4 on earlier
   * releases of the OS. Therefore claim we don't support ftime.
   */
# undef HAVE_FTIME
#endif
#endif

#include <ctype.h>

#ifdef HAVE_SYS_TIMES_H
#include <sys/times.h>
#endif

#ifdef HAVE_SYS_TYPES_H
#include <sys/types.h>
#endif /* HAVE_SYS_TYPES_H */

#if defined(HAVE_SYS_RESOURCE_H)
#include <sys/resource.h>
#endif

#ifdef QUICKWIN
#include <io.h>
#endif

#ifdef HAVE_FTIME
#include <sys/timeb.h>
#if !defined(MS_WINDOWS) && !defined(PYOS_OS2)
extern int ftime(struct timeb *);
#endif /* MS_WINDOWS */
#endif /* HAVE_FTIME */

#if defined(__WATCOMC__) && !defined(__QNX__)
#include <i86.h>
#else
#ifdef MS_WINDOWS
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include "pythread.h"

/* helper to allow us to interrupt sleep() on Windows*/
static HANDLE hInterruptEvent = NULL;
static BOOL WINAPI PyCtrlHandler(DWORD dwCtrlType)
{
    SetEvent(hInterruptEvent);
    /* allow other default handlers to be called.
       Default Python handler will setup the
       KeyboardInterrupt exception.
    */
    return FALSE;
}
static long main_thread;


#if defined(__BORLANDC__)
/* These overrides not needed for Win32 */
#define timezone _timezone
#define tzname _tzname
#define daylight _daylight
#endif /* __BORLANDC__ */
#endif /* MS_WINDOWS */
#endif /* !__WATCOMC__ || __QNX__ */

#if defined(MS_WINDOWS) && !defined(__BORLANDC__)
#include <time.h>
#define timezone _timezone
#define daylight _daylight
#define tzname _tzname
#endif /* MS_WINDOWS && !defined(__BORLANDC__) */

#if defined(PYOS_OS2)
#define INCL_DOS
#define INCL_ERRORS
#include <os2.h>
#endif

#if defined(PYCC_VACPP)
#include <sys/time.h>
#endif

#ifdef __BEOS__
#include <time.h>
/* For bigtime_t, snooze(). - [cjh] */
#include <support/SupportDefs.h>
#include <kernel/OS.h>
#endif

#ifdef RISCOS
extern int riscos_sleep(double);
#endif

/* Forward declarations */
static int floatsleep(double);
static double floattime(void);

/* For Y2K check */
static PyObject *moddict = NULL;

#define SEC_TO_NS (1000 * 1000 * 1000)

/* Exposed in pytime.h. */
time_t
_PyTime_DoubleToTimet(double x)
{
    time_t result;
    double diff;

    result = (time_t)x;
    /* How much info did we lose?  time_t may be an integral or
     * floating type, and we don't know which.  If it's integral,
     * we don't know whether C truncates, rounds, returns the floor,
     * etc.  If we lost a second or more, the C rounding is
     * unreasonable, or the input just doesn't fit in a time_t;
     * call it an error regardless.  Note that the original cast to
     * time_t can cause a C error too, but nothing we can do to
     * worm around that.
     */
    diff = x - (double)result;
    if (diff <= -1.0 || diff >= 1.0) {
        PyErr_SetString(PyExc_ValueError,
                        "timestamp out of range for platform time_t");
        result = (time_t)-1;
    }
    return result;
}

static PyObject*
_PyFloat_FromPyTime(_PyTime_t t)
{
    double d = _PyTime_AsSecondsDouble(t);
    return PyFloat_FromDouble(d);
}

static PyObject *
time_time(PyObject *self, PyObject *unused)
{
    double secs;
    secs = floattime();
    if (secs == 0.0) {
        PyErr_SetFromErrno(PyExc_IOError);
        return NULL;
    }
    return PyFloat_FromDouble(secs);
}

PyDoc_STRVAR(time_doc,
"time() -> floating point number\n\
\n\
Return the current time in seconds since the Epoch.\n\
Fractions of a second may be present if the system clock provides them.");

static PyObject *
time_time_ns(PyObject *self, PyObject *unused)
{
    _PyTime_t t = _PyTime_GetSystemClock();
    return _PyTime_AsNanosecondsObject(t);
}

PyDoc_STRVAR(time_ns_doc,
"time_ns() -> int\n\
\n\
Return the current time in nanoseconds since the Epoch.");

#if defined(HAVE_CLOCK)

#ifndef CLOCKS_PER_SEC
#  ifdef CLK_TCK
#    define CLOCKS_PER_SEC CLK_TCK
#  else
#    define CLOCKS_PER_SEC 1000000
#  endif
#endif

static int
_PyTime_GetClockWithInfo(_PyTime_t *tp, _Py_clock_info_t *info)
{
    static int initialized = 0;
    clock_t ticks;

    if (!initialized) {
        initialized = 1;

        /* must sure that _PyTime_MulDiv(ticks, SEC_TO_NS, CLOCKS_PER_SEC)
           above cannot overflow */
        if ((_PyTime_t)CLOCKS_PER_SEC > _PyTime_MAX / SEC_TO_NS) {
            PyErr_SetString(PyExc_OverflowError,
                            "CLOCKS_PER_SEC is too large");
            return -1;
        }
    }

    if (info) {
        info->implementation = "clock()";
        info->resolution = 1.0 / (double)CLOCKS_PER_SEC;
        info->monotonic = 1;
        info->adjustable = 0;
    }

    ticks = clock();
    if (ticks == (clock_t)-1) {
        PyErr_SetString(PyExc_RuntimeError,
                        "the processor time used is not available "
                        "or its value cannot be represented");
        return -1;
    }
    *tp = _PyTime_MulDiv(ticks, SEC_TO_NS, (_PyTime_t)CLOCKS_PER_SEC);
    return 0;
}
#endif /* HAVE_CLOCK */

static PyObject*
perf_counter(_Py_clock_info_t *info)
{
    _PyTime_t t;
    if (_PyTime_GetPerfCounterWithInfo(&t, info) < 0) {
        return NULL;
    }
    return _PyFloat_FromPyTime(t);
}

#if defined(MS_WINDOWS) || defined(HAVE_CLOCK)
#define PYCLOCK
static PyObject*
pyclock(_Py_clock_info_t *info)
{
    if (PyErr_WarnEx(PyExc_DeprecationWarning,
                      "time.clock has been deprecated in Python 3.3 and will "
                      "be removed from Python 3.8: "
                      "use time.perf_counter or time.process_time "
                      "instead", 1) < 0) {
        return NULL;
    }

#ifdef MS_WINDOWS
    return perf_counter(info);
#else
    _PyTime_t t;
    if (_PyTime_GetClockWithInfo(&t, info) < 0) {
        return NULL;
    }
    return _PyFloat_FromPyTime(t);
#endif
}

static PyObject *
time_clock(PyObject *self, PyObject *unused)
{
    return pyclock(NULL);
}
#endif /* HAVE_CLOCK || MS_WINDOWS */

#ifdef PYCLOCK
PyDoc_STRVAR(clock_doc,
"clock() -> floating point number\n\
\n\
Return the CPU time or real time since the start of the process or since\n\
the first call to clock().  This has as much precision as the system\n\
records.");
#endif

#ifdef HAVE_CLOCK_GETTIME
static PyObject *
time_clock_gettime(PyObject *self, PyObject *args)
{
    int ret;
    int clk_id;
    struct timespec tp;

    if (!PyArg_ParseTuple(args, "i:clock_gettime", &clk_id)) {
        return NULL;
    }

    ret = clock_gettime((clockid_t)clk_id, &tp);
    if (ret != 0) {
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }
    return PyFloat_FromDouble(tp.tv_sec + tp.tv_nsec * 1e-9);
}

PyDoc_STRVAR(clock_gettime_doc,
"clock_gettime(clk_id) -> float\n\
\n\
Return the time of the specified clock clk_id.");

static PyObject *
time_clock_gettime_ns(PyObject *self, PyObject *args)
{
    int ret;
    int clk_id;
    struct timespec ts;
    _PyTime_t t;

    if (!PyArg_ParseTuple(args, "i:clock_gettime", &clk_id)) {
        return NULL;
    }

    ret = clock_gettime((clockid_t)clk_id, &ts);
    if (ret != 0) {
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }
    if (_PyTime_FromTimespec(&t, &ts) < 0) {
        return NULL;
    }
    return _PyTime_AsNanosecondsObject(t);
}

PyDoc_STRVAR(clock_gettime_ns_doc,
"clock_gettime_ns(clk_id) -> int\n\
\n\
Return the time of the specified clock clk_id as nanoseconds.");
#endif   /* HAVE_CLOCK_GETTIME */

#ifdef HAVE_CLOCK_SETTIME
static PyObject *
time_clock_settime(PyObject *self, PyObject *args)
{
    int clk_id;
    PyObject *obj;
    _PyTime_t t;
    struct timespec tp;
    int ret;

    if (!PyArg_ParseTuple(args, "iO:clock_settime", &clk_id, &obj))
        return NULL;

    if (_PyTime_FromSecondsObject(&t, obj, _PyTime_ROUND_FLOOR) < 0)
        return NULL;

    if (_PyTime_AsTimespec(t, &tp) == -1)
        return NULL;

    ret = clock_settime((clockid_t)clk_id, &tp);
    if (ret != 0) {
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }
    Py_RETURN_NONE;
}

PyDoc_STRVAR(clock_settime_doc,
"clock_settime(clk_id, time)\n\
\n\
Set the time of the specified clock clk_id.");

static PyObject *
time_clock_settime_ns(PyObject *self, PyObject *args)
{
    int clk_id;
    PyObject *obj;
    _PyTime_t t;
    struct timespec ts;
    int ret;

    if (!PyArg_ParseTuple(args, "iO:clock_settime", &clk_id, &obj)) {
        return NULL;
    }

    if (_PyTime_FromNanosecondsObject(&t, obj) < 0) {
        return NULL;
    }
    if (_PyTime_AsTimespec(t, &ts) == -1) {
        return NULL;
    }

    ret = clock_settime((clockid_t)clk_id, &ts);
    if (ret != 0) {
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }
    Py_RETURN_NONE;
}

PyDoc_STRVAR(clock_settime_ns_doc,
"clock_settime_ns(clk_id, time)\n\
\n\
Set the time of the specified clock clk_id with nanoseconds.");
#endif   /* HAVE_CLOCK_SETTIME */

#ifdef HAVE_CLOCK_GETRES
static PyObject *
time_clock_getres(PyObject *self, PyObject *args)
{
    int ret;
    int clk_id;
    struct timespec tp;

    if (!PyArg_ParseTuple(args, "i:clock_getres", &clk_id))
        return NULL;

    ret = clock_getres((clockid_t)clk_id, &tp);
    if (ret != 0) {
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }

    return PyFloat_FromDouble(tp.tv_sec + tp.tv_nsec * 1e-9);
}

PyDoc_STRVAR(clock_getres_doc,
"clock_getres(clk_id) -> floating point number\n\
\n\
Return the resolution (precision) of the specified clock clk_id.");
#endif   /* HAVE_CLOCK_GETRES */

#ifdef HAVE_PTHREAD_GETCPUCLOCKID
static PyObject *
time_pthread_getcpuclockid(PyObject *self, PyObject *args)
{
    unsigned long thread_id;
    int err;
    clockid_t clk_id;
    if (!PyArg_ParseTuple(args, "k:pthread_getcpuclockid", &thread_id)) {
        return NULL;
    }
    err = pthread_getcpuclockid((pthread_t)thread_id, &clk_id);
    if (err) {
        errno = err;
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }
    return PyLong_FromLong(clk_id);
}

PyDoc_STRVAR(pthread_getcpuclockid_doc,
"pthread_getcpuclockid(thread_id) -> int\n\
\n\
Return the clk_id of a thread's CPU time clock.");
#endif /* HAVE_PTHREAD_GETCPUCLOCKID */

static PyObject *
time_sleep(PyObject *self, PyObject *args)
{
    double secs;
    if (!PyArg_ParseTuple(args, "d:sleep", &secs))
        return NULL;
    if (floatsleep(secs) != 0)
        return NULL;
    Py_INCREF(Py_None);
    return Py_None;
}

PyDoc_STRVAR(sleep_doc,
"sleep(seconds)\n\
\n\
Delay execution for a given number of seconds.  The argument may be\n\
a floating point number for subsecond precision.");

static PyStructSequence_Field struct_time_type_fields[] = {
    {"tm_year", "year, for example, 1993"},
    {"tm_mon", "month of year, range [1, 12]"},
    {"tm_mday", "day of month, range [1, 31]"},
    {"tm_hour", "hours, range [0, 23]"},
    {"tm_min", "minutes, range [0, 59]"},
    {"tm_sec", "seconds, range [0, 61])"},
    {"tm_wday", "day of week, range [0, 6], Monday is 0"},
    {"tm_yday", "day of year, range [1, 366]"},
    {"tm_isdst", "1 if summer time is in effect, 0 if not, and -1 if unknown"},
    {0}
};

static PyStructSequence_Desc struct_time_type_desc = {
    "time.struct_time",
    "The time value as returned by gmtime(), localtime(), and strptime(), and\n"
    " accepted by asctime(), mktime() and strftime().  May be considered as a\n"
    " sequence of 9 integers.\n\n"
    " Note that several fields' values are not the same as those defined by\n"
    " the C language standard for struct tm.  For example, the value of the\n"
    " field tm_year is the actual year, not year - 1900.  See individual\n"
    " fields' descriptions for details.",
    struct_time_type_fields,
    9,
};

static int initialized;
static PyTypeObject StructTimeType;

static PyObject *
tmtotuple(struct tm *p)
{
    PyObject *v = PyStructSequence_New(&StructTimeType);
    if (v == NULL)
        return NULL;

#define SET(i,val) PyStructSequence_SET_ITEM(v, i, PyInt_FromLong((long) val))

    SET(0, p->tm_year + 1900);
    SET(1, p->tm_mon + 1);         /* Want January == 1 */
    SET(2, p->tm_mday);
    SET(3, p->tm_hour);
    SET(4, p->tm_min);
    SET(5, p->tm_sec);
    SET(6, (p->tm_wday + 6) % 7); /* Want Monday == 0 */
    SET(7, p->tm_yday + 1);        /* Want January, 1 == 1 */
    SET(8, p->tm_isdst);
#undef SET
    if (PyErr_Occurred()) {
        Py_XDECREF(v);
        return NULL;
    }

    return v;
}

static PyObject *
time_convert(double when, struct tm * (*function)(const time_t *))
{
    struct tm *p;
    time_t whent = _PyTime_DoubleToTimet(when);

    if (whent == (time_t)-1 && PyErr_Occurred())
        return NULL;
    errno = 0;
    p = function(&whent);
    if (p == NULL) {
#ifdef EINVAL
        if (errno == 0)
            errno = EINVAL;
#endif
        return PyErr_SetFromErrno(PyExc_ValueError);
    }
    return tmtotuple(p);
}

/* Parse arg tuple that can contain an optional float-or-None value;
   format needs to be "|O:name".
   Returns non-zero on success (parallels PyArg_ParseTuple).
*/
static int
parse_time_double_args(PyObject *args, char *format, double *pwhen)
{
    PyObject *ot = NULL;

    if (!PyArg_ParseTuple(args, format, &ot))
        return 0;
    if (ot == NULL || ot == Py_None)
        *pwhen = floattime();
    else {
        double when = PyFloat_AsDouble(ot);
        if (PyErr_Occurred())
            return 0;
        *pwhen = when;
    }
    return 1;
}

static PyObject *
time_gmtime(PyObject *self, PyObject *args)
{
    double when;
    if (!parse_time_double_args(args, "|O:gmtime", &when))
        return NULL;
    return time_convert(when, gmtime);
}

PyDoc_STRVAR(gmtime_doc,
"gmtime([seconds]) -> (tm_year, tm_mon, tm_mday, tm_hour, tm_min,\n\
                       tm_sec, tm_wday, tm_yday, tm_isdst)\n\
\n\
Convert seconds since the Epoch to a time tuple expressing UTC (a.k.a.\n\
GMT).  When 'seconds' is not passed in, convert the current time instead.");

static PyObject *
time_localtime(PyObject *self, PyObject *args)
{
    double when;
    if (!parse_time_double_args(args, "|O:localtime", &when))
        return NULL;
    return time_convert(when, localtime);
}

PyDoc_STRVAR(localtime_doc,
"localtime([seconds]) -> (tm_year,tm_mon,tm_mday,tm_hour,tm_min,\n\
                          tm_sec,tm_wday,tm_yday,tm_isdst)\n\
\n\
Convert seconds since the Epoch to a time tuple expressing local time.\n\
When 'seconds' is not passed in, convert the current time instead.");

static int
gettmarg(PyObject *args, struct tm *p)
{
    int y;
    memset((void *) p, '\0', sizeof(struct tm));

    if (!PyArg_Parse(args, "(iiiiiiiii)",
                     &y,
                     &p->tm_mon,
                     &p->tm_mday,
                     &p->tm_hour,
                     &p->tm_min,
                     &p->tm_sec,
                     &p->tm_wday,
                     &p->tm_yday,
                     &p->tm_isdst))
        return 0;
    if (y < 1900) {
        PyObject *accept = PyDict_GetItemString(moddict,
                                                "accept2dyear");
        if (accept == NULL || !PyInt_Check(accept) ||
            PyInt_AsLong(accept) == 0) {
            PyErr_SetString(PyExc_ValueError,
                            "year >= 1900 required");
            return 0;
        }
        if (69 <= y && y <= 99)
            y += 1900;
        else if (0 <= y && y <= 68)
            y += 2000;
        else {
            PyErr_SetString(PyExc_ValueError,
                            "year out of range");
            return 0;
        }
    }
    p->tm_year = y - 1900;
    p->tm_mon--;
    p->tm_wday = (p->tm_wday + 1) % 7;
    p->tm_yday--;
    return 1;
}

/* Check values of the struct tm fields before it is passed to strftime() and
 * asctime().  Return 1 if all values are valid, otherwise set an exception
 * and returns 0.
 */
static int
checktm(struct tm* buf)
{
    /* Checks added to make sure strftime() and asctime() does not crash Python by
       indexing blindly into some array for a textual representation
       by some bad index (fixes bug #897625 and #6608).

       Also support values of zero from Python code for arguments in which
       that is out of range by forcing that value to the lowest value that
       is valid (fixed bug #1520914).

       Valid ranges based on what is allowed in struct tm:

       - tm_year: [0, max(int)] (1)
       - tm_mon: [0, 11] (2)
       - tm_mday: [1, 31]
       - tm_hour: [0, 23]
       - tm_min: [0, 59]
       - tm_sec: [0, 60]
       - tm_wday: [0, 6] (1)
       - tm_yday: [0, 365] (2)
       - tm_isdst: [-max(int), max(int)]

       (1) gettmarg() handles bounds-checking.
       (2) Python's acceptable range is one greater than the range in C,
       thus need to check against automatic decrement by gettmarg().
    */
    if (buf->tm_mon == -1)
        buf->tm_mon = 0;
    else if (buf->tm_mon < 0 || buf->tm_mon > 11) {
        PyErr_SetString(PyExc_ValueError, "month out of range");
        return 0;
    }
    if (buf->tm_mday == 0)
        buf->tm_mday = 1;
    else if (buf->tm_mday < 0 || buf->tm_mday > 31) {
        PyErr_SetString(PyExc_ValueError, "day of month out of range");
        return 0;
    }
    if (buf->tm_hour < 0 || buf->tm_hour > 23) {
        PyErr_SetString(PyExc_ValueError, "hour out of range");
        return 0;
    }
    if (buf->tm_min < 0 || buf->tm_min > 59) {
        PyErr_SetString(PyExc_ValueError, "minute out of range");
        return 0;
    }
    if (buf->tm_sec < 0 || buf->tm_sec > 61) {
        PyErr_SetString(PyExc_ValueError, "seconds out of range");
        return 0;
    }
    /* tm_wday does not need checking of its upper-bound since taking
    ``% 7`` in gettmarg() automatically restricts the range. */
    if (buf->tm_wday < 0) {
        PyErr_SetString(PyExc_ValueError, "day of week out of range");
        return 0;
    }
    if (buf->tm_yday == -1)
        buf->tm_yday = 0;
    else if (buf->tm_yday < 0 || buf->tm_yday > 365) {
        PyErr_SetString(PyExc_ValueError, "day of year out of range");
        return 0;
    }
    return 1;
}

#ifdef HAVE_STRFTIME
static PyObject *
time_strftime(PyObject *self, PyObject *args)
{
    PyObject *tup = NULL;
    struct tm buf;
    const char *fmt;
    size_t fmtlen, buflen;
    char *outbuf = 0;
    size_t i;

    memset((void *) &buf, '\0', sizeof(buf));

    if (!PyArg_ParseTuple(args, "s|O:strftime", &fmt, &tup))
        return NULL;

    if (tup == NULL) {
        time_t tt = time(NULL);
        buf = *localtime(&tt);
    } else if (!gettmarg(tup, &buf)
               || !checktm(&buf)) {
        return NULL;
    }

    /* Checks added to make sure strftime() does not crash Python by
       indexing blindly into some array for a textual representation
       by some bad index (fixes bug #897625).

        Also support values of zero from Python code for arguments in which
        that is out of range by forcing that value to the lowest value that
        is valid (fixed bug #1520914).

        Valid ranges based on what is allowed in struct tm:

        - tm_year: [0, max(int)] (1)
        - tm_mon: [0, 11] (2)
        - tm_mday: [1, 31]
        - tm_hour: [0, 23]
        - tm_min: [0, 59]
        - tm_sec: [0, 60]
        - tm_wday: [0, 6] (1)
        - tm_yday: [0, 365] (2)
        - tm_isdst: [-max(int), max(int)]

        (1) gettmarg() handles bounds-checking.
        (2) Python's acceptable range is one greater than the range in C,
        thus need to check against automatic decrement by gettmarg().
    */
    if (buf.tm_mon == -1)
        buf.tm_mon = 0;
    else if (buf.tm_mon < 0 || buf.tm_mon > 11) {
        PyErr_SetString(PyExc_ValueError, "month out of range");
            return NULL;
    }
    if (buf.tm_mday == 0)
        buf.tm_mday = 1;
    else if (buf.tm_mday < 0 || buf.tm_mday > 31) {
        PyErr_SetString(PyExc_ValueError, "day of month out of range");
            return NULL;
    }
    if (buf.tm_hour < 0 || buf.tm_hour > 23) {
        PyErr_SetString(PyExc_ValueError, "hour out of range");
        return NULL;
    }
    if (buf.tm_min < 0 || buf.tm_min > 59) {
        PyErr_SetString(PyExc_ValueError, "minute out of range");
        return NULL;
    }
    if (buf.tm_sec < 0 || buf.tm_sec > 61) {
        PyErr_SetString(PyExc_ValueError, "seconds out of range");
        return NULL;
    }
    /* tm_wday does not need checking of its upper-bound since taking
    ``% 7`` in gettmarg() automatically restricts the range. */
    if (buf.tm_wday < 0) {
        PyErr_SetString(PyExc_ValueError, "day of week out of range");
        return NULL;
    }
    if (buf.tm_yday == -1)
        buf.tm_yday = 0;
    else if (buf.tm_yday < 0 || buf.tm_yday > 365) {
        PyErr_SetString(PyExc_ValueError, "day of year out of range");
        return NULL;
    }
    /* Normalize tm_isdst just in case someone foolishly implements %Z
       based on the assumption that tm_isdst falls within the range of
       [-1, 1] */
    if (buf.tm_isdst < -1)
        buf.tm_isdst = -1;
    else if (buf.tm_isdst > 1)
        buf.tm_isdst = 1;

#ifdef MS_WINDOWS
    /* check that the format string contains only valid directives */
    for(outbuf = strchr(fmt, '%');
        outbuf != NULL;
        outbuf = strchr(outbuf+2, '%'))
    {
        if (outbuf[1]=='#')
            ++outbuf; /* not documented by python, */
        if (outbuf[1]=='\0' ||
            !strchr("aAbBcdHIjmMpSUwWxXyYzZ%", outbuf[1]))
        {
            PyErr_SetString(PyExc_ValueError, "Invalid format string");
            return 0;
        }
    }
#endif

    fmtlen = strlen(fmt);

    /* I hate these functions that presume you know how big the output
     * will be ahead of time...
     */
    for (i = 1024; ; i += i) {
        outbuf = (char *)malloc(i);
        if (outbuf == NULL) {
            return PyErr_NoMemory();
        }
        buflen = strftime(outbuf, i, fmt, &buf);
        if (buflen > 0 || i >= 256 * fmtlen) {
            /* If the buffer is 256 times as long as the format,
               it's probably not failing for lack of room!
               More likely, the format yields an empty result,
               e.g. an empty format, or %Z when the timezone
               is unknown. */
            PyObject *ret;
            ret = PyString_FromStringAndSize(outbuf, buflen);
            free(outbuf);
            return ret;
        }
        free(outbuf);
#if defined _MSC_VER && _MSC_VER >= 1400 && defined(__STDC_SECURE_LIB__)
        /* VisualStudio .NET 2005 does this properly */
        if (buflen == 0 && errno == EINVAL) {
            PyErr_SetString(PyExc_ValueError, "Invalid format string");
            return 0;
        }
#endif

    }
}

PyDoc_STRVAR(strftime_doc,
"strftime(format[, tuple]) -> string\n\
\n\
Convert a time tuple to a string according to a format specification.\n\
See the library reference manual for formatting codes. When the time tuple\n\
is not present, current time as returned by localtime() is used.");
#endif /* HAVE_STRFTIME */

static PyObject *
time_strptime(PyObject *self, PyObject *args)
{
    PyObject *strptime_module = PyImport_ImportModuleNoBlock("_strptime");
    PyObject *strptime_result;

    if (!strptime_module)
        return NULL;
    strptime_result = PyObject_CallMethod(strptime_module,
                                            "_strptime_time", "O", args);
    Py_DECREF(strptime_module);
    return strptime_result;
}

PyDoc_STRVAR(strptime_doc,
"strptime(string, format) -> struct_time\n\
\n\
Parse a string to a time tuple according to a format specification.\n\
See the library reference manual for formatting codes (same as strftime()).");


static PyObject *
_asctime(struct tm *timeptr)
{
    /* Inspired by Open Group reference implementation available at
     * http://pubs.opengroup.org/onlinepubs/009695399/functions/asctime.html */
    static const char wday_name[7][4] = {
        "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"
    };
    static const char mon_name[12][4] = {
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    };
    PyObject *unicode, *str;
    /* PyString_FromString() cannot be used because it doesn't support %3d */
    unicode = PyUnicode_FromFormat(
        "%s %s%3d %.2d:%.2d:%.2d %d",
        wday_name[timeptr->tm_wday],
        mon_name[timeptr->tm_mon],
        timeptr->tm_mday, timeptr->tm_hour,
        timeptr->tm_min, timeptr->tm_sec,
        1900 + timeptr->tm_year);
    if (unicode == NULL) {
        return NULL;
    }

    str = PyUnicode_AsASCIIString(unicode);
    Py_DECREF(unicode);
    return str;
}

static PyObject *
time_asctime(PyObject *self, PyObject *args)
{
    PyObject *tup = NULL;
    struct tm buf;
    if (!PyArg_UnpackTuple(args, "asctime", 0, 1, &tup))
        return NULL;
    if (tup == NULL) {
        time_t tt = time(NULL);
        buf = *localtime(&tt);
    } else if (!gettmarg(tup, &buf)
               || !checktm(&buf)) {
        return NULL;
    }
    return _asctime(&buf);
}

PyDoc_STRVAR(asctime_doc,
"asctime([tuple]) -> string\n\
\n\
Convert a time tuple to a string, e.g. 'Sat Jun 06 16:26:11 1998'.\n\
When the time tuple is not present, current time as returned by localtime()\n\
is used.");

static PyObject *
time_ctime(PyObject *self, PyObject *args)
{
    PyObject *ot = NULL;
    time_t tt;
    struct tm *buf;

    if (!PyArg_UnpackTuple(args, "ctime", 0, 1, &ot))
        return NULL;
    if (ot == NULL || ot == Py_None)
        tt = time(NULL);
    else {
        double dt = PyFloat_AsDouble(ot);
        if (PyErr_Occurred())
            return NULL;
        tt = _PyTime_DoubleToTimet(dt);
        if (tt == (time_t)-1 && PyErr_Occurred())
            return NULL;
    }
    buf = localtime(&tt);
    if (buf == NULL) {
#ifdef EINVAL
        if (errno == 0) {
            errno = EINVAL;
        }
#endif
        return PyErr_SetFromErrno(PyExc_ValueError);
    }
    return _asctime(buf);
}

PyDoc_STRVAR(ctime_doc,
"ctime(seconds) -> string\n\
\n\
Convert a time in seconds since the Epoch to a string in local time.\n\
This is equivalent to asctime(localtime(seconds)). When the time tuple is\n\
not present, current time as returned by localtime() is used.");

#ifdef HAVE_MKTIME
static PyObject *
time_mktime(PyObject *self, PyObject *tup)
{
    struct tm buf;
    time_t tt;
    if (!gettmarg(tup, &buf))
        return NULL;
    buf.tm_wday = -1;  /* sentinel; original value ignored */
    tt = mktime(&buf);
    /* Return value of -1 does not necessarily mean an error, but tm_wday
     * cannot remain set to -1 if mktime succeeded. */
    if (tt == (time_t)(-1) && buf.tm_wday == -1) {
        PyErr_SetString(PyExc_OverflowError,
                        "mktime argument out of range");
        return NULL;
    }
    return PyFloat_FromDouble((double)tt);
}

PyDoc_STRVAR(mktime_doc,
"mktime(tuple) -> floating point number\n\
\n\
Convert a time tuple in local time to seconds since the Epoch.");
#endif /* HAVE_MKTIME */

#ifdef HAVE_WORKING_TZSET
static void inittimezone(PyObject *module);

static PyObject *
time_tzset(PyObject *self, PyObject *unused)
{
    PyObject* m;

    m = PyImport_ImportModuleNoBlock("time");
    if (m == NULL) {
        return NULL;
    }

    tzset();

    /* Reset timezone, altzone, daylight and tzname */
    inittimezone(m);
    Py_DECREF(m);

    Py_INCREF(Py_None);
    return Py_None;
}

PyDoc_STRVAR(tzset_doc,
"tzset()\n\
\n\
Initialize, or reinitialize, the local timezone to the value stored in\n\
os.environ['TZ']. The TZ environment variable should be specified in\n\
standard Unix timezone format as documented in the tzset man page\n\
(eg. 'US/Eastern', 'Europe/Amsterdam'). Unknown timezones will silently\n\
fall back to UTC. If the TZ environment variable is not set, the local\n\
timezone is set to the systems best guess of wallclock time.\n\
Changing the TZ environment variable without calling tzset *may* change\n\
the local timezone used by methods such as localtime, but this behaviour\n\
should not be relied on.");
#endif /* HAVE_WORKING_TZSET */

static PyObject *
time_monotonic(PyObject *self, PyObject *unused)
{
    _PyTime_t t = _PyTime_GetMonotonicClock();
    return _PyFloat_FromPyTime(t);
}

PyDoc_STRVAR(monotonic_doc,
"monotonic() -> float\n\
\n\
Monotonic clock, cannot go backward.");

static PyObject *
time_monotonic_ns(PyObject *self, PyObject *unused)
{
    _PyTime_t t = _PyTime_GetMonotonicClock();
    return _PyTime_AsNanosecondsObject(t);
}

PyDoc_STRVAR(monotonic_ns_doc,
"monotonic_ns() -> int\n\
\n\
Monotonic clock, cannot go backward, as nanoseconds.");

static PyObject *
time_perf_counter(PyObject *self, PyObject *unused)
{
    return perf_counter(NULL);
}

PyDoc_STRVAR(perf_counter_doc,
"perf_counter() -> float\n\
\n\
Performance counter for benchmarking.");

static PyObject *
time_perf_counter_ns(PyObject *self, PyObject *unused)
{
    _PyTime_t t = _PyTime_GetPerfCounter();
    return _PyTime_AsNanosecondsObject(t);
}

PyDoc_STRVAR(perf_counter_ns_doc,
"perf_counter_ns() -> int\n\
\n\
Performance counter for benchmarking as nanoseconds.");

static int
_PyTime_GetProcessTimeWithInfo(_PyTime_t *tp, _Py_clock_info_t *info)
{
#if defined(MS_WINDOWS)
    HANDLE process;
    FILETIME creation_time, exit_time, kernel_time, user_time;
    ULARGE_INTEGER large;
    _PyTime_t ktime, utime, t;
    BOOL ok;

    process = GetCurrentProcess();
    ok = GetProcessTimes(process, &creation_time, &exit_time,
                         &kernel_time, &user_time);
    if (!ok) {
        PyErr_SetFromWindowsErr(0);
        return -1;
    }

    if (info) {
        info->implementation = "GetProcessTimes()";
        info->resolution = 1e-7;
        info->monotonic = 1;
        info->adjustable = 0;
    }

    large.u.LowPart = kernel_time.dwLowDateTime;
    large.u.HighPart = kernel_time.dwHighDateTime;
    ktime = large.QuadPart;

    large.u.LowPart = user_time.dwLowDateTime;
    large.u.HighPart = user_time.dwHighDateTime;
    utime = large.QuadPart;

    /* ktime and utime have a resolution of 100 nanoseconds */
    t = _PyTime_FromNanoseconds((ktime + utime) * 100);
    *tp = t;
    return 0;
#else

    /* clock_gettime */
#if defined(HAVE_CLOCK_GETTIME) \
    && (defined(CLOCK_PROCESS_CPUTIME_ID) || defined(CLOCK_PROF))
    struct timespec ts;
#ifdef CLOCK_PROF
    const clockid_t clk_id = CLOCK_PROF;
    const char *function = "clock_gettime(CLOCK_PROF)";
#else
    const clockid_t clk_id = CLOCK_PROCESS_CPUTIME_ID;
    const char *function = "clock_gettime(CLOCK_PROCESS_CPUTIME_ID)";
#endif

    if (clock_gettime(clk_id, &ts) == 0) {
        if (info) {
            struct timespec res;
            info->implementation = function;
            info->monotonic = 1;
            info->adjustable = 0;
            if (clock_getres(clk_id, &res)) {
                PyErr_SetFromErrno(PyExc_OSError);
                return -1;
            }
            info->resolution = res.tv_sec + res.tv_nsec * 1e-9;
        }

        if (_PyTime_FromTimespec(tp, &ts) < 0) {
            return -1;
        }
        return 0;
    }
#endif

    /* getrusage(RUSAGE_SELF) */
#if defined(HAVE_SYS_RESOURCE_H)
    struct rusage ru;

    if (getrusage(RUSAGE_SELF, &ru) == 0) {
        _PyTime_t utime, stime;

        if (info) {
            info->implementation = "getrusage(RUSAGE_SELF)";
            info->monotonic = 1;
            info->adjustable = 0;
            info->resolution = 1e-6;
        }

        if (_PyTime_FromTimeval(&utime, &ru.ru_utime) < 0) {
            return -1;
        }
        if (_PyTime_FromTimeval(&stime, &ru.ru_stime) < 0) {
            return -1;
        }

        _PyTime_t total = utime + utime;
        *tp = total;
        return 0;
    }
#endif

    /* times() */
#ifdef HAVE_TIMES
    struct tms t;

    if (times(&t) != (clock_t)-1) {
        static long ticks_per_second = -1;

        if (ticks_per_second == -1) {
            long freq;
#if defined(HAVE_SYSCONF) && defined(_SC_CLK_TCK)
            freq = sysconf(_SC_CLK_TCK);
            if (freq < 1) {
                freq = -1;
            }
#elif defined(HZ)
            freq = HZ;
#else
            freq = 60; /* magic fallback value; may be bogus */
#endif

            if (freq != -1) {
                /* check that _PyTime_MulDiv(t, SEC_TO_NS, ticks_per_second)
                   cannot overflow below */
#if LONG_MAX > _PyTime_MAX / SEC_TO_NS
                if ((_PyTime_t)freq > _PyTime_MAX / SEC_TO_NS) {
                    PyErr_SetString(PyExc_OverflowError,
                                    "_SC_CLK_TCK is too large");
                    return -1;
                }
#endif

                ticks_per_second = freq;
            }
        }

        if (ticks_per_second != -1) {
            if (info) {
                info->implementation = "times()";
                info->monotonic = 1;
                info->adjustable = 0;
                info->resolution = 1.0 / (double)ticks_per_second;
            }

            _PyTime_t total;
            total = _PyTime_MulDiv(t.tms_utime, SEC_TO_NS, ticks_per_second);
            total += _PyTime_MulDiv(t.tms_stime, SEC_TO_NS, ticks_per_second);
            *tp = total;
            return 0;
        }
    }
#endif

    /* clock */
    /* Currently, Python 3 requires clock() to build: see issue #22624 */
    return _PyTime_GetClockWithInfo(tp, info);
#endif
}

static PyObject *
time_process_time(PyObject *self, PyObject *unused)
{
    _PyTime_t t;
    if (_PyTime_GetProcessTimeWithInfo(&t, NULL) < 0) {
        return NULL;
    }
    return _PyFloat_FromPyTime(t);
}

PyDoc_STRVAR(process_time_doc,
"process_time() -> float\n\
\n\
Process time for profiling: sum of the kernel and user-space CPU time.");

static PyObject *
time_process_time_ns(PyObject *self, PyObject *unused)
{
    _PyTime_t t;
    if (_PyTime_GetProcessTimeWithInfo(&t, NULL) < 0) {
        return NULL;
    }
    return _PyTime_AsNanosecondsObject(t);
}

PyDoc_STRVAR(process_time_ns_doc,
"process_time() -> int\n\
\n\
Process time for profiling as nanoseconds:\n\
sum of the kernel and user-space CPU time.");

#if defined(MS_WINDOWS)
#define HAVE_THREAD_TIME
static int
_PyTime_GetThreadTimeWithInfo(_PyTime_t *tp, _Py_clock_info_t *info)
{
    HANDLE thread;
    FILETIME creation_time, exit_time, kernel_time, user_time;
    ULARGE_INTEGER large;
    _PyTime_t ktime, utime, t;
    BOOL ok;

    thread =  GetCurrentThread();
    ok = GetThreadTimes(thread, &creation_time, &exit_time,
                        &kernel_time, &user_time);
    if (!ok) {
        PyErr_SetFromWindowsErr(0);
        return -1;
    }

    if (info) {
        info->implementation = "GetThreadTimes()";
        info->resolution = 1e-7;
        info->monotonic = 1;
        info->adjustable = 0;
    }

    large.u.LowPart = kernel_time.dwLowDateTime;
    large.u.HighPart = kernel_time.dwHighDateTime;
    ktime = large.QuadPart;

    large.u.LowPart = user_time.dwLowDateTime;
    large.u.HighPart = user_time.dwHighDateTime;
    utime = large.QuadPart;

    /* ktime and utime have a resolution of 100 nanoseconds */
    t = _PyTime_FromNanoseconds((ktime + utime) * 100);
    *tp = t;
    return 0;
}

#elif defined(HAVE_CLOCK_GETTIME) && defined(CLOCK_PROCESS_CPUTIME_ID)
#define HAVE_THREAD_TIME
static int
_PyTime_GetThreadTimeWithInfo(_PyTime_t *tp, _Py_clock_info_t *info)
{
    struct timespec ts;
    const clockid_t clk_id = CLOCK_THREAD_CPUTIME_ID;
    const char *function = "clock_gettime(CLOCK_THREAD_CPUTIME_ID)";

    if (clock_gettime(clk_id, &ts)) {
        PyErr_SetFromErrno(PyExc_OSError);
        return -1;
    }
    if (info) {
        struct timespec res;
        info->implementation = function;
        info->monotonic = 1;
        info->adjustable = 0;
        if (clock_getres(clk_id, &res)) {
            PyErr_SetFromErrno(PyExc_OSError);
            return -1;
        }
        info->resolution = res.tv_sec + res.tv_nsec * 1e-9;
    }

    if (_PyTime_FromTimespec(tp, &ts) < 0) {
        return -1;
    }
    return 0;
}
#endif

#ifdef HAVE_THREAD_TIME
static PyObject *
time_thread_time(PyObject *self, PyObject *unused)
{
    _PyTime_t t;
    if (_PyTime_GetThreadTimeWithInfo(&t, NULL) < 0) {
        return NULL;
    }
    return _PyFloat_FromPyTime(t);
}

PyDoc_STRVAR(thread_time_doc,
"thread_time() -> float\n\
\n\
Thread time for profiling: sum of the kernel and user-space CPU time.");

static PyObject *
time_thread_time_ns(PyObject *self, PyObject *unused)
{
    _PyTime_t t;
    if (_PyTime_GetThreadTimeWithInfo(&t, NULL) < 0) {
        return NULL;
    }
    return _PyTime_AsNanosecondsObject(t);
}

PyDoc_STRVAR(thread_time_ns_doc,
"thread_time() -> int\n\
\n\
Thread time for profiling as nanoseconds:\n\
sum of the kernel and user-space CPU time.");
#endif


static void
inittimezone(PyObject *m) {
    /* This code moved from inittime wholesale to allow calling it from
    time_tzset. In the future, some parts of it can be moved back
    (for platforms that don't HAVE_WORKING_TZSET, when we know what they
    are), and the extraneous calls to tzset(3) should be removed.
    I haven't done this yet, as I don't want to change this code as
    little as possible when introducing the time.tzset and time.tzsetwall
    methods. This should simply be a method of doing the following once,
    at the top of this function and removing the call to tzset() from
    time_tzset():

        #ifdef HAVE_TZSET
        tzset()
        #endif

    And I'm lazy and hate C so nyer.
     */
#if defined(HAVE_TZNAME) && !defined(__GLIBC__) && !defined(__CYGWIN__)
    tzset();
#ifdef PYOS_OS2
    PyModule_AddIntConstant(m, "timezone", _timezone);
#else /* !PYOS_OS2 */
    PyModule_AddIntConstant(m, "timezone", timezone);
#endif /* PYOS_OS2 */
#ifdef HAVE_ALTZONE
    PyModule_AddIntConstant(m, "altzone", altzone);
#else
#ifdef PYOS_OS2
    PyModule_AddIntConstant(m, "altzone", _timezone-3600);
#else /* !PYOS_OS2 */
    PyModule_AddIntConstant(m, "altzone", timezone-3600);
#endif /* PYOS_OS2 */
#endif
    PyModule_AddIntConstant(m, "daylight", daylight);
    PyModule_AddObject(m, "tzname",
                       Py_BuildValue("(zz)", tzname[0], tzname[1]));
#else /* !HAVE_TZNAME || __GLIBC__ || __CYGWIN__*/
#ifdef HAVE_STRUCT_TM_TM_ZONE
    {
#define YEAR ((time_t)((365 * 24 + 6) * 3600))
        time_t t;
        struct tm *p;
        long janzone, julyzone;
        char janname[10], julyname[10];
        t = (time((time_t *)0) / YEAR) * YEAR;
        p = localtime(&t);
        janzone = -p->tm_gmtoff;
        strncpy(janname, p->tm_zone ? p->tm_zone : "   ", 9);
        janname[9] = '\0';
        t += YEAR/2;
        p = localtime(&t);
        julyzone = -p->tm_gmtoff;
        strncpy(julyname, p->tm_zone ? p->tm_zone : "   ", 9);
        julyname[9] = '\0';

        if( janzone < julyzone ) {
            /* DST is reversed in the southern hemisphere */
            PyModule_AddIntConstant(m, "timezone", julyzone);
            PyModule_AddIntConstant(m, "altzone", janzone);
            PyModule_AddIntConstant(m, "daylight",
                                    janzone != julyzone);
            PyModule_AddObject(m, "tzname",
                               Py_BuildValue("(zz)",
                                             julyname, janname));
        } else {
            PyModule_AddIntConstant(m, "timezone", janzone);
            PyModule_AddIntConstant(m, "altzone", julyzone);
            PyModule_AddIntConstant(m, "daylight",
                                    janzone != julyzone);
            PyModule_AddObject(m, "tzname",
                               Py_BuildValue("(zz)",
                                             janname, julyname));
        }
    }
#else
#endif /* HAVE_STRUCT_TM_TM_ZONE */
#ifdef __CYGWIN__
    tzset();
    PyModule_AddIntConstant(m, "timezone", _timezone);
    PyModule_AddIntConstant(m, "altzone", _timezone-3600);
    PyModule_AddIntConstant(m, "daylight", _daylight);
    PyModule_AddObject(m, "tzname",
                       Py_BuildValue("(zz)", _tzname[0], _tzname[1]));
#endif /* __CYGWIN__ */
#endif /* !HAVE_TZNAME || __GLIBC__ || __CYGWIN__*/
}

static PyMethodDef time_methods[] = {
    {"time",            time_time, METH_NOARGS, time_doc},
    {"time_ns",         time_time_ns, METH_NOARGS, time_ns_doc},
#ifdef PYCLOCK
    {"clock",           time_clock, METH_NOARGS, clock_doc},
#endif
#ifdef HAVE_CLOCK_GETTIME
    {"clock_gettime",   time_clock_gettime, METH_VARARGS, clock_gettime_doc},
    {"clock_gettime_ns",time_clock_gettime_ns, METH_VARARGS, clock_gettime_ns_doc},
#endif
#ifdef HAVE_CLOCK_SETTIME
    {"clock_settime",   time_clock_settime, METH_VARARGS, clock_settime_doc},
    {"clock_settime_ns",time_clock_settime_ns, METH_VARARGS, clock_settime_ns_doc},
#endif
#ifdef HAVE_CLOCK_GETRES
    {"clock_getres",    time_clock_getres, METH_VARARGS, clock_getres_doc},
#endif
#ifdef HAVE_PTHREAD_GETCPUCLOCKID
    {"pthread_getcpuclockid", time_pthread_getcpuclockid, METH_VARARGS, pthread_getcpuclockid_doc},
#endif
    {"sleep",           time_sleep, METH_VARARGS, sleep_doc},
    {"gmtime",          time_gmtime, METH_VARARGS, gmtime_doc},
    {"localtime",       time_localtime, METH_VARARGS, localtime_doc},
    {"asctime",         time_asctime, METH_VARARGS, asctime_doc},
    {"ctime",           time_ctime, METH_VARARGS, ctime_doc},
#ifdef HAVE_MKTIME
    {"mktime",          time_mktime, METH_O, mktime_doc},
#endif
#ifdef HAVE_STRFTIME
    {"strftime",        time_strftime, METH_VARARGS, strftime_doc},
#endif
    {"strptime",        time_strptime, METH_VARARGS, strptime_doc},
#ifdef HAVE_WORKING_TZSET
    {"tzset",           time_tzset, METH_NOARGS, tzset_doc},
#endif
    {"monotonic",       time_monotonic, METH_NOARGS, monotonic_doc},
    {"monotonic_ns",    time_monotonic_ns, METH_NOARGS, monotonic_ns_doc},
    {"process_time",    time_process_time, METH_NOARGS, process_time_doc},
    {"process_time_ns", time_process_time_ns, METH_NOARGS, process_time_ns_doc},
#ifdef HAVE_THREAD_TIME
    {"thread_time",     time_thread_time, METH_NOARGS, thread_time_doc},
    {"thread_time_ns",  time_thread_time_ns, METH_NOARGS, thread_time_ns_doc},
#endif

    {"perf_counter",    time_perf_counter, METH_NOARGS, perf_counter_doc},
    {"perf_counter_ns", time_perf_counter_ns, METH_NOARGS, perf_counter_ns_doc},
    {NULL,              NULL}           /* sentinel */
};


PyDoc_STRVAR(module_doc,
"This module provides various functions to manipulate time values.\n\
\n\
There are two standard representations of time.  One is the number\n\
of seconds since the Epoch, in UTC (a.k.a. GMT).  It may be an integer\n\
or a floating point number (to represent fractions of seconds).\n\
The Epoch is system-defined; on Unix, it is generally January 1st, 1970.\n\
The actual value can be retrieved by calling gmtime(0).\n\
\n\
The other representation is a tuple of 9 integers giving local time.\n\
The tuple items are:\n\
  year (four digits, e.g. 1998)\n\
  month (1-12)\n\
  day (1-31)\n\
  hours (0-23)\n\
  minutes (0-59)\n\
  seconds (0-59)\n\
  weekday (0-6, Monday is 0)\n\
  Julian day (day in the year, 1-366)\n\
  DST (Daylight Savings Time) flag (-1, 0 or 1)\n\
If the DST flag is 0, the time is given in the regular time zone;\n\
if it is 1, the time is given in the DST time zone;\n\
if it is -1, mktime() should guess based on the date and time.\n\
\n\
Variables:\n\
\n\
timezone -- difference in seconds between UTC and local standard time\n\
altzone -- difference in  seconds between UTC and local DST time\n\
daylight -- whether local time should reflect DST\n\
tzname -- tuple of (standard time zone name, DST time zone name)\n\
\n\
Functions:\n\
\n\
time() -- return current time in seconds since the Epoch as a float\n\
clock() -- return CPU time since process start as a float\n\
sleep() -- delay for a number of seconds given as a float\n\
gmtime() -- convert seconds since Epoch to UTC tuple\n\
localtime() -- convert seconds since Epoch to local time tuple\n\
asctime() -- convert time tuple to string\n\
ctime() -- convert time in seconds to string\n\
mktime() -- convert local time tuple to seconds since Epoch\n\
strftime() -- convert time tuple to string according to format specification\n\
strptime() -- parse string to time tuple according to format specification\n\
tzset() -- change the local timezone");

PyMODINIT_FUNC
inittime(void)
{
    PyObject *m;
    char *p;
    m = Py_InitModule3("time", time_methods, module_doc);
    if (m == NULL)
        return;

    /* Accept 2-digit dates unless PYTHONY2K is set and non-empty */
    p = Py_GETENV("PYTHONY2K");
    PyModule_AddIntConstant(m, "accept2dyear", (long) (!p || !*p));
    /* If an embedded interpreter is shutdown and reinitialized the old
       moddict was not decrefed on shutdown and the next import of this
       module leads to a leak.  Conditionally decref here to prevent that.
    */
    Py_XDECREF(moddict);
    /* Squirrel away the module's dictionary for the y2k check */
    moddict = PyModule_GetDict(m);
    Py_INCREF(moddict);

    /* Set, or reset, module variables like time.timezone */
    inittimezone(m);

#ifdef CLOCK_REALTIME
    PyModule_AddIntMacro(m, CLOCK_REALTIME);
#endif
#ifdef CLOCK_MONOTONIC
    PyModule_AddIntMacro(m, CLOCK_MONOTONIC);
#endif
#ifdef CLOCK_MONOTONIC_RAW
    PyModule_AddIntMacro(m, CLOCK_MONOTONIC_RAW);
#endif
#ifdef CLOCK_HIGHRES
    PyModule_AddIntMacro(m, CLOCK_HIGHRES);
#endif
#ifdef CLOCK_PROCESS_CPUTIME_ID
    PyModule_AddIntMacro(m, CLOCK_PROCESS_CPUTIME_ID);
#endif
#ifdef CLOCK_THREAD_CPUTIME_ID
    PyModule_AddIntMacro(m, CLOCK_THREAD_CPUTIME_ID);
#endif
#ifdef CLOCK_PROF
    PyModule_AddIntMacro(m, CLOCK_PROF);
#endif
#ifdef CLOCK_BOOTTIME
    PyModule_AddIntMacro(m, CLOCK_BOOTTIME);
#endif
#ifdef CLOCK_UPTIME
    PyModule_AddIntMacro(m, CLOCK_UPTIME);
#endif

#ifdef MS_WINDOWS
    /* Helper to allow interrupts for Windows.
       If Ctrl+C event delivered while not sleeping
       it will be ignored.
    */
    main_thread = PyThread_get_thread_ident();
    hInterruptEvent = CreateEvent(NULL, TRUE, FALSE, NULL);
    SetConsoleCtrlHandler( PyCtrlHandler, TRUE);
#endif /* MS_WINDOWS */
    if (!initialized) {
        PyStructSequence_InitType(&StructTimeType,
                                  &struct_time_type_desc);
    }
    Py_INCREF(&StructTimeType);
    PyModule_AddObject(m, "struct_time", (PyObject*) &StructTimeType);

    initialized = 1;
}

/* Implement floattime() for various platforms */

static double
floattime(void)
{
    /* There are three ways to get the time:
      (1) gettimeofday() -- resolution in microseconds
      (2) ftime() -- resolution in milliseconds
      (3) time() -- resolution in seconds
      In all cases the return value is a float in seconds.
      Since on some systems (e.g. SCO ODT 3.0) gettimeofday() may
      fail, so we fall back on ftime() or time().
      Note: clock resolution does not imply clock accuracy! */
#ifdef HAVE_GETTIMEOFDAY
    {
        struct timeval t;
#ifdef GETTIMEOFDAY_NO_TZ
        if (gettimeofday(&t) == 0)
            return (double)t.tv_sec + t.tv_usec*0.000001;
#else /* !GETTIMEOFDAY_NO_TZ */
        if (gettimeofday(&t, (struct timezone *)NULL) == 0)
            return (double)t.tv_sec + t.tv_usec*0.000001;
#endif /* !GETTIMEOFDAY_NO_TZ */
    }

#endif /* !HAVE_GETTIMEOFDAY */
    {
#if defined(HAVE_FTIME)
        struct timeb t;
        ftime(&t);
        return (double)t.time + (double)t.millitm * (double)0.001;
#else /* !HAVE_FTIME */
        time_t secs;
        time(&secs);
        return (double)secs;
#endif /* !HAVE_FTIME */
    }
}


/* Implement floatsleep() for various platforms.
   When interrupted (or when another error occurs), return -1 and
   set an exception; else return 0. */

static int
floatsleep(double secs)
{
/* XXX Should test for MS_WINDOWS first! */
#if defined(HAVE_SELECT) && !defined(__BEOS__) && !defined(__EMX__)
    struct timeval t;
    double frac;
    frac = fmod(secs, 1.0);
    secs = floor(secs);
    t.tv_sec = (long)secs;
    t.tv_usec = (long)(frac*1000000.0);
    Py_BEGIN_ALLOW_THREADS
    if (select(0, (fd_set *)0, (fd_set *)0, (fd_set *)0, &t) != 0) {
#ifdef EINTR
        if (errno != EINTR) {
#else
        if (1) {
#endif
            Py_BLOCK_THREADS
            PyErr_SetFromErrno(PyExc_IOError);
            return -1;
        }
    }
    Py_END_ALLOW_THREADS
#elif defined(__WATCOMC__) && !defined(__QNX__)
    /* XXX Can't interrupt this sleep */
    Py_BEGIN_ALLOW_THREADS
    delay((int)(secs * 1000 + 0.5));  /* delay() uses milliseconds */
    Py_END_ALLOW_THREADS
#elif defined(MS_WINDOWS)
    {
        double millisecs = secs * 1000.0;
        unsigned long ul_millis;

        if (millisecs > (double)ULONG_MAX) {
            PyErr_SetString(PyExc_OverflowError,
                            "sleep length is too large");
            return -1;
        }
        Py_BEGIN_ALLOW_THREADS
        /* Allow sleep(0) to maintain win32 semantics, and as decreed
         * by Guido, only the main thread can be interrupted.
         */
        ul_millis = (unsigned long)millisecs;
        if (ul_millis == 0 ||
            main_thread != PyThread_get_thread_ident())
            Sleep(ul_millis);
        else {
            DWORD rc;
            ResetEvent(hInterruptEvent);
            rc = WaitForSingleObject(hInterruptEvent, ul_millis);
            if (rc == WAIT_OBJECT_0) {
                /* Yield to make sure real Python signal
                 * handler called.
                 */
                Sleep(1);
                Py_BLOCK_THREADS
                errno = EINTR;
                PyErr_SetFromErrno(PyExc_IOError);
                return -1;
            }
        }
        Py_END_ALLOW_THREADS
    }
#elif defined(PYOS_OS2)
    /* This Sleep *IS* Interruptable by Exceptions */
    Py_BEGIN_ALLOW_THREADS
    if (DosSleep(secs * 1000) != NO_ERROR) {
        Py_BLOCK_THREADS
        PyErr_SetFromErrno(PyExc_IOError);
        return -1;
    }
    Py_END_ALLOW_THREADS
#elif defined(__BEOS__)
    /* This sleep *CAN BE* interrupted. */
    {
        if( secs <= 0.0 ) {
            return;
        }

        Py_BEGIN_ALLOW_THREADS
        /* BeOS snooze() is in microseconds... */
        if( snooze( (bigtime_t)( secs * 1000.0 * 1000.0 ) ) == B_INTERRUPTED ) {
            Py_BLOCK_THREADS
            PyErr_SetFromErrno( PyExc_IOError );
            return -1;
        }
        Py_END_ALLOW_THREADS
    }
#elif defined(RISCOS)
    if (secs <= 0.0)
        return 0;
    Py_BEGIN_ALLOW_THREADS
    /* This sleep *CAN BE* interrupted. */
    if ( riscos_sleep(secs) )
        return -1;
    Py_END_ALLOW_THREADS
#elif defined(PLAN9)
    {
        double millisecs = secs * 1000.0;
        if (millisecs > (double)LONG_MAX) {
            PyErr_SetString(PyExc_OverflowError, "sleep length is too large");
            return -1;
        }
        /* This sleep *CAN BE* interrupted. */
        Py_BEGIN_ALLOW_THREADS
        if(sleep((long)millisecs) < 0){
            Py_BLOCK_THREADS
            PyErr_SetFromErrno(PyExc_IOError);
            return -1;
        }
        Py_END_ALLOW_THREADS
    }
#else
    /* XXX Can't interrupt this sleep */
    Py_BEGIN_ALLOW_THREADS
    sleep((int)secs);
    Py_END_ALLOW_THREADS
#endif

    return 0;
}

/* export floattime to socketmodule.c */
PyAPI_FUNC(double)
_PyTime_FloatTime(void)
{
    return floattime();
}
