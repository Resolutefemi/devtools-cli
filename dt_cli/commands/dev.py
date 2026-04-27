import click, os
from pathlib import Path
from ..config import Colors

@click.command()
@click.argument('lang', type=click.Choice(['node', 'python', 'go', 'rust', 'flutter']))
def ignore(lang):
    """Generate .gitignore for a language"""
    import requests
    url = f"https://raw.githubusercontent.com/github/gitignore/master/{lang.capitalize()}.gitignore"
    try:
        res = requests.get(url)
        Path('.gitignore').write_text(res.text)
        click.echo(f"{Colors.GREEN}✅ .gitignore for {lang} created{Colors.RESET}")
    except:
        click.echo(f"{Colors.RED}Could not fetch gitignore{Colors.RESET}")

@click.command()
def license():
    """Add MIT License to project"""
    name = click.prompt("Your Name")
    year = os.datetime.now().year if hasattr(os, 'datetime') else 2026
    mit = f"""MIT License

Copyright (c) {year} {name}

Permission is hereby granted, free of charge, to any person obtaining a copy..."""
    Path('LICENSE').write_text(mit)
    click.echo(f"{Colors.GREEN}✅ LICENSE (MIT) created{Colors.RESET}")

@click.command()
def readme():
    """Generate a beautiful README template"""
    content = "# Project Name\n\n## Description\n...\n\n## Installation\n```bash\n...\n```"
    Path('README.md').write_text(content)
    click.echo(f"{Colors.GREEN}✅ README.md created{Colors.RESET}")
