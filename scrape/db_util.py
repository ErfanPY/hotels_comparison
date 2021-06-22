from scrape.config import Config

import mysql.connector


def get_db_connection(host=None, user=None, password=None, port=None, database=None):
    cnx = mysql.connector.connect(
        host     = host     or Config.DATABASE_HOST,
        user     = user     or Config.DATABASE_USER,
        password = password or Config.DATABASE_PASSWORD,
        port     = port     or Config.DATABASE_PORT,
        database = database  or Config.DATABASE_NAME
    )

    return cnx


def insert_select_id(table:str, key_value:dict, id_field:str, identifier_condition, conn):
    curs = conn.cursor(buffered=True, dictionary=True)

    keys_string = ', '.join(key for key in key_value.keys())
    values_string = ', '.join('%s' for _ in range(len(key_value)))

    update_string = ', '.join("`{0}`=VALUES(`{0}`)".format(name) for name in key_value.keys())
    insert_string = "INSERT INTO  {} ({}) VALUES ({}) ON DUPLICATE KEY UPDATE {};".format(table, keys_string, values_string, update_string)
    # insert_string = "INSERT IGNORE INTO  {} ({}) VALUES ({});".format(table, keys_string, values_string)
    
    curs.execute(insert_string, list(key_value.values()))
    conn.commit()

    if not id_field is None:
        identifier_string = ' AND '.join(f"{key} like '%{str(value)[:49]}%'" for key, value in identifier_condition.items())
        select_id_query = "SELECT {} from {} WHERE {}".format(id_field, table, identifier_string)
        
        curs.execute(select_id_query)

        row_id = curs.fetchone()[id_field]
        
        return str(row_id)



def update(table:str, key_value:dict, condition:str, conn):
    curs = conn.cursor(buffered=True)

    key_value_string = ', '.update(key+' = ?' for key in key_value.keys())

    query_string = "UPDATE {} SET {} WHERE {}".format(table, key_value_string, condition)
    
    res = curs.execute(query_string, list(key_value.values()))
    
    conn.commit()
    return res


# select
