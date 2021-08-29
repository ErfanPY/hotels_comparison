import json
from scrape.db_util import custom, get_db_connection, insert_select_id
from scrape.common_utils import mgroupby

rooms_data = []
romUUID_romIDs = {}

def main():
    global rooms_data
    global romUUID_romIDs

    single_rooms = []
    
    get_romUUIDs_query = """
    SELECT htlFrom, romID, romUUID 
    FROM tblRooms
    INNER JOIN tblHotels on htlID = rom_htlID
    ;
    """
    
    with get_db_connection() as conn:
        result = custom(query_string=get_romUUIDs_query, conn=conn)


    for room in result:
        htlFrom = room['htlFrom']
        romID = room['romID']
        romUUID = room['romUUID']

        past = romUUID_romIDs.get(romUUID, {})
        past[htlFrom] = romID
        romUUID_romIDs[romUUID] = past
    
    rooms_data_query = """
            SELECT romUUID, avlInsertionDate, avlDate, romID, avlBasePrice,
                avlDiscountPrice, romName, rom_htlID, htlFrom, romMealPlan
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

    with get_db_connection() as conn:

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
                compare_rooms(
                    alibaba_room=htlFrom_groups['A'][0],
                    snapptrip_room=htlFrom_groups['S'][0],
                    conn=conn
                )
            else:
                print("Non handled condition, {}".format(str(htlFrom_groups)))
          
        add_single_available_rooms(single_rooms, conn)


def compare_rooms(alibaba_room, snapptrip_room, conn):
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
    if not alibaba_room['avlBasePrice'] == snapptrip_room['avlBasePrice']:

        alrType = 'P'
        alrInfo = prices_alrInfo
        
    elif not alibaba_room['avlDiscountPrice'] == snapptrip_room['avlDiscountPrice']:
        alrType = 'D'
        alrInfo = prices_alrInfo

    elif not alibaba_room['romMealPlan'] == snapptrip_room['romMealPlan']:
        alrType = 'O'
        alrInfo = {
            alibaba_room['romID']: alibaba_room['romMealPlan'],
            snapptrip_room['romID']: snapptrip_room['romMealPlan'],
        }
    else:
        return
    
    romUUID = alibaba_room['romUUID']


    insert_select_id(table='tblAlert', key_value={
        "alrRoomUUID": romUUID, 
        "alrOnDate": alibaba_room['avlDate'],
        "alrType": alrType,
        "alrA_romID": alibaba_room['romID'],
        "alrS_romID": snapptrip_room['romID'],
        'alrInfo': json.dumps(alrInfo)
    }, id_field=None, identifier_condition=None, conn=conn)


def add_single_available_rooms(rooms, conn):
    for room in rooms:
        romUUID = room['romUUID']

        if romUUID == " ":
            singlity_msg = "No mathcing UUID on other hotel."
        else:
            singlity_msg = "Reserved on other hotel in this date."

        alrInfo = {
            room['romID']: singlity_msg
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
            "alrType": 'R',
            "alrA_romID": alrA_romID,
            "alrS_romID": alrS_romID,
            "alrInfo": json.dumps(alrInfo)
        }, id_field=None, identifier_condition=None, conn=conn)

if __name__ == "__main__":
    main()        
