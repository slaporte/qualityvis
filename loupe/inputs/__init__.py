from base import Input
from lib.wapiti import get_json, get_url  # TODO: necessary here?

from backlinks import Backlinks
from feedback import FeedbackV4
from feedback import FeedbackV5
from dom import DOM
from google import GoogleNews
from google import GoogleSearch
from wikitrust import Wikitrust
from grokse import PageViews
from revisions import Revisions
from langlinks import LangLinks
from interwikilinks import InterWikiLinks
from watchers import Watchers
from article_history import ArticleHistory
from protection import Protection

DEFAULT_INPUTS = [DOM, ArticleHistory, Protection]
