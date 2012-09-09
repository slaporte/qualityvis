import json
import codecs


def load_results(file_name):
    return [json.loads(line.strip()) for line in codecs.open(file_name)]
