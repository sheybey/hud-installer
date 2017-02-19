from distutils.core import setup
import py2exe

RT_MANIFEST = 24

setup(
    console=[
        {
            'script': 'main.py',
            'icon_resources': [(1, 'tyrone.ico')],
            'other_resources': [
                (RT_MANIFEST, 1, open('manifest.xml').read())
            ],
            'version': '0.4.1.1',
            'description': 'Scriptable HUD installer'
        }
    ],
    zipfile=None,
    options={
        'py2exe': {
            'bundle_files': 1,
            'unbuffered': True,
            'compressed': True,
            'includes': [
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
