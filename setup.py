import os
from cx_Freeze import setup, Executable

# Dependencies are automatically detected, but it might need
# fine tuning.
build_options = {
    'packages': [
        'imp',
        'ssl',
        'winprocs'
    ],
    'excludes': [
        '_bz2',
        'bz2',
        '_lzma',
        'lzma',
        '_multiprocessing',
        'multiprocessing',
        'pyexpat',
        '_compat_pickle',
        'pickle',
        'distutils',
        'setuptools',
        'html',
        'logging',
        'pydoc_data',
        'unittest',
        'xml',
        '_strptime',
        'argparse',
        'bdb',
        'cmd',
        'difflib',
        'dis',
        'doctest',
        'ftplib',
        'getopt',
        'getpass',
        'gettext',
        'glob',
        'gzip',
        'inspect',
        'mimetypes',
        'optparse'
    ],
    'include_files': [
        'assets',
        'budhud.cfg'
    ]
}

if os.name == 'nt':
    exe_args = {'icon': 'tyrone.ico', 'manifest': 'manifest.xml'}
else:
    exe_args = {'icon': 'tyrone-248.png'}

executables = [Executable('main.py', **exe_args)]


setup(
    name='HUD Installer',
    version = '0.5',
    description = 'Scriptable HUD installer',
    options = dict(build_exe=build_options),
    executables = executables,
)
