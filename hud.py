#!/usr/bin/env python3

import os
import shutil
import re
import ssl
from zipfile import ZipFile
from urllib.request import urlopen
from io import BytesIO
from sys import argv, exit, platform
from tempfile import mkdtemp

# this will be true even in posix-like environments on windows
WINDOWS = (
    os.name == 'nt' or
    platform == 'msys' or
    platform == 'cygwin'
)


# path to steamapps folder
STEAMAPPS = os.path.normpath(os.path.join(
    # while native windows python normalizes environment variable names to
    # uppercase, msys does not. this capitalization works on my machine
    os.path.join(
        os.environ.get('ProgramFiles(x86)', os.environ['PROGRAMFILES']),
        'Steam'
    )
    if WINDOWS else
    os.path.join(os.environ['HOME'], '.steam', 'steam'),

    # steamapps is camelcase on windows, but not linux
    'steamapps'
))

# path to TF2
TF = os.path.join(STEAMAPPS, 'common', 'Team Fortress 2')

if WINDOWS and os.name == 'posix':
    TF = TF.replace('\\', '/')
    if platform == 'msys':
        TF = re.sub(r'([a-zA-Z]):/', r'/\1/', TF)
    elif platform == 'cygwin':
        TF = re.sub(r'([a-zA-Z]):/', r'/cygdrive/\1/', TF)

# path to custom directory
CUSTOM = os.path.join(TF, 'tf', 'custom')
# path to VPK executable
VPK = os.path.join(TF, 'bin', 'vpk.exe' if WINDOWS else 'vpk_linux32')


class NoCfgException(Exception):
    def __init__(self, e, cfg_name):
        super().__init__(e)
        self.cfg_name = cfg_name

    def __str__(self):
        return '\n'.join([
            'unable to load configuration file {}:'.format(self.cfg_name),
            super().__str__()
        ])


class Hud:
    def __init__(self, name):
        self.name = name

        self.wd = None

        self.config = {}
        cfg_name = name + '.cfg'
        try:
            with open(os.path.join(cfg_name)) as f:
                exec(compile(f.read(), cfg_name, 'exec'), self.config)
        except Exception as e:
            raise NoCfgException(e, cfg_name)

        self.zip_url = 'https://github.com/{}/archive/master.zip'.format(
            self.config['GITHUB']
        )
        self.repo_name = self.config['GITHUB'].split('/')[-1] + '-master'

    def here(self, path):
        return os.path.join(self.working, os.path.normpath(path))

    def here_fonts(self, path):
        return os.path.join(self.working_fonts, os.path.normpath(path))

    def fetch(self):
        self.clean()

        self.wd = mkdtemp()

        self.repo = os.path.join(self.wd, self.name)

        self.working = os.path.join(self.wd, self.name + '-nofonts')
        self.working_fonts = os.path.join(self.wd, self.name + '-fonts')

        with urlopen(self.zip_url) as z:
            # the BytesIO wrapper allows seek to work
            zf = ZipFile(BytesIO(z.read()))

        if self.config.get('ROOT', os.path.curdir) == os.path.curdir:
            zf.extractall(self.wd)
            os.rename(os.path.join(self.wd, self.repo_name), self.working)
        else:
            prefix = self.repo_name + '/' + self.config['ROOT'] + '/'
            for info in zf.infolist():
                if info.filename.startswith(prefix):
                    zf.extract(info, self.wd)
            os.rename(
                os.path.join(self.wd, *prefix.split('/')),
                os.path.join(self.wd, self.working)
            )
            shutil.rmtree(os.path.join(self.wd, self.repo_name))

    def clean(self):
        if self.wd is not None:
            shutil.rmtree(self.wd)
        self.wd = None

    def configure(self):
        if self.wd is None:
            self.fetch()

        if self.config.get('VPK', True):
            fonts = []
            font_extensions = ['ttf', 'otf', 'fon']
            os.chdir(self.working)
            for folder, dirs, files in os.walk('.'):
                if ".git" in dirs:
                    shutil.rmtree(os.path.join(folder, ".git"))
                    dirs.remove(".git")
                for name in files:
                    if name.split(".")[-1].lower() in font_extensions:
                        fonts.append((folder, name))
            os.chdir(self.wd)

            if len(fonts) != 0:
                os.mkdir(self.working_fonts)
                for folder, font in fonts:
                    source = self.here(folder)
                    dest = self.here_fonts(folder)
                    os.makedirs(dest, exist_ok=True)
                    shutil.move(os.path.join(source, font), dest)
                    if not any(map(
                        lambda n: n != os.path.curdir and n != os.path.pardir,
                        os.listdir(source)
                    )):
                        os.rmdir(source)

        for source, dest in map(
            lambda *s: (self.here(p) for p in s),
            self.config.get('MOVE', [])
        ):
            if os.isdir(dest):
                dest = os.path.join(dest, os.path.basename(source))
            os.replace(source, dest)

        for filename, dest in self.config.get('INSTALL', []):
            filename = os.path.normpath(filename)
            dest = self.here(dest)
            if os.path.isfile(dest):
                os.unlink(dest)
            if os.path.isdir(filename):
                shutil.copytree(filename, dest)
            else:
                shutil.copy2(filename, dest)

        for script, repl, filename in self.config.get('REGEX', []):
            with open(self.here(filename), 'r') as f:
                contents = f.read()
            with open(self.here(filename), 'w') as f:
                f.write(re.sub(script, repl, contents))

        for filename in map(self.here, self.config.get('DELETE', [])):
            if os.path.isdir(filename):
                shutil.rmtree(filename)
            elif os.path.exists(filename):
                os.unlink(filename)

    def install(self):
        # configure can be intentionally skipped by calling fetch and install.
        if self.wd is None:
            self.configure()
        self.uninstall()

        if self.config.get('VPK', True):
            vpk = self.working + '.vpk'
            if os.path.isfile(vpk):
                os.unlink(vpk)
            check_call([VPK, self.working])
            shutil.copy2(self.working + '.vpk', CUSTOM)
        else:
            shutil.copytree(
                self.working,
                os.path.join(CUSTOM, os.path.basename(self.working))
            )

        if os.path.exists(self.working_fonts):
            shutil.copytree(
                self.working_fonts,
                os.path.join(CUSTOM, os.path.basename(self.working_fonts))
            )

    def uninstall(self):
        for suffix in '-nofonts', '-fonts':
            folder = os.path.join(CUSTOM, self.name + suffix)
            vpk = folder + '.vpk'

            if os.path.isfile(vpk):
                os.unlink(vpk)

            if os.path.exists(folder):
                if os.path.isdir(folder):
                    shutil.rmtree(folder)
                else:
                    os.unlink(folder)

__all__ = ['Hud', 'NoCfgException']

if __name__ == '__main__':
    if len(argv) != 3:
        print('usage: {} (install|uninstall) <hud>'.format(argv[0]))
        exit(1)

    print('Constants:')
    print('os.name:', repr(os.name))
    print('sys.platform:', repr(platform))
    print('WINDOWS:', repr(WINDOWS), end='\n\n')

    print('TF:', repr(TF))
    print('os.path.isdir(TF):', repr(os.path.isdir(TF)), end='\n\n')

    print('CUSTOM:', repr(CUSTOM))
    print('os.path.isdir(CUSTOM):', repr(os.path.isdir(CUSTOM)), end='\n\n')

    print('VPK:', repr(VPK))
    print('os.path.isfile(VPK):', repr(os.path.isfile(VPK)), end='\n\n')

    input('Press enter to continue')

    operation, hud_name = argv[1:]
    try:
        hud = Hud(hud_name)
    except NoCfgException as e:
        print('fatal: ' + str(e))
        exit(1)

    if operation == 'install':
        print('fetching and unpacking zip file...')
        hud.fetch()

        print('temporary directory:', hud.wd)

        print('applying configuration...')
        hud.configure()

        dest = os.path.join(CUSTOM, os.path.basename(hud.working))
        if os.path.exists(dest) or os.path.exists(dest + '.vpk'):
            if not input(
                'Existing installation will be replaced. Continue? (y/n) '
            ).strip().lower().startswith('y'):
                print('Abort. Cleaning up...')
                hud.clean()
                exit(1)

        print('installing...')
        hud.install()

        print('cleaning up...')
        hud.clean()

    elif operation == 'uninstall':
        print('uninstalling...')
        hud.uninstall()

    else:
        print('fatal: invalid operation', operation)
        exit(1)
