"""Rich text shared by blog posts and product descriptions.

render_body() turns stored HTML into what readers see:

1. Sanitize again with the editor's allowlist (defence in depth: covers posts saved outside the admin).
2. Replace paragraphs that contain only a YouTube/Vimeo link with a privacy-friendly embed.
3. Give h2/h3 headings ids and build a table of contents.
"""

import re
from dataclasses import dataclass, field
from functools import lru_cache

from django.utils.html import escape, strip_tags
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django_prose_editor.fields import create_sanitizer


# Rich-text editor features. The same list drives server-side sanitization (nh3),
# so editors can only save the HTML these extensions produce.
RICH_TEXT = {
    "extensions": {
        "Bold": True,
        "Italic": True,
        "Underline": True,
        "Strike": True,
        "Code": True,
        "Heading": {"levels": [2, 3, 4]},
        "BulletList": True,
        "OrderedList": True,
        "ListItem": True,
        "Blockquote": True,
        "HorizontalRule": True,
        "Link": {"enableTarget": True},
        "CodeBlock": True,
        "Table": True,
        "TableRow": True,
        "TableHeader": True,
        "TableCell": True,
        "Image": True,
        "Figure": True,
        "Caption": True,
        "Typographic": True,
    }
}


YOUTUBE = re.compile(r"^https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]{6,})")
VIMEO = re.compile(r"^https?://(?:www\.)?vimeo\.com/(\d+)")
LONE_LINK = re.compile(
    r"<p>\s*(?:<a [^>]*href=\"([^\"]+)\"[^>]*>[^<]*</a>|(https?://[^\s<]+))\s*</p>", re.IGNORECASE
)
HEADING = re.compile(r"<(h[23])(?: [^>]*)?>(.*?)</\1>", re.IGNORECASE | re.DOTALL)


@lru_cache(maxsize=1)
def _sanitizer():
    return create_sanitizer(RICH_TEXT["extensions"])


def _embed(match):
    url = match.group(1) or match.group(2)
    if m := YOUTUBE.match(url):
        src = f"https://www.youtube-nocookie.com/embed/{m.group(1)}"
    elif m := VIMEO.match(url):
        src = f"https://player.vimeo.com/video/{m.group(1)}?dnt=1"
    else:
        return match.group(0)
    return (
        '<div class="not-prose my-8 aspect-video overflow-hidden rounded-md border border-slate-200">'
        f'<iframe src="{escape(src)}" class="h-full w-full" title="Embedded video" loading="lazy" '
        'allow="fullscreen; picture-in-picture" referrerpolicy="strict-origin-when-cross-origin"></iframe></div>'
    )


@dataclass
class RenderedBody:
    html: str
    toc: list = field(default_factory=list)  # [(level, id, text)]


def render_body(raw):
    html = _sanitizer()(raw or "")
    html = LONE_LINK.sub(_embed, html)
    toc, used = [], set()

    def add_id(m):
        tag, inner = m.group(1).lower(), m.group(2)
        text = strip_tags(inner).strip()
        base = slugify(text)[:60] or "section"
        anchor, n = base, 2
        while anchor in used:
            anchor, n = f"{base}-{n}", n + 1
        used.add(anchor)
        toc.append((int(tag[1]), anchor, text))
        return f'<{tag} id="{anchor}">{inner}</{tag}>'

    html = HEADING.sub(add_id, html)
    return RenderedBody(mark_safe(html), toc)
