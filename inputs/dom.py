from base import Input
from wapiti import get_url
import wapiti
from pyquery import PyQuery

from stats import dist_stats


def word_count(element):
    return len(element.text_content().split())


def paragraph_counts(pq):
    wcs = [word_count(x) for x in pq('p')]
    return [x for x in wcs if x > 0]


def section_stats(headers):
    hs = [h for h in headers if h.text_content() != 'Contents']
    # how not to write Python: ['h'+str(i) for i in range(1, 8)]
    all_headers = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'h7']
    totals = []
    for header in hs:
        if header.getnext() is not None:  # TODO: the next item after an h1 is #bodyContents div
            pos = header.getnext()
            text = ''
            while pos.tag not in all_headers:
                text += ' ' + pos.text_content()  # TODO: the references section may skew the no. words under an h2
                if pos.getnext() is not None:
                    pos = pos.getnext()
                else:
                    break
            totals.append((header.text_content().replace('[edit] ', ''), len(text.split())))
    dists = {}
    dists['header'] = dist_stats([len(header.split()) for header, t in totals])
    dists['text'] = dist_stats([text for h, text in totals])
    return dists


def get_sections(pq):
    dist = {}
    depth = {}
    total_words = 0
    headers = ['h2', 'h3', 'h4', 'h5', 'h6', 'h7']  
    for header in headers:
        sec_stats = section_stats(pq(header))
        if sec_stats['header']['count'] > 0:
            dist[header] = sec_stats
            words = sec_stats['text']['count'] * sec_stats['text']['mean']
            total_words += words
            depth[header] = words
    if total_words > 0:
        for header in depth.keys():
            depth[header] = depth[header] / total_words
    return {'dist': dist, 'depth': depth}


def element_words_dist(elem):
    return lambda f: dist_stats([len(navbox.text_content().split()) for navbox in f(elem)])


def get_root(pq):
    try:
        roottree = pq.root  # for pyquery on lxml 2
    except AttributeError:
        roottree = pq[0].getroottree()  # for lxml 3
    return roottree

def pq_contains(elem, search):
    """Just a quick factory function to create lambdas to do xpath in a cross-version way"""
    def xpath_search(f):
        if not f:
            return 0
        else:
            roottree = get_root(f)
            return len(roottree.xpath(u'//{e}[contains(., "{s}")]'.format(e=elem, s=search)))
    return xpath_search


def per_word(feature, f):
        words = float(len(f('p').text().split()))
        if words > 0:
            return len(f(feature)) / words
        else:
            return 0


class DOM(Input):
    prefix = 'd'

    def api_fetch(self):
        """
        Deprecated fetch() that gets parsed content from the API.
        The API doesn't cache parsed wikitext, and can be up to 10x slower
        depending on page complexity.
        """
        page = wapiti.get_articles(self.page_id)[0]
        pq = PyQuery(page.rev_text)
        return pq

    def fetch(self):
        # avg process time: 0.14827052116394043 seconds
        ret = get_url('http://en.wikipedia.org/wiki/' + self.page_title.replace(' ', '_'))
        return ret

    def process(self, f_res):
        ret = PyQuery(f_res.text).find('div#content')
        ret('div#siteNotice').remove()
        return super(DOM, self).process(ret)

    # TODO: check pyquery errors
    stats = {
        # General page/page structure stats
        'word_count': lambda f: len(f('p').text().split()),
        'p': lambda f: dist_stats(paragraph_counts(f)),

        # Key stats relative to word count
        'img_per_w': lambda f:  per_word('.image', f),
        'cite_per_w': lambda f: per_word('li[id^="cite_note"]', f),
        'int_link_per_w': lambda f: per_word('p a[href^="/wiki/"]', f),
        'red_link_per_w': lambda f: per_word('.new', f),
        'ext_link_per_w': lambda f: per_word('.external', f),

        # Section-based page structure stats
        's': lambda f: get_sections(f),
        'refbegin_count': lambda f: len(f('div.refbegin')),
        'reflist_count': lambda f: len(f('div.reflist')),
        'ref_text_count': lambda f: len(f('.reference-text')),
        'bold_terms_in_first_p': lambda f: len(f('p:first b')),
        'has_ext_link_sect': lambda f:  len(f('#External_links')),
        'ext_link_sect_li_count': lambda f: len(f('#External_links').parent().nextAll('ul').children()),
        'see_also_sect_li_count': lambda f: len(f('#See_also').parent().nextAll('ul').children()),
        'has_ref_sect': lambda f: len(f('#References')),
        'has_notes_sect': lambda f: len(f('#Notes')),
        'fr_sect_count': lambda f: len(f('#Further_reading')),
        
        # Lead stats; the introductory area before the TOC
        'lead_p_count': lambda f: len(f('#toc').prevAll('p')),
        
        # Hatnotes
        'hn_rellink_count': lambda f: len(f('div.rellink')), # "See also" link for a section
        'hn_dablink_count': lambda f: len(f('div.dablink')), # Disambiguation page links
        'hn_mainlink_count': lambda f: len(f('div.mainarticle')), # Link to main, expanded article
        'hn_seealso_count': lambda f: len(f('div.seealso')), # Generic see also
        'hn_relarticle_count': lambda f: len(f('div.relarticle')), # somehow distinct from rellink
        
        # Inline/link-based stats
        'ref_count': lambda f: len(f('sup.reference')),
        'cite_count': lambda f: len(f('li[id^="cite_note"]')),
        'red_link_count': lambda f: len(f('.new')), # New internal links, aka "red links"
        'ext_link_count': lambda f: len(f('.external')),
        'int_link_text': lambda f: dist_stats([ len(text.text_content()) for text in f('p a[href^="/wiki/"]')]),
        'dead_link_count': lambda f: len(f('a[title^="Wikipedia:Link rot"]')),
        'ref_needed_span_count': pq_contains('span', 'citation'),
        'pov_span_count': pq_contains('span', 'neutrality'),

        # DOM-based category stats, not to be confused with the API-based Input
        'cat_count': lambda f: len(f("#mw-normal-catlinks ul li")),
        'hidden_cat_count': lambda f: len(f('#mw-hidden-catlinks ul li')),
        
        # Media/page richness stats
        'wiki_file_link_count': lambda f: len(f("a[href*='/wiki/File:']")),
        'ipa_count': lambda f: len(f('span[title="pronunciation:"]')),
        'all_img_count': lambda f: len(f('img')),
        'thumb_img_count': lambda f: len(f('div.thumb')),
        'thumb_left_count': lambda f: len(f('div.tleft')),
        'thumb_right_count': lambda f: len(f('div.tright')),
        'image_map_count': lambda f: len(f('map')), # The clickable image construct (EasyTimeline)
        'tex_count': lambda f: len(f('.tex')), # LaTeX/TeX used by mathy things
        'infobox_count': lambda f: len(f('.infobox')),
        'navbox_word': element_words_dist('.navbox'),
        'caption_word': element_words_dist('.thumbcaption'),
        'ogg_count': lambda f: len(f("a[href$='.ogg']")),
        'svg_count': lambda f: len(f("img[src*='.svg']")),
        'pdf_count': lambda f: len(f("a[href$='.pdf']")),
        'midi_count': lambda f: len(f("a[href$='.mid']")),
        'geo_count': lambda f: len(f('.geo-dms')),
        'blockquote_count': lambda f: len(f('blockquote')),
        'metadata_link_count': lambda f: len(f('.metadata.plainlinks')),  # Commons related media
        'spoken_wp_count': lambda f: len(f('#section_SpokenWikipedia')),
        'wikitable_word': element_words_dist('table.wikitable'),
        'gallery_li_count': lambda f: len(f('.gallery').children('li')),
        'unicode_count': lambda f: len(f('.unicode, .Unicode')),

        # Template inspection, mostly fault detection
        'tmpl_general': lambda f: len(f('.ambox')),
        'tmpl_delete': lambda f: len(f('.ambox-delete')),
        'tmpl_autobiography': lambda f: len(f('.ambox-autobiography')),
        'tmpl_advert': lambda f: len(f('.ambox-Advert')),
        'tmpl_citation_style': lambda f: len(f('.ambox-citation_style')),
        'tmpl_cleanup': lambda f: len(f('.ambox-Cleanup')),
        'tmpl_COI': lambda f: len(f('.ambox-COI')),
        'tmpl_confusing': lambda f: len(f('.ambox-confusing')),
        'tmpl_context': lambda f: len(f('.ambox-Context')),
        'tmpl_copy_edit': lambda f: len(f('.ambox-Copy_edit')),
        'tmpl_dead_end': lambda f: len(f('.ambox-dead_end')),
        'tmpl_disputed': lambda f: len(f('.ambox-disputed')),
        'tmpl_essay_like': lambda f: len(f('.ambox-essay-like')),
        'tmpl_expert': pq_contains('td', 'needs attention from an expert'),
        'tmpl_fansight': pq_contains('td', 's point of view'),
        'tmpl_globalize': pq_contains('td', 'do not represent a worldwide view'),
        'tmpl_hoax': pq_contains('td', 'hoax'),
        'tmpl_in_universe': lambda f: len(f('.ambox-in-universe')),
        'tmpl_intro_rewrite': lambda f: len(f('.ambox-lead_rewrite')),
        'tmpl_merge': pq_contains('td', 'suggested that this article or section be merged'),
        'tmpl_no_footnotes': lambda f: len(f('.ambox-No_footnotes')),
        'tmpl_howto': pq_contains('td', 'contains instructions, advice, or how-to content'),
        'tmpl_non_free': lambda f: len(f('.ambox-non-free')),
        'tmpl_notability': lambda f: len(f('.ambox-Notability')),
        'tmpl_not_english': lambda f: len(f('.ambox-not_English')),
        'tmpl_NPOV': lambda f: len(f('.ambox-POV')),
        'tmpl_original_research': lambda f: len(f('.ambox-Original_research')),
        'tmpl_orphan': lambda f: len(f('.ambox-Orphan')),
        'tmpl_plot': lambda f: len(f('.ambox-Plot')),
        'tmpl_primary_sources': lambda f: len(f('.ambox-Primary_sources')),
        'tmpl_prose': lambda f: len(f('.ambox-Prose')),
        'tmpl_refimprove': lambda f: len(f('.ambox-Refimprove')),
        'tmpl_sections': lambda f: len(f('.ambox-sections')),
        'tmpl_tone': lambda f: len(f('.ambox-Tone')),
        'tmpl_tooshort': lambda f: len(f('.ambox-lead_too_short')),
        'tmpl_style': lambda f: len(f('.ambox-style')),
        'tmpl_uncategorized': lambda f: len(f('.ambox-uncategorized')),
        'tmpl_update': lambda f: len(f('.ambox-Update')),
        'tmpl_wikify': lambda f: len(f('.ambox-Wikify')),
        'tmpl_multiple_issues': lambda f: len(f('.ambox-multiple_issues li')),

        # Citation type statistics
        'cite_cl': lambda f: len(f('.citation')), # not to be confused with cite_count
        'cite_journal': lambda f: len(f('.citation.Journal')),
        'cite_web': lambda f: len(f('.citation.web')),
        'cite_news': lambda f: len(f('.citation.news')),
        'cite_episode': lambda f: len(f('.citation.episode')),
        'cite_newsgroup': lambda f: len(f('.citation.newgroup')),
        'cite_patent': lambda f: len(f('.citation.patent')),
        'cite_pressrelease': lambda f: len(f('.citation.pressrelease')),
        'cite_report': lambda f: len(f('.citation.report')),
        'cite_video': lambda f: len(f('.citation.video')),
        'cite_videogame': lambda f: len(f('.citation.videogame')),
        'cite_book': lambda f: len(f('.citation.book')),
    }
