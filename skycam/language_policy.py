"""Station presentation language, separate from authenticated source storage."""


def english(value=None):
    # CAP defaults an omitted language to English. RSS feeds selected by the
    # station are English, but an explicit item/feed override must be respected.
    tag=str(value or 'en').strip().lower().replace('_','-')
    return tag in {'en','eng','english'} or tag.startswith('en-')


def xml_language(node, fallback=None):
    return (node.get('{http://www.w3.org/XML/1998/namespace}lang') or
            node.findtext('language') or
            node.findtext('{http://purl.org/dc/elements/1.1/}language') or fallback)
