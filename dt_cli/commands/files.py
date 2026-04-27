import click, shutil, os
from pathlib import Path
from colorama import Fore, Style
from ..config import get_save_path, Colors, IGNORE_DIRS

@click.command()
def send():
    """Zip current folder for sharing"""
    folder = Path.cwd()
    name = click.prompt(f"{Colors.BLUE}Zip name{Colors.RESET}", default=folder.name)

    zip_path = get_save_path('desktop') / f"{name}.zip"
    click.echo(f"{Colors.CYAN}Creating zip...{Colors.RESET}")

    shutil.make_archive(str(zip_path.with_suffix('')), 'zip', folder,
                       ignore=lambda d, files: [f for f in files if f in IGNORE_DIRS])

    size = zip_path.stat().st_size / 1024 / 1024
    click.echo(f"{Colors.GREEN}✅ Saved to: {zip_path}{Colors.RESET}")
    click.echo(f"{Colors.CYAN}Size: {size:.1f} MB{Colors.RESET}")

@click.command()
def clean():
    """Clean junk files"""
    patterns = ['*.pyc', '*.log', '*.tmp', '.DS_Store', 'Thumbs.db']
    count = 0
    for pattern in patterns:
        for f in Path.cwd().rglob(pattern):
            if not any(d in str(f) for d in IGNORE_DIRS):
                try:
                    f.unlink()
                    count += 1
                except:
                    pass

    for d in Path.cwd().rglob('__pycache__'):
        if d.is_dir():
            try:
                shutil.rmtree(d)
                count += 1
            except:
                pass

    click.echo(f"{Colors.GREEN}✅ Cleaned {count} files{Colors.RESET}")

@click.command()
def organize():
    """Organize Downloads folder"""
    downloads = get_save_path('downloads')
    moved = 0

    types = {
        'images': ['.jpg','.jpeg','.png','.gif','.webp'],
        'videos': ['.mp4','.mov','.avi','.mkv'],
        'documents': ['.pdf','.doc','.docx','.txt'],
        'music': ['.mp3','.wav','.flac'],
    }

    for f in downloads.iterdir():
        if f.is_file():
            for folder, exts in types.items():
                if f.suffix.lower() in exts:
                    dest = get_save_path(folder) / f.name
                    try:
                        shutil.move(str(f), str(dest))
                        moved += 1
                    except:
                        pass
                    break

    click.echo(f"{Colors.GREEN}✅ Organized {moved} files{Colors.RESET}")

@click.command()
@click.argument('name')
def find(name):
    """Find file by name"""
    click.echo(f"{Colors.CYAN}Searching for '{name}'...{Colors.RESET}")
    found = []
    for f in Path.home().rglob(f'*{name}*'):
        if f.is_file() and not any(d in str(f) for d in IGNORE_DIRS):
            found.append(f)
            click.echo(f"{Colors.GREEN}{f}{Colors.RESET}")
            if len(found) >= 10:
                break
    if not found:
        click.echo(f"{Colors.YELLOW}Not found{Colors.RESET}")

@click.command()
def big():
    """Show biggest files"""
    files = []
    for f in Path.cwd().rglob('*'):
        if f.is_file() and not any(d in str(f) for d in IGNORE_DIRS):
            try:
                files.append((f, f.stat().st_size))
            except:
                pass

    files.sort(key=lambda x: x[1], reverse=True)

    click.echo(f"{Colors.CYAN}Top 10 biggest files:{Colors.RESET}")
    for f, size in files[:10]:
        size_mb = size / 1024 / 1024
        color = Colors.RED if size_mb > 1000 else Colors.YELLOW if size_mb > 100 else Colors.GREEN
        click.echo(f"{color}{size_mb:7.1f} MB {f.relative_to(Path.cwd())}{Colors.RESET}")

@click.command()
def duplicate():
    """Find duplicate files"""
    import hashlib
    seen = {}
    dups = []

    for f in Path.cwd().rglob('*'):
        if f.is_file() and f.stat().st_size < 100*1024*1024:
            if any(d in str(f) for d in IGNORE_DIRS):
                continue
            try:
                h = hashlib.md5(f.read_bytes()).hexdigest()
                if h in seen:
                    dups.append((f, seen[h]))
                else:
                    seen[h] = f
            except:
                pass

    if dups:
        click.echo(f"{Colors.YELLOW}Found {len(dups)} duplicates:{Colors.RESET}")
        for f1, f2 in dups[:10]:
            click.echo(f"{Colors.RED}{f1.name}{Colors.RESET}")
    else:
        click.echo(f"{Colors.GREEN}No duplicates found{Colors.RESET}")

@click.command()
def tree():
    """Show folder tree"""
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        level = root.count(os.sep)
        indent = ' ' * 2 * level
        click.echo(f"{Colors.CYAN}{indent}{os.path.basename(root)}/{Colors.RESET}")
        subindent = ' ' * 2 * (level + 1)
        for f in files[:5]:
            click.echo(f"{Colors.WHITE}{subindent}{f}{Colors.RESET}")

@click.command()
def backup():
    """Create timestamped backup"""
    import datetime
    name = f"{Path.cwd().name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}"
    dest = get_save_path('documents') / f"{name}.zip"
    shutil.make_archive(str(dest.with_suffix('')), 'zip', '.')
    click.echo(f"{Colors.GREEN}✅ Backup: {dest}{Colors.RESET}")

@click.command()
@click.argument('src')
@click.argument('dest')
def fcp(src, dest):
    """High-speed Multi-threaded Copy for big files/folders"""
    import shutil, concurrent.futures
    from pathlib import Path

    src_path = Path(src)
    dest_path = Path(dest)

    if not src_path.exists():
        click.echo(f"{Colors.RED}Source does not exist.{Colors.RESET}")
        return

    click.echo(f"{Colors.CYAN}🚀 Initializing High-Speed Engine...{Colors.RESET}")

    def copy_file(f):
        rel = f.relative_to(src_path)
        target = dest_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, target)

    if src_path.is_file():
        shutil.copy2(src_path, dest_path)
    else:
        files = [f for f in src_path.rglob('*') if f.is_file()]
        click.echo(f"{Colors.YELLOW}Copying {len(files)} files using 8 threads...{Colors.RESET}")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            executor.map(copy_file, files)

    click.echo(f"{Colors.GREEN}✅ Fast-Copy Complete!{Colors.RESET}")

@click.command()
def where():
    """Show current location info"""
    cwd = Path.cwd()
    click.echo(f"{Colors.CYAN}Location: {cwd}{Colors.RESET}")

    if (cwd / '.git').exists():
        import subprocess
        try:
            branch = subprocess.check_output(['git', 'branch', '--show-current'], text=True).strip()
            click.echo(f"{Colors.GREEN}Git branch: {branch}{Colors.RESET}")
        except:
            pass
