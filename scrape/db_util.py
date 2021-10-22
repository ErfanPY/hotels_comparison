import os
import time

import mysql.connector
import logging

logger = logging.getLogger("main_logger")


def get_db_connection(host=None, user=None, password=None, port=None, database=None):
    counter = 0
    while True:
        try:
            cnx = mysql.connector.connect(
                host     = host      or os.environ.get("MYSQL_HOST"),
                user     = user      or os.environ.get("MYSQL_USER"),
                password = password  or os.environ.get("MYSQL_PASSWORD"),
                # port     = port      or os.environ.get("MYSQL_PORT"),
                database = database  or os.environ.get("MYSQL_DATABASE")
            )
            break
        except Exception as e:
            logger.error(e)
            time.sleep(2)
    
    return cnx


def insert_select_id(table:str, key_value:dict, id_field:str, identifier_condition, conn):
    curs = conn.cursor(buffered=True, dictionary=True)

    keys_string = ', '.join(key for key in key_value.keys())
    values_string = ', '.join('%s' for _ in range(len(key_value)))

    update_string = ', '.join("`{0}`=VALUES(`{0}`)".format(name) for name in key_value.keys())
    insert_string = "INSERT INTO  {} ({}) VALUES ({}) ON DUPLICATE KEY UPDATE {};".format(table, keys_string, values_string, update_string)

    try:
        start_time = time.time()
        curs.execute(insert_string, list(key_value.values()))
        conn.commit()
    except Exception as e:
        end_time = time.time() - start_time

        key_values_text = ",".join(f"{k}: {v}" for k, v in key_value.items())
        logger.error(f"Insertion failed, time: {end_time:.2f}s, query: {insert_string}, [{key_values_text}]")
        logger.exception(e)
        
        raise e


    if not id_field is None:
        identifier_string = ' AND '.join(f"{key} like '%{value}%'" for key, value in identifier_condition.items())

        if type(id_field) == list:
            select_id_query = "SELECT {} from {} WHERE {}".format(", ".join(id_field), table, identifier_string)
            curs.execute(select_id_query)
            return curs.fetchone()
            
        else:
            select_id_query = "SELECT {} from {} WHERE {}".format(id_field, table, identifier_string)
            
            curs.execute(select_id_query)

            row_id = curs.fetchone()[id_field]
            
            return str(row_id)


def custom(query_string:str, data:list=[], conn=None):
    curs = conn.cursor(buffered=True, dictionary=True)

    curs.execute(query_string, data)
    if curs._rowcount > -1:
        result = curs.fetchall()
    else:
        result = None

    conn.commit()
    
    return result
