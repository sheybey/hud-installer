from distutils.core import setup
import py2exe

setup(
    console=[
        {
            'script': 'hud.py',
            'icon_resources': [(1, 'tyrone.ico')]
        }
    ],
    zipfile=None,
    options={
        'py2exe': {
            'bundle_files': 1,
            'unbuffered': True,
            'compressed': True,
            'includes': [
                'imp'
            ],
            'excludes': [
                '_bz2',
                'bz2',
                '_lzma',
                'lzma',
                '_multiprocessing',
                'multiprocessing',
                'pyexpat',
                'select',
                '__future__',
                '_compat_pickle',
                'pickle',
                '_dummy_thread',
                'threading',
                'distutils',
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
                'dummy_threading',
                'ftplib',
                'getopt',
                'getpass',
                'gettext',
                'glob',
                'gzip',
                'inspect',
                'linecache',
                'mimetypes',
                'optparse',
                'selectors',
                'traceback'
            ]
        }
    }
)
