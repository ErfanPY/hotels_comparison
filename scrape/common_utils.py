import re
import logging

logger = logging.getLogger(__name__)

types_abrv = [
        ['دبل', 'D'],
        ["دابل", "D"],
        
        ['یکتخت', 'S'],
        ['دوتخت', 'D'],
        ['سهتخت', 'T'],
        ['چهارتخت', 'Q'],
        ['پنجتخت', '5'],
        ['ششتخت', '6'],
        ['هفتتخت', '7'],

        ['سوییت', 'SU'],
        ['سوئیت', 'SU'],
        ['سینیور', 'SE'],
        ['سنیور', 'SE'],
        ['کانکت', 'C'],
        ['جونیور', 'JU'],
        ['دوبلکس', 'DU'],
        ['امپریال', 'AM'],
        ['کویین', 'QU'],
        ['VIP', 'VIP'],
        ['سوپریور', 'SUP'],
        ['لوکس', 'LU'],
        ['رویال', 'RO'],
        ['کیدز', 'KI'],
        ['ملل', 'IN'],
        ['پرزیدنت', 'PR'],
        ['پرنسس', 'PRA'],
        ['پردیس', 'PAR'],
        ['عروسوداماد', 'B&G'],
        
        ["تویین", "2"],
        ['تریپل', 'T'],
        ['سینگل', 'S'],
        ["یک", 'S'],
        ["دو", "D"],
        ["سه", 'T'],
        ['چهار', 'Q'],

        ['پنج', '5'],
        ['شش', '6'],
        ['هفت', '7'],
        ['هشت', '8'],
        ['نه', '9'],
        ['ده', '10'],
        ['یازده', '11'],
        ['دوازده', '12'],

        ['2', '2'],
        ['3', '3'],
        ['4', '4'],
        ['5', '5'],
    ]

# dict_types_abrv = {k: v for k, v in types_abrv}

def get_room_types(room_name:str)-> str:
    """Gets type of room by searching abbreviation keywoards on room name.

    Args:
        room_name (str): room name.

    Returns:
        str: room type
    """

    # search_room_name = re.sub('\W+', ' ', room_name)
    
    # for room_name_part in search_room_name.split():
    #     room_type = dict_types_abrv.get(room_name_part)
    #     if not room_type is None:
    #         return room_type

    search_room_name = re.sub('\W+', '', room_name)

    for type_name, abrv in types_abrv:
        if type_name in search_room_name:
            return abrv

    logger.error("No abbreviation found for room name: {}".format(room_name))

    return " "


def mgroupby(iterator, key, sort_key=None, reverse=False):
    groups = {}
    for item in iterator:
        group = key(item)
        
        items = groups.get(group, [])
        items.append(item)
        
        groups[group] = items
    
    if not sort_key is None:
        for group, items in groups.items():
            groups[group] = sorted(items, key=sort_key, reverse=reverse)

    return groups