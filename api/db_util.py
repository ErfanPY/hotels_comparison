import os

import mysql.connector


def get_db_connection(host=None, user=None, password=None, port=None, database=None):

    cnx = mysql.connector.connect(
        host     = host      or os.environ.get("MYSQL_HOST"),
        user     = user      or os.environ.get("MYSQL_USER"),
        password = password  or os.environ.get("MYSQL_PASSWORD"),
        # port     = port      or os.environ.get("MYSQL_PORT"),
        database = database  or os.environ.get("MYSQL_DATABASE")
    )

    return cnx


def select(table:str, select_columns:list, and_conditions:dict={}, extra_conditions:str="", conn=None):
    curs = conn.cursor(buffered=True, dictionary=True)

    select_columns_string = ', '.join(select_columns)
    
    and_string = ' WHERE ' if and_conditions.values() else ''
    and_string += ' AND '.join(f"{key} like '%{value}%'" for key, value in and_conditions.items() if value)
    
    select_id_query = "SELECT {} from {} {} {};".format(select_columns_string, table, and_string, extra_conditions)
    
    curs.execute(select_id_query)

    selected_columns = curs.fetchone()
    
    return selected_columns


def select_all(table:str, select_columns:list, and_conditions:dict={}, extra_conditions:str="", conn=None):
    curs = conn.cursor(buffered=True, dictionary=True)

    select_columns_string = ', '.join(select_columns)
    
    and_string = ' WHERE ' if and_conditions.values() else ''
    and_string += ' AND '.join(f"{key} like '%{value}%'" for key, value in and_conditions.items() if value)
    
    select_id_query = "SELECT {} from {} {} {};".format(select_columns_string, table, and_string, extra_conditions)
    
    curs.execute(select_id_query)

    selected_columns = curs.fetchall()
    
    return selected_columns


def custom(query_string:str, data:list=[], conn=None):
    curs = conn.cursor(buffered=True, dictionary=True)

    curs.execute(query_string, data)

    result = curs.fetchall()
    
    return result