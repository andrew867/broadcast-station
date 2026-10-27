"""Display casing only. Never rewrite the authenticated CAP payload or speech."""
import re

WORDS = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)*", re.UNICODE)
SMALL = {'a', 'an', 'and', 'as', 'at', 'but', 'by', 'for', 'from', 'in', 'of', 'on', 'or', 'the', 'to', 'with'}


def display_title(text, language='en-CA'):
    """Cap lower-case English words; French uses sentence case per segment.

    Preserve existing acronym/proper-name casing and all punctuation. Unknown
    languages are left unchanged. Hyphen-separated CAP status phrases begin
    new segments; apostrophes stay inside words.
    """
    language = language.lower().split('-')[0]
    if language not in ('en', 'fr'):
        return text
    first = True
    previous = 0
    def replace(match):
        nonlocal first, previous
        gap = text[previous:match.start()]
        if re.search(r'(?:\s[-–—]\s|[:.!?\n])', gap):
            first = True
        word = match.group()
        capitalize = first or (language == 'en' and word not in SMALL)
        previous = match.end()
        first = False
        if word.islower() and capitalize:
            return word[0].upper() + word[1:]
        return word
    return WORDS.sub(replace, text)


def headline(alert):
    return display_title(alert.get('headline') or alert.get('event', ''), alert.get('language', 'en-CA'))


def display_body(text, alert):
    # Some issuers repeat the heading as the first body line. Format that
    # exact line only; instructions and all other message text stay intact.
    lines = text.splitlines(keepends=True)
    if lines and lines[0].strip() == (alert.get('headline') or alert.get('event', '')).strip():
        original = lines[0].rstrip('\r\n')
        lines[0] = headline(alert) + lines[0][len(original):]
    return ''.join(lines)
