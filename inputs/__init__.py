from base import Input, get_json, get_url

from backlinks import Backlinks
from feedback import FeedbackV4
from dom import DOM
from google import GoogleNews
from google import GoogleSearch
from wikitrust import Wikitrust
from grokse import PageViews
from revisions import Revisions
from assessment import Assessment
from langlinks import LangLinks
from interwikilinks import InterWikiLinks
from watchers import Watchers

DEFAULT_INPUTS = [Backlinks, LangLinks, InterWikiLinks, FeedbackV4, DOM, GoogleNews, GoogleSearch, Wikitrust, PageViews, Revisions, Assessment, Watchers]
