from . import Input
import wapiti
from pyquery import PyQuery
import pdb

from stats import dist_stats


def word_count(element):
    return len(element.text_content().split())


def paragraph_counts(pq):
    wcs = [word_count(x) for x in pq('p')]
    return [x for x in wcs if x > 0]


def section_stats(headers):
    hs = (h for h in headers if h.text_content() != 'Contents')
    all_headers = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'h7']
    totals = []
    for header in hs:
        if header.getnext() is not None:
            pos = header.getnext()
            text = ''
            while pos.tag not in all_headers:
                text += ' ' + pos.text_content()
                if pos.getnext() is not None:
                    pos = pos.getnext()
                else:
                    break
            totals.append((header.text_content().replace('[edit] ', ''), len(text.split())))
    return totals


def pq_contains(elem, search):
    """Just a quick factory function to create lambdas to do xpath in a cross-version way"""
    return lambda f: len(f.root.xpath(u'{e}[contains("{s}")]'.format(e=elem, s=search)))


class DOM(Input):
    def fetch(self):
        page = wapiti.get_articles(self.page_id)[0]
        text = page.rev_text
        return PyQuery(text)

    stats = {
        'word_count':       lambda f: len(f('p').text().split()),
        'p_dist':           lambda f: dist_stats(paragraph_counts(f)),
        'reference_count':  lambda f: len(f('.reference')),
        'source_count':     lambda f: len(f('li[id^="cite_note"]')),
        'reference_section_count': lambda f: len(f('#References')),
        'external_links_section_count': lambda f:  len(f('#External_links')),
        'intro_p_count': lambda f: len(f('#toc').prevAll('p')),
        'new_internal_links_count': lambda f: len(f('.new')),
        'infobox_count': lambda f: len(f('.infobox')),
        'footnotes_in_section': lambda f: len(f('#Footnotes').parent().nextAll('div').children('ul').children('li')),
        'external_links_in_section': lambda f: len(f('#External_links').parent().nextAll('ul').children()),
        'see_also_links_in_section': lambda f: len(f('#See_also').parent().nextAll('ul').children()),
        'external_links_total_count': lambda f: len(f('.external')),
        'links_count':      lambda f: len([text.text_content() for text in f('p a:not([class])[href^="/wiki/"]')]),
        'dom_internal_link_count': lambda f: len(f('p a:not([class])[href^="/wiki/"]')),
        'ref_needed_count': pq_contains('span', 'citation'),
        'pov_statement_count': pq_contains('span', 'neutrality'),
        'dom_category_count': lambda f: len(f("a[href^='/wiki/Category:']")),
        'image_count': lambda f: len(f('img')),
        'ogg': lambda f: len(f("a[href$='ogg']")),
        'mid': lambda f: len(f("a[href$='mid']")),
        'geo': lambda f: len(f('.geo-dms')),
        'templ_delete': lambda f: len(f('.ambox-delete')),
        'templ_autobiography': lambda f: len(f('.ambox-autobiography')),
        'templ_advert': lambda f: len(f('.ambox-Advert')),
        'templ_citation_style': lambda f: len(f('.ambox-citation_style')),
        'templ_cleanup': lambda f: len(f('.ambox-Cleanup')),
        'templ_COI': lambda f: len(f('.ambox-COI')),
        'templ_confusing': lambda f: len(f('.ambox-confusing')),
        'templ_context': lambda f: len(f('.ambox-Context')),
        'templ_copy_edit': lambda f: len(f('.ambox-Copy_edit')),
        'templ_dead_end': lambda f: len(f('.ambox-dead_end')),
        'templ_disputed': lambda f: len(f('.ambox-disputed')),
        'templ_essay_like': lambda f: len(f('.ambox-essay-like')),
        'templ_expert': pq_contains('td', 'needs attention from an expert'),
        'templ_fansight': pq_contains('td', 's point of view'),
        'templ_globalize': pq_contains('td', 'do not represent a worldwide view'),
        'templ_hoax': pq_contains('td', 'hoax'),
        'templ_in_universe': lambda f: len(f('.ambox-in-universe')),
        'templ_intro_rewrite': lambda f: len(f('.ambox-lead_rewrite')),
        'templ_merge': pq_contains('td', 'suggested that this article or section be merged'),
        'templ_no_footnotes': lambda f: len(f('.ambox-No_footnotes')),
        'templ_howto': pq_contains('td', 'contains instructions, advice, or how-to content'),
        'templ_non_free': lambda f: len(f('.ambox-non-free')),
        'templ_notability': lambda f: len(f('.ambox-Notability')),
        'templ_not_english': lambda f: len(f('.ambox-not_English')),
        'templ_NPOV': lambda f: len(f('.ambox-POV')),
        'templ_original_research': lambda f: len(f('.ambox-Original_research')),
        'templ_orphan': lambda f: len(f('.ambox-Orphan')),
        'templ_plot': lambda f: len(f('.ambox-Plot')),
        'templ_primary_sources': lambda f: len(f('.ambox-Primary_sources')),
        'templ_prose': lambda f: len(f('.ambox-Prose')),
        'templ_refimprove': lambda f: len(f('.ambox-Refimprove')),
        'templ_sections': lambda f: len(f('.ambox-sections')),
        'templ_tone': lambda f: len(f('.ambox-Tone')),
        'templ_tooshort': lambda f: len(f('.ambox-lead_too_short')),
        'templ_style': lambda f: len(f('.ambox-style')),
        'templ_uncategorized': lambda f: len(f('.ambox-uncategorized')),
        'templ_update': lambda f: len(f('.ambox-Update')),
        'templ_wikify': lambda f: len(f('.ambox-Wikify')),
        'templ_multiple_issues': lambda f: len(f('.ambox-multiple_issues li')),
        'h2': lambda f: section_stats(f('h2')),
        'h3': lambda f: section_stats(f('h3')),
        'h4': lambda f: section_stats(f('h4')),
        'h5': lambda f: section_stats(f('h5')),
    }
