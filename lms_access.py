import mysql.connector
from mysql.connector import Error
import requests
from dotenv import load_dotenv
import os
from typing import List, Dict, Tuple

# Load environment variables
load_dotenv()

class ContentProcessor:
    def __init__(self):
        self.token = None
        self.user_id = None
        self.moodle_user_id = None
        self.base_url = os.getenv('MOODLE_BASE_URL')

    def get_mysql_connection(self) -> mysql.connector.connection.MySQLConnection:
        """Establish MySQL connection"""
        config = {
            'user': os.getenv('MYSQL_USER'),
            'password': os.getenv('MYSQL_PASSWORD'),
            'host': os.getenv('MYSQL_HOST', 'localhost'),
            'database': os.getenv('MYSQL_DATABASE', 'user_course_db')
        }
        return mysql.connector.connect(**config)

    def populate_database(self):
        """Populate database with course content and URLs"""
        if not self.token or not self.user_id or not self.moodle_user_id:
            raise ValueError("Moodle API token, user_id, and moodle_user_id must be set")
            
        try:
            connection = self.get_mysql_connection()
            cursor = connection.cursor()
            
            # Clear existing data for the user
            cursor.execute("DELETE FROM pdf_urls WHERE user_id = %s", (self.user_id,))
            cursor.execute("DELETE FROM discussion_urls WHERE user_id = %s", (self.user_id,))
            connection.commit()

            # Get courses for the specific user
            params = {
                'wstoken': self.token,
                'moodlewsrestformat': 'json',
                'wsfunction': 'core_enrol_get_users_courses',
                'userid': self.moodle_user_id
            }
            
            response = requests.get(f"{self.base_url}/webservice/rest/server.php", params=params)
            response.raise_for_status()
            
            courses = response.json()
            
            for course in courses:
                # Insert course
                cursor.execute(
                    "INSERT IGNORE INTO courses (course_id, course_name) VALUES (%s, %s)",
                    (course['id'], course['fullname'])
                )
                connection.commit()
                
                # Get course contents
                content_params = {
                    'wstoken': self.token,
                    'moodlewsrestformat': 'json',
                    'wsfunction': 'core_course_get_contents',
                    'courseid': course['id']
                }
                
                content_response = requests.get(f"{self.base_url}/webservice/rest/server.php", params=content_params)
                content_response.raise_for_status()
                
                contents = content_response.json()
                
                for section in contents:
                    for module in section.get('modules', []):
                        # Process PDF files
                        if 'contents' in module:
                            for content in module['contents']:
                                if content.get('type') == 'file' and content.get('filename', '').lower().endswith(('.pdf', '.docx', '.pptx', '.txt')):
                                    file_url = f"{content['fileurl']}&token={self.token}"
                                    cursor.execute(
                                        "INSERT IGNORE INTO pdf_urls (course_id, user_id, pdf_url) VALUES (%s, %s, %s)",
                                        (course['id'], self.user_id, file_url)
                                    )
                                    
                        # Process forum discussions
                        if module.get('modname') == 'forum':
                            forum_id = module.get('instance')
                            if forum_id:
                                forum_params = {
                                    'wstoken': self.token,
                                    'moodlewsrestformat': 'json',
                                    'wsfunction': 'mod_forum_get_forum_discussions',
                                    'forumid': forum_id
                                }
                                
                                forum_response = requests.get(f"{self.base_url}/webservice/rest/server.php", params=forum_params)
                                if forum_response.status_code == 200:
                                    discussions = forum_response.json()
                                    if 'discussions' in discussions:
                                        for discussion in discussions['discussions']:
                                            discussion_url = f"{self.base_url}/mod/forum/discuss.php?d={discussion['discussion']}&token={self.token}"
                                            cursor.execute(
                                                "INSERT IGNORE INTO discussion_urls (course_id, user_id, discussion_url) VALUES (%s, %s, %s)",
                                                (course['id'], self.user_id, discussion_url)
                                            )
                
                connection.commit()
                
        except Exception as e:
            print(f"Error populating database: {str(e)}")
            raise
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'connection' in locals() and connection.is_connected():
                connection.close()

    def fetch_urls(self) -> Tuple[List[Dict], List[Dict]]:
        """Fetch PDF and discussion URLs from MySQL"""
        connection = self.get_mysql_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Fetch PDF URLs
        cursor.execute("""
            SELECT p.pdf_url, c.course_name, c.course_id 
            FROM pdf_urls p 
            JOIN courses c ON p.course_id = c.course_id
            WHERE p.user_id = %s
        """, (self.user_id,))
        pdf_urls = cursor.fetchall()
        
        # Fetch discussion URLs
        cursor.execute("""
            SELECT d.discussion_url, c.course_name, c.course_id 
            FROM discussion_urls d 
            JOIN courses c ON d.course_id = c.course_id
            WHERE d.user_id = %s
        """, (self.user_id,))
        discussion_urls = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return pdf_urls, discussion_urls

def main():
    processor = ContentProcessor()
    
    # Set required credentials (these should come from environment variables or user input)
    processor.token = os.getenv('MOODLE_TOKEN')
    processor.user_id = os.getenv('USER_ID')
    processor.moodle_user_id = os.getenv('MOODLE_USER_ID')
    
    # Populate database with course content
    print("Populating database with course content...")
    processor.populate_database()
    
    # Fetch URLs from MySQL
    print("\nFetching URLs from MySQL...")
    pdf_urls, discussion_urls = processor.fetch_urls()
    
    print(f"\nFound {len(pdf_urls)} PDF files and {len(discussion_urls)} discussions")

if __name__ == "__main__":
    main()