"""
theseus_threading_cr3 - Clean-room extended threading primitives.
Do NOT import threading. Implemented from scratch using _thread module.
"""

import _thread
import time


class Lock:
    """A simple non-reentrant lock."""
    
    def __init__(self):
        self._lock = _thread.allocate_lock()
    
    def acquire(self, blocking=True, timeout=-1):
        if timeout != -1 and blocking:
            deadline = time.monotonic() + timeout
            while True:
                if self._lock.acquire(False):
                    return True
                if time.monotonic() >= deadline:
                    return False
                time.sleep(0.0001)
        return self._lock.acquire(blocking)
    
    def release(self):
        self._lock.release()
    
    def locked(self):
        return self._lock.locked()
    
    def __enter__(self):
        self.acquire()
        return self
    
    def __exit__(self, *args):
        self.release()


class RLock:
    """A reentrant lock."""
    
    def __init__(self):
        self._lock = _thread.allocate_lock()
        self._owner = None
        self._count = 0
        self._meta_lock = _thread.allocate_lock()
    
    def acquire(self, blocking=True, timeout=-1):
        me = _thread.get_ident()
        with self._meta_lock:
            if self._owner == me:
                self._count += 1
                return True
        
        if timeout != -1 and blocking:
            deadline = time.monotonic() + timeout
            while True:
                if self._lock.acquire(False):
                    with self._meta_lock:
                        self._owner = me
                        self._count = 1
                    return True
                if time.monotonic() >= deadline:
                    return False
                time.sleep(0.0001)
        
        result = self._lock.acquire(blocking)
        if result:
            with self._meta_lock:
                self._owner = me
                self._count = 1
        return result
    
    def release(self):
        me = _thread.get_ident()
        with self._meta_lock:
            if self._owner != me:
                raise RuntimeError("release() called on un-acquired RLock")
            self._count -= 1
            if self._count == 0:
                self._owner = None
                self._lock.release()
    
    def __enter__(self):
        self.acquire()
        return self
    
    def __exit__(self, *args):
        self.release()


class Semaphore:
    """Counting semaphore. acquire() decrements, release() increments."""
    
    def __init__(self, value=1):
        if value < 0:
            raise ValueError("Semaphore initial value must be >= 0")
        self._value = value
        self._lock = _thread.allocate_lock()
        self._cond_lock = _thread.allocate_lock()
        # We'll use a list of waiting locks
        self._waiters = []
    
    def acquire(self, blocking=True, timeout=None):
        with self._lock:
            if self._value > 0:
                self._value -= 1
                return True
            if not blocking:
                return False
        
        # Need to wait
        waiter = _thread.allocate_lock()
        waiter.acquire()
        
        with self._lock:
            # Check again after acquiring lock
            if self._value > 0:
                self._value -= 1
                return True
            self._waiters.append(waiter)
        
        if timeout is not None:
            deadline = time.monotonic() + timeout
            # Try to acquire with timeout
            while True:
                if waiter.acquire(False):
                    return True
                if time.monotonic() >= deadline:
                    # Remove from waiters
                    with self._lock:
                        try:
                            self._waiters.remove(waiter)
                        except ValueError:
                            # Already removed (notified), so we got it
                            return True
                    return False
                time.sleep(0.0001)
        else:
            waiter.acquire()
            return True
    
    def release(self, n=1):
        for _ in range(n):
            with self._lock:
                self._value += 1
                if self._waiters:
                    waiter = self._waiters.pop(0)
                    self._value -= 1
                    waiter.release()
    
    def __enter__(self):
        self.acquire()
        return self
    
    def __exit__(self, *args):
        self.release()


class BoundedSemaphore(Semaphore):
    """A semaphore that raises ValueError if released too many times."""
    
    def __init__(self, value=1):
        super().__init__(value)
        self._initial_value = value
    
    def release(self, n=1):
        with self._lock:
            if self._value + n > self._initial_value:
                raise ValueError("Semaphore released too many times")
        super().release(n)


class Condition:
    """Condition variable. Wraps a lock; acquire/release forward to the lock."""
    
    def __init__(self, lock=None):
        if lock is None:
            self._lock = RLock()
        else:
            self._lock = lock
        self._waiters = []
        self._waiters_lock = _thread.allocate_lock()
    
    def acquire(self, *args, **kwargs):
        return self._lock.acquire(*args, **kwargs)
    
    def release(self):
        self._lock.release()
    
    def __enter__(self):
        self.acquire()
        return self
    
    def __exit__(self, *args):
        self.release()
    
    def wait(self, timeout=None):
        """Wait until notified or until timeout occurs."""
        # Must be called with lock held
        waiter = _thread.allocate_lock()
        waiter.acquire()
        
        with self._waiters_lock:
            self._waiters.append(waiter)
        
        # Release the condition lock
        self._lock.release()
        
        try:
            if timeout is not None:
                deadline = time.monotonic() + timeout
                while True:
                    if waiter.acquire(False):
                        return True
                    if time.monotonic() >= deadline:
                        with self._waiters_lock:
                            try:
                                self._waiters.remove(waiter)
                            except ValueError:
                                return True
                        return False
                    time.sleep(0.0001)
            else:
                waiter.acquire()
                return True
        finally:
            self._lock.acquire()
    
    def wait_for(self, predicate, timeout=None):
        """Wait until predicate is true."""
        endtime = None
        waittime = timeout
        result = predicate()
        while not result:
            if waittime is not None:
                if endtime is None:
                    endtime = time.monotonic() + waittime
                else:
                    waittime = endtime - time.monotonic()
                    if waittime <= 0:
                        break
            self.wait(waittime)
            result = predicate()
        return result
    
    def notify(self, n=1):
        """Wake up one or more threads waiting on this condition."""
        with self._waiters_lock:
            to_notify = self._waiters[:n]
            self._waiters = self._waiters[n:]
        for waiter in to_notify:
            waiter.release()
    
    def notify_all(self):
        """Wake up all threads waiting on this condition."""
        with self._waiters_lock:
            waiters = self._waiters[:]
            self._waiters = []
        for waiter in waiters:
            waiter.release()
    
    notifyAll = notify_all


class Event:
    """Thread synchronization event. set()/clear()/is_set()/wait()."""
    
    def __init__(self):
        self._flag = False
        self._lock = _thread.allocate_lock()
        self._waiters = []
    
    def is_set(self):
        return self._flag
    
    isSet = is_set
    
    def set(self):
        with self._lock:
            self._flag = True
            waiters = self._waiters[:]
            self._waiters = []
        for waiter in waiters:
            try:
                waiter.release()
            except Exception:
                pass
    
    def clear(self):
        with self._lock:
            self._flag = False
    
    def wait(self, timeout=None):
        with self._lock:
            if self._flag:
                return True
            waiter = _thread.allocate_lock()
            waiter.acquire()
            self._waiters.append(waiter)
        
        if timeout is not None:
            deadline = time.monotonic() + timeout
            while True:
                if waiter.acquire(False):
                    return True
                if time.monotonic() >= deadline:
                    with self._lock:
                        try:
                            self._waiters.remove(waiter)
                        except ValueError:
                            return True
                    return self._flag
                time.sleep(0.0001)
        else:
            waiter.acquire()
            return True


class Barrier:
    """A barrier synchronization primitive."""
    
    def __init__(self, parties, action=None, timeout=None):
        self._parties = parties
        self._action = action
        self._timeout = timeout
        self._count = 0
        self._phase = 0
        self._broken = False
        self._lock = _thread.allocate_lock()
        self._cond = Condition(Lock())
    
    @property
    def parties(self):
        return self._parties
    
    @property
    def n_waiting(self):
        with self._lock:
            return self._count
    
    @property
    def broken(self):
        return self._broken
    
    def wait(self, timeout=None):
        if timeout is None:
            timeout = self._timeout
        
        with self._cond:
            if self._broken:
                raise BrokenBarrierError("Barrier is broken")
            
            phase = self._phase
            self._count += 1
            
            if self._count == self._parties:
                # Last thread to arrive
                self._count = 0
                self._phase += 1
                if self._action is not None:
                    try:
                        self._action()
                    except Exception:
                        self._broken = True
                        self._cond.notify_all()
                        raise
                self._cond.notify_all()
                return self._parties - 1
            else:
                # Wait for others
                index = self._count - 1
                
                def check():
                    return self._phase != phase or self._broken
                
                if timeout is not None:
                    result = self._cond.wait_for(check, timeout)
                    if not result:
                        self._broken = True
                        self._cond.notify_all()
                        raise BrokenBarrierError("Barrier timeout")
                else:
                    self._cond.wait_for(check)
                
                if self._broken:
                    raise BrokenBarrierError("Barrier is broken")
                
                return index
    
    def reset(self):
        with self._cond:
            self._broken = False
            self._count = 0
            self._phase += 1
            self._cond.notify_all()
    
    def abort(self):
        with self._cond:
            self._broken = True
            self._cond.notify_all()


class BrokenBarrierError(Exception):
    pass


class Thread:
    """A simple thread class."""
    
    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None, daemon=None):
        self._target = target
        self._name = name or f"Thread-{id(self)}"
        self._args = args
        self._kwargs = kwargs or {}
        self._daemon = daemon
        self._started = Event()
        self._finished = Event()
        self._ident = None
    
    def start(self):
        self._started.set()
        _thread.start_new_thread(self._bootstrap, ())
    
    def _bootstrap(self):
        self._ident = _thread.get_ident()
        try:
            self.run()
        finally:
            self._finished.set()
    
    def run(self):
        if self._target is not None:
            self._target(*self._args, **self._kwargs)
    
    def join(self, timeout=None):
        self._finished.wait(timeout)
    
    def is_alive(self):
        return self._started.is_set() and not self._finished.is_set()
    
    isAlive = is_alive
    
    @property
    def name(self):
        return self._name
    
    @name.setter
    def name(self, value):
        self._name = value
    
    @property
    def ident(self):
        return self._ident
    
    @property
    def daemon(self):
        return self._daemon if self._daemon is not None else False
    
    @daemon.setter
    def daemon(self, value):
        self._daemon = value


# ─── Invariant functions ───────────────────────────────────────────────────────

def threading3_semaphore() -> bool:
    """Semaphore(2) acquire twice then release — returns True."""
    sem = Semaphore(2)
    r1 = sem.acquire()
    r2 = sem.acquire()
    sem.release()
    sem.release()
    return r1 and r2


def threading3_condition() -> bool:
    """Condition() acquire and release without deadlock — returns True."""
    cond = Condition()
    cond.acquire()
    cond.release()
    return True


def threading3_event() -> bool:
    """Event() set/clear/is_set cycle — returns True."""
    evt = Event()
    evt.set()
    if not evt.is_set():
        return False
    evt.clear()
    if evt.is_set():
        return False
    return True