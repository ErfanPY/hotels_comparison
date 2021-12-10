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
                host=host or os.environ.get("MYSQL_HOST"),
                user=user or os.environ.get("MYSQL_USER"),
                password=password or os.environ.get("MYSQL_PASSWORD"),
                # port     = port      or os.environ.get("MYSQL_PORT"),
                database=database or os.environ.get("MYSQL_DATABASE")
            )
            break
        except Exception as e:
            logger.error(e)
            time.sleep(2)

    return cnx


def insert_select_id(table: str, key_value: dict, conn, id_field: str = None, identifier_condition: dict = None):
    if table == "tblAlert":
        logger.debug("\n".join([f"{k}: {v}" for k, v in key_value.items()]))
    curs = conn.cursor(buffered=True, dictionary=True)

    keys_string = ', '.join(key for key in key_value.keys())
    values_string = ', '.join('%s' for _ in range(len(key_value)))

    identifier_condition = key_value if not identifier_condition else identifier_condition
    identifier_string = ' AND '.join(
        f"{key} = '{value}'" for key, value in identifier_condition.items())

    insert_query = f"""
        INSERT INTO {table} ({keys_string})
        SELECT  
        {values_string}
        FROM (SELECT 1) A
        LEFT JOIN(
            SELECT 1 AS Dup
            FROM {table}
            WHERE {identifier_string}
        ) B
        ON TRUE
        WHERE B.Dup IS NULL
        LIMIT 1
    """
    try:
        start_time = time.time()
        curs.execute(insert_query, list(key_value.values()))
        conn.commit()
    except Exception as e:
        end_time = time.time() - start_time

        key_values_text = ",".join(f"{k}: {v}" for k, v in key_value.items())

        if "WSREP" in str(e):
            logger.error("WSREP deadlock/conflict. Retring")
            return -1
        elif e.errno == 2013:
            logger.error("Lost connection to MySQL server during query.")
            return -1
        else:
            logger.error(
                f"Insertion failed, time: {end_time:.2f}s, query: {insert_query}, [{key_values_text}]")
            logger.exception(e)
            raise e

    if not id_field is None:

        if type(id_field) == list:
            select_id_query = "SELECT {} from {} WHERE {}".format(
                ", ".join(id_field), table, identifier_string)
            curs.execute(select_id_query)
            return curs.fetchone()

        else:
            select_id_query = "SELECT {} from {} WHERE {}".format(
                id_field, table, identifier_string)
            curs.execute(select_id_query)
            row_id = curs.fetchone()

            if not row_id:
                logger.critical("No row was added to database.")
                return -1

            return str(row_id[id_field])


def custom(query_string: str, data: list = [], conn=None):
    curs = conn.cursor(buffered=True, dictionary=True)

    curs.execute(query_string, data)
    if curs._rowcount > -1:
        result = curs.fetchall()
    else:
        result = None

    conn.commit()

    return result
