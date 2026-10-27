# SPDX-License-Identifier: Apache-2.0
"""Check first-party manuals, embedded help destinations and published schema."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from skycam.station_config import StationConfig


class HtmlIds(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []

    def handle_starttag(self, tag, attrs):
        self.ids.extend(value for key, value in attrs if key == 'id')


def anchors(text):
    parser = HtmlIds()
    parser.feed(text)
    found = set(parser.ids)
    used = {}
    for heading in re.findall(r'^#{1,6}\s+(.+?)\s*#*$', text, re.M):
        slug = re.sub(r'[^\w\- ]', '', heading.lower()).replace(' ', '-')
        number = used.get(slug, 0)
        found.add(slug if not number else f'{slug}-{number}')
        used[slug] = number + 1
    return found


def verify(root=ROOT):
    errors = []
    documents = sorted(root.glob('*.md')) + sorted((root / 'docs').glob('*.md'))
    links = 0
    for path in documents:
        text = path.read_text(encoding='utf-8')
        # Ignore shell/code examples; document links remain checked.
        text = re.sub(r'^```.*?^```\s*$', '', text, flags=re.M | re.S)
        for destination in re.findall(r'(?<!!)\[[^\]\n]+\]\(([^)\n]+)\)', text):
            parsed = urlsplit(destination.strip('<>'))
            if parsed.scheme or destination.startswith('/'):
                continue
            links += 1
            target = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path
            if not target.is_file():
                errors.append(f'{path.relative_to(root)}: missing {destination}')
            elif parsed.fragment and target.suffix in {'.md', '.html'}:
                if unquote(parsed.fragment) not in anchors(target.read_text(encoding='utf-8')):
                    errors.append(f'{path.relative_to(root)}: missing anchor {destination}')
    guide = (root / 'skycam/static/guide.html').read_text(encoding='utf-8')
    parser = HtmlIds()
    parser.feed(guide)
    if len(parser.ids) != len(set(parser.ids)):
        errors.append('guide.html: duplicate IDs')
    help_links = set()
    for path in (root / 'skycam/static').iterdir():
        if path.suffix not in {'.html', '.js'}:
            continue
        help_links.update(re.findall(r'/guide#([\w-]+)', path.read_text(encoding='utf-8')))
    for anchor in sorted(help_links):
        if anchor not in parser.ids:
            errors.append(f'guide.html: missing linked section #{anchor}')
    manual = (root / 'docs/STUDIO-GUIDE.md').read_text(encoding='utf-8')
    from html import unescape
    for paragraph in re.findall(r'<p>(.*?)</p>', guide, re.S):
        plain = unescape(paragraph)
        if '<' not in plain and plain not in manual:
            errors.append(f'Operator manual/help text differs: {plain[:70]}')
    schema = json.loads((root / 'examples/station.schema.json').read_text(encoding='utf-8'))
    if schema != StationConfig.model_json_schema():
        errors.append('Published station.schema.json differs from the application model')
    if errors:
        raise SystemExit('\n'.join(errors))
    print(json.dumps({'manuals': len(documents), 'local_links': links,
                      'embedded_help_sections': sorted(help_links),
                      'operator_text_matches': True, 'schema_matches_model': True}, indent=2))


if __name__ == '__main__':
    verify()
