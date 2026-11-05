import click
import subprocess
import os
import shlex
import re
from pathlib import Path

from ..config import (
    console, get_save_path, ask_filename, confirm_save,
    ensure_cli_tool, ensure_pip_module, bar_width
)

from rich.prompt import Prompt
from rich.table import Table
from rich.panel import Panel
from rich.progress import (
    Progress, SpinnerColumn, BarColumn,
    TextColumn, TimeElapsedColumn
)
from rich import box


def _ffmpeg_convert(input_path, output_path, extra_args=None):
    """Run ffmpeg conversion with error handling."""

    input_path = Path(input_path)
    output_path = Path(output_path)

    if not input_path.is_file():
        console.print(f"[red]Input file not found: {input_path}[/red]")
        return False

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            'ffmpeg',
            '-y',
            '-i', str(input_path)
        ]

        if extra_args:
            cmd.extend(extra_args)

        cmd.append(str(output_path))

        console.print(
            f"[dim]Running: {subprocess.list2cmdline(cmd)}[/dim]\n"
        )

        with Progress(
            SpinnerColumn("dots"),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=bar_width()),
            TimeElapsedColumn(),
            console=console,
        ) as progress:

            task = progress.add_task(
                "[info]Converting...[/info]",
                total=None
            )

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                errors="replace",
                check=False
            )

            progress.update(task, completed=1)

        if result.returncode != 0:
            error = result.stderr or "Unknown FFmpeg error"

            console.print(
                f"[red]FFmpeg Error: {error[-1000:]}[/red]"
            )

            if output_path.exists():
                output_path.unlink()

            return False

        if not output_path.is_file() or output_path.stat().st_size == 0:
            console.print(
                "[red]Conversion failed: Output file is missing or empty.[/red]"
            )

            if output_path.exists():
                output_path.unlink()

            return False

        return True

    except FileNotFoundError:
        console.print("[red]FFmpeg executable was not found.[/red]")
        return False

    except subprocess.SubprocessError as e:
        console.print(f"[red]FFmpeg execution failed: {e}[/red]")
        return False

    except OSError as e:
        console.print(f"[red]File operation failed: {e}[/red]")
        return False


# ── FORMAT MAPS ────────────────────────────────────────────────────

AUDIO_FORMATS = {
    "1": ("MP3", ".mp3", ["-vn", "-acodec", "libmp3lame", "-q:a", "2"]),
    "2": ("WAV", ".wav", ["-vn", "-acodec", "pcm_s16le"]),
    "3": ("AAC", ".aac", ["-vn", "-acodec", "aac", "-b:a", "192k"]),
    "4": ("OGG", ".ogg", ["-vn", "-acodec", "libvorbis", "-q:a", "5"]),
    "5": ("FLAC", ".flac", ["-vn", "-acodec", "flac"]),
    "6": ("WMA", ".wma", ["-vn", "-acodec", "wmav2", "-b:a", "192k"]),
    "7": ("M4A", ".m4a", ["-vn", "-acodec", "aac", "-b:a", "192k"]),
}

VIDEO_FORMATS = {
    "1": ("MP4", ".mp4", ["-c:v", "libx264", "-preset", "medium", "-crf", "23", "-c:a", "aac"]),
    "2": ("MKV", ".mkv", ["-c:v", "libx264", "-preset", "medium", "-crf", "23", "-c:a", "aac"]),
    "3": ("AVI", ".avi", ["-c:v", "libx264", "-c:a", "mp3"]),
    "4": ("MOV", ".mov", ["-c:v", "libx264", "-c:a", "aac", "-f", "mov"]),
    "5": ("WEBM", ".webm", ["-c:v", "libvpx-vp9", "-crf", "30", "-b:v", "0", "-c:a", "libopus"]),
    "6": ("GIF", ".gif", ["-vf", "fps=15,scale=480:-1:flags=lanczos"]),
    "7": ("TS", ".ts", ["-c:v", "libx264", "-c:a", "aac", "-f", "mpegts"]),
    "8": ("FLV", ".flv", ["-c:v", "libx264", "-c:a", "aac", "-f", "flv"]),
    "9": ("3GP", ".3gp", ["-c:v", "libx264", "-s", "352x288", "-c:a", "aac", "-b:a", "128k"]),
}

IMAGE_FORMATS = {
    "1": ("JPEG", ".jpg", "JPEG"),
    "2": ("PNG", ".png", "PNG"),
    "3": ("WEBP", ".webp", "WEBP"),
    "4": ("BMP", ".bmp", "BMP"),
    "5": ("ICO", ".ico", "ICO"),
    "6": ("TIFF", ".tiff", "TIFF"),
    "7": ("GIF", ".gif", "GIF"),
}

SVG_IMAGE_FORMATS = {
    "1": ("PNG", ".png", "PNG"),
    "2": ("JPEG", ".jpg", "JPEG"),
    "3": ("WEBP", ".webp", "WEBP"),
    "4": ("PDF", ".pdf", "PDF"),
    "5": ("SVG Optimized", ".svg", None),
}

DOCUMENT_FORMATS = {
    "1": ("PDF to DOCX", "pdf_to_docx"),
    "2": ("DOCX to PDF", "docx_to_pdf"),
    "3": ("PDF to Images", "pdf_to_images"),
    "4": ("Images to PDF", "images_to_pdf"),
    "5": ("TXT to PDF", "txt_to_pdf"),
    "6": ("HTML to PDF", "html_to_pdf"),
}


def _validate_input(input_path):
    """Validate an input file path."""

    p = Path(input_path).expanduser()

    if not p.exists():
        console.print(f"[red]File not found: {p}[/red]")
        return None

    if not p.is_file():
        console.print(f"[red]Path is not a file: {p}[/red]")
        return None

    if not os.access(p, os.R_OK):
        console.print(f"[red]File is not readable: {p}[/red]")
        return None

    return p


def _check_output(output):
    """Check whether an output file was created successfully."""

    output = Path(output)

    if not output.is_file():
        console.print("[red]Output file was not created.[/red]")
        return False

    if output.stat().st_size == 0:
        console.print("[red]Output file is empty.[/red]")
        return False

    return True


def _remove_partial_output(output):
    """Remove incomplete output files."""

    try:
        output = Path(output)

        if output.exists() and output.is_file():
            output.unlink()

    except OSError:
        pass


@click.command()
def convert():
    """Convert files between any format (Audio, Video, Image, SVG, Documents)."""

    console.print()

    console.print(
        Panel(
            "[bold brand]DT CONVERT[/bold brand]\n"
            "[dim]Universal file converter - convert anything to anything[/dim]",
            border_style="brand",
            box=box.DOUBLE_EDGE
        )
    )

    console.print()

    table = Table(
        box=box.ROUNDED,
        border_style="accent",
        show_header=False,
        padding=(0, 2)
    )

    table.add_column(style="dim", ratio=1)
    table.add_column(style="white bold", ratio=3)

    table.add_row("[1]", "Audio  (MP3, WAV, AAC, OGG, FLAC, WMA, M4A)")
    table.add_row("[2]", "Documents  (PDF, DOCX, TXT, HTML, Images)")
    table.add_row("[3]", "Video  (MP4, MKV, AVI, MOV, WEBM, GIF, TS, FLV, 3GP)")
    table.add_row("[4]", "Image  (JPEG, PNG, WEBP, BMP, ICO, TIFF, GIF)")
    table.add_row("[5]", "SVG  (to PNG, JPEG, WEBP, PDF, or optimize)")

    console.print(table)

    choice = Prompt.ask(
        "\n[info]Which type of files are you working with?[/info]",
        choices=["1", "2", "3", "4", "5"]
    )

    if choice == "1":
        _convert_audio()

    elif choice == "2":
        _convert_document()

    elif choice == "3":
        _convert_video()

    elif choice == "4":
        _convert_image()

    elif choice == "5":
        _convert_svg()


def _convert_audio():
    """Audio conversion flow."""

    if not ensure_cli_tool('ffmpeg', display_name='ffmpeg'):
        return

    input_path = Prompt.ask("[info]Enter audio file path[/info]")
    p = _validate_input(input_path)

    if p is None:
        return

    console.print("\n[bold]Output format:[/bold]")

    for k, (name, ext, _) in AUDIO_FORMATS.items():
        console.print(f"  [accent]{k}[/accent]. {name} {ext}")

    fmt_choice = Prompt.ask(
        "[info]Choose format[/info]",
        choices=list(AUDIO_FORMATS.keys())
    )

    name, ext, args = AUDIO_FORMATS[fmt_choice]

    filename = ask_filename(p.stem)

    if not filename:
        console.print("[red]Invalid filename.[/red]")
        return

    output = get_save_path('music') / f"{filename}{ext}"

    if _ffmpeg_convert(p, output, args):

        size = output.stat().st_size / 1024 / 1024

        console.print(f"[dim]Size: {size:.2f} MB[/dim]")

        confirm_save(output)


def _convert_video():
    """Video conversion flow."""

    if not ensure_cli_tool('ffmpeg', display_name='ffmpeg'):
        return

    input_path = Prompt.ask("[info]Enter video file path[/info]")
    p = _validate_input(input_path)

    if p is None:
        return

    console.print("\n[bold]Output format:[/bold]")

    for k, (name, ext, _) in VIDEO_FORMATS.items():
        console.print(f"  [accent]{k}[/accent]. {name} {ext}")

    fmt_choice = Prompt.ask(
        "[info]Choose format[/info]",
        choices=list(VIDEO_FORMATS.keys())
    )

    name, ext, args = VIDEO_FORMATS[fmt_choice]

    filename = ask_filename(p.stem)

    if not filename:
        console.print("[red]Invalid filename.[/red]")
        return

    output = get_save_path('videos') / f"{filename}{ext}"

    if _ffmpeg_convert(p, output, args):

        size = output.stat().st_size / 1024 / 1024
        orig_size = p.stat().st_size / 1024 / 1024

        console.print(
            f"[dim]Original: {orig_size:.2f} MB -> New: {size:.2f} MB[/dim]"
        )

        confirm_save(output)


def _convert_image():
    """Image conversion using Pillow."""

    if not ensure_pip_module(
        'PIL',
        pip_name='Pillow',
        display_name='Pillow'
    ):
        return

    input_path = Prompt.ask("[info]Enter image file path[/info]")
    p = _validate_input(input_path)

    if p is None:
        return

    console.print("\n[bold]Output format:[/bold]")

    for k, (name, ext, _) in IMAGE_FORMATS.items():
        console.print(f"  [accent]{k}[/accent]. {name} {ext}")

    fmt_choice = Prompt.ask(
        "[info]Choose format[/info]",
        choices=list(IMAGE_FORMATS.keys())
    )

    name, ext, pil_fmt = IMAGE_FORMATS[fmt_choice]

    filename = ask_filename(p.stem)

    if not filename:
        console.print("[red]Invalid filename.[/red]")
        return

    output = get_save_path('images') / f"{filename}{ext}"

    try:
        from PIL import Image

        with Progress(
            SpinnerColumn("dots"),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:

            progress.add_task(
                "[info]Converting image...[/info]",
                total=None
            )

            with Image.open(p) as source:

                img = source.copy()

                if pil_fmt == "JPEG":

                    if img.mode not in ("RGB", "L"):
                        if "A" in img.getbands() or img.mode == "P":
                            rgba = img.convert("RGBA")

                            background = Image.new(
                                "RGB",
                                rgba.size,
                                (255, 255, 255)
                            )

                            background.paste(
                                rgba,
                                mask=rgba.getchannel("A")
                            )

                            img = background

                        else:
                            img = img.convert("RGB")

                elif pil_fmt == "ICO":

                    img = img.convert("RGBA")
                    img.thumbnail((256, 256))

                elif pil_fmt == "GIF":

                    img = img.convert("RGBA")

                elif pil_fmt == "WEBP":

                    if img.mode not in ("RGB", "RGBA"):
                        img = img.convert("RGBA")

                elif pil_fmt == "BMP":

                    if img.mode not in ("RGB", "L"):
                        img = img.convert("RGB")

                save_options = {}

                if pil_fmt == "JPEG":
                    save_options["quality"] = 90
                    save_options["optimize"] = True

                elif pil_fmt == "PNG":
                    save_options["optimize"] = True

                elif pil_fmt == "WEBP":
                    save_options["quality"] = 90
                    save_options["method"] = 6

                elif pil_fmt == "GIF":
                    save_options["optimize"] = True

                img.save(
                    output,
                    format=pil_fmt,
                    **save_options
                )

                img.close()

        if not _check_output(output):
            _remove_partial_output(output)
            return

        size = output.stat().st_size / 1024

        console.print(f"[dim]Size: {size:.2f} KB[/dim]")

        confirm_save(output)

    except Exception as e:

        _remove_partial_output(output)

        console.print(f"[red]Conversion failed: {e}[/red]")


def _convert_svg():
    """SVG conversion."""

    input_path = Prompt.ask("[info]Enter SVG file path[/info]")
    p = _validate_input(input_path)

    if p is None:
        return

    if p.suffix.lower() != ".svg":
        console.print("[red]Input file must be an SVG file.[/red]")
        return

    console.print("\n[bold]Convert to:[/bold]")

    for k, (name, ext, _) in SVG_IMAGE_FORMATS.items():
        console.print(f"  [accent]{k}[/accent]. {name} {ext}")

    fmt_choice = Prompt.ask(
        "[info]Choose format[/info]",
        choices=list(SVG_IMAGE_FORMATS.keys())
    )

    name, ext, pil_fmt = SVG_IMAGE_FORMATS[fmt_choice]

    filename = ask_filename(p.stem)

    if not filename:
        console.print("[red]Invalid filename.[/red]")
        return

    output = get_save_path('images') / f"{filename}{ext}"

    try:

        content = p.read_text(encoding="utf-8")

        if not content.strip():
            console.print("[red]SVG file is empty.[/red]")
            return

        if "<svg" not in content.lower():
            console.print("[red]Invalid SVG file.[/red]")
            return

        if pil_fmt is None:

            # SVG optimization

            content = re.sub(
                r'<!--.*?-->',
                '',
                content,
                flags=re.DOTALL
            )

            content = content.strip()

            output.write_text(
                content,
                encoding="utf-8"
            )

        elif pil_fmt == "PDF":

            import cairosvg

            with Progress(
                SpinnerColumn("dots"),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True
            ) as progress:

                progress.add_task(
                    "[info]Converting SVG to PDF...[/info]",
                    total=None
                )

                cairosvg.svg2pdf(
                    url=str(p),
                    write_to=str(output)
                )

        else:

            import cairosvg
            from PIL import Image
            import io

            with Progress(
                SpinnerColumn("dots"),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True
            ) as progress:

                progress.add_task(
                    f"[info]Converting SVG to {name}...[/info]",
                    total=None
                )

                png_data = cairosvg.svg2png(
                    url=str(p)
                )

                with Image.open(io.BytesIO(png_data)) as source:

                    img = source.convert("RGBA")

                    if pil_fmt == "JPEG":

                        background = Image.new(
                            "RGB",
                            img.size,
                            (255, 255, 255)
                        )

                        background.paste(
                            img,
                            mask=img.getchannel("A")
                        )

                        img.close()
                        img = background

                    elif pil_fmt == "WEBP":

                        img = img.convert("RGBA")

                    save_options = {}

                    if pil_fmt == "JPEG":
                        save_options["quality"] = 90
                        save_options["optimize"] = True

                    elif pil_fmt == "WEBP":
                        save_options["quality"] = 90
                        save_options["method"] = 6

                    img.save(
                        output,
                        format=pil_fmt,
                        **save_options
                    )

                    img.close()

        if not _check_output(output):
            _remove_partial_output(output)
            return

        size = output.stat().st_size / 1024

        console.print(f"[dim]Size: {size:.2f} KB[/dim]")

        confirm_save(output)

    except ImportError as e:

        _remove_partial_output(output)

        package = "cairosvg" if "cairosvg" in str(e).lower() else "Pillow"

        console.print(
            f"[yellow]Required package is missing: {package}[/yellow]"
        )

    except Exception as e:

        _remove_partial_output(output)

        console.print(f"[red]SVG conversion failed: {e}[/red]")


def _convert_document():
    """Document conversion."""

    console.print("\n[bold]Document conversion type:[/bold]")

    for k, (name, _) in DOCUMENT_FORMATS.items():
        console.print(f"  [accent]{k}[/accent]. {name}")

    conv_choice = Prompt.ask(
        "[info]Choose conversion[/info]",
        choices=list(DOCUMENT_FORMATS.keys())
    )

    _, conv_type = DOCUMENT_FORMATS[conv_choice]

    if conv_type == "pdf_to_images":
        _pdf_to_images()

    elif conv_type == "images_to_pdf":
        _images_to_pdf()

    elif conv_type == "txt_to_pdf":
        _txt_to_pdf()

    elif conv_type == "html_to_pdf":
        _html_to_pdf()

    elif conv_type in ("pdf_to_docx", "docx_to_pdf"):
        _document_convert(conv_type)


def _pdf_to_images():
    """Convert PDF pages to images."""

    input_path = Prompt.ask("[info]Enter PDF file path[/info]")
    p = _validate_input(input_path)

    if p is None:
        return

    if p.suffix.lower() != ".pdf":
        console.print("[red]Input file must be a PDF.[/red]")
        return

    filename = ask_filename(p.stem)

    if not filename:
        console.print("[red]Invalid filename.[/red]")
        return

    output_dir = get_save_path('images') / f"{filename}_pages"

    try:

        from pdf2image import convert_from_path

        output_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        with Progress(
            SpinnerColumn("dots"),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:

            progress.add_task(
                "[info]Converting PDF to images...[/info]",
                total=None
            )

            images = convert_from_path(str(p))

            if not images:
                console.print("[red]PDF contains no pages.[/red]")
                return

            saved_count = 0

            try:

                for i, img in enumerate(images):

                    page_path = output_dir / f"page_{i + 1}.png"

                    img.save(
                        page_path,
                        format="PNG"
                    )

                    saved_count += 1

            finally:

                for img in images:
                    img.close()

        console.print(
            f"[success]Saved {saved_count} pages to {output_dir}[/success]"
        )

    except ImportError:

        console.print(
            "[yellow]pdf2image not installed. "
            "Install with: pip install pdf2image[/yellow]"
        )

        console.print(
            "[dim]Also requires poppler: "
            "apt install poppler-utils (Linux) / "
            "brew install poppler (Mac)[/dim]"
        )

    except Exception as e:

        console.print(f"[red]Conversion failed: {e}[/red]")


def _images_to_pdf():
    """Convert images to PDF."""

    if not ensure_pip_module(
        'PIL',
        pip_name='Pillow',
        display_name='Pillow'
    ):
        return

    console.print(
        "[info]Enter image file paths (space-separated, or 'all' for all images in CWD)[/info]"
    )

    raw = Prompt.ask("[info]Images[/info]")

    try:

        if raw.strip().lower() == 'all':

            image_files = []

            for pattern in (
                "*.[jJ][pP][gG]",
                "*.[jJ][pP][eE][gG]",
                "*.[pP][nN][gG]",
                "*.[wW][eE][bB][pP]",
                "*.[bB][mM][pP]",
                "*.[tT][iI][fF]",
                "*.[tT][iI][fF][fF]",
                "*.[gG][iI][fF]"
            ):

                image_files.extend(
                    sorted(Path.cwd().glob(pattern))
                )

        else:

            image_files = [
                Path(f).expanduser()
                for f in shlex.split(raw)
            ]

        image_files = list(dict.fromkeys(image_files))

        if not image_files:
            console.print("[red]No images found.[/red]")
            return

        valid_files = []

        for f in image_files:

            if not f.is_file():
                console.print(f"[yellow]Skipping missing file: {f}[/yellow]")
                continue

            valid_files.append(f)

        if not valid_files:
            console.print("[red]No valid image files found.[/red]")
            return

        filename = ask_filename("converted")

        if not filename:
            console.print("[red]Invalid filename.[/red]")
            return

        output = get_save_path('documents') / f"{filename}.pdf"

        from PIL import Image

        imgs = []

        try:

            with Progress(
                SpinnerColumn("dots"),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True
            ) as progress:

                progress.add_task(
                    "[info]Creating PDF from images...[/info]",
                    total=None
                )

                for f in valid_files:

                    try:

                        with Image.open(f) as source:

                            source.seek(0)

                            imgs.append(
                                source.convert("RGB")
                            )

                    except Exception as e:

                        console.print(
                            f"[yellow]Skipping invalid image {f}: {e}[/yellow]"
                        )

                if not imgs:
                    console.print("[red]No valid images to convert.[/red]")
                    return

                imgs[0].save(
                    output,
                    format="PDF",
                    save_all=True,
                    append_images=imgs[1:]
                )

        finally:

            for img in imgs:
                img.close()

        if not _check_output(output):
            _remove_partial_output(output)
            return

        confirm_save(output)

    except Exception as e:

        console.print(f"[red]Conversion failed: {e}[/red]")


def _txt_to_pdf():
    """Convert TXT to PDF."""

    input_path = Prompt.ask("[info]Enter text file path[/info]")
    p = _validate_input(input_path)

    if p is None:
        return

    filename = ask_filename(p.stem)

    if not filename:
        console.print("[red]Invalid filename.[/red]")
        return

    output = get_save_path('documents') / f"{filename}.pdf"

    try:

        content = p.read_text(
            encoding='utf-8-sig',
            errors='replace'
        )

        try:

            from fpdf import FPDF

            pdf = FPDF()
            pdf.set_auto_page_break(
                auto=True,
                margin=15
            )

            pdf.add_page()
            pdf.set_font("Helvetica", size=11)

            for line in content.splitlines():

                pdf.multi_cell(
                    0,
                    6,
                    line.encode(
                        "latin-1",
                        errors="replace"
                    ).decode("latin-1")
                )

            pdf.output(str(output))

        except ImportError:

            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            from reportlab.lib.utils import simpleSplit

            page_width, page_height = letter

            c = canvas.Canvas(
                str(output),
                pagesize=letter
            )

            c.setFont("Helvetica", 11)

            y = page_height - 42

            for line in content.splitlines():

                wrapped_lines = simpleSplit(
                    line,
                    "Helvetica",
                    11,
                    page_width - 100
                )

                if not wrapped_lines:
                    wrapped_lines = [""]

                for wrapped_line in wrapped_lines:

                    if y < 50:

                        c.showPage()
                        c.setFont("Helvetica", 11)
                        y = page_height - 42

                    safe_line = wrapped_line.encode(
                        "latin-1",
                        errors="replace"
                    ).decode("latin-1")

                    c.drawString(
                        50,
                        y,
                        safe_line
                    )

                    y -= 14

            c.save()

        if not _check_output(output):
            _remove_partial_output(output)
            return

        confirm_save(output)

    except Exception as e:

        _remove_partial_output(output)

        console.print(f"[red]Conversion failed: {e}[/red]")


def _html_to_pdf():
    """Convert HTML to PDF."""

    input_path = Prompt.ask(
        "[info]Enter HTML file path or URL[/info]"
    ).strip()

    if not input_path:
        console.print("[red]Input cannot be empty.[/red]")
        return

    is_url = input_path.lower().startswith(
        ("http://", "https://")
    )

    if not is_url:

        p = _validate_input(input_path)

        if p is None:
            return

        input_path = str(p)

    else:

        from urllib.parse import urlparse

        parsed = urlparse(input_path)

        if not parsed.netloc:
            console.print("[red]Invalid URL.[/red]")
            return

    filename = ask_filename("converted")

    if not filename:
        console.print("[red]Invalid filename.[/red]")
        return

    output = get_save_path('documents') / f"{filename}.pdf"

    try:

        from weasyprint import HTML

        with Progress(
            SpinnerColumn("dots"),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:

            progress.add_task(
                "[info]Converting HTML to PDF...[/info]",
                total=None
            )

            if is_url:

                HTML(
                    url=input_path
                ).write_pdf(str(output))

            else:

                HTML(
                    filename=input_path
                ).write_pdf(str(output))

        if not _check_output(output):
            _remove_partial_output(output)
            return

        confirm_save(output)

    except ImportError:

        console.print(
            "[yellow]For HTML to PDF, install: "
            "pip install weasyprint[/yellow]"
        )

    except Exception as e:

        _remove_partial_output(output)

        console.print(f"[red]Conversion failed: {e}[/red]")


def _document_convert(conv_type):
    """PDF <-> DOCX conversion."""

    if conv_type == "pdf_to_docx":

        input_path = Prompt.ask(
            "[info]Enter PDF file path[/info]"
        )

        p = _validate_input(input_path)

        if p is None:
            return

        if p.suffix.lower() != ".pdf":
            console.print("[red]Input file must be a PDF.[/red]")
            return

        filename = ask_filename(p.stem)

        if not filename:
            console.print("[red]Invalid filename.[/red]")
            return

        output = get_save_path('documents') / f"{filename}.docx"

        cv = None

        try:

            from pdf2docx import Converter

            with Progress(
                SpinnerColumn("dots"),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                console=console
            ) as progress:

                progress.add_task(
                    "[info]Converting PDF to DOCX...[/info]",
                    total=None
                )

                try:

                    cv = Converter(str(p))
                    cv.convert(str(output))

                finally:

                    if cv is not None:
                        cv.close()

            if not _check_output(output):
                _remove_partial_output(output)
                return

            confirm_save(output)

        except ImportError:

            console.print(
                "[yellow]Install pdf2docx: "
                "pip install pdf2docx[/yellow]"
            )

        except Exception as e:

            _remove_partial_output(output)

            console.print(f"[red]Conversion failed: {e}[/red]")

    elif conv_type == "docx_to_pdf":

        input_path = Prompt.ask(
            "[info]Enter DOCX file path[/info]"
        )

        p = _validate_input(input_path)

        if p is None:
            return

        if p.suffix.lower() != ".docx":
            console.print("[red]Input file must be a DOCX file.[/red]")
            return

        filename = ask_filename(p.stem)

        if not filename:
            console.print("[red]Invalid filename.[/red]")
            return

        output = get_save_path('documents') / f"{filename}.pdf"

        try:

            from docx2pdf import convert as docx2pdf_convert

            with Progress(
                SpinnerColumn("dots"),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True
            ) as progress:

                progress.add_task(
                    "[info]Converting DOCX to PDF...[/info]",
                    total=None
                )

                docx2pdf_convert(
                    str(p),
                    str(output)
                )

            if not _check_output(output):
                _remove_partial_output(output)
                return

            confirm_save(output)

        except ImportError:

            console.print(
                "[yellow]Install docx2pdf: "
                "pip install docx2pdf[/yellow]"
            )

        except Exception as e:

            _remove_partial_output(output)

            console.print(f"[red]Conversion failed: {e}[/red]")