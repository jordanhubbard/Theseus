"""
theseus_sched_cr: Clean-room implementation of an event scheduler (sched module).
"""

import time
import heapq


class Event:
    """Represents a scheduled event."""
    __slots__ = ['time', 'priority', 'sequence', 'action', 'argument', 'kwargs']

    def __init__(self, time, priority, sequence, action, argument, kwargs):
        self.time = time
        self.priority = priority
        self.sequence = sequence
        self.action = action
        self.argument = argument
        self.kwargs = kwargs

    def __lt__(self, other):
        if self.time != other.time:
            return self.time < other.time
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.sequence < other.sequence

    def __le__(self, other):
        return self == other or self < other

    def __gt__(self, other):
        return other < self

    def __ge__(self, other):
        return other <= self

    def __eq__(self, other):
        if not isinstance(other, Event):
            return False
        return (self.time == other.time and
                self.priority == other.priority and
                self.sequence == other.sequence and
                self.action is other.action and
                self.argument == other.argument and
                self.kwargs == other.kwargs)

    def __hash__(self):
        return id(self)

    def __repr__(self):
        return (f'Event(time={self.time!r}, priority={self.priority!r}, '
                f'sequence={self.sequence!r}, action={self.action!r}, '
                f'argument={self.argument!r}, kwargs={self.kwargs!r})')


class scheduler:
    def __init__(self, timefunc, delayfunc):
        self._timefunc = timefunc
        self._delayfunc = delayfunc
        self._queue = []  # heap of Event objects
        self._sequence = 0

    def enter(self, delay, priority, action, argument=(), kwargs={}):
        """Schedule an event after 'delay' time units."""
        t = self._timefunc() + delay
        seq = self._sequence
        self._sequence += 1
        event = Event(t, priority, seq, action, argument, kwargs)
        heapq.heappush(self._queue, event)
        return event

    def cancel(self, event):
        """Cancel a previously scheduled event."""
        # Find and remove the event by identity
        for i, e in enumerate(self._queue):
            if e is event:
                self._queue[i] = self._queue[-1]
                self._queue.pop()
                heapq.heapify(self._queue)
                return
        raise ValueError('event not in queue')

    def run(self, blocking=True):
        """Run all scheduled events."""
        delayfunc = self._delayfunc
        timefunc = self._timefunc

        while self._queue:
            event = self._queue[0]
            now = timefunc()
            if event.time > now:
                delay = event.time - now
                if not blocking:
                    return delay
                delayfunc(delay)
            else:
                heapq.heappop(self._queue)
                event.action(*event.argument, **event.kwargs)

        return None

    @property
    def queue(self):
        """Return a sorted list of pending Event objects."""
        return sorted(self._queue)

    def empty(self):
        """Return True if the queue is empty."""
        return len(self._queue) == 0


# --- Invariant functions ---

def sched_enter():
    """
    s = scheduler(time.monotonic, time.sleep)
    s.enter(0, 1, lambda: None)
    return len(s.queue) == 1
    """
    s = scheduler(time.monotonic, time.sleep)
    s.enter(0, 1, lambda: None)
    return len(s.queue)


def sched_empty():
    """
    Empty scheduler queue is [].
    """
    s = scheduler(time.monotonic, time.sleep)
    return s.queue


def sched_cancel():
    """
    Cancel event removes it from queue — queue becomes empty.
    """
    s = scheduler(time.monotonic, time.sleep)
    event = s.enter(0, 1, lambda: None)
    s.cancel(event)
    return len(s.queue) == 0