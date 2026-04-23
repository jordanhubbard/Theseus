"""
theseus_unittest_cr — Clean-room unittest subset.
No import of the standard `unittest` module.
"""

import sys
import traceback as _traceback


class AssertionError(Exception):
    pass


class TestCase:
    """Minimal TestCase base class."""

    def __init__(self, methodName='runTest'):
        self._methodName = methodName

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def run(self, result=None):
        if result is None:
            result = TestResult()
        result.startTest(self)
        try:
            self.setUp()
        except Exception as e:
            result.addError(self, sys.exc_info())
            result.stopTest(self)
            return result
        try:
            method = getattr(self, self._methodName)
            method()
            result.addSuccess(self)
        except AssertionError as e:
            result.addFailure(self, sys.exc_info())
        except Exception as e:
            result.addError(self, sys.exc_info())
        finally:
            try:
                self.tearDown()
            except Exception:
                result.addError(self, sys.exc_info())
        result.stopTest(self)
        return result

    def assertEqual(self, first, second, msg=None):
        if first != second:
            message = msg or f'{first!r} != {second!r}'
            raise AssertionError(message)

    def assertNotEqual(self, first, second, msg=None):
        if first == second:
            message = msg or f'{first!r} == {second!r}'
            raise AssertionError(message)

    def assertTrue(self, expr, msg=None):
        if not expr:
            raise AssertionError(msg or f'{expr!r} is not true')

    def assertFalse(self, expr, msg=None):
        if expr:
            raise AssertionError(msg or f'{expr!r} is not false')

    def assertIsNone(self, obj, msg=None):
        if obj is not None:
            raise AssertionError(msg or f'{obj!r} is not None')

    def assertIsNotNone(self, obj, msg=None):
        if obj is None:
            raise AssertionError(msg or 'unexpectedly None')

    def assertIn(self, member, container, msg=None):
        if member not in container:
            raise AssertionError(msg or f'{member!r} not in {container!r}')

    def assertNotIn(self, member, container, msg=None):
        if member in container:
            raise AssertionError(msg or f'{member!r} in {container!r}')

    def assertRaises(self, expected_exception, *args, **kwargs):
        if args:
            callable_obj = args[0]
            rest = args[1:]
            try:
                callable_obj(*rest, **kwargs)
            except expected_exception:
                return
            except Exception as e:
                raise AssertionError(
                    f'{expected_exception.__name__} not raised; got {type(e).__name__}')
            raise AssertionError(f'{expected_exception.__name__} not raised')
        return _AssertRaisesContext(expected_exception)

    def fail(self, msg=None):
        raise AssertionError(msg or 'Test failed')

    def shortDescription(self):
        doc = getattr(getattr(self, self._methodName, None), '__doc__', None)
        return doc and doc.strip().splitlines()[0] or None

    def __str__(self):
        return f'{self._methodName} ({type(self).__module__}.{type(self).__qualname__})'


class _AssertRaisesContext:
    def __init__(self, expected):
        self.expected = expected
        self.exception = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            raise AssertionError(f'{self.expected.__name__} not raised')
        if issubclass(exc_type, self.expected):
            self.exception = exc_val
            return True
        return False


class TestSuite:
    """A collection of test cases."""

    def __init__(self, tests=()):
        self._tests = list(tests)

    def addTest(self, test):
        self._tests.append(test)

    def addTests(self, tests):
        for test in tests:
            self.addTest(test)

    def countTestCases(self):
        count = 0
        for test in self._tests:
            count += test.countTestCases() if isinstance(test, TestSuite) else 1
        return count

    def run(self, result):
        for test in self._tests:
            test.run(result)
        return result

    def __iter__(self):
        return iter(self._tests)

    def __len__(self):
        return len(self._tests)


class TestResult:
    """Holds the results of a test run."""

    def __init__(self):
        self.failures = []
        self.errors = []
        self.testsRun = 0
        self.skipped = []
        self._successes = 0

    def startTest(self, test):
        self.testsRun += 1

    def stopTest(self, test):
        pass

    def addSuccess(self, test):
        self._successes += 1

    def addFailure(self, test, err):
        self.failures.append((test, err))

    def addError(self, test, err):
        self.errors.append((test, err))

    def addSkip(self, test, reason):
        self.skipped.append((test, reason))

    @property
    def wasSuccessful(self):
        return not self.failures and not self.errors


class TestLoader:
    """Loads test cases from TestCase subclasses."""

    testMethodPrefix = 'test'

    def getTestCaseNames(self, testCaseClass):
        names = [n for n in dir(testCaseClass) if n.startswith(self.testMethodPrefix)]
        return sorted(names)

    def loadTestsFromTestCase(self, testCaseClass):
        names = self.getTestCaseNames(testCaseClass)
        tests = [testCaseClass(name) for name in names]
        return TestSuite(tests)


class TextTestRunner:
    """Minimal test runner that prints results to stderr."""

    def __init__(self, stream=None, verbosity=1):
        self.stream = stream or sys.stderr
        self.verbosity = verbosity

    def run(self, test):
        result = TestResult()
        test.run(result)
        if self.verbosity > 0:
            print(f'Ran {result.testsRun} test(s).', file=self.stream)
        return result


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def unittest2_assertequal():
    """assertEqual(1, 1) passes; assertEqual(1, 2) raises AssertionError; returns True."""
    tc = TestCase()
    tc.assertEqual(1, 1)
    try:
        tc.assertEqual(1, 2)
        return False
    except AssertionError:
        return True


def unittest2_assertraises():
    """assertRaises(ValueError) catches ValueError correctly; returns True."""
    tc = TestCase()
    with tc.assertRaises(ValueError):
        raise ValueError('test')
    return True


def unittest2_run_suite():
    """Run a 2-test suite; result.testsRun == 2."""
    class MyTests(TestCase):
        def test_one(self):
            self.assertEqual(1, 1)
        def test_two(self):
            self.assertTrue(True)

    loader = TestLoader()
    suite = loader.loadTestsFromTestCase(MyTests)
    result = TestResult()
    suite.run(result)
    return result.testsRun


__all__ = [
    'TestCase', 'TestSuite', 'TestResult', 'TestLoader', 'TextTestRunner',
    'AssertionError',
    'unittest2_assertequal', 'unittest2_assertraises', 'unittest2_run_suite',
]
