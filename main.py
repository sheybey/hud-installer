import os
from typing import Never
import vdf
import sys

from hud import Hud, NoConfigError

def fatal(message) -> Never:
    print('fatal:', message)
    sys.exit(1)


# this will be true even in posix-like environments on windows
WINDOWS = (
    os.name == 'nt' or
    sys.platform == 'msys' or
    sys.platform == 'cygwin'
)

STEAMAPPS = None
# path to steamapps folder
# STEAMAPPS = os.path.normpath(os.path.join(
#     # while native windows python normalizes environment variable names to
#     # uppercase, msys does not. this capitalization works on my machine
#     os.path.join(
#         os.environ.get('ProgramFiles(x86)', os.environ['PROGRAMFILES']),
#         'Steam'
#     )
#     if WINDOWS else
#     os.path.join(os.environ['HOME'], '.steam', 'steam'),

#     # steamapps is camelcase on linux
#     'SteamApps'
# ))
if WINDOWS:
    from winprocs import all_pids, process_exe
    for pid in all_pids():
        try:
            directory, name = os.path.split(process_exe(pid))
            if name.lower() == 'steam.exe':
                STEAMAPPS = os.path.join(directory, 'steamapps')
                break
        except RuntimeError:
            pass
    else:
        fatal('Open steam before trying to install')
else:
    STEAMAPPS = os.path.join(
        os.environ['HOME'],
        '.steam', 'steam', 'steamapps'
    )

# default path to TF2
TF_DEFAULT = os.path.join(STEAMAPPS, 'common', 'Team Fortress 2')

if WINDOWS and os.name == 'posix':
    TF = TF.replace('\\', '/')
    if sys.platform == 'msys':
        TF = re.sub(r'([a-zA-Z]):/', r'/\1/', TF)
    elif sys.platform == 'cygwin':
        TF = re.sub(r'([a-zA-Z]):/', r'/cygdrive/\1/', TF)

if len(sys.argv) < 3:
    print('usage: {} (install|uninstall) [OPTIONS] <hud>'.format(sys.argv[0]))
    sys.exit(1)

options = {'n': False, 'h': False}

operation, *args = sys.argv[1:]
hud_name = None

for arg in args:
    if arg[0] == '-':
        for flag in arg[1:]:
            if flag in options:
                options[flag] = True
            else:
                fatal(f'unrecognized option: {flag}')
    else:
        if hud_name is None:
            hud_name = arg
        else:
            fatal('only one hud can be installed at once')

if hud_name is None:
    fatal('no hud specified')

if not os.path.isdir(STEAMAPPS):
    fatal('can\'t find steam install at {}'.format(STEAMAPPS))

TF = TF_DEFAULT
if not os.path.isdir(TF):
    print('TF2 not in default path, searching...')

    library_folders = os.path.join(STEAMAPPS, 'libraryfolders.vdf')
    try:
        with open(library_folders) as f:
            folders = vdf.parse(f)['LibraryFolders']
    except OSError as e:
        fatal('unable to open {}: {}'.format(library_folders, e))
    except KeyError:
        fatal(library_folders + ' does not contain LibraryFolders key')
    except Exception as e:
        fatal('error while parsing {}: {}'.format(library_folders, e))

    for key in folders:
        if key.isnumeric():
            print('searching library {}'.format(folders[key]))
            STEAMAPPS = os.path.join(
                os.path.normpath(folders[key]),
                'steamapps'
            )
            TF = os.path.join(STEAMAPPS, 'common', 'Team Fortress 2')
            if os.path.isdir(TF):
                break
    else:
        fatal('couldn\'t find TF2')

# path to custom directory
CUSTOM = os.path.join(TF, 'tf', 'custom')
# path to VPK executable
VPK = os.path.join(TF, 'bin', 'vpk.exe' if WINDOWS else 'vpk_linux32')


print('found TF2 at', TF)

if os.path.isfile(VPK):
    hud = Hud(hud_name, CUSTOM, VPK)
else:
    hud = Hud(hud_name, CUSTOM)

if operation == 'install':
    print('fetching and unpacking zip file...')
    hud.fetch()

    print('temporary directory:', hud.wd)

    if not options['n']:
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
    fatal('invalid operation ' + operation)
