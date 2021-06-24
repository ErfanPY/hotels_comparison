import json
from scrape.db_util import custom, get_db_connection, insert_select_id

rows = []

def main():
    global rows
    rowIdentifier_rowIndex = {}

    with get_db_connection() as conn:
        query = """
            SELECT romUUID, romID, avlBasePrice,avlDate, avlDiscountPrice, romName, rom_htlID
            FROM tblRooms
            INNER JOIN tblAvailabilityInfo ON romID = avl_romID
            WHERE NOT romUUID IS NULL
            ;
        """
        rows = custom(query, conn)
        
        for i, row in enumerate(rows):

            rowIdentifier = '|'.join([' ' or row['romUUID'], str(row['avlDate'])])
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
    else:
        return
    insert_select_id(table='tblAlert', key_value={
        'alrType': alrType,
        'alrRoomUUID': room1['romUUID'],
        'alrInfo': json.dumps(alrInfo)
    }, id_field=None, identifier_condition=None, conn=conn)
 

def add_single_available_rooms(rowIdentifier_rowIndex, conn):
    for rowIdentifier, index in rowIdentifier_rowIndex.items():
        romUUID, _ = rowIdentifier.split('|')

        if romUUID == " ":
            singlity_msg = "No mathcing room found on other hotel."
        else:
            singlity_msg = "Not alailable on this date."

        alrInfo = {
            rows[index]['romID']: singlity_msg
        }
    
        insert_select_id(table='tblAlert', key_value={
            'alrType': 'R',
            'alrRoomUUID': romUUID,
            'alrInfo': json.dumps(alrInfo)
        }, id_field=None, identifier_condition=None, conn=conn)

if __name__ == "__main__":
    main()        
