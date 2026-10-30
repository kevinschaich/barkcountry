"""Save a page read in the built-in browser pane (for hosts that block fetch.py, like sepaq.com).

    .venv/bin/python save_browser.py <url> <status> < page-text.txt

Pass the page text from the browser's get_page_text on stdin, and as <status> pass 200 if the page
loaded, or what the browser showed (404, blocked). The time is taken here, not typed by hand.
"""
import sys
from fetch import save

url, status = sys.argv[1], sys.argv[2]
text = sys.stdin.read()
print(save(url, text, int(status) if status.isdigit() else status, 'browser'))
