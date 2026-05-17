"""
Presentation-only template helpers — no business logic.

`strip_emoji` lets templates render the model `get_FOO_display()` strings
without the legacy emoji prefixes; the labels stay in the model so existing
data and admin filters remain stable, the UI just picks the clean text.
"""
from __future__ import annotations

import re

from django import template


register = template.Library()


# Covers the BMP emoji ranges we actually use in choice labels (food, meds,
# house, mosque, hospital, books, document, ring, etc.) plus any trailing
# whitespace. Intentionally narrow so unrelated unicode survives.
_EMOJI_RE = re.compile(
    r'^[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F1FF]+\s*'
)


@register.filter(name='strip_emoji')
def strip_emoji(value: str | None) -> str:
    if not value:
        return ''
    return _EMOJI_RE.sub('', str(value)).strip()
