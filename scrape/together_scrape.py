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

from scrape.compare_rooms import main as compare_scrapes


logger = logging.getLogger(__name__)

START_DAY_OFFSET = os.environ.get("ALIBABA_START_DAY", 0)
scrape_stat_path = "scrape_stat/"+'-'.join(TO_SCRAPE_CITIES)

if not os.path.exists("scrape_stat"):
    os.mkdir("scrape_stat")

if START_DAY_OFFSET == 0 and os.path.exists(scrape_stat_path):
    with open(scrape_stat_path) as f:
        START_DAY_OFFSET = int(f.readline().strip())


def main():
    visited_snapp_hotel = []

    for day_offset in range(START_DAY_OFFSET, 30):
        logger.info(f"Day: {day_offset}")

        for city_name in TO_SCRAPE_CITIES:
            logger.info(f"City: {city_name}")

            uuid_hotels = defaultdict(list)

            snapptrip_hotels = s_get_city_hotels(en_fa_cities[city_name], day_offset)
            for hotel in snapptrip_hotels:
                hotel_uuid = hotel_to_uuid(hotel)

                if hotel_uuid and hotel_uuid in visited_snapp_hotel:
                    continue

                uuid_hotels[hotel_uuid].append(hotel)
                visited_snapp_hotel.append(hotel_uuid)
            
            alibaba_hotels = a_get_city_hotels(city_name, day_offset)
            for hotel in alibaba_hotels:
                uuid_hotels[hotel_to_uuid(hotel)].append(hotel)
                
            for i, (uuid, hotels) in enumerate(uuid_hotels.items()):

                for hotel in hotels:
                    scrape_hotel(hotel)

                logger.info(f"Hotels: {i}/{len(uuid_hotels)}")

        with open(scrape_stat_path, 'w') as f:
            f.write(str(day_offset+1))

    with open(scrape_stat_path, 'w') as f:
        f.write("0")

    compare_scrapes()


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
    
    uuid = uuids[0].get('htlUUID')
    
    return uuid


def scrape_hotel(hotel: dict) -> int:
    """
        Checks if hotel is from alibaba or snapptripp, and call that site scrapper.

       returns:
            non-zero int on error
    """
    if hotel['hotel_from'] == "alibaba":
            
        alibaba_scrape_hotel(
            hotel['city'],
            hotel,
            hotel['session_id'],
            hotel['date_from'],
            hotel['day_offset']
        )

    else:
        snapptrip_scrape_hotel(
            hotel['url'],
            hotel['faName'],
            hotel['id'],
            hotel['city']
        )


if __name__ == "__main__":
    main()
