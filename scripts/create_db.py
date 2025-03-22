import psycopg2
from psycopg2 import sql
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def create_database(conn_str, dbname):
    """Creates the database if it doesn't exist."""
    try:
        conn_params = psycopg2.connect(conn_str.replace(f"/{dbname}", "/postgres"))
        conn_params.autocommit = True  # Autocommit to avoid transaction issues
        cur = conn_params.cursor()
        cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(dbname)))
        cur.close()
        conn_params.close()
        print(f"Database '{dbname}' created successfully!")
    except psycopg2.ProgrammingError as e:
        if "already exists" in str(e).lower():
            print(f"Database '{dbname}' already exists.")
        else:
            print(f"Error creating database: {e}")
    except psycopg2.Error as e:
        print(f"Error connecting to default database: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during database creation: {e}")

def create_tables(conn):
    """Creates the 'businesses', 'contacts', and 'business_contacts' tables."""
    cur = conn.cursor()

    # Create the 'businesses' table
    cur.execute(sql.SQL("""
        CREATE TABLE IF NOT EXISTS businesses (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) UNIQUE NOT NULL,
            industry VARCHAR(255),
            location VARCHAR(255)
        );
    """))

    # Create the 'contacts' table
    cur.execute(sql.SQL("""
        CREATE TABLE IF NOT EXISTS contacts (
            id SERIAL PRIMARY KEY,
            first_name VARCHAR(255) NOT NULL,
            last_name VARCHAR(255) NOT NULL,
            email VARCHAR(255) UNIQUE,
            phone VARCHAR(20),
            title VARCHAR(255)
        );
    """))

    # Create the join table 'business_contacts'
    cur.execute(sql.SQL("""
        CREATE TABLE IF NOT EXISTS business_contacts (
            business_id INTEGER REFERENCES businesses(id) ON DELETE CASCADE,
            contact_id INTEGER REFERENCES contacts(id) ON DELETE CASCADE,
            PRIMARY KEY (business_id, contact_id)
        );
    """))

    conn.commit()
    cur.close()
    print("Tables created successfully!")

def main():
    """Main function to create database and tables."""
    try:
        dbname = DATABASE_URL.split('/')[-1]
        conn_str = DATABASE_URL.replace(f"/{dbname}", "/postgres")
        create_database(conn_str, dbname)

        #conn = psycopg2.connect(DATABASE_URL)
        #create_tables(conn)

    except psycopg2.Error as e:
        print(f"Error creating tables or connecting to the database: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
    #    if conn:
    #        conn.close()
        print("Database connection closed.")

if __name__ == "__main__":
    main()