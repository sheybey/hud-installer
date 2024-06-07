#!/usr/bin/env python3

import os
import shutil
import re
from zipfile import ZipFile
from urllib.request import urlopen
from io import BytesIO
from tempfile import mkdtemp
from subprocess import check_call


class NoConfigError(Exception):
    def __init__(self, cfg_name):
        super().__init__('unable to load configuration file {}'.format(cfg_name))
        self.cfg_name = cfg_name


class Hud:
    def __init__(self, name, destdir, vpk_exe=None):
        self.name = name
        self.destdir = destdir

        self.wd = None

        self.config = {}
        cfg_name = name + '.cfg'
        try:
            with open(os.path.join(cfg_name)) as f:
                exec(compile(f.read(), cfg_name, 'exec'), self.config)
        except Exception as e:
            raise NoConfigError(cfg_name) from e

        if self.config.get('VPK', True):
            if vpk_exe is None:
                raise ValueError('no vpk executable')
            self.vpk_exe = vpk_exe

        ref = self.config.get('REF', 'master')

        self.zip_url = 'https://github.com/{}/archive/{}.zip'.format(
            self.config['GITHUB'],
            ref
        )
        self.repo_name = self.config['GITHUB'].split('/')[-1] + '-' + ref

    def here(self, path):
        return os.path.join(self.working, os.path.normpath(path))

    def here_fonts(self, path):
        return os.path.join(self.working_fonts, os.path.normpath(path))

    def fetch(self):
        self.clean()

        self.wd = mkdtemp()

        self.repo = os.path.join(self.wd, self.name)

        self.working = os.path.join(self.wd, self.name)
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

        make_vpk = self.config.get('VPK', True)
        if make_vpk:
            fonts = []
            font_extensions = ['ttf', 'otf', 'fon']
            for folder, dirs, files in os.walk(self.working):
                if ".git" in dirs:
                    shutil.rmtree(os.path.join(folder, ".git"))
                    dirs.remove(".git")
                for name in files:
                    if name.split(".")[-1].lower() in font_extensions:
                        fonts.append((
                            os.path.relpath(folder, start=self.working),
                            name
                        ))

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

        for source, dest in self.config.get('MOVE', []):
            try:
                srcpath = self.here(source)
                destpath = self.here(dest)
                if os.path.isdir(dest):
                    destpath = os.path.join(dest, os.path.basename(srcpath))
                os.replace(srcpath, destpath)
            except Exception as e:
                print('Warning: Failed to apply MOVE "{}" -> "{}": {}'.format(source, dest, e))

        for filename, dest in self.config.get('INSTALL', []):
            try:
                filepath = os.path.normpath(filename)
                destpath = self.here(dest)
                if os.path.isfile(destpath):
                    os.unlink(destpath)
                if os.path.isdir(filepath):
                    shutil.copytree(filepath, destpath)
                else:
                    shutil.copy2(filepath, destpath)
            except Exception as e:
                print('Warning: Failed to apply INSTALL "{}" -> "{}": {}'.format(filename, dest, e))


        for script, repl, filename in self.config.get('REGEX', []):
            try:
                filepath = self.here(filename)
                with open(filepath, 'r') as f:
                    contents = f.read()
                contents = re.sub(script, repl, contents)
                with open(filepath, 'w') as f:
                    f.write(contents)
            except Exception as e:
                print('Warning: Failed to apply REGEX "{}" -> "{}" on {}: {}'.format(script, repl, filename, e))

        for filename in self.config.get('DELETE', []):
            try:
                filepath = self.here(filename)
                if os.path.isdir(filepath):
                    shutil.rmtree(filepath)
                elif os.path.exists(filepath):
                    os.unlink(filepath)
            except Exception as e:
                print('Warning: Failed to apply DELETE "{}": {}'.format(filename, e))


    def install(self):
        # configure can be intentionally skipped by calling fetch and install.
        if self.wd is None:
            self.configure()
        self.uninstall()

        if self.config.get('VPK', True):
            print('compiling vpk...')
            vpk = self.working + '.vpk'
            if os.path.isfile(vpk):
                os.unlink(vpk)
            env = os.environ.copy()
            # this environment variable is necessary on linux and harmless on
            # windows
            env['LD_LIBRARY_PATH'] = os.path.abspath(
                os.path.dirname(self.vpk_exe))
            check_call([self.vpk_exe, self.working], env=env)
            shutil.copy2(self.working + '.vpk', self.destdir)
        else:
            shutil.copytree(
                self.working,
                os.path.join(self.destdir, os.path.basename(self.working))
            )

        if os.path.exists(self.working_fonts):
            shutil.copytree(
                self.working_fonts,
                os.path.join(
                    self.destdir,
                    os.path.basename(self.working_fonts)
                )
            )

    def uninstall(self):
        folder = os.path.join(self.destdir, self.name)
        for dest in [folder, folder + '-nofonts', folder + '.vpk']:
            if os.path.exists(dest):
                if os.path.isdir(dest):
                    shutil.rmtree(dest)
                else:
                    os.unlink(dest)

__all__ = ['Hud', 'NoConfigError']
