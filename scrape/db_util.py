import logging
import os
import sys
import time

import mysql.connector

from scrape.critical_log import log_critical_error

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

    values = list(key_value.values())
    err_check = try_execute_function(execute_commit, curs=curs, conn=conn,
                                     insert_query=insert_query, values=values)

    logger.debug("'{}' called 'insert_select_id', table: {}, added {} rows".format(
        sys._getframe().f_back.f_code.co_name, table, curs.rowcount))

    if not err_check is None:
        return err_check

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
                log_critical_error("No row was added to database.")
                return -1

            return str(row_id[id_field])


def try_execute_function(func, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except Exception as e:

        if "WSREP" in str(e):
            logger.error("WSREP deadlock/conflict. Retring")
            return -1
        elif e.errno == 2013:
            logger.error("Lost connection to MySQL server during query.")
            return -1
        else:
            args_text = ', '.join(args)
            kwargs_text = ', '.join(f"{k}:{v}" for k, v in kwargs.items())

            logger.error(
                f"Database function failed, from: {sys._getframe().f_back.f_code.co_name} - args: {args_text} - kwargs: {kwargs_text}")
            logger.exception(e)
            raise e


def execute_commit(curs, conn, insert_query, values):
    curs.execute(insert_query, values)
    conn.commit()


def insert_multiple_room_info(conn, rooms_info_list):
    logger.debug("'{}' called 'insert_multiple_room_info'".format(
        sys._getframe().f_back.f_code.co_name))
    curs = conn.cursor()

    insert_query = """
        INSERT INTO tblAvailabilityInfo (avl_romID, avlDate, avlCrawlTime, avlInsertionDate, avlBasePrice, avlDiscountPrice)
        SELECT  
        %s, %s, %s, %s, %s, %s
        FROM (SELECT 1) A
        LEFT JOIN(
            SELECT 1 AS Dup
            FROM tblAvailabilityInfo
            WHERE avl_romID = %s AND avlDate = %s AND avlCrawlTime = %s
        ) B
        ON TRUE
        WHERE B.Dup IS NULL
        LIMIT 1
    """
    list_of_values = []
    for info in rooms_info_list:
        list_of_values.append(tuple(info.values())+(info['avl_romID'],
                                                    info['avlDate'], info['avlCrawlTime']))

    err_check = try_execute_function(
        execute_many_commit,
        curs=curs,
        conn=conn,
        insert_query=insert_query,
        list_of_values=list_of_values
    )

    if not err_check is None:
        return None


def execute_many_commit(curs, conn, insert_query, list_of_values):
    curs.executemany(insert_query, list_of_values)
    conn.commit()


def custom(query_string: str, data: list = [], conn=None):
    logger.debug("'{}' called 'custom' on '{}'".format(
        sys._getframe().f_back.f_code.co_name, query_string.split("\n")[1].strip()))

    curs = conn.cursor(buffered=True, dictionary=True)

    curs.execute(query_string, data)
    if curs._rowcount > -1:
        result = curs.fetchall()
    else:
        result = None

    conn.commit()

    return result
