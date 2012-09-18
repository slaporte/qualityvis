from base import Input
from collections import namedtuple
import wapiti
import datetime


class Protection(Input):
    prefix = 'pr'

    def fetch(self):
        resp = wapiti.get_protection(self.page_title)
        return resp

    def process(self, f_res):
        proc = wapiti.Permissions(f_res)
        return super(Protection, self).process(proc)

    stats = {
        'any': lambda f_res: f_res.has_protection,
        'indef': lambda f_res: f_res.has_indef,
        'full': lambda f_res: f_res.is_full_prot,
        'semi': lambda f_res: f_res.is_semi_prot,
    }
