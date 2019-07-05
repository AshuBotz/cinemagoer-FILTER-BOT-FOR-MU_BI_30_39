# Copyright 2019 H. Turgut Uyar <uyar@tekir.org>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

"""
This module provides the classes (and the instances) that are used to parse
the results of an advanced search for a given title.

For example, when searching for the title "the passion", the parsed page
would be:

http://www.imdb.com/search/title/?title=the+passion
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import re

from .piculet import Path, Rule, Rules, preprocessors, reducers
from .utils import DOMParserBase, analyze_imdbid


_re_secondary_info = re.compile(
    r'''(\(([IVXLCM]+)\)\s+)?\((\d{4})(–(\s|(\d{4})))?(\s+(.*))?\)'''
)


_KIND_MAP = {
    'tv short': 'tv short movie',
    'video': 'video movie'
}


def _parse_secondary_info(info):
    parsed = {}
    match = _re_secondary_info.match(info)
    kind = None
    if match.group(2):
        parsed['imdbIndex'] = match.group(2)
    if match.group(3):
        parsed['year'] = int(match.group(3))
    if match.group(4):
        kind = 'tv series'
    if match.group(6):
        parsed['end_year'] = int(match.group(6))
    if match.group(8):
        kind = match.group(8).lower()
    if kind is None:
        kind = 'movie'
    parsed['kind'] = _KIND_MAP.get(kind, kind)
    return parsed


class DOMHTMLSearchMovieAdvancedParser(DOMParserBase):
    """A parser for the title search page."""

    rules = [
        Rule(
            key='data',
            extractor=Rules(
                foreach='//div[@class="lister-item-content"]',
                rules=[
                    Rule(
                        key='link',
                        extractor=Path('./h3/a/@href', reduce=reducers.first)
                    ),
                    Rule(
                        key='title',
                        extractor=Path('./h3/a/text()', reduce=reducers.first)
                    ),
                    Rule(
                        key='secondary_info',
                        extractor=Path('./h3/span[@class="lister-item-year text-muted unbold"]/text()',
                                       reduce=reducers.first)
                    ),
                    Rule(
                        key='state',
                        extractor=Path('.//b/text()', reduce=reducers.first)
                    ),
                    Rule(
                        key='certificates',
                        extractor=Path('.//span[@class="certificate"]/text()',
                                       reduce=reducers.first,
                                       transform=list)
                    ),
                    Rule(
                        key='runtimes',
                        extractor=Path('.//span[@class="runtime"]/text()',
                                       reduce=reducers.first,
                                       transform=lambda s: [[w for w in s.split() if w.isdigit()][0]])
                    ),
                    Rule(
                        key='genres',
                        extractor=Path('.//span[@class="genre"]/text()',
                                       reduce=reducers.first,
                                       transform=lambda s: [w.strip() for w in s.split(',')])
                    ),
                    Rule(
                        key='cover url',
                        extractor=Path('..//a/img/@loadlate')
                    )
                ],
                transform=lambda x: (analyze_imdbid(x.pop('link')), x)
            )
        )
    ]

    def _init(self):
        self.url = ''

    def _reset(self):
        self.url = ''

    preprocessors = [
        ('Directors?:(.*?)(<span|</p>)', '<div class="DIRECTORS">\1</div>\2'),
        ('Stars?:(.*?)(<span|</p>)', '<div class="STARS">\1</div>\2'),
        ('(Gross:.*?<span name=)"nv"', '\1"GROSS"'),
        ('Add a Plot', '<br class="ADD_A_PLOT"/>'),
        ('(Episode:)(</small>)(.*?)(</h3>)', '\1\3\2\4')
    ]

    def preprocess_dom(self, dom):
        preprocessors.remove(dom, '//br[@class="ADD_A_PLOT"]/../..')
        return dom

    def postprocess_data(self, data):
        if 'data' not in data:
            data['data'] = []
        results = getattr(self, 'results', None)
        if results is not None:
            data['data'][:] = data['data'][:results]

        for movieID, movie in data['data']:
            secondary_info = movie.pop('secondary_info', None)
            if secondary_info is not None:
                secondary = _parse_secondary_info(secondary_info)
                movie.update(secondary)

        return data

    def add_refs(self, data):
        return data


_OBJECTS = {
    'search_movie_advanced_parser': ((DOMHTMLSearchMovieAdvancedParser,), None)
}
