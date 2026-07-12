import os

import pymysql
from dotenv import load_dotenv
from pymysql.cursors import DictCursor


load_dotenv()


def get_mysql_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "coach_app"),
        password=os.getenv("DB_PASSWORD", "Coach2026#"),
        database=os.getenv("DB_NAME", "pingpang_db"),
        charset="utf8mb4",
        cursorclass=DictCursor,
        connect_timeout=int(os.getenv("DB_CONNECT_TIMEOUT", 1)),
        autocommit=False,
    )
