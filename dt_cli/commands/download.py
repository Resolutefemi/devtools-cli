import click, subprocess, re
from pathlib import Path
from ..config import console, get_save_path, ask_filename, confirm_save, check_yt_dlp, BORDER_ROUNDED
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

    # Detect type from URL
    is_audio = any(domain in url.lower() for domain in ['soundcloud.com', 'bandcamp.com', 'audiomack.com', '.mp3', '.wav', '.flac', '.aac', '.ogg'])
    is_image = any(domain in url.lower() for domain in ['instagram.com/p/', 'imgur.com', 'flickr.com', 'unsplash.com', 'pin.it', 'pinterest.com']) or url.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif', '.svg', '.bmp'))

    # Ask what to download
    console.print("\n[bold]What do you want to download?[/bold]")
    table = Table(box=None, show_header=False, padding=(0, 1))
    table.add_column(style="accent", ratio=1)
    table.add_column(style="white", ratio=4)

    auto_type = "1" if is_audio else ("3" if is_image else "1")
    if is_audio:
        table.add_row("[1]", "Audio only  (MP3) [auto-detected]")
    else:
        table.add_row("[1]", "Audio only  (MP3)")
    table.add_row("[2]", "Video  (Best quality)")
    table.add_row("[3]", "Image(s)")
    table.add_row("[4]", "Video  (Custom quality)")
    console.print(table)

    choice = Prompt.ask("[info]Choose download type[/info]", choices=["1", "2", "3", "4"], default=auto_type)

    filename = ask_filename("download")

    if choice == "1":
        _download_audio(url, filename)
    elif choice == "2":
        _download_video(url, filename, quality="best")
    elif choice == "3":
        _download_images(url, filename)
    elif choice == "4":
        _download_video(url, filename, quality="custom")


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


def _download_audio(url, filename):
    """Download audio from URL."""
    cmd = _get_yt_dlp_cmd()
    if not cmd:
        return

    output_dir = get_save_path('music')
    output_template = str(output_dir / f"{filename}.%(ext)s")

    console.print(f"\n[info]Downloading audio from:[/info] [white]{url}[/white]\n")

    result = subprocess.run([
        cmd,
        '-x', '--audio-format', 'mp3', '--audio-quality', '2',
        '--embed-thumbnail',
        '-o', output_template,
        '--no-playlist',
        url
    ], capture_output=True, text=True)

    if result.returncode == 0:
        # Find the downloaded file
        mp3_file = output_dir / f"{filename}.mp3"
        if not mp3_file.exists():
            # yt-dlp might have used a different name, find it
            downloaded = list(output_dir.glob(f"{filename}*.mp3"))
            if not downloaded:
                downloaded = list(output_dir.glob("*.mp3"))
                if downloaded:
                    mp3_file = max(downloaded, key=lambda f: f.stat().st_mtime)

        if mp3_file.exists():
            size = mp3_file.stat().st_size / (1024 * 1024)
            console.print(f"[dim]Size: {size:.2f} MB[/dim]")
            confirm_save(mp3_file)
        else:
            console.print("[success]Download completed![/success]")
    else:
        _show_download_error(result)


def _download_video(url, filename, quality="best"):
    """Download video from URL."""
    cmd = _get_yt_dlp_cmd()
    if not cmd:
        return

    output_dir = get_save_path('videos')
    output_template = str(output_dir / f"{filename}.%(ext)s")

    if quality == "custom":
        console.print("\n[bold]Select video quality:[/bold]")
        console.print("  [accent]1[/accent]. 4K (2160p)")
        console.print("  [accent]2[/accent]. 1080p")
        console.print("  [accent]3[/accent]. 720p")
        console.print("  [accent]4[/accent]. 480p")
        console.print("  [accent]5[/accent]. 360p")
        q_choice = Prompt.ask("[info]Quality[/info]", choices=["1", "2", "3", "4", "5"], default="2")

        format_map = {
            "1": "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
            "2": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
            "3": "bestvideo[height<=720]+bestaudio/best[height<=720]",
            "4": "bestvideo[height<=480]+bestaudio/best[height<=480]",
            "5": "bestvideo[height<=360]+bestaudio/best[height<=360]",
        }
        fmt = format_map[q_choice]
    else:
        fmt = "bestvideo+bestaudio/best"

    console.print(f"\n[info]Downloading video from:[/info] [white]{url}[/white]\n")

    dl_cmd = [
        cmd,
        '-f', fmt,
        '--merge-output-format', 'mp4',
        '--embed-thumbnail',
        '--embed-subs',
        '-o', output_template,
        '--no-playlist',
    ]

    # Run with progress tracking
    result = subprocess.run(dl_cmd + [url], capture_output=True, text=True)

    if result.returncode == 0:
        # Find the downloaded file
        mp4_file = output_dir / f"{filename}.mp4"
        if not mp4_file.exists():
            downloaded = list(output_dir.glob(f"{filename}*.mp4"))
            if not downloaded:
                downloaded = list(output_dir.glob("*.mp4"))
                if downloaded:
                    mp4_file = max(downloaded, key=lambda f: f.stat().st_mtime)

        if mp4_file.exists():
            size = mp4_file.stat().st_size / (1024 * 1024)
            console.print(f"[dim]Size: {size:.2f} MB[/dim]")
            confirm_save(mp4_file)
        else:
            console.print("[success]Download completed![/success]")
    else:
        _show_download_error(result)


def _download_images(url, filename):
    """Download images from URL."""
    # Try gallery-dl first, then yt-dlp as fallback
    import shutil
    has_gallery_dl = shutil.which("gallery-dl") is not None

    if has_gallery_dl:
        output_dir = get_save_path('images')
        console.print(f"\n[info]Downloading images from:[/info] [white]{url}[/white]\n")

        result = subprocess.run([
            'gallery-dl', '-d', str(output_dir), url
        ], capture_output=True, text=True)

        if result.returncode == 0:
            # Count downloaded files
            new_files = list(output_dir.glob("*"))
            if new_files:
                console.print(f"[success]Downloaded {len(new_files)} image(s) to {output_dir}[/success]")
            else:
                console.print("[yellow]No images were downloaded.[/yellow]")
        else:
            # Fallback to yt-dlp
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
        # Find downloaded images
        images = list(output_dir.glob(f"{filename}*"))
        if images:
            total_size = sum(f.stat().st_size for f in images) / (1024 * 1024)
            console.print(f"[success]Downloaded {len(images)} image(s)[/success]")
            console.print(f"[dim]Total size: {total_size:.2f} MB[/dim]")
            console.print(f"[dim]Saved to: {output_dir}[/dim]")
            confirm_save(output_dir)
        else:
            # Try direct download if URL points to an image
            _direct_image_download(url, filename, output_dir)
    else:
        # Last resort: try direct download
        console.print("[dim]yt-dlp couldn't extract, trying direct download...[/dim]")
        _direct_image_download(url, filename, output_dir)


def _direct_image_download(url, filename, output_dir):
    """Direct image download fallback."""
    import requests

    # Determine extension from URL
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
            BarColumn(bar_width=30),
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
        # Extract the error line
        for line in stderr.split('\n'):
            if 'ERROR:' in line:
                console.print(f"[red]{line.strip()}[/red]")
                break
        else:
            console.print(f"[red]Download failed[/red]")
    else:
        console.print(f"[red]Download failed. Try updating yt-dlp: yt-dlp -U[/red]")