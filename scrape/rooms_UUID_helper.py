import os
import re
from itertools import zip_longest

import mysql.connector
import logging
from dotenv import load_dotenv, find_dotenv
from itertools import groupby
from prettytable import PrettyTable

from scrape.common_utils import get_room_types 

logger = logging.getLogger(__name__)

env_path = find_dotenv(raise_error_if_not_found=True)
load_dotenv(dotenv_path=env_path, verbose=True, override=True)

def get_db_connection(host=None, user=None, password=None, port=None, database=None):
    cnx = mysql.connector.connect(
        host     = host      or os.environ.get("MYSQL_HOST"),
        user     = user      or os.environ.get("MYSQL_USER"),
        password = password  or os.environ.get("MYSQL_PASSWORD"),
        # port     = port      or os.environ.get("MYSQL_PORT"),
        database = database  or os.environ.get("MYSQL_DATABASE")
    )

    return cnx

def custom(query_string:str, data:list=[], conn=None):
    curs = conn.cursor(buffered=True, dictionary=True)

    curs.execute(query_string, data)

    if curs.with_rows:
        result = curs.fetchall()
        
        return result


all_rooms_query = "SELECT romID, romName, romType FROM  tblRooms"

##########################################################
### RECHECK ROOM NAMES AND FIND NEW ROOM TYPE FOR THEM ###
##########################################################

# new_type_count = 0
# update_type_ciunt = 0
# no_changes_count = 0
# no_type_found_count = 0
# error_count = 0

# with get_db_connection() as conn:
#     all_rooms = custom(query_string=all_rooms_query, conn=conn)
#     for room_counter, room in enumerate(all_rooms):
#         room_type = get_room_types(room_name=room['romName'])
#         if not room_type == " ":
#             if not room_type == room['romType']:
#                 try:
#                     room_type_update_query = "UPDATE tblRooms SET romType='{}' WHERE romID = {}".format(room_type, room['romID'])
#                     custom(query_string=room_type_update_query, conn=conn)
#                     conn.commit()
                    
#                     if not room['romType'] or room['romType'] == " ":
#                         new_type_count += 1
#                     else:
#                         update_type_ciunt += 1
                
#                 except Exception as e:
#                     logger.error("rooms_UUID - Error: {}".format(e))
#                     error_count += 1
#             else:
#                 no_changes_count += 1            
#         else:
#             no_type_found_count += 1

# logger.error("\nFound {} rooms.\n{} No type found\n{} No change made\n{} New type\n{} Update\n{} Error".format(
#     len(all_rooms),
#     no_type_found_count,
#     no_changes_count,
#     new_type_count,
#     update_type_ciunt,
#     error_count
#     ))

#####################################
### SHOW ROOMS GROUPED BY HOTELID ###
#####################################

def mgroupby(iterator, key):
    groups = {}
    for item in iterator:
        group = key(item)
        
        items = groups.get(group, [])
        items.append(item)
        
        groups[group] = items
    
    return groups

def get_room_text(room):
    room_text = " - ".join([
                    str(room['index']),
                    str(room['romID']),
                    room['romName'],
                    str(room['avlBasePrice']),
                    room['romType']
                ])
    
    return room_text


all_rooms_query = """
SELECT romName, romType, htlUUID, htlFrom, avlBasePrice, romID FROM tblRooms
INNER JOIN tblAvailabilityInfo ON romID = avl_romID
INNER JOIN tblHotels ON htlID = rom_htlID
WHERE not htlUUID is NULL AND romUUID is NULL
GROUP BY romName, romType, htlUUID, htlFrom, romID
ORDER BY htlUUID, htlFrom, romType, avlBasePrice, romName;
"""

with get_db_connection() as conn:
    custom(query_string="SET sql_mode=(SELECT REPLACE(@@sql_mode,'ONLY_FULL_GROUP_BY',''));", conn=conn)
    all_rooms = custom(query_string=all_rooms_query, conn=conn)

hotel_rooms = groupby(all_rooms, key=lambda room:room['htlUUID'])

room_ID_UUID = {}
room_index_ID = {}

for htlUUID, rooms in hotel_rooms:
    with open('rooms.txt', 'w') as f:
        # f.write("htlUUID: {}\n".format(htlUUID))
        site_rooms = mgroupby(rooms, key=lambda room:room['htlFrom'])

        index = 0
        if len(site_rooms.keys()) < 2:
            continue

        for htlFrom, htlFrom_rooms in site_rooms.items():
            # f.write("\nhtlFrom: {}\n".format(htlFrom))
            
            for htlFrom_room_index, room in enumerate(htlFrom_rooms):
                
                romUUID = htlUUID+"_"+room['romType']
                
                room_ID_UUID[room['romID']] = romUUID
                room_index_ID[index] = room['romID']
            
                site_rooms[htlFrom][htlFrom_room_index]['index'] = index
               
                room_text = get_room_text(room)
                
                site_rooms[htlFrom][htlFrom_room_index] = room_text

                # f.write(room_text+'\n')
                index += 1
        x = PrettyTable()
        x.field_names = site_rooms.keys()
        x.add_rows(zip_longest(*site_rooms.values(), fillvalue='?'))

        f.write(x.get_string())
        f.flush()
        b = 2

    while True:
        inp1 = input("Ind1: ")
        
        if not inp1:
            break

        ind1 = inp1
        ind2 = input("Ind2: ")
        id1 = room_index_ID[int(ind1)]
        id2 = room_index_ID[int(ind2)]
        UUID = room_ID_UUID[int(id1)]

        update_query = """
        UPDATE tblRooms 
        SET romUUID = '{}'
        WHERE romID = {} OR romID = {};
        """.format(UUID, id1, id2)

        with get_db_connection() as conn:
            custom(update_query, conn=conn)
            conn.commit()