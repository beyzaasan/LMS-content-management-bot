import mysql.connector
from mysql.connector import errorcode
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Configuration details for the MySQL connection
config = {
    'user': os.getenv('MYSQL_USER'),
    'password': os.getenv('MYSQL_PASSWORD'),
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'database': os.getenv('MYSQL_DATABASE', 'user_course_db')  # Updated database name
}

try:
    # Connect to MySQL server
    connection = mysql.connector.connect(
        user=config['user'],
        password=config['password'],
        host=config['host']
    )

    cursor = connection.cursor()


    # Create database if it does not exist
    try:
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {config['database']};")
        print(f"Database '{config['database']}' is ready.")
    except mysql.connector.Error as err:
        print(f"Failed to create database: {err}")

    # Use the database
    connection.database = config['database']

    # Drop tables in the correct order due to foreign key dependencies
    # Drop tables that reference other tables first

    # Drop tables that might reference 'collections'
    cursor.execute("DROP TABLE IF EXISTS collection_files;")
    print("Dropped existing 'collection_files' table (if it existed).")

    cursor.execute("DROP TABLE IF EXISTS pdf_urls;")
    print("Dropped existing 'pdf_urls' table.")

    cursor.execute("DROP TABLE IF EXISTS discussion_urls;")
    print("Dropped existing 'discussion_urls' table.")

    cursor.execute("DROP TABLE IF EXISTS course_urls;") # Assuming this might also have FKs
    print("Dropped existing 'course_urls' table.")

    # IMPORTANT: Drop 'collections' table before 'users' if it exists and references 'users'
    cursor.execute("DROP TABLE IF EXISTS collections;")
    print("Dropped existing 'collections' table (if it existed).")

    cursor.execute("DROP TABLE IF EXISTS courses;")
    print("Dropped existing 'courses' table.")

    cursor.execute("DROP TABLE IF EXISTS users;")
    print("Dropped existing 'users' table.")


    # Define users table creation query
    create_users_table_query = """
    CREATE TABLE IF NOT EXISTS users (
        user_id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(255) NOT NULL UNIQUE,
        password VARCHAR(255) NOT NULL,
        moodle_user_key VARCHAR(255) ,
        moodle_user_id VARCHAR(255)
    );
    """

    # Execute the table creation query
    cursor.execute(create_users_table_query)
    print("Table 'users' is ready.")

     # Define courses table creation query
    create_courses_table_query = """
    CREATE TABLE IF NOT EXISTS courses (
        course_id INT PRIMARY KEY,
        course_name VARCHAR(255) NOT NULL
    );
    """

    # Execute the table creation query
    cursor.execute(create_courses_table_query)
    print("Table 'courses' is ready.")


    # Define pdf_urls table creation query
    create_pdf_urls_table_query = """
    CREATE TABLE IF NOT EXISTS pdf_urls (
        id INT AUTO_INCREMENT PRIMARY KEY,
        course_id INT NOT NULL,
        user_id INT NOT NULL,
        pdf_url TEXT,
        FOREIGN KEY (course_id) REFERENCES courses(course_id),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );
    """

    # Execute the table creation query
    cursor.execute(create_pdf_urls_table_query)
    print("Table 'pdf_urls' is ready.")

    # Define discussion_urls table creation query
    create_discussion_urls_table_query = """
    CREATE TABLE IF NOT EXISTS discussion_urls (
        id INT AUTO_INCREMENT PRIMARY KEY,
        course_id INT NOT NULL,
        user_id INT NOT NULL,
        discussion_url TEXT,
        FOREIGN KEY (course_id) REFERENCES courses(course_id),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );
    """

    # Execute the table creation query
    cursor.execute(create_discussion_urls_table_query)
    print("Table 'discussion_urls' is ready.")


    # Load user_key from .env
    moodle_user_key = os.getenv('MOODLE_USER_KEY')
    moodle_user_id = os.getenv('MOODLE_USER_ID')
    moodle_user_key2 = os.getenv('MOODLE_USER_KEY2')
    moodle_user_id2 = os.getenv('MOODLE_USER_ID2')

    # Example values to insert into the 'users' table
    username = 'user'
    username2 = 'user2'
    password = '123'

    # Insert user data into the table
    insert_user_query = """
    INSERT INTO users (username, password, moodle_user_key, moodle_user_id)
    VALUES (%s, %s, %s, %s);
    """
    cursor.execute(insert_user_query, (username, password, moodle_user_key, moodle_user_id))
    cursor.execute(insert_user_query, (username2, password, moodle_user_key2, moodle_user_id2))

    connection.commit()
    user_id = cursor.lastrowid
    print(f"User '{username2}' inserted into the 'users' table with ID: {user_id}.")

except mysql.connector.Error as err:
    if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        print("Invalid credentials. Please check your username and password.")
    elif err.errno == errorcode.ER_BAD_DB_ERROR:
        print("Database does not exist and cannot be created.")
    else:
        print(err)

finally:
    # Close the cursor and connection
    if 'cursor' in locals():
        cursor.close()
    if 'connection' in locals() and connection.is_connected():
        connection.close()
