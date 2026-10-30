"""Fetch an official page, save its text as evidence and log the fetch.

    .venv/bin/python fetch.py <url> [<url> ...]

Prints one JSON line per URL: {url, status, sha1, path, chars}. The fetch log is written by this
script, never by hand, so it shows what really happened.

Requests use an honest user agent that names this project, and wait between requests to the same host.
"""
import hashlib, html.parser, re, threading, io, json, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
PAGES = ROOT / 'pages'
LOG = ROOT / 'fetch-log.jsonl'
UA = 'dog-friendly-national-parks-research/1.0 (+https://github.com/kevinschaich/dog-friendly-national-parks)'
DELAY = 1.5  # seconds between requests to one host
_last = {}
_locks = {}
_guard = threading.Lock()
_loglock = threading.Lock()


class _Text(html.parser.HTMLParser):
    SKIP = {'script', 'style', 'noscript', 'svg', 'head'}
    BLOCK = {'p', 'div', 'li', 'br', 'tr', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'section', 'article', 'td', 'dt', 'dd'}

    def __init__(self):
        super().__init__()
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP: self.skip += 1
        elif tag in self.BLOCK: self.out.append('\n')

    def handle_endtag(self, tag):
        if tag in self.SKIP: self.skip = max(0, self.skip - 1)
        elif tag in self.BLOCK: self.out.append('\n')

    def handle_data(self, data):
        if not self.skip: self.out.append(data)


def to_text(body: bytes, ctype: str) -> str:
    if 'json' in ctype:
        return body.decode('utf-8', 'replace')
    if 'pdf' in ctype or body[:5] == b'%PDF-':
        import pypdf
        return '\n'.join(p.extract_text() or '' for p in pypdf.PdfReader(io.BytesIO(body)).pages)
    p = _Text()
    p.feed(body.decode('utf-8', 'replace'))
    lines = (' '.join(l.split()) for l in ''.join(p.out).splitlines())
    return '\n'.join(l for l in lines if l)


def sha1(url: str) -> str:
    return hashlib.sha1(url.encode()).hexdigest()


def log(entry: dict):
    with _loglock, LOG.open('a') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')


TOKEN = re.compile(r'\b(sk|pk|tk)\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+')  # map keys some sites embed


def save(url: str, text: str, status, via: str) -> dict:
    text = TOKEN.sub('[access token removed]', text)
    PAGES.mkdir(exist_ok=True)
    path = PAGES / f'{sha1(url)}.txt'
    ok = status == 200 and text.strip()
    if ok:
        path.write_text(text)
    entry = {'url': url, 'fetched': datetime.now(timezone.utc).isoformat(timespec='seconds'),
             'status': status, 'via': via, 'sha1': sha1(url), 'chars': len(text) if ok else 0}
    log(entry)
    return {**entry, 'path': str(path.relative_to(ROOT)) if ok else None}


def fetch(url: str) -> dict:
    host = urllib.parse.urlparse(url).netloc
    with _guard:
        lock = _locks.setdefault(host, threading.Lock())
    with lock:
        wait = DELAY - (time.time() - _last.get(host, 0))
        if wait > 0: time.sleep(wait)
        _last[host] = time.time()
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'text/html,application/pdf,application/json,*/*'})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            status, ctype, body = r.status, r.headers.get('Content-Type', ''), r.read()
            final = r.geturl()
    except urllib.error.HTTPError as e:
        return save(url, '', e.code, 'script')
    except Exception as e:
        return save(url, '', f'error: {type(e).__name__}', 'script')
    try:
        text = to_text(body, ctype)
    except Exception as e:
        return save(url, '', f'unreadable: {type(e).__name__}', 'script')
    result = save(url, text, status, 'script')
    if final != url: result['redirectedTo'] = final
    return result


if __name__ == '__main__':
    for u in sys.argv[1:]:
        print(json.dumps(fetch(u)))
