#!/usr/bin/env python3

import os
import shutil
import re
from zipfile import ZipFile
from urllib.request import urlopen
from io import BytesIO
from tempfile import mkdtemp
from subprocess import check_call


class NoCfgError(Exception):
    def __init__(self, e, cfg_name):
        super().__init__(e)
        self.cfg_name = cfg_name

    def __str__(self):
        return '\n'.join([
            'unable to load configuration file {}:'.format(self.cfg_name),
            super().__str__()
        ])


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
            raise NoCfgError(e, cfg_name)

        if self.config.get('VPK', True):
            if vpk_exe is None:
                raise ValueError('no vpk executable')
            self.vpk_exe = vpk_exe

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

        for source, dest in map(
            lambda pair: map(self.here, pair),
            self.config.get('MOVE', [])
        ):
            if os.path.isdir(dest):
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

        if self.config.get('CREATE_MISSING', make_vpk):
            print('parsing and normalizing #base references...')
            base_refs = set()
            for folder, subdirs, files in os.walk(self.working):
                # for every .res file
                for res in (f for f in files if f.lower().endswith('.res')):
                    with open(os.path.join(folder, res), 'r') as file:
                        # normalize all base refs and deduplicate them
                        for ref in (
                            m.group(1) for m in (
                                re.match(r'^\s*#base\s*\"?([^"]+)', l)
                                for l in file)
                            if m is not None
                        ):
                            base_refs.add(os.path.realpath(os.path.join(
                                folder, os.path.normpath(
                                    ref.replace('\\', os.sep).strip()))))

            print('creating missing files...')
            for ref in base_refs:
                if not os.path.exists(ref):
                    print('creating ref', os.path.basename(ref))
                    os.makedirs(os.path.dirname(ref), exist_ok=True)
                    with open(ref, 'a'):
                        pass

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
        for suffix in '-nofonts', '-fonts':
            folder = os.path.join(self.destdir, self.name + suffix)
            vpk = folder + '.vpk'

            if os.path.isfile(vpk):
                os.unlink(vpk)

            if os.path.exists(folder):
                if os.path.isdir(folder):
                    shutil.rmtree(folder)
                else:
                    os.unlink(folder)

__all__ = ['Hud', 'NoCfgError']
