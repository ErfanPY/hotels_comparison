import re
import logging

logger = logging.getLogger(__name__)


def get_room_types(room_name:str)-> str:
    """Gets type of room by searching abbreviation keywoards on room name.

    Args:
        room_name (str): room name.

    Returns:
        str: room type
    """

    search_room_name = re.sub('\W+', '', room_name)

    types_abrv = {
        "یک": 'S',
        "دو": "D",
        "سه": 'T',
        'چهار': 'Q',
        'پنج': '5',
        'شش': '6',
        'هفت': '7',
        'هشت': '8',
        'نه': '9',
        'ده': '10',
        'یازده': '11',
        'دوازده': '12',
        'سوییت': 'SU',
        'جونیور': 'JU',
        'دوبلکس': 'DU',
        "تویین": "2",
        'دبل': 'D',
        "دابل": "D",
    }

    for type_name, abrv in types_abrv.items():
        if type_name in search_room_name:
            return abrv

    logger.error("No abbreviation found for room name: {}".format(room_name))

    return " "
