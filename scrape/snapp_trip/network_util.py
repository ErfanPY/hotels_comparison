import logging
from urllib.parse import urlparse
from urllib.request import Request, quote, urlopen

from bs4 import BeautifulSoup


def get_content_make_soup(url:str, headers:dict={}, **kwargs) -> BeautifulSoup:
        
        page_content = get_content(url=url, headers=headers, **kwargs)
        
        if page_content == -1:
            return -1
        soup = BeautifulSoup(page_content, features="html.parser")
        
        return soup

def get_content(url:str, headers:dict={}) -> bytes:
    default_headers = {'User-Agent' : "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:87.0) Gecko/20100101 Firefox/87.0"}
    headers.update(default_headers)

    if not "%" in url:
        url_parts = urlparse(url)
        url = url_parts._replace(path=quote(url_parts.path)).geturl()
        
    try:
        req = Request(url, headers=headers)
    
        connection = urlopen(req)
        page_content = connection.read()
    except Exception as e:
        logging.error(f"Getting url failed, url: {url}, Error: {e}")
        return -1

    return page_content

