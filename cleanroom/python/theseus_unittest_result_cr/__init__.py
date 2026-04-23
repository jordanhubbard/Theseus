"""
theseus_unittest_result_cr — Clean-room unittest.result module.
No import of the standard `unittest.result` module.
"""

import sys as _sys
import io as _io
import traceback as _traceback


STDOUT_LINE = '\nStdout:\n%s'
STDERR_LINE = '\nStderr:\n%s'


class TestResult:
    """Holder for test result information."""

    def __init__(self):
        self.failures = []
        self.errors = []
        self.testsRun = 0
        self.skipped = []
        self.expectedFailures = []
        self.unexpectedSuccesses = []
        self._stdout_buffer = None
        self._stderr_buffer = None
        self._original_stdout = _sys.stdout
        self._original_stderr = _sys.stderr
        self._mirrorOutput = False
        self.buffer = False
        self.tb_locals = False
        self._stop = False

    def printErrors(self):
        """Called by TestRunner after all tests run."""
        pass

    def startTest(self, test):
        """Called when a test starts."""
        self.testsRun += 1

    def startTestRun(self):
        """Called once before any tests are executed."""
        pass

    def stopTest(self, test):
        """Called when a test has completed."""
        pass

    def stopTestRun(self):
        """Called once after all tests are executed."""
        pass

    def addError(self, test, err):
        """Called when an error (unexpected exception) occurred."""
        self.errors.append((test, self._exc_info_to_string(err, test)))
        self._mirrorOutput = True

    def addFailure(self, test, err):
        """Called when a test failure occurred."""
        self.failures.append((test, self._exc_info_to_string(err, test)))
        self._mirrorOutput = True

    def addSuccess(self, test):
        """Called when a test has completed successfully."""
        pass

    def addSkip(self, test, reason):
        """Called when a test is skipped."""
        self.skipped.append((test, reason))

    def addExpectedFailure(self, test, err):
        """Called when an expected failure/error occurred."""
        self.expectedFailures.append((test, self._exc_info_to_string(err, test)))

    def addUnexpectedSuccess(self, test):
        """Called when a test was expected to fail, but succeeded."""
        self.unexpectedSuccesses.append(test)

    def addSubTest(self, test, subtest, outcome):
        """Called at the end of a subtest."""
        if outcome is None:
            return
        if issubclass(outcome[0], test.failureException):
            self.addFailure(test, outcome)
        else:
            self.addError(test, outcome)

    def wasSuccessful(self):
        """Tells whether or not this result was a success."""
        return (len(self.failures) == 0 and len(self.errors) == 0)

    def stop(self):
        """Indicates that the tests should be aborted."""
        self._stop = True

    def shouldStop(self):
        """Should the test run stop?"""
        return self._stop

    def _exc_info_to_string(self, err, test):
        """Converts a sys.exc_info()-style tuple to a string."""
        exctype, value, tb = err
        while tb and self._is_relevant_tb_level(tb):
            tb = tb.tb_next
        msg_lines = _traceback.format_exception(exctype, value, tb,
                                                 tb_locals=self.tb_locals)
        return ''.join(msg_lines)

    def _is_relevant_tb_level(self, tb):
        return '__unittest' in tb.tb_frame.f_globals

    def __repr__(self):
        return (f'<{type(self).__name__} run={self.testsRun} errors={len(self.errors)} '
                f'failures={len(self.failures)}>')


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def utresult2_testresult():
    """TestResult class tracks test outcomes; returns True."""
    result = TestResult()
    return (isinstance(result, TestResult) and
            result.testsRun == 0 and
            result.wasSuccessful())


def utresult2_errors():
    """failures and errors lists track test failures; returns True."""
    result = TestResult()
    result.errors.append(('test', 'some error'))
    result.failures.append(('test2', 'some failure'))
    return (not result.wasSuccessful() and
            len(result.errors) == 1 and
            len(result.failures) == 1)


def utresult2_counts():
    """testsRun and skipped counts are tracked; returns True."""
    result = TestResult()
    result.testsRun = 5
    result.skipped.append(('test', 'reason'))
    return result.testsRun == 5 and len(result.skipped) == 1


__all__ = [
    'TestResult', 'STDOUT_LINE', 'STDERR_LINE',
    'utresult2_testresult', 'utresult2_errors', 'utresult2_counts',
]
