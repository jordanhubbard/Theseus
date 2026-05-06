"""Clean-room implementation of unittest.result.

Provides TestResult class and self-verifying invariant functions.
Does not import unittest or unittest.result.
"""

import sys
import traceback
import functools


__unittest = True


def failfast(method):
    """Decorator that calls self.stop() if self.failfast is set."""
    @functools.wraps(method)
    def inner(self, *args, **kw):
        if getattr(self, 'failfast', False):
            self.stop()
        return method(self, *args, **kw)
    return inner


STDOUT_LINE = '\nStdout:\n%s'
STDERR_LINE = '\nStderr:\n%s'


class _WritelnDecorator:
    """File-like object that adds a writeln method."""
    def __init__(self, stream):
        self.stream = stream

    def __getattr__(self, attr):
        if attr in ('stream', '__getstate__'):
            raise AttributeError(attr)
        return getattr(self.stream, attr)

    def writeln(self, arg=None):
        if arg:
            self.write(arg)
        self.write('\n')


class TestResult(object):
    """Holder for test result information.

    Test results are automatically managed by the TestCase and TestSuite
    classes, and do not need to be explicitly manipulated by writers of
    tests.

    Each instance holds the total number of tests run, and collections of
    failures and errors that occurred among those test runs. The collections
    contain tuples of (testcase, exceptioninfo), where exceptioninfo is the
    formatted traceback of the error that occurred.
    """
    _previousTestClass = None
    _testRunEntered = False
    _moduleSetUpFailed = False

    def __init__(self, stream=None, descriptions=None, verbosity=None):
        self.failfast = False
        self.failures = []
        self.errors = []
        self.testsRun = 0
        self.skipped = []
        self.expectedFailures = []
        self.unexpectedSuccesses = []
        self.shouldStop = False
        self.buffer = False
        self.tb_locals = False
        self._stdout_buffer = None
        self._stderr_buffer = None
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        self._mirrorOutput = False

    def printErrors(self):
        "Called by TestRunner after test run"
        pass

    def startTest(self, test):
        "Called when the given test is about to be run"
        self.testsRun += 1
        self._mirrorOutput = False
        self._setupStdout()

    def _setupStdout(self):
        if self.buffer:
            try:
                from io import StringIO
            except ImportError:
                return
            if self._stderr_buffer is None:
                self._stderr_buffer = StringIO()
                self._stdout_buffer = StringIO()
            sys.stdout = self._stdout_buffer
            sys.stderr = self._stderr_buffer

    def startTestRun(self):
        """Called once before any tests are executed.

        See startTest for a method called before each test.
        """
        pass

    def stopTest(self, test):
        """Called when the given test has been run"""
        self._restoreStdout()
        self._mirrorOutput = False

    def _restoreStdout(self):
        if self.buffer:
            if self._mirrorOutput:
                output = self._stdout_buffer.getvalue() if self._stdout_buffer else ''
                error = self._stderr_buffer.getvalue() if self._stderr_buffer else ''
                if output:
                    if not output.endswith('\n'):
                        output += '\n'
                    self._original_stdout.write(STDOUT_LINE % output)
                if error:
                    if not error.endswith('\n'):
                        error += '\n'
                    self._original_stderr.write(STDERR_LINE % error)
            sys.stdout = self._original_stdout
            sys.stderr = self._original_stderr
            if self._stdout_buffer is not None:
                self._stdout_buffer.seek(0)
                self._stdout_buffer.truncate()
            if self._stderr_buffer is not None:
                self._stderr_buffer.seek(0)
                self._stderr_buffer.truncate()

    def stopTestRun(self):
        """Called once after all tests are executed.

        See stopTest for a method called after each test.
        """
        pass

    @failfast
    def addError(self, test, err):
        """Called when an error has occurred. 'err' is a tuple of values as
        returned by sys.exc_info().
        """
        self.errors.append((test, self._exc_info_to_string(err, test)))
        self._mirrorOutput = True

    @failfast
    def addFailure(self, test, err):
        """Called when an error has occurred. 'err' is a tuple of values as
        returned by sys.exc_info()."""
        self.failures.append((test, self._exc_info_to_string(err, test)))
        self._mirrorOutput = True

    def addSubTest(self, test, subtest, err):
        """Called at the end of a subtest.
        'err' is None if the subtest ended successfully, otherwise it's a
        tuple of values as returned by sys.exc_info().
        """
        if err is not None:
            if getattr(self, 'failfast', False):
                self.stop()
            failure_exc = getattr(test, 'failureException', AssertionError)
            if issubclass(err[0], failure_exc):
                errors = self.failures
            else:
                errors = self.errors
            errors.append((subtest, self._exc_info_to_string(err, test)))
            self._mirrorOutput = True

    def addSuccess(self, test):
        "Called when a test has completed successfully"
        pass

    def addSkip(self, test, reason):
        """Called when a test is skipped."""
        self.skipped.append((test, reason))

    def addExpectedFailure(self, test, err):
        """Called when an expected failure/error occurred."""
        self.expectedFailures.append(
            (test, self._exc_info_to_string(err, test)))

    @failfast
    def addUnexpectedSuccess(self, test):
        """Called when a test was expected to fail, but succeed."""
        self.unexpectedSuccesses.append(test)

    def wasSuccessful(self):
        """Tells whether or not this result was a success."""
        # The hasattr check is used for test_result's OldResult test. That
        # way this method works with old-style results that don't have
        # unexpectedSuccesses.
        return ((len(self.failures) == len(self.errors) == 0) and
                (not hasattr(self, 'unexpectedSuccesses') or
                 len(self.unexpectedSuccesses) == 0))

    def stop(self):
        """Indicates that the tests should be aborted."""
        self.shouldStop = True

    def _exc_info_to_string(self, err, test):
        """Converts a sys.exc_info()-style tuple of values into a string."""
        exctype, value, tb = err
        # Skip test runner traceback levels
        while tb and self._is_relevant_tb_level(tb):
            tb = tb.tb_next

        if exctype is getattr(test, 'failureException', None):
            # Skip assert*() traceback levels
            length = self._count_relevant_tb_levels(tb)
        else:
            length = None
        tb_e = traceback.TracebackException(
            exctype, value, tb, limit=length, capture_locals=self.tb_locals)
        msgLines = list(tb_e.format())

        if self.buffer:
            output = (self._stdout_buffer.getvalue()
                      if self._stdout_buffer is not None else '')
            error = (self._stderr_buffer.getvalue()
                     if self._stderr_buffer is not None else '')
            if output:
                if not output.endswith('\n'):
                    output += '\n'
                msgLines.append(STDOUT_LINE % output)
            if error:
                if not error.endswith('\n'):
                    error += '\n'
                msgLines.append(STDERR_LINE % error)
        return ''.join(msgLines)

    def _is_relevant_tb_level(self, tb):
        return '__unittest' in tb.tb_frame.f_globals

    def _count_relevant_tb_levels(self, tb):
        length = 0
        while tb and not self._is_relevant_tb_level(tb):
            length += 1
            tb = tb.tb_next
        return length

    def __repr__(self):
        return ("<%s run=%i errors=%i failures=%i>" %
                (type(self).__name__, self.testsRun, len(self.errors),
                 len(self.failures)))


# ---------------------------------------------------------------------------
# Self-verifying invariant functions
# ---------------------------------------------------------------------------

class _FakeTest(object):
    """Minimal test stand-in used by the invariant functions."""
    failureException = AssertionError

    def __init__(self, name="fake_test"):
        self._name = name

    def __str__(self):
        return self._name

    def __repr__(self):
        return "<_FakeTest %s>" % self._name


def utresult2_testresult():
    """Verify default-constructed TestResult state and basic behaviors."""
    try:
        r = TestResult()
        # Initial state.
        if r.testsRun != 0:
            return False
        if r.failures != []:
            return False
        if r.errors != []:
            return False
        if r.skipped != []:
            return False
        if r.expectedFailures != []:
            return False
        if r.unexpectedSuccesses != []:
            return False
        if r.shouldStop is not False:
            return False
        if r.failfast is not False:
            return False
        if r.buffer is not False:
            return False
        if not r.wasSuccessful():
            return False

        # stop() flips shouldStop.
        r.stop()
        if r.shouldStop is not True:
            return False

        # Constructor should accept stream/descriptions/verbosity kwargs.
        r2 = TestResult(stream=None, descriptions=None, verbosity=2)
        if r2.testsRun != 0:
            return False
        if not r2.wasSuccessful():
            return False

        # repr should mention the class name and counts.
        rep = repr(r2)
        if 'TestResult' not in rep:
            return False
        if 'run=0' not in rep or 'errors=0' not in rep or 'failures=0' not in rep:
            return False

        # printErrors / startTestRun / stopTestRun must be callable no-ops.
        r2.printErrors()
        r2.startTestRun()
        r2.stopTestRun()
        return True
    except Exception:
        return False


def utresult2_errors():
    """Verify error/failure/skip/expectedFailure/unexpectedSuccess flow."""
    try:
        r = TestResult()
        test = _FakeTest("err_test")

        # addError: should append to errors and make wasSuccessful False.
        r.startTest(test)
        try:
            raise ValueError("boom")
        except ValueError:
            err = sys.exc_info()
        r.addError(test, err)
        r.stopTest(test)

        if len(r.errors) != 1:
            return False
        if r.errors[0][0] is not test:
            return False
        if not isinstance(r.errors[0][1], str):
            return False
        if "ValueError" not in r.errors[0][1]:
            return False
        if r.wasSuccessful():
            return False

        # addFailure: should append to failures.
        r.startTest(test)
        try:
            raise AssertionError("nope")
        except AssertionError:
            err = sys.exc_info()
        r.addFailure(test, err)
        r.stopTest(test)
        if len(r.failures) != 1:
            return False
        if "AssertionError" not in r.failures[0][1]:
            return False

        # addSkip should record (test, reason).
        r.addSkip(test, "skipping it")
        if len(r.skipped) != 1:
            return False
        if r.skipped[0] != (test, "skipping it"):
            return False

        # addExpectedFailure should record formatted traceback.
        try:
            raise RuntimeError("expected")
        except RuntimeError:
            err = sys.exc_info()
        r.addExpectedFailure(test, err)
        if len(r.expectedFailures) != 1:
            return False
        if "RuntimeError" not in r.expectedFailures[0][1]:
            return False

        # addUnexpectedSuccess should record the test.
        r.addUnexpectedSuccess(test)
        if len(r.unexpectedSuccesses) != 1:
            return False
        if r.unexpectedSuccesses[0] is not test:
            return False
        if r.wasSuccessful():
            return False

        # failfast should cause stop() on addError/addFailure.
        r2 = TestResult()
        r2.failfast = True
        try:
            raise ValueError("ff")
        except ValueError:
            err = sys.exc_info()
        r2.addError(test, err)
        if r2.shouldStop is not True:
            return False

        r3 = TestResult()
        r3.failfast = True
        try:
            raise AssertionError("ff2")
        except AssertionError:
            err = sys.exc_info()
        r3.addFailure(test, err)
        if r3.shouldStop is not True:
            return False

        # addSubTest with None err should be a silent success.
        r4 = TestResult()
        r4.addSubTest(test, test, None)
        if r4.errors or r4.failures:
            return False

        # addSubTest with AssertionError -> failures.
        try:
            raise AssertionError("sub")
        except AssertionError:
            err = sys.exc_info()
        r4.addSubTest(test, test, err)
        if len(r4.failures) != 1:
            return False

        # addSubTest with non-AssertionError -> errors.
        try:
            raise ValueError("sub-err")
        except ValueError:
            err = sys.exc_info()
        r4.addSubTest(test, test, err)
        if len(r4.errors) != 1:
            return False

        return True
    except Exception:
        return False


def utresult2_counts():
    """Verify testsRun counter, addSuccess no-op, and overall accounting."""
    try:
        r = TestResult()
        test = _FakeTest("count_test")

        # 5 successful tests.
        for _ in range(5):
            r.startTest(test)
            r.addSuccess(test)
            r.stopTest(test)
        if r.testsRun != 5:
            return False
        if r.errors or r.failures or r.skipped:
            return False
        if not r.wasSuccessful():
            return False

        # Add an error and re-check counts/state.
        r.startTest(test)
        try:
            raise KeyError("k")
        except KeyError:
            err = sys.exc_info()
        r.addError(test, err)
        r.stopTest(test)
        if r.testsRun != 6:
            return False
        if len(r.errors) != 1:
            return False
        if r.wasSuccessful():
            return False

        # Add a skip; testsRun should still increase via startTest.
        r.startTest(test)
        r.addSkip(test, "meh")
        r.stopTest(test)
        if r.testsRun != 7:
            return False
        if len(r.skipped) != 1:
            return False

        # Repr reflects current counts.
        rep = repr(r)
        if 'run=7' not in rep:
            return False
        if 'errors=1' not in rep:
            return False
        if 'failures=0' not in rep:
            return False

        # Fresh result is independent (no shared mutable defaults).
        r2 = TestResult()
        if r2.testsRun != 0:
            return False
        if r2.errors or r2.failures or r2.skipped:
            return False
        # Ensure lists are not aliased between instances.
        r.errors.append("sentinel")
        if "sentinel" in r2.errors:
            return False

        return True
    except Exception:
        return False


__all__ = [
    'TestResult',
    'failfast',
    'utresult2_testresult',
    'utresult2_errors',
    'utresult2_counts',
]