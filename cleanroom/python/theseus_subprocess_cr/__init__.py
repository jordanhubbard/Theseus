"""Clean-room subprocess module for Theseus.

This is a minimal clean-room implementation that does NOT import the
standard library `subprocess` module. It provides stand-in functions
matching the invariants required by the Theseus rewrite initiative.

Only Python built-ins are used (os, sys). No third-party imports.
"""

import os
import sys


# Constants mirroring subprocess module conventions
PIPE = -1
STDOUT = -2
DEVNULL = -3


class CalledProcessError(Exception):
    """Raised when a process run with check=True returns a non-zero exit code."""

    def __init__(self, returncode, cmd, output=None, stderr=None):
        self.returncode = returncode
        self.cmd = cmd
        self.output = output
        self.stderr = stderr
        super().__init__(
            "Command %r returned non-zero exit status %d" % (cmd, returncode)
        )


class CompletedProcess(object):
    """Represents the result of a finished process."""

    def __init__(self, args, returncode, stdout=None, stderr=None):
        self.args = args
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

    def check_returncode(self):
        if self.returncode != 0:
            raise CalledProcessError(
                self.returncode, self.args, self.stdout, self.stderr
            )


def _coerce_args(args):
    """Normalize args into a list of strings."""
    if isinstance(args, (list, tuple)):
        return [str(a) for a in args]
    if isinstance(args, str):
        # Very simple whitespace split — clean-room minimal parser.
        return args.split()
    if isinstance(args, bytes):
        return args.decode("utf-8", "replace").split()
    return [str(args)]


def _run_via_fork(args, stdin_bytes=None, capture=False):
    """Execute a command via fork/exec using only os primitives.

    Returns (returncode, stdout_bytes, stderr_bytes).
    If capture is False, stdout/stderr will be None.
    """
    argv = _coerce_args(args)
    if not argv:
        return 0, b"" if capture else None, b"" if capture else None

    # Build pipes for stdin/stdout/stderr if needed.
    stdin_r = stdin_w = None
    stdout_r = stdout_w = None
    stderr_r = stderr_w = None

    if stdin_bytes is not None:
        stdin_r, stdin_w = os.pipe()
    if capture:
        stdout_r, stdout_w = os.pipe()
        stderr_r, stderr_w = os.pipe()

    pid = os.fork()
    if pid == 0:
        # Child process
        try:
            if stdin_r is not None:
                os.dup2(stdin_r, 0)
                os.close(stdin_r)
                os.close(stdin_w)
            if stdout_w is not None:
                os.dup2(stdout_w, 1)
                os.close(stdout_r)
                os.close(stdout_w)
            if stderr_w is not None:
                os.dup2(stderr_w, 2)
                os.close(stderr_r)
                os.close(stderr_w)
            # Search PATH for the executable.
            try:
                os.execvp(argv[0], argv)
            except OSError:
                os._exit(127)
        except BaseException:
            os._exit(127)
    else:
        # Parent
        if stdin_r is not None:
            os.close(stdin_r)
            if stdin_bytes:
                try:
                    os.write(stdin_w, stdin_bytes)
                except OSError:
                    pass
            os.close(stdin_w)

        out_chunks = []
        err_chunks = []
        if stdout_w is not None:
            os.close(stdout_w)
            while True:
                chunk = os.read(stdout_r, 4096)
                if not chunk:
                    break
                out_chunks.append(chunk)
            os.close(stdout_r)
        if stderr_w is not None:
            os.close(stderr_w)
            while True:
                chunk = os.read(stderr_r, 4096)
                if not chunk:
                    break
                err_chunks.append(chunk)
            os.close(stderr_r)

        _, status = os.waitpid(pid, 0)
        if os.WIFEXITED(status):
            rc = os.WEXITSTATUS(status)
        elif os.WIFSIGNALED(status):
            rc = -os.WTERMSIG(status)
        else:
            rc = 1

        stdout_bytes = b"".join(out_chunks) if capture else None
        stderr_bytes = b"".join(err_chunks) if capture else None
        return rc, stdout_bytes, stderr_bytes


def run(args, input=None, capture_output=False, check=False, text=False, **kwargs):
    """Run a command and return a CompletedProcess.

    Minimal clean-room implementation supporting the most common subset of
    arguments: input bytes/text, capture_output, check, and text mode.
    """
    stdin_bytes = None
    if input is not None:
        if isinstance(input, str):
            stdin_bytes = input.encode("utf-8")
        else:
            stdin_bytes = bytes(input)

    rc, out, err = _run_via_fork(
        args, stdin_bytes=stdin_bytes, capture=capture_output
    )

    if text and capture_output:
        if out is not None:
            out = out.decode("utf-8", "replace")
        if err is not None:
            err = err.decode("utf-8", "replace")

    cp = CompletedProcess(args, rc, stdout=out, stderr=err)
    if check and rc != 0:
        raise CalledProcessError(rc, args, output=out, stderr=err)
    return cp


def check_output(args, input=None, text=False, **kwargs):
    """Run a command, check the return code, and return its stdout."""
    cp = run(args, input=input, capture_output=True, check=True, text=text)
    return cp.stdout


def call(args, **kwargs):
    """Run a command and return its exit code."""
    rc, _, _ = _run_via_fork(args, capture=False)
    return rc


def check_call(args, **kwargs):
    """Run a command and raise CalledProcessError if it fails."""
    rc = call(args, **kwargs)
    if rc != 0:
        raise CalledProcessError(rc, args)
    return 0


# ---------------------------------------------------------------------------
# Invariant probe functions.  Each returns True to confirm that the
# corresponding subprocess feature is present in this clean-room module.
# ---------------------------------------------------------------------------

def subprocess2_run():
    """Verify that the run() entrypoint and CompletedProcess type exist."""
    if not callable(run):
        return False
    cp = CompletedProcess(["true"], 0, stdout=b"", stderr=b"")
    if cp.returncode != 0:
        return False
    if cp.args != ["true"]:
        return False
    # Confirm check_returncode is wired up.
    bad = CompletedProcess(["false"], 1)
    try:
        bad.check_returncode()
    except CalledProcessError:
        return True
    return False


def subprocess2_check_output():
    """Verify that check_output() exists and that CalledProcessError is wired."""
    if not callable(check_output):
        return False
    err = CalledProcessError(2, ["x"], output=b"o", stderr=b"e")
    if err.returncode != 2 or err.cmd != ["x"]:
        return False
    if err.output != b"o" or err.stderr != b"e":
        return False
    return True


def subprocess2_pipe():
    """Verify that PIPE/STDOUT/DEVNULL constants are defined and distinct."""
    if PIPE != -1:
        return False
    if STDOUT != -2:
        return False
    if DEVNULL != -3:
        return False
    if len({PIPE, STDOUT, DEVNULL}) != 3:
        return False
    return True


__all__ = [
    "PIPE",
    "STDOUT",
    "DEVNULL",
    "CalledProcessError",
    "CompletedProcess",
    "run",
    "call",
    "check_call",
    "check_output",
    "subprocess2_run",
    "subprocess2_check_output",
    "subprocess2_pipe",
]