import click, requests, random, math, uuid, base64, urllib.parse, os, subprocess
from pathlib import Path
from ..config import Colors

extra_cmds = []

def register(name, doc, action):
    @click.command(name=name)
    @click.argument('args', nargs=-1)
    def cmd(args):
        try:
            res = action(args)
            if res is not None: click.echo(f"{Colors.GREEN}{res}{Colors.RESET}")
        except Exception as e:
            click.echo(f"{Colors.RED}Error: {e}{Colors.RESET}")
    cmd.__doc__ = doc
    extra_cmds.append(cmd)

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
register('uuid', 'Generate UUID', lambda a: uuid.uuid4())
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
register('sin', 'Sine', lambda a: math.sin(float(a[0])))
register('cos', 'Cosine', lambda a: math.cos(float(a[0])))
register('tan', 'Tangent', lambda a: math.tan(float(a[0])))
register('log', 'Natural log', lambda a: math.log(float(a[0])))
register('log10', 'Log10', lambda a: math.log10(float(a[0])))
register('ceil', 'Ceiling', lambda a: math.ceil(float(a[0])))
register('floor', 'Floor', lambda a: math.floor(float(a[0])))
register('round', 'Round', lambda a: round(float(a[0])))
register('abs', 'Absolute', lambda a: abs(float(a[0])))
register('fact', 'Factorial', lambda a: math.factorial(int(a[0])))
register('c2f', 'Celsius to Fahrenheit', lambda a: (float(a[0]) * 9/5) + 32)
register('f2c', 'Fahrenheit to Celsius', lambda a: (float(a[0]) - 32) * 5/9)
register('bmi', 'BMI Calculator (kg, m)', lambda a: float(a[0]) / (float(a[1]) ** 2))

# API / FUN COMMANDS
register('catfact', 'Random cat fact', lambda a: requests.get('https://catfact.ninja/fact').json()['fact'])
register('dogfact', 'Random dog fact', lambda a: requests.get('https://dog-api.kinduff.com/api/facts').json()['facts'][0])
register('chuck', 'Chuck Norris joke', lambda a: requests.get('https://api.chucknorris.io/jokes/random').json()['value'])
register('yesno', 'Random yes or no', lambda a: requests.get('https://yesno.wtf/api').json()['answer'])
register('agify', 'Guess age by name', lambda a: requests.get(f'https://api.agify.io?name={a[0]}').json()['age'])
register('genderize', 'Guess gender by name', lambda a: requests.get(f'https://api.genderize.io?name={a[0]}').json()['gender'])
register('nationalize', 'Guess nationality by name', lambda a: requests.get(f'https://api.nationalize.io?name={a[0]}').json()['country'][0]['country_id'])
register('bored', 'Random activity', lambda a: requests.get('https://www.boredapi.com/api/activity').json()['activity'])
register('ip2', 'Get your IP', lambda a: requests.get('https://api.ipify.org').text)
register('bitcoin', 'Current Bitcoin price', lambda a: requests.get('https://api.coindesk.com/v1/bpi/currentprice.json').json()['bpi']['USD']['rate'] + ' USD')
register('github', 'GitHub user info', lambda a: str(requests.get(f'https://api.github.com/users/{a[0]}').json().get('public_repos', 'User not found')) + " public repos")

# OS / SYSTEM WRAPPERS
register('touch2', 'Create empty file', lambda a: open(a[0], 'a').close())
register('mkdir2', 'Create directory', lambda a: os.makedirs(a[0], exist_ok=True))
register('rm2', 'Remove file', lambda a: os.remove(a[0]))
register('ls2', 'List files', lambda a: '\n'.join(os.listdir(a[0] if a else '.')))
register('pwd2', 'Print working directory', lambda a: os.getcwd())
register('whoami2', 'Current user', lambda a: os.getlogin())
register('echo2', 'Print text', lambda a: ' '.join(a))
register('date2', 'Current date/time', lambda a: __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
register('sleep2', 'Sleep for N seconds', lambda a: __import__('time').sleep(float(a[0])))
register('random', 'Random number 0-1', lambda a: random.random())
register('randint', 'Random int A B', lambda a: random.randint(int(a[0]), int(a[1])))
register('choice', 'Random choice', lambda a: random.choice(a))
register('shuffle', 'Shuffle arguments', lambda a: random.sample(a, len(a)))
register('coin', 'Flip a coin', lambda a: random.choice(['Heads', 'Tails']))
register('dice', 'Roll a dice', lambda a: random.randint(1, 6))
register('magic8', 'Magic 8 Ball', lambda a: random.choice(['It is certain', 'Without a doubt', 'You may rely on it', 'Yes definitely', 'It is decidedly so', 'As I see it, yes', 'Most likely', 'Yes', 'Outlook good', 'Signs point to yes', 'Reply hazy try again', 'Ask again later', 'Better not tell you now', 'Cannot predict now', 'Concentrate and ask again', 'Don\'t count on it', 'My reply is no', 'My sources say no', 'Outlook not so good', 'Very doubtful']))
register('rps', 'Rock Paper Scissors', lambda a: f"You: {a[0].title()}, Me: {random.choice(['Rock', 'Paper', 'Scissors'])}")

# NETWORKING / HACKER
register('http_get', 'HTTP GET', lambda a: requests.get(a[0]).text[:1000] + '...')
register('http_head', 'HTTP HEAD', lambda a: str(requests.head(a[0]).headers))
register('http_options', 'HTTP OPTIONS', lambda a: str(requests.options(a[0]).headers))
register('url_parse', 'Parse URL', lambda a: str(urllib.parse.urlparse(a[0])))
register('mac_addr', 'Random MAC address', lambda a: ':'.join(f"{random.randint(0, 255):02x}" for _ in range(6)))
register('ipv4_gen', 'Random IPv4', lambda a: '.'.join(str(random.randint(0, 255)) for _ in range(4)))
register('port_gen', 'Random Port', lambda a: random.randint(1024, 65535))
register('user_agent', 'Random User Agent', lambda a: random.choice(['Mozilla/5.0 (Windows NT 10.0; Win64; x64)', 'Mozilla/5.0 (Macintosh; Intel Mac OS X)', 'Mozilla/5.0 (X11; Linux x86_64)']))
register('password', 'Simple Password', lambda a: ''.join(random.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*') for _ in range(int(a[0]) if a else 12)))
register('pin', 'Random PIN', lambda a: ''.join(str(random.randint(0, 9)) for _ in range(int(a[0]) if a else 4)))
register('clear2', 'Clear screen', lambda a: os.system('cls' if os.name == 'nt' else 'clear'))
register('size', 'File size', lambda a: f"{os.path.getsize(a[0]) / 1024:.2f} KB")
register('ext', 'File extension', lambda a: os.path.splitext(a[0])[1])
register('basename', 'File basename', lambda a: os.path.basename(a[0]))
register('dirname', 'File dirname', lambda a: os.path.dirname(a[0]))
register('exists', 'File exists?', lambda a: str(os.path.exists(a[0])))
register('isdir', 'Is directory?', lambda a: str(os.path.isdir(a[0])))
register('isfile', 'Is file?', lambda a: str(os.path.isfile(a[0])))

# FINANCE
register('mortgage', 'Mortgage Calc (P, r, n)', lambda a: f"Monthly: {(float(a[0])*(float(a[1])/100/12)*(1+float(a[1])/100/12)**float(a[2]))/((1+float(a[1])/100/12)**float(a[2])-1):.2f}")
register('tip', 'Tip Calc (Total, %)', lambda a: f"Tip: {float(a[0])*(float(a[1])/100):.2f}")
register('tax', 'Tax Calc (Total, %)', lambda a: f"Total: {float(a[0])*(1+float(a[1])/100):.2f}")

# DEV UTILS
register('lorem', 'Lorem Ipsum (Words)', lambda a: ' '.join(['lorem', 'ipsum', 'dolor', 'sit', 'amet', 'consectetur', 'adipiscing', 'elit']*int(a[0] if a else 5))[:int(a[0] if a else 50)])
register('hex_color', 'Random Hex Color', lambda a: f"#{random.randint(0, 0xFFFFFF):06x}")
register('rgb_color', 'Random RGB Color', lambda a: f"rgb({random.randint(0,255)},{random.randint(0,255)},{random.randint(0,255)})")
register('json_mock', 'Dummy JSON', lambda a: '{"id": 1, "name": "Test", "status": "active"}')
register('base64_img', 'B64 Placeholder', lambda a: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==")
register('port_check', 'Port Check (Host, Port)', lambda a: "Open" if subprocess.run(f"powershell Test-NetConnection {a[0]} -Port {a[1]}", shell=True, capture_output=True).returncode == 0 else "Closed")

# CONVERSION
register('bin2dec', 'Binary to Decimal', lambda a: int(a[0], 2))
register('dec2bin', 'Decimal to Binary', lambda a: bin(int(a[0])))
register('hex2dec', 'Hex to Decimal', lambda a: int(a[0], 16))
register('dec2hex', 'Decimal to Hex', lambda a: hex(int(a[0])))
register('oct2dec', 'Octal to Decimal', lambda a: int(a[0], 8))
register('dec2oct', 'Decimal to Octal', lambda a: oct(int(a[0])))
register('kg2lb', 'KG to Lbs', lambda a: float(a[0]) * 2.20462)
register('lb2kg', 'Lbs to KG', lambda a: float(a[0]) / 2.20462)
register('m2ft', 'Meters to Feet', lambda a: float(a[0]) * 3.28084)
register('ft2m', 'Feet to Meters', lambda a: float(a[0]) / 3.28084)

# TIME & DATE
register('tz', 'Current Timezone', lambda a: __import__('time').tzname[0])
register('timestamp', 'Current Timestamp', lambda a: int(__import__('time').time()))
register('days_until', 'Days until YYYY-MM-DD', lambda a: (datetime.datetime.strptime(a[0], '%Y-%m-%d') - datetime.datetime.now()).days)
register('week_num', 'Current Week Number', lambda a: datetime.datetime.now().isocalendar()[1])

# ADVANCED SYSTEM (Wrappers)
register('cpu_count', 'CPU Core Count', lambda a: os.cpu_count())
register('env_var', 'Get Env Var', lambda a: os.environ.get(a[0], "Not Found"))
register('path_list', 'System PATH List', lambda a: '\n'.join(os.environ.get('PATH', '').split(';')))
register('mem_total', 'Total RAM', lambda a: f"{psutil.virtual_memory().total / (1024**3):.2f} GB")
register('mem_avail', 'Available RAM', lambda a: f"{psutil.virtual_memory().available / (1024**3):.2f} GB")
register('disk_io', 'Disk IO Stats', lambda a: str(psutil.disk_io_counters()))
register('net_io', 'Net IO Stats', lambda a: str(psutil.net_io_counters()))

# MORE FUN
register('riddles', 'Random Riddle', lambda a: requests.get('https://riddles-api.vercel.app/random').json()['riddle'])
register('advice', 'Random Advice', lambda a: requests.get('https://api.adviceslip.com/advice').json()['slip']['advice'])
register('quote', 'Inspirational Quote', lambda a: requests.get('https://api.quotable.io/random').json()['content'])
register('trump', 'Trump Quote', lambda a: requests.get('https://api.whatdoestrumpthink.com/api/v1/quotes/random').json()['message'])
register('kanye', 'Kanye Quote', lambda a: requests.get('https://api.kanye.rest').json()['quote'])
register('pokefact', 'Pokemon Fact (ID)', lambda a: requests.get(f'https://pokeapi.co/api/v2/pokemon/{a[0] if a else random.randint(1,151)}').json()['name'].title())
register('coffee', 'Coffee Pic URL', lambda a: requests.get('https://aws.random.cat/meow').json()['file']) # Using cat api as coffee placeholder or similar
register('name_gen', 'Random Name', lambda a: requests.get('https://randomuser.me/api/').json()['results'][0]['name']['first'] + " " + requests.get('https://randomuser.me/api/').json()['results'][0]['name']['last'])
register('ip_loc', 'IP Geolocation', lambda a: requests.get(f'http://ip-api.com/json/{a[0] if a else ""}').json()['city'])

# MISC
register('md5_file', 'MD5 of file', lambda a: hashlib.md5(Path(a[0]).read_bytes()).hexdigest())
register('sha1_file', 'SHA1 of file', lambda a: hashlib.sha1(Path(a[0]).read_bytes()).hexdigest())
register('sha256_file', 'SHA256 of file', lambda a: hashlib.sha256(Path(a[0]).read_bytes()).hexdigest())
register('count_files', 'File count in dir', lambda a: len([f for f in os.listdir(a[0] if a else '.') if os.path.isfile(os.path.join(a[0] if a else '.', f))]))
register('count_dirs', 'Dir count in dir', lambda a: len([f for f in os.listdir(a[0] if a else '.') if os.path.isdir(os.path.join(a[0] if a else '.', f))]))
register('uptime', 'System Uptime', lambda a: f"{(int(__import__('time').time()) - int(psutil.boot_time())) / 3600:.2f} hours")
