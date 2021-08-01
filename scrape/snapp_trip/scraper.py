import json
import logging
import os
import queue
import re
import socket
import time
from datetime import datetime, timedelta
from urllib.parse import urljoin

import socks
from bs4 import BeautifulSoup
from scrape.db_util import get_db_connection, insert_select_id
from scrape.common_utils import get_room_types

from .network_util import get_content, get_content_make_soup, urlparse

logger = logging.getLogger(__name__)

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

en_fa_cities = {v:k for k, v in fa_en_cities.items()}

to_scrape_cities_inp = os.environ.get("SNAPPTRIP_TO_SCRAPE_CITIES", "")

if not to_scrape_cities_inp:
    to_scrape_cities = list(fa_en_cities.keys())
else:
    en_to_scrape_cities = to_scrape_cities_inp.split(',')
    to_scrape_cities = [en_fa_cities[city] for city in en_to_scrape_cities]


def main(sleep_time:int, proxy_host:str=None, proxy_port:int=None):
    # socks.set_default_proxy(proxy_host, proxy_port)
    # if not proxy_host is None:
    #     socket.socket = socks.socksocket

    BASE_URL = 'https://www.snapptrip.com/'
    

    for city_name in to_scrape_cities:
        city_url = make_city_url(city_name.strip())
        to_scrape_url = get_city_dated_url(city_url)
        
        has_next_page = True
        total_hotels_counter = 0
        available_hotels_counter = 0
        page_no = 1

        while has_next_page:

            logger.error("Snapptrip - Fetching hotels : {}".format(to_scrape_url))

            search_page_soup = get_content_make_soup(to_scrape_url)
            time.sleep(sleep_time)
            if search_page_soup == -1:
                logger.error("Snapptrip - Getting search page failed: url: {}".format(to_scrape_url))
                continue

            hotels = search_page_soup.select_one(".hotels-data").findAll("li", {'data-hotel-id': True})
            
            total_hotels_counter += len(hotels)
            
            for hotel in hotels:
                if "ظرفیت تکمیل" in hotel.text or hotel.select_one(".badge-fill-danger"):
                    has_next_page = False
                    logger.error("Snapptrip - City: {} FINISHED(No more room available). total {} and {} available hotels in {} page.".format(
                        city_name,
                        total_hotels_counter,
                        available_hotels_counter,
                        page_no
                    ))
                    break

                hotel_site_id = hotel.contents[3].attrs['data-id']

                hotel_url = hotel.select_one(
                    '#resultpage-hotelcard-cta').get('href')
                hotel_url = urljoin(BASE_URL, hotel_url)

                try:
                    scrape_hotel(hotel_url, hotel_site_id, city_name)
                    
                    time.sleep(sleep_time)
                
                    available_hotels_counter += 1

                except Exception as e:
                    logger.error("Snapptrip - FAILED on City: {} hotel: {}, error: {}".format(
                        city_name,
                        hotel_url,
                        e
                    ))

            logger.error("Snapptrip - City: {} has total {} and {} available hotels in {} page.".format(
                city_name,
                total_hotels_counter,
                available_hotels_counter,
                page_no
            ))

            next_page_div = search_page_soup.select_one('.pagination-next')
            if not next_page_div is None:
                next_page_url = next_page_div.select_one('a').get('href')
                if next_page_url is None or next_page_url == "" or next_page_url == "/":
                    has_next_page = False
                    logger.error("Snapptrip - City: {} FINISHED(No more pages). total {} and {} available hotels in {} page.".format(
                        city_name,
                        total_hotels_counter,
                        available_hotels_counter,
                        page_no
                    ))
                    continue

                to_scrape_url = urljoin(BASE_URL, next_page_url)
                page_no += 1
            else:
                has_next_page = False
                logger.error("Snapptrip - City: {} FINISHED(No more pages). total {} and {} available hotels in {} page.".format(
                    city_name,
                    total_hotels_counter,
                    available_hotels_counter,
                    page_no
                ))
                continue


def make_city_url(city_name):
    base_url = "https://www.snapptrip.com/رزرو-هتل/{city_name}"
    return base_url.format(city_name=city_name)


def scrape_hotel(hotel_url: str, hotel_site_id: str, city_name: str) -> None:
    """Gets and saves hotel then cals scrape_hotel_rooms

    Args:
        hotel_url (str): A url points to the hotel page.
        hotel_site_id (str): ID of hotel on snapptrip site.
        city_name (str): City name.

    Returns:
        None
    """

    hotel_name = hotel_url.split("/")[5].split("?")[0]

    logger.error("Snapptrip - Scape Hotel {} - {}".format(city_name, hotel_name))

    with get_db_connection() as conn:
        hotel_id = insert_select_id(
            table='tblHotels',
            key_value={
                "htlFaName": hotel_name,
                "htlEnName": "",
                "htlCity": fa_en_cities[city_name],
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
        logger.error("Snapptrip - Getting hotel content failed: url: {}".format(hotel_url))
        return

    comments_soup = hotel_soup.select('#rating-hotel')[0]

    rooms_name_id = scrape_hotel_rooms(hotel_soup, hotel_id, hotel_site_id,)
    
    add_rooms_comment(comments_soup, rooms_name_id)


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
    """Iterats on hotel room and save room and date to database.

    Args:
        hotel_soup (BeautifulSoup): A BeautifulSoup contains hotel webpage.
        hotel_id (int): Hotel ID on our databse.
        hotel_site_id (str): hote ID on snapptrip site.

    Returns:
        dict: A mapping from room_name to database room_id
        example:
        
        [['mashhad', 2], ['yazd', 5]]
    """
    rooms_div = hotel_soup.select_one("div.position-relative")
    rooms = rooms_div.select(".room-item")

    today = datetime.strftime(datetime.today(), '%Y-%m-%d')

    rooms_name_id = {}

    with get_db_connection() as conn:
        rooms_counter = 0
        for room in rooms:
            room_site_id = room.contents[3].attrs['data-room_id']
            room_name = room.contents[1].attrs['data-roomname']

            breakfast = room.select_one('.breakfast')
            meal_plan = 'RO' if 'disabled' in breakfast.attrs['class'] else 'BB'

            room_id = insert_select_id(
                table='tblRooms',
                key_value={
                    "rom_htlID": hotel_id,
                    "romName": room_name,
                    "romType": get_room_types(room_name),
                    'romMealPlan': meal_plan
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
                logger.error("Snapptrip - getting hotel room failed, hotel_id: {}".format(hotel_id))
                continue

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
            
            rooms_name_id[room_name]= room_id
            rooms_counter += 1

        # logger.error("Snapptrip - Hotel: {} has {} rooms.".format(hotel_id, rooms_counter))

    return rooms_name_id


def add_rooms_comment(comments_soup:BeautifulSoup, rooms_name_id:list) -> None:
    """Extract comments from html and connect comment with specified room.

    Args:
        comments_soup (BeautifulSoup): html data of comments section
        rooms_name_id (dict): A mapping from room_name to database room_id
            example:
            
            [['mashhad', 2], ['yazd', 5]]
        
    Returns:
        None
    """

    with get_db_connection() as conn:
    
        for comment in comments_soup.select('li'):
            user_name = comment.select_one('.user-name')
            user_name = user_name.text.strip() if user_name else "مهمان"

            comment_date = comment.select_one('.date-modify > span').attrs['data-registerdate'] # attr date
            room_name = comment.select_one('.reserve-info__room > span')
            room_name = room_name.text.strip() if room_name else ""

            comment_text = comment.select_one('.comment-text-wrapper')
            comment_text = comment_text.text.strip() if not comment_text is None else ""

            stren_point = comment.select_one('.strengths-point-text > p')
            weak_point = comment.select_one('.weakness-point-text > p')
            
            stren_point = stren_point.text.strip() if stren_point else ""
            weak_point = weak_point.text.strip() if weak_point else ""

            room_id = rooms_name_id.get(room_name)
            if not room_id:
                # room_id = 0
                continue

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
                id_field=None,
                identifier_condition={},
                conn=conn
            )


if __name__ == "__main__":
    main(sleep_time=1)
    print("done")
