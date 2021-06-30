import logging
import re
import socket
import time
from datetime import datetime
from urllib.parse import urljoin

import socks
from scrape.db_util import get_db_connection, insert_select_id

from .network_utils import *



logger = logging.getLogger(__name__)

DB_PATH = "alibaba/data.db"
BASE_URL = "https://www.alibaba.ir/hotel/"
START_DAY_OFFSET = 3
END_DAY_OFFSET = START_DAY_OFFSET + 30 

city_ids = {
    'tehran': '5be3f68be9a116befc66704b',
    'mashhad': '5be3f68be9a116befc66701b',
    'shiraz': '5be3f68be9a116befc6669e6',
    'isfahan': '5be3f68be9a116befc6669e5',
    'tabriz': '5be3f68be9a116befc666b82',
    'kish': '5be3f68be9a116befc66704b',
}


def main(sleep_time:int, proxy_host:str, proxy_port:int):
    socks.set_default_proxy(proxy_host, proxy_port)
    if not proxy_host is None:
        socket.socket = socks.socksocket

    today = datetime.strftime(datetime.today(), '%Y-%m-%d')

    for day_offset in range(START_DAY_OFFSET, END_DAY_OFFSET):
        for city_name, city_id in city_ids.items():

            session_id, date_from = get_search_session_id(city_id, day_offset)
            
            logger.info('scraping city: {} on day: {}'.format(city_name, day_offset))

            if session_id == -1:
                logger.error("Getting city search failed: city_name:{}".format(city_name))
                continue

            completed = False
            while not completed:
                hotels_data = get_search_data(session_id)
                completed = hotels_data['result']['lastChunk']
                time.sleep(sleep_time)

            for hotel in hotels_data["result"]["result"]:
                time.sleep(sleep_time)

                scrape_hotel(city_name, hotel, session_id, date_from, today)


def scrape_hotel(city_name:str, hotel:dict, session_id:str, date_from:str, today:str, sleep_time:int):
    """Scrape and save hotel and cals rooms scraper.

    Args:
        city_name (str): The english name of search city.
        hotel (dict): Contains hotel data (id, name).
        session_id (str): A session id to search in snaptrip site
        date_from (str): Formated date of search date range start.
        today (str): Frmated date of today for InsertionDate

    Returns:
        None
    """
    hotel_site_id = hotel["id"]
    hotel_url = urljoin(BASE_URL, hotel['link'])

    with get_db_connection() as conn:
        hotel_id = insert_select_id(
            table='tblHotels',
            key_value={
                'htlCity': city_name,
                'htlFaName': hotel['name'].get('fa'),
                'htlEnName': hotel['name'].get('en'),
                "htlUrl": hotel_url,
                "htlFrom": 'A'
            },
            id_field='htlID',
            identifier_condition={
                "htlFaName": hotel['name'].get('fa')
            },
            conn=conn
        )


    final_result = False
    while not final_result:
        hotel_rooms_data = get_hotel_rooms_data(session_id, hotel_site_id)

        final_result = hotel_rooms_data['result']['finalResult']
        time.sleep(sleep_time)

    for room_type in hotel_rooms_data['result']["rooms"]:

        room_type_id = room_type["id"]
        for room in room_type["rooms"]:
            scrape_room(room, hotel_id, date_from, today)


def scrape_room(room:dict, hotel_id:int, date_from:str, today:str) -> None:
    """Scrape and save room 

    Args:
        room (dict): A dictionry of room data (contains name, name_en, price, boardPrice).
        hotel_id (int): ID of hotel in out database.
        date_from (str): Formated date of search date range start.
        today (str): Frmated date of today for InsertionDate

    Returns:
        None
    """

    with get_db_connection() as conn:

        room_id = insert_select_id(
            table='tblRooms',
            key_value={
                'romName': room['name'],
                "romType": get_room_types(room['name']),
                'rom_htlID': hotel_id
            },
            id_field='romID',
            identifier_condition={
                "romName": room['name'],
                'rom_htlID': hotel_id
            },
            conn=conn
        )
        insert_select_id(
            table="tblAvailabilityInfo",
            key_value={
                "avl_romID": room_id,
                "avlDate": date_from,
                "avlInsertionDate": today,
                "avlBasePrice": room['boardPrice'],
                "avlDiscountPrice": room['price']
            },
            id_field=None,
            identifier_condition={},
            conn=conn
        )


def get_room_types(room_name:str)-> str:
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
        "دوتخته":
        "D",
        "سهتخته":
        'T',
        'چهارتحته':
        'Q',
        "یکخوابه":
        'S',
        "دوخوابه":
        "D",
        "سهخوابه":
        'T',
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
    with profile_ctx("/home/erfan/Desktop/myprofile.png"):
        main()
    print("Alibaba Done!")
