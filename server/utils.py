from urllib.parse import urlparse

def url_parser(url):
    o = urlparse(url)
    return o.scheme, o.netloc, o.path

def is_same_domain(url1, url2):
    _, domain1, _ = url_parser(url1)
    _, domain2, _ = url_parser(url2)
    return domain1 == domain2
