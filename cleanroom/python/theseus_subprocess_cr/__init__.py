"""
theseus_subprocess_cr — Clean-room subprocess module.
No import of the standard `subprocess` module.
"""

import os as _os
import sys as _sys
import io as _io
import signal as _signal
import threading as _threading
import time as _time
import errno as _errno

PIPE = -1
STDOUT = -2
DEVNULL = -3

STD_INPUT_HANDLE = -10
STD_OUTPUT_HANDLE = -11
STD_ERROR_HANDLE = -12

SW_HIDE = 0
STARTF_USESTDHANDLES = 0x00000100
STARTF_USESHOWWINDOW = 0x00000001

ABOVE_NORMAL_PRIORITY_CLASS = 0x00008000
BELOW_NORMAL_PRIORITY_CLASS = 0x00004000
HIGH_PRIORITY_CLASS = 0x00000080
IDLE_PRIORITY_CLASS = 0x00000040
NORMAL_PRIORITY_CLASS = 0x00000020
REALTIME_PRIORITY_CLASS = 0x00000100

CREATE_NEW_CONSOLE = 0x00000010
CREATE_NEW_PROCESS_GROUP = 0x00000200
CREATE_NO_WINDOW = 0x08000000
CREATE_DEFAULT_ERROR_MODE = 0x04000000
CREATE_BREAKAWAY_FROM_JOB = 0x01000000

STD_OUTPUT = 1
STD_ERROR = 2
STD_INPUT = 0


class SubprocessError(Exception):
    pass


class CalledProcessError(SubprocessError):
    def __init__(self, returncode, cmd, output=None, stderr=None):
        self.returncode = returncode
        self.cmd = cmd
        self.output = output
        self.stderr = stderr

    def __str__(self):
        if self.returncode and self.returncode < 0:
            try:
                return "Command '%s' died with %r." % (
                    self.cmd, _signal.Signals(-self.returncode))
            except ValueError:
                return "Command '%s' died with unknown signal %d." % (self.cmd, -self.returncode)
        else:
            return "Command '%s' returned non-zero exit status %d." % (self.cmd, self.returncode)

    @property
    def stdout(self):
        return self.output

    @stdout.setter
    def stdout(self, value):
        self.output = value


class TimeoutExpired(SubprocessError):
    def __init__(self, cmd, timeout, output=None, stderr=None):
        self.cmd = cmd
        self.timeout = timeout
        self.output = output
        self.stderr = stderr

    def __str__(self):
        return "Command '%s' timed out after %s seconds" % (self.cmd, self.timeout)

    @property
    def stdout(self):
        return self.output

    @stdout.setter
    def stdout(self, value):
        self.output = value


class CompletedProcess:
    """A process that has finished running."""

    def __init__(self, args, returncode, stdout=None, stderr=None):
        self.args = args
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

    def __repr__(self):
        args = ['args={!r}'.format(self.args),
                'returncode={!r}'.format(self.returncode)]
        if self.stdout is not None:
            args.append('stdout={!r}'.format(self.stdout))
        if self.stderr is not None:
            args.append('stderr={!r}'.format(self.stderr))
        return '{}({})'.format(type(self).__name__, ', '.join(args))

    def check_returncode(self):
        if self.returncode:
            raise CalledProcessError(self.returncode, self.args, self.stdout, self.stderr)


class Popen:
    """Execute a child program in a new process."""

    def __init__(self, args, bufsize=-1, executable=None,
                 stdin=None, stdout=None, stderr=None,
                 preexec_fn=None, close_fds=True,
                 shell=False, cwd=None, env=None, universal_newlines=None,
                 startupinfo=None, creationflags=0, restore_signals=True,
                 start_new_session=False, pass_fds=(), *,
                 user=None, group=None, extra_groups=None,
                 encoding=None, errors=None, text=None,
                 umask=-1, pipesize=-1, process_group=None):
        self.stdin = None
        self.stdout = None
        self.stderr = None
        self.pid = None
        self.returncode = None
        self.args = args

        if text is None and universal_newlines is not None:
            text = universal_newlines
        if text:
            encoding = encoding or _sys.getdefaultencoding()

        if isinstance(args, str):
            if shell:
                args = ['/bin/sh', '-c', args]
            else:
                import shlex
                args = shlex.split(args)
        elif shell:
            args = ['/bin/sh', '-c'] + list(args)

        c2pread = c2pwrite = -1
        p2cread = p2cwrite = -1
        errread = errwrite = -1
        _parent_close = []  # child-facing pipe ends to close in parent after fork

        if stdin is None:
            pass  # child inherits parent stdin
        elif stdin == PIPE:
            p2cread, p2cwrite = _os.pipe()
            _parent_close.append(p2cread)
        elif stdin == DEVNULL:
            p2cread = _os.open(_os.devnull, _os.O_RDONLY)
            _parent_close.append(p2cread)
        elif isinstance(stdin, int):
            p2cread = stdin
        else:
            p2cread = stdin.fileno()

        if stdout is None:
            pass  # child inherits parent stdout
        elif stdout == PIPE:
            c2pread, c2pwrite = _os.pipe()
            _parent_close.append(c2pwrite)
        elif stdout == DEVNULL:
            c2pwrite = _os.open(_os.devnull, _os.O_WRONLY)
            _parent_close.append(c2pwrite)
        elif isinstance(stdout, int):
            c2pwrite = stdout
        else:
            c2pwrite = stdout.fileno()

        if stderr is None:
            pass  # child inherits parent stderr
        elif stderr == PIPE:
            errread, errwrite = _os.pipe()
            _parent_close.append(errwrite)
        elif stderr == STDOUT:
            errwrite = c2pwrite
        elif stderr == DEVNULL:
            errwrite = _os.open(_os.devnull, _os.O_WRONLY)
            _parent_close.append(errwrite)
        elif isinstance(stderr, int):
            errwrite = stderr
        else:
            errwrite = stderr.fileno()

        if cwd is None:
            cwd = _os.getcwd()

        self.pid = _os.fork()
        if self.pid == 0:
            try:
                if p2cread != -1 and p2cread != 0:
                    _os.dup2(p2cread, 0)
                    _os.close(p2cread)
                if c2pwrite != -1 and c2pwrite != 1:
                    _os.dup2(c2pwrite, 1)
                    if c2pwrite != errwrite:
                        _os.close(c2pwrite)
                if errwrite != -1 and errwrite != 2:
                    _os.dup2(errwrite, 2)
                    _os.close(errwrite)

                if preexec_fn:
                    preexec_fn()

                if env is not None:
                    _os.execvpe(args[0], args, env)
                else:
                    _os.execvp(args[0], args)
            except Exception:
                pass
            finally:
                _os._exit(255)

        # Parent: close child-facing ends of pipes
        for fd in _parent_close:
            try:
                _os.close(fd)
            except OSError:
                pass

        if p2cwrite != -1:
            self.stdin = _os.fdopen(p2cwrite, 'wb', bufsize)
        if c2pread != -1:
            if encoding or errors or text:
                self.stdout = _io.TextIOWrapper(_os.fdopen(c2pread, 'rb', bufsize), encoding=encoding, errors=errors)
            else:
                self.stdout = _os.fdopen(c2pread, 'rb', bufsize)
        if errread != -1:
            if encoding or errors or text:
                self.stderr = _io.TextIOWrapper(_os.fdopen(errread, 'rb', bufsize), encoding=encoding, errors=errors)
            else:
                self.stderr = _os.fdopen(errread, 'rb', bufsize)

    def communicate(self, input=None, timeout=None):
        stdout = None
        stderr = None

        if timeout is not None:
            end_time = _time.monotonic() + timeout

        if input is not None:
            if self.stdin:
                self.stdin.write(input)
                self.stdin.close()
        else:
            if self.stdin:
                self.stdin.close()

        if self.stdout:
            stdout = self.stdout.read()
            self.stdout.close()
        if self.stderr:
            stderr = self.stderr.read()
            self.stderr.close()

        self.wait()
        return stdout, stderr

    def wait(self, timeout=None):
        if self.returncode is not None:
            return self.returncode
        try:
            pid, status = _os.waitpid(self.pid, 0)
            if _os.WIFEXITED(status):
                self.returncode = _os.WEXITSTATUS(status)
            elif _os.WIFSIGNALED(status):
                self.returncode = -_os.WTERMSIG(status)
            else:
                self.returncode = status
        except ChildProcessError:
            self.returncode = 0
        return self.returncode

    def poll(self):
        if self.returncode is not None:
            return self.returncode
        try:
            pid, status = _os.waitpid(self.pid, _os.WNOHANG)
            if pid == 0:
                return None
            if _os.WIFEXITED(status):
                self.returncode = _os.WEXITSTATUS(status)
            elif _os.WIFSIGNALED(status):
                self.returncode = -_os.WTERMSIG(status)
            else:
                self.returncode = status
        except ChildProcessError:
            self.returncode = 0
        return self.returncode

    def send_signal(self, sig):
        if self.returncode is not None:
            return
        _os.kill(self.pid, sig)

    def terminate(self):
        self.send_signal(_signal.SIGTERM)

    def kill(self):
        self.send_signal(_signal.SIGKILL)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.stdin:
            self.stdin.close()
        try:
            if exc_type:
                self.communicate()
            else:
                self.wait()
        except:
            pass
        if self.stdout:
            self.stdout.close()
        if self.stderr:
            self.stderr.close()

    def __del__(self):
        if self.stdin:
            try:
                self.stdin.close()
            except:
                pass
        if self.stdout:
            try:
                self.stdout.close()
            except:
                pass
        if self.stderr:
            try:
                self.stderr.close()
            except:
                pass


def run(args, *, stdin=None, input=None, capture_output=False, timeout=None,
        check=False, **kwargs):
    """Run a command described by args."""
    if input is not None:
        if kwargs.get('stdin') is not None:
            raise ValueError('stdin and input arguments may not both be used.')
        kwargs['stdin'] = PIPE
    if capture_output:
        if kwargs.get('stdout') is not None or kwargs.get('stderr') is not None:
            raise ValueError('stdout and stderr arguments may not be used with capture_output.')
        kwargs['stdout'] = PIPE
        kwargs['stderr'] = PIPE
    with Popen(args, stdin=stdin, **kwargs) as process:
        try:
            stdout, stderr = process.communicate(input, timeout=timeout)
        except TimeoutExpired as exc:
            process.kill()
            exc.stdout, exc.stderr = process.communicate()
            raise
        except:
            process.kill()
            raise
        retcode = process.poll()
        if check and retcode:
            raise CalledProcessError(retcode, process.args, stdout, stderr)
    return CompletedProcess(process.args, retcode, stdout, stderr)


def call(*popenargs, timeout=None, **kwargs):
    """Run command with arguments and return its return code."""
    with Popen(*popenargs, **kwargs) as p:
        try:
            return p.wait(timeout=timeout)
        except:
            p.kill()
            raise


def check_call(*popenargs, timeout=None, **kwargs):
    """Run command and raise CalledProcessError if non-zero exit."""
    retcode = call(*popenargs, timeout=timeout, **kwargs)
    if retcode:
        cmd = kwargs.get('args', popenargs[0] if popenargs else None)
        raise CalledProcessError(retcode, cmd)
    return 0


def check_output(*popenargs, timeout=None, **kwargs):
    """Run command with arguments and return its output."""
    if 'stdout' in kwargs:
        raise ValueError('stdout argument not allowed, it will be overridden.')
    stdout = run(*popenargs, stdout=PIPE, timeout=timeout, check=True, **kwargs).stdout
    return stdout


def getoutput(cmd):
    """Return output of shell command."""
    return getstatusoutput(cmd)[1]


def getstatusoutput(cmd):
    """Return (exitcode, output) of shell command."""
    with Popen(cmd, shell=True, stdout=PIPE, stderr=STDOUT) as process:
        try:
            data, _ = process.communicate()
            exitcode = process.returncode
        except:
            process.kill()
            raise
    if data[-1:] == b'\n':
        data = data[:-1]
    return exitcode, data.decode() if data else ''


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def subprocess2_run():
    """run() executes a command and returns CompletedProcess; returns True."""
    result = run(['echo', 'hello'], capture_output=True)
    return isinstance(result, CompletedProcess) and result.returncode == 0


def subprocess2_check_output():
    """check_output() captures stdout from a command; returns True."""
    out = check_output(['echo', 'test'])
    return isinstance(out, bytes) and b'test' in out


def subprocess2_pipe():
    """PIPE constant exists and Popen accepts it; returns True."""
    with Popen(['echo', 'pipe'], stdout=PIPE) as p:
        out, _ = p.communicate()
    return PIPE == -1 and isinstance(out, bytes) and b'pipe' in out


__all__ = [
    'Popen', 'CompletedProcess', 'CalledProcessError', 'TimeoutExpired',
    'SubprocessError', 'run', 'call', 'check_call', 'check_output',
    'getoutput', 'getstatusoutput',
    'PIPE', 'STDOUT', 'DEVNULL',
    'subprocess2_run', 'subprocess2_check_output', 'subprocess2_pipe',
]
