import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Get the DATABASE_URL from environment variables
DATABASE_URL = os.getenv('DATABASE_URL')

def test_connection(url):
    try:
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        cur.execute("SELECT 1")
        result = cur.fetchone()
        print("Connection successful:", result)
        cur.close()
        conn.close()
    except Exception as e:
        print("Connection failed:", str(e))

if __name__ == "__main__":
    if DATABASE_URL:
        print("Testing connection with DATABASE_URL")
        test_connection(DATABASE_URL)
    else:
        print("DATABASE_URL not found in environment variables")