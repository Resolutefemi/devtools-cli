import click, subprocess, os
from pathlib import Path
from ..config import console, get_save_path, ask_filename, confirm_save, ensure_cli_tool, ensure_pip_module, bar_width, BORDER_ROUNDED
from rich.prompt import Prompt, IntPrompt
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich import box


def _ffmpeg_convert(input_path, output_path, extra_args=None):
    """Run ffmpeg conversion with progress display."""
    cmd = ['ffmpeg', '-y', '-i', str(input_path)]
    if extra_args:
        cmd.extend(extra_args)
    cmd.append(str(output_path))

    console.print(f"[dim]Running: {' '.join(cmd)}[/dim]\n")

    with Progress(
        SpinnerColumn("dots"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=bar_width()),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[info]Converting...[/info]", total=None)
        result = subprocess.run(cmd, capture_output=True, text=True)
        progress.update(task, completed=1)

    if result.returncode != 0:
        console.print(f"[red]FFmpeg Error: {result.stderr[-500:]}[/red]")
        return False
    return True


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


@click.command()
def convert():
    """Convert files between any format (Audio, Video, Image, SVG, Documents)"""
    console.print()
    console.print(Panel(
        "[bold brand]DT CONVERT[/bold brand]\n[dim]Universal file converter - convert anything to anything[/dim]",
        border_style="brand", box=box.DOUBLE_EDGE
    ))
    console.print()

    # Category selection
    table = Table(box=box.ROUNDED, border_style="accent", show_header=False, padding=(0, 2))
    table.add_column(style="dim", ratio=1)
    table.add_column(style="white bold", ratio=3)
    table.add_row("[1]", "Audio  (MP3, WAV, AAC, OGG, FLAC, WMA, M4A)")
    table.add_row("[2]", "Documents  (PDF, DOCX, TXT, HTML, Images)")
    table.add_row("[3]", "Video  (MP4, MKV, AVI, MOV, WEBM, GIF, TS, FLV, 3GP)")
    table.add_row("[4]", "Image  (JPEG, PNG, WEBP, BMP, ICO, TIFF, GIF)")
    table.add_row("[5]", "SVG  (to PNG, JPEG, WEBP, PDF, or optimize)")
    console.print(table)

    choice = Prompt.ask("\n[info]Which type of files are you working with?[/info]", choices=["1", "2", "3", "4", "5"])

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
    p = Path(input_path)
    if not p.exists():
        console.print(f"[red]File not found: {input_path}[/red]")
        return

    # Show format options
    console.print("\n[bold]Output format:[/bold]")
    for k, (name, ext, _) in AUDIO_FORMATS.items():
        console.print(f"  [accent]{k}[/accent]. {name} {ext}")

    fmt_choice = Prompt.ask("[info]Choose format[/info]", choices=list(AUDIO_FORMATS.keys()))
    name, ext, args = AUDIO_FORMATS[fmt_choice]
    filename = ask_filename(p.stem)
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
    p = Path(input_path)
    if not p.exists():
        console.print(f"[red]File not found: {input_path}[/red]")
        return

    console.print("\n[bold]Output format:[/bold]")
    for k, (name, ext, _) in VIDEO_FORMATS.items():
        console.print(f"  [accent]{k}[/accent]. {name} {ext}")

    fmt_choice = Prompt.ask("[info]Choose format[/info]", choices=list(VIDEO_FORMATS.keys()))
    name, ext, args = VIDEO_FORMATS[fmt_choice]
    filename = ask_filename(p.stem)
    output = get_save_path('videos') / f"{filename}{ext}"

    if _ffmpeg_convert(p, output, args):
        size = output.stat().st_size / 1024 / 1024
        orig_size = p.stat().st_size / 1024 / 1024
        console.print(f"[dim]Original: {orig_size:.2f} MB -> New: {size:.2f} MB[/dim]")
        confirm_save(output)


def _convert_image():
    """Image conversion using Pillow."""
    if not ensure_pip_module('PIL', pip_name='Pillow', display_name='Pillow'):
        return

    input_path = Prompt.ask("[info]Enter image file path[/info]")
    p = Path(input_path)
    if not p.exists():
        console.print(f"[red]File not found: {input_path}[/red]")
        return

    console.print("\n[bold]Output format:[/bold]")
    for k, (name, ext, _) in IMAGE_FORMATS.items():
        console.print(f"  [accent]{k}[/accent]. {name} {ext}")

    fmt_choice = Prompt.ask("[info]Choose format[/info]", choices=list(IMAGE_FORMATS.keys()))
    name, ext, pil_fmt = IMAGE_FORMATS[fmt_choice]
    filename = ask_filename(p.stem)
    output = get_save_path('images') / f"{filename}{ext}"

    try:
        from PIL import Image
        with Progress(SpinnerColumn("dots"), TextColumn("[progress.description]{task.description}"), console=console, transient=True) as progress:
            progress.add_task("[info]Converting image...[/info]", total=None)
            img = Image.open(p)
            if pil_fmt == "JPEG" and img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            if pil_fmt == "ICO":
                # Resize for ICO
                img.thumbnail((256, 256))
            img.save(output, format=pil_fmt, optimize=True, quality=90)

        size = output.stat().st_size / 1024
        console.print(f"[dim]Size: {size:.2f} KB[/dim]")
        confirm_save(output)
    except Exception as e:
        console.print(f"[red]Conversion failed: {e}[/red]")


def _convert_svg():
    """SVG conversion."""
    input_path = Prompt.ask("[info]Enter SVG file path[/info]")
    p = Path(input_path)
    if not p.exists():
        console.print(f"[red]File not found: {input_path}[/red]")
        return

    console.print("\n[bold]Convert to:[/bold]")
    for k, (name, ext, _) in SVG_IMAGE_FORMATS.items():
        console.print(f"  [accent]{k}[/accent]. {name} {ext}")

    fmt_choice = Prompt.ask("[info]Choose format[/info]", choices=list(SVG_IMAGE_FORMATS.keys()))
    name, ext, pil_fmt = SVG_IMAGE_FORMATS[fmt_choice]
    filename = ask_filename(p.stem)
    output = get_save_path('images') / f"{filename}{ext}"

    try:
        if pil_fmt is None:
            # SVG optimize - simple minification
            import re
            with Progress(SpinnerColumn("dots"), TextColumn("[progress.description]{task.description}"), console=console, transient=True) as progress:
                progress.add_task("[info]Optimizing SVG...[/info]", total=None)
                content = p.read_text()
                # Remove comments, extra whitespace
                content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
                content = re.sub(r'\s+', ' ', content)
                output.write_text(content)
        elif pil_fmt == "PDF":
            # Use cairosvg if available, fallback to Pillow
            try:
                import cairosvg
                with Progress(SpinnerColumn("dots"), TextColumn("[progress.description]{task.description}"), console=console, transient=True) as progress:
                    progress.add_task("[info]Converting SVG to PDF...[/info]", total=None)
                    cairosvg.svg2pdf(url=str(p), write_to=str(output))
            except ImportError:
                console.print("[yellow]cairosvg not installed. Using Pillow fallback...[/yellow]")
                from PIL import Image
                with Progress(SpinnerColumn("dots"), TextColumn("[progress.description]{task.description}"), console=console, transient=True) as progress:
                    progress.add_task("[info]Converting SVG...[/info]", total=None)
                    # Render SVG via cairosvg or report missing
                    console.print("[red]Install cairosvg for SVG rendering: pip install cairosvg[/red]")
                    return
        else:
            # SVG to raster image
            try:
                import cairosvg
                with Progress(SpinnerColumn("dots"), TextColumn("[progress.description]{task.description}"), console=console, transient=True) as progress:
                    progress.add_task(f"[info]Converting SVG to {name}...[/info]", total=None)
                    cairosvg.svg2png(url=str(p), write_to=str(output), output_width=1024, output_height=1024)
            except ImportError:
                # Fallback: try using Pillow with svg support or report
                console.print("[yellow]For best SVG rendering, install cairosvg: pip install cairosvg[/yellow]")
                console.print("[dim]Attempting Pillow-based conversion...[/dim]")
                from PIL import Image
                try:
                    with Progress(SpinnerColumn("dots"), TextColumn("[progress.description]{task.description}"), console=console, transient=True) as progress:
                        progress.add_task(f"[info]Converting SVG to {name}...[/info]", total=None)
                        # Pillow can't natively read SVG, but we can try
                        import io
                        img = Image.open(io.BytesIO(p.read_bytes()))
                        if img.mode in ('RGBA', 'LA', 'P') and pil_fmt == "JPEG":
                            img = img.convert('RGB')
                        img.save(output, format=pil_fmt)
                except Exception:
                    console.print("[red]Cannot convert SVG without cairosvg. Install it: pip install cairosvg[/red]")
                    return

        size = output.stat().st_size / 1024
        console.print(f"[dim]Size: {size:.2f} KB[/dim]")
        confirm_save(output)
    except Exception as e:
        console.print(f"[red]SVG conversion failed: {e}[/red]")


def _convert_document():
    """Document conversion."""
    console.print("\n[bold]Document conversion type:[/bold]")
    for k, (name, _) in DOCUMENT_FORMATS.items():
        console.print(f"  [accent]{k}[/accent]. {name}")

    conv_choice = Prompt.ask("[info]Choose conversion[/info]", choices=list(DOCUMENT_FORMATS.keys()))
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
    p = Path(input_path)
    if not p.exists():
        console.print(f"[red]File not found[/red]")
        return

    filename = ask_filename(p.stem)
    output_dir = get_save_path('images') / f"{filename}_pages"
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        from pdf2image import convert_from_path
        with Progress(SpinnerColumn("dots"), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            progress.add_task("[info]Converting PDF to images...[/info]", total=None)
            images = convert_from_path(str(p))
            for i, img in enumerate(images):
                img.save(output_dir / f"page_{i+1}.png", "PNG")
        console.print(f"[success]Saved {len(images)} pages to {output_dir}[/success]")
    except ImportError:
        console.print("[yellow]pdf2image not installed. Install with: pip install pdf2image[/yellow]")
        console.print("[dim]Also requires poppler: apt install poppler-utils (Linux) / brew install poppler (Mac)[/dim]")
    except Exception as e:
        console.print(f"[red]Conversion failed: {e}[/red]")


def _images_to_pdf():
    """Convert images to PDF."""
    if not ensure_pip_module('PIL', pip_name='Pillow', display_name='Pillow'):
        return

    console.print("[info]Enter image file paths (space-separated, or 'all' for all images in CWD)[/info]")
    raw = Prompt.ask("[info]Images[/info]")

    if raw.strip().lower() == 'all':
        image_files = sorted(Path.cwd().glob("*.[jJ][pP][gG]")) + \
                      sorted(Path.cwd().glob("*.[pP][nN][gG]")) + \
                      sorted(Path.cwd().glob("*.[wW][eE][bB][pP]"))
    else:
        image_files = [Path(f) for f in raw.split()]

    if not image_files:
        console.print("[red]No images found[/red]")
        return

    filename = ask_filename("converted")
    output = get_save_path('documents') / f"{filename}.pdf"

    try:
        from PIL import Image
        with Progress(SpinnerColumn("dots"), TextColumn("[progress.description]{task.description}"), console=console, transient=True) as progress:
            progress.add_task("[info]Creating PDF from images...[/info]", total=None)
            imgs = [Image.open(f).convert('RGB') for f in image_files if f.exists()]
            if imgs:
                imgs[0].save(output, "PDF", save_all=True, append_images=imgs[1:])
        confirm_save(output)
    except Exception as e:
        console.print(f"[red]Conversion failed: {e}[/red]")


def _txt_to_pdf():
    """Convert TXT to PDF."""
    input_path = Prompt.ask("[info]Enter text file path[/info]")
    p = Path(input_path)
    if not p.exists():
        console.print(f"[red]File not found[/red]")
        return

    filename = ask_filename(p.stem)
    output = get_save_path('documents') / f"{filename}.pdf"

    try:
        from fpdf import FPDF
        with Progress(SpinnerColumn("dots"), TextColumn("[progress.description]{task.description}"), console=console, transient=True) as progress:
            progress.add_task("[info]Converting TXT to PDF...[/info]", total=None)
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", size=11)
            content = p.read_text(encoding='utf-8', errors='replace')
            for line in content.split('\n'):
                pdf.cell(0, 6, line, ln=True)
            pdf.output(str(output))
        confirm_save(output)
    except ImportError:
        # Fallback: basic PDF with reportlab
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            from reportlab.lib.utils import simpleSplit
            with Progress(SpinnerColumn("dots"), TextColumn("[progress.description]{task.description}"), console=console, transient=True) as progress:
                progress.add_task("[info]Converting TXT to PDF...[/info]", total=None)
                c = canvas.Canvas(str(output), pagesize=letter)
                c.setFont("Helvetica", 11)
                content = p.read_text(encoding='utf-8', errors='replace')
                y = 750
                for line in content.split('\n'):
                    if y < 50:
                        c.showPage()
                        y = 750
                        c.setFont("Helvetica", 11)
                    c.drawString(50, y, line)
                    y -= 14
                c.save()
            confirm_save(output)
        except ImportError:
            console.print("[yellow]Install fpdf2 or reportlab: pip install fpdf2[/yellow]")
    except Exception as e:
        console.print(f"[red]Conversion failed: {e}[/red]")


def _html_to_pdf():
    """Convert HTML to PDF."""
    input_path = Prompt.ask("[info]Enter HTML file path or URL[/info]")
    filename = ask_filename("converted")
    output = get_save_path('documents') / f"{filename}.pdf"

    # Try using a headless approach
    ensure_cli_tool('ffmpeg', display_name='ffmpeg')  # ensure tools available

    try:
        import subprocess
        # Try weasyprint first
        with Progress(SpinnerColumn("dots"), TextColumn("[progress.description]{task.description}"), console=console, transient=True) as progress:
            progress.add_task("[info]Converting HTML to PDF...[/info]", total=None)
            try:
                from weasyprint import HTML
                if input_path.startswith('http'):
                    HTML(url=input_path).write_pdf(str(output))
                else:
                    HTML(filename=input_path).write_pdf(str(output))
                confirm_save(output)
            except ImportError:
                console.print("[yellow]For HTML to PDF, install: pip install weasyprint[/yellow]")
    except Exception as e:
        console.print(f"[red]Conversion failed: {e}[/red]")


def _document_convert(conv_type):
    """PDF <-> DOCX conversion."""
    if conv_type == "pdf_to_docx":
        input_path = Prompt.ask("[info]Enter PDF file path[/info]")
        p = Path(input_path)
        if not p.exists():
            console.print("[red]File not found[/red]")
            return
        filename = ask_filename(p.stem)
        output = get_save_path('documents') / f"{filename}.docx"

        try:
            from pdf2docx import Converter
            with Progress(SpinnerColumn("dots"), TextColumn("[progress.description]{task.description}"), BarColumn(), console=console) as progress:
                progress.add_task("[info]Converting PDF to DOCX...[/info]", total=None)
                cv = Converter(str(p))
                cv.convert(str(output))
                cv.close()
            confirm_save(output)
        except ImportError:
            console.print("[yellow]Install pdf2docx: pip install pdf2docx[/yellow]")
        except Exception as e:
            console.print(f"[red]Conversion failed: {e}[/red]")

    elif conv_type == "docx_to_pdf":
        input_path = Prompt.ask("[info]Enter DOCX file path[/info]")
        p = Path(input_path)
        if not p.exists():
            console.print("[red]File not found[/red]")
            return
        filename = ask_filename(p.stem)
        output = get_save_path('documents') / f"{filename}.pdf"

        try:
            from docx2pdf import convert as docx2pdf_convert
            with Progress(SpinnerColumn("dots"), TextColumn("[progress.description]{task.description}"), console=console, transient=True) as progress:
                progress.add_task("[info]Converting DOCX to PDF...[/info]", total=None)
                docx2pdf_convert(str(p), str(output))
            confirm_save(output)
        except ImportError:
            console.print("[yellow]Install docx2pdf: pip install docx2pdf[/yellow]")
        except Exception as e:
            console.print(f"[red]Conversion failed: {e}[/red]")