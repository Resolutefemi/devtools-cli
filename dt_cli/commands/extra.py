import click, random, secrets, math, uuid, base64, urllib.parse, os, datetime, hashlib, time
from pathlib import Path
from ..config import console, ensure_pip_module

extra_cmds = []

def register(name, doc, action):
    @click.command(name=name)
    @click.argument('args', nargs=-1)
    def cmd(args):
        try:
            res = action(args)
            if res is not None:
                console.print(f"[success]{res}[/success]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
    cmd.__doc__ = doc
    extra_cmds.append(cmd)

def _api_get(url, timeout=5):
    """Helper: lazy-import requests and do GET."""
    if not ensure_pip_module('requests', display_name='requests'):
        return None
    import requests
    return requests.get(url, timeout=timeout)

# TEXT COMMANDS
register('upper', 'To uppercase', lambda a: ' '.join(a).upper())
register('lower', 'To lowercase', lambda a: ' '.join(a).lower())
register('title', 'To titlecase', lambda a: ' '.join(a).title())
register('reverse', 'Reverse text', lambda a: ' '.join(a)[::-1])
register('length', 'Text length', lambda a: len(' '.join(a)))
register('wordcount', 'Word count', lambda a: len(a))
register('slugify', 'To slug', lambda a: '-'.join(a).lower())
register('b64enc', 'Base64 encode', lambda a: base64.b64encode(' '.join(a).encode()).decode())
register('b64dec', 'Base64 decode', lambda a: base64.b64decode(' '.join(a).encode()).decode())
register('urlenc', 'URL encode', lambda a: urllib.parse.quote(' '.join(a)))
register('urldec', 'URL decode', lambda a: urllib.parse.unquote(' '.join(a)))
register('hexenc', 'Hex encode', lambda a: ' '.join(a).encode().hex())
register('hexdec', 'Hex decode', lambda a: bytes.fromhex(' '.join(a)).decode())
register('uuid', 'Generate UUID', lambda a: str(uuid.uuid4()))
register('rot13', 'ROT13 cipher', lambda a: ' '.join(a).translate(str.maketrans('ABCDEFGHIJKLMabcdefghijklmNOPQRSTUVWXYZnopqrstuvwxyz', 'NOPQRSTUVWXYZnopqrstuvwxyzABCDEFGHIJKLMabcdefghijklm')))
register('camelcase', 'To camelCase', lambda a: a[0].lower() + ''.join(x.title() for x in a[1:]) if a else "")
register('snakecase', 'To snake_case', lambda a: '_'.join(a).lower())
register('kebabcase', 'To kebab-case', lambda a: '-'.join(a).lower())
register('morse', 'To Morse code', lambda a: ' '.join({'A':'.-','B':'-...','C':'-.-.','D':'-..','E':'.','F':'..-.','G':'--.','H':'....','I':'..','J':'.---','K':'-.-','L':'.-..','M':'--','N':'-.','O':'---','P':'.--.','Q':'--.-','R':'.-.','S':'...','T':'-','U':'..-','V':'...-','W':'.--','X':'-..-','Y':'-.--','Z':'--..','0':'-----','1':'.----','2':'..---','3':'...--','4':'....-','5':'.....','6':'-....','7':'--...','8':'---..','9':'----.'}.get(c.upper(), c) for c in ' '.join(a)))

# MATH COMMANDS
register('add', 'Add numbers', lambda a: sum(float(x) for x in a))
register('mul', 'Multiply numbers', lambda a: math.prod(float(x) for x in a))
register('sub', 'Subtract numbers', lambda a: float(a[0]) - sum(float(x) for x in a[1:]))
register('div', 'Divide numbers', lambda a: float(a[0]) / math.prod(float(x) for x in a[1:]))
register('mod', 'Modulo', lambda a: float(a[0]) % float(a[1]))
register('pow', 'Power', lambda a: math.pow(float(a[0]), float(a[1])))
register('sqrt', 'Square root', lambda a: math.sqrt(float(a[0])))
register('sin', 'Sine (radians)', lambda a: math.sin(float(a[0])))
register('cos', 'Cosine (radians)', lambda a: math.cos(float(a[0])))
register('tan', 'Tangent (radians)', lambda a: math.tan(float(a[0])))
register('log', 'Natural log', lambda a: math.log(float(a[0])))
register('log10', 'Log10', lambda a: math.log10(float(a[0])))
register('ceil', 'Ceiling', lambda a: math.ceil(float(a[0])))
register('floor', 'Floor', lambda a: math.floor(float(a[0])))
register('round', 'Round number', lambda a: round(float(a[0])))
register('abs', 'Absolute value', lambda a: abs(float(a[0])))
register('fact', 'Factorial', lambda a: math.factorial(int(a[0])))
register('c2f', 'Celsius to Fahrenheit', lambda a: (float(a[0]) * 9/5) + 32)
register('f2c', 'Fahrenheit to Celsius', lambda a: (float(a[0]) - 32) * 5/9)
register('bmi', 'BMI Calculator (kg, m)', lambda a: f"{float(a[0]) / (float(a[1]) ** 2):.1f}")

# API / FUN COMMANDS (lazy-load requests)
def _catfact(a):
    r = _api_get('https://catfact.ninja/fact')
    return r.json()['fact'] if r else None
def _dogfact(a):
    r = _api_get('https://dog-api.kinduff.com/api/facts')
    return r.json()['facts'][0] if r else None
def _chuck(a):
    r = _api_get('https://api.chucknorris.io/jokes/random')
    return r.json()['value'] if r else None
def _yesno(a):
    r = _api_get('https://yesno.wtf/api')
    return r.json()['answer'] if r else None
def _agify(a):
    r = _api_get(f'https://api.agify.io?name={a[0]}')
    return r.json()['age'] if r else None
def _genderize(a):
    r = _api_get(f'https://api.genderize.io?name={a[0]}')
    return r.json()['gender'] if r else None
def _nationalize(a):
    r = _api_get(f'https://api.nationalize.io?name={a[0]}')
    return r.json()['country'][0]['country_id'] if r and r.json().get('country') else None
def _bored(a):
    r = _api_get('https://www.boredapi.com/api/activity')
    return r.json()['activity'] if r else None
def _ip2(a):
    r = _api_get('https://api.ipify.org')
    return r.text if r else None
def _bitcoin(a):
    r = _api_get('https://api.coindesk.com/v1/bpi/currentprice.json')
    return r.json()['bpi']['USD']['rate'] + ' USD' if r else None
def _github_info(a):
    r = _api_get(f'https://api.github.com/users/{a[0]}')
    return str(r.json().get('public_repos', 'User not found')) + " public repos" if r else None
def _riddles(a):
    r = _api_get('https://riddles-api.vercel.app/random')
    return r.json()['riddle'] if r else None
def _advice(a):
    r = _api_get('https://api.adviceslip.com/advice')
    return r.json()['slip']['advice'] if r else None
def _quote(a):
    r = _api_get('https://api.quotable.io/random')
    return r.json()['content'] if r else None
def _trump(a):
    r = _api_get('https://api.whatdoestrumpthink.com/api/v1/quotes/random')
    return r.json()['message'] if r else None
def _kanye(a):
    r = _api_get('https://api.kanye.rest')
    return r.json()['quote'] if r else None
def _pokefact(a):
    pid = a[0] if a else random.randint(1, 151)
    r = _api_get(f'https://pokeapi.co/api/v2/pokemon/{pid}')
    return r.json()['name'].title() if r else None
def _coffee(a):
    r = _api_get('https://coffee.alexflipnote.dev/random.json')
    return r.json().get('file', 'No image') if r else None
def _name_gen(a):
    r = _api_get('https://randomuser.me/api/')
    if r:
        d = r.json()
        return f"{d['results'][0]['name']['first']} {d['results'][0]['name']['last']}"
    return None

register('catfact', 'Random cat fact', _catfact)
register('dogfact', 'Random dog fact', _dogfact)
register('chuck', 'Chuck Norris joke', _chuck)
register('yesno', 'Random yes or no', _yesno)
register('agify', 'Guess age by name', _agify)
register('genderize', 'Guess gender by name', _genderize)
register('nationalize', 'Guess nationality by name', _nationalize)
register('bored', 'Random activity', _bored)
register('ip2', 'Get your IP', _ip2)
register('bitcoin', 'Current Bitcoin price', _bitcoin)
register('github', 'GitHub user info', _github_info)
register('riddles', 'Random riddle', _riddles)
register('advice', 'Random advice', _advice)
register('quote', 'Inspirational quote', _quote)
register('trump', 'Trump quote', _trump)
register('kanye', 'Kanye quote', _kanye)
register('pokefact', 'Pokemon name by ID', _pokefact)
register('coffee', 'Random coffee image URL', _coffee)
register('name_gen', 'Random name', _name_gen)

# OS / SYSTEM WRAPPERS
register('touch2', 'Create empty file', lambda a: Path(a[0]).touch() or None)
register('mkdir2', 'Create directory', lambda a: os.makedirs(a[0], exist_ok=True) or None)
register('rm2', 'Remove file', lambda a: os.remove(a[0]) or None)
register('ls2', 'List files', lambda a: '\n'.join(sorted(os.listdir(a[0] if a else '.'))))
register('pwd2', 'Print working directory', lambda a: os.getcwd())
register('whoami2', 'Current user', lambda a: os.getlogin())
register('echo2', 'Print text', lambda a: ' '.join(a))
register('date2', 'Current date/time', lambda a: datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
register('sleep2', 'Sleep for N seconds', lambda a: (time.sleep(float(a[0])), "Done")[1])

# RANDOM
register('random', 'Random number 0-1', lambda a: random.random())
register('randint', 'Random int A B', lambda a: random.randint(int(a[0]), int(a[1])))
register('choice', 'Random choice', lambda a: random.choice(a))
register('shuffle', 'Shuffle arguments', lambda a: random.sample(a, len(a)))
register('coin', 'Flip a coin', lambda a: random.choice(['Heads', 'Tails']))
register('dice', 'Roll a dice', lambda a: random.randint(1, 6))
register('magic8', 'Magic 8 Ball', lambda a: random.choice(['It is certain', 'Without a doubt', 'You may rely on it', 'Yes definitely', 'It is decidedly so', 'As I see it, yes', 'Most likely', 'Yes', 'Outlook good', 'Signs point to yes', 'Reply hazy try again', 'Ask again later', 'Better not tell you now', 'Cannot predict now', 'Concentrate and ask again', "Don't count on it", 'My reply is no', 'My sources say no', 'Outlook not so good', 'Very doubtful']))
register('rps', 'Rock Paper Scissors', lambda a: f"You: {a[0].title()}, Me: {random.choice(['Rock', 'Paper', 'Scissors'])}")

# NETWORKING (lazy-load requests)
def _http_get(a):
    r = _api_get(a[0], timeout=10)
    return r.text[:1000] + '...' if r else None
def _http_head(a):
    r = _api_get(a[0], timeout=10)
    return str(dict(r.headers)) if r else None
def _http_options(a):
    if not ensure_pip_module('requests', display_name='requests'):
        return None
    import requests
    r = requests.options(a[0], timeout=10)
    return str(dict(r.headers))

register('http_get', 'HTTP GET', _http_get)
register('http_head', 'HTTP HEAD', _http_head)
register('http_options', 'HTTP OPTIONS', _http_options)
register('url_parse', 'Parse URL', lambda a: str(urllib.parse.urlparse(a[0])))
register('mac_addr', 'Random MAC address', lambda a: ':'.join(f"{random.randint(0, 255):02x}" for _ in range(6)))
register('ipv4_gen', 'Random IPv4', lambda a: '.'.join(str(random.randint(0, 255)) for _ in range(4)))
register('port_gen', 'Random Port', lambda a: random.randint(1024, 65535))
register('user_agent', 'Random User Agent', lambda a: random.choice(['Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36', 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)']))
register('password', 'Simple password', lambda a: ''.join(secrets.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*') for _ in range(int(a[0]) if a else 12)))
register('pin', 'Random PIN', l