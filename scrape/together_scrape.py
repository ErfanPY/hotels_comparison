from collections import defaultdict
import logging
import os

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
    get_city_hotels as snapp_get_city_hotels,
    scrape_hotel as snapptrip_scrape_hotel,
    en_fa_cities
)

from scrape.compare_rooms import main as compare_scrapes, compare_rooms


logger = logging.getLogger("main_logger")

START_DAY_OFFSET = os.environ.get("SCRAPE_START_DAY", "1")
START_DAY_OFFSET = int(START_DAY_OFFSET)

scrape_stat_path = "scrape_stat/"+'-'.join(TO_SCRAPE_CITIES)

if not os.path.exists("scrape_stat"):
    os.mkdir("scrape_stat")

if START_DAY_OFFSET == 1 and os.path.exists(scrape_stat_path):
    with open(scrape_stat_path) as f:
        START_DAY_OFFSET = int(f.readline().strip())

START_DAY_OFFSET -= 1

SCRAPE_END_DAY = os.environ.get("SCRAPE_END_DAY", "31")
SCRAPE_END_DAY = int(SCRAPE_END_DAY)
SCRAPE_END_DAY += 1

def main():
    visited_snapp_hotel = []

    for day_offset in range(START_DAY_OFFSET, SCRAPE_END_DAY):
        logger.info(f"Day: {day_offset}")

        for city_name in TO_SCRAPE_CITIES:
            logger.info(f"City: {city_name}")

            htlFaName_htlUUID = get_htlFaName_htlUUID(city_name)

            uuid_hotels = defaultdict(list)
            
            counter = 0
            alibaba_hotels = a_get_city_hotels(city_name, day_offset)
            for hotel in alibaba_hotels:
                hotel_uuid = htlFaName_htlUUID.get(hotel['faName'])
                uuid_hotels[hotel_uuid].append(hotel)
                counter += 1

            logger.info(f"Alibaba: {counter}")
            
            counter = 0
            snapptrip_hotels = s_get_city_hotels(en_fa_cities[city_name], day_offset)
            for hotel in snapptrip_hotels:
                hotel_uuid = htlFaName_htlUUID.get(hotel['faName'])
                counter += 1
                
                if hotel_uuid and hotel_uuid in visited_snapp_hotel:
                    continue

                uuid_hotels[hotel_uuid].append(hotel)
                visited_snapp_hotel.append(hotel_uuid)
            
            logger.info(f"Snapptrip: {counter}")
            
            len_uuid_hotels = len(uuid_hotels)
            for i, (uuid, hotels) in enumerate(uuid_hotels.items()):
                if uuid is None:
                    continue
                logger.info(f"{uuid}: {i}/{len_uuid_hotels}")

                site_rooms = {}

                len_hotels = len(hotels)
                for j, hotel in enumerate(hotels):
                    logger.info(f" UUID - {j}/{len_hotels}")

                    rooms = scrape_hotel(hotel)
                    site_rooms[hotel['hotel_from']] = rooms
                
                if len(site_rooms.keys()) == 2:
                    compare_hotel_rooms(**site_rooms)
                else:
                    pass
                    # add_single_available_rooms() #TODO


            none_uuid_hotels = uuid_hotels.get(None, [])
            len_none_uuid = len(none_uuid_hotels)
            for i in range(len_none_uuid//2):
                logger.info(f" no UUID - {i}/{len_none_uuid//2}")
                
                scrape_hotel(none_uuid_hotels[i])
                from_end_index = -1*(i+1)
                scrape_hotel(none_uuid_hotels[from_end_index])
            
            if not len_none_uuid%2 == 0:
                scrape_hotel(none_uuid_hotels[i+1])

        with open(scrape_stat_path, 'w') as f:
            f.write(str(day_offset+1))

    with open(scrape_stat_path, 'w') as f:
        f.write("0")


def get_htlFaName_htlUUID(city):
    query = """
        SELECT htlFaName, htlUUID from tblHotels
        WHERE NOT htlUUID is NULL AND htlCity = %s ;
    """
    
    group = {}

    with get_db_connection() as conn:
        name_uuids = custom(query, [city], conn=conn)
    
    for row in name_uuids:
        #TODO may exist some rooms that have same persian name but acctualy are diffrent hotels (فردوسی)
        group[row['htlFaName']] = row['htlUUID']
    
    return group


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


def s_get_city_hotels(city_name: str, day_offset: int) -> list:
    """
        Gets a city name and return hotels of Snapptrip site on city.

        returns:
            non-zero int on error
    """
    hotels = snapp_get_city_hotels(city_name, day_offset)
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
        rooms = snapptrip_scrape_hotel(
            hotel['url'],
            hotel['faName'],
            hotel['id'],
            hotel['city']
        )
    
    return rooms


def compare_hotel_rooms(alibaba, snapptrip):
    uuidـrooms = {}

    uuid_room = defaultdict(list)

    for a in alibaba:
        uuid_room[a.get('room_UUID')].append(a)

    for s in snapptrip:
        uuid_room[s.get('room_UUID')].append(s)

    for uuid, rooms in uuidـrooms.items():
        if not uuid is None:
            compare_rooms(rooms[0], rooms[-1])


if __name__ == "__main__":
    main()
