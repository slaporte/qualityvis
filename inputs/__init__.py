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

DEFAULT_INPUTS = [Backlinks, FeedbackV4, DOM, GoogleNews, GoogleSearch, Wikitrust, PageViews, Revisions, Assessment]
