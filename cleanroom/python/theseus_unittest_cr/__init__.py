"""Clean-room unittest subset for theseus_unittest_cr."""


class _AssertRaisesContext:
    """Context manager returned by assertRaises()."""

    def __init__(self, expected):
        self.expected = expected
        self.exception = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            raise AssertionError(
                "%s not raised" % getattr(self.expected, "__name__", str(self.expected))
            )
        if not issubclass(exc_type, self.expected):
            # Let it propagate
            return False
        self.exception = exc_val
        return True


class TestCase(object):
    """Base class for test cases."""

    def __init__(self, methodName="runTest"):
        self._methodName = methodName

    # --- Assertion helpers -------------------------------------------------

    def assertEqual(self, a, b, msg=None):
        if not (a == b):
            raise AssertionError(msg if msg is not None else "%r != %r" % (a, b))

    def assertNotEqual(self, a, b, msg=None):
        if a == b:
            raise AssertionError(msg if msg is not None else "%r == %r" % (a, b))

    def assertTrue(self, expr, msg=None):
        if not expr:
            raise AssertionError(
                msg if msg is not None else "%r is not true" % (expr,)
            )

    def assertFalse(self, expr, msg=None):
        if expr:
            raise AssertionError(
                msg if msg is not None else "%r is not false" % (expr,)
            )

    def assertRaises(self, expected_exception, *args, **kwargs):
        # Context-manager form: assertRaises(Exc)
        if not args:
            return _AssertRaisesContext(expected_exception)
        # Direct form: assertRaises(Exc, callable, *args, **kwargs)
        callable_obj = args[0]
        rest = args[1:]
        try:
            callable_obj(*rest, **kwargs)
        except expected_exception:
            return None
        raise AssertionError(
            "%s not raised"
            % getattr(expected_exception, "__name__", str(expected_exception))
        )

    # --- Lifecycle hooks ---------------------------------------------------

    def setUp(self):
        pass

    def tearDown(self):
        pass

    # --- Execution ---------------------------------------------------------

    def run(self, result=None):
        if result is None:
            result = TestResult()
        result.testsRun += 1
        try:
            self.setUp()
        except AssertionError as e:
            result.failures.append((self, str(e)))
            return result
        except Exception as e:
            result.errors.append((self, repr(e)))
            return result

        success = False
        try:
            method = getattr(self, self._methodName)
            method()
            success = True
        except AssertionError as e:
            result.failures.append((self, str(e)))
        except Exception as e:
            result.errors.append((self, repr(e)))

        try:
            self.tearDown()
        except AssertionError as e:
            result.failures.append((self, str(e)))
            success = False
        except Exception as e:
            result.errors.append((self, repr(e)))
            success = False

        if success:
            result.passed += 1
        return result

    def __call__(self, result=None):
        return self.run(result)


class TestSuite(object):
    """A composite of test cases / suites."""

    def __init__(self, tests=()):
        self._tests = []
        for t in tests:
            self.addTest(t)

    def addTest(self, test):
        self._tests.append(test)

    def addTests(self, tests):
        for t in tests:
            self.addTest(t)

    def countTestCases(self):
        count = 0
        for t in self._tests:
            if isinstance(t, TestSuite):
                count += t.countTestCases()
            else:
                count += 1
        return count

    def __iter__(self):
        return iter(self._tests)

    def __len__(self):
        return len(self._tests)

    def run(self, result):
        for test in self._tests:
            test.run(result)
        return result

    def __call__(self, result):
        return self.run(result)


class TestResult(object):
    """Tracks the outcome of a test run."""

    def __init__(self):
        self.testsRun = 0
        self.passed = 0
        self.failures = []
        self.errors = []

    def wasSuccessful(self):
        return not self.failures and not self.errors

    def __repr__(self):
        return (
            "<TestResult run=%d passed=%d failures=%d errors=%d>"
            % (self.testsRun, self.passed, len(self.failures), len(self.errors))
        )


class TestLoader(object):
    """Builds suites from TestCase classes."""

    testMethodPrefix = "test"

    def loadTestsFromTestCase(self, testCaseClass):
        suite = TestSuite()
        names = []
        for name in dir(testCaseClass):
            if not name.startswith(self.testMethodPrefix):
                continue
            attr = getattr(testCaseClass, name, None)
            if not callable(attr):
                continue
            names.append(name)
        names.sort()
        for name in names:
            suite.addTest(testCaseClass(name))
        return suite


class TextTestRunner(object):
    """Runs a suite and returns a TestResult."""

    def __init__(self, verbosity=0):
        self.verbosity = verbosity

    def run(self, suite):
        result = TestResult()
        suite.run(result)
        return result


# ---------------------------------------------------------------------------
# Invariants
# ---------------------------------------------------------------------------

def unittest2_assertequal():
    """assertEqual passes on equal values, raises AssertionError on unequal."""
    tc = TestCase()
    # Equal values: must not raise.
    try:
        tc.assertEqual(1, 1)
        tc.assertEqual("abc", "abc")
        tc.assertEqual([1, 2, 3], [1, 2, 3])
    except AssertionError:
        return False
    # Unequal values: must raise.
    try:
        tc.assertEqual(1, 2)
    except AssertionError:
        return True
    return False


def unittest2_assertraises():
    """assertRaises context manager catches the expected exception."""
    tc = TestCase()
    try:
        with tc.assertRaises(ValueError):
            raise ValueError("boom")
    except AssertionError:
        return False

    # Should also raise AssertionError if expected exception is not raised.
    raised_assertion = False
    try:
        with tc.assertRaises(ValueError):
            pass
    except AssertionError:
        raised_assertion = True
    if not raised_assertion:
        return False
    return True


def unittest2_run_suite():
    """Build a 2-test suite, run it, and return the count of passing tests."""

    class _MiniTest(TestCase):
        def test_one(self):
            self.assertEqual(1, 1)

        def test_two(self):
            self.assertTrue(True)

    loader = TestLoader()
    suite = loader.loadTestsFromTestCase(_MiniTest)
    runner = TextTestRunner(verbosity=0)
    result = runner.run(suite)
    return result.passed