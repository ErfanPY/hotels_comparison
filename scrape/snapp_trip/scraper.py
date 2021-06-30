import json
import logging
import queue
import re
import socket
import sys
import time
from datetime import datetime, timedelta
from urllib.parse import urljoin

import socks
from bs4 import BeautifulSoup
from scrape.db_util import get_db_connection, insert_select_id

from .network_util import get_content, get_content_make_soup, urlparse

logger = logging.getLogger(__name__)

en_cities = {
    'تهران':
    'tehran',
    'شیراز':
    'shiraz',
    'مشهد':
    'mashhad',
    'تبریز':
    'tabriz',
    'اصفهان':
    'isfahan',
    'کیش':
    'kish',
}


def main(sleep_time:int, proxy_host:str, proxy_port:int):
    socks.set_default_proxy(proxy_host, proxy_port)
    if not proxy_host is None:
        socket.socket = socks.socksocket

    BASE_URL = 'https://www.snapptrip.com/'
    BASE_CITIES_URL = {
        'tehran': 'https://www.snapptrip.com/رزرو-هتل/تهران',
        'mashhad': "https://www.snapptrip.com/رزرو-هتل/مشهد",
        'shiraz': 'https://www.snapptrip.com/رزرو-هتل/شیراز',
        'isfahan': 'https://www.snapptrip.com/رزرو-هتل/اصفهان',
        'tabriz': 'https://www.snapptrip.com/رزرو-هتل/تبریز',
        'kish': 'https://www.snapptrip.com/رزرو-هتل/کیش'
    }


    city_date_queue = queue.LifoQueue()

    for city_url in BASE_CITIES_URL.values():
        city_date_url = get_city_dated_url(city_url)
        city_date_queue.put(city_date_url)

    while city_date_queue.qsize() > 0:
        to_scrape_url = city_date_queue.get()
        logger.info("Fetching hotels : {}".format(to_scrape_url))

        soup = get_content_make_soup(to_scrape_url)
        time.sleep(sleep_time)
        if soup == -1:
            logger.error("Getting search page failed: url: {}".format(to_scrape_url))
            continue

        hotels = soup.select_one(
            ".hotels-data").findAll("li", {'data-hotel-id': True})

        for hotel in hotels:
            if "ظرفیت تکمیل" in hotel:
                # log
                break

            hotel_site_id = hotel.contents[3].attrs['data-id']

            hotel_url = hotel.select_one(
                '#resultpage-hotelcard-cta').get('href')
            hotel_url = urljoin(BASE_URL, hotel_url)

            scrape_hotel(hotel_url, hotel_site_id)
            time.sleep(sleep_time)

        city_date_queue.task_done()
        time.sleep(sleep_time)

        next_page_div = soup.select_one('.pagination-next')
        if not next_page_div is None:
            next_page_url = next_page_div.select_one('a').get('href')
            if next_page_url is None or next_page_url == "" or next_page_url == "/":
                return
            next_page_url = urljoin(BASE_URL, next_page_url)
        else:
            return

        city_date_queue.put(next_page_url)


def scrape_hotel(hotel_url: str, hotel_site_id: str) -> None:
    """Gets and saves hotel then cals scrape_hotel_rooms

    Args:
        hotel_url (str): A url points to the hotel page.
        hotel_site_id (str): ID of hotel on snapptrip site.

    Returns:
        None
    """

    city = hotel_url.split("/")[4]
    hotel_name = hotel_url.split("/")[5].split("?")[0]
    hotel_name = hotel_name
    logger.info("Scape Hotel {} - {}".format(city, hotel_name))
    with get_db_connection() as conn:
        hotel_id = insert_select_id(
            table='tblHotels',
            key_value={
                "htlFaName": hotel_name,
                "htlEnName": "",
                "htlCity": en_cities[city],
                "htlUrl": hotel_url,
                "htlFrom": 'S'
            },
            id_field='htlID',
            identifier_condition={
                "htlFaName": hotel_name
            },
            conn=conn
        )

    hotel_soup = get_content_make_soup(hotel_url)

    if hotel_soup == -1:
        logger.error("Getting hotel content failed: url: {}".format(hotel_url))
        return

    scrape_hotel_rooms(hotel_soup, hotel_id, hotel_site_id,)


def get_city_dated_url(city_url: str, day_offset: int = 0) -> str:
    """
        Makes city hotels search url,
        Calculates date range start today + day_offset and end to next day.

    Args:
        city_url (str): A url points to the A city hotels search page.
        day_offset (int): Days passed from today.
            (default is 0)

    Returns:
        str: A dated Url of city hotels search. 
    """

    today_date = datetime.now() + timedelta(days=day_offset)
    tomorrow_date = today_date + timedelta(days=1)

    date_from = today_date.strftime("%Y-%m-%d")
    date_to = tomorrow_date.strftime("%Y-%m-%d")

    parse_url = urlparse(city_url)
    parse_url = parse_url._replace(
        query="date_from={}&date_to={}".format(date_from, date_to))

    dated_url = parse_url.geturl()
    return dated_url


def scrape_hotel_rooms(hotel_soup: BeautifulSoup, hotel_id: int, hotel_site_id: str) -> None:
    """Iterats on hotel room and save room and date to database.

    Args:
        hotel_soup (BeautifulSoup): A BeautifulSoup contains hotel webpage.
        hotel_id (int): Hotel ID on our databse.
        hotel_site_id (str): hote ID on snapptrip site.

    Returns:
        None
    """
    rooms_div = hotel_soup.select_one("div.position-relative")
    rooms = rooms_div.select(".room-item")

    today = datetime.strftime(datetime.today(), '%Y-%m-%d')

    with get_db_connection() as conn:

        for room in rooms:
            room_site_id = room.contents[3].attrs['data-room_id']
            room_name = room.contents[1].attrs['data-roomname']
            room_name = room_name

            room_id = insert_select_id(
                table='tblRooms',
                key_value={
                    "rom_htlID": hotel_id,
                    "romName": room_name,
                    "romType": get_room_types(room_name)
                },
                id_field='romID',
                identifier_condition={
                    "rom_htlID": hotel_id,
                    'romName': room_name
                },
                conn=conn
            )
            
            room_calender_content = get_content(
                "https://www.snapptrip.com/shopping/{}/calendar/{}".format(
                    hotel_site_id, room_site_id))

            if room_calender_content == -1:
                logger.error("getting hotel room failed, hotel_id: {}".format())
                return

            room_calender = json.loads(room_calender_content)

            for data in room_calender['data']:
                for day in data['calendar']:

                    insert_select_id(
                        table="tblAvailabilityInfo",
                        key_value={
                            "avl_romID": room_id,
                            "avlDate": day['date'],
                            "avlInsertionDate": today,
                            "avlBasePrice": day['prices']['local_price']*10,
                            "avlDiscountPrice": day['prices']['local_price_off']*10
                        },
                        id_field=None,
                        identifier_condition={},
                        conn=conn
                    )


def get_room_types(room_name: str) -> str:
    """Gets type of room by searching abbreviation keywoards on room name.

    Args:
        room_name (str): room name.

    Returns:
        str: room type
    """
    
    search_room_name = re.sub('\W+', '', room_name)

    types_abrv = {
        "یکتخته":
        'S',
        "یکخوابه":
        'S',
        "دوتخته":
        "D",
        "دوخوابه":
        "D",
        "سهتخته":
        'T',
        "سهخوابه":
        'T',
        'چهارتحته':
        'Q',
        'چهارخوابه':
        'Q',
        "تویین":
        "2",
        "دابل":
        "D",
    }

    for type_name, abrv in types_abrv.items():
        if type_name in search_room_name:
            return abrv

    return " "


if __name__ == "__main__":
    main()
    print("done")
