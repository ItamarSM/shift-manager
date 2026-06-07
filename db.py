import psycopg2
import psycopg2.extras
import os

def get_conn():
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    return conn

def get_cursor(conn):
    return conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

def init_db():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS users (
                   id SERIAL PRIMARY KEY,
                   username TEXT UNIQUE,
                   password_hash TEXT,
                   city TEXT
                   )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS jobs (
                   id SERIAL PRIMARY KEY,
                   user_id INTEGER REFERENCES users(id),
                   name TEXT
                   )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS salary_config (
                   id SERIAL PRIMARY KEY,
                   job_id INTEGER REFERENCES jobs(id),
                   user_id INTEGER REFERENCES users(id),
                   regular_rate REAL,
                   shabbat_rate REAL
                   )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS shifts (
                   id SERIAL PRIMARY KEY,
                   job_id INTEGER REFERENCES jobs(id),
                   user_id INTEGER REFERENCES users(id),
                   clock_in TEXT,
                   clock_out TEXT,
                   hours_worked REAL,
                   earnings REAL,
                   day_of_week TEXT
                   )""")
    conn.commit()
    conn.close()
