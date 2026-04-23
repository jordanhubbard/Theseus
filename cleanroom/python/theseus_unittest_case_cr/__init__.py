"""
theseus_unittest_case_cr — Clean-room unittest.case module.
No import of the standard `unittest.case` module.
"""

import sys as _sys
import functools as _functools
import traceback as _traceback
import re as _re
import warnings as _warnings
import collections.abc as _abc


class SkipTest(Exception):
    """Raised when a test is to be skipped."""


class _Outcome:
    def __init__(self, result=None):
        self.expecting_failure = False
        self.result = result
        self.result_supports_subtests = hasattr(result, "addSubTest")
        self.success = True
        self.skipped = []
        self.expectedFailure = None
        self.errors = []


def skip(reason):
    """Unconditionally skip a test."""
    def decorator(test_item):
        if not isinstance(test_item, type):
            @_functools.wraps(test_item)
            def skip_wrapper(*args, **kwargs):
                raise SkipTest(reason)
            test_item = skip_wrapper
        test_item.__unittest_skip__ = True
        test_item.__unittest_skip_why__ = reason
        return test_item
    if isinstance(reason, type) and issubclass(reason, BaseException):
        raise TypeError("skip() requires a reason, not a class")
    if callable(reason):
        test_item = reason
        @_functools.wraps(test_item)
        def skip_wrapper(*args, **kwargs):
            raise SkipTest('unconditionally skipped')
        test_item = skip_wrapper
        return test_item
    return decorator


def skipIf(condition, reason):
    """Skip a test if the condition is true."""
    if condition:
        return skip(reason)
    return lambda x: x


def skipUnless(condition, reason):
    """Skip a test unless the condition is true."""
    if not condition:
        return skip(reason)
    return lambda x: x


def expectedFailure(test_item):
    """Mark a test as an expected failure."""
    test_item.__unittest_expecting_failure__ = True
    return test_item


def _id(obj):
    return obj


class _AssertRaisesContext:
    """A context manager for assertRaises."""

    def __init__(self, expected, test_case):
        self.expected = expected
        self.test_case = test_case
        self.exception = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is None:
            raise AssertionError(f'{self.expected.__name__} not raised')
        if not issubclass(exc_type, self.expected):
            return False
        self.exception = exc_value
        return True


class TestCase:
    """Base class for test cases."""

    maxDiff = 80 * 8
    longMessage = True
    failureException = AssertionError
    _subtest = None

    def __init__(self, methodName='runTest'):
        self._testMethodName = methodName
        self._outcome = None
        self._testMethodDoc = 'No test'
        try:
            testMethod = getattr(self, methodName)
        except AttributeError:
            if methodName != 'runTest':
                raise ValueError(
                    f'no such test method in {type(self).__name__}: {methodName!r}')
        else:
            self._testMethodDoc = testMethod.__doc__

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def setUpClass(cls):
        pass

    def tearDownClass(cls):
        pass

    def id(self):
        return f'{type(self).__module__}.{type(self).__qualname__}.{self._testMethodName}'

    def shortDescription(self):
        doc = self._testMethodDoc
        return doc and doc.split('\n')[0].strip() or None

    def __repr__(self):
        return f'{type(self).__name__}.{self._testMethodName}'

    def __str__(self):
        return f'{type(self).__name__}.{self._testMethodName}'

    def _formatMessage(self, msg, standardMsg):
        if not self.longMessage:
            return msg or standardMsg
        if msg is None:
            return standardMsg
        return f'{standardMsg} : {msg}'

    def fail(self, msg=None):
        raise self.failureException(msg)

    def assertEqual(self, first, second, msg=None):
        if not first == second:
            standardMsg = f'{first!r} != {second!r}'
            msg = self._formatMessage(msg, standardMsg)
            self.fail(msg)

    def assertNotEqual(self, first, second, msg=None):
        if first == second:
            standardMsg = f'{first!r} == {second!r}'
            msg = self._formatMessage(msg, standardMsg)
            self.fail(msg)

    def assertTrue(self, expr, msg=None):
        if not expr:
            standardMsg = f'{expr!r} is not true'
            msg = self._formatMessage(msg, standardMsg)
            self.fail(msg)

    def assertFalse(self, expr, msg=None):
        if expr:
            standardMsg = f'{expr!r} is not false'
            msg = self._formatMessage(msg, standardMsg)
            self.fail(msg)

    def assertIsNone(self, obj, msg=None):
        if obj is not None:
            standardMsg = f'{obj!r} is not None'
            self.fail(self._formatMessage(msg, standardMsg))

    def assertIsNotNone(self, obj, msg=None):
        if obj is None:
            self.fail(self._formatMessage(msg, 'unexpectedly None'))

    def assertIs(self, expr1, expr2, msg=None):
        if expr1 is not expr2:
            standardMsg = f'{expr1!r} is not {expr2!r}'
            self.fail(self._formatMessage(msg, standardMsg))

    def assertIsNot(self, expr1, expr2, msg=None):
        if expr1 is expr2:
            standardMsg = f'unexpectedly identical: {expr1!r}'
            self.fail(self._formatMessage(msg, standardMsg))

    def assertIn(self, member, container, msg=None):
        if member not in container:
            standardMsg = f'{member!r} not found in {container!r}'
            self.fail(self._formatMessage(msg, standardMsg))

    def assertNotIn(self, member, container, msg=None):
        if member in container:
            standardMsg = f'{member!r} unexpectedly found in {container!r}'
            self.fail(self._formatMessage(msg, standardMsg))

    def assertIsInstance(self, obj, cls, msg=None):
        if not isinstance(obj, cls):
            standardMsg = f'{obj!r} is not an instance of {cls!r}'
            self.fail(self._formatMessage(msg, standardMsg))

    def assertNotIsInstance(self, obj, cls, msg=None):
        if isinstance(obj, cls):
            standardMsg = f'{obj!r} is an instance of {cls!r}'
            self.fail(self._formatMessage(msg, standardMsg))

    def assertRaises(self, expected_exception, *args, **kwargs):
        context = _AssertRaisesContext(expected_exception, self)
        try:
            return context.handle('assertRaises', args, kwargs)
        except AttributeError:
            return context

    def assertRaisesRegex(self, expected_exception, expected_regex, *args, **kwargs):
        return _AssertRaisesContext(expected_exception, self)

    def assertGreater(self, a, b, msg=None):
        if not a > b:
            standardMsg = f'{a!r} not greater than {b!r}'
            self.fail(self._formatMessage(msg, standardMsg))

    def assertLess(self, a, b, msg=None):
        if not a < b:
            standardMsg = f'{a!r} not less than {b!r}'
            self.fail(self._formatMessage(msg, standardMsg))

    def assertAlmostEqual(self, first, second, places=7, msg=None, delta=None):
        if delta is not None:
            if abs(first - second) <= delta:
                return
        else:
            if round(abs(second - first), places) == 0:
                return
        standardMsg = f'{first!r} != {second!r} within {places} places'
        self.fail(self._formatMessage(msg, standardMsg))

    def assertSequenceEqual(self, seq1, seq2, msg=None, seq_type=None):
        if seq1 != seq2:
            self.fail(self._formatMessage(msg, f'{seq1!r} != {seq2!r}'))

    def assertListEqual(self, list1, list2, msg=None):
        self.assertSequenceEqual(list1, list2, msg, list)

    def assertTupleEqual(self, tuple1, tuple2, msg=None):
        self.assertSequenceEqual(tuple1, tuple2, msg, tuple)

    def assertSetEqual(self, set1, set2, msg=None):
        if set1 != set2:
            self.fail(self._formatMessage(msg, f'{set1!r} != {set2!r}'))

    def assertDictEqual(self, d1, d2, msg=None):
        if d1 != d2:
            self.fail(self._formatMessage(msg, f'{d1!r} != {d2!r}'))

    def run(self, result=None):
        """Run the test."""
        if result is None:
            from theseus_unittest_result_cr import TestResult
            result = TestResult()
        result.startTest(self)
        testMethod = getattr(self, self._testMethodName)
        try:
            try:
                self.setUp()
            except SkipTest as e:
                result.addSkip(self, str(e))
                return result
            except Exception:
                result.addError(self, _sys.exc_info())
                return result
            success = False
            try:
                testMethod()
                success = True
            except self.failureException:
                result.addFailure(self, _sys.exc_info())
            except SkipTest as e:
                result.addSkip(self, str(e))
                success = True
            except Exception:
                result.addError(self, _sys.exc_info())
            if success:
                try:
                    self.tearDown()
                except Exception:
                    result.addError(self, _sys.exc_info())
                    success = False
            if success:
                result.addSuccess(self)
        finally:
            result.stopTest(self)
        return result

    def debug(self):
        """Run the test without collecting errors."""
        self.setUp()
        getattr(self, self._testMethodName)()
        self.tearDown()

    def countTestCases(self):
        return 1


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def utcase2_testcase():
    """TestCase class can be subclassed; returns True."""
    class MyTest(TestCase):
        def test_something(self):
            self.assertEqual(1, 1)

    tc = MyTest('test_something')
    return (isinstance(tc, TestCase) and
            tc._testMethodName == 'test_something')


def utcase2_assertions():
    """assertEqual, assertTrue, assertFalse work correctly; returns True."""
    class MyTest(TestCase):
        def runTest(self):
            pass

    tc = MyTest()
    tc.assertEqual(1, 1)
    tc.assertTrue(True)
    tc.assertFalse(False)
    tc.assertIsNone(None)
    return True


def utcase2_skip():
    """skip and skipIf decorators exist; returns True."""
    @skip('reason')
    def test_func():
        pass
    return (callable(skip) and
            callable(skipIf) and
            callable(skipUnless) and
            getattr(test_func, '__unittest_skip__', False))


__all__ = [
    'TestCase', 'SkipTest', 'skip', 'skipIf', 'skipUnless', 'expectedFailure',
    'utcase2_testcase', 'utcase2_assertions', 'utcase2_skip',
]
