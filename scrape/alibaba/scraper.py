import re
import socket
import sys
import time
from datetime import datetime
from os import name
from urllib.parse import urljoin

import socks
from scrape.db_util import get_db_connection, insert_select_id

from .network_utils import *

socks.set_default_proxy("host", "port")
if '-p' in sys.argv:
    socket.socket = socks.socksocket

DB_PATH = "alibaba/data.db"
BASE_URL = "https://www.alibaba.ir/hotel/"
SLEEP_TIME = 3

city_ids = {
    'mashhad': '5be3f68be9a116befc66701b',
    'shiraz': '5be3f68be9a116befc6669e6'
}


def main():

    today = datetime.strftime(datetime.today(), '%Y-%m-%d')

    for day_offset in range(30):
        for city_name, city_id in city_ids.items():

            session_id, date_from = get_search_session_id(city_id, day_offset)

            completed = False
            while not completed:
                hotels_data = get_search_data(session_id)
                completed = hotels_data['result']['lastChunk']
                time.sleep(SLEEP_TIME)

            for hotel in hotels_data["result"]["result"]:
                time.sleep(SLEEP_TIME)

                scrape_hotel(city_name, hotel, session_id, date_from, today)


def scrape_hotel(city_name, hotel, session_id, date_from, today):
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

    # places[i](site_id _id, name, priority, location, type, distance)

    final_result = False
    while not final_result:
        hotel_rooms_data = get_hotel_rooms_data(session_id, hotel_site_id)

        final_result = hotel_rooms_data['result']['finalResult']
        time.sleep(SLEEP_TIME)

    for room_type in hotel_rooms_data['result']["rooms"]:

        room_type_id = room_type["id"]
        for room in room_type["rooms"]:
            scrape_room(room, hotel_id, date_from, today)


def scrape_room(room, hotel_id, date_from, today):
    print(
        room['name'],
        room['name_en'],
        room['price'],
        room['boardPrice']
    )
    with get_db_connection() as conn:
        hotel_id_and_name_en = '|'.join((hotel_id, room['name_en']))

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


def get_room_types(room_name):
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
    main()

