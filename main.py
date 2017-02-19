import os
import vdf
from hud import Hud, NoCfgError
from sys import argv, exit, platform


def fatal(message):
    print('fatal:', message)
    exit(1)


# this will be true even in posix-like environments on windows
WINDOWS = (
    os.name == 'nt' or
    platform == 'msys' or
    platform == 'cygwin'
)

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

#     # steamapps is camelcase on windows, but not linux
#     'steamapps'
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

if len(argv) != 3:
    print('usage: {} (install|uninstall) <hud>'.format(argv[0]))
    exit(1)

if not os.path.isdir(STEAMAPPS):
    fatal('can\'t find steam install at {}'.format(STEAMAPPS))

if not os.path.isdir(TF):
    print('tf2 not in default path, searching...')

    library_folders = os.path.join(STEAMAPPS, 'libraryfolders.vdf')
    try:
        with open(library_folders) as f:
            folders = vdf.parse(f)['LibraryFolders']
    except OSError as e:
        fatal('unable to open {}: {}'.format(library_folders, e))
    except SyntaxError as e:
        fatal('error while parsing {}: {}'.format(library_folders, e))
    except KeyError:
        fatal(library_folders + ' does not contain LibraryFolders key')

    for key in folders:
        if key.isnumeric():
            print('searching library {}'.format(folders[key]))
            STEAMAPPS = os.path.join(
                os.path.normpath(folders[key]),
                'steamapps'
            )
            TF = os.path.join(STEAMAPPS, 'common', 'Team Fortress 2')
            CUSTOM = os.path.join(TF, 'tf', 'custom')
            VPK = os.path.join(
                TF, 'bin',
                'vpk.exe' if WINDOWS else 'vpk_linux32'
            )
            if os.path.isdir(TF):
                break
    else:
        fatal('couldn\'t find TF2')

print('found TF2 at', TF)

operation, hud_name = argv[1:]
try:
    if os.path.isfile(VPK):
        hud = Hud(hud_name, CUSTOM, VPK)
    else:
        hud = Hud(hud_name, CUSTOM)
except NoCfgError as e:
    fatal(str(e))

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
    fatal('invalid operation ' + operation)
