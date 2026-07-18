import click, subprocess, re
from pathlib import Path
from ..config import console, get_save_path, ask_filename, confirm_save, check_yt_dlp, bar_width, BORDER_ROUNDED
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn, DownloadColumn
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich import box


@click.command()
@click.argument('url', required=False)
def dm(url):
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

    # Detect platform
    is_youtube = any(d in url.lower() for d in ['youtube.com', 'youtu.be'])
    is_audio = any(domain in url.lower() for domain in ['soundcloud.com', 'bandcamp.com', 'audiomack.com', '.mp3', '.wav', '.flac', '.aac', '.ogg'])
    is_image = any(domain in url.lower() for domain in ['instagram.com/p/', 'imgur.com', 'flickr.com', 'unsplash.com', 'pin.it', 'pinterest.com']) or url.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif', '.svg', '.bmp'))

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
        filename = ask_filename("download")

        if choice == "6":
            _download_audio(url, filename, fmt="mp3")
        elif choice == "7":
            _download_audio(url, filename, fmt="wav")
        else:
            quality_map = {
                "1": ("2160p", "bestvideo[height<=2160]+bestaudio/best[height<=2160]"),
                "2": ("1080p", "bestvideo[height<=1080]+bestaudio/best[height<=1080]"),
                "3": ("720p", "bestvideo[height<=720]+bestaudio/best[height<=720]"),
                "4": ("480p", "bestvideo[height<=480]+bestaudio/best[height<=480]"),
                "5": ("360p", "bestvideo[height<=360]+bestaudio/best[height<=360]"),
            }
            label, fmt = quality_map[choice]
            _download_video(url, filename, fmt=fmt, quality_label=label)

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

    filename = ask_filename("download")

    if choice == "1":
        _download_audio(url, filename, fmt="mp3")
    elif choice == "2":
        # Always ask quality for video downloads
        _ask_video_quality(url, filename)
    elif choice == "3":
        _download_images(url, filename)


def _ask_video_quality(url, filename):
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

    format_map = {
        "1": ("2160p", "bestvideo[height<=2160]+bestaudio/best[height<=2160]"),
        "2": ("1080p", "bestvideo[height<=1080]+bestaudio/best[height<=1080]"),
        "3": ("720p", "bestvideo[height<=720]+bestaudio/best[height<=720]"),
        "4": ("480p", "bestvideo[height<=480]+bestaudio/best[height<=480]"),
        "5": ("360p", "bestvideo[height<=360]+bestaudio/best[height<=360]"),
        "6": ("best", "bestvideo+bestaudio/best"),
    }
    label, fmt = format_map[q_choice]
    _download_video(url, filename, fmt=fmt, quality_label=label)


def _get_yt_dlp_cmd():
    """Get the yt-dlp command, checking if installed."""
    if not check_yt_dlp():
        console.print()
        console.print(Panel(
            "[bold warn]yt-dlp is not installed[/bold warn]\n\n"
            "dt download media requires yt-dlp. Install it with:\n\n"
            "[accent]  pip install yt-dlp[/accent]\n"
            "[accent]  brew install yt-dlp[/accent]  (macOS)\n"
            "[accent]  pkg install yt-dlp[/accent]    (Termux)\n"
            "[accent]  scoop install yt-dlp[/accent]   (Windows)",
            border_style="warn", box=box.ROUNDED
        ))
        return None
    return "yt-dlp"


def _download_audio(url, filename, fmt="mp3"):
    """Download audio from URL."""
    cmd = _get_yt_dlp_cmd()
    if not cmd:
        return

    output_dir = get_save_path('music')
    output_template = str(output_dir / f"{filename}.%(ext)s")

    console.print(f"\n[info]Downloading audio ({fmt.upper()}) from:[/info] [white]{url}[/white]\n")

    quality_map = {"mp3": "2", "wav": "0", "flac": "0", "aac": "2", "ogg": "2"}

    dl_cmd = [
        cmd,
        '-x', '--audio-format', fmt, '--audio-quality', quality_map.get(fmt, "2"),
        '--embed-thumbnail',
        '-o', output_template,
        '--no-playlist',
        url
    ]

    # Show live progress
    console.print("[dim]Starting download...[/dim]")
    result = subprocess.run(dl_cmd, capture_output=True, text=True)

    if result.returncode == 0:
        ext = fmt
        audio_file = output_dir / f"{filename}.{ext}"
        if not audio_file.exists():
            downloaded = list(output_dir.glob(f"{filename}*.{ext}"))
            if not downloaded:
                downloaded = list(output_dir.glob(f"{filename}.*"))
            if downloaded:
                audio_file = max(downloaded, key=lambda f: f.stat().st_mtime)

        if audio_file.exists():
            size = audio_file.stat().st_size / (1024 * 1024)
            console.print(f"[dim]Size: {size:.2f} MB[/dim]")
            confirm_save(audio_file)
        else:
            console.print("[success]Download completed![/success]")
    else:
        _show_download_error(result)


def _download_video(url, filename, fmt="bestvideo+bestaudio/best", quality_label="best"):
    """Download video from URL with specified quality."""
    cmd = _get_yt_dlp_cmd()
    if not cmd:
        return

    output_dir = get_save_path('videos')
    output_template = str(output_dir / f"{filename}.%(ext)s")

    console.print(f"\n[info]Downloading video ({quality_label}) from:[/info] [white]{url}[/white]\n")

    dl_cmd = [
        cmd,
        '-f', fmt,
        '--merge-output-format', 'mp4',
        '--embed-thumbnail',
        '--embed-subs',
        '-o', output_template,
        '--no-playlist',
    ]

    console.print("[dim]Starting download... (this may take a while for high quality)[/dim]")
    result = subprocess.run(dl_cmd + [url], capture_output=True, text=True)

    if result.returncode == 0:
        mp4_file = output_dir / f"{filename}.mp4"
        if not mp4_file.exists():
            downloaded = list(output_dir.glob(f"{filename}*.mp4"))
            if not downloaded:
                downloaded = list(output_dir.glob(f"{filename}.*"))
            if downloaded:
                mp4_file = max(downloaded, key=lambda f: f.stat().st_mtime)

        if mp4_file.exists():
            size = mp4_file.stat().st_size / (1024 * 1024)
            console.print(f"[dim]Size: {size:.2f} MB[/dim]")
            console.print(f"[dim]Quality: {quality_label}[/dim]")
            confirm_save(mp4_file)
        else:
            console.print("[success]Download completed![/success]")
    else:
        _show_download_error(result)


def _download_images(url, filename):
    """Download images from URL."""
    import shutil
    has_gallery_dl = shutil.which("gallery-dl") is not None

    if has_gallery_dl:
        output_dir = get_save_path('images')
        console.print(f"\n[info]Downloading images from:[/info] [white]{url}[/white]\n")

        result = subprocess.run([
            'gallery-dl', '-d', str(output_dir), url
        ], capture_output=True, text=True)

        if result.returncode == 0:
            new_files = list(output_dir.glob("*"))
            if new_files:
                console.print(f"[success]Downloaded {len(new_files)} image(s) to {output_dir}[/success]")
            else:
                console.print("[yellow]No images were downloaded.[/yellow]")
        else:
            console.print("[dim]gallery-dl failed, trying yt-dlp...[/dim]")
            _download_images_ytdlp(url, filename)
    else:
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
        cmd,
        '-f', 'bestimage/best',
        '-o', output_template,
        '--no-playlist',
        url
    ], capture_output=True, text=True)

    if result.returncode == 0:
        images = list(output_dir.glob(f"{filename}*"))
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


def _show_download_error(result):
    """Parse and show yt-dlp error."""
    stderr = result.stderr.strip()
    if "Unsupported URL" in stderr:
        console.print("[red]This URL is not supported by yt-dlp.[/red]")
    elif "ERROR:" in stderr:
        for line in stderr.split('\n'):
            if 'ERROR:' in line:
                console.print(f"[red]{line.strip()}[/red]")
                break
        else:
            console.print(f"[red]Download failed[/red]")
    else:
        console.print(f"[red]Download failed. Try updating yt-dlp: yt-dlp -U[/red]")