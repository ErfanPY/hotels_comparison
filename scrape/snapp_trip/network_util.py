import logging
from urllib.parse import urlparse
from urllib.request import Request, quote, urlopen
from time import sleep

from bs4 import BeautifulSoup
from scrape.critical_log import log_critical_error

logger = logging.getLogger("main_logger")


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
    
    sleep_time = 1
    while True:    
        try:
            req = Request(url, headers=headers)
        
            connection = urlopen(req)
            page_content = connection.read()
            return page_content

        except Exception as e:
            logger.error(f"Getting url failed, url: {url}, Error: {e}")
            if sleep_time >= 120:
                log_critical_error(f"Snapptrip unhandleable network error. (url: {url})")
                return -1

        sleep(sleep_time)
        sleep_time *= 2
