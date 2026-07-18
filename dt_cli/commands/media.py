import click, subprocess, shlex, tempfile
from pathlib import Path
from ..config import console, get_save_path, ask_filename, confirm_save, check_ffmpeg, BORDER_ROUNDED
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.prompt import Prompt
from rich import box


def _require_ffmpeg():
    """Check ffmpeg and show install instructions if missing."""
    if not check_ffmpeg():
        console.print(Panel(
            "[bold warn]ffmpeg is required for media commands[/bold warn]\n\n"
            "Install with:\n"
            "  [accent]sudo apt install ffmpeg[/accent]      (Ubuntu/Debian)\n"
            "  [accent]brew install ffmpeg[/accent]          (macOS)\n"
            "  [accent]choco install ffmpeg[/accent]         (Windows)\n"
            "  [accent]pkg install ffmpeg[/accent]           (Termux)",
            border_style="warn", box=box.ROUNDED
        ))
        return False
    return True


@click.command()
def join():
    """Join/merge videos together"""
    if not _require_ffmpeg():
        return

    console.print()
    console.print(Panel("[bold brand]JOIN VIDEOS[/bold brand]", border_style="brand", box=box.ROUNDED))

    raw_input = Prompt.ask("\n[info]Video files (space-separated)[/info]")
    try:
        files = shlex.split(raw_input)
    except ValueError:
        files = raw_input.split()

    if not files:
        console.print("[red]No files provided.[/red]")
        return

    # Validate all files exist
    for f in files:
        if not Path(f).exists():
            console.print(f"[red]File not found: {f}[/red]")
            return

    filename = ask_filename("joined")
    output = get_save_path('videos') / f"{filename}.mp4"

    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        list_file = Path(f.name)
        for vid in files:
            f.write(f"file '{Path(vid).absolute()}'\n")

    try:
        with Progress(
            SpinnerColumn("dots"),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=30),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            progress.add_task("[info]Joining videos...[/info]", total=None)
            result = subprocess.run(
                ['ffmpeg', '-f', 'concat', '-safe', '0', '-i', str(list_file),
                 '-c', 'copy', str(output)],
                capture_output=True, text=True
            )

        if result.returncode != 0:
            console.print(f"[red]FFmpeg Error: {result.stderr[-300:]}[/red]")
            return

        size = output.stat().st_size / (1024 * 1024)
        console.print(f"[dim]Total size: {size:.1f} MB[/dim]")
        confirm_save(output)
    except FileNotFoundError:
        console.print("[red]ffmpeg not found.[/red]")
    except OSError as e:
        if "225" in str(e):
            console.print("[red]Antivirus blocked ffmpeg. Add folder to exclusions.[/red]")
        else:
            console.print(f"[red]System Error: {e}[/red]")
    finally:
        if list_file.exists():
            list_file.unlink()


@click.command()
def music():
    """Extract audio from video"""
    if not _require_ffmpeg():
        return

    console.print()
    console.print(Panel("[bold brand]EXTRACT AUDIO[/bold brand]", border_style="brand", box=box.ROUNDED))

    video = Prompt.ask("\n[info]Video file path[/info]")
    if not Path(video).exists():
        console.print("[red]File not found.[/red]")
        return

    filename = ask_filename(Path(video).stem)
    output = get_save_path('music') / f"{filename}.mp3"

    console.print(f"\n[info]Extracting audio from:[/info] [white]{video}[/white]")

    with Progress(
        SpinnerColumn("dots"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=30),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        progress.add_task("[info]Extracting audio...[/info]", total=None)
        result = subprocess.run(
            ['ffmpeg', '-y', '-i', video, '-vn', '-acodec', 'libmp3lame', '-q:a', '2', str(output)],
            capture_output=True, text=True
        )

    if result.returncode == 0 and output.exists():
        size = output.stat().st_size / (1024 * 1024)
        console.print(f"[dim]Size: {size:.2f} MB[/dim]")
        confirm_save(output)
    else:
        console.print(f"[red]Failed to extract audio: {result.stderr[-200:]}[/red]")


@click.command()
def shrink():
    """Compress/reduce video file size"""
    if not _require_ffmpeg():
        return

    console.print()
    console.print(Panel("[bold brand]COMPRESS VIDEO[/bold brand]", border_style="brand", box=box.ROUNDED))

    video = Prompt.ask("\n[info]Video file path[/info]")
    if not Path(video).exists():
        console.print("[red]File not found.[/red]")
        return

    console.print("\n[bold]Quality preset:[/bold]")
    console.print("  [accent]1[/accent]. WhatsApp  (640px, small file)")
    console.print("  [accent]2[/accent]. Small     (1280px, good quality)")
    console.print("  [accent]3[/accent]. Medium    (1920px, HD)")
    quality = Prompt.ask("[info]Choose quality[/info]", choices=["1", "2", "3"], default="2")

    scales = {'1': '640:-2', '2': '1280:-2', '3': '1920:-2'}
    labels = {'1': 'WhatsApp', '2': 'Small', '3': 'Medium'}

    filename = ask_filename(f"{Path(video).stem}_compressed")
    output = get_save_path('videos') / f"{filename}.mp4"

    console.print(f"\n[info]Compressing to {labels[quality]} quality...[/info]")

    with Progress(
        SpinnerColumn("dots"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=30),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        progress.add_task("[info]Compressing video...[/info]", total=None)
        result = subprocess.run(
            ['ffmpeg', '-y', '-i', video, '-vf', f"scale={scales[quality]}", '-crf', '28', '-preset', 'fast', str(output)],
            capture_output=True, text=True
        )

    if output.exists():
        orig_size = Path(video).stat().st_size / (1024 * 1024)
        new_size = output.stat().st_size / (1024 * 1024)
        reduction = (1 - new_size / orig_size) * 100 if orig_size > 0 else 0

        table = Table(box=box.ROUNDED, border_style="success", show_header=False, padding=(0, 2))
        table.add_column(style="dim", ratio=1)
        table.add_column(style="white", ratio=2)
        table.add_row("Original", f"{orig_size:.1f} MB")
        table.add_row("Compressed", f"{new_size:.1f} MB")
        table.add_row("Reduction", f"[success]{reduction:.0f}%[/success]")
        console.print(table)
        confirm_save(output)
    else:
        console.print(f"[red]Compression failed: {result.stderr[-200:]}[/red]")


@click.command()
def clip():
    """Cut a video clip"""
    if not _require_ffmpeg():
        return

    console.print()
    console.print(Panel("[bold brand]CUT VIDEO CLIP[/bold brand]", border_style="brand", box=box.ROUNDED))

    video = Prompt.ask("\n[info]Video file path[/info]")
    if not Path(video).exists():
        console.print("[red]File not found.[/red]")
        return

    start = Prompt.ask("[info]Start time[/info]", default="00:00:00")
    end = Prompt.ask("[info]End time[/info]", default="00:00:30")

    filename = ask_filename(f"clip_{Path(video).stem}")
    output = get_save_path('videos') / f"{filename}.mp4"

    console.print(f"\n[info]Cutting from {start} to {end}...[/info]")

    with Progress(
        SpinnerColumn("dots"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=30),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        progress.add_task("[info]Cutting clip...[/info]", total=None)
        result = subprocess.run(
            ['ffmpeg', '-y', '-i', video, '-ss', start, '-to', end, '-c', 'copy', str(output)],
            capture_output=True, text=True
        )

    if output.exists():
        size = output.stat().st_size / (1024 * 1024)
        console.print(f"[dim]Duration: {start} to {end}[/dim]")
        console.print(f"[dim]Size: {size:.1f} MB[/dim]")
        confirm_save(output)
    else:
        console.print(f"[red]Failed to cut clip: {result.stderr[-200:]}[/red]")


@click.command()
def gif():
    """Convert video to GIF with palette optimization"""
    if not _require_ffmpeg():
        return

    console.print()
    console.print(Panel("[bold brand]VIDEO TO GIF[/bold brand]", border_style="brand", box=box.ROUNDED))

    video = Prompt.ask("\n[info]Video file path[/info]")
    if not Path(video).exists():
        console.print("[red]File not found.[/red]")
        return

    console.print("\n[bold]GIF Settings:[/bold]")
    width = Prompt.ask("[info]Width in pixels[/info]", default="480")
    fps = Prompt.ask("[info]Frames per second[/info]", default="12")

    filename = ask_filename(Path(video).stem)
    output = get_save_path('images') / f"{filename}.gif"

    console.print(f"\n[info]Creating GIF ({width}px, {fps}fps)...[/info]")

    # Two-pass palette optimization for high quality GIF
    with Progress(
        SpinnerColumn("dots"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=30),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        progress.add_task("[info]Generating palette...[/info]", total=None)
        # Pass 1: Generate palette
        palette_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        palette_path = palette_file.name
        palette_file.close()

        subprocess.run([
            'ffmpeg', '-y', '-i', video,
            '-vf', f'fps={fps},scale={width}:-1:flags=lanczos,palettegen',
            str(palette_path)
        ], capture_output=True)

        progress.add_task("[info]Creating GIF...[/info]", total=None)
        # Pass 2: Create GIF using palette
        result = subprocess.run([
            'ffmpeg', '-y', '-i', video, '-i', palette_path,
            '-lavfi', f'fps={fps},scale={width}:-1:flags=lanczos [x]; [x][1:v] paletteuse',
            str(output)
        ], capture_output=True)

        # Clean up palette
        Path(palette_path).unlink(missing_ok=True)

    if output.exists():
        size = output.stat().st_size / (1024 * 1024)
        console.print(f"[dim]Size: {size:.2f} MB[/dim]")
        confirm_save(output)
    else:
        console.print(f"[red]GIF creation failed: {result.stderr[-200:]}[/red]")


@click.command()
def extract():
    """Extract all frames from a video"""
    if not _require_ffmpeg():
        return

    console.print()
    console.print(Panel("[bold brand]EXTRACT FRAMES[/bold brand]", border_style="brand", box=box.ROUNDED))

    video = Prompt.ask("\n[info]Video file path[/info]")
    if not Path(video).exists():
        console.print("[red]File not found.[/red]")
        return

    filename = ask_filename(f"{Path(video).stem}_frames")
    output_dir = get_save_path('images') / filename
    output_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"\n[info]Extracting frames...[/info]")

    with Progress(
        SpinnerColumn("dots"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=30),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        progress.add_task("[info]Extracting frames...[/info]", total=None)
        result = subprocess.run(
            ['ffmpeg', '-y', '-i', video, str(output_dir / 'frame_%04d.png')],
            capture_output=True, text=True
        )

    frames = list(output_dir.glob("frame_*.png"))
    if frames:
        console.print(f"[success]Extracted {len(frames)} frames to {output_dir}[/success]")
        console.print(Panel(f"[dim]{output_dir}[/dim]", title="[success]FRAMES[/success]", border_style="success", box=box.ROUNDED))
    else:
        console.print(f"[red]Frame extraction failed: {result.stderr[-200:]}[/red]")


@click.command()
@click.argument('folder', required=False, default=".")
def compress(folder):
    """Compress images in a folder"""
    from PIL import Image
    target = Path(folder)

    console.print()
    console.print(Panel("[bold brand]COMPRESS IMAGES[/bold brand]", border_style="brand", box=box.ROUNDED))

    if not target.exists():
        console.print(f"[red]Directory not found: {folder}[/red]")
        return

    image_files = []
    for img_path in target.rglob('*'):
        if img_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp', '.bmp']:
            if not any(d in str(img_path) for d in ['node_modules', '.git', '.dt', '__pycache__']):
                image_files.append(img_path)

    if not image_files:
        console.print("[yellow]No images found to compress.[/yellow]")
        return

    console.print(f"\n[info]Found {len(image_files)} image(s) to compress...[/info]\n")

    total_saved = 0
    with Progress(
        SpinnerColumn("dots"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=30),
        console=console,
    ) as progress:
        task = progress.add_task("[info]Compressing...[/info]", total=len(image_files))
        for img_path in image_files:
            try:
                orig_size = img_path.stat().st_size
                img = Image.open(img_path)
                img.save(img_path, optimize=True, quality=85)
                new_size = img_path.stat().st_size
                saved = orig_size - new_size
                if saved > 0:
                    total_saved += saved
            except Exception:
                pass
            progress.advance(task)

    console.print(f"\n[success]Compressed {len(image_files)} images[/success]")
    console.print(f"[dim]Total space saved: {total_saved / 1024:.1f} KB[/dim]")