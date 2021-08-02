import re
import logging

logger = logging.getLogger(__name__)


types_abrv = [
        ['سوییت', 'SU'],
        ['سوئیت', 'SU'],
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
        ['دبل', 'D'],
        ["دابل", "D"],
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

    for type_name, abrv in types_abrv:
        if type_name in search_room_name:
            return abrv

    logger.error("No abbreviation found for room name: {}".format(room_name))

    return " "
