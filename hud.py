#!/usr/bin/env python3

import os
import shutil
import re
import ssl
from zipfile import ZipFile
from urllib.request import urlopen
from io import BytesIO
from os import path
from sys import argv, exit, platform
from types import MethodType

# this will be true even in posix-like environments on windows
WINDOWS = (
    os.name == 'nt' or
    platform == 'msys' or
    platform == 'cygwin'
)

# path to TF2
TF = os.path.normpath(os.path.join(
    # while native windows python normalizes environment variable names to
    # uppercase, msys does not. this capitalization works on my machine
    os.environ.get('ProgramFiles(x86)', os.environ['PROGRAMFILES'])
    if WINDOWS else
    os.path.join(os.environ['HOME'], '.local', 'share'),

    # steamapps is camelcase on windows, but not linux
    'Steam', 'steamapps', 'common', 'Team Fortress 2'
))

if WINDOWS and os.name == 'posix':
    TF = TF.replace('\\', '/')
    if platform == 'msys':
        TF = re.sub(r'([a-zA-Z]):/', r'/\1/', TF)
    elif platform == 'cygwin':
        TF = re.sub(r'([a-zA-Z]):/', r'/cygdrive/\1/', TF)

# path to custom directory
CUSTOM = os.path.join(TF, 'tf', 'custom')
# path to VPK executable
VPK = os.path.join(TF, 'bin', 'vpk.exe' if WINDOWS else 'vpk')

WD = os.path.abspath(os.environ.get('HUDDIR', os.path.curdir))


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

        self.repo = os.path.join(WD, name)

        self.working = os.path.join(WD, name + '-nofonts')
        self.working_fonts = os.path.join(WD, name + '-fonts')

        self.config = {}
        cfg_name = name + '.cfg'
        try:
            with open(os.path.join(WD, cfg_name)) as f:
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
        self.cleanup()
        with urlopen(self.zip_url) as z:
            # the BytesIO wrapper allows seek to work
            zf = ZipFile(BytesIO(z.read()))

        if self.config.get('ROOT', os.path.curdir) == os.path.curdir:
            zf.extractall(WD)
            os.rename(os.path.join(WD, self.repo_name), self.working)
        else:
            prefix = self.repo_name + '/' + self.config['ROOT'] + '/'
            for info in zf.infolist():
                if info.filename.startswith(prefix):
                    zf.extract(info, WD)
            os.rename(
                os.path.join(WD, *prefix.split('/')),
                os.path.join(WD, self.working)
            )
            shutil.rmtree(os.path.join(WD, self.repo_name))

    def cleanup(self):
        if os.path.isdir(self.working):
            shutil.rmtree(self.working)
        if os.path.isdir(self.working_fonts):
            shutil.rmtree(self.working_fonts)
        if os.path.isfile(self.working + '.vpk'):
            os.unlink(self.working + '.vpk')

    def configure(self):
        if not os.path.isdir(self.working):
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
            os.chdir(WD)

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
        if not os.path.isdir(self.working):
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
    # any method on the Hud class can be called directly with this interface.
    if len(argv) != 3:
        print('usage: {} <operation> <hud>'.format(argv[0]))
        print('\tYou probably want to run {} (un)install <hud>.'.format(
            argv[0])
        )
        print('\tRead the source code for other supported operations.')
        exit(1)

    operation, hud_name = argv[1:]
    try:
        hud = Hud(hud_name)
    except NoCfgException as e:
        print('fatal: ' + str(e))
        exit(1)

    function = getattr(hud, operation, None)
    if not isinstance(function, MethodType):
        print('fatal: invalid operation ' + operation)
        exit()

    print('running {} on {}...'.format(operation, hud_name))
    function()
