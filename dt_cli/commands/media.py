import click, subprocess, shlex, tempfile, time
from pathlib import Path
from ..config import console, get_save_path, ask_filename, confirm_save, ensure_cli_tool, ensure_pip_module, IS_TERMUX, bar_width, BORDER_ROUNDED
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.prompt import Prompt, IntPrompt
from rich import box
from rich.live import Live
from rich.text import Text


def _require_ffmpeg():
    """Ensure ffmpeg is available, auto-installing if missing."""
    return ensure_cli_tool('ffmpeg', display_name='ffmpeg')


def _run_ffmpeg_with_progress(cmd, description="Processing..."):
    """Run ffmpeg with live progress tracking."""
    process = subprocess.Popen(
        cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True
    )

    duration = None
    current_time = None
    stderr_log = ''

    with Progress(
        SpinnerColumn("dots"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=bar_width()),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(f"[info]{description}[/info]", total=100)

        while True:
            line = process.stderr.readline()
            if not line and process.poll() is not None:
                break
            if 'Duration:' in line and duration is None:
                try:
                    h, m, s = line.split('Duration:')[1].strip().split(',')[0].split(':')
                    duration = int(h) * 3600 + int(m) * 60 + float(s)
                except Exception:
                    duration = None

            if 'time=' in line and duration:
                stderr_log += line
                try:
                    time_str = line.split('time=')[1].split(' ')[0]
                    h, m, s = time_str.split(':')
                    current_time = int(h) * 3600 + int(m) * 60 + float(s)
                    if duration > 0:
                        pct = min(100, (current_time / duration) * 100)
                        progress.update(task, completed=pct)
                except Exception:
                    pass

    if process.returncode != 0:
        # Collect remaining stderr for error reporting
        remaining = process.stderr.read() if process.stderr else ''
        _last_lines = (stderr_log + remaining).strip().split('\n')
        # Show last 3 lines of ffmpeg error
        for line in _last_lines[-3:]:
            if line.strip():
                console.print(f"  [dim]{line.strip()}[/dim]")
    return process.returncode == 0


@click.command()
def join():
    """Join/merge videos together"""
    if not _require_ffmpeg():
        return

    console.print()
    console.print(Panel("[bold brand]JOIN VIDEOS[/bold brand]\n[dim]Merge multiple videos into one[/dim]", border_style="brand", box=box.ROUNDED))

    raw_input = Prompt.ask("\n[info]Video files (space-separated)[/info]")
    try:
        files = shlex.split(raw_input)
    except ValueError:
        files = raw_input.split()

    if not files:
        console.print("[red]No files provided.[/red]")
        return

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
        success = _run_ffmpeg_with_progress(
            ['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', str(list_file),
             '-c', 'copy', str(output)],
            "Joining videos..."
        )

        if success and output.exists():
            size = output.stat().st_size / (1024 * 1024)
            console.print(f"[dim]Total size: {size:.1f} MB[/dim]")
            confirm_save(output)
        else:
            console.print("[red]Failed to join videos. Check that all files have the same codec/parameters.[/red]")
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
    console.print(Panel("[bold brand]EXTRACT AUDIO[/bold brand]\n[dim]Extract audio track from any video file[/dim]", border_style="brand", box=box.ROUNDED))

    video = Prompt.ask("\n[info]Video file path[/info]")
    if not Path(video).exists():
        console.print("[red]File not found.[/red]")
        return

    console.print("\n[bold]Audio format:[/bold]")
    console.print("  [accent]1[/accent]. MP3  (universal)")
    console.print("  [accent]2[/accent]. WAV  (lossless)")
    console.print("  [accent]3[/accent]. FLAC (lossless compressed)")
    console.print("  [accent]4[/accent]. AAC  (Apple/default)")
    console.print("  [accent]5[/accent]. OGG  (open source)")
    fmt = Prompt.ask("[info]Choose format[/info]", choices=["1", "2", "3", "4", "5"], default="1")

    fmt_map = {
        "1": (".mp3", ["-vn", "-acodec", "libmp3lame", "-q:a", "2"]),
        "2": (".wav", ["-vn", "-acodec", "pcm_s16le"]),
        "3": (".flac", ["-vn", "-acodec", "flac"]),
        "4": (".m4a", ["-vn", "-acodec", "aac", "-b:a", "192k"]),
        "5": (".ogg", ["-vn", "-acodec", "libvorbis", "-q:a", "5"]),
    }

    ext, args = fmt_map[fmt]
    filename = ask_filename(Path(video).stem)
    output = get_save_path('music') / f"{filename}{ext}"

    console.print(f"\n[info]Extracting audio from:[/info] [white]{video}[/white]")

    success = _run_ffmpeg_with_progress(
        ['ffmpeg', '-y', '-i', video] + args + [str(output)],
        f"Extracting {ext[1:].upper()} audio..."
    )

    if success and output.exists():
        size = output.stat().st_size / (1024 * 1024)
        console.print(f"[dim]Size: {size:.2f} MB[/dim]")
        confirm_save(output)
    else:
        console.print("[red]Failed to extract audio.[/red]")


@click.command()
def shrink():
    """Compress/reduce video file size"""
    if not _require_ffmpeg():
        return

    console.print()
    console.print(Panel("[bold brand]COMPRESS VIDEO[/bold brand]\n[dim]Reduce video file size while keeping quality[/dim]", border_style="brand", box=box.ROUNDED))

    video = Prompt.ask("\n[info]Video file path[/info]")
    if not Path(video).exists():
        console.print("[red]File not found.[/red]")
        return

    console.print("\n[bold]Quality preset:[/bold]")
    console.print("  [accent]1[/accent]. Low      (360p, smallest file)")
    console.print("  [accent]2[/accent]. Medium   (720p, good quality)")
    console.print("  [accent]3[/accent]. High     (1080p, best quality)")
    console.print("  [accent]4[/accent]. WhatsApp  (640px, optimized for sharing)")
    quality = Prompt.ask("[info]Choose quality[/info]", choices=["1", "2", "3", "4"], default="2")

    scales = {'1': '640:-2', '2': '1280:-2', '3': '1920:-2', '4': '640:-2'}
    crfs = {'1': '32', '2': '28', '3': '23', '4': '30'}
    labels = {'1': 'Low', '2': 'Medium', '3': 'High', '4': 'WhatsApp'}

    filename = ask_filename(f"{Path(video).stem}_compressed")
    output = get_save_path('videos') / f"{filename}.mp4"

    console.print(f"\n[info]Compressing to {labels[quality]} quality...[/info]")

    success = _run_ffmpeg_with_progress(
        ['ffmpeg', '-y', '-i', video, '-vf', f"scale={scales[quality]}",
         '-crf', crfs[quality], '-preset', 'fast', str(output)],
        f"Compressing ({labels[quality]})..."
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
        console.print("[red]Compression failed.[/red]")


@click.command()
def clip():
    """Cut a video clip"""
    if not _require_ffmpeg():
        return

    console.print()
    console.print(Panel("[bold brand]CUT VIDEO CLIP[/bold brand]\n[dim]Extract a portion of a video[/dim]", border_style="brand", box=box.ROUNDED))

    video = Prompt.ask("\n[info]Video file path[/info]")
    if not Path(video).exists():
        console.print("[red]File not found.[/red]")
        return

    start = Prompt.ask("[info]Start time (HH:MM:SS or MM:SS)[/info]", default="00:00:00")
    end = Prompt.ask("[info]End time (HH:MM:SS or MM:SS)[/info]", default="00:00:30")

    filename = ask_filename(f"clip_{Path(video).stem}")
    output = get_save_path('videos') / f"{filename}.mp4"

    console.print(f"\n[info]Cutting from {start} to {end}...[/info]")

    success = _run_ffmpeg_with_progress(
        ['ffmpeg', '-y', '-i', video, '-ss', start, '-to', end, '-c', 'copy', str(output)],
        "Cutting clip..."
    )

    if output.exists():
        size = output.stat().st_size / (1024 * 1024)
        console.print(f"[dim]Duration: {start} to {end}[/dim]")
        console.print(f"[dim]Size: {size:.1f} MB[/dim]")
        confirm_save(output)
    else:
        console.print("[red]Failed to cut clip.[/red]")


@click.command()
def gif():
    """Convert video to GIF with palette optimization"""
    if not _require_ffmpeg():
        return

    console.print()
    console.print(Panel("[bold brand]VIDEO TO GIF[/bold brand]\n[dim]Create an optimized GIF from any video[/dim]", border_style="brand", box=box.ROUNDED))

    video = Prompt.ask("\n[info]Video file path[/info]")
    if not Path(video).exists():
        console.print("[red]File not found.[/red]")
        return

    width = Prompt.ask("[info]Width in pixels[/info]", default="480")
    fps = Prompt.ask("[info]Frames per second[/info]", default="12")

    filename = ask_filename(Path(video).stem)
    output = get_save_path('images') / f"{filename}.gif"

    console.print(f"\n[info]Creating GIF ({width}px, {fps}fps)...[/info]")

    with Progress(
        SpinnerColumn("dots"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=bar_width()),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        progress.add_task("[info]Generating palette...[/info]", total=None)
        palette_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        palette_path = palette_file.name
        palette_file.close()

        subprocess.run([
            'ffmpeg', '-y', '-i', video,
            '-vf', f'fps={fps},scale={width}:-1:flags=lanczos,palettegen',
            str(palette_path)
        ], capture_output=True)

        progress.add_task("[info]Creating GIF...[/info]", total=None)
        result = subprocess.run([
            'ffmpeg', '-y', '-i', video, '-i', palette_path,
            '-lavfi', f'fps={fps},scale={width}:-1:flags=lanczos [x]; [x][1:v] paletteuse',
            str(output)
        ], capture_output=True)

        Path(palette_path).unlink(missing_ok=True)

    if output.exists():
        size = output.stat().st_size / (1024 * 1024)
        console.print(f"[dim]Size: {size:.2f} MB[/dim]")
        confirm_save(output)
    else:
        console.print("[red]GIF creation failed.[/red]")


@click.command()
def extract():
    """Extract all frames from a video"""
    if not _require_ffmpeg():
        return

    console.print()
    console.print(Panel("[bold brand]EXTRACT FRAMES[/bold brand]\n[dim]Extract every frame from a video as images[/dim]", border_style="brand", box=box.ROUNDED))

    video = Prompt.ask("\n[info]Video file path[/info]")
    if not Path(video).exists():
        console.print("[red]File not found.[/red]")
        return

    filename = ask_filename(f"{Path(video).stem}_frames")
    output_dir = get_save_path('images') / filename
    output_dir.mkdir(parents=True, exist_ok=True)

    success = _run_ffmpeg_with_progress(
        ['ffmpeg', '-y', '-i', video, str(output_dir / 'frame_%04d.png')],
        "Extracting frames..."
    )

    frames = list(output_dir.glob("frame_*.png"))
    if frames:
        console.print(f"[success]Extracted {len(frames)} frames[/success]")
        console.print(Panel(f"[dim]{output_dir}[/dim]", title="[success]FRAMES[/success]", border_style="success", box=box.ROUNDED))
    else:
        console.print("[red]Frame extraction failed.[/red]")


@click.command()
@click.argument('folder', required=False, default=".")
def compress(folder):
    """Compress images in a folder"""
    if not ensure_pip_module('PIL', pip_name='Pillow', display_name='Pillow'):
        return
    from PIL import Image
    target = Path(folder)

    console.print()
    console.print(Panel("[bold brand]COMPRESS IMAGES[/bold brand]\n[dim]Optimize images to reduce file size[/dim]", border_style="brand", box=box.ROUNDED))

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
        BarColumn(bar_width=bar_width()),
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


# ── NEW: Audio Editing Commands ────────────────────────────────────

@click.command()
def trim_audio():
    """Trim/cut an audio file"""
    if not _require_ffmpeg():
        return

    console.print()
    console.print(Panel("[bold brand]TRIM AUDIO[/bold brand]\n[dim]Cut a portion of an audio file[/dim]", border_style="brand", box=box.ROUNDED))

    audio = Prompt.ask("\n[info]Audio file path[/info]")
    if not Path(audio).exists():
        console.print("[red]File not found.[/red]")
        return

    start = Prompt.ask("[info]Start time (MM:SS or HH:MM:SS)[/info]", default="00:00")
    end = Prompt.ask("[info]End time (MM:SS or HH:MM:SS)[/info]", default="00:30")

    filename = ask_filename(f"trimmed_{Path(audio).stem}")
    ext = Path(audio).suffix
    output = get_save_path('music') / f"{filename}{ext}"

    success = _run_ffmpeg_with_progress(
        ['ffmpeg', '-y', '-i', audio, '-ss', start, '-to', end, '-c', 'copy', str(output)],
        "Trimming audio..."
    )

    if output.exists():
        size = output.stat().st_size / (1024 * 1024)
        console.print(f"[dim]Duration: {start} to {end} | Size: {size:.2f} MB[/dim]")
        confirm_save(output)
    else:
        console.print("[red]Failed to trim audio.[/red]")


@click.command()
def merge_audio():
    """Merge/join multiple audio files"""
    if not _require_ffmpeg():
        return

    console.print()
    console.print(Panel("[bold brand]MERGE AUDIO[/bold brand]\n[dim]Combine multiple audio files into one[/dim]", border_style="brand", box=box.ROUNDED))

    raw_input = Prompt.ask("\n[info]Audio files (space-separated)[/info]")
    try:
        files = shlex.split(raw_input)
    except ValueError:
        files = raw_input.split()

    if not files:
        console.print("[red]No files provided.[/red]")
        return

    for f in files:
        if not Path(f).exists():
            console.print(f"[red]File not found: {f}[/red]")
            return

    filename = ask_filename("merged_audio")
    output = get_save_path('music') / f"{filename}.mp3"

    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        list_file = Path(f.name)
        for aud in files:
            f.write(f"file '{Path(aud).absolute()}'\n")

    try:
        success = _run_ffmpeg_with_progress(
            ['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', str(list_file),
             '-acodec', 'libmp3lame', '-q:a', '2', str(output)],
            "Merging audio files..."
        )

        if output.exists():
            size = output.stat().st_size / (1024 * 1024)
            console.print(f"[dim]Merged {len(files)} files | Size: {size:.2f} MB[/dim]")
            confirm_save(output)
        else:
            console.print("[red]Failed to merge audio. Ensure files have the same format/sample rate.[/red]")
    finally:
        if list_file.exists():
            list_file.unlink()


@click.command()
def audio_speed():
    """Change the speed of an audio file"""
    if not _require_ffmpeg():
        return

    console.print()
    console.print(Panel("[bold brand]AUDIO SPEED CHANGE[/bold brand]\n[dim]Speed up or slow down audio[/dim]", border_style="brand", box=box.ROUNDED))

    audio = Prompt.ask("\n[info]Audio file path[/info]")
    if not Path(audio).exists():
        console.print("[red]File not found.[/red]")
        return

    console.print("\n[bold]Speed multiplier:[/bold]")
    console.print("  [accent]0.5[/accent] - Half speed (slow)")
    console.print("  [accent]0.75[/accent] - 75% speed")
    console.print("  [accent]1.5[/accent] - 1.5x speed")
    console.print("  [accent]2.0[/accent] - Double speed (fast)")
    speed = Prompt.ask("[info]Enter speed (e.g. 1.5)[/info]", default="1.5")

    try:
        speed_val = float(speed)
        if speed_val <= 0 or speed_val > 4:
            console.print("[red]Speed must be between 0.01 and 4.0[/red]")
            return
    except ValueError:
        console.print("[red]Invalid number.[/red]")
        return

    filename = ask_filename(f"{Path(audio).stem}_{speed}x")
    ext = Path(audio).suffix
    output = get_save_path('music') / f"{filename}{ext}"

    # atempo filter range is [0.5, 100.0], for values outside chain filters
    def build_atempo_filter(val):
        filters = []
        while val > 2.0:
            filters.append("atempo=2.0")
            val /= 2.0
        while val < 0.5:
            filters.append("atempo=0.5")
            val /= 0.5
        filters.append(f"atempo={val}")
        return ",".join(filters)

    atempo_filter = build_atempo_filter(speed_val)

    success = _run_ffmpeg_with_progress(
        ['ffmpeg', '-y', '-i', audio, '-filter:a', atempo_filter, str(output)],
        f"Changing speed to {speed_val}x..."
    )

    if output.exists():
        size = output.stat().st_size / (1024 * 1024)
        console.print(f"[dim]Speed: {speed_val}x | Size: {size:.2f} MB[/dim]")
        confirm_save(output)
    else:
        console.print("[red]Failed to change audio speed.[/red]")


@click.command()
def video_speed():
    """Change the speed of a video"""
    if not _require_ffmpeg():
        return

    console.print()
    console.print(Panel("[bold brand]VIDEO SPEED CHANGE[/bold brand]\n[dim]Speed up or slow down a video[/dim]", border_style="brand", box=box.ROUNDED))

    video = Prompt.ask("\n[info]Video file path[/info]")
    if not Path(video).exists():
        console.print("[red]File not found.[/red]")
        return

    console.print("\n[bold]Speed multiplier:[/bold]")
    console.print("  [accent]0.5[/accent] - Slow motion")
    console.print("  [accent]1.5[/accent] - 1.5x faster")
    console.print("  [accent]2.0[/accent] - Double speed")
    speed = Prompt.ask("[info]Enter speed (e.g. 1.5)[/info]", default="1.5")

    try:
        speed_val = float(speed)
        if speed_val <= 0 or speed_val > 4:
            console.print("[red]Speed must be between 0.01 and 4.0[/red]")
            return
    except ValueError:
        console.print("[red]Invalid number.[/red]")
        return

    filename = ask_filename(f"{Path(video).stem}_{speed}x")
    output = get_save_path('videos') / f"{filename}.mp4"

    # Both video and audio filters
    v_filter = f"setpts={1/speed_val}*PTS"

    def build_atempo(val):
        filters = []
        while val > 2.0:
            filters.append("atempo=2.0")
            val /= 2.0
        while val < 0.5:
            filters.append("atempo=0.5")
            val /= 0.5
        filters.append(f"atempo={val}")
        return ",".join(filters)

    a_filter = build_atempo(speed_val)

    success = _run_ffmpeg_with_progress(
        ['ffmpeg', '-y', '-i', video,
         '-filter:v', v_filter, '-filter:a', a_filter,
         '-preset', 'fast', str(output)],
        f"Changing video speed to {speed_val}x..."
    )

    if output.exists():
        orig_size = Path(video).stat().st_size / (1024 * 1024)
        new_size = output.stat().st_size / (1024 * 1024)
        console.print(f"[dim]Speed: {speed_val}x | Size: {new_size:.1f} MB (was {orig_size:.1f} MB)[/dim]")
        confirm_save(output)
    else:
        console.print("[red]Failed to change video speed.[/red]")


@click.command()
def reverse_video():
    """Reverse a video (play backwards)"""
    if not _require_ffmpeg():
        return

    console.print()
    console.print(Panel("[bold brand]REVERSE VIDEO[/bold brand]\n[dim]Play a video in reverse[/dim]", border_style="brand", box=box.ROUNDED))

    video = Prompt.ask("\n[info]Video file path[/info]")
    if not Path(video).exists():
        console.print("[red]File not found.[/red]")
        return

    filename = ask_filename(f"reversed_{Path(video).stem}")
    output = get_save_path('videos') / f"{filename}.mp4"

    success = _run_ffmpeg_with_progress(
        ['ffmpeg', '-y', '-i', video, '-vf', 'reverse', '-af', 'areverse',
         '-preset', 'fast', str(output)],
        "Reversing video..."
    )

    if output.exists():
        size = output.stat().st_size / (1024 * 1024)
        console.print(f"[dim]Size: {size:.1f} MB[/dim]")
        confirm_save(output)
    else:
        console.print("[red]Failed to reverse video.[/red]")


@click.command()
def add_audio():
    """Add/replace audio track on a video"""
    if not _require_ffmpeg():
        return

    console.print()
    console.print(Panel("[bold brand]ADD AUDIO TO VIDEO[/bold brand]\n[dim]Add or replace the audio track of a video[/dim]", border_style="brand", box=box.ROUNDED))

    video = Prompt.ask("\n[info]Video file path[/info]")
    if not Path(video).exists():
        console.print("[red]Video not found.[/red]")
        return

    audio = Prompt.ask("[info]Audio file path[/info]")
    if not Path(audio).exists():
        console.print("[red]Audio not found.[/red]")
        return

    filename = ask_filename(f"{Path(video).stem}_with_audio")
    output = get_save_path('videos') / f"{filename}.mp4"

    success = _run_ffmpeg_with_progress(
        ['ffmpeg', '-y', '-i', video, '-i', audio,
         '-c:v', 'copy', '-c:a', 'aac', '-map', '0:v:0', '-map', '1:a:0',
         '-shortest', str(output)],
        "Adding audio to video..."
    )

    if output.exists():
        size = output.stat().st_size / (1024 * 1024)
        console.print(f"[dim]Size: {size:.1f} MB[/dim]")
        confirm_save(output)
    else:
        console.print("[red]Failed to add audio.[/red]")


@click.command()
def mute_video():
    """Remove audio from a video (mute)"""
    if not _require_ffmpeg():
        return

    console.print()
    console.print(Panel("[bold brand]MUTE VIDEO[/bold brand]\n[dim]Remove the audio track from a video[/dim]", border_style="brand", box=box.ROUNDED))

    video = Prompt.ask("\n[info]Video file path[/info]")
    if not Path(video).exists():
        console.print("[red]File not found.[/red]")
        return

    filename = ask_filename(f"muted_{Path(video).stem}")
    output = get_save_path('videos') / f"{filename}.mp4"

    success = _run_ffmpeg_with_progress(
        ['ffmpeg', '-y', '-i', video, '-an', '-c:v', 'copy', str(output)],
        "Removing audio..."
    )

    if output.exists():
        size = output.stat().st_size / (1024 * 1024)
        console.print(f"[dim]Size: {size:.1f} MB (muted)[/dim]")
        confirm_save(output)
    else:
        console.print("[red]Failed to mute video.[/red]")


@click.command()
def watermark():
    """Add a text watermark to a video"""
    if not _require_ffmpeg():
        return

    console.print()
    console.print(Panel("[bold brand]ADD WATERMARK[/bold brand]\n[dim]Add a text watermark to your video[/dim]", border_style="brand", box=box.ROUNDED))

    video = Prompt.ask("\n[info]Video file path[/info]")
    if not Path(video).exists():
        console.print("[red]File not found.[/red]")
        return

    text = Prompt.ask("[info]Watermark text[/info]", default="DT CLI")

    console.print("\n[bold]Position:[/bold]")
    console.print("  [accent]1[/accent]. Top-Left")
    console.print("  [accent]2[/accent]. Top-Right")
    console.print("  [accent]3[/accent]. Bottom-Left")
    console.print("  [accent]4[/accent]. Bottom-Right")
    console.print("  [accent]5[/accent]. Center")
    pos = Prompt.ask("[info]Position[/info]", choices=["1", "2", "3", "4", "5"], default="4")

    positions = {
        "1": "10:10", "2": "w-tw-10:10", "3": "10:h-th-10", "4": "w-tw-10:h-th-10", "5": "(w-tw)/2:(h-th)/2"
    }

    filename = ask_filename(f"watermarked_{Path(video).stem}")
    output = get_save_path('videos') / f"{filename}.mp4"

    # Find a font file (required on Termux/Android, good practice everywhere)
    font_file = None
    font_paths = [
        '/system/fonts/DroidSans.ttf',
        '/system/fonts/Roboto-Regular.ttf',
        '/system/fonts/NotoSans-Regular.ttf',
        '/system/fonts/NotoSansCJK-Regular.ttc',
    ]
    for fp in font_paths:
        if Path(fp).exists():
            font_file = fp
            break

    # Build drawtext filter with separate x and y
    pos_str = positions[pos]
    pos_x, pos_y = pos_str.split(':', 1)

    if font_file:
        filter_str = f"drawtext=fontfile={font_file}:text='{text}':fontsize=24:fontcolor=white@0.7:borderw=1:bordercolor=black@0.5:x={pos_x}:y={pos_y}"
    else:
        filter_str = f"drawtext=text='{text}':fontsize=24:fontcolor=white@0.7:borderw=1:bordercolor=black@0.5:x={pos_x}:y={pos_y}"

    success = _run_ffmpeg_with_progress(
        ['ffmpeg', '-y', '-i', video, '-vf', filter_str,
         '-c:a', 'copy', '-preset', 'fast', str(output)],
        "Adding watermark..."
    )

    if output.exists():
        size = output.stat().st_size / (1024 * 1024)
        console.print(f"[dim]Watermark: '{text}' | Size: {size:.1f} MB[/dim]")
        confirm_save(output)
    else:
        console.print("[red]Failed to add watermark.[/red]")


@click.command()
def thumbnail():
    """Extract a thumbnail/poster from a video"""
    if not _require_ffmpeg():
        return

    console.print()
    console.print(Panel("[bold brand]VIDEO THUMBNAIL[/bold brand]\n[dim]Extract a high-quality thumbnail from any video[/dim]", border_style="brand", box=box.ROUNDED))

    video = Prompt.ask("\n[info]Video file path[/info]")
    if not Path(video).exists():
        console.print("[red]File not found.[/red]")
        return

    timestamp = Prompt.ask("[info]Timestamp (HH:MM:SS)[/info]", default="00:00:05")

    filename = ask_filename(f"thumb_{Path(video).stem}")
    output = get_save_path('images') / f"{filename}.jpg"

    with Progress(
        SpinnerColumn("dots"),
        TextColumn("[progress.description]{task.description}"),
        console=console, transient=True,
    ) as progress:
        progress.add_task("[info]Extracting thumbnail...[/info]", total=None)
        result = subprocess.run([
            'ffmpeg', '-y', '-ss', timestamp, '-i', video,
            '-vframes', '1', '-q:v', '2', str(output)
        ], capture_output=True, text=True)

    if output.exists():
        size = output.stat().st_size / 1024
        console.print(f"[dim]Size: {size:.2f} KB[/dim]")
        confirm_save(output)
    else:
        console.print("[red]Failed to extract thumbnail.[/red]")


@click.command()
def audio_info():
    """Get detailed info about an audio file"""
    if not _require_ffmpeg():
        return
    if not ensure_cli_tool('ffprobe', display_name='ffprobe'):
        return

    console.print()
    audio = Prompt.ask("[info]Audio file path[/info]")
    if not Path(audio).exists():
        console.print("[red]File not found.[/red]")
        return

    result = subprocess.run(
        ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', audio],
        capture_output=True, text=True
    )

    try:
        import json
        data = json.loads(result.stdout)

        # Audio stream info
        audio_stream = None
        for stream in data.get('streams', []):
            if stream.get('codec_type') == 'audio':
                audio_stream = stream
                break

        table = Table(box=box.ROUNDED, border_style="accent", show_header=False, padding=(0, 2))
        table.add_column(style="dim", ratio=1)
        table.add_column(style="white", ratio=2)

        fmt = data.get('format', {})
        table.add_row("File", Path(audio).name)
        table.add_row("Size", f"{int(fmt.get('size', 0)) / (1024*1024):.2f} MB")
        table.add_row("Duration", f"{float(fmt.get('duration', 0)):.1f} seconds")

        if audio_stream:
            table.add_row("Codec", audio_stream.get('codec_name', 'N/A'))
            table.add_row("Sample Rate", f"{int(audio_stream.get('sample_rate', 0))} Hz")
            table.add_row("Channels", str(audio_stream.get('channels', 'N/A')))
            table.add_row("Bit Rate", f"{int(audio_stream.get('bit_rate', 0)) // 1000} kbps")

        console.print(table)
    except Exception as e:
        console.print(f"[red]Could not read audio info: {e}[/red]")


@click.command()
def video_info():
    """Get detailed info about a video file"""
    if not _require_ffmpeg():
        return
    if not ensure_cli_tool('ffprobe', display_name='ffprobe'):
        return

    console.print()
    video = Prompt.ask("[info]Video file path[/info]")
    if not Path(video).exists():
        console.print("[red]File not found.[/red]")
        return

    result = subprocess.run(
        ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', video],
        capture_output=True, text=True
    )

    try:
        import json
        data = json.loads(result.stdout)

        video_stream = None
        audio_stream = None
        for stream in data.get('streams', []):
            if stream.get('codec_type') == 'video' and video_stream is None:
                video_stream = stream
            elif stream.get('codec_type') == 'audio' and audio_stream is None:
                audio_stream = stream

        table = Table(box=box.ROUNDED, border_style="accent", show_header=False, padding=(0, 2))
        table.add_column(style="dim", ratio=1)
        table.add_column(style="white", ratio=2)

        fmt = data.get('format', {})
        table.add_row("File", Path(video).name)
        table.add_row("Size", f"{int(fmt.get('size', 0)) / (1024*1024):.2f} MB")
        table.add_row("Duration", f"{float(fmt.get('duration', 0)):.1f} seconds")

        if video_stream:
            w = video_stream.get('width', '?')
            h = video_stream.get('height', '?')
            table.add_row("Resolution", f"{w}x{h}")
            table.add_row("Video Codec", video_stream.get('codec_name', 'N/A'))
            fps = video_stream.get('r_frame_rate', '0/1')
            try:
                num, den = fps.split('/')
                fps_val = float(num) / float(den)
                table.add_row("FPS", f"{fps_val:.1f}")
            except Exception:
                table.add_row("FPS", fps)

        if audio_stream:
            table.add_row("Audio Codec", audio_stream.get('codec_name', 'N/A'))
            table.add_row("Sample Rate", f"{int(audio_stream.get('sample_rate', 0))} Hz")

        console.print(table)
    except Exception as e:
        console.print(f"[red]Could not read video info: {e}[/red]")