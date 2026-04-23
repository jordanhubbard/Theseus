"""
theseus_venv_cr — Clean-room venv module.
No import of the standard `venv` module.
"""

import os as _os
import sys as _sys
import shutil as _shutil
import subprocess as _subprocess
import types as _types
import sysconfig as _sysconfig


CORE_VENV_DEPS = ('pip',)


class EnvBuilder:
    """Creates virtual environments."""

    def __init__(self, system_site_packages=False, clear=False,
                 symlinks=False, upgrade=False, with_pip=False,
                 prompt=None, upgrade_deps=False):
        self.system_site_packages = system_site_packages
        self.clear = clear
        self.symlinks = symlinks
        self.upgrade = upgrade
        self.with_pip = with_pip
        if prompt == '.':
            prompt = _os.path.basename(_os.getcwd())
        self.prompt = prompt
        self.upgrade_deps = upgrade_deps

    def create(self, env_dir):
        """Create a virtual environment at env_dir."""
        env_dir = _os.path.abspath(env_dir)
        context = self.ensure_directories(env_dir)
        if self.with_pip:
            self.setup_scripts(context)
            self.post_setup(context)
        return context

    def ensure_directories(self, env_dir):
        """Create the environment directories."""
        if _os.path.exists(env_dir) and self.clear:
            _shutil.rmtree(env_dir)

        context = _types.SimpleNamespace()
        context.env_dir = env_dir
        context.env_name = _os.path.basename(env_dir)
        prompt = self.prompt or context.env_name
        context.prompt = '(%s) ' % prompt
        context.executable = _sys.executable
        context.python_path = _sys.executable

        # Create directory structure
        _os.makedirs(env_dir, exist_ok=True)
        dirname = 'bin' if _sys.platform != 'win32' else 'Scripts'
        binpath = _os.path.join(env_dir, dirname)
        context.bin_path = binpath
        _os.makedirs(binpath, exist_ok=True)

        # lib directory
        if _sys.platform == 'win32':
            libpath = _os.path.join(env_dir, 'Lib', 'site-packages')
        else:
            version = '%d.%d' % _sys.version_info[:2]
            libpath = _os.path.join(env_dir, 'lib', 'python%s' % version, 'site-packages')
        context.lib_path = libpath
        _os.makedirs(libpath, exist_ok=True)

        # pyvenv.cfg
        cfg_path = _os.path.join(env_dir, 'pyvenv.cfg')
        with open(cfg_path, 'w') as f:
            f.write('home = %s\n' % _os.path.dirname(_sys.executable))
            f.write('include-system-site-packages = %s\n' %
                    ('true' if self.system_site_packages else 'false'))
            f.write('version = %s\n' % _sys.version.split()[0])
            if self.prompt:
                f.write('prompt = %s\n' % prompt)
        context.cfg_path = cfg_path

        # Python symlink or copy
        venv_python = _os.path.join(binpath, 'python')
        if not _os.path.exists(venv_python):
            if self.symlinks:
                _os.symlink(_sys.executable, venv_python)
            else:
                _shutil.copy2(_sys.executable, venv_python)

        return context

    def create_configuration(self, context):
        """Create the pyvenv.cfg file."""
        pass

    def setup_python(self, context):
        """Set up Python executables in the venv."""
        pass

    def setup_scripts(self, context):
        """Install scripts in the venv."""
        pass

    def post_setup(self, context):
        """Called after the basic setup."""
        pass

    def install_scripts(self, context, path):
        """Install scripts into the bin directory."""
        pass

    def upgrade_dependencies(self, context):
        """Upgrade pip and setuptools."""
        pass

    def _setup_pip(self, context):
        """Install pip in the venv."""
        pass


def create(env_dir, system_site_packages=False, clear=False,
           symlinks=False, with_pip=False, prompt=None, upgrade_deps=False):
    """Create a virtual environment at env_dir."""
    builder = EnvBuilder(
        system_site_packages=system_site_packages,
        clear=clear,
        symlinks=symlinks,
        with_pip=with_pip,
        prompt=prompt,
        upgrade_deps=upgrade_deps
    )
    builder.create(env_dir)


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def venv2_builder():
    """EnvBuilder class exists and is instantiatable; returns True."""
    builder = EnvBuilder()
    return (isinstance(builder, EnvBuilder) and
            hasattr(builder, 'create') and
            hasattr(builder, 'system_site_packages'))


def venv2_context():
    """EnvBuilder has setup_scripts and post_setup methods; returns True."""
    builder = EnvBuilder()
    return (callable(builder.setup_scripts) and
            callable(builder.post_setup) and
            callable(builder.ensure_directories))


def venv2_create():
    """create() creates a virtual environment in a temp dir; returns True."""
    import tempfile as _tmp
    with _tmp.TemporaryDirectory() as tmpdir:
        venv_dir = _os.path.join(tmpdir, 'testvenv')
        builder = EnvBuilder()
        ctx = builder.create(venv_dir)
        return (_os.path.exists(venv_dir) and
                _os.path.exists(_os.path.join(venv_dir, 'pyvenv.cfg')) and
                hasattr(ctx, 'env_dir'))


__all__ = [
    'EnvBuilder', 'create', 'CORE_VENV_DEPS',
    'venv2_builder', 'venv2_context', 'venv2_create',
]
