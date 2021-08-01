import logging
import os
import socket
import time
from datetime import datetime
from urllib.parse import urljoin

import socks
from scrape.db_util import get_db_connection, insert_select_id
from scrape.common_utils import get_room_types

from .network_utils import *

logger = logging.getLogger(__name__)

BASE_URL = "https://www.alibaba.ir/hotel/"

city_ids = {
    'tehran':      '5be3f68be9a116befc6669e7',
    'mashhad':     '5be3f68be9a116befc66701b',
    'shiraz':      '5be3f68be9a116befc6669e6',
    'isfahan':     '5be3f68be9a116befc6669e5',
    'tabriz':      '5be3f68be9a116befc666b82',
    'kish':        '5be3f68be9a116befc66704b',
    'yazd':        '5be3f692e9a116befc66e439',
    'qeshm':       '5be3f697e9a116befc674378',
    'bandarAbbas': '5be3f697e9a116befc674278',
    'ahvaz':       '5be3f695e9a116befc671b47',
    'qazvin':      '5d19d47b4a6d0cbd432e481e',
    'sari':        '5be3f697e9a116befc674035',
    'sarein':      '5d19d47b4a6d0cbd432e4818',
    'gorgan':      '5be3f697e9a116befc674686',
    'rasht':       '5be3f697e9a116befc674279',
    'bushehr':     '5be3f697e9a116befc67427b',
    'kerman':      '5be3f68be9a116befc667055',
    'urmia':       '5d19d4804a6d0cbd432e4a0b',
}

TO_SCRAPE_CITIES = os.environ.get("ALIBABA_TO_SCRAPE_CITIES", "")

if not TO_SCRAPE_CITIES:
    TO_SCRAPE_CITIES = list(city_ids.keys())
else:
    TO_SCRAPE_CITIES = [city.strip() for city in TO_SCRAPE_CITIES.split(',') if city.strip()]

def main(sleep_time:int, proxy_host:str=None, proxy_port:int=None):
    # socks.set_default_proxy(proxy_host, proxy_port)
    # if not proxy_host is None:
    #     socket.socket = socks.socksocket

    today = datetime.strftime(datetime.today(), '%Y-%m-%d')

    for day_offset in range(0, 30):
        for city_name in TO_SCRAPE_CITIES:
            hotels_counter = 0
            city_id = city_ids[city_name]
            session_id, date_from = get_search_session_id(city_id, day_offset)
            
            logger.error('Alibab - scraping city: {} on day: {}'.format(city_name, day_offset))

            if session_id == -1:
                logger.error("Alibaba - Getting city search failed: city_name:{}".format(city_name))
                continue

            completed = False
            hotels_data_results = []
            while not completed:
                hotels_data = get_search_data(session_id)
                hotels_data_results.extend(hotels_data['result']['result'])
                completed = hotels_data['result']['lastChunk']
                time.sleep(sleep_time)

            # Make hotels_data unique
            hotels_data_results = list({v['id']:v for v in hotels_data_results}.values()) 

            for hotel in hotels_data_results:
                time.sleep(sleep_time)
                try:
                    scrape_hotel(city_name, hotel, session_id, date_from, today, sleep_time=sleep_time)
                except Exception as e:
                    logger.error("Alibaba - FAILED on City: {} hotel {} with error: {}".format(city_name, hotel['name'].get('fa'), e))

                hotels_counter += 1
            
            logger.error("Alibaba - City: {} has {} hotels.".format(city_name, hotels_counter))

def scrape_hotel(city_name:str, hotel:dict, session_id:str, date_from:str, today:str, sleep_time:int=1):
    """Scrape and save hotel then calls rooms scraper.

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
    rooms_counter = 0

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
        meal_plan = room_type['mealPlan']
        for room in room_type["rooms"]:
            save_room(room=room, hotel_id=hotel_id, date_from=date_from,
                today=today, meal_plan=meal_plan)
            rooms_counter += 1

    logger.error("Alibaba - Hotel: {} has {} rooms.".format(hotel['name'], rooms_counter))
        

def save_room(room:dict, hotel_id:int, date_from:str, today:str, meal_plan:str) -> None:
    """Save room data to database

    Args:
        room (dict): A dictionry of room data (contains name, name_en, price, boardPrice).
        hotel_id (int): ID of hotel in out database.
        date_from (str): Formated date of search date range start.
        today (str): Frmated date of today for InsertionDate
        meal_plan (str): One of these (BB/RO)

    Returns:
        None
    """

    with get_db_connection() as conn:

        room_id = insert_select_id(
            table='tblRooms',
            key_value={
                'romName': room['name'],
                "romType": get_room_types(room['name']),
                'rom_htlID': hotel_id,
                'romMealPlan': meal_plan
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


if __name__ == "__main__":
    main(sleep_time=1)
    print("Alibaba Done!")
