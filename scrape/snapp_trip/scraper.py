import json
import logging
import os
import queue
import re
import socket
import time
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse

import socks
from bs4 import BeautifulSoup
from scrape.db_util import get_db_connection, insert_multiple_room_info, insert_select_id
from scrape.common_utils import get_room_types

from .network_util import get_content, get_content_make_soup, urlparse

logger = logging.getLogger("main_logger")

fa_en_cities = {
    'تهران': 'tehran',
    'شیراز': 'shiraz',
    'مشهد': 'mashhad',
    'تبریز': 'tabriz',
    'اصفهان': 'isfahan',
    'کیش': 'kish',
    'یزد': 'yazd',
    'قشم': 'qeshm',
    'بندر-عباس': 'bandarAbbas',
    'اهواز': 'ahvaz',
    'قزوین': 'qazvin',
    'ساری': 'sari',
    'سرعین': 'sarein',
    'گرگان': 'gorgan',
    'رشت': 'rasht',
    'بندر-بوشهر': 'bushehr',
    'کرمان': 'kerman',
    'ارومیه': 'urmia',
}

en_fa_cities = {v: k for k, v in fa_en_cities.items()}

to_scrape_cities_inp = os.environ.get("SNAPPTRIP_TO_SCRAPE_CITIES", "")

if not to_scrape_cities_inp:
    to_scrape_cities = list(fa_en_cities.keys())
else:
    en_to_scrape_cities = to_scrape_cities_inp.split(',')
    to_scrape_cities = [en_fa_cities[city] for city in en_to_scrape_cities]

SLEEP_TIME = int(os.environ.get("SNAPPTRIP_SCRAPPER_SLEEP_TIME", "4"))

BASE_URL = 'https://www.snapptrip.com/'
CRAWL_START_DATETIME = datetime.now().strftime("%Y-%m-%d %H:00:00")

# DEBUG_HOTEL_FA_NAME = "آماتیس"

def main(proxy_host: str = None, proxy_port: int = None):
    # socks.set_default_proxy(proxy_host, proxy_port)
    # if not proxy_host is None:
    #     socket.socket = socks.socksocket

    for city_name in to_scrape_cities:

        hotels = get_city_hotels(city_name)
        if hotels == -1:
            continue
        scrape_hotels(city_name, hotels)


def get_city_hotels(city_name, day_offset=0):
    all_hotels = []

    city_url = make_city_url(city_name.strip())
    to_scrape_url = get_city_dated_url(city_url, day_offset)

    total_hotels_counter = 0
    page_no = 1
    # do_break = False

    while True:

        search_page_soup = get_content_make_soup(to_scrape_url)
        if search_page_soup == -1:
            logger.error(
                "Snapptrip - Getting search page failed: url: {}".format(to_scrape_url))
            return -1

        hotels = search_page_soup.select_one(
            ".hotels-data").findAll("li", {'data-hotel-id': True})

        for hotel in hotels:

            parsed_hotel = parse_hotel(hotel, city_name)

            # if DEBUG_HOTEL_FA_NAME and not DEBUG_HOTEL_FA_NAME in parsed_hotel['faName']:
            #     continue

            all_hotels.append(parsed_hotel)

            total_hotels_counter += 1

            # if DEBUG_HOTEL_FA_NAME and DEBUG_HOTEL_FA_NAME in parsed_hotel["faName"]:
            #     do_break = True
            #     break

        # if do_break:
        #     break

        next_page_div = search_page_soup.select_one('.pagination-next')
        if not next_page_div is None:
            next_page_url = next_page_div.select_one('a').get('href')
            if next_page_url and not next_page_url == "/":
                to_scrape_url = urljoin(BASE_URL, next_page_url)
                page_no += 1
            else:
                break
        else:
            break

    return all_hotels


def scrape_hotels(city_name, hotels):
    available_hotels_counter = 0
    hotels_count = len(hotels)

    for hotel in hotels:

        try:
            scrape_hotel(hotel['url'], hotel['faName'], hotel['id'], city_name)

            time.sleep(SLEEP_TIME)

            available_hotels_counter += 1

        except Exception as e:
            logger.error("Snapptrip - FAILED on City: {} hotel: {}, error: {}".format(
                city_name,
                hotel['url'],
                e
            ))

    logger.info("Snapptrip - City: {} has total {} and {} available hotels.".format(
                city_name,
                hotels_count,
                available_hotels_counter,
                ))


def parse_hotel(hotel, city_name):
    hotel_site_id = hotel.contents[3].attrs['data-id']

    hotel_url = hotel.select_one(
        '#resultpage-hotelcard-cta').get('href')
    hotel_url = urljoin(BASE_URL, hotel_url)
    hotel_name = hotel_url.split("/")[5].split("?")[0]

    hotel = {
        "hotel_from": "snapptrip",
        "id": hotel_site_id,
        "url": hotel_url,
        "faName": hotel_name,
        "city": city_name
    }

    return hotel


def make_city_url(city_name):
    base_url = "https://www.snapptrip.com/رزرو-هتل/{city_name}"
    return base_url.format(city_name=city_name)


def scrape_hotel(hotel_url: str, hotel_name: str, hotel_site_id: str, city_name: str) -> None:
    """Gets and saves hotel then calls scrape_hotel_rooms

    Args:
        hotel_url (str): A url points to the hotel page.
        hotel_name (str): Persian name of hotel.
        hotel_site_id (str): ID of hotel on snapptrip site.
        city_name (str): City name.

    Returns:
        None
    """

    unique_url = urljoin(hotel_url, urlparse(hotel_url).path)
    city = fa_en_cities.get(city_name, city_name)

    while True:
        with get_db_connection() as conn:
            hotel_id = insert_select_id(
                table='tblHotels',
                key_value={
                    "htlFaName": hotel_name,
                    "htlEnName": "",
                    "htlCity": city,
                    "htlUrl": unique_url,
                    "htlFrom": 'S'
                },
                id_field='htlID',
                identifier_condition={
                    'htlCity': city,
                    "htlFaName": hotel_name,
                    "htlFrom": 'S'
                },
                conn=conn
            )

        if not hotel_id == -1:
            break
        time.sleep(2)

    hotel_soup = get_content_make_soup(hotel_url)

    if hotel_soup == -1:
        logger.error(
            "Snapptrip - Getting hotel content failed: url: {}".format(hotel_url))
        return -1

    comments_soup = hotel_soup.select('#rating-hotel')[0]

    rooms, rooms_name_id = scrape_hotel_rooms(
        hotel_soup, hotel_id, hotel_site_id)

    add_rooms_comment(comments_soup=comments_soup, rooms_name_id=rooms_name_id)

    return rooms


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


def scrape_hotel_rooms(hotel_soup: BeautifulSoup, hotel_id: int, hotel_site_id: str) -> dict:
    """Iterates on hotel room and save room and date to database.

    Args:
        hotel_soup (BeautifulSoup): A BeautifulSoup contains hotel webpage.
        hotel_id (int): Hotel ID on our database.
        hotel_site_id (str): hotel ID on snapptrip site.
    """
    rooms_div = hotel_soup.select_one("div.position-relative")
    rooms = rooms_div.select(".room-item")

    res_rooms = []
    rooms_name_id = {}

    for i, room in enumerate(rooms):
        res_room, room_name_id, rooms_info_buff = get_parse_room(
            hotel_id,
            hotel_site_id,
            room
        )

        res_rooms.extend(res_room)
        rooms_name_id.update(room_name_id)

    with get_db_connection() as conn:
        err_check = insert_multiple_room_info(conn, rooms_info_buff)
        if err_check == -1:
            logger.error("adding availability info failed.")

    return res_rooms, rooms_name_id


def get_parse_room(hotel_id, hotel_site_id, room):
    res_rooms = []
    rooms_name_id = {}
    unique_romID_crawl_insertion = set()

    room_site_id = room.contents[3].attrs['data-room_id']
    room_name = room.contents[1].attrs['data-roomname']

    breakfast = room.select_one('.breakfast')
    meal_plan = 'RO' if 'disabled' in breakfast.attrs['class'] else 'BB'

    additives = []
    no_extra_bed = room.select_one(".extra-bed.disabled")
    if no_extra_bed is None:
        additives.append("extra-bed")
    no_breakfast = room.select_one(".breakfast.disabled")
    if no_breakfast is None:
        additives.append("breakfast")

    room_data = {
        "romAdditives": json.dumps(additives),
        "rom_htlID": hotel_id,
        "romName": room_name,
        "romType": get_room_types(room_name),
        'romMealPlan': meal_plan
    }

    while True:
        with get_db_connection() as conn:
            roomID_and_UUID = insert_select_id(
                table='tblRooms',
                key_value=room_data,
                id_field=['romID', 'romUUID'],
                identifier_condition=room_data,
                conn=conn
            )

        if not roomID_and_UUID == -1:
            break

        time.sleep(SLEEP_TIME)

    room_data['romUUID'] = roomID_and_UUID['romUUID']
    room_data['romID'] = roomID_and_UUID['romID']
    room_data['htlFrom'] = "S"

    while True:
        room_calender_content = get_content(
            "https://www.snapptrip.com/shopping/{}/calendar/{}?limit=36".format(hotel_site_id, room_site_id))

        if not room_calender_content == -1:
            break

        logger.error(
            "Snapptrip - getting hotel room failed, hotel_id: {}".format(hotel_id))
        time.sleep(SLEEP_TIME)

    rooms_info_buff = []
    room_calender = json.loads(room_calender_content)
    with get_db_connection() as conn:
        for data in room_calender['data']:
            # rooms_info_buff = []
            for day in data['calendar']:
                room_day_data = room_data.copy()
                unique_check = f"{roomID_and_UUID['romID']}{day['date']}"

                if unique_check in unique_romID_crawl_insertion:
                    continue

                unique_romID_crawl_insertion.add(unique_check)

                base_price = day['prices']['local_price']*10
                discount_price = day['prices']['local_price_off']*10

                if discount_price > base_price:
                    base_price, discount_price = discount_price, base_price

                room_avl_info = {
                    "avl_romID": roomID_and_UUID['romID'],
                    "avlDate": day['date'],
                    "avlCrawlTime": CRAWL_START_DATETIME,
                    "avlInsertionDate": datetime.now(),
                    "avlBasePrice": day['prices']['local_price']*10,
                    "avlDiscountPrice": day['prices']['local_price_off']*10
                }

                rooms_info_buff.append(room_avl_info)
                # err_check = insert_select_id(
                #     table="tblAvailabilityInfo",
                #     key_value=room_avl_info,
                #     identifier_condition={
                #         "avl_romID": roomID_and_UUID['romID'],
                #         "avlDate": day['date'],
                #         "avlCrawlTime": CRAWL_START_DATETIME,
                #     },
                #     conn=conn
                # )

                # if err_check == -1:
                #     logger.error("adding availability info failed.")

                room_day_data.update(room_avl_info)
                res_rooms.append(room_day_data)

            # err_check = insert_multiple_room_info(conn, rooms_info_buff)
            # if err_check == -1:
            #     logger.error("adding availability info failed.")

    rooms_name_id[room_name] = roomID_and_UUID['romID']

    return res_rooms, rooms_name_id, rooms_info_buff


def add_rooms_comment(comments_soup: BeautifulSoup, rooms_name_id: dict) -> None:
    """Extract comments from html and connect comment with specified room.

    Args:
        comments_soup (BeautifulSoup): html data of comments section
        rooms_name_id (dict): A mapping from room_name to database room_id
    Returns:
        None
    """

    with get_db_connection() as conn:

        for comment in comments_soup.select('li'):
            user_name = comment.select_one('.user-name')
            user_name = user_name.text.strip() if user_name else "مهمان"

            comment_date = comment.select_one(
                '.date-modify > span').attrs['data-registerdate']  # attr date
            room_name = comment.select_one('.reserve-info__room > span')
            room_name = room_name.text.strip() if room_name else ""

            comment_text = comment.select_one('.comment-text-wrapper')
            comment_text = comment_text.text.strip() if not comment_text is None else ""

            stren_point = comment.select_one('.strengths-point-text > p')
            weak_point = comment.select_one('.weakness-point-text > p')

            stren_point = stren_point.text.strip() if stren_point else ""
            weak_point = weak_point.text.strip() if weak_point else ""

            # single quote escape
            stren_point = re.sub("'", "''", stren_point)
            weak_point = re.sub("'", "''", weak_point)
            comment_text = re.sub("'", "''", comment_text)

            room_id = rooms_name_id.get(room_name)
            if not room_id:
                continue
            try:
                insert_select_id(
                    table="tblRoomsOpinions",
                    key_value={
                        "rop_romID": room_id,
                        "ropUserName": user_name,
                        "ropDate": comment_date,
                        "ropStrengths": stren_point,
                        "ropWeakness": weak_point,
                        "ropText": comment_text
                    },
                    conn=conn
                )
            except Exception as e:
                logger.error("adding comment failed.")
                return


if __name__ == "__main__":
    main()
    print("done")
