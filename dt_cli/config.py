import os, subprocess, shutil, sys
from pathlib import Path

IS_TERMUX = 'com.termux' in os.environ.get('PREFIX', '')
IS_ANDROID = Path('/system/bin/app_process').exists()
IS_WINDOWS = os.name == 'nt'
IS_MACOS = os.sys.platform == 'darwin'
IS_LINUX = os.sys.platform.startswith('linux') and not IS_TERMUX and not IS_ANDROID
IS_NARROW = False  # updated after Console init

CONFIG_DIR = Path.home() / '.dt'
CONFIG_DIR.mkdir(exist_ok=True)

# ── Lazy Dependency Auto-Installer ─────────────────────────────────
# Tracks which deps have already been installed this session to avoid repeats
_installed_this_session = set()

def ensure_cli_tool(name, pip_name=None, display_name=None):
    """Check if a CLI tool is available; if not, auto-install it.

    Args:
        name: command name to check (e.g. 'yt-dlp', 'ffmpeg')
        pip_name: pip package name if different from name (default: same as name)
        display_name: human-readable name for messages (default: name)

    Returns:
        True if tool is available (was already there or was successfully installed)
    """
    if shutil.which(name) is not None:
        return True

    display = display_name or name
    pip_pkg = pip_name or name

    if name in _installed_this_session:
        return False

    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.panel import Panel

    console.print()
    console.print(Panel(
        f"[bold warn]{display} is not installed[/bold warn]\n"
        f"[dim]Auto-installing {display} now...[/dim]",
        border_style="warn", box=BORDER_ROUNDED
    ))

    install_cmds = []

    if IS_TERMUX:
        install_cmds = [
            ['pkg', 'install', '-y', pip_pkg],
            ['pip', 'install', '--user', pip_pkg],
        ]
    elif IS_WINDOWS:
        install_cmds = [
            [sys.executable, '-m', 'pip', 'install', '--user', pip_pkg],
            ['pip', 'install', '--user', pip_pkg],
        ]
    elif IS_MACOS:
        install_cmds = [
            [sys.executable, '-m', 'pip', 'install', '--user', pip_pkg],
            ['pip3', 'install', '--user', pip_pkg],
            ['brew', 'install', pip_pkg],
        ]
    else:
        # Linux
        install_cmds = [
            [sys.executable, '-m', 'pip', 'install', '--user', pip_pkg],
            ['pip3', 'install', '--user', pip_pkg],
            ['sudo', 'apt', 'install', '-y', name],
        ]

    with Progress(
        SpinnerColumn("dots"),
        TextColumn(f"[progress.description]Installing {display}...[/progress.description]"),
        console=console, transient=True
    ) as progress:
        progress.add_task("installing", total=None)
        for cmd in install_cmds:
            try:
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=120
                )
                if result.returncode == 0:
                    # Verify it's actually available now
                    if shutil.which(name) is not None:
                        _installed_this_session.add(name)
                        console.print(f"[success]{display} installed successfully![/success]\n")
                        return True
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue

    _installed_this_session.add(name)
    console.print(f"[red]Could not auto-install {display}.[/red]")
    console.print(f"[dim]Try manually: pip install {pip_pkg}[/dim]\n")
    return False


def ensure_pip_module(module_name, pip_name=None, display_name=None):
    """Check if a Python module is importable; if not, auto-install via pip.

    Args:
        module_name: import name (e.g. 'requests', 'PIL', 'qrcode')
        pip_name: pip package name if different (e.g. 'Pillow' for 'PIL')
        display_name: human-readable name for messages

    Returns:
        True if module is available
    """
    display = display_name or (pip_name or module_name)
    pip_pkg = pip_name or module_name

    try:
        __import__(module_name)
        return True
    except ImportError:
        pass

    if module_name in _installed_this_session:
        return False

    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn

    console.print()
    console.print(Panel(
        f"[bold warn]{display} is not installed[/bold warn]\n"
        f"[dim]Auto-installing {display} now...[/dim]",
        border_style="warn", box=BORDER_ROUNDED
    ))

    with Progress(
        SpinnerColumn("dots"),
        TextColumn(f"[progress.description]Installing {display}...[/progress.description]"),
        console=console, transient=True
    ) as progress:
        progress.add_task("installing", total=None)
        for cmd in [
            [sys.executable, '-m', 'pip', 'install', '--user', pip_pkg],
            ['pip3', 'install', '--user', pip_pkg],
            ['pip', 'install', '--user', pip_pkg],
        ]:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                if result.returncode == 0:
                    try:
                        __import__(module_name)
                        _installed_this_session.add(module_name)
                        console.print(f"[success]{display} installed successfully![/success]\n")
                        return True
                    except ImportError:
                        continue
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue

    _installed_this_session.add(module_name)
    console.print(f"[red]Could not auto-install {display}.[/red]")
    console.print(f"[dim]Try manually: pip install {pip_pkg}[/dim]\n")
    return False

# ── Rich Console (single shared instance) ──────────────────────────
from rich.console import Console
from rich.theme import Theme

DT_THEME = Theme({
    "brand": "#FF6B6B",
    "accent": "#4ECDC4",
    "success": "#00FF88",
    "warn": "#FFD93D",
    "info": "#6C9BCF",
    "muted": "#888888",
    "dim": "#555555",
    "cmd": "#00FF88",
    "cat": "#FF6B9D",
    "border": "#333333",
})

console = Console(theme=DT_THEME, highlight=False, legacy_windows=False)

# ── Responsive helpers ─────────────────────────────────────────────
def is_narrow():
    """True when terminal is narrow (< 50 columns)."""
    return console.width < 50


def bar_width():
    """Return a sensible bar width for progress bars."""
    w = console.width
    if w < 30:
        return 10
    elif w < 50:
        return 20
    else:
        return 30


def help_columns():
    """Return number of columns for help display (1, 2, or 3)."""
    w = console.width
    if w < 35:
        return 1
    elif w < 55:
        return 2
    else:
        return 3

# ── Re-usable Rich objects ─────────────────────────────────────────
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.prompt import Prompt, Confirm
from rich.live import Live
from rich.layout import Layout
from rich.text import Text
from rich.columns import Columns
from rich.rule import Rule
from rich import box

BORDER_ROUNDED = box.ROUNDED
BORDER_HEAVY = box.HEAVY
BORDER_DOUBLE = box.DOUBLE_EDGE

def get_save_path(file_type='downloads'):
    """Return platform-aware save directory, creating it if needed."""
    if IS_TERMUX:
        base = Path.home() / 'storage' / 'shared'
        paths = {
            'videos': base / 'Movies' / 'dt-cli',
            'music': base / 'Music' / 'dt-cli',
            'images': base / 'Pictures' / 'dt-cli',
            'documents': base / 'Documents' / 'dt-cli',
            'downloads': base / 'Download',
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


def ask_filename(default_name="output"):
    """Prompt user for output filename (no extension)."""
    return Prompt.ask("[info]Enter filename[/info]", default=default_name)


def confirm_save(path):
    """Show a success panel after saving."""
    console.print()
    console.print(Panel(
        f"[success]Saved successfully![/success]\n"
        f"[dim]{path}[/dim]",
        title="[brand]DT[/brand]",
        border_style="success",
        box=BORDER_ROUNDED,
    ))


def spinner_task(description, func, *args, **kwargs):
    """Run a function with a rich spinner."""
    from rich.progress import Progress, SpinnerColumn, TextColumn
    with Progress(SpinnerColumn("dots"), TextColumn("[progress.description]{task.description}"), console=console, transient=True) as progress:
        task = progress.add_task(description, total=None)
        result = func(*args, **kwargs)
        progress.update(task, completed=True)
    return result


def check_ffmpeg():
    """Check if ffmpeg is available."""
    import shutil
    return shutil.which("ffmpeg") is not None


def check_yt_dlp():
    """Check if yt-dlp is available."""
    import shutil
    return shutil.which("yt-dlp") is not None

IGNORE_DIRS = {'.git', 'node_modules', 'venv', '__pycache__', '.next', 'dist', 'build', '.vercel', '.netlify', 'vendor', '.dt', '.eggs', '*.egg-info', 'dt_cli.egg-info', 'renance_dt.egg-info'}