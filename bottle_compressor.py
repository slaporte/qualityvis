# -*- coding: utf-8 -*-

"""
    Output compression plugin for bottle applications

    This plugin compresses output to the client with two encoding
    type options: gzip and deflate. It first checks the request headers
    to decide which encoding type to use. The gzip is the preferred
    encoding method. If the client support neither, it immediately
    ignores. This plugin only compresses contents of user-defined mime
    types. The default mime types are:
    ['text/plain', 'text/html', 'text/css', 'application/json',
     'application/x-javascript', 'text/xml', 'application/xml',
     'application/xml+rss', 'text/javascript'].

    WARNING: This plugin only supports dynamicly generated content.
             It doesn't work with staic_file method. In this case,
             you should put the plugin into the 'skip' argument and
             so the plugin does not apply to the route.

    parameters:
        content_types: the mime types to compress, if not set, use the default
        compress_level: which level of gzip compression to use, from 0 to 9.
                        6 is default. The deflate method will not use it.
        minimal_size: the minimal size to compress
                        smaller will be not compressed, default is 200b

    Example of use:

    import bottle
    from compressor import CompressorPlugin

    compressor_plugin = CompressorPlugin()
	bottle.install(compressor_plugin)

    @get('/text')
    def text():
        return 'Hello World!'

    # the encoding_plugin will not apply to the route
    @get('/image', skip=[compressor_plugin])
    def image():
        return static_file('test.jpg', root='./view')

"""


from gzip import GzipFile
import cStringIO
import zlib
from bottle import request, response, HTTPResponse


__author__ =  'Li Gang, Roy Shan'
__version__=  '0.1'
__email__  =  'ligang at ibkon.com, roy at ibkon.com'


# encoding type enum
Gzip_Encoding, Deflate_Encoding = range(1, 3)


def compress(data, compression_level):
    """
    Compress data with gzip encoding
    
    Keyword arguments:
    data -- data to be compressed
    compression_level -- which level of gzip compression to use, from 0 to 9
    """
    buffer = cStringIO.StringIO()
    gz_file = GzipFile(None, 'wb', compression_level, buffer)
    if isinstance(data, unicode): 
        data = data.encode(response.charset)
    gz_file.write(data)
    gz_file.close()
    return buffer.getvalue()


def parse_encoding_header(header):
    """
    Break up the `HTTP_ACCEPT_ENCODING` header into a dict of
    the form, {'encoding-name':qvalue}. if qvalue <= 0, the
    encoding-name is not put inot the dict.

    Keyword arguments:
    header -- HTTP_ACCEPT_ENCODING header
    """ 
    encodings = {}
    for encoding in header.split(','):
        if encoding.find(';') > -1:
            encoding, qvalue = encoding.split(';')
            encoding = encoding.strip()
            qvalue = qvalue.split('=', 1)[1]
            if qvalue != '':
                if float(qvalue) > 0:
                    encodings[encoding] = float(qvalue)
            else:
                encodings[encoding] = 1
        else:
            encodings[encoding] = 1
    return encodings


def client_wants_encoding(accept_encoding_header):
    """
    Check the encoding type that the client can accept

    Keyword arguments:
    accept_encoding_header -- a dict for accept encoding info
    """
    encodings = parse_encoding_header(accept_encoding_header)

    gzip_value = encodings.get('gzip', 0)
    deflate_value = encodings.get('deflate', 0)
    if gzip_value or deflate_value:
        if deflate_value > gzip_value:
            return Deflate_Encoding
        else:
            return Gzip_Encoding
    elif '*' in encodings:
        return Gzip_Encoding
    else:
        return None


DEFAULT_COMPRESSABLES = set(['text/plain', 'text/html', 'text/css',
'application/json', 'application/x-javascript', 'text/xml',
'application/xml', 'application/xml+rss', 'text/javascript'])
        

class CompressorPlugin(object):
    """
    Bottle plugin for compressing content
    """
    name = 'compressor_plugin'
    api = 2

    def __init__(self, content_types=DEFAULT_COMPRESSABLES, compress_level=6,\
                    minimal_size=200):
        """
        Initialize attribute values

        Keyword arguments:
        content_types  -- set the content types to be compressed
        compress_level -- set the gzip compress level
        minimal_size   -- set the min size to be compressed
        """
        self.content_types = content_types
        self.compress_level = compress_level
        self.minimal_size = minimal_size


    def apply(self, callback, route):
        """
        Decorate route callback

        keyword arguments:
        callback -- the route callback to be decorated
        context  -- an instance of Route and provides a lot of meta-information
                    and context for that route 
        """
        content_types = self.content_types
        compress_level = self.compress_level
        minimal_size = self.minimal_size 

        def wrapper(*args, **kwargs):
            """
            The decorated route callback
            """
            data = callback(*args, **kwargs)

            # ignore empty data
            if not data or not isinstance(data, (str, unicode)):
                return data

            # ignore redirect
            if response.status_code >= 300 and response.status_code < 400:
                return data
            
            # ignore encoded data
            if 'Content-Encoding' in response.headers:
                return data

            # ignore non-compressable types
            content_type = response.headers.get('Content-Type')
            ctype = content_type.split(';')[0]
            if ctype not in content_types:
                return data

            # ie bug
            user_agent = request.headers.get('User-Agent')
            if user_agent and 'msie' in user_agent.lower() \
                and 'javascript' in ctype:
                return data

            accept_encoding = request.headers.get('Accept-Encoding')
            encoding_type = client_wants_encoding(accept_encoding) \
                if accept_encoding else None 

            if encoding_type:
                data = ''.join(data)
                # data size smaller than minimal_size
                if len(data) < minimal_size:
                    return [data]
                if encoding_type == Gzip_Encoding:
                    data = compress(data, compress_level)
                    response.headers.append('Content-Encoding', 'gzip')
                else:
                    data = zlib.compress(data)
                    response.headers.append('Content-Encoding', 'deflate')
                response.headers.append('Vary', 'Accept-Encoding')
                response.headers.replace('Content-Length', str(len(data)))
                data = [data]
            return data

        return wrapper
