import click, subprocess
from pathlib import Path
from ..config import get_save_path, Colors

@click.command()
def join():
    """Join videos together"""
    import shlex, tempfile
    
    raw_input = click.prompt(f"{Colors.BLUE}Video files (space-separated){Colors.RESET}")
    # Use shlex to correctly handle quoted paths with or without spaces
    try:
        files = shlex.split(raw_input)
    except ValueError:
        files = raw_input.split()

    if not files:
        click.echo(f"{Colors.RED}No files provided.{Colors.RESET}")
        return

    name = click.prompt(f"{Colors.BLUE}Output name{Colors.RESET}", default="joined")
    output = get_save_path('videos') / f"{name}.mp4"

    # Use system temp directory instead of /tmp to avoid Windows security issues
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        list_file = Path(f.name)
        for vid in files:
            f.write(f"file '{Path(vid).absolute()}'\n")

    click.echo(f"{Colors.CYAN}Joining videos...{Colors.RESET}")
    try:
        result = subprocess.run(['ffmpeg', '-f', 'concat', '-safe', '0', '-i', str(list_file),
                       '-c', 'copy', str(output)], capture_output=True, text=True)
        
        if result.returncode != 0:
             click.echo(f"{Colors.RED}FFmpeg Error: {result.stderr}{Colors.RESET}")
    except FileNotFoundError:
        click.echo(f"{Colors.RED}❌ ffmpeg not found. Please install ffmpeg to use media commands.{Colors.RESET}")
        return
    except OSError as e:
        if "225" in str(e):
            click.echo(f"{Colors.RED}❌ Antivirus Blocked: Windows Defender blocked ffmpeg execution.{Colors.RESET}")
            click.echo(f"{Colors.YELLOW}👉 Solution: Add this project folder to your Antivirus Exclusions.{Colors.RESET}")
        else:
            click.echo(f"{Colors.RED}❌ System Error: {e}{Colors.RESET}")
        return
    finally:
        if list_file.exists():
            list_file.unlink()

    if output.exists():
        size = output.stat().st_size / 1024 / 1024
        click.echo(f"{Colors.GREEN}✅ Saved to:{Colors.RESET}")
        click.echo(f"{Colors.CYAN}{output}{Colors.RESET}")
        click.echo(f"{Colors.WHITE}Size: {size:.1f} MB{Colors.RESET}")
    else:
        click.echo(f"{Colors.RED}❌ Failed to join videos{Colors.RESET}")

@click.command()
def music():
    """Extract audio from video"""
    video = click.prompt(f"{Colors.BLUE}Video file{Colors.RESET}")
    name = Path(video).stem
    output = get_save_path('music') / f"{name}.mp3"

    click.echo(f"{Colors.CYAN}Extracting audio...{Colors.RESET}")
    subprocess.run(['ffmpeg', '-i', video, '-vn', '-acodec', 'libmp3lame', '-q:a', '2', str(output)],
                  capture_output=True)

    click.echo(f"{Colors.GREEN}✅ Saved to: {output}{Colors.RESET}")

@click.command()
def shrink():
    """Compress video"""
    video = click.prompt(f"{Colors.BLUE}Video file{Colors.RESET}")
    quality = click.prompt(f"{Colors.BLUE}Quality{Colors.RESET}", type=click.Choice(['whatsapp','small','medium']), default='small')

    scales = {'whatsapp': '640:-2', 'small': '1280:-2', 'medium': '1920:-2'}
    name = Path(video).stem
    output = get_save_path('videos') / f"{name}_compressed.mp4"

    click.echo(f"{Colors.CYAN}Compressing...{Colors.RESET}")
    subprocess.run(['ffmpeg', '-i', video, '-vf', f"scale={scales[quality]}", '-crf', '28', str(output)],
                  capture_output=True)

    if output.exists():
        orig_size = Path(video).stat().st_size / 1024 / 1024
        new_size = output.stat().st_size / 1024 / 1024

        click.echo(f"{Colors.GREEN}✅ Saved to: {output}{Colors.RESET}")
        click.echo(f"{Colors.WHITE}Reduced: {orig_size:.1f}MB → {new_size:.1f}MB{Colors.RESET}")
    else:
         click.echo(f"{Colors.RED}❌ Failed to compress video{Colors.RESET}")

@click.command()
def clip():
    """Cut video clip"""
    video = click.prompt(f"{Colors.BLUE}Video file{Colors.RESET}")
    start = click.prompt(f"{Colors.BLUE}Start time (00:00:10){Colors.RESET}")
    end = click.prompt(f"{Colors.BLUE}End time (00:00:20){Colors.RESET}")

    output = get_save_path('videos') / f"clip_{Path(video).stem}.mp4"

    subprocess.run(['ffmpeg', '-i', video, '-ss', start, '-to', end, '-c', 'copy', str(output)],
                  capture_output=True)

    click.echo(f"{Colors.GREEN}✅ Clip saved: {output}{Colors.RESET}")

@click.command()
def gif():
    """Convert video to GIF"""
    video = click.prompt(f"{Colors.BLUE}Video file{Colors.RESET}")
    output = get_save_path('images') / f"{Path(video).stem}.gif"

    subprocess.run(['ffmpeg', '-i', video, '-vf', 'fps=10,scale=480:-1', str(output)],
                  capture_output=True)

    click.echo(f"{Colors.GREEN}✅ GIF saved: {output}{Colors.RESET}")

@click.command()
def extract():
    """Extract frames from video"""
    video = click.prompt(f"{Colors.BLUE}Video file{Colors.RESET}")
    output_dir = get_save_path('images') / f"{Path(video).stem}_frames"
    output_dir.mkdir(exist_ok=True)

    subprocess.run(['ffmpeg', '-i', video, str(output_dir / 'frame_%04d.png')],
                  capture_output=True)

    click.echo(f"{Colors.GREEN}✅ Frames saved to: {output_dir}{Colors.RESET}")

@click.command()
def compress():
    """Compress images"""
    from PIL import Image
    folder = Path.cwd()
    count = 0

    for img_path in folder.rglob('*'):
        if img_path.suffix.lower() in ['.jpg','.jpeg','.png']:
            if any(d in str(img_path) for d in ['node_modules','.git']):
                continue
            try:
                img = Image.open(img_path)
                img.save(img_path, optimize=True, quality=85)
                count += 1
            except:
                pass

    click.echo(f"{Colors.GREEN}✅ {count} Images compressed{Colors.RESET}")
