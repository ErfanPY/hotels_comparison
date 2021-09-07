from scraper import city_ids
from network_utils import get_search_session_id


hotel_name = "tehran_alibaba"
day_offset = 0


city_name = hotel_name.split("_")[0]
hotel = {}
city_id = city_ids[city_name]

session_id, date_from = get_search_session_id(city_id, day_offset)

def scrape_hotel(): pass
scrape_hotel(
    city_name:str, hotel:dict,
    session_id:str, date_from:str,
    city_id,
    day_offset, sleep_time:int=1
)
 (id, name, link)

(
    'tehran',
    {'id': '625008', 'score': 9, 'maxScore': 10, 'star': 5, 'accommodation': {...}, 'facilities': [...], 'minPriceProviderName': 'DomesticHotels', 'minPrice': 12000000, 'minBoardPrice': 15000000, ...},
    '6134d741d5870500225b6dd8',
    '2021-09-05',
    '5be3f68be9a116befc6669e7',
    0,
    1
)