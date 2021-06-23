import json
from scrape.db_util import custom, get_db_connection, insert_select_id

rows = []

def main():
    global rows
    rowIdentifier_rowIndex = {}

    with get_db_connection() as conn:
        query = """
            SELECT romUUID, romID, avlBasePrice,avlDAte, avlDiscountPrice, romName, rom_htlID
            FROM tblRooms
            INNER JOIN tblAvailabilityInfo ON romID = avl_romID

            GROUP BY romID
            ;
        """
        rows = custom(query)
        
        for i, row in enumerate(rows):

            rowIdentifier = '|'.join(['' or row['romUUID'], row['avlDate']])
            other_room_index = rowIdentifier_rowIndex.get(rowIdentifier)
            
            if other_room_index is None or row['romUUID'] is None:
                rowIdentifier_rowIndex[rowIdentifier] = i
                continue
            
            del rowIdentifier_rowIndex[rowIdentifier]

            compare_rooms(row, rows[other_room_index])
    
    add_single_available_rooms(rowIdentifier_rowIndex)


def compare_rooms(room1, room2):       
    if not room1['avlBasePrice'] == room2['avlBasePrice']:
        alrType = 'P'
        alrInfo = {
            room1['romID']: room1['avlBasePrice'],
            room2['romID']: room2['avlBasePrice'],
        }
    if not room1['avlDiscountPrice'] == room2['avlDiscountPrice']:
        alrType = 'D'
        alrInfo = {
            room1['romID']: room1['avlDiscountPrice'],
            room2['romID']: room2['avlDiscountPrice'],
        }
    
    insert_select_id(table='', key_value={
        'alrType': alrType,
        'alrRoomUUID': room1['romUUID'],
        'alrInfo': json(alrInfo)
    }, id_field=None, identifier_condition=None)
 

def add_single_available_rooms(rowIdentifier_rowIndex):
    for rowIdentifier, _ in rowIdentifier_rowIndex.items():
        romUUID, index = rowIdentifier.split('|')

        if romUUID == "":
            singlity_msg = "No mathcing room found on other hotel."
        else:
            singlity_msg = "Not alailable on this date."

        alrInfo = {
            rows[index]['romID']: singlity_msg
        }
    
        insert_select_id(table='', key_value={
            'alrType': 'R',
            'alrRoomUUID': romUUID,
            'alrInfo': json(alrInfo)
        }, id_field=None, identifier_condition=None)

if __name__ == "__main__":
    main()        
