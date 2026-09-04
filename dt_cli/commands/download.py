import click, subprocess, re, shutil, sys, glob as glob_mod
from pathlib import Path
from datetime import datetime
from ..config import (console, get_save_path, ask_filename, confirm_save,
                      ensure_cli_tool, ensure_pip_module, check_ffmpeg,
                      bar_width, BORDER_ROUNDED)
from rich.panel import Panel
from rich.progress import (Progress, SpinnerColumn, BarColumn, TextColumn,
                           DownloadColumn, TransferSpeedColumn, TimeRemainingColumn)
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.markup import escape
from rich import box

# yt-dlp pip spec with the "default" extras (mutagen etc.) and curl_cffi for
# browser impersonation — required by TikTok/Instagram and many anti-bot sites.
YT_DLP_SPEC = 'yt-dlp[default,curl-cffi]'

# Platforms that (almost) always require an authenticated session to download.
NEEDS_COOKIES_PLATFORMS = ('instagram.com', 'facebook.com', 'fb.watch', 'threads.net')
COOKIE_BROWSERS = ['chrome', 'firefox', 'edge', 'brave', 'safari', 'skip']


# ── yt-dlp resolution (binary OR python module) ────────────────────

def _module_ytdlp_cmd():
    """Invoke yt-dlp as a module of the current interpreter.

    This covers the very common case where the yt-dlp package is pip-installed
    but its console script directory (~/.local/bin, Scripts\\, ...) is not on PATH.
    """
    try:
        r = subprocess.run([sys.executable, '-m', 'yt_dlp', '--version'],
                           capture_output=True, text=True, timeout=30)
        if r.returncode == 0 and r.stdout.strip():
            return [sys.executable, '-m', 'yt_dlp']
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def _find_ytdlp():
    """Return the yt-dlp command (list) or None — never installs."""
    if shutil.which('yt-dlp'):
        return ['yt-dlp']
    return _module_ytdlp_cmd()


def _install_ytdlp():
    """Auto-install yt-dlp (with impersonation extras). Returns cmd or None."""
    console.print()
    console.print(Panel(
        f"[bold warn]yt-dlp is not installed[/bold warn]\n"
        f"[dim]Auto-installing yt-dlp (with impersonation support)...[/dim]",
        border_style="warn", box=BORDER_ROUNDED
    ))

    attempts = [
        [sys.executable, '-m', 'pip', 'install', '--user', YT_DLP_SPEC],
        [sys.executable, '-m', 'pip', 'install', YT_DLP_SPEC],
        [sys.executable, '-m', 'pip', 'install', '--user', 'yt-dlp'],
        ['pip3', 'install', '--user', YT_DLP_SPEC],
    ]

    with Progress(
        SpinnerColumn("dots"),
        TextColumn("[progress.description]Installing yt-dlp...[/progress.description]"),
        console=console, transient=True
    ) as progress:
        progress.add_task("installing", total=None)
        for cmd in attempts:
            try:
                subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            except (OSError, subprocess.TimeoutExpired):
                continue
            found = _find_ytdlp()
            if found:
                console.print("[success]yt-dlp installed successfully![/success]\n")
                return found

    console.print("[red]Could not auto-install yt-dlp.[/red]")
    console.print(f"[dim]Install it manually with:  pip install \"{escape(YT_DLP_SPEC)}\"[/dim]\n")
    return None


def _get_yt_dlp_cmd():
    """Resolve yt-dlp; auto-install only when truly missing."""
    return _find_ytdlp() or _install_ytdlp()


def _ytdlp_version(cmd):
    try:
        r = subprocess.run(cmd + ['--version'], capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            return r.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def _ytdlp_age_days(version):
    """yt-dlp versions are dates (2025.06.09). None if unparseable."""
    try:
        y, m, d = (int(x) for x in version.split('.')[:3])
        return max(0, (datetime.now() - datetime(y, m, d)).days)
    except (ValueError, IndexError):
        return None


def _update_ytdlp(cmd):
    """Update yt-dlp in place (self-update first, then pip). Returns cmd or None."""
    console.print("[dim]Updating yt-dlp...[/dim]")
    old_version = _ytdlp_version(cmd)

    # 1) Self-update (works for the standalone binary / exe releases)
    try:
        subprocess.run(cmd + ['-U'], capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired):
        pass
    new_cmd = _find_ytdlp() or cmd
    if _ytdlp_version(new_cmd) != old_version:
        console.print(f"[success]yt-dlp updated to {_ytdlp_version(new_cmd)}[/success]")
        return new_cmd

    # 2) pip upgrade (extras also pulls in curl_cffi for impersonation)
    pip_ok = False
    for pip_cmd in (
        [sys.executable, '-m', 'pip', 'install', '--user', '-U', YT_DLP_SPEC],
        [sys.executable, '-m', 'pip', 'install', '-U', YT_DLP_SPEC],
    ):
        try:
            r = subprocess.run(pip_cmd, capture_output=True, text=True, timeout=600)
        except (OSError, subprocess.TimeoutExpired):
            continue
        new_cmd = _find_ytdlp()
        if new_cmd and _ytdlp_version(new_cmd) != old_version:
            console.print(f"[success]yt-dlp updated to {_ytdlp_version(new_cmd)}[/success]")
            return new_cmd
        if r.returncode == 0:
            pip_ok = True

    if pip_ok and new_cmd:
        console.print(f"[dim]yt-dlp is already up to date ({old_version})[/dim]")
        return new_cmd

    console.print("[yellow]Could not auto-update yt-dlp.[/yellow]")
    console.print(f"[dim]Try manually:  pip install -U \"{escape(YT_DLP_SPEC)}\"[/dim]")
    return None


# ── live progress runner ───────────────────────────────────────────

_PCT_RE = re.compile(
    r'\[download\]\s+(\d+(?:\.\d+)?)%\s+of\s+(?:~\s*)?([\d.]+)\s*(KiB|MiB|GiB|TiB)')
_UNITS = {'KiB': 1024, 'MiB': 1024 ** 2, 'GiB': 1024 ** 3, 'TiB': 1024 ** 4}


def _run_ytdlp_live(cmd):
    """Run yt-dlp streaming its output into a live Rich progress bar.

    Returns (returncode, all_output_lines). Never leaves the user staring at a
    frozen screen, and keeps every line for accurate error reporting.
    """
    lines = []
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1, encoding='utf-8', errors='replace'
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
            task = progress.add_task("[info]Fetching media info...[/info]", total=None)
            prev_pct = 0.0

            for raw in proc.stdout:
                line = raw.rstrip('\r\n')
                lines.append(line)

                m = _PCT_RE.search(line)
                if m:
                    pct, size, unit = float(m.group(1)), float(m.group(2)), _UNITS[m.group(3)]
                    total = size * unit
                    # % restarts for each stream (video, then audio) — reset the bar
                    if pct < prev_pct:
                        progress.update(task, completed=0)
                    prev_pct = pct
                    progress.update(task, total=total, completed=total * pct / 100.0,
                                    description="[info]Downloading...[/info]")
                elif 'Destination:' in line:
                    dest = line.split('Destination:', 1)[1].strip()
                    try:
                        name = Path(dest).name
                    except ValueError:
                        name = dest[:40]
                    progress.update(task, description=f"[info]⬇ {name}[/info]")
                elif 'fragment' in line.lower() and line.startswith('[download]'):
                    progress.update(task, description=f"[info]{line.split(']', 1)[1].strip()[:50]}[/info]")
                elif '[Merger]' in line:
                    progress.update(task, description="[info]Merging video + audio...[/info]", total=None)

            proc.stdout.close()
            proc.wait()
    except KeyboardInterrupt:
        proc.kill()
        proc.wait()
        console.print("\n[red]Download interrupted.[/red]")
        return 130, lines

    return proc.returncode, lines


# ── helpers ────────────────────────────────────────────────────────

def _sanitize_filename(name):
    """Make a user-supplied filename safe for yt-dlp's -o template and all OSes."""
    name = (name or '').strip() or 'download'
    # '%' breaks the output template; the rest are Windows-illegal / glob metachars
    name = re.sub(r'[%<>:"/\\|?*\[\]]', '_', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name[:150] or 'download'


def _find_output_file(output_dir, filename, prefer_ext=None):
    """Locate the downloaded file robustly (glob-safe, skips .part fragments)."""
    esc = glob_mod.escape(filename)
    candidates = [
        p for p in output_dir.glob(esc + '.*')
        if not p.name.endswith('.part') and not re.search(r'\.f\d+\.', p.name)
    ]
    if not candidates:
        return None
    if prefer_ext:
        exact = [c for c in candidates if c.suffix.lower() == '.' + prefer_ext.lstrip('.').lower()]
        if exact:
            return max(exact, key=lambda f: f.stat().st_mtime)
    return max(candidates, key=lambda f: f.stat().st_mtime)


def _is_interactive():
    try:
        return sys.stdin.isatty() and sys.stdout.isatty()
    except Exception:
        return False


def _warn_if_stale(cmd):
    """Social sites change weekly — a stale yt-dlp is the #1 cause of failures."""
    version = _ytdlp_version(cmd)
    if not version:
        return
    age = _ytdlp_age_days(version)
    if age and age > 90:
        console.print(f"[warn]Your yt-dlp is {age} days old ({version}).[/warn] "
                      f"[dim]Sites change fast — if the download fails, run with --update.[/dim]")


# ── error classification & auto-repair ─────────────────────────────

def _classify_failure(lines):
    """Inspect yt-dlp output and return a failure class."""
    errors = [l for l in lines if l.startswith('ERROR') or ': ERROR:' in l or 'ERROR:' in l]
    text = ' '.join(errors + [l for l in lines if l.startswith('WARNING')]).lower()

    if 'impersonat' in text or 'curl_cffi' in text or 'curl-cffi' in text:
        return 'impersonate', errors
    if 'requested format is not available' in text:
        return 'format', errors
    if 'ffmpeg' in text or 'ffprobe' in text:
        return 'ffmpeg', errors
    if any(k in text for k in ('login', 'cookies', 'rate-limit', 'rate limit',
                               'authentication', 'sign in', 'blocked', 'private video')):
        return 'login', errors
    if any(k in text for k in ('nsig', 'signature', 'update yt-dlp', 'unable to extract',
                               'unable to download webpage', 'no video formats',
                               'unsupported url', 'player')):
        return 'stale', errors
    if 'tls' in text or 'ssl' in text or 'http error 403' in text:
        return 'stale', errors
    return 'unknown', errors


def _attempt_fix(failure, ctx):
    """Try to auto-repair a failure. Mutates ctx; True if worth retrying."""
    interactive = _is_interactive()

    if failure == 'ffmpeg':
        console.print("[warn]ffmpeg is required for HD video merging and audio conversion.[/warn]")
        if ensure_cli_tool('ffmpeg', display_name='ffmpeg'):
            ctx['ffmpeg_ok'] = check_ffmpeg()
            return True
        console.print("[yellow]ffmpeg unavailable — retrying in single-file mode "
                      "(quality may be limited).[/yellow]")
        ctx['ffmpeg_ok'] = False
        return True

    if failure == 'login':
        if not ctx.get('cookies'):
            console.print("[warn]This platform requires an authenticated session (cookies).[/warn]")
            if interactive:
                browser = Prompt.ask("[info]Use cookies from which browser?[/info]",
                                     choices=COOKIE_BROWSERS, default='chrome')
                if browser != 'skip':
                    ctx['cookies'] = browser
                    return True
            else:
                console.print("[dim]Re-run with:  dt dm <url> --cookies-from-browser chrome[/dim]")
        return False

    if failure == 'impersonate':
        console.print("[warn]This site blocks non-browser requests (TLS fingerprinting).[/warn]")
        if ensure_pip_module('curl_cffi', pip_name='curl_cffi', display_name='curl_cffi'):
            console.print("[success]Impersonation support installed — retrying.[/success]")
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
    console.print()
    if errors:
        for line in errors[:3]:
            console.print(f"[red]{line.strip()}[/red]")

    hints = {
        'ffmpeg': "Install ffmpeg (dt setup) for full quality and audio conversion.",
        'login': "This platform needs login cookies — try: dt dm <url> --cookies-from-browser chrome",
        'impersonate': f"Install impersonation support:  pip install \"{escape(YT_DLP_SPEC)}\"",
        'stale': f"Update yt-dlp and retry:  dt dm <url> --update",
        'format': "The chosen quality isn't available for this media.",
    }
    if failure in hints:
        console.print(f"[dim]{hints[failure]}[/dim]")
    else:
        console.print("[dim]Check the URL, or update yt-dlp: dt dm <url> --update[/dim]")


# ── download engine ────────────────────────────────────────────────

def _build_args(ctx, kind, url, filename, output_dir, fmt='best'):
    """Build the yt-dlp argument list for the current attempt."""
    ffmpeg_ok = ctx.get('ffmpeg_ok', False)
    template = str(output_dir / f"{filename}.%(ext)s")

    args = ['--newline', '--no-playlist', '--retries', '5', '--fragment-retries', '5',
            '-o', template]

    if ctx.get('cookies'):
        args += ['--cookies-from-browser', ctx['cookies']]

    if kind == 'audio':
        if ffmpeg_ok:
            args += ['-f', 'bestaudio/best', '-x', '--audio-format', fmt,
                     '--audio-quality', '2', '--embed-thumbnail']
        else:
            args += ['-f', 'bestaudio/best']  # native format (usually .m4a), no conversion
    else:  # video
        height = ctx.get('height')
        if ctx.get('force_plain_best') or not height:
            fmt_str = 'bestvideo+bestaudio/best' if ffmpeg_ok else 'best'
        elif ffmpeg_ok:
            fmt_str = f'bestvideo[height<={height}]+bestaudio/best[height<={height}]/best'
        else:
            fmt_str = f'best[height<={height}]/best'
        args += ['-f', fmt_str]
        if ffmpeg_ok:
            args += ['--merge-output-format', 'mp4', '--embed-subs']

    return args + [url]


def _download_with_retry(kind, url, filename, fmt='best', quality_label='best',
                         height=None, cookies=None):
    cmd = _get_yt_dlp_cmd()
    if not cmd:
        return

    _warn_if_stale(cmd)

    ffmpeg_ok = check_ffmpeg()
    if not ffmpeg_ok:
        # Give ourselves the best shot: try once to install it, degrade gracefully after.
        ffmpeg_ok = ensure_cli_tool('ffmpeg', display_name='ffmpeg')

    output_dir = get_save_path('videos' if kind == 'video' else 'music')

    if kind == 'video':
        console.print(f"\n[info]Downloading video ({quality_label}) from:[/info] [white]{url}[/white]\n")
        prefer_ext = 'mp4' if ffmpeg_ok else None
    else:
        console.print(f"\n[info]Downloading audio ({fmt.upper()}) from:[/info] [white]{url}[/white]\n")
        prefer_ext = fmt if ffmpeg_ok else None

    ctx = {'cmd': cmd, 'ffmpeg_ok': ffmpeg_ok, 'cookies': cookies, 'height': height,
           'force_plain_best': False}

    for attempt in (1, 2):
        args = _build_args(ctx, kind, url, filename, output_dir, fmt)
        rc, lines = _run_ytdlp_live(ctx['cmd'] + args)

        file = _find_output_file(output_dir, filename, prefer_ext=prefer_ext)
        if file:
            size_mb = file.stat().st_size / (1024 * 1024)
            console.print(f"[dim]Size: {size_mb:.2f} MB[/dim]")
            if kind == 'video':
                console.print(f"[dim]Quality: {quality_label}[/dim]")
            if rc != 0:
                console.print("[yellow]Downloaded OK, but post-processing had warnings "
                              "(thumbnail/subtitles may be missing).[/yellow]")
            if kind == 'audio' and not ctx['ffmpeg_ok']:
                console.print(f"[yellow]Saved as native {file.suffix.lstrip('.')} — "
                              "install ffmpeg to convert to " + fmt.upper() + ".[/yellow]")
            confirm_save(file)
            return

        if rc == 0:
            console.print(f"[yellow]yt-dlp finished but no file was found in {output_dir}[/yellow]")
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
@click.option('--type', 'media_type', type=click.Choice(['video', 'audio', 'image']),
              help='Download type (skips the prompt)')
@click.option('-q', '--quality', type=click.Choice(['2160', '1080', '720', '480', '360', 'best']),
              help='Video quality (skips the prompt)')
@click.option('-f', '--filename', 'filename_opt', default=None,
              help='Output filename (without extension)')
@click.option('--cookies-from-browser', 'cookies', default=None,
              help='Use cookies from a browser (chrome, firefox, edge, brave, safari)')
@click.option('--update', 'update', is_flag=True, help='Update yt-dlp before downloading')
def dm(url, media_type, quality, filename_opt, cookies, update):
    """Download any video, audio or image from any social media / website"""
    console.print()
    console.print(Panel(
        "[bold brand]DT DOWNLOAD MEDIA[/bold brand]\n[dim]Download videos, audio, and images from any platform[/dim]\n"
        "[dim]Supported: YouTube, Instagram, TikTok, Twitter/X, Facebook, Reddit, SoundCloud, and 1000+ more[/dim]",
        border_style="brand", box=box.DOUBLE_EDGE
    ))

    if not url:
        url = Prompt.ask("\n[info]Enter the URL to download from[/info]")

    if not url.strip():
        console.print("[red]No URL provided.[/red]")
        return
    url = url.strip()

    cmd = _get_yt_dlp_cmd()
    if not cmd:
        return
    if update:
        new_cmd = _update_ytdlp(cmd)
        if new_cmd:
            cmd = new_cmd

    # Instagram / Facebook (etc.) almost always need an authenticated session
    low = url.lower()
    if cookies is None and any(d in low for d in NEEDS_COOKIES_PLATFORMS):
        console.print("\n[warn]This platform usually requires login to download media.[/warn]")
        if _is_interactive():
            browser = Prompt.ask("[info]Use cookies from which browser?[/info]",
                                 choices=COOKIE_BROWSERS, default='chrome')
            if browser != 'skip':
                cookies = browser
        else:
            console.print("[dim]If it fails, re-run with:  --cookies-from-browser chrome[/dim]")

    # Detect platform
    is_youtube = any(d in low for d in ['youtube.com', 'youtu.be'])
    is_audio = any(domain in low for domain in ['soundcloud.com', 'bandcamp.com', 'audiomack.com'])
    is_video_platform = any(d in low for d in ['instagram.com/reel', 'instagram.com/tv', '/video/', 'watch?v=', 'tiktok.com'])
    is_image = (any(domain in low for domain in ['imgur.com', 'flickr.com', 'unsplash.com', 'pin.it', 'pinterest.com'])
                and not is_video_platform) or low.endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif', '.svg', '.bmp'))

    filename = _sanitize_filename(filename_opt) if filename_opt else None

    # Fast path: everything provided via flags
    if media_type:
        filename = filename or _sanitize_filename(ask_filename("download"))
        if media_type == 'audio':
            _download_with_retry('audio', url, filename, fmt='mp3', cookies=cookies)
        elif media_type == 'image':
            _download_images(url, filename)
        else:
            q = quality or 'best'
            _download_with_retry('video', url, filename,
                                 height=None if q == 'best' else int(q),
                                 quality_label=q + 'p' if q != 'best' else 'best',
                                 cookies=cookies)
        return

    # For YouTube videos, ALWAYS show quality menu prominently
    if is_youtube:
        console.print("\n[bold accent]YouTube video detected[/bold accent]")
        console.print(Panel(
            "[bold white]Select download quality:[/bold white]",
            border_style="brand", box=box.ROUNDED, padding=(0, 2)
        ))
        quality_table = Table(box=None, show_header=False, padding=(0, 1), expand=True)
        quality_table.add_column(style="accent", ratio=1)
        quality_table.add_column(style="white", ratio=4)
        quality_table.add_column(style="dim", ratio=3)
        quality_table.add_row("[1]", "4K  (2160p) - Ultra HD", "[dim]~2-10 GB[/dim]")
        quality_table.add_row("[2]", "1080p - Full HD", "[dim]~500 MB - 3 GB  [recommended][/dim]")
        quality_table.add_row("[3]", "720p - HD", "[dim]~300 MB - 1.5 GB[/dim]")
        quality_table.add_row("[4]", "480p - SD", "[dim]~150 MB - 500 MB[/dim]")
        quality_table.add_row("[5]", "360p - Low", "[dim]~50 MB - 200 MB[/dim]")
        quality_table.add_row("[6]", "Audio only (MP3)", "[dim]~5 MB - 50 MB[/dim]")
        quality_table.add_row("[7]", "Audio only (WAV)", "[dim]~30 MB - 300 MB[/dim]")
        console.print(quality_table)

        choice = Prompt.ask("[info]Choose quality[/info]", choices=["1", "2", "3", "4", "5", "6", "7"], default="2")
        filename = filename or _sanitize_filename(ask_filename("download"))

        if choice == "6":
            _download_with_retry('audio', url, filename, fmt='mp3', cookies=cookies)
        elif choice == "7":
            _download_with_retry('audio', url, filename, fmt='wav', cookies=cookies)
        else:
            height_map = {"1": 2160, "2": 1080, "3": 720, "4": 480, "5": 360}
            height = height_map[choice]
            _download_with_retry('video', url, filename, height=height,
                                 quality_label=f"{height}p", cookies=cookies)
        return

    # For other platforms, show general menu
    console.print("\n[bold]What do you want to download?[/bold]")
    table = Table(box=None, show_header=False, padding=(0, 1))
    table.add_column(style="accent", ratio=1)
    table.add_column(style="white", ratio=4)

    auto_type = "1" if is_audio else ("3" if is_image else "2")
    table.add_row("[1]", "Audio only  (MP3)" + (" [auto-detected]" if is_audio else ""))
    table.add_row("[2]", "Video  (Best quality)")
    table.add_row("[3]", "Image(s)" + (" [auto-detected]" if is_image else ""))
    console.print(table)

    choice = Prompt.ask("[info]Choose download type[/info]", choices=["1", "2", "3"], default=auto_type)

    filename = filename or _sanitize_filename(ask_filename("download"))

    if choice == "1":
        _download_with_retry('audio', url, filename, fmt='mp3', cookies=cookies)
    elif choice == "2":
        # Always ask quality for video downloads
        _ask_video_quality(url, filename, cookies)
    elif choice == "3":
        _download_images(url, filename)


def _ask_video_quality(url, filename, cookies=None):
    """Show quality selection menu for non-YouTube video downloads."""
    console.print("\n[bold]Select video quality:[/bold]")
    quality_table = Table(box=None, show_header=False, padding=(0, 1))
    quality_table.add_column(style="accent", ratio=1)
    quality_table.add_column(style="white", ratio=4)
    quality_table.add_row("[1]", "4K  (2160p) - Ultra HD")
    quality_table.add_row("[2]", "1080p - Full HD  [recommended]")
    quality_table.add_row("[3]", "720p - HD")
    quality_table.add_row("[4]", "480p - SD")
    quality_table.add_row("[5]", "360p - Low")
    quality_table.add_row("[6]", "Best available (auto)")
    console.print(quality_table)

    q_choice = Prompt.ask("[info]Choose quality[/info]", choices=["1", "2", "3", "4", "5", "6"], default="6")

    height_map = {"1": 2160, "2": 1080, "3": 720, "4": 480, "5": 360}
    height = height_map.get(q_choice)
    label = f"{height}p" if height else "best"
    _download_with_retry('video', url, filename, height=height, quality_label=label,
                         cookies=cookies)


# ── images (gallery-dl → yt-dlp → direct) ──────────────────────────

def _download_images(url, filename):
    """Download images from URL."""
    has_gallery_dl = shutil.which("gallery-dl") is not None

    if has_gallery_dl:
        output_dir = get_save_path('images')
        console.print(f"\n[info]Downloading images from:[/info] [white]{url}[/white]\n")

        result = subprocess.run(['gallery-dl', '-d', str(output_dir), url],
                                capture_output=True, text=True)

        if result.returncode == 0:
            new_files = list(output_dir.glob("*"))
            if new_files:
                console.print(f"[success]Downloaded {len(new_files)} image(s) to {output_dir}[/success]")
            else:
                console.print("[yellow]No images were downloaded.[/yellow]")
            return
        else:
            console.print("[dim]gallery-dl failed, trying yt-dlp...[/dim]")

    _download_images_ytdlp(url, filename)


def _download_images_ytdlp(url, filename):
    """Download images using yt-dlp."""
    cmd = _get_yt_dlp_cmd()
    if not cmd:
        return

    output_dir = get_save_path('images')
    output_template = str(output_dir / f"{filename}_%(id)s.%(ext)s")

    console.print(f"\n[info]Downloading images from:[/info] [white]{url}[/white]\n")

    result = subprocess.run([
        cmd[0], *cmd[1:], '-f', 'bestimage/best',
        '-o', output_template, '--no-playlist', url
    ], capture_output=True, text=True)

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

    console.print(f"[info]Downloading directly...[/info]")
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
