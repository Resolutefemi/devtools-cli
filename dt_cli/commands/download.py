import click
import subprocess
import re
import shutil
import sys
import glob as glob_mod
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

from ..config import (
    console, get_save_path, ask_filename, confirm_save,
    ensure_cli_tool, ensure_pip_module, check_ffmpeg,
    bar_width, BORDER_ROUNDED
)

from rich.panel import Panel
from rich.progress import (
    Progress, SpinnerColumn, BarColumn, TextColumn,
    DownloadColumn, TransferSpeedColumn, TimeRemainingColumn
)
from rich.table import Table
from rich.prompt import Prompt
from rich.markup import escape
from rich import box


YT_DLP_SPEC = 'yt-dlp[default,curl-cffi]'

NEEDS_COOKIES_PLATFORMS = (
    'instagram.com', 'facebook.com', 'fb.watch', 'threads.net'
)

COOKIE_BROWSERS = [
    'chrome', 'firefox', 'edge', 'brave', 'safari', 'skip'
]


# ── yt-dlp resolution ──────────────────────────────────────────────

def _module_ytdlp_cmd():
    """Invoke yt-dlp as a module of the current interpreter."""

    try:
        r = subprocess.run(
            [sys.executable, '-m', 'yt_dlp', '--version'],
            capture_output=True,
            text=True,
            timeout=30
        )

        if r.returncode == 0 and r.stdout.strip():
            return [sys.executable, '-m', 'yt_dlp']

    except (OSError, subprocess.SubprocessError):
        pass

    return None


def _find_ytdlp():
    """Return yt-dlp command or None."""

    binary = shutil.which('yt-dlp')

    if binary:
        try:
            result = subprocess.run(
                [binary, '--version'],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return [binary]

        except (OSError, subprocess.SubprocessError):
            pass

    return _module_ytdlp_cmd()


def _install_ytdlp():
    """Auto-install yt-dlp with required extras."""

    console.print()

    console.print(
        Panel(
            "[bold warn]yt-dlp is not installed[/bold warn]\n"
            "[dim]Auto-installing yt-dlp (with impersonation support)...[/dim]",
            border_style="warn",
            box=BORDER_ROUNDED
        )
    )

    attempts = [
        [sys.executable, '-m', 'pip', 'install', '--user', YT_DLP_SPEC],
        [sys.executable, '-m', 'pip', 'install', YT_DLP_SPEC],
        [sys.executable, '-m', 'pip', 'install', '--user', 'yt-dlp'],
        ['pip3', 'install', '--user', YT_DLP_SPEC],
    ]

    with Progress(
        SpinnerColumn("dots"),
        TextColumn(
            "[progress.description]Installing yt-dlp...[/progress.description]"
        ),
        console=console,
        transient=True
    ) as progress:

        progress.add_task("installing", total=None)

        for cmd in attempts:

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=600
                )

            except (OSError, subprocess.SubprocessError):
                continue

            if result.returncode == 0:
                found = _find_ytdlp()

                if found:
                    console.print(
                        "[success]yt-dlp installed successfully![/success]\n"
                    )
                    return found

    console.print("[red]Could not auto-install yt-dlp.[/red]")

    console.print(
        f"[dim]Install it manually with: "
        f"pip install \"{escape(YT_DLP_SPEC)}\"[/dim]\n"
    )

    return None


def _get_yt_dlp_cmd():
    """Resolve yt-dlp; install only when missing."""

    return _find_ytdlp() or _install_ytdlp()


def _ytdlp_version(cmd):
    """Get installed yt-dlp version."""

    try:
        r = subprocess.run(
            cmd + ['--version'],
            capture_output=True,
            text=True,
            timeout=30
        )

        if r.returncode == 0:
            return r.stdout.strip() or None

    except (OSError, subprocess.SubprocessError):
        pass

    return None


def _ytdlp_age_days(version):
    """Calculate yt-dlp version age."""

    try:
        y, m, d = (
            int(x) for x in version.split('.')[:3]
        )

        version_date = datetime(y, m, d)

        return max(
            0,
            (datetime.now() - version_date).days
        )

    except (ValueError, IndexError, TypeError):
        return None


def _update_ytdlp(cmd):
    """Update yt-dlp in place."""

    console.print("[dim]Updating yt-dlp...[/dim]")

    old_version = _ytdlp_version(cmd)

    try:
        subprocess.run(
            cmd + ['-U'],
            capture_output=True,
            text=True,
            timeout=300
        )

    except (OSError, subprocess.SubprocessError):
        pass

    new_cmd = _find_ytdlp() or cmd
    new_version = _ytdlp_version(new_cmd)

    if new_version and new_version != old_version:

        console.print(
            f"[success]yt-dlp updated to {new_version}[/success]"
        )

        return new_cmd

    for pip_cmd in (
        [
            sys.executable, '-m', 'pip',
            'install', '--user', '-U', YT_DLP_SPEC
        ],
        [
            sys.executable, '-m', 'pip',
            'install', '-U', YT_DLP_SPEC
        ],
    ):

        try:
            result = subprocess.run(
                pip_cmd,
                capture_output=True,
                text=True,
                timeout=600
            )

        except (OSError, subprocess.SubprocessError):
            continue

        new_cmd = _find_ytdlp()

        if new_cmd:

            new_version = _ytdlp_version(new_cmd)

            if new_version and new_version != old_version:

                console.print(
                    f"[success]yt-dlp updated to {new_version}[/success]"
                )

                return new_cmd

            if result.returncode == 0:

                console.print(
                    f"[dim]yt-dlp is already up to date "
                    f"({new_version or old_version})[/dim]"
                )

                return new_cmd

    console.print("[yellow]Could not auto-update yt-dlp.[/yellow]")

    console.print(
        f"[dim]Try manually: "
        f"pip install -U \"{escape(YT_DLP_SPEC)}\"[/dim]"
    )

    return None


# ── live progress runner ───────────────────────────────────────────

_PCT_RE = re.compile(
    r'download\s+(\d+(?:\.\d+)?)%\s+of\s+'
    r'(?:~\s*)?([\d.]+)\s*(KiB|MiB|GiB|TiB)'
)

_UNITS = {
    'KiB': 1024,
    'MiB': 1024 ** 2,
    'GiB': 1024 ** 3,
    'TiB': 1024 ** 4
}


def _run_ytdlp_live(cmd):
    """Run yt-dlp with live progress."""

    lines = []

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            encoding='utf-8',
            errors='replace'
        )

    except (OSError, ValueError) as e:
        return 127, [f'ERROR: could not launch yt-dlp: {e}']

    try:

        with Progress(
            SpinnerColumn("dots"),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=bar_width()),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:

            task = progress.add_task(
                "[info]Fetching media info...[/info]",
                total=None
            )

            prev_pct = 0.0
            prev_total = None

            for raw in proc.stdout:

                line = raw.rstrip('\r\n')
                lines.append(line)

                match = _PCT_RE.search(line)

                if match:

                    pct = float(match.group(1))
                    size = float(match.group(2))
                    unit = match.group(3)

                    total = size * _UNITS[unit]

                    if pct < prev_pct or (
                        prev_total is not None and total != prev_total
                    ):
                        progress.reset(
                            task,
                            total=None,
                            completed=0
                        )

                    prev_pct = pct
                    prev_total = total

                    progress.update(
                        task,
                        total=total,
                        completed=total * pct / 100.0,
                        description="[info]Downloading...[/info]"
                    )

                elif 'Destination:' in line:

                    dest = line.split(
                        'Destination:',
                        1
                    )[1].strip()

                    name = Path(dest).name

                    progress.update(
                        task,
                        description=f"[info]⬇ {name}[/info]"
                    )

                elif (
                    'fragment' in line.lower()
                    and line.startswith('[download]')
                ):

                    progress.update(
                        task,
                        description=(
                            f"[info]"
                            f"{line.split(']', 1)[1].strip()[:50]}"
                            f"[/info]"
                        )
                    )

                elif '[Merger]' in line:

                    progress.update(
                        task,
                        description="[info]Merging video + audio...[/info]",
                        total=None
                    )

            proc.stdout.close()
            returncode = proc.wait()

        return returncode, lines

    except KeyboardInterrupt:

        try:
            proc.kill()
            proc.wait(timeout=10)

        except (OSError, subprocess.SubprocessError):
            pass

        console.print("\n[red]Download interrupted.[/red]")

        return 130, lines

    except Exception as e:

        try:
            proc.kill()
            proc.wait(timeout=10)

        except (OSError, subprocess.SubprocessError):
            pass

        lines.append(f'ERROR: {e}')

        return 1, lines

    finally:

        if proc.stdout and not proc.stdout.closed:
            proc.stdout.close()


# ── helpers ────────────────────────────────────────────────────────

def _sanitize_filename(name):
    """Make filenames safe for all supported operating systems."""

    name = (name or '').strip() or 'download'

    name = re.sub(
        r'[%<>:"/\\|?*\x00-\x1f]',
        '_',
        name
    )

    name = re.sub(r'\s+', ' ', name).strip()

    name = name.rstrip('. ')

    if name.upper().split('.')[0] in {
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4',
        'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4',
        'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }:
        name = '_' + name

    return name[:150] or 'download'


def _find_output_file(output_dir, filename, prefer_ext=None):
    """Locate the downloaded file."""

    output_dir = Path(output_dir)

    try:

        if not output_dir.is_dir():
            return None

        esc = glob_mod.escape(filename)

        candidates = [
            p for p in output_dir.glob(esc + '.*')
            if p.is_file()
            and not p.name.endswith(('.part', '.ytdl', '.temp'))
            and not re.search(r'\.f\d+\.', p.name)
        ]

        if not candidates:
            return None

        candidates = [
            p for p in candidates
            if p.stat().st_size > 0
        ]

        if not candidates:
            return None

        if prefer_ext:

            exact = [
                c for c in candidates
                if c.suffix.lower() == (
                    '.' + prefer_ext.lstrip('.').lower()
                )
            ]

            if exact:
                candidates = exact

        return max(
            candidates,
            key=lambda f: f.stat().st_mtime
        )

    except OSError:
        return None


def _is_interactive():
    """Check whether terminal input is interactive."""

    try:
        return (
            sys.stdin.isatty()
            and sys.stdout.isatty()
        )

    except Exception:
        return False


def _warn_if_stale(cmd):
    """Warn when yt-dlp is outdated."""

    version = _ytdlp_version(cmd)

    if not version:
        return

    age = _ytdlp_age_days(version)

    if age is not None and age > 90:

        console.print(
            f"[warn]Your yt-dlp is {age} days old "
            f"({version}).[/warn] "
            f"[dim]Sites change fast — if the download fails, "
            f"run with --update.[/dim]"
        )


def _is_supported_url(url):
    """Validate URL structure."""

    try:

        parsed = urlparse(url)

        return (
            parsed.scheme.lower() in ('http', 'https')
            and bool(parsed.hostname)
            and not any(c.isspace() for c in url)
        )

    except (ValueError, TypeError):
        return False


def _get_domain(url):
    """Get normalized hostname from URL."""

    try:
        return (urlparse(url).hostname or '').lower().rstrip('.')

    except (ValueError, TypeError):
        return ''


def _needs_cookies(url):
    """Check whether the platform commonly requires cookies."""

    domain = _get_domain(url)

    return any(
        domain == platform or domain.endswith('.' + platform)
        for platform in NEEDS_COOKIES_PLATFORMS
    )


def _ensure_output_dir(path):
    """Create output directory safely."""

    try:

        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)

        return path if path.is_dir() else None

    except OSError as e:

        console.print(
            f"[red]Cannot create output directory: {e}[/red]"
        )

        return None


# ── error classification & auto-repair ─────────────────────────────

def _classify_failure(lines):
    """Inspect yt-dlp output and classify failures."""

    errors = [
        line for line in lines
        if (
            line.startswith('ERROR')
            or ': ERROR:' in line
            or 'ERROR:' in line
        )
    ]

    text = ' '.join(
        errors + [
            line for line in lines
            if line.startswith('WARNING')
        ]
    ).lower()

    if 'impersonat' in text or 'curl_cffi' in text or 'curl-cffi' in text:
        return 'impersonate', errors

    if 'requested format is not available' in text:
        return 'format', errors

    if 'ffmpeg' in text or 'ffprobe' in text:
        return 'ffmpeg', errors

    if any(
        key in text
        for key in (
            'login', 'cookies', 'rate-limit', 'rate limit',
            'authentication', 'sign in', 'blocked',
            'private video', 'private content'
        )
    ):
        return 'login', errors

    if any(
        key in text
        for key in (
            'nsig', 'signature', 'update yt-dlp',
            'unable to extract', 'unable to download webpage',
            'no video formats', 'unsupported url', 'player'
        )
    ):
        return 'stale', errors

    if any(
        key in text
        for key in (
            'tls', 'ssl', 'http error 403',
            'http error 429'
        )
    ):
        return 'stale', errors

    return 'unknown', errors


def _attempt_fix(failure, ctx):
    """Try to automatically repair a failure."""

    interactive = _is_interactive()

    if failure == 'ffmpeg':

        console.print(
            "[warn]ffmpeg is required for HD video merging "
            "and audio conversion.[/warn]"
        )

        if ensure_cli_tool(
            'ffmpeg',
            display_name='ffmpeg'
        ):

            ctx['ffmpeg_ok'] = check_ffmpeg()

            if ctx['ffmpeg_ok']:
                return True

        console.print(
            "[yellow]ffmpeg unavailable — retrying in "
            "single-file mode (quality may be limited).[/yellow]"
        )

        ctx['ffmpeg_ok'] = False

        return True

    if failure == 'login':

        if not ctx.get('cookies'):

            console.print(
                "[warn]This platform requires an authenticated "
                "session (cookies).[/warn]"
            )

            if interactive:

                browser = Prompt.ask(
                    "[info]Use cookies from which browser?[/info]",
                    choices=COOKIE_BROWSERS,
                    default='chrome'
                )

                if browser != 'skip':
                    ctx['cookies'] = browser
                    return True

            else:

                console.print(
                    "[dim]Re-run with: "
                    "dt dm <url> --cookies-from-browser chrome[/dim]"
                )

        return False

    if failure == 'impersonate':

        console.print(
            "[warn]This site blocks non-browser requests "
            "(TLS fingerprinting).[/warn]"
        )

        if ensure_pip_module(
            'curl_cffi',
            pip_name='curl_cffi',
            display_name='curl_cffi'
        ):

            console.print(
                "[success]Impersonation support installed — retrying.[/success]"
            )

            return True

        return False

    if failure == 'stale':

        new_cmd = _update_ytdlp(ctx['cmd'])

        if new_cmd:

            ctx['cmd'] = new_cmd

            return True

        return False

    if failure == 'format':

        ctx['force_plain_best'] = True

        return True

    return False


def _show_final_error(failure, errors):
    """Display final download error."""

    console.print()

    if errors:

        for line in errors[:3]:
            console.print(f"[red]{line.strip()}[/red]")

    hints = {
        'ffmpeg': (
            "Install ffmpeg (dt setup) for full quality "
            "and audio conversion."
        ),
        'login': (
            "This platform needs login cookies — try: "
            "dt dm <url> --cookies-from-browser chrome"
        ),
        'impersonate': (
            f"Install impersonation support: "
            f"pip install \"{escape(YT_DLP_SPEC)}\""
        ),
        'stale': (
            "Update yt-dlp and retry: "
            "dt dm <url> --update"
        ),
        'format': (
            "The chosen quality isn't available for this media."
        ),
    }

    if failure in hints:

        console.print(
            f"[dim]{hints[failure]}[/dim]"
        )

    else:

        console.print(
            "[dim]Check the URL, or update yt-dlp: "
            "dt dm <url> --update[/dim]"
        )


# ── download engine ────────────────────────────────────────────────

def _build_args(ctx, kind, url, filename, output_dir, fmt='best'):
    """Build yt-dlp arguments."""

    ffmpeg_ok = ctx.get('ffmpeg_ok', False)

    template = str(
        output_dir / f"{filename}.%(ext)s"
    )

    args = [
        '--newline',
        '--no-playlist',
        '--retries', '5',
        '--fragment-retries', '5',
        '-o', template
    ]

    if ctx.get('cookies'):

        args += [
            '--cookies-from-browser',
            ctx['cookies']
        ]

    if kind == 'audio':

        if ffmpeg_ok:

            args += [
                '-f', 'bestaudio/best',
                '-x',
                '--audio-format', fmt,
                '--audio-quality', '2',
                '--embed-thumbnail'
            ]

        else:

            args += [
                '-f', 'bestaudio/best'
            ]

    else:

        height = ctx.get('height')

        if ctx.get('force_plain_best') or not height:

            fmt_str = (
                'bestvideo+bestaudio/best'
                if ffmpeg_ok else 'best'
            )

        elif ffmpeg_ok:

            fmt_str = (
                f'bestvideo[height<={height}]+'
                f'bestaudio/best[height<={height}]/best'
            )

        else:

            fmt_str = (
                f'best[height<={height}]/best'
            )

        args += [
            '-f',
            fmt_str
        ]

        if ffmpeg_ok:

            args += [
                '--merge-output-format', 'mp4',
                '--embed-subs'
            ]

    return args + [url]


def _download_with_retry(
    kind, url, filename, fmt='best',
    quality_label='best', height=None, cookies=None
):
    """Download media with automatic retry and repair."""

    cmd = _get_yt_dlp_cmd()

    if not cmd:
        return

    _warn_if_stale(cmd)

    ffmpeg_ok = check_ffmpeg()

    if not ffmpeg_ok:

        ffmpeg_ok = ensure_cli_tool(
            'ffmpeg',
            display_name='ffmpeg'
        )

        if ffmpeg_ok:
            ffmpeg_ok = check_ffmpeg()

    output_dir = _ensure_output_dir(
        get_save_path(
            'videos' if kind == 'video' else 'music'
        )
    )

    if output_dir is None:
        return

    if kind == 'video':

        console.print(
            f"\n[info]Downloading video ({quality_label}) from:[/info] "
            f"[white]{escape(url)}[/white]\n"
        )

        prefer_ext = 'mp4' if ffmpeg_ok else None

    else:

        console.print(
            f"\n[info]Downloading audio ({fmt.upper()}) from:[/info] "
            f"[white]{escape(url)}[/white]\n"
        )

        prefer_ext = fmt if ffmpeg_ok else None

    ctx = {
        'cmd': cmd,
        'ffmpeg_ok': ffmpeg_ok,
        'cookies': cookies,
        'height': height,
        'force_plain_best': False
    }

    for attempt in (1, 2):

        args = _build_args(
            ctx,
            kind,
            url,
            filename,
            output_dir,
            fmt
        )

        rc, lines = _run_ytdlp_live(
            ctx['cmd'] + args
        )

        file = _find_output_file(
            output_dir,
            filename,
            prefer_ext=prefer_ext
        )

        if file:

            size_mb = file.stat().st_size / (1024 * 1024)

            console.print(
                f"[dim]Size: {size_mb:.2f} MB[/dim]"
            )

            if kind == 'video':

                console.print(
                    f"[dim]Quality: {quality_label}[/dim]"
                )

            if rc != 0:

                console.print(
                    "[yellow]Downloaded OK, but post-processing "
                    "had warnings (thumbnail/subtitles may be missing)."
                    "[/yellow]"
                )

            if kind == 'audio' and not ctx['ffmpeg_ok']:

                console.print(
                    f"[yellow]Saved as native "
                    f"{file.suffix.lstrip('.')} — "
                    f"install ffmpeg to convert to {fmt.upper()}.[/yellow]"
                )

            confirm_save(file)

            return

        if rc == 0:

            console.print(
                f"[yellow]yt-dlp finished but no file was found "
                f"in {output_dir}[/yellow]"
            )

            for line in lines[-5:]:
                console.print(f"[dim]{line}[/dim]")

            return

        failure, errors = _classify_failure(lines)

        if attempt == 1 and _attempt_fix(failure, ctx):
            continue

        _show_final_error(failure, errors)

        return


# ── command ────────────────────────────────────────────────────────

@click.command()
@click.argument('url', required=False)
@click.option(
    '--type',
    'media_type',
    type=click.Choice(['video', 'audio', 'image']),
    help='Download type (skips the prompt)'
)
@click.option(
    '-q', '--quality',
    type=click.Choice(['2160', '1080', '720', '480', '360', 'best']),
    help='Video quality (skips the prompt)'
)
@click.option(
    '-f', '--filename',
    'filename_opt',
    default=None,
    help='Output filename (without extension)'
)
@click.option(
    '--cookies-from-browser',
    'cookies',
    default=None,
    help='Use cookies from a browser (chrome, firefox, edge, brave, safari)'
)
@click.option(
    '--update',
    'update',
    is_flag=True,
    help='Update yt-dlp before downloading'
)
def dm(url, media_type, quality, filename_opt, cookies, update):
    """Download any video, audio or image from websites."""

    console.print()

    console.print(
        Panel(
            "[bold brand]DT DOWNLOAD MEDIA[/bold brand]\n"
            "[dim]Download videos, audio, and images from any platform[/dim]\n"
            "[dim]Supported: YouTube, Instagram, TikTok, Twitter/X, "
            "Facebook, Reddit, SoundCloud, and 1000+ more[/dim]",
            border_style="brand",
            box=box.DOUBLE_EDGE
        )
    )

    if not url:

        url = Prompt.ask(
            "\n[info]Enter the URL to download from[/info]"
        )

    if not url or not url.strip():

        console.print("[red]No URL provided.[/red]")

        return

    url = url.strip()

    if not _is_supported_url(url):

        console.print("[red]Invalid URL. Use HTTP or HTTPS.[/red]")

        return

    cmd = _get_yt_dlp_cmd()

    if not cmd:
        return

    if update:

        new_cmd = _update_ytdlp(cmd)

        if new_cmd:
            cmd = new_cmd

    if cookies and cookies not in COOKIE_BROWSERS[:-1]:

        console.print(
            "[red]Invalid browser name for cookies.[/red]"
        )

        return

    if cookies == 'skip':
        cookies = None

    if cookies is None and _needs_cookies(url):

        console.print(
            "\n[warn]This platform usually requires "
            "login cookies to download media.[/warn]"
        )

        if _is_interactive():

            browser = Prompt.ask(
                "[info]Use cookies from which browser?[/info]",
                choices=COOKIE_BROWSERS,
                default='chrome'
            )

            if browser != 'skip':
                cookies = browser

        else:

            console.print(
                "[dim]If it fails, re-run with: "
                "--cookies-from-browser chrome[/dim]"
            )

    low = url.lower()
    domain = _get_domain(url)

    is_youtube = (
        domain == 'youtube.com'
        or domain.endswith('.youtube.com')
        or domain == 'youtu.be'
    )

    is_audio = any(
        domain == d or domain.endswith('.' + d)
        for d in (
            'soundcloud.com',
            'bandcamp.com',
            'audiomack.com'
        )
    )

    is_video_platform = (
        'instagram.com/reel' in low
        or 'instagram.com/tv' in low
        or '/video/' in low
        or 'watch?v=' in low
        or 'tiktok.com' in low
    )

    path = urlparse(url).path.lower()

    is_image = (
        (
            any(
                domain == d or domain.endswith('.' + d)
                for d in (
                    'imgur.com',
                    'flickr.com',
                    'unsplash.com',
                    'pin.it',
                    'pinterest.com'
                )
            )
            and not is_video_platform
        )
        or path.endswith((
            '.jpg', '.jpeg', '.png',
            '.webp', '.gif', '.svg', '.bmp'
        ))
    )

    filename = (
        _sanitize_filename(filename_opt)
        if filename_opt else None
    )

    if media_type:

        filename = filename or _sanitize_filename(
            ask_filename("download")
        )

        if media_type == 'audio':

            _download_with_retry(
                'audio',
                url,
                filename,
                fmt='mp3',
                cookies=cookies
            )

        elif media_type == 'image':

            _download_images(
                url,
                filename,
                cookies=cookies
            )

        else:

            q = quality or 'best'

            _download_with_retry(
                'video',
                url,
                filename,
                height=None if q == 'best' else int(q),
                quality_label=(
                    q + 'p' if q != 'best' else 'best'
                ),
                cookies=cookies
            )

        return

    if is_youtube:

        console.print(
            "\n[bold accent]YouTube video detected[/bold accent]"
        )

        console.print(
            Panel(
                "[bold white]Select download quality:[/bold white]",
                border_style="brand",
                box=box.ROUNDED,
                padding=(0, 2)
            )
        )

        quality_table = Table(
            box=None,
            show_header=False,
            padding=(0, 1),
            expand=True
        )

        quality_table.add_column(style="accent", ratio=1)
        quality_table.add_column(style="white", ratio=4)
        quality_table.add_column(style="dim", ratio=3)

        quality_table.add_row(
            "[1]", "4K  (2160p) - Ultra HD", "[dim]~2-10 GB[/dim]"
        )

        quality_table.add_row(
            "[2]", "1080p - Full HD",
            "[dim]~500 MB - 3 GB  [recommended][/dim]"
        )

        quality_table.add_row(
            "[3]", "720p - HD", "[dim]~300 MB - 1.5 GB[/dim]"
        )

        quality_table.add_row(
            "[4]", "480p - SD", "[dim]~150 MB - 500 MB[/dim]"
        )

        quality_table.add_row(
            "[5]", "360p - Low", "[dim]~50 MB - 200 MB[/dim]"
        )

        quality_table.add_row(
            "[6]", "Audio only (MP3)", "[dim]~5 MB - 50 MB[/dim]"
        )

        quality_table.add_row(
            "[7]", "Audio only (WAV)", "[dim]~30 MB - 300 MB[/dim]"
        )

        console.print(quality_table)

        choice = Prompt.ask(
            "[info]Choose quality[/info]",
            choices=["1", "2", "3", "4", "5", "6", "7"],
            default="2"
        )

        filename = filename or _sanitize_filename(
            ask_filename("download")
        )

        if choice == "6":

            _download_with_retry(
                'audio', url, filename,
                fmt='mp3', cookies=cookies
            )

        elif choice == "7":

            _download_with_retry(
                'audio', url, filename,
                fmt='wav', cookies=cookies
            )

        else:

            height_map = {
                "1": 2160,
                "2": 1080,
                "3": 720,
                "4": 480,
                "5": 360
            }

            height = height_map[choice]

            _download_with_retry(
                'video',
                url,
                filename,
                height=height,
                quality_label=f"{height}p",
                cookies=cookies
            )

        return

    console.print(
        "\n[bold]What do you want to download?[/bold]"
    )

    table = Table(
        box=None,
        show_header=False,
        padding=(0, 1)
    )

    table.add_column(style="accent", ratio=1)
    table.add_column(style="white", ratio=4)

    auto_type = (
        "1" if is_audio
        else ("3" if is_image else "2")
    )

    table.add_row(
        "[1]",
        "Audio only  (MP3)" +
        (" [auto-detected]" if is_audio else "")
    )

    table.add_row(
        "[2]",
        "Video  (Best quality)"
    )

    table.add_row(
        "[3]",
        "Image(s)" +
        (" [auto-detected]" if is_image else "")
    )

    console.print(table)

    choice = Prompt.ask(
        "[info]Choose download type[/info]",
        choices=["1", "2", "3"],
        default=auto_type
    )

    filename = filename or _sanitize_filename(
        ask_filename("download")
    )

    if choice == "1":

        _download_with_retry(
            'audio',
            url,
            filename,
            fmt='mp3',
            cookies=cookies
        )

    elif choice == "2":

        _ask_video_quality(
            url,
            filename,
            cookies
        )

    elif choice == "3":

        _download_images(
            url,
            filename,
            cookies=cookies
        )


def _download_images(url, filename, cookies=None):
    """Download images from URL (gallery-dl, then yt-dlp, then direct)."""
    if shutil.which("gallery-dl") is not None:
        output_dir = _ensure_output_dir(get_save_path('images'))
        if output_dir is None:
            return
        console.print(f"\n[info]Downloading images from:[/info] [white]{escape(url)}[/white]\n")
        result = subprocess.run(
            ['gallery-dl', '-d', str(output_dir), url],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            new_files = [p for p in output_dir.glob("*") if p.is_file()]
            if new_files:
                console.print(f"[success]Downloaded {len(new_files)} image(s) to {output_dir}[/success]")
                confirm_save(output_dir)
            else:
                console.print("[yellow]No images were downloaded.[/yellow]")
            return
        console.print("[dim]gallery-dl failed, trying yt-dlp...[/dim]")

    _download_images_ytdlp(url, filename, cookies=cookies)


def _download_images_ytdlp(url, filename, cookies=None):
    """Download images using yt-dlp."""
    cmd = _get_yt_dlp_cmd()
    if not cmd:
        return

    output_dir = _ensure_output_dir(get_save_path('images'))
    if output_dir is None:
        return
    output_template = str(output_dir / f"{filename}_%(id)s.%(ext)s")

    console.print(f"\n[info]Downloading images from:[/info] [white]{escape(url)}[/white]\n")

    args = [*cmd, '-f', 'bestimage/best', '-o', output_template, '--no-playlist']
    if cookies:
        args += ['--cookies-from-browser', cookies]
    args.append(url)
    result = subprocess.run(args, capture_output=True, text=True)

    if result.returncode == 0:
        images = [p for p in output_dir.glob(glob_mod.escape(filename) + '_*')
                  if not p.name.endswith('.part')]
        if images:
            total_size = sum(f.stat().st_size for f in images) / (1024 * 1024)
            console.print(f"[success]Downloaded {len(images)} image(s)[/success]")
            console.print(f"[dim]Total size: {total_size:.2f} MB[/dim]")
            console.print(f"[dim]Saved to: {output_dir}[/dim]")
            confirm_save(output_dir)
        else:
            _direct_image_download(url, filename, output_dir)
    else:
        console.print("[dim]yt-dlp couldn't extract, trying direct download...[/dim]")
        _direct_image_download(url, filename, output_dir)


def _direct_image_download(url, filename, output_dir):
    """Direct image download fallback."""
    if not ensure_pip_module('requests', display_name='requests'):
        console.print("[red]requests is required for direct download. Install: pip install requests[/red]")
        return
    import requests

    ext_match = re.search(r'\.(jpg|jpeg|png|webp|gif|svg|bmp|ico)(\?.*)?$', url.lower())
    ext = ext_match.group(1) if ext_match else 'jpg'

    console.print("[info]Downloading directly...[/info]")
    try:
        resp = requests.get(url, stream=True, timeout=30, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        resp.raise_for_status()

        output_path = output_dir / f"{filename}.{ext}"
        total = int(resp.headers.get('content-length', 0))

        with Progress(
            SpinnerColumn("dots"),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=bar_width()),
            DownloadColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("[info]Downloading...[/info]", total=total or 100)
            with open(output_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
                    if total:
                        progress.update(task, advance=len(chunk))

        size = output_path.stat().st_size / 1024
        console.print(f"[dim]Size: {size:.2f} KB[/dim]")
        confirm_save(output_path)
    except Exception as e:
        console.print(f"[red]Download failed: {e}[/red]")


def _ask_video_quality(url, filename, cookies=None):
    """Show video quality selection menu."""

    console.print(
        "\n[bold]Select video quality:[/bold]"
    )

    quality_table = Table(
        box=None,
        show_header=False,
        padding=(0, 1)
    )

    quality_table.add_column(style="accent", ratio=1)
    quality_table.add_column(style="white", ratio=4)

    quality_table.add_row("[1]", "4K  (2160p) - Ultra HD")
    quality_table.add_row("[2]", "1080p - Full HD  [recommended]")
    quality_table.add_row("[3]", "720p - HD")
    quality_table.add_row("[4]", "480p - SD")
    quality_table.add_row("[5]", "360p - Low")
    quality_table.add_row("[6]", "Best available (auto)")

    console.print(quality_table)

    q_choice = Prompt.ask(
        "[info]Choose quality[/info]",
        choices=["1", "2", "3", "4", "5", "6"],
        default="6"
    )

    height_map = {
        "1": 2160,
        "2": 1080,
        "3": 720,
        "4": 480,
        "5": 360,
        "6": None
    }

    height = height_map[q_choice]

    _download_with_retry(
        'video',
        url,
        filename,
        height=height,
        quality_label=(
            f"{height}p" if height else 'best'
        ),
        cookies=cookies
    )
