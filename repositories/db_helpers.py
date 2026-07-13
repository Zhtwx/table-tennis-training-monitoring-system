from pymysql import MySQLError

from db import get_mysql_connection


DATABASE_SETUP_ERROR_CODES = {1045, 1049, 1146, 2002, 2003, 2005, 2006}


def is_database_setup_error(exc):
    code = exc.args[0] if exc.args and isinstance(exc.args[0], int) else None
    return code in DATABASE_SETUP_ERROR_CODES


def fetch_all(query, params=None):
    connection = get_mysql_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.fetchall()
    finally:
        connection.close()


def fetch_one(query, params=None):
    connection = get_mysql_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.fetchone()
    finally:
        connection.close()


def execute_write(query, params=None):
    connection = get_mysql_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, params or ())
            last_id = cursor.lastrowid
        connection.commit()
        return last_id
    except MySQLError:
        connection.rollback()
        raise
    finally:
        connection.close()


def execute_affected(query, params=None):
    connection = get_mysql_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, params or ())
            affected = cursor.rowcount
        connection.commit()
        return affected
    except MySQLError:
        connection.rollback()
        raise
    finally:
        connection.close()


def execute_many(query, params_list):
    connection = get_mysql_connection()
    try:
        with connection.cursor() as cursor:
            cursor.executemany(query, params_list)
        connection.commit()
    except MySQLError:
        connection.rollback()
        raise
    finally:
        connection.close()
