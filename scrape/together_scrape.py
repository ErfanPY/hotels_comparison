from collections import defaultdict
import logging
import os
from datetime import datetime, timedelta
import time

from scrape.db_util import (
    custom,
    get_db_connection
)

from scrape.alibaba.scraper import (
    TO_SCRAPE_CITIES,
    START_DAY_OFFSET,
    city_ids,
    get_search_session_id,
    scrape_hotel as alibaba_scrape_hotel,
    get_city_hotels as alibaba_get_city_hotels,
) 

from scrape.snapp_trip.scraper import (
    get_city_hotels as snapptrip_get_city_hotels,
    scrape_hotel as snapptrip_scrape_hotel,
    en_fa_cities
)

from scrape.compare_rooms import compare_rooms, add_single_available_rooms, make_romUUID_romIDs


logger = logging.getLogger("main_logger")

START_DAY_OFFSET = os.environ.get("SCRAPE_START_DAY", "1")
START_DAY_OFFSET = int(START_DAY_OFFSET)


if not os.path.exists("scrape_stat"):
    os.mkdir("scrape_stat")

START_DAY_OFFSET -= 1
START_DAY_OFFSET = max(0, START_DAY_OFFSET)

SCRAPE_END_DAY = os.environ.get("SCRAPE_END_DAY", "31")
SCRAPE_END_DAY = int(SCRAPE_END_DAY) + 1
SCRAPE_END_DAY = min(SCRAPE_END_DAY, 31)

crawl_start_datetime = datetime.now().strftime("%Y-%m-%d %H:00:00")


def main():

    for city_name in TO_SCRAPE_CITIES:
        logger.info(f"City: {city_name}")

        error_code = scrape_city(city_name)
        if error_code == -1:
            logging.critical(f"Geting city failed, city: {city_name}")


def scrape_city(city_name):
    htlFaName_htlUUID = get_htlFaName_htlUUID(city_name)
    snapptrip_uuid_hotel, snapptrip_no_uuid_hotels = get_snapptrip_hotels_rooms(city_name, htlFaName_htlUUID)
    if snapptrip_uuid_hotel == -1:
        return -1

    city_scrape_stat_path = "scrape_stat/"+city_name

    if not START_DAY_OFFSET == "1" and os.path.exists(city_scrape_stat_path):
        with open(city_scrape_stat_path) as f:
            city_start_day_offset = int(f.readline().strip())
    else:
        city_start_day_offset = 0

    for day_offset in range(city_start_day_offset, SCRAPE_END_DAY):
        logger.info(f"Day: {day_offset}")
        scrape_day(city_name, day_offset, snapptrip_uuid_hotel, snapptrip_no_uuid_hotels, htlFaName_htlUUID)

        with open(city_scrape_stat_path, 'w') as f:
            f.write(str(day_offset+1))

    with open(city_scrape_stat_path, 'w') as f:
        f.write("0")


def scrape_day(city_name, day_offset, snapptrip_uuid_hotel, snapptrip_no_uuid_hotels, htlFaName_htlUUID):

    alibaba_uuid_hotel, alibaba_no_uuid_hotels = get_alibaba_hotels(city_name, day_offset, htlFaName_htlUUID)
    
    uuid_hotels = combine_hotels_rooms(
        alibaba_data=alibaba_uuid_hotel,
        snapptrip_data=snapptrip_uuid_hotel,
        day_offset=day_offset
    )

    if uuid_hotels == -1:
        return -1

    len_uuid_hotels = len(uuid_hotels)
    for i, (uuid, hotels) in enumerate(uuid_hotels.items()):
        if uuid:
            match_and_compare_hotels(len_uuid_hotels, i, uuid, hotels, day_offset)

    no_uuid_hotels = alibaba_no_uuid_hotels+snapptrip_no_uuid_hotels
    scrape_no_uuid_hotels(no_uuid_hotels)


def get_htlFaName_htlUUID(city):
    query = """
        SELECT htlFaName, htlUUID from tblHotels
        WHERE NOT htlUUID is NULL AND htlCity = %s ;
    """
    
    group = {}

    with get_db_connection() as conn:
        name_uuids = custom(query, [city], conn=conn)
    
    for row in name_uuids:
        group[row['htlFaName']] = row['htlUUID']
    
    return group


def get_alibaba_hotels(city_name, day_offset, htlFaName_htlUUID):
    uuid_hotel = {}
    no_uuid_hotels = []
    counter = 0

    alibaba_hotels = a_get_city_hotels(city_name, day_offset)
    
    if alibaba_hotels == -1:
        return -1

    for hotel in alibaba_hotels:
        hotel_uuid = htlFaName_htlUUID.get(hotel['faName'])
        if hotel_uuid is None:
            no_uuid_hotels.append(hotel)
        else:
            uuid_hotel[hotel_uuid] = hotel
        counter += 1

    logger.info(f"Alibaba: {counter}")
    return uuid_hotel, no_uuid_hotels


def combine_hotels_rooms(alibaba_data, snapptrip_data, day_offset):
    uuid_hotels = defaultdict(list)

    for uuid, hotel in alibaba_data.items():
        uuid_hotels[uuid].append(hotel)

    for uuid, hotel in snapptrip_data.items():
        uuid_hotels[uuid].append(hotel)

    return uuid_hotels


def get_snapptrip_hotels_rooms(city_name, htlFaName_htlUUID):
    counter = 0
    uuid_hotel = {}
    no_uuid_hotels = []
    
    snapptrip_hotels = snapptrip_get_city_hotels(city_name=en_fa_cities[city_name])

    if snapptrip_hotels == -1:
        return -1, -1
    
    for counter, hotel in enumerate(snapptrip_hotels):
        logger.debug(f"Snapptrip, hotel: {counter}/{len(snapptrip_hotels)}, {hotel['faName']}")
        hotel_uuid = htlFaName_htlUUID.get(hotel['faName'])
        
        hotel['rooms'] = scrape_hotel(hotel)

        if hotel_uuid is None:
            no_uuid_hotels.append(hotel)
        else:
            uuid_hotel[hotel_uuid] = hotel
    
    logger.info(f"Snapptrip: {counter}")

    return uuid_hotel, no_uuid_hotels 


def match_and_compare_hotels(len_uuid_hotels, i, uuid, hotels, day_offset):
    logger.info(f"{uuid}: {i}/{len_uuid_hotels}")

    site_rooms = {}
    offset_date = str((datetime.now() + timedelta(days=day_offset)).date())

    len_hotels = len(hotels)
    for j, hotel in enumerate(hotels):
        rooms = scrape_hotel(hotel)
        
        if rooms == -1:
            continue
        
        filtered_rooms = list(filter(
            lambda room: room['avlDate'] == offset_date and not room['romUUID'] is None,
            rooms
        ))

        site_rooms[hotel['hotel_from']] = filtered_rooms

        logger.debug(f" UUID - {j+1}/{len_hotels}")

    try:
        if len(site_rooms.keys()) == 2:
            compare_hotel_rooms(crawl_start_datetime=crawl_start_datetime, **site_rooms)
        elif len(site_rooms.keys()) == 1:
            add_reserved_hotel(list(site_rooms.values())[0])
        else:
            logger.error("unhandleable count of sites.")
    except Exception as e:
        logger.critical(f"Unhandled error on hotels compare.\n{e}", stack_info=True)

    return site_rooms


def scrape_no_uuid_hotels(none_uuid_hotels):
    len_none_uuid = len(none_uuid_hotels)
    
    front_i, end_i = 0, len_none_uuid
    while front_i < end_i:
        end_i -= 1
        
        logger.info(f" no UUID - {front_i*2}/{len_none_uuid}")
        
        try:
            scrape_hotel(none_uuid_hotels[front_i])
            if not front_i == end_i:
                scrape_hotel(none_uuid_hotels[end_i])
        except Exception as e:
            logger.critical(f"Unhandled error on no uuid hotel.\n{e}", stack_info=True)

        front_i += 1


def a_get_city_hotels(city_name: str, day_offset: int) -> list:
    """
        Gets a city name and return hotels of Alibaba site on city.

        returns:
            non-zero int on error
    """

    city_id = city_ids[city_name]
    session_id, date_from = get_search_session_id(city_id, day_offset)
            
    if session_id == -1:
        logger.error("Alibaba - Getting city search failed: city_name:{}".format(city_name))
        return -1

    hotels = alibaba_get_city_hotels(session_id=session_id, city_name=city_name, date_from=date_from, day_offset=day_offset)

    return hotels


def hotel_to_uuid(hotel: dict) -> str:
    """
        Make a select query to database to get uuid of hotel (Maybe from hotel farsi name).
    """

    query = """
        SELECT htlUUID from tblHotels
        WHERE htlFaName = %s;
    """
    
    with get_db_connection() as conn:
        uuids = custom(query, [hotel['faName']], conn=conn)
    
    if uuids :
        uuid = uuids[0].get('htlUUID')
        
        return uuid


def scrape_hotel(hotel: dict) -> int:
    """
        Checks if hotel is from alibaba or snapptripp, and call that site scrapper.

       returns:
            non-zero int on error
    """
    if hotel['hotel_from'] == "alibaba":
            
        s_id, rooms = alibaba_scrape_hotel(
            hotel['city'],
            hotel,
            hotel['session_id'],
            hotel['date_from'],
            hotel['day_offset']
        )

    else:
        # To scrape snapptrip just once
        if not hotel.get('rooms') is None:
            return hotel['rooms']

        rooms = snapptrip_scrape_hotel(
            hotel['url'],
            hotel['faName'],
            hotel['id'],
            hotel['city']
        )
    
    return rooms


def compare_hotel_rooms(alibaba, snapptrip, crawl_start_datetime):
    uuidـrooms = {}

    uuid_room = defaultdict(list)

    for a in alibaba:
        uuid_room[a.get('romUUID')].append(a)

    for s in snapptrip:
        uuid_room[s.get('romUUID')].append(s)

    for uuid, rooms in uuidـrooms.items():
        if not uuid is None:
            while True:
                with get_db_connection() as conn:

                    err_check = compare_rooms(
                        alibaba_room=rooms[0],
                        snapptrip_room=rooms[-1],
                        conn=conn,
                        crawsl_start_time=crawl_start_datetime
                    )
                   
                    if not err_check == -1:
                        break
                
                time.sleep(2)

def add_reserved_hotel(rooms):
    romUUID_romIDs = make_romUUID_romIDs(rooms)

    with get_db_connection() as conn:
        add_single_available_rooms(rooms=rooms, romUUID_romIDs=romUUID_romIDs, conn=conn)


if __name__ == "__main__":
    main()
