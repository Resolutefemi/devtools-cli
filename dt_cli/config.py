import os
from pathlib import Path

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    HAS_COLORAMA = True
except ImportError:
    # Fallback class to prevent crashes if colorama is missing
    class MockColor:
        def __getattr__(self, name): return ""
    Fore = Style = MockColor()
    HAS_COLORAMA = False

IS_TERMUX = 'com.termux' in os.environ.get('PREFIX', '')
IS_ANDROID = Path('/system/bin/app_process').exists()
IS_WINDOWS = os.name == 'nt'

CONFIG_DIR = Path.home() / '.dt'
CONFIG_DIR.mkdir(exist_ok=True)

def get_save_path(file_type):
    if IS_TERMUX:
        base = Path.home() / 'storage' / 'shared'
        paths = {
            'videos': base / 'Movies' / 'dt-cli',
            'music': base / 'Music' / 'dt-cli',
            'images': base / 'Pictures' / 'dt-cli',
            'documents': base / 'Documents' / 'dt-cli',
            'downloads': base / 'Download' / 'dt-cli',
            'desktop': base / 'Download',
        }
    else:
        home = Path.home()
        paths = {
            'videos': home / 'Videos' / 'dt-cli',
            'music': home / 'Music' / 'dt-cli',
            'images': home / 'Pictures' / 'dt-cli',
            'documents': home / 'Documents' / 'dt-cli',
            'downloads': home / 'Downloads',
            'desktop': home / 'Desktop',
        }
    path = paths.get(file_type, paths['downloads'])
    path.mkdir(parents=True, exist_ok=True)
    return path

class Colors:
    RED = Fore.RED
    GREEN = Fore.GREEN
    YELLOW = Fore.YELLOW
    CYAN = Fore.CYAN
    BLUE = Fore.BLUE
    MAGENTA = Fore.MAGENTA
    WHITE = Fore.WHITE
    RESET = Style.RESET_ALL
    BOLD = Style.BRIGHT

IGNORE_DIRS = {'.git', 'node_modules', 'venv', '__pycache__', '.next', 'dist', 'build', '.vercel', '.netlify', 'vendor'}
