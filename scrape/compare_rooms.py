import json
import time
from scrape.db_util import custom, get_db_connection, insert_select_id
from scrape.common_utils import mgroupby


def main():
    rooms_data = []

    single_rooms = []
    
    get_romUUIDs_query = """
    SELECT htlFrom, romID, romUUID 
    FROM tblRooms
    INNER JOIN tblHotels on htlID = rom_htlID
    ;
    """
    
    with get_db_connection() as conn:
        result = custom(query_string=get_romUUIDs_query, conn=conn)


    romUUID_romIDs = make_romUUID_romIDs(result)
    
    rooms_data_query = """
            SELECT romUUID, avlInsertionDate, avlDate, romID, avlBasePrice,
                avlDiscountPrice, romName, rom_htlID, htlFrom, romMealPlan, romAdditives
            FROM tblRooms
            INNER JOIN tblAvailabilityInfo ON romID = avl_romID
            INNER JOIN tblHotels ON htlID = rom_htlID 
            WHERE NOT romUUID IS NULL
            ;
        """

    with get_db_connection() as conn:
        rooms_data = custom(query_string=rooms_data_query, conn=conn)

    rom_identifier_groups = mgroupby(
        rooms_data,
        lambda room:"{}_{}".format(room['romID'], room['avlDate']),
        sort_key=lambda room:room['avlInsertionDate'], reverse=True
    )
   
    last_inserted_rooms = {k:v[0] for k, v in rom_identifier_groups.items()}
    
    room_UUID_groups = mgroupby(
        last_inserted_rooms.values(),
        # lambda room:room['romUUID']
        lambda room:"{}_{}".format(room['romUUID'], room['avlDate'])
    )


    for roomUUID, rooms_group in room_UUID_groups.items():
        htlFrom_groups = mgroupby(
            rooms_group,
            lambda room:room['htlFrom'],
            sort_key=lambda room:room['romMealPlan']
        )
        
        if len(htlFrom_groups.keys()) == 1:
            single_room = list(htlFrom_groups.values())[0][0]
            single_rooms.append(single_room)
        elif len(htlFrom_groups.keys()) == 2:
            while True:
                with get_db_connection() as conn:
                    err_check = compare_rooms(
                        alibaba_room=htlFrom_groups['A'][0],
                        snapptrip_room=htlFrom_groups['S'][0],
                        conn=conn
                    )
                if not err_check == -1:
                    break
                time.sleep(2)
        else:
            print("Non handled condition, {}".format(str(htlFrom_groups)))

    with get_db_connection() as conn:
        add_single_available_rooms(rooms=single_rooms, romUUID_romIDs=romUUID_romIDs, conn=conn)


def make_romUUID_romIDs(rooms):
    romUUID_romIDs = {}

    for room in rooms:
        htlFrom = room['htlFrom']
        romID = room['romID']
        romUUID = room['romUUID']

        past = romUUID_romIDs.get(romUUID, {})
        past[htlFrom] = romID
        romUUID_romIDs[romUUID] = past

    return romUUID_romIDs


def compare_rooms(alibaba_room, snapptrip_room, conn, crawsl_start_time=None):
    prices_alrInfo = {
        'base_price':{
            alibaba_room['romID']: alibaba_room['avlBasePrice'],
            snapptrip_room['romID']: snapptrip_room['avlBasePrice']
        },
        'discount_price':{
            alibaba_room['romID']: alibaba_room['avlDiscountPrice'],
            snapptrip_room['romID']: snapptrip_room['avlDiscountPrice'],
        }
    }
    romUUID = alibaba_room['romUUID']

    if not alibaba_room['avlBasePrice'] == snapptrip_room['avlBasePrice']:

        alrType = 'P'
        alrInfo = prices_alrInfo
        room_alret = {
            "alrRoomUUID": romUUID, 
            "alrOnDate": alibaba_room['avlDate'],
            "alrCrawlTime": crawsl_start_time,
            "alrType": alrType,
            "alrA_romID": alibaba_room['romID'],
            "alrS_romID": snapptrip_room['romID'],
            'alrInfo': json.dumps(alrInfo)
        }

        err_check = insert_select_id(
            table='tblAlert',
            key_value=room_alret,
            conn=conn
        )

        if err_check == -1:
            return -1
    if not alibaba_room['avlDiscountPrice'] == snapptrip_room['avlDiscountPrice']:
        alrType = 'D'
        alrInfo = prices_alrInfo

        err_check = insert_select_id(table='tblAlert', key_value={
            "alrRoomUUID": romUUID, 
            "alrOnDate": alibaba_room['avlDate'],
            "alrCrawlTime": crawsl_start_time,
            "alrType": alrType,
            "alrA_romID": alibaba_room['romID'],
            "alrS_romID": snapptrip_room['romID'],
            'alrInfo': json.dumps(alrInfo)
        }, conn=conn)
        
        if err_check == -1:
            return -1
    
    if not alibaba_room['romMealPlan'] == snapptrip_room['romMealPlan']:
        alrType = 'O'
        alrInfo = prices_alrInfo
        alrInfo["options"] = {
            alibaba_room['romID']: [alibaba_room['romMealPlan']],
            snapptrip_room['romID']: [snapptrip_room['romMealPlan']],
        }

        err_check = insert_select_id(table='tblAlert', key_value={
            "alrRoomUUID": romUUID, 
            "alrOnDate": alibaba_room['avlDate'],
            "alrCrawlTime": crawsl_start_time,
            "alrType": alrType,
            "alrA_romID": alibaba_room['romID'],
            "alrS_romID": snapptrip_room['romID'],
            'alrInfo': json.dumps(alrInfo)
        }, conn=conn)
        
        if err_check == -1:
            return -1

    set_a = set(alibaba_room['romAdditives'])
    set_b = set(snapptrip_room['romAdditives'])

    diff_a = set_a-set_b
    diff_b = set_b-set_a

    if diff_a or diff_b:
        alrType = 'O'
        alrInfo = prices_alrInfo
        alrInfo["options"] = {
            alibaba_room['romID']: list(diff_a),
            snapptrip_room['romID']: list(diff_b),
        }

        err_check = insert_select_id(table='tblAlert', key_value={
            "alrRoomUUID": romUUID, 
            "alrOnDate": alibaba_room['avlDate'],
            "alrCrawlTime": crawsl_start_time,
            "alrType": alrType,
            "alrA_romID": alibaba_room['romID'],
            "alrS_romID": snapptrip_room['romID'],
            'alrInfo': json.dumps(alrInfo)
        }, conn=conn)
        
        if err_check == -1:
            return -1

def add_single_available_rooms(rooms, romUUID_romIDs, conn, crawsl_start_time=None):
    for room in rooms:
        romUUID = room['romUUID']

        alrInfo = {
            'base_price':{
                room['romID']: room['avlBasePrice'],
            },
            'discount_price':{
                room['romID']: room['avlBasePrice'],
            }
        }

        # TODO
        try:
            alrA_romID = romUUID_romIDs[romUUID]['A']
            alrS_romID = romUUID_romIDs[romUUID]['S']
        except KeyError:
            return

        insert_select_id(table='tblAlert', key_value={
            "alrRoomUUID": romUUID, 
            "alrOnDate": room['avlDate'],
            "alrCrawlTime": crawsl_start_time,
            "alrType": 'R',
            "alrA_romID": alrA_romID,
            "alrS_romID": alrS_romID,
            "alrInfo": json.dumps(alrInfo)
        }, conn=conn)

if __name__ == "__main__":
    main()        
