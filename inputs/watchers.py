from base import Input, get_json

class Watchers(Input):
    def fetch(self):
    	result = get_json('http://ortelius.toolserver.org:8089/wl?title=' + self.page_title.replace(' ', '_'))
        return result.get('watchers')

    stats = {
        'watchers': lambda f_res: f_res,
    }
