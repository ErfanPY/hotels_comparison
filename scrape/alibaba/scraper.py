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

logger = logging.getLogger("main_logger")

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

START_DAY_OFFSET = os.environ.get("ALIBABA_START_DAY", 0)
scrape_stat_path = "scrape_stat/"+'-'.join(TO_SCRAPE_CITIES)

if not os.path.exists("scrape_stat"):
    os.mkdir("scrape_stat")

if START_DAY_OFFSET == 0 and os.path.exists(scrape_stat_path):
    with open(scrape_stat_path) as f:
        START_DAY_OFFSET = int(f.readline().strip())

SLEEP_TIME = int(os.environ.get("ALIBABA_SCRAPPER_SLEEP_TIME", "0"))
CRAWL_START_DATETIME = datetime.now().strftime("%Y-%m-%d %H:00:00")


def main(proxy_host:str=None, proxy_port:int=None):

    for day_offset in range(START_DAY_OFFSET, 30):
        for city_name in TO_SCRAPE_CITIES:
            hotels_counter = 0
            city_id = city_ids[city_name]
            session_id, date_from = get_search_session_id(city_id, day_offset)
            
            logger.info('Alibab - scraping city: {} on day: {}'.format(city_name, day_offset))

            if session_id == -1:
                logger.error("Alibaba - Getting city search failed: city_name:{}".format(city_name))
                continue

            hotels_data = get_city_hotels(session_id, city_name)

            for hotel in hotels_data:
                time.sleep(SLEEP_TIME)
                try:
                    session_id, r = scrape_hotel(
                        city_name, hotel, session_id=session_id,
                        date_from=date_from, day_offset=day_offset
                    )
                    if session_id == -1:
                        logger.error("Alibaba - FAILED on City: {}, hotel {}, with error: {}".format(city_name, hotel['name'].get('fa'), e))

                except Exception as e:
                    logger.error("Alibaba - FAILED on City: {}, hotel {}, with error: {}".format(city_name, hotel['name'].get('fa'), e))

                hotels_counter += 1
            
            logger.info("Alibaba - City: {} has {} hotels.".format(city_name, hotels_counter))

        with open(scrape_stat_path, 'w') as f:
            f.write(str(day_offset+1))

    with open(scrape_stat_path, 'w') as f:
        f.write("0")


def get_city_hotels(session_id, city_name, date_from=None, day_offset=None):
    completed = False
    hotels_data_results = []

    while not completed:
        hotels_data = get_search_data(session_id)
        
        if hotels_data['error']:
            logger.error("Alibaba - Getting city hotels failed: city_name:{}".format(city_name))
            return -1
        
        for hotel in hotels_data['result']['result']:
            parsed_hotel = parse_hotel(hotel)
            
            parsed_hotel['session_id'] = session_id
            parsed_hotel['city'] = city_name
            parsed_hotel['date_from'] = date_from
            parsed_hotel['day_offset'] = day_offset

            hotels_data_results.append(parsed_hotel)
        
        completed = hotels_data['result']['lastChunk']
        time.sleep(SLEEP_TIME)

    # Make hotels_data unique
    hotels_data_results = list({v['id']:v for v in hotels_data_results}.values()) 
    return hotels_data_results


def parse_hotel(hotel):
    hotel_site_id = hotel["id"]
    hotel_url = urljoin(BASE_URL, hotel['link'])
    faName = hotel['name'].get('fa')
    enName = hotel['name'].get('en')

    return {
        "url": hotel_url,
        "hotel_from": "alibaba",
        "id": hotel_site_id,
        "faName": faName,
        "enName": enName
    }


def scrape_hotel(city_name:str, hotel:dict, session_id:str, date_from:str, day_offset):
    """Scrape and save hotel then calls rooms scraper.

    Args:
        city_name (str): The english name of search city.
        hotel (dict): Contains hotel data (id, faName, enName, url).
        session_id (str): A session id to search in snaptrip site
        date_from (str): Formated date of search date range start.

    Returns:
        None
    """
    while True:
        with get_db_connection() as conn:
            hotel_id = insert_select_id(
                table='tblHotels',
                key_value={
                    'htlCity': city_name,
                    'htlFaName': hotel['faName'],
                    'htlEnName': hotel['enName'],
                    "htlUrl": hotel['url'],
                    "htlFrom": 'A'
                },
                id_field='htlID',
                identifier_condition={
                    'htlCity': city_name,
                    'htlEnName': hotel['enName'],
                    "htlFaName": hotel['faName'],
                    "htlFrom": 'A'
                },
                conn=conn
            )
        if not hotel_id == -1:
            break
        time.sleep(2)

    final_result = False
    rooms = []
    while not final_result:
        hotel_rooms_data = get_hotel_rooms_data(session_id, hotel['id'])
        if hotel_rooms_data == -1:
            logger.error("Alibaba - Getting city search failed - max sleep : city_name:{}".format(city_name))
            return -1
      
        if hotel_rooms_data.get('statusCode') == 408:
            city_id = city_ids[city_name]
            session_id, date_from = get_search_session_id(city_id, day_offset)

            if session_id == -1:
                logger.error("Alibaba - Getting city search failed: city_name:{}".format(city_name))
                return -1

            logger.error(f"Session Expired - city-id: {city_id}, day: {day_offset}, session: {session_id[:10]}...{session_id[-10:]}")
        else:
            rooms.extend(hotel_rooms_data['result']["rooms"])
            final_result = hotel_rooms_data['result']['finalResult']
            time.sleep(SLEEP_TIME)

    rooms_counter = 0
    res_rooms = []
    for room_type in rooms:

        room_type_id = room_type["id"]
        meal_plan = room_type['mealPlan']
        for room in room_type["rooms"]:
            

            room_ID, room_UUID, room_data = save_room(room=room, hotel_id=hotel_id, date_from=date_from,
                meal_plan=meal_plan)
            rooms_counter += 1
            
            res_rooms.append(room_data)

    # logger.info("Alibaba - Hotel: {} has {} rooms.".format(hotel['enName'], rooms_counter))
    return session_id, res_rooms


def save_room(room:dict, hotel_id:int, date_from:str, meal_plan:str) -> None:
    """Save room data to database

    Args:
        room (dict): A dictionry of room data (contains name, name_en, price, boardPrice).
        hotel_id (int): ID of hotel in out database.
        date_from (str): Formated date of search date range start.
        meal_plan (str): One of these (BB/RO)

    Returns:
        None
    """

    additives = []
    # extra-bed should be before breakfast if needed
    if meal_plan == "BB":
        additives.append("breakfast")

    while True:
        with get_db_connection() as conn:
            room_data = {
                'romName': room['name'],
                "romType": get_room_types(room['name']),
                'rom_htlID': hotel_id,
                'romMealPlan': meal_plan,
                "romAdditives": json.dumps(additives)
            }
            room_id_and_uuid = insert_select_id(
                table='tblRooms',
                key_value=room_data,
                id_field=['romID', 'romUUID'],
                identifier_condition=room_data,
                conn=conn
            )

            if room_id_and_uuid == -1:
                time.sleep(2)
                continue

            if room['price'] > room['boardPrice']:
                room['price'], room['boardPrice'] = room['boardPrice'], room['price']
            
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            room_avl_info = {
                "avl_romID": room_id_and_uuid['romID'],
                "avlDate": date_from,
                "avlCrawlTime": CRAWL_START_DATETIME,
                "avlInsertionDate": now,
                "avlBasePrice": room['boardPrice'],
                "avlDiscountPrice": room['price']
            }
            err_check = insert_select_id(
                table="tblAvailabilityInfo",
                key_value=room_avl_info,
                identifier_condition={
                    "avl_romID": room_id_and_uuid['romID'],
                    "avlDate": date_from,
                    "avlCrawlTime": CRAWL_START_DATETIME,
                },
                conn=conn
            )

            if not err_check == -1:
                room_data.update(room_avl_info)
                break
        

    return room_id_and_uuid['romID'], room_id_and_uuid['romUUID'], room_data


if __name__ == "__main__":
    main()
    print("Alibaba Done!")
