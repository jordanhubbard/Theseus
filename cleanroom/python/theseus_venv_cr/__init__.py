"""theseus_venv_cr — clean-room reimplementation of a minimal venv-like module.

This module provides a tiny, self-contained surface that mirrors the shape of
the standard library's venv module without importing it. It exposes a
``EnvBuilder`` class, a ``Context`` helper, and a ``create`` convenience
function. The invariant probe functions ``venv2_builder``, ``venv2_context``,
and ``venv2_create`` confirm that those primitives behave as expected.
"""

import os
import sys


class Context:
    """Lightweight environment-context record.

    Mirrors the attributes commonly attached to the context object that
    ``venv.EnvBuilder`` produces during environment creation.
    """

    def __init__(self, env_dir=None):
        self.env_dir = env_dir
        self.env_name = os.path.basename(env_dir) if env_dir else None
        self.prompt = "(%s) " % self.env_name if self.env_name else None
        self.python_dir = os.path.dirname(sys.executable) if sys.executable else ""
        self.python_exe = os.path.basename(sys.executable) if sys.executable else ""
        if env_dir:
            if os.name == "nt":
                self.bin_path = os.path.join(env_dir, "Scripts")
            else:
                self.bin_path = os.path.join(env_dir, "bin")
            self.bin_name = os.path.basename(self.bin_path)
            self.env_exe = os.path.join(self.bin_path, self.python_exe or "python")
            self.cfg_path = os.path.join(env_dir, "pyvenv.cfg")
        else:
            self.bin_path = None
            self.bin_name = None
            self.env_exe = None
            self.cfg_path = None

    def as_dict(self):
        return {
            "env_dir": self.env_dir,
            "env_name": self.env_name,
            "prompt": self.prompt,
            "python_dir": self.python_dir,
            "python_exe": self.python_exe,
            "bin_path": self.bin_path,
            "bin_name": self.bin_name,
            "env_exe": self.env_exe,
            "cfg_path": self.cfg_path,
        }


class EnvBuilder:
    """Clean-room equivalent of ``venv.EnvBuilder``.

    Holds configuration flags that control how a virtual environment would be
    materialised. The class is intentionally inert with respect to the
    filesystem unless ``create`` is called.
    """

    def __init__(
        self,
        system_site_packages=False,
        clear=False,
        symlinks=False,
        upgrade=False,
        with_pip=False,
        prompt=None,
        upgrade_deps=False,
    ):
        self.system_site_packages = bool(system_site_packages)
        self.clear = bool(clear)
        self.symlinks = bool(symlinks)
        self.upgrade = bool(upgrade)
        self.with_pip = bool(with_pip)
        self.prompt = prompt
        self.upgrade_deps = bool(upgrade_deps)

    # ------------------------------------------------------------------
    # Context creation
    # ------------------------------------------------------------------
    def ensure_directories(self, env_dir):
        """Create a Context describing the layout for ``env_dir``.

        In this clean-room implementation we build the descriptor in memory
        only; we do not touch the filesystem unless ``create`` is invoked.
        """
        ctx = Context(env_dir)
        if self.prompt is not None:
            ctx.prompt = "(%s) " % self.prompt
        return ctx

    # ------------------------------------------------------------------
    # Filesystem creation
    # ------------------------------------------------------------------
    def create(self, env_dir):
        """Materialise a minimal virtual-environment-like directory tree."""
        if not env_dir:
            raise ValueError("env_dir must be a non-empty path")
        env_dir = os.path.abspath(env_dir)
        if os.path.exists(env_dir):
            if self.clear:
                self._rm_tree(env_dir)
            elif not self.upgrade and os.listdir(env_dir):
                # Existing non-empty directory and we are not refreshing.
                pass
        os.makedirs(env_dir, exist_ok=True)
        ctx = self.ensure_directories(env_dir)
        os.makedirs(ctx.bin_path, exist_ok=True)
        self._write_cfg(ctx)
        self.post_setup(ctx)
        return ctx

    def _write_cfg(self, ctx):
        lines = [
            "home = %s" % (ctx.python_dir or ""),
            "include-system-site-packages = %s"
            % ("true" if self.system_site_packages else "false"),
            "version = %d.%d.%d" % sys.version_info[:3],
        ]
        if self.prompt is not None:
            lines.append("prompt = %s" % self.prompt)
        with open(ctx.cfg_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")

    def post_setup(self, context):
        """Hook for subclasses; intentionally a no-op here."""
        return None

    @staticmethod
    def _rm_tree(path):
        for root, dirs, files in os.walk(path, topdown=False):
            for name in files:
                try:
                    os.remove(os.path.join(root, name))
                except OSError:
                    pass
            for name in dirs:
                try:
                    os.rmdir(os.path.join(root, name))
                except OSError:
                    pass
        try:
            os.rmdir(path)
        except OSError:
            pass


def create(env_dir, system_site_packages=False, clear=False, symlinks=False,
           with_pip=False, prompt=None, upgrade_deps=False):
    """Convenience wrapper mirroring ``venv.create``."""
    builder = EnvBuilder(
        system_site_packages=system_site_packages,
        clear=clear,
        symlinks=symlinks,
        with_pip=with_pip,
        prompt=prompt,
        upgrade_deps=upgrade_deps,
    )
    return builder.create(env_dir)


# ----------------------------------------------------------------------
# Invariant probes
# ----------------------------------------------------------------------
def venv2_builder():
    b = EnvBuilder(system_site_packages=True, clear=True, prompt="demo")
    if not isinstance(b, EnvBuilder):
        return False
    if b.system_site_packages is not True:
        return False
    if b.clear is not True:
        return False
    if b.prompt != "demo":
        return False
    # Defaults
    d = EnvBuilder()
    if d.system_site_packages or d.clear or d.symlinks or d.with_pip:
        return False
    if d.prompt is not None:
        return False
    return True


def venv2_context():
    ctx = Context("/tmp/example_env")
    if ctx.env_dir != "/tmp/example_env":
        return False
    if ctx.env_name != "example_env":
        return False
    if ctx.prompt != "(example_env) ":
        return False
    if not ctx.bin_path or not ctx.bin_path.startswith("/tmp/example_env"):
        return False
    if not ctx.cfg_path.endswith("pyvenv.cfg"):
        return False
    empty = Context()
    if empty.env_dir is not None or empty.bin_path is not None:
        return False
    return True


def venv2_create():
    import tempfile

    tmp = tempfile.mkdtemp(prefix="theseus_venv_cr_")
    target = os.path.join(tmp, "venv")
    try:
        builder = EnvBuilder(prompt="probe")
        ctx = builder.create(target)
        if not isinstance(ctx, Context):
            return False
        if not os.path.isdir(target):
            return False
        if not os.path.isdir(ctx.bin_path):
            return False
        if not os.path.isfile(ctx.cfg_path):
            return False
        with open(ctx.cfg_path, "r", encoding="utf-8") as fh:
            data = fh.read()
        if "include-system-site-packages = false" not in data:
            return False
        if "prompt = probe" not in data:
            return False
        # Top-level convenience function
        target2 = os.path.join(tmp, "venv2")
        ctx2 = create(target2, system_site_packages=True)
        if not os.path.isfile(ctx2.cfg_path):
            return False
        with open(ctx2.cfg_path, "r", encoding="utf-8") as fh:
            data2 = fh.read()
        if "include-system-site-packages = true" not in data2:
            return False
        return True
    finally:
        EnvBuilder._rm_tree(tmp)


__all__ = [
    "Context",
    "EnvBuilder",
    "create",
    "venv2_builder",
    "venv2_context",
    "venv2_create",
]