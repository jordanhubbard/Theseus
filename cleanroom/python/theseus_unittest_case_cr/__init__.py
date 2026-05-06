"""Clean-room reimplementation of unittest.case behavioral surface.

This module provides a from-scratch implementation of the small subset of
unittest.case behavior probed by the Theseus invariants. It does not import
unittest, unittest.case, or any third-party library.
"""


# ---------------------------------------------------------------------------
# Exceptions used to signal test outcomes (clean-room)
# ---------------------------------------------------------------------------

class _SkipTest(Exception):
    """Raised to indicate a test should be skipped."""
    pass


class _FailTest(AssertionError):
    """Raised to indicate a test failure."""
    pass


# ---------------------------------------------------------------------------
# Decorators: skip / skipIf / skipUnless / expectedFailure
# ---------------------------------------------------------------------------

def _skip(reason):
    """Unconditionally skip a test."""
    def decorator(test_item):
        if isinstance(test_item, type):
            # Class decorator: mark every test method as skipped.
            test_item.__unittest_skip__ = True
            test_item.__unittest_skip_why__ = reason
            return test_item

        def wrapper(*args, **kwargs):
            raise _SkipTest(reason)
        wrapper.__unittest_skip__ = True
        wrapper.__unittest_skip_why__ = reason
        wrapper.__name__ = getattr(test_item, "__name__", "wrapper")
        wrapper.__doc__ = getattr(test_item, "__doc__", None)
        return wrapper
    return decorator


def _skipIf(condition, reason):
    if condition:
        return _skip(reason)
    def decorator(test_item):
        return test_item
    return decorator


def _skipUnless(condition, reason):
    if not condition:
        return _skip(reason)
    def decorator(test_item):
        return test_item
    return decorator


def _expectedFailure(test_item):
    test_item.__unittest_expecting_failure__ = True
    return test_item


# ---------------------------------------------------------------------------
# TestCase: minimal but correct enough to support the invariants
# ---------------------------------------------------------------------------

class TestCase(object):
    """A from-scratch TestCase analogue."""

    failureException = _FailTest
    longMessage = True
    maxDiff = 80 * 8

    def __init__(self, methodName="runTest"):
        self._testMethodName = methodName
        self._cleanups = []
        self._outcome = None
        try:
            method = getattr(self, methodName)
        except AttributeError:
            method = None
        self._testMethodDoc = getattr(method, "__doc__", None) if method else None

    # ----- lifecycle -------------------------------------------------------

    def setUp(self):
        pass

    def tearDown(self):
        pass

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def addCleanup(self, function, *args, **kwargs):
        self._cleanups.append((function, args, kwargs))

    def doCleanups(self):
        ok = True
        while self._cleanups:
            func, args, kwargs = self._cleanups.pop()
            try:
                func(*args, **kwargs)
            except Exception:
                ok = False
        return ok

    def id(self):
        return "%s.%s" % (type(self).__name__, self._testMethodName)

    def shortDescription(self):
        doc = self._testMethodDoc
        if doc:
            return doc.strip().split("\n")[0].strip()
        return None

    def __str__(self):
        return "%s (%s)" % (self._testMethodName, type(self).__name__)

    def __repr__(self):
        return "<%s testMethod=%s>" % (type(self).__name__, self._testMethodName)

    def __eq__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        return self._testMethodName == other._testMethodName

    def __hash__(self):
        return hash((type(self), self._testMethodName))

    # ----- run -------------------------------------------------------------

    def run(self, result=None):
        method = getattr(self, self._testMethodName)
        skip_class = getattr(type(self), "__unittest_skip__", False)
        skip_method = getattr(method, "__unittest_skip__", False)
        if skip_class or skip_method:
            reason = (getattr(method, "__unittest_skip_why__", None)
                      or getattr(type(self), "__unittest_skip_why__", None)
                      or "")
            return ("skipped", reason)

        try:
            self.setUp()
        except _SkipTest as exc:
            return ("skipped", str(exc))
        except Exception as exc:
            return ("error", exc)

        outcome = ("success", None)
        try:
            method()
        except _SkipTest as exc:
            outcome = ("skipped", str(exc))
        except self.failureException as exc:
            outcome = ("failure", exc)
        except Exception as exc:
            outcome = ("error", exc)

        try:
            self.tearDown()
        except Exception as exc:
            if outcome[0] == "success":
                outcome = ("error", exc)

        self.doCleanups()
        return outcome

    def __call__(self, *args, **kwargs):
        return self.run(*args, **kwargs)

    # ----- skip helper ----------------------------------------------------

    def skipTest(self, reason):
        raise _SkipTest(reason)

    def fail(self, msg=None):
        raise self.failureException(msg)

    # ----- internal message formatting ------------------------------------

    def _formatMessage(self, msg, standardMsg):
        if not self.longMessage:
            return msg if msg is not None else standardMsg
        if msg is None:
            return standardMsg
        try:
            return "%s : %s" % (standardMsg, msg)
        except UnicodeDecodeError:
            return "%s : %s" % (standardMsg, msg)

    # ----- assertions ------------------------------------------------------

    def assertTrue(self, expr, msg=None):
        if not expr:
            std = "%r is not true" % (expr,)
            raise self.failureException(self._formatMessage(msg, std))

    def assertFalse(self, expr, msg=None):
        if expr:
            std = "%r is not false" % (expr,)
            raise self.failureException(self._formatMessage(msg, std))

    def assertEqual(self, first, second, msg=None):
        if not (first == second):
            std = "%r != %r" % (first, second)
            raise self.failureException(self._formatMessage(msg, std))

    def assertNotEqual(self, first, second, msg=None):
        if not (first != second):
            std = "%r == %r" % (first, second)
            raise self.failureException(self._formatMessage(msg, std))

    def assertIs(self, first, second, msg=None):
        if first is not second:
            std = "%r is not %r" % (first, second)
            raise self.failureException(self._formatMessage(msg, std))

    def assertIsNot(self, first, second, msg=None):
        if first is second:
            std = "unexpectedly identical: %r" % (first,)
            raise self.failureException(self._formatMessage(msg, std))

    def assertIsNone(self, obj, msg=None):
        if obj is not None:
            std = "%r is not None" % (obj,)
            raise self.failureException(self._formatMessage(msg, std))

    def assertIsNotNone(self, obj, msg=None):
        if obj is None:
            std = "unexpectedly None"
            raise self.failureException(self._formatMessage(msg, std))

    def assertIn(self, member, container, msg=None):
        if member not in container:
            std = "%r not found in %r" % (member, container)
            raise self.failureException(self._formatMessage(msg, std))

    def assertNotIn(self, member, container, msg=None):
        if member in container:
            std = "%r unexpectedly found in %r" % (member, container)
            raise self.failureException(self._formatMessage(msg, std))

    def assertIsInstance(self, obj, cls, msg=None):
        if not isinstance(obj, cls):
            std = "%r is not an instance of %r" % (obj, cls)
            raise self.failureException(self._formatMessage(msg, std))

    def assertNotIsInstance(self, obj, cls, msg=None):
        if isinstance(obj, cls):
            std = "%r is an instance of %r" % (obj, cls)
            raise self.failureException(self._formatMessage(msg, std))

    def assertGreater(self, a, b, msg=None):
        if not (a > b):
            std = "%r not greater than %r" % (a, b)
            raise self.failureException(self._formatMessage(msg, std))

    def assertGreaterEqual(self, a, b, msg=None):
        if not (a >= b):
            std = "%r not greater than or equal to %r" % (a, b)
            raise self.failureException(self._formatMessage(msg, std))

    def assertLess(self, a, b, msg=None):
        if not (a < b):
            std = "%r not less than %r" % (a, b)
            raise self.failureException(self._formatMessage(msg, std))

    def assertLessEqual(self, a, b, msg=None):
        if not (a <= b):
            std = "%r not less than or equal to %r" % (a, b)
            raise self.failureException(self._formatMessage(msg, std))

    def assertAlmostEqual(self, first, second, places=None, msg=None, delta=None):
        if first == second:
            return
        if delta is not None and places is not None:
            raise TypeError("specify delta or places, not both")
        if delta is not None:
            diff = abs(first - second)
            if diff <= delta:
                return
            std = "%r != %r within %r delta (%r difference)" % (
                first, second, delta, diff)
        else:
            if places is None:
                places = 7
            if round(abs(second - first), places) == 0:
                return
            std = "%r != %r within %r places" % (first, second, places)
        raise self.failureException(self._formatMessage(msg, std))

    def assertNotAlmostEqual(self, first, second, places=None, msg=None, delta=None):
        if delta is not None and places is not None:
            raise TypeError("specify delta or places, not both")
        if delta is not None:
            if not (first == second) and abs(first - second) > delta:
                return
            std = "%r == %r within %r delta" % (first, second, delta)
        else:
            if places is None:
                places = 7
            if not (first == second) and round(abs(second - first), places) != 0:
                return
            std = "%r == %r within %r places" % (first, second, places)
        raise self.failureException(self._formatMessage(msg, std))

    def assertRaises(self, excClass, callableObj=None, *args, **kwargs):
        context = _AssertRaisesContext(excClass, self)
        if callableObj is None:
            return context
        with context:
            callableObj(*args, **kwargs)
        return context

    def assertSequenceEqual(self, seq1, seq2, msg=None, seq_type=None):
        if seq_type is not None:
            if not isinstance(seq1, seq_type):
                raise self.failureException(
                    self._formatMessage(msg, "First sequence is not a %s" % seq_type))
            if not isinstance(seq2, seq_type):
                raise self.failureException(
                    self._formatMessage(msg, "Second sequence is not a %s" % seq_type))
        if len(seq1) != len(seq2):
            raise self.failureException(
                self._formatMessage(msg,
                                    "sequence lengths differ: %d != %d" % (len(seq1), len(seq2))))
        for i, (a, b) in enumerate(zip(seq1, seq2)):
            if a != b:
                raise self.failureException(
                    self._formatMessage(msg,
                                        "first differing element %d: %r != %r" % (i, a, b)))

    def assertListEqual(self, list1, list2, msg=None):
        self.assertSequenceEqual(list1, list2, msg, seq_type=list)

    def assertTupleEqual(self, tuple1, tuple2, msg=None):
        self.assertSequenceEqual(tuple1, tuple2, msg, seq_type=tuple)

    def assertDictEqual(self, d1, d2, msg=None):
        if not isinstance(d1, dict):
            raise self.failureException(self._formatMessage(msg, "First argument is not a dictionary"))
        if not isinstance(d2, dict):
            raise self.failureException(self._formatMessage(msg, "Second argument is not a dictionary"))
        if d1 != d2:
            raise self.failureException(self._formatMessage(msg, "%r != %r" % (d1, d2)))

    def assertSetEqual(self, set1, set2, msg=None):
        try:
            difference1 = set1.difference(set2)
        except TypeError:
            raise self.failureException(self._formatMessage(msg,
                                        "invalid type when comparing sets"))
        try:
            difference2 = set2.difference(set1)
        except TypeError:
            raise self.failureException(self._formatMessage(msg,
                                        "invalid type when comparing sets"))
        if difference1 or difference2:
            std = "items in first not second: %r; items in second not first: %r" % (
                difference1, difference2)
            raise self.failureException(self._formatMessage(msg, std))


# ---------------------------------------------------------------------------
# Context manager for assertRaises
# ---------------------------------------------------------------------------

class _AssertRaisesContext(object):
    def __init__(self, expected, test_case):
        self.expected = expected
        self.test_case = test_case
        self.exception = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is None:
            try:
                exc_name = self.expected.__name__
            except AttributeError:
                exc_name = str(self.expected)
            raise self.test_case.failureException(
                "%s not raised" % exc_name)
        if not issubclass(exc_type, self.expected):
            return False
        self.exception = exc_value
        return True


# ---------------------------------------------------------------------------
# Public aliases (so the surface looks like unittest.case)
# ---------------------------------------------------------------------------

SkipTest = _SkipTest
skip = _skip
skipIf = _skipIf
skipUnless = _skipUnless
expectedFailure = _expectedFailure


# ---------------------------------------------------------------------------
# Invariant probes
# ---------------------------------------------------------------------------

def utcase2_testcase():
    """Confirm a basic TestCase lifecycle works end-to-end."""

    events = []

    class _T(TestCase):
        def setUp(self):
            events.append("setUp")

        def tearDown(self):
            events.append("tearDown")

        def runTest(self):
            events.append("test")
            self.assertTrue(True)
            self.assertEqual(2 + 2, 4)

    t = _T()
    if t.id() != "_T.runTest":
        return False
    if str(t) != "runTest (_T)":
        return False
    outcome = t.run()
    if outcome[0] != "success":
        return False
    if events != ["setUp", "test", "tearDown"]:
        return False

    # cleanups should run after tearDown, in reverse order
    cleanup_log = []

    class _T2(TestCase):
        def runTest(self):
            self.addCleanup(cleanup_log.append, "first")
            self.addCleanup(cleanup_log.append, "second")

    t2 = _T2()
    t2.run()
    if cleanup_log != ["second", "first"]:
        return False

    # equality / hashability
    a = _T()
    b = _T()
    if a != b:
        return False
    if hash(a) != hash(b):
        return False

    return True


def utcase2_assertions():
    """Exercise the assertion helpers — both passing and failing branches."""

    class _T(TestCase):
        def runTest(self):
            pass

    t = _T()

    # Assertions that should pass silently.
    t.assertTrue(1)
    t.assertFalse(0)
    t.assertEqual(1, 1)
    t.assertEqual([1, 2], [1, 2])
    t.assertNotEqual(1, 2)
    t.assertIs(None, None)
    t.assertIsNot(object(), object())
    t.assertIsNone(None)
    t.assertIsNotNone(0)
    t.assertIn(2, [1, 2, 3])
    t.assertNotIn(4, [1, 2, 3])
    t.assertIsInstance("x", str)
    t.assertNotIsInstance("x", int)
    t.assertGreater(2, 1)
    t.assertGreaterEqual(2, 2)
    t.assertLess(1, 2)
    t.assertLessEqual(2, 2)
    t.assertAlmostEqual(1.0, 1.0000001, places=5)
    t.assertNotAlmostEqual(1.0, 1.5, places=2)
    t.assertListEqual([1, 2], [1, 2])
    t.assertTupleEqual((1, 2), (1, 2))
    t.assertDictEqual({"a": 1}, {"a": 1})
    t.assertSetEqual({1, 2}, {2, 1})
    t.assertSequenceEqual("abc", "abc")

    # Each failing assertion must raise failureException.
    failing_calls = [
        lambda: t.assertTrue(False),
        lambda: t.assertFalse(True),
        lambda: t.assertEqual(1, 2),
        lambda: t.assertNotEqual(1, 1),
        lambda: t.assertIs(object(), object()),
        lambda: t.assertIsNot(None, None),
        lambda: t.assertIsNone(0),
        lambda: t.assertIsNotNone(None),
        lambda: t.assertIn(0, [1, 2, 3]),
        lambda: t.assertNotIn(2, [1, 2, 3]),
        lambda: t.assertIsInstance("x", int),
        lambda: t.assertNotIsInstance("x", str),
        lambda: t.assertGreater(1, 2),
        lambda: t.assertGreaterEqual(1, 2),
        lambda: t.assertLess(2, 1),
        lambda: t.assertLessEqual(2, 1),
        lambda: t.assertAlmostEqual(1.0, 1.5, places=5),
        lambda: t.assertNotAlmostEqual(1.0, 1.0, places=5),
        lambda: t.assertListEqual([1, 2], [1, 3]),
        lambda: t.assertTupleEqual((1,), (2,)),
        lambda: t.assertDictEqual({"a": 1}, {"a": 2}),
        lambda: t.assertSetEqual({1}, {2}),
        lambda: t.assertSequenceEqual("abc", "abd"),
    ]

    for call in failing_calls:
        try:
            call()
        except t.failureException:
            continue
        return False

    # assertRaises — both context manager and direct call forms.
    def _boom():
        raise ValueError("bad")

    with t.assertRaises(ValueError):
        _boom()

    try:
        with t.assertRaises(ValueError):
            pass  # nothing raised → must turn into a failure
    except t.failureException:
        pass
    else:
        return False

    ctx = t.assertRaises(KeyError, lambda: ({})["missing"])
    if not isinstance(ctx.exception, KeyError):
        return False

    # fail() always raises the failureException
    try:
        t.fail("nope")
    except t.failureException:
        pass
    else:
        return False

    return True


def utcase2_skip():
    """Verify the skip / skipIf / skipUnless / expectedFailure machinery."""

    # Module-level skipTest helper raises SkipTest.
    class _T(TestCase):
        def runTest(self):
            self.skipTest("nope")

    outcome = _T().run()
    if outcome[0] != "skipped" or outcome[1] != "nope":
        return False

    # Method decorated with @skip is recognised before setUp runs.
    setup_ran = []

    class _T2(TestCase):
        def setUp(self):
            setup_ran.append(True)

        @skip("decorated skip")
        def runTest(self):
            raise RuntimeError("should not execute")

    outcome = _T2().run()
    if outcome[0] != "skipped" or outcome[1] != "decorated skip":
        return False
    if setup_ran:
        return False  # setUp must not have run

    # Whole class decorated with @skip.
    @skip("class skip")
    class _T3(TestCase):
        def runTest(self):
            raise RuntimeError("should not execute")

    outcome = _T3().run()
    if outcome[0] != "skipped" or outcome[1] != "class skip":
        return False

    # skipIf with truthy condition skips; with falsy it does nothing.
    class _T4(TestCase):
        @skipIf(True, "because")
        def runTest(self):
            raise RuntimeError("should not execute")

    if _T4().run()[0] != "skipped":
        return False

    class _T5(TestCase):
        @skipIf(False, "because")
        def runTest(self):
            self.assertTrue(True)

    if _T5().run()[0] != "success":
        return False

    # skipUnless inverts the sense of skipIf.
    class _T6(TestCase):
        @skipUnless(False, "needs feature")
        def runTest(self):
            raise RuntimeError("should not execute")

    if _T6().run()[0] != "skipped":
        return False

    class _T7(TestCase):
        @skipUnless(True, "needs feature")
        def runTest(self):
            self.assertTrue(True)

    if _T7().run()[0] != "success":
        return False

    # expectedFailure tags the method.
    class _T8(TestCase):
        @expectedFailure
        def runTest(self):
            self.fail("expected")

    method = _T8().runTest
    if not getattr(method, "__unittest_expecting_failure__", False):
        return False

    # SkipTest raised directly from a test method is captured as a skip.
    class _T9(TestCase):
        def runTest(self):
            raise SkipTest("manual")

    if _T9().run()[0] != "skipped":
        return False

    return True