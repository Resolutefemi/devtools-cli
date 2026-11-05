import click
import subprocess
import shlex
import tempfile
import re
import os
import math
from pathlib import Path

from ..config import (
    console,
    get_save_path,
    ask_filename,
    confirm_save,
    ensure_cli_tool,
    ensure_pip_module,
    bar_width,
)

from rich.panel import Panel
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.prompt import Prompt
from rich import box


# ─────────────────────────────────────────────────────────────
# Common helpers
# ─────────────────────────────────────────────────────────────

def _require_ffmpeg():
    """Ensure ffmpeg is available."""
    return ensure_cli_tool("ffmpeg", display_name="ffmpeg")


def _valid_file(path, label="File"):
    """Check whether a path points to an existing regular file."""
    try:
        p = Path(path).expanduser()
        if not p.exists() or not p.is_file():
            console.print(f"[red]{label} not found: {path}[/red]")
            return None
        return p.resolve()
    except (OSError, TypeError, ValueError) as exc:
        console.print(f"[red]Invalid {label.lower()} path: {exc}[/red]")
        return None


def _prepare_output(category, filename, extension):
    """Create an output path and ensure its directory exists."""
    try:
        directory = Path(get_save_path(category)).expanduser()
        directory.mkdir(parents=True, exist_ok=True)

        name = str(filename or "").strip()
        name = Path(name).name
        name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
        name = name.strip(" .")

        if not name:
            name = "output"

        # Empty extension is valid for directory names.
        if extension:
            extension = (
                extension
                if extension.startswith(".")
                else f".{extension}"
            )
        else:
            extension = ""

        return directory / f"{name}{extension}"

    except (OSError, TypeError, ValueError) as exc:
        console.print(
            f"[red]Could not prepare output directory: {exc}[/red]"
        )
        return None


def _output_ready(path):
    """Return True only if a non-empty output file exists."""
    try:
        p = Path(path)
        return p.is_file() and p.stat().st_size > 0
    except OSError:
        return False


def _remove_partial(path):
    """Remove an incomplete output file, if possible."""
    try:
        p = Path(path)
        if p.exists() and p.is_file():
            p.unlink()
    except OSError:
        pass


def _parse_time(value):
    """Parse HH:MM:SS, MM:SS or seconds into seconds."""
    value = str(value).strip()

    if not value:
        raise ValueError("Time cannot be empty.")

    parts = value.split(":")

    if len(parts) not in (1, 2, 3):
        raise ValueError("Use HH:MM:SS, MM:SS or seconds.")

    try:
        numbers = [float(part) for part in parts]
    except ValueError:
        raise ValueError("Time contains an invalid number.")

    if any(not math.isfinite(n) or n < 0 for n in numbers):
        raise ValueError("Time values must be finite and non-negative.")

    if len(numbers) == 1:
        return numbers[0]

    if len(numbers) == 2:
        minutes, seconds = numbers
        if seconds >= 60:
            raise ValueError("Seconds must be less than 60.")
        return minutes * 60 + seconds

    hours, minutes, seconds = numbers

    if minutes >= 60 or seconds >= 60:
        raise ValueError("Minutes and seconds must be less than 60.")

    return hours * 3600 + minutes * 60 + seconds


def _validate_time_range(start, end):
    """Validate a start/end time range."""
    try:
        start_seconds = _parse_time(start)
        end_seconds = _parse_time(end)

        if end_seconds <= start_seconds:
            console.print(
                "[red]End time must be greater than start time.[/red]"
            )
            return False

        return True

    except ValueError as exc:
        console.print(f"[red]Invalid time: {exc}[/red]")
        return False


def _concat_quote(path):
    """Escape a path for FFmpeg concat demuxer list files."""
    value = str(Path(path).resolve())
    value = value.replace("\\", "\\\\")
    value = value.replace("'", "\\'")
    value = value.replace("\n", "\\n")
    value = value.replace("\r", "\\r")
    return f"file '{value}'\n"


def _create_concat_list(files):
    """Create a temporary FFmpeg concat list."""
    temp = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".txt",
        delete=False,
    )

    list_path = Path(temp.name)

    try:
        for item in files:
            temp.write(_concat_quote(item))

        temp.close()
        return list_path

    except Exception:
        temp.close()
        _remove_partial(list_path)
        raise


def _build_atempo_filter(speed):
    """Build an FFmpeg atempo chain for supported speeds."""
    filters = []

    while speed > 2.0:
        filters.append("atempo=2.0")
        speed /= 2.0

    while speed < 0.5:
        filters.append("atempo=0.5")
        speed /= 0.5

    filters.append(f"atempo={speed:.8g}")
    return ",".join(filters)


def _escape_drawtext(value):
    """Escape user text for FFmpeg drawtext filter."""
    value = str(value)

    replacements = {
        "\\": "\\\\",
        "'": "\\'",
        ":": "\\:",
        ",": "\\,",
        "[": "\\[",
        "]": "\\]",
        "%": "\\%",
        "\n": " ",
        "\r": " ",
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    return value


def _run_ffmpeg_with_progress(cmd, description="Processing..."):
    """Run FFmpeg and track progress without blocking on stdout."""
    process = None
    stderr_log = []
    duration = None

    try:
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            errors="replace",
            bufsize=1,
        )

        with Progress(
            SpinnerColumn("dots"),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=bar_width()),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:

            task = progress.add_task(
                f"[info]{description}[/info]",
                total=100,
            )

            if process.stderr is not None:
                for line in process.stderr:
                    if not line:
                        continue

                    line = line.rstrip()
                    stderr_log.append(line)

                    if len(stderr_log) > 80:
                        stderr_log.pop(0)

                    if duration is None and "Duration:" in line:
                        try:
                            duration_text = (
                                line.split("Duration:", 1)[1]
                                .strip()
                                .split(",", 1)[0]
                            )
                            duration = _parse_time(duration_text)
                        except (ValueError, IndexError):
                            duration = None

                    if duration and duration > 0 and "time=" in line:
                        try:
                            time_text = (
                                line.split("time=", 1)[1].split()[0]
                            )
                            current_time = _parse_time(time_text)

                            percentage = min(
                                100,
                                max(0, current_time / duration * 100),
                            )

                            progress.update(
                                task,
                                completed=percentage,
                            )

                        except (ValueError, IndexError):
                            pass

        return_code = process.wait()

        if return_code != 0:
            console.print("[red]FFmpeg reported an error:[/red]")

            for line in stderr_log[-5:]:
                if line.strip():
                    console.print(f"  [dim]{line}[/dim]")

            return False

        return True

    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled.[/yellow]")

        if process is not None and process.poll() is None:
            process.terminate()

            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

        return False

    except FileNotFoundError:
        console.print("[red]FFmpeg executable was not found.[/red]")
        return False

    except OSError as exc:
        console.print(f"[red]FFmpeg system error: {exc}[/red]")
        return False

    finally:
        if process is not None:
            if process.poll() is None:
                process.kill()
                process.wait()

            if process.stderr is not None:
                try:
                    process.stderr.close()
                except OSError:
                    pass


def _show_saved_file(path, label="File"):
    """Display output information and ask whether to keep the file."""
    if not _output_ready(path):
        console.print(f"[red]{label} creation failed.[/red]")
        _remove_partial(path)
        return False

    try:
        size = Path(path).stat().st_size / (1024 * 1024)
        console.print(f"[dim]Size: {size:.2f} MB[/dim]")
        confirm_save(path)
        return True

    except OSError as exc:
        console.print(f"[red]Could not access output file: {exc}[/red]")
        return False


def _get_multiple_files(prompt_text):
    """Read multiple file paths, supporting quoted paths."""
    raw_input = Prompt.ask(prompt_text).strip()

    if not raw_input:
        console.print("[red]No files provided.[/red]")
        return None

    try:
        files = shlex.split(raw_input)
    except ValueError as exc:
        console.print(f"[red]Invalid file list: {exc}[/red]")
        return None

    if not files:
        console.print("[red]No files provided.[/red]")
        return None

    resolved = []

    for item in files:
        path = _valid_file(item)

        if path is None:
            return None

        resolved.append(path)

    return resolved


def _ask_speed():
    """Ask for and validate a speed multiplier."""
    speed = Prompt.ask(
        "[info]Enter speed (e.g. 1.5)[/info]",
        default="1.5",
    )

    try:
        value = float(speed)

        if not math.isfinite(value) or value <= 0 or value > 4:
            console.print(
                "[red]Speed must be between 0.01 and 4.0.[/red]"
            )
            return None

        return value

    except ValueError:
        console.print("[red]Invalid number.[/red]")
        return None


# ─────────────────────────────────────────────────────────────
# Join videos
# ─────────────────────────────────────────────────────────────

@click.command()
def join():
    """Join/merge videos together."""
    if not _require_ffmpeg():
        return

    console.print()
    console.print(
        Panel(
            "[bold brand]JOIN VIDEOS[/bold brand]\n"
            "[dim]Merge multiple videos into one[/dim]",
            border_style="brand",
            box=box.ROUNDED,
        )
    )

    files = _get_multiple_files(
        "\n[info]Video files (space-separated; quote paths containing spaces)[/info]"
    )

    if not files:
        return

    filename = ask_filename("joined")
    output = _prepare_output("videos", filename, ".mp4")

    if output is None:
        return

    list_file = None

    try:
        list_file = _create_concat_list(files)

        success = _run_ffmpeg_with_progress(
            [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(list_file),
                "-c", "copy",
                str(output),
            ],
            "Joining videos...",
        )

        if success and _output_ready(output):
            _show_saved_file(output, "Joined video")
        else:
            _remove_partial(output)
            console.print(
                "[red]Failed to join videos. "
                "Check that the files have compatible codecs and parameters.[/red]"
            )

    except (OSError, ValueError) as exc:
        console.print(f"[red]Could not create the video list: {exc}[/red]")

    finally:
        if list_file is not None:
            _remove_partial(list_file)


# ─────────────────────────────────────────────────────────────
# Extract audio
# ─────────────────────────────────────────────────────────────

@click.command()
def music():
    """Extract audio from video."""
    if not _require_ffmpeg():
        return

    console.print()
    console.print(
        Panel(
            "[bold brand]EXTRACT AUDIO[/bold brand]\n"
            "[dim]Extract audio track from any video file[/dim]",
            border_style="brand",
            box=box.ROUNDED,
        )
    )

    video = _valid_file(
        Prompt.ask("\n[info]Video file path[/info]"),
        "Video file",
    )

    if video is None:
        return

    console.print("\n[bold]Audio format:[/bold]")
    console.print("  [accent]1[/accent]. MP3  (universal)")
    console.print("  [accent]2[/accent]. WAV  (lossless)")
    console.print("  [accent]3[/accent]. FLAC (lossless compressed)")
    console.print("  [accent]4[/accent]. AAC  (Apple/default)")
    console.print("  [accent]5[/accent]. OGG  (open source)")

    fmt = Prompt.ask(
        "[info]Choose format[/info]",
        choices=["1", "2", "3", "4", "5"],
        default="1",
    )

    fmt_map = {
        "1": (".mp3", ["-vn", "-acodec", "libmp3lame", "-q:a", "2"]),
        "2": (".wav", ["-vn", "-acodec", "pcm_s16le"]),
        "3": (".flac", ["-vn", "-acodec", "flac"]),
        "4": (".m4a", ["-vn", "-acodec", "aac", "-b:a", "192k"]),
        "5": (".ogg", ["-vn", "-acodec", "libvorbis", "-q:a", "5"]),
    }

    ext, args = fmt_map[fmt]
    filename = ask_filename(video.stem)
    output = _prepare_output("music", filename, ext)

    if output is None:
        return

    console.print(
        f"\n[info]Extracting audio from:[/info] [white]{video}[/white]"
    )

    success = _run_ffmpeg_with_progress(
        ["ffmpeg", "-y", "-i", str(video)] + args + [str(output)],
        f"Extracting {ext[1:].upper()} audio...",
    )

    if success and _output_ready(output):
        _show_saved_file(output, "Audio")
    else:
        _remove_partial(output)
        console.print("[red]Failed to extract audio.[/red]")


# ─────────────────────────────────────────────────────────────
# Compress video
# ─────────────────────────────────────────────────────────────

@click.command()
def shrink():
    """Compress/reduce video file size."""
    if not _require_ffmpeg():
        return

    console.print()
    console.print(
        Panel(
            "[bold brand]COMPRESS VIDEO[/bold brand]\n"
            "[dim]Reduce video file size while keeping quality[/dim]",
            border_style="brand",
            box=box.ROUNDED,
        )
    )

    video = _valid_file(
        Prompt.ask("\n[info]Video file path[/info]"),
        "Video file",
    )

    if video is None:
        return

    console.print("\n[bold]Quality preset:[/bold]")
    console.print("  [accent]1[/accent]. Low      (360p, smallest file)")
    console.print("  [accent]2[/accent]. Medium   (720p, good quality)")
    console.print("  [accent]3[/accent]. High     (1080p, best quality)")
    console.print("  [accent]4[/accent]. WhatsApp  (640px, optimized for sharing)")

    quality = Prompt.ask(
        "[info]Choose quality[/info]",
        choices=["1", "2", "3", "4"],
        default="2",
    )

    scales = {
        "1": "640:-2",
        "2": "1280:-2",
        "3": "1920:-2",
        "4": "640:-2",
    }

    crfs = {
        "1": "32",
        "2": "28",
        "3": "23",
        "4": "30",
    }

    labels = {
        "1": "Low",
        "2": "Medium",
        "3": "High",
        "4": "WhatsApp",
    }

    filename = ask_filename(f"{video.stem}_compressed")
    output = _prepare_output("videos", filename, ".mp4")

    if output is None:
        return

    console.print(
        f"\n[info]Compressing to {labels[quality]} quality...[/info]"
    )

    success = _run_ffmpeg_with_progress(
        [
            "ffmpeg", "-y",
            "-i", str(video),
            "-vf",
            f"scale={scales[quality]}:force_original_aspect_ratio=decrease",
            "-c:v", "libx264",
            "-crf", crfs[quality],
            "-preset", "fast",
            "-c:a", "aac",
            "-b:a", "128k",
            str(output),
        ],
        f"Compressing ({labels[quality]})...",
    )

    if not success or not _output_ready(output):
        _remove_partial(output)
        console.print("[red]Compression failed.[/red]")
        return

    try:
        orig_size = video.stat().st_size / (1024 * 1024)
        new_size = output.stat().st_size / (1024 * 1024)

        reduction = (
            (1 - new_size / orig_size) * 100
            if orig_size > 0 else 0
        )

        table = Table(
            box=box.ROUNDED,
            border_style="success",
            show_header=False,
            padding=(0, 2),
        )

        table.add_column(style="dim", ratio=1)
        table.add_column(style="white", ratio=2)

        table.add_row("Original", f"{orig_size:.1f} MB")
        table.add_row("Compressed", f"{new_size:.1f} MB")
        table.add_row(
            "Reduction",
            f"[success]{reduction:.0f}%[/success]",
        )

        console.print(table)
        confirm_save(output)

    except OSError as exc:
        console.print(f"[red]Could not compare file sizes: {exc}[/red]")


# ─────────────────────────────────────────────────────────────
# Cut video clip
# ─────────────────────────────────────────────────────────────

@click.command()
def clip():
    """Cut a video clip."""
    if not _require_ffmpeg():
        return

    console.print()
    console.print(
        Panel(
            "[bold brand]CUT VIDEO CLIP[/bold brand]\n"
            "[dim]Extract a portion of a video[/dim]",
            border_style="brand",
            box=box.ROUNDED,
        )
    )

    video = _valid_file(
        Prompt.ask("\n[info]Video file path[/info]"),
        "Video file",
    )

    if video is None:
        return

    start = Prompt.ask(
        "[info]Start time (HH:MM:SS or MM:SS)[/info]",
        default="00:00:00",
    )

    end = Prompt.ask(
        "[info]End time (HH:MM:SS or MM:SS)[/info]",
        default="00:00:30",
    )

    if not _validate_time_range(start, end):
        return

    filename = ask_filename(f"clip_{video.stem}")
    output = _prepare_output("videos", filename, ".mp4")

    if output is None:
        return

    # Calculate exact clip duration from start and end.
    duration = _parse_time(end) - _parse_time(start)

    console.print(f"\n[info]Cutting from {start} to {end}...[/info]")

    success = _run_ffmpeg_with_progress(
        [
            "ffmpeg", "-y",
            "-ss", start,
            "-i", str(video),
            "-t", str(duration),
            "-c", "copy",
            str(output),
        ],
        "Cutting clip...",
    )

    if success and _output_ready(output):
        console.print(f"[dim]Duration: {start} to {end}[/dim]")
        _show_saved_file(output, "Video clip")
    else:
        _remove_partial(output)
        console.print("[red]Failed to cut clip.[/red]")


# ─────────────────────────────────────────────────────────────
# Video to GIF
# ─────────────────────────────────────────────────────────────

@click.command()
def gif():
    """Convert video to GIF with palette optimization."""
    if not _require_ffmpeg():
        return

    console.print()
    console.print(
        Panel(
            "[bold brand]VIDEO TO GIF[/bold brand]\n"
            "[dim]Create an optimized GIF from any video[/dim]",
            border_style="brand",
            box=box.ROUNDED,
        )
    )

    video = _valid_file(
        Prompt.ask("\n[info]Video file path[/info]"),
        "Video file",
    )

    if video is None:
        return

    width_text = Prompt.ask(
        "[info]Width in pixels[/info]",
        default="480",
    )

    fps_text = Prompt.ask(
        "[info]Frames per second[/info]",
        default="12",
    )

    try:
        width = int(width_text)
        fps = int(fps_text)

        if width < 1 or width > 7680:
            raise ValueError("Width must be between 1 and 7680.")

        if fps < 1 or fps > 120:
            raise ValueError("FPS must be between 1 and 120.")

    except ValueError as exc:
        console.print(f"[red]Invalid GIF settings: {exc}[/red]")
        return

    filename = ask_filename(video.stem)
    output = _prepare_output("images", filename, ".gif")

    if output is None:
        return

    palette_file = None

    try:
        with tempfile.NamedTemporaryFile(
            suffix=".png",
            delete=False,
        ) as temp:
            palette_file = Path(temp.name)

        palette_filter = (
            f"fps={fps},"
            f"scale={width}:-1:flags=lanczos,"
            "palettegen"
        )

        palette_success = _run_ffmpeg_with_progress(
            [
                "ffmpeg", "-y",
                "-i", str(video),
                "-vf", palette_filter,
                str(palette_file),
            ],
            "Generating palette...",
        )

        if not palette_success or not _output_ready(palette_file):
            console.print("[red]Could not generate GIF palette.[/red]")
            return

        gif_filter = (
            f"fps={fps},"
            f"scale={width}:-1:flags=lanczos"
            "[x];[x][1:v]paletteuse"
        )

        success = _run_ffmpeg_with_progress(
            [
                "ffmpeg", "-y",
                "-i", str(video),
                "-i", str(palette_file),
                "-lavfi", gif_filter,
                "-loop", "0",
                str(output),
            ],
            "Creating GIF...",
        )

        if success and _output_ready(output):
            _show_saved_file(output, "GIF")
        else:
            _remove_partial(output)
            console.print("[red]GIF creation failed.[/red]")

    except OSError as exc:
        console.print(f"[red]GIF creation error: {exc}[/red]")

    finally:
        if palette_file is not None:
            _remove_partial(palette_file)


# ─────────────────────────────────────────────────────────────
# Extract frames
# ─────────────────────────────────────────────────────────────

@click.command()
def extract():
    """Extract all frames from a video."""
    if not _require_ffmpeg():
        return

    console.print()
    console.print(
        Panel(
            "[bold brand]EXTRACT FRAMES[/bold brand]\n"
            "[dim]Extract every frame from a video as images[/dim]",
            border_style="brand",
            box=box.ROUNDED,
        )
    )

    video = _valid_file(
        Prompt.ask("\n[info]Video file path[/info]"),
        "Video file",
    )

    if video is None:
        return

    filename = ask_filename(f"{video.stem}_frames")

    # Empty extension creates a folder name without a trailing dot.
    output_dir = _prepare_output("images", filename, "")

    if output_dir is None:
        return

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        console.print(
            f"[red]Could not create output folder: {exc}[/red]"
        )
        return

    success = _run_ffmpeg_with_progress(
        [
            "ffmpeg", "-y",
            "-i", str(video),
            str(output_dir / "frame_%04d.png"),
        ],
        "Extracting frames...",
    )

    frames = list(output_dir.glob("frame_*.png"))

    if success and frames:
        console.print(
            f"[success]Extracted {len(frames)} frames[/success]"
        )

        console.print(
            Panel(
                f"[dim]{output_dir}[/dim]",
                title="[success]FRAMES[/success]",
                border_style="success",
                box=box.ROUNDED,
            )
        )
    else:
        console.print("[red]Frame extraction failed.[/red]")


# ─────────────────────────────────────────────────────────────
# Compress images
# ─────────────────────────────────────────────────────────────

@click.command()
@click.argument("folder", required=False, default=".")
def compress(folder):
    """Compress images in a folder."""
    if not ensure_pip_module(
        "PIL",
        pip_name="Pillow",
        display_name="Pillow",
    ):
        return

    from PIL import Image, ImageOps

    target = Path(folder).expanduser()

    console.print()
    console.print(
        Panel(
            "[bold brand]COMPRESS IMAGES[/bold brand]\n"
            "[dim]Optimize images to reduce file size[/dim]",
            border_style="brand",
            box=box.ROUNDED,
        )
    )

    if not target.exists() or not target.is_dir():
        console.print(f"[red]Directory not found: {folder}[/red]")
        return

    ignored_dirs = {
        "node_modules",
        ".git",
        ".dt",
        "__pycache__",
        ".venv",
        "venv",
    }

    image_extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".bmp",
    }

    image_files = []

    try:
        for img_path in target.rglob("*"):
            if not img_path.is_file():
                continue

            if img_path.suffix.lower() not in image_extensions:
                continue

            try:
                relative_parts = img_path.relative_to(target).parts
            except ValueError:
                continue

            if any(part in ignored_dirs for part in relative_parts):
                continue

            image_files.append(img_path)

    except OSError as exc:
        console.print(f"[red]Could not scan directory: {exc}[/red]")
        return

    if not image_files:
        console.print("[yellow]No images found to compress.[/yellow]")
        return

    console.print(
        f"\n[info]Found {len(image_files)} image(s) to compress...[/info]\n"
    )

    total_saved = 0
    successful = 0
    failed = 0

    with Progress(
        SpinnerColumn("dots"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=bar_width()),
        console=console,
    ) as progress:

        task = progress.add_task(
            "[info]Compressing images...[/info]",
            total=len(image_files),
        )

        for img_path in image_files:
            temp_path = None

            try:
                original_size = img_path.stat().st_size

                with Image.open(img_path) as source:
                    image_format = source.format

                    if not image_format:
                        raise ValueError("Unknown image format.")

                    source.load()
                    image = ImageOps.exif_transpose(source)

                    if image_format.upper() in ("JPEG", "JPG"):
                        if image.mode not in ("RGB", "L"):
                            image = image.convert("RGB")

                    with tempfile.NamedTemporaryFile(
                        suffix=img_path.suffix,
                        prefix=".compress_",
                        dir=str(img_path.parent),
                        delete=False,
                    ) as temp:
                        temp_path = Path(temp.name)

                    save_options = {}

                    if image_format.upper() in ("JPEG", "JPG"):
                        save_options = {
                            "quality": 85,
                            "optimize": True,
                        }

                    elif image_format.upper() == "PNG":
                        save_options = {
                            "optimize": True,
                        }

                    elif image_format.upper() == "WEBP":
                        save_options = {
                            "quality": 85,
                            "method": 4,
                        }

                    image.save(
                        str(temp_path),
                        format=image_format,
                        **save_options,
                    )

                new_size = temp_path.stat().st_size

                if new_size < original_size:
                    os.replace(str(temp_path), str(img_path))
                    total_saved += original_size - new_size
                    successful += 1
                else:
                    _remove_partial(temp_path)
                    successful += 1

            except Exception:
                failed += 1

                if temp_path is not None:
                    _remove_partial(temp_path)

            finally:
                progress.advance(task)

    console.print(
        f"\n[success]Processed {successful} image(s) successfully.[/success]"
    )

    if failed:
        console.print(f"[yellow]Failed: {failed} image(s)[/yellow]")

    console.print(
        f"[dim]Total space saved: {total_saved / 1024:.1f} KB[/dim]"
    )


# ─────────────────────────────────────────────────────────────
# Trim audio
# ─────────────────────────────────────────────────────────────

@click.command()
def trim_audio():
    """Trim/cut an audio file."""
    if not _require_ffmpeg():
        return

    console.print()
    console.print(
        Panel(
            "[bold brand]TRIM AUDIO[/bold brand]\n"
            "[dim]Cut a portion of an audio file[/dim]",
            border_style="brand",
            box=box.ROUNDED,
        )
    )

    audio = _valid_file(
        Prompt.ask("\n[info]Audio file path[/info]"),
        "Audio file",
    )

    if audio is None:
        return

    start = Prompt.ask(
        "[info]Start time (MM:SS or HH:MM:SS)[/info]",
        default="00:00",
    )

    end = Prompt.ask(
        "[info]End time (MM:SS or HH:MM:SS)[/info]",
        default="00:30",
    )

    if not _validate_time_range(start, end):
        return

    filename = ask_filename(f"trimmed_{audio.stem}")
    ext = audio.suffix.lower() or ".mp3"
    output = _prepare_output("music", filename, ext)

    if output is None:
        return

    duration = _parse_time(end) - _parse_time(start)

    success = _run_ffmpeg_with_progress(
        [
            "ffmpeg", "-y",
            "-ss", start,
            "-i", str(audio),
            "-t", str(duration),
            "-c", "copy",
            str(output),
        ],
        "Trimming audio...",
    )

    if success and _output_ready(output):
        console.print(f"[dim]Duration: {start} to {end}[/dim]")
        _show_saved_file(output, "Audio")
    else:
        _remove_partial(output)
        console.print("[red]Failed to trim audio.[/red]")


# ─────────────────────────────────────────────────────────────
# Merge audio
# ─────────────────────────────────────────────────────────────

@click.command()
def merge_audio():
    """Merge/join multiple audio files."""
    if not _require_ffmpeg():
        return

    console.print()
    console.print(
        Panel(
            "[bold brand]MERGE AUDIO[/bold brand]\n"
            "[dim]Combine multiple audio files into one[/dim]",
            border_style="brand",
            box=box.ROUNDED,
        )
    )

    files = _get_multiple_files(
        "\n[info]Audio files (space-separated; quote paths containing spaces)[/info]"
    )

    if not files:
        return

    filename = ask_filename("merged_audio")
    output = _prepare_output("music", filename, ".mp3")

    if output is None:
        return

    list_file = None

    try:
        list_file = _create_concat_list(files)

        success = _run_ffmpeg_with_progress(
            [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(list_file),
                "-vn",
                "-acodec", "libmp3lame",
                "-q:a", "2",
                str(output),
            ],
            "Merging audio files...",
        )

        if success and _output_ready(output):
            console.print(f"[dim]Merged {len(files)} files[/dim]")
            _show_saved_file(output, "Merged audio")
        else:
            _remove_partial(output)
            console.print(
                "[red]Failed to merge audio. "
                "Check that the files are valid audio files.[/red]"
            )

    except (OSError, ValueError) as exc:
        console.print(f"[red]Could not merge audio: {exc}[/red]")

    finally:
        if list_file is not None:
            _remove_partial(list_file)


# ─────────────────────────────────────────────────────────────
# Audio speed
# ─────────────────────────────────────────────────────────────

@click.command()
def audio_speed():
    """Change the speed of an audio file."""
    if not _require_ffmpeg():
        return

    console.print()
    console.print(
        Panel(
            "[bold brand]AUDIO SPEED CHANGE[/bold brand]\n"
            "[dim]Speed up or slow down audio[/dim]",
            border_style="brand",
            box=box.ROUNDED,
        )
    )

    audio = _valid_file(
        Prompt.ask("\n[info]Audio file path[/info]"),
        "Audio file",
    )

    if audio is None:
        return

    console.print("\n[bold]Speed multiplier:[/bold]")
    console.print("  [accent]0.5[/accent] - Half speed (slow)")
    console.print("  [accent]0.75[/accent] - 75% speed")
    console.print("  [accent]1.5[/accent] - 1.5x speed")
    console.print("  [accent]2.0[/accent] - Double speed (fast)")

    speed_val = _ask_speed()

    if speed_val is None:
        return

    filename = ask_filename(f"{audio.stem}_{speed_val}x")
    ext = audio.suffix.lower() or ".mp3"
    output = _prepare_output("music", filename, ext)

    if output is None:
        return

    atempo_filter = _build_atempo_filter(speed_val)

    success = _run_ffmpeg_with_progress(
        [
            "ffmpeg", "-y",
            "-i", str(audio),
            "-filter:a", atempo_filter,
            str(output),
        ],
        f"Changing speed to {speed_val}x...",
    )

    if success and _output_ready(output):
        console.print(f"[dim]Speed: {speed_val}x[/dim]")
        _show_saved_file(output, "Audio")
    else:
        _remove_partial(output)
        console.print("[red]Failed to change audio speed.[/red]")


# ─────────────────────────────────────────────────────────────
# Video speed
# ─────────────────────────────────────────────────────────────

@click.command()
def video_speed():
    """Change the speed of a video."""
    if not _require_ffmpeg():
        return

    console.print()
    console.print(
        Panel(
            "[bold brand]VIDEO SPEED CHANGE[/bold brand]\n"
            "[dim]Speed up or slow down a video[/dim]",
            border_style="brand",
            box=box.ROUNDED,
        )
    )

    video = _valid_file(
        Prompt.ask("\n[info]Video file path[/info]"),
        "Video file",
    )

    if video is None:
        return

    console.print("\n[bold]Speed multiplier:[/bold]")
    console.print("  [accent]0.5[/accent] - Slow motion")
    console.print("  [accent]1.5[/accent] - 1.5x faster")
    console.print("  [accent]2.0[/accent] - Double speed")

    speed_val = _ask_speed()

    if speed_val is None:
        return

    filename = ask_filename(f"{video.stem}_{speed_val}x")
    output = _prepare_output("videos", filename, ".mp4")

    if output is None:
        return

    video_filter = f"setpts={1 / speed_val:.8g}*PTS"
    audio_filter = _build_atempo_filter(speed_val)

    success = _run_ffmpeg_with_progress(
        [
            "ffmpeg", "-y",
            "-i", str(video),
            "-map", "0:v:0",
            "-map", "0:a?",
            "-filter:v", video_filter,
            "-filter:a", audio_filter,
            "-c:v", "libx264",
            "-preset", "fast",
            "-c:a", "aac",
            str(output),
        ],
        f"Changing video speed to {speed_val}x...",
    )

    if success and _output_ready(output):
        try:
            orig_size = video.stat().st_size / (1024 * 1024)
            new_size = output.stat().st_size / (1024 * 1024)

            console.print(
                f"[dim]Speed: {speed_val}x | "
                f"Size: {new_size:.1f} MB "
                f"(was {orig_size:.1f} MB)[/dim]"
            )
        except OSError:
            pass

        confirm_save(output)

    else:
        _remove_partial(output)
        console.print("[red]Failed to change video speed.[/red]")


# ─────────────────────────────────────────────────────────────
# Reverse video
# ─────────────────────────────────────────────────────────────

@click.command()
def reverse_video():
    """Reverse a video (play backwards)."""
    if not _require_ffmpeg():
        return

    console.print()
    console.print(
        Panel(
            "[bold brand]REVERSE VIDEO[/bold brand]\n"
            "[dim]Play a video in reverse[/dim]",
            border_style="brand",
            box=box.ROUNDED,
        )
    )

    video = _valid_file(
        Prompt.ask("\n[info]Video file path[/info]"),
        "Video file",
    )

    if video is None:
        return

    filename = ask_filename(f"reversed_{video.stem}")
    output = _prepare_output("videos", filename, ".mp4")

    if output is None:
        return

    success = _run_ffmpeg_with_progress(
        [
            "ffmpeg", "-y",
            "-i", str(video),
            "-map", "0:v:0",
            "-map", "0:a?",
            "-vf", "reverse",
            "-af", "areverse",
            "-c:v", "libx264",
            "-preset", "fast",
            "-c:a", "aac",
            str(output),
        ],
        "Reversing video...",
    )

    if success and _output_ready(output):
        _show_saved_file(output, "Reversed video")
    else:
        _remove_partial(output)
        console.print("[red]Failed to reverse video.[/red]")


# ─────────────────────────────────────────────────────────────
# Add audio to video
# ─────────────────────────────────────────────────────────────

@click.command()
def add_audio():
    """Add/replace audio track on a video."""
    if not _require_ffmpeg():
        return

    console.print()
    console.print(
        Panel(
            "[bold brand]ADD AUDIO TO VIDEO[/bold brand]\n"
            "[dim]Add or replace the audio track of a video[/dim]",
            border_style="brand",
            box=box.ROUNDED,
        )
    )

    video = _valid_file(
        Prompt.ask("\n[info]Video file path[/info]"),
        "Video file",
    )

    if video is None:
        return

    audio = _valid_file(
        Prompt.ask("[info]Audio file path[/info]"),
        "Audio file",
    )

    if audio is None:
        return

    filename = ask_filename(f"{video.stem}_with_audio")
    output = _prepare_output("videos", filename, ".mp4")

    if output is None:
        return

    success = _run_ffmpeg_with_progress(
        [
            "ffmpeg", "-y",
            "-i", str(video),
            "-i", str(audio),
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            str(output),
        ],
        "Adding audio to video...",
    )

    if success and _output_ready(output):
        _show_saved_file(output, "Video")
    else:
        _remove_partial(output)
        console.print("[red]Failed to add audio.[/red]")


# ─────────────────────────────────────────────────────────────
# Mute video
# ─────────────────────────────────────────────────────────────

@click.command()
def mute_video():
    """Remove audio from a video (mute)."""
    if not _require_ffmpeg():
        return

    console.print()
    console.print(
        Panel(
            "[bold brand]MUTE VIDEO[/bold brand]\n"
            "[dim]Remove the audio track from a video[/dim]",
            border_style="brand",
            box=box.ROUNDED,
        )
    )

    video = _valid_file(
        Prompt.ask("\n[info]Video file path[/info]"),
        "Video file",
    )

    if video is None:
        return

    filename = ask_filename(f"muted_{video.stem}")
    output = _prepare_output("videos", filename, ".mp4")

    if output is None:
        return

    success = _run_ffmpeg_with_progress(
        [
            "ffmpeg", "-y",
            "-i", str(video),
            "-map", "0:v:0",
            "-an",
            "-c:v", "copy",
            str(output),
        ],
        "Removing audio...",
    )

    if success and _output_ready(output):
        _show_saved_file(output, "Muted video")
    else:
        _remove_partial(output)
        console.print("[red]Failed to mute video.[/red]")


# ─────────────────────────────────────────────────────────────
# Watermark
# ─────────────────────────────────────────────────────────────

@click.command()
def watermark():
    """Add a text watermark to a video."""
    if not _require_ffmpeg():
        return

    console.print()
    console.print(
        Panel(
            "[bold brand]ADD WATERMARK[/bold brand]\n"
            "[dim]Add a text watermark to your video[/dim]",
            border_style="brand",
            box=box.ROUNDED,
        )
    )

    video = _valid_file(
        Prompt.ask("\n[info]Video file path[/info]"),
        "Video file",
    )

    if video is None:
        return

    watermark_text = Prompt.ask(
        "[info]Watermark text[/info]",
        default="DT CLI",
    ).strip()

    if not watermark_text:
        console.print("[red]Watermark text cannot be empty.[/red]")
        return

    console.print("\n[bold]Position:[/bold]")
    console.print("  [accent]1[/accent]. Top-Left")
    console.print("  [accent]2[/accent]. Top-Right")
    console.print("  [accent]3[/accent]. Bottom-Left")
    console.print("  [accent]4[/accent]. Bottom-Right")
    console.print("  [accent]5[/accent]. Center")

    pos = Prompt.ask(
        "[info]Position[/info]",
        choices=["1", "2", "3", "4", "5"],
        default="4",
    )

    positions = {
        "1": ("10", "10"),
        "2": ("w-tw-10", "10"),
        "3": ("10", "h-th-10"),
        "4": ("w-tw-10", "h-th-10"),
        "5": ("(w-tw)/2", "(h-th)/2"),
    }

    filename = ask_filename(f"watermarked_{video.stem}")
    output = _prepare_output("videos", filename, ".mp4")

    if output is None:
        return

    font_paths = [
        "/system/fonts/DroidSans.ttf",
        "/system/fonts/Roboto-Regular.ttf",
        "/system/fonts/NotoSans-Regular.ttf",
        "/system/fonts/NotoSansCJK-Regular.ttc",
    ]

    font_file = None

    for font_path in font_paths:
        if Path(font_path).is_file():
            font_file = font_path
            break

    pos_x, pos_y = positions[pos]
    safe_text = _escape_drawtext(watermark_text)

    filter_parts = []

    if font_file:
        safe_font = _escape_drawtext(font_file)
        filter_parts.append(f"fontfile='{safe_font}'")

    filter_parts.extend([
        f"text='{safe_text}'",
        "fontsize=24",
        "fontcolor=white@0.7",
        "borderw=1",
        "bordercolor=black@0.5",
        f"x={pos_x}",
        f"y={pos_y}",
    ])

    filter_str = "drawtext=" + ":".join(filter_parts)

    success = _run_ffmpeg_with_progress(
        [
            "ffmpeg", "-y",
            "-i", str(video),
            "-vf", filter_str,
            "-c:v", "libx264",
            "-preset", "fast",
            "-c:a", "copy",
            str(output),
        ],
        "Adding watermark...",
    )

    if success and _output_ready(output):
        console.print(f"[dim]Watermark: '{watermark_text}'[/dim]")
        _show_saved_file(output, "Watermarked video")
    else:
        _remove_partial(output)
        console.print("[red]Failed to add watermark.[/red]")


# ─────────────────────────────────────────────────────────────
# Video thumbnail
# ─────────────────────────────────────────────────────────────

@click.command()
def thumbnail():
    """Extract a thumbnail/poster from a video."""
    if not _require_ffmpeg():
        return

    console.print()
    console.print(
        Panel(
            "[bold brand]VIDEO THUMBNAIL[/bold brand]\n"
            "[dim]Extract a high-quality thumbnail from any video[/dim]",
            border_style="brand",
            box=box.ROUNDED,
        )
    )

    video = _valid_file(
        Prompt.ask("\n[info]Video file path[/info]"),
        "Video file",
    )

    if video is None:
        return

    timestamp = Prompt.ask(
        "[info]Timestamp (HH:MM:SS)[/info]",
        default="00:00:05",
    )

    try:
        _parse_time(timestamp)
    except ValueError as exc:
        console.print(f"[red]Invalid timestamp: {exc}[/red]")
        return

    filename = ask_filename(f"thumb_{video.stem}")
    output = _prepare_output("images", filename, ".jpg")

    if output is None:
        return

    success = _run_ffmpeg_with_progress(
        [
            "ffmpeg", "-y",
            "-ss", timestamp,
            "-i", str(video),
            "-frames:v", "1",
            "-q:v", "2",
            str(output),
        ],
        "Extracting thumbnail...",
    )

    if success and _output_ready(output):
        try:
            size = output.stat().st_size / 1024
            console.print(f"[dim]Size: {size:.2f} KB[/dim]")
            confirm_save(output)
        except OSError as exc:
            console.print(f"[red]Could not read thumbnail: {exc}[/red]")
    else:
        _remove_partial(output)
        console.print("[red]Failed to extract thumbnail.[/red]")


# ─────────────────────────────────────────────────────────────
# Audio information
# ─────────────────────────────────────────────────────────────

@click.command()
def audio_info():
    """Get detailed info about an audio file."""
    if not _require_ffmpeg():
        return

    if not ensure_cli_tool("ffprobe", display_name="ffprobe"):
        return

    console.print()

    audio = _valid_file(
        Prompt.ask("[info]Audio file path[/info]"),
        "Audio file",
    )

    if audio is None:
        return

    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                str(audio),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            console.print("[red]FFprobe could not read this file.[/red]")

            if result.stderr:
                console.print(
                    f"[dim]{result.stderr.strip()[-500:]}[/dim]"
                )

            return

        import json
        data = json.loads(result.stdout)

        audio_stream = None

        for stream in data.get("streams", []):
            if stream.get("codec_type") == "audio":
                audio_stream = stream
                break

        if audio_stream is None:
            console.print(
                "[yellow]No audio stream found in this file.[/yellow]"
            )
            return

        table = Table(
            box=box.ROUNDED,
            border_style="accent",
            show_header=False,
            padding=(0, 2),
        )

        table.add_column(style="dim", ratio=1)
        table.add_column(style="white", ratio=2)

        fmt = data.get("format", {})

        try:
            file_size = int(fmt.get("size", audio.stat().st_size))
        except (TypeError, ValueError, OSError):
            file_size = audio.stat().st_size

        try:
            duration = float(fmt.get("duration", 0))
        except (TypeError, ValueError):
            duration = 0

        table.add_row("File", audio.name)
        table.add_row("Size", f"{file_size / (1024 * 1024):.2f} MB")
        table.add_row("Duration", f"{duration:.1f} seconds")
        table.add_row("Codec", audio_stream.get("codec_name", "N/A"))

        try:
            sample_rate = int(audio_stream.get("sample_rate", 0))
            table.add_row("Sample Rate", f"{sample_rate} Hz")
        except (TypeError, ValueError):
            table.add_row("Sample Rate", "N/A")

        table.add_row(
            "Channels",
            str(audio_stream.get("channels", "N/A")),
        )

        try:
            bitrate = int(audio_stream.get("bit_rate", 0)) // 1000
            table.add_row("Bit Rate", f"{bitrate} kbps")
        except (TypeError, ValueError):
            table.add_row("Bit Rate", "N/A")

        console.print(table)

    except subprocess.TimeoutExpired:
        console.print("[red]FFprobe timed out.[/red]")

    except (OSError, ValueError, KeyError) as exc:
        console.print(f"[red]Could not read audio info: {exc}[/red]")


# ─────────────────────────────────────────────────────────────
# Video information
# ─────────────────────────────────────────────────────────────

@click.command()
def video_info():
    """Get detailed info about a video file."""
    if not _require_ffmpeg():
        return

    if not ensure_cli_tool("ffprobe", display_name="ffprobe"):
        return

    console.print()

    video = _valid_file(
        Prompt.ask("[info]Video file path[/info]"),
        "Video file",
    )

    if video is None:
        return

    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                str(video),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            console.print("[red]FFprobe could not read this file.[/red]")

            if result.stderr:
                console.print(
                    f"[dim]{result.stderr.strip()[-500:]}[/dim]"
                )

            return

        import json
        data = json.loads(result.stdout)

        video_stream = None
        audio_stream = None

        for stream in data.get("streams", []):
            if (
                stream.get("codec_type") == "video"
                and video_stream is None
            ):
                video_stream = stream

            elif (
                stream.get("codec_type") == "audio"
                and audio_stream is None
            ):
                audio_stream = stream

        if video_stream is None:
            console.print(
                "[yellow]No video stream found in this file.[/yellow]"
            )
            return

        table = Table(
            box=box.ROUNDED,
            border_style="accent",
            show_header=False,
            padding=(0, 2),
        )

        table.add_column(style="dim", ratio=1)
        table.add_column(style="white", ratio=2)

        fmt = data.get("format", {})

        try:
            file_size = int(fmt.get("size", video.stat().st_size))
        except (TypeError, ValueError, OSError):
            file_size = video.stat().st_size

        try:
            duration = float(fmt.get("duration", 0))
        except (TypeError, ValueError):
            duration = 0

        table.add_row("File", video.name)
        table.add_row("Size", f"{file_size / (1024 * 1024):.2f} MB")
        table.add_row("Duration", f"{duration:.1f} seconds")

        width = video_stream.get("width", "?")
        height = video_stream.get("height", "?")

        table.add_row("Resolution", f"{width}x{height}")
        table.add_row(
            "Video Codec",
            video_stream.get("codec_name", "N/A"),
        )

        fps = (
            video_stream.get("avg_frame_rate")
            or video_stream.get("r_frame_rate", "0/1")
        )

        try:
            numerator, denominator = fps.split("/", 1)
            denominator = float(denominator)

            if denominator == 0:
                raise ValueError("Invalid FPS denominator.")

            fps_value = float(numerator) / denominator
            table.add_row("FPS", f"{fps_value:.2f}")

        except (ValueError, TypeError, ZeroDivisionError):
            table.add_row("FPS", str(fps))

        if audio_stream:
            table.add_row(
                "Audio Codec",
                audio_stream.get("codec_name", "N/A"),
            )

            try:
                sample_rate = int(audio_stream.get("sample_rate", 0))
                table.add_row("Sample Rate", f"{sample_rate} Hz")
            except (TypeError, ValueError):
                table.add_row("Sample Rate", "N/A")

        else:
            table.add_row("Audio", "No audio stream")

        console.print(table)

    except subprocess.TimeoutExpired:
        console.print("[red]FFprobe timed out.[/red]")

    except (OSError, ValueError, KeyError) as exc:
        console.print(f"[red]Could not read video info: {exc}[/red]")