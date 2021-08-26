import os
import re

import mysql.connector
import logging
from dotenv import load_dotenv, find_dotenv
from itertools import groupby

from scrape.common_utils import get_room_types 
from scrape.common_utils import mgroupby

logger = logging.getLogger(__name__)

env_path = find_dotenv(raise_error_if_not_found=True)
load_dotenv(dotenv_path=env_path, verbose=True, override=True)

DO_CHECK_ROOM_TYPES = True

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

if DO_CHECK_ROOM_TYPES:
    new_type_count = 0
    update_type_ciunt = 0
    no_changes_count = 0
    no_type_found_count = 0
    error_count = 0

    with get_db_connection() as conn:
        all_rooms = custom(query_string=all_rooms_query, conn=conn)
        for room_counter, room in enumerate(all_rooms):
            room_type = get_room_types(room_name=room['romName'])
            if not room_type == " ":
                if not room_type == room['romType']:
                    try:
                        room_type_update_query = "UPDATE tblRooms SET romType='{}' WHERE romID = {}".format(room_type, room['romID'])
                        custom(query_string=room_type_update_query, conn=conn)
                        conn.commit()
                        
                        if not room['romType'] or room['romType'] == " ":
                            new_type_count += 1
                        else:
                            update_type_ciunt += 1
                    
                    except Exception as e:
                        logger.error("rooms_UUID - Error: {}".format(e))
                        error_count += 1
                else:
                    no_changes_count += 1            
            else:
                no_type_found_count += 1

    logger.error("\nFound {} rooms.\n{} No type found\n{} No change made\n{} New type\n{} Update\n{} Error".format(
        len(all_rooms),
        no_type_found_count,
        no_changes_count,
        new_type_count,
        update_type_ciunt,
        error_count
        ))

#####################################
### SHOW ROOMS GROUPED BY HOTELID ###
#####################################
# AND romUUID is NULL
all_rooms_query = """
SELECT romName, romType, htlUUID, htlFrom, avlBasePrice, romID FROM tblRooms
INNER JOIN tblAvailabilityInfo ON romID = avl_romID
INNER JOIN tblHotels ON htlID = rom_htlID
WHERE not htlUUID is NULL 
GROUP BY romName, romType, htlUUID, htlFrom, romID
ORDER BY htlUUID, htlFrom, romType, avlBasePrice, romName;
"""

rooms_all_UUUID_query = """
    SELECT romUUID from tblRooms
    WHERE NOT romUUID is NULL
    GROUP BY romUUID;"""

with get_db_connection() as conn:
    custom(query_string="SET sql_mode=(SELECT REPLACE(@@sql_mode,'ONLY_FULL_GROUP_BY',''));", conn=conn)
    all_rooms = custom(query_string=all_rooms_query, conn=conn)

    rooms_all_UUUID = custom(query_string=rooms_all_UUUID_query, conn=conn)

used_room_UUID = set([i['romUUID'] for i in rooms_all_UUUID])
# used_room_UUID = set()
room_index_ID = {}


def print_rooms(room_index_ID, htlUUID, site_rooms):
    index = 0
    htlFrom_order = []
    with open('rooms.txt', 'w') as f:
        f.write("htlUUID: {}\n".format(htlUUID))
        
        site_rooms = dict(sorted(site_rooms.items(), key=lambda item:len(item[1])))
       
        for htlFrom_index, (htlFrom, site_rooms) in enumerate(site_rooms.items()):
            f.write("\nhtlFrom: {}\n".format(htlFrom))
            htlFrom_order.append(htlFrom)
            for i, room in enumerate(site_rooms):
                room_text = " - ".join([
                        str(i),
                        str(room['romID']),
                        room['romName'],
                        str(room['avlBasePrice']),
                        room['romType']
                    ])
                    
                global_index = "{}_{}".format(htlFrom, i)

                room_index_ID[global_index] = room['romID']
                

                f.write(room_text+'\n')
                index += 1
                f.flush()
    
    return htlFrom_order

def delete_ids(site_rooms, *IDs):
    for htlFrom, htlFrom_rooms in site_rooms.items():
        for i, htlFrom_room in enumerate(htlFrom_rooms):
            if htlFrom_room['romID'] in IDs:
                del site_rooms[htlFrom][i]


hotel_rooms = mgroupby(
    all_rooms,
    key=lambda room:room['htlUUID'])

def link_UUIDs(id1, id2, htlUUID, romUUID=None):
    if romUUID is None:
        romUUID_index = 0
        while True:
            romUUID = '{}_{}__{}'.format(
                htlUUID,
                room['romType'],
                romUUID_index
            )
            if romUUID in used_room_UUID:
                romUUID_index += 1
            else:
                break

    update_query = """
        UPDATE tblRooms 
        SET romUUID = '{}'
        WHERE romID = {} OR romID = {};
        """.format(romUUID, id1, id2)
    
    with get_db_connection() as conn:
        # print("Linked {} - {} -> {}".format(id1, id2, romUUID))
        custom(update_query, conn=conn)
        used_room_UUID.add(romUUID)
        conn.commit()

deleted_ids = []

for htlUUID, rooms in hotel_rooms.items():
   
    site_rooms = mgroupby(
        rooms,
        key=lambda room:room['htlFrom'],
        sort_key=lambda room:room['avlBasePrice'])

    if len(site_rooms.keys()) < 2:
        continue
    
    ### Try to find UUID automaticly

    for room in list(site_rooms.values())[1]:
        for i, check_room in enumerate(list(site_rooms.values())[0]):
            price_check = abs(room['avlBasePrice'] - check_room['avlBasePrice']) < 500000
            type_check = room['romType'] == check_room['romType']
            if price_check and type_check :

                id1 = check_room['romID']
                id2 = room['romID']

                deleted_ids.append(id1)
                deleted_ids.append(id2)
                romUUID = '{}_{}__{}'.format(
                    htlUUID,
                    room['romType'],
                    re.sub("0+$", "", str(room['avlBasePrice']))
                )
                # with open('rooms.txt', 'a') as f :
                #     f.write(" | ".join([room['romName'], check_room['romName'], romUUID])+"\n")
                link_UUIDs(id1, id2, htlUUID, romUUID=romUUID)


    continue
    delete_ids(site_rooms, *deleted_ids)

    ### Ask user to complete other rooms UUID

    htlFrom_order = print_rooms(room_index_ID, htlUUID, site_rooms)

    while True and len(site_rooms['A']) and len(site_rooms['S']):
        inp1 = input("Ind1: ")
        
        if not inp1:
            break

        ind1 = inp1
        ind2 = input("Ind2: ")
        if not ind2:
            break

        id1 = room_index_ID[htlFrom_order[0]+"_"+ind1]
        id2 = room_index_ID[htlFrom_order[-1]+"_"+ind2]

        link_UUIDs(id1, id2, htlUUID)
        
        delete_ids(site_rooms, id1, id2)
        print_rooms(room_index_ID, htlUUID, site_rooms)

print("\nMatched {} rooms".format(len(deleted_ids)))    
a = 2