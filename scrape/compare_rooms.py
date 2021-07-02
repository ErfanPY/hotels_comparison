import json
from scrape.db_util import custom, get_db_connection, insert_select_id

rows = []
romUUID_romIDs = {}

def main():
    global rows
    global romUUID_romIDs

    rowIdentifier_rowIndex = {}
    
    get_romUUIDs_query = """
    SELECT htlFrom, romID, romUUID 
    FROM tblRooms
    INNER JOIN tblHotels on htlID = rom_htlID
    ;
    """
    
    with get_db_connection() as conn:
        result = custom(get_romUUIDs_query, conn)


    for row in result:
        htlFrom = row['htlFrom']
        romID = row['romID']
        romUUID = row['romUUID']

        past = romUUID_romIDs.get(romUUID, {})
        past[htlFrom] = romID
        romUUID_romIDs[romUUID] = past
    
    query = """
            SELECT romUUID, avlDate, romID, avlBasePrice, avlDiscountPrice, romName, rom_htlID, htlFrom, romMealPlan
            FROM tblRooms
            INNER JOIN tblAvailabilityInfo ON romID = avl_romID
            INNER JOIN tblHotels ON htlID = rom_htlID 
            WHERE NOT romUUID IS NULL
            ;
        """

    with get_db_connection() as conn:
        
        rows = custom(query, conn)
        
        for i, row in enumerate(rows):

            rowIdentifier = '|'.join([row['romUUID'] or ' ', str(row['avlDate'])])
            other_room_index = rowIdentifier_rowIndex.get(rowIdentifier)
            
            if other_room_index is None or row['romUUID'] is None:
                rowIdentifier_rowIndex[rowIdentifier] = i
                continue
            
            del rowIdentifier_rowIndex[rowIdentifier]

            compare_rooms(row, rows[other_room_index], conn)
    
        add_single_available_rooms(rowIdentifier_rowIndex, conn)


def compare_rooms(room1, room2, conn):      
    if not room1['avlBasePrice'] == room2['avlBasePrice']:
        alrType = 'P'
        alrInfo = {
            room1['romID']: room1['avlBasePrice'],
            room2['romID']: room2['avlBasePrice'],
        }
    elif not room1['avlDiscountPrice'] == room2['avlDiscountPrice']:
        alrType = 'D'
        alrInfo = {
            room1['romID']: room1['avlDiscountPrice'],
            room2['romID']: room2['avlDiscountPrice'],
        }
    elif not room1['romMealPlan'] == room2['romMealPlan']:
        alrType = 'M'
        alrInfo = {
            room1['romID']: room1['romMealPlan'],
            room2['romID']: room2['romMealPlan'],
        }
    else:
        return
    
    romUUID = room1['romUUID']

    alrA_romID = romUUID_romIDs[romUUID]['A']
    alrS_romID = romUUID_romIDs[romUUID]['S']

    insert_select_id(table='tblAlert', key_value={
        "alrRoomUUID": romUUID, 
        "alrOnDate": room1['avlDate'],
        "alrType": alrType,
        "alrA_romID": alrA_romID,
        "alrS_romID": alrS_romID,
        'alrInfo': json.dumps(alrInfo)
    }, id_field=None, identifier_condition=None, conn=conn)


def add_single_available_rooms(rowIdentifier_rowIndex, conn):
    for rowIdentifier, index in rowIdentifier_rowIndex.items():
        romUUID, _ = rowIdentifier.split('|')

        if romUUID == " ":
            singlity_msg = "No mathcing UUID on other hotel."
        else:
            singlity_msg = "Reserved on other hotel in this date."

        alrInfo = {
            rows[index]['romID']: singlity_msg
            }

        alrA_romID = romUUID_romIDs[romUUID]['A']
        alrS_romID = romUUID_romIDs[romUUID]['S']

        insert_select_id(table='tblAlert', key_value={
            "alrRoomUUID": romUUID, 
            "alrOnDate": rows[index]['avlDate'],
            "alrType": 'R',
            "alrA_romID": alrA_romID,
            "alrS_romID": alrS_romID,
            "alrInfo": json.dumps(alrInfo)
        }, id_field=None, identifier_condition=None, conn=conn)

if __name__ == "__main__":
    main()        
