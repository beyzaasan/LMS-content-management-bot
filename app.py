from gc import collect
import json
import streamlit as st
import mysql.connector
from mysql.connector import errorcode
import os
from dotenv import load_dotenv
#from ExamQuestionAgent import ExamQuestionAgent
import ChatBotAgent
from RAG import ChromaDBManager, RetrieveDocuments, TextProcessor
from StudyAgent import StudyAgent
from lms_access import ContentProcessor
import time
from ReminderAgent import ReminderAgent
from ChatBotAgent import ChatBotAgent
import chromadb
from chromadb.config import Settings
from chromadb import PersistentClient

# Load environment variables
load_dotenv()

# Function to process LMS content
def process_lms_content(user_id, moodle_key, moodle_id):
    """Process LMS content using ContentProcessor"""
    try:
        processor = ContentProcessor()
        processor.token = moodle_key
        processor.user_id = user_id
        processor.moodle_user_id = moodle_id
        
        # Debug: Print the values to see what's being passed
        print(f"Debug - Token: {moodle_key}")
        print(f"Debug - User ID: {user_id}")
        print(f"Debug - Moodle User ID: {moodle_id}")
        
        # Check if values are set
        if not moodle_key or not user_id or not moodle_id:
            return False, f"Missing values - Token: {bool(moodle_key)}, User ID: {bool(user_id)}, Moodle ID: {bool(moodle_id)}"
        
        # Populate database with course content
        processor.populate_database()
        
        return True, "LMS content processed successfully!"
    except Exception as e:
        return False, f"Error processing LMS content: {str(e)}"

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'moodle_key' not in st.session_state:
    st.session_state.moodle_key = None
if 'moodle_id' not in st.session_state:
    st.session_state.moodle_id = None
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'main'
if 'selected_course' not in st.session_state:
    st.session_state.selected_course = None
if 'assistant_page' not in st.session_state:
    st.session_state.assistant_page = False
if 'selected_agent' not in st.session_state:
    st.session_state.selected_agent = None
if 'selected_files' not in st.session_state:
    st.session_state.selected_files = []

# Database connection

def get_db_connection():
    """Create database connection"""
    return mysql.connector.connect(
        user=os.getenv('MYSQL_USER'),
        password=os.getenv('MYSQL_PASSWORD'),
        host=os.getenv('MYSQL_HOST', 'localhost'),
        database=os.getenv('MYSQL_DATABASE', 'user_course_db')
    )

def get_available_collections():
    """Get list of available ChromaDB collections"""
    try:
        client = PersistentClient(
            path='./ChromaDbPersistent',
            settings=Settings(),
            tenant="default_tenant",
            database="default_database"
        )
        collections = client.list_collections()
        return [collection.name for collection in collections]
    except Exception as e:
        print(f"Error fetching collections: {str(e)}")
        return []
    
# User management functions

def sign_up(username, password, moodle_key, moodle_id):
    """Handle user registration"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if username already exists
        cursor.execute("SELECT username FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            return False, "Username already exists"
        
        # Insert new user
        insert_query = """
        INSERT INTO users (username, password, moodle_user_key, moodle_user_id)
        VALUES (%s, %s, %s, %s)
        """
        cursor.execute(insert_query, (username, password, moodle_key, moodle_id))
        conn.commit()
        
        return True, "Registration successful! Please sign in."
    except mysql.connector.Error as err:
        return False, f"Database error: {str(err)}"
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def sign_in(username, password):
    """Handle user authentication"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Check credentials and get Moodle information
        cursor.execute("""
            SELECT user_id, username, moodle_user_key, moodle_user_id 
            FROM users 
            WHERE username = %s AND password = %s
        """, (username, password))
        
        user = cursor.fetchone()
        if user:
            return True, user
        return False, "Invalid credentials"
    except mysql.connector.Error as err:
        return False, f"Database error: {str(err)}"
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

# Course content display

def display_course_content(course_id, course_name):
    """Display content for a specific course"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        st.title(f"{course_name}")
        
        # Add back button
        if st.button("Back to Courses"):
            st.session_state.current_page = 'main'
            st.session_state.selected_course = None
            st.rerun()
        
        # Fetch PDFs for this course
        cursor.execute("""
            SELECT DISTINCT pdf_url 
            FROM pdf_urls 
            WHERE course_id = %s AND user_id = %s
        """, (course_id, st.session_state.user_id))
        pdfs = cursor.fetchall()
        
        if pdfs:
            st.subheader("PDF Documents")
            for pdf in pdfs:
                st.markdown(f"- [{os.path.basename(pdf['pdf_url'])}]({pdf['pdf_url']})")

    except mysql.connector.Error as err:
        st.error(f"Error fetching course content: {str(err)}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

# Course list display

def display_course_list():
    """Display list of courses as expanders"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Fetch courses
        cursor.execute("""
            SELECT DISTINCT c.course_id, c.course_name 
            FROM courses c
            INNER JOIN (
                SELECT course_id FROM pdf_urls WHERE user_id = %s
                UNION
                SELECT course_id FROM discussion_urls WHERE user_id = %s
                ) AS user_courses ON c.course_id = user_courses.course_id
                ORDER BY c.course_name
        """, (st.session_state.user_id, st.session_state.user_id))
        
        courses = cursor.fetchall()
        
        if not courses:
            st.warning("No courses found. Please process LMS content first.")
            return

        st.title("Your Courses")
        
        # Display courses as expanders
        for course in courses:
            with st.expander(f"📚 {course['course_name']}"):
                if st.button("Open Course", key=f"course_{course['course_id']}"):
                    st.session_state.current_page = 'course'
                    st.session_state.selected_course = {
                        'id': course['course_id'],
                        'name': course['course_name']
                    }
                    st.rerun()

        # Add a single assistant button at the bottom
        if st.button("Go to Assistant"):
            st.session_state.assistant_page = True
            st.rerun()

    except mysql.connector.Error as err:
        st.error(f"Error fetching courses: {str(err)}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

# Assistant page with file upload functionality

# Update the display_assistant_page function
def display_assistant_page():
    """Display assistant page with agents and file upload in sidebar"""
    st.sidebar.title("Agents")
    
    # Get available collections
    collections = get_available_collections()
    
    # Collection selector
    if collections:
        selected_collection = st.sidebar.selectbox(
            "Select Your Library:",
            options=collections,
            key="collection_selector"
        )
    else:
        st.sidebar.warning("No collections available. Please upload and process files first.")
        selected_collection = None

    agents = ["💬 Chat with Your Libraries!", "📚 Study Helper", "🗓️ Reminder"]

    for agent in agents:
        if st.sidebar.button(agent):
            st.session_state.selected_agent = agent

    st.sidebar.title("Upload Files")
    uploaded_files = st.sidebar.file_uploader("Upload your documents:", accept_multiple_files=True, type=["pdf", "txt", "docx", "pptx"])
    collection_name = st.sidebar.text_input("Enter the library name:")
    if uploaded_files and collection_name and st.sidebar.button("Process Files"):
        process_uploaded_files(uploaded_files, collection_name)

    st.title("Assistant Page")

    if st.session_state.selected_agent and selected_collection:
        st.header(f"{st.session_state.selected_agent}")

        if st.session_state.selected_agent == "💬 Chat with Your Libraries!":
            chat_history = []  # Initialize an empty list for chat history
            chatbot_agent_interface(selected_collection, chat_history)

        elif st.session_state.selected_agent == "📚 Study Helper":
            study_agent_interface(selected_collection)

        elif st.session_state.selected_agent == "🗓️ Reminder":
            reminder_agent_interface(selected_collection)
    elif st.session_state.selected_agent and not selected_collection:
        st.warning("Please select a collection to continue.")
    else:
        st.info("Please select an agent and a collection to begin.")


def chatbot_agent_interface(collection_name, chat_history):
    # if chat_history is None:
    #     chat_history = []
    st.title("ChatBot Study Assistant")
    
    try:
        # Initialize ChatBot Agent
        agent = ChatBotAgent(course_id=collection_name)
        st.success("ChatBot Agent initialized successfully!")
    except Exception as e:
        st.error(f"Error initializing ChatBot Agent: {str(e)}")
        return chat_history

    # Create a clean, modern interface
    st.markdown("""
        <style>
        .chat-message {
            padding: 1rem;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
        }
        .user-message {
            background-color: #f0f2f6;
        }
        .assistant-message {
            background-color: #e8f0fe;
        }
        </style>
    """, unsafe_allow_html=True)
    
    
    # # Display the previous chat history
    # for message in chat_history:
    #     if message['role'] == 'user':
    #         with st.chat_message("user", avatar="🧑‍💻"):
    #             st.markdown(message['content'])
    #     else:
    #         with st.chat_message("assistant", avatar="🤖"):
    #             st.markdown(message['content'])

    # Create a scrollable chat container
    with st.container():
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)

        # Display the previous chat history (user and assistant messages)
        for message in chat_history:
            if message['role'] == 'user':
                with st.chat_message("user", avatar="🧑‍💻"):
                    st.markdown(message['content'])
            else:
                with st.chat_message("assistant", avatar="🤖"):
                    st.markdown(message['content'])

        st.markdown('</div>', unsafe_allow_html=True)


    # Input area with placeholder text
    user_input = st.chat_input(
        placeholder="Ask me anything about the course material..."
    )

    # Process user input
    if user_input and collection_name:
        
        # Add the user message to chat history
        chat_history.append({"role": "user", "content": user_input})

        # Display user message
        with st.chat_message("user", avatar="🧑‍💻"):
            st.markdown(user_input)
        
        try:
            
            # Combine chat history and user input for agent context
            full_conversation = "\n".join([message['content'] for message in chat_history])
                    
            # Get response from agent with loading indicator
            with st.spinner("Thinking..."):
                response = agent.respond(full_conversation)
            
            # Display assistant response
            with st.chat_message("assistant", avatar="🤖"):
                try:
                    
                    

                    response_data = json.loads(response)
                    
                    if "error" in response_data:
                        st.error(response_data["error"])
                        if "suggestion" in response_data:
                            st.info(response_data["suggestion"])
                    else:
                        
                        # Display structured response components
                        response_content = ""
                        
                        
                        # Display structured response components
                        if "summary" in response_data:
                            st.markdown("### Summary")
                            st.write(response_data["summary"])
                        
                        if "key_concepts" in response_data and response_data["key_concepts"]:
                            st.markdown("### Key Concepts")
                            for concept in response_data["key_concepts"]:
                                st.markdown(f"- {concept}")
                        
                        if "detailed_explanation" in response_data:
                            st.markdown("### Detailed Explanation")
                            st.write(response_data["detailed_explanation"])
                        
                        if "related_topics" in response_data and response_data["related_topics"]:
                            st.markdown("### Related Topics")
                            for topic in response_data["related_topics"]:
                                st.markdown(f"- {topic}")
                        
                        if "source_reference" in response_data:
                            st.markdown("### Source Reference")
                            st.info(response_data["source_reference"])
                        
                        if "confidence_level" in response_data:
                            confidence_color = {
                                "HIGH": "green",
                                "MEDIUM": "orange",
                                "LOW": "red"
                            }.get(response_data["confidence_level"], "gray")
                            st.markdown(f"<span style='color: {confidence_color}'>Confidence Level: {response_data['confidence_level']}</span>", unsafe_allow_html=True)
                           
                        st.markdown(response_content)

                        # Add assistant message to chat history
                        chat_history.append({"role": "assistant", "content": response_content})

                except json.JSONDecodeError:
                    # Fallback for non-JSON responses
                    st.write(response)
                    chat_history.append({"role": "assistant", "content": response})

        
        except Exception as e:
            # Handle errors gracefully
            error_message = f"An error occurred: {str(e)}"
            st.error(error_message)
            st.warning("Please try rephrasing your question or try again later.")
            chat_history.append({"role": "assistant", "content": error_message})
            
    return chat_history
        
def study_agent_interface(collection_name):
    
    
    with st.container():
        st.markdown('<div class="study-header">', unsafe_allow_html=True)
        st.write("📚 Practice and test your knowledge")
        st.markdown('</div>', unsafe_allow_html=True)  
    
    if not collection_name:
        st.error("Please provide a collection name first")
        return
    
    # Initialize session state for question management if not exists
    if 'current_questions' not in st.session_state:
        st.session_state.current_questions = None
    if 'current_question_index' not in st.session_state:
        st.session_state.current_question_index = 0
    if 'user_answers' not in st.session_state:
        st.session_state.user_answers = {}
    if 'feedback' not in st.session_state:
        st.session_state.feedback = None
    
    # Get topic or query from user
    topic = st.text_input(
        "Enter a topic or query:", 
        placeholder="Type a topic or agent task (e.g., 'provide exam question, topic')..."
    )
    
    def get_current_question():
        if not st.session_state.current_questions:
            return None
        
        all_questions = []
        for q_type in ['multiple_choice', 'true_false', 'open_ended']:
            if q_type in st.session_state.current_questions:
                for q in st.session_state.current_questions[q_type]:
                    all_questions.append((q_type, q))
        
        if not all_questions:
            return None
        
        if st.session_state.current_question_index >= len(all_questions):
            st.session_state.current_question_index = len(all_questions) - 1
            
        return all_questions[st.session_state.current_question_index]

    if topic:
        # Generate questions button
        if st.button("Generate Questions"):
            try:
                study_agent = StudyAgent(course_id=collection_name)
                with st.spinner("Generating questions..."):
                    query = topic.strip()
                    questions = study_agent.prepare_exam_question(query=query)
                    questions_dict = json.loads(questions)
                    
                    if "Error" in questions_dict:
                        st.error(questions_dict["Error"])
                    else:
                        st.session_state.current_questions = questions_dict
                        st.session_state.current_question_index = 0
                        st.session_state.user_answers = {}
                        st.session_state.feedback = None
                        st.rerun()
                        
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                return
    
    # Display current question and navigation
    if st.session_state.current_questions:
        current = get_current_question()
        
        if current:
            question_type, question_data = current
            
            # Display progress
            total_questions = sum(len(st.session_state.current_questions.get(qt, [])) 
                                for qt in ['multiple_choice', 'true_false', 'open_ended'])
            st.progress((st.session_state.current_question_index + 1) / total_questions)
            st.write(f"Question {st.session_state.current_question_index + 1} of {total_questions}")
            
            # Display question
            st.subheader(question_data['question'])
            
            # Handle different question types
            if question_type == 'multiple_choice':
                answer = st.radio("Select your answer:", question_data['options'], key=f"q_{st.session_state.current_question_index}")
                
            elif question_type == 'true_false':
                answer = st.radio("Select your answer:", ['True', 'False'], key=f"q_{st.session_state.current_question_index}")
                
            elif question_type == 'open_ended':
                answer = st.text_area("Your answer:", key=f"q_{st.session_state.current_question_index}")
            
            # Submit answer button
            if st.button("Submit Answer"):
                study_agent = StudyAgent(course_id=collection_name)
                evaluation = study_agent.evaluate_answer({question_type: [question_data]}, answer)
                evaluation_dict = json.loads(evaluation)
                
                if "evaluation" in evaluation_dict:
                    if evaluation_dict["evaluation"]["is_correct"]:
                        st.success("Doğru cevapladınız!")
                    else:
                        st.error("Yanlış cevap.")
                        st.write(f"Doğru cevap: {evaluation_dict['evaluation']['correct_answer']}")
                        st.write(f"Açıklama: {evaluation_dict['evaluation']['explanation']}")
            
            # Navigation buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Previous", disabled=st.session_state.current_question_index == 0):
                    st.session_state.current_question_index -= 1
                    st.session_state.feedback = None
                    st.rerun()
                    
            with col2:
                if st.button("Next", disabled=st.session_state.current_question_index == total_questions - 1):
                    st.session_state.current_question_index += 1
                    st.session_state.feedback = None
                    st.rerun()

    else:
     st.info("Please enter a topic and generate questions to begin.")
        
def reminder_agent_interface(collection_name):
    st.title("Reminder Agent")
    
    # User inputs
    current_week = st.text_input("Enter the current week:", placeholder="e.g., 'Week 5'")
    query = st.text_input("Enter a query:", placeholder="Type a task (e.g., 'search upcoming activities')...")
    
    if current_week and query:
        if st.button("Search Activities"):
            # Initialize Reminder Agent
            agent = ReminderAgent(course_id=collection_name)
            
            # Search for upcoming activities
            with st.spinner("Searching for upcoming activities..."):
                response = agent.search_upcoming_activities(query=query, current_week=current_week)
                
                try:
                    # Parse JSON response
                    data = json.loads(response)
                    
                    # Create two columns for activities and reminders
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.header("📅 Upcoming Activities")
                        if "activities" in data:
                            for activity in data["activities"]:
                                with st.expander(f"{activity['type'].title()} - {activity['date']}"):
                                    st.markdown(f"""
                                        **Description:** {activity['description']}  
                                        **Week:** {activity['week_number']}  
                                        **Date:** {activity['date']}
                                    """)
                        else:
                            st.info("No upcoming activities found.")
                    
                    with col2:
                        st.header("⚠️ Reminders")
                        if "reminders" in data:
                            for reminder in data["reminders"]:
                                if reminder["type"] == "urgent":
                                    st.error(reminder["message"].title())
                                else:
                                    st.info(reminder["message"].title())
                        else:
                            st.info("No reminders available.")
                    
                except json.JSONDecodeError:
                    st.error("Failed to parse the response. Please try again.")
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
    else:
        st.info("Please enter both the current week and a query to search for activities.")

# Query RAG for documents
def query_rag(user_query, collection_name):
    chromaDB_path = './ChromaDbPersistent'  # Path to your ChromaDB storage
    model_name = "distiluse-base-multilingual-cased-v1"

    try:
        retriever = RetrieveDocuments(
            chromaDB_path=chromaDB_path,
            collection_name=collection_name,
            model_name=model_name
        )
        retrieved_docs = retriever.retrieve_documents(query=user_query, n_results=5)
        return retrieved_docs
    except Exception as e:
        st.error(f"Error querying RAG: {str(e)}")
        return None

# Process uploaded files
def process_uploaded_files(uploaded_files, collection_name):
    chromaDB_path = './ChromaDbPersistent'  # Path to your ChromaDB storage
    sentence_transformer_model = "distiluse-base-multilingual-cased-v1"

    upload_dir = "uploads"
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)

    try:
        for uploaded_file in uploaded_files:
            file_path = os.path.join(upload_dir, uploaded_file.name)

            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            chroma_manager = ChromaDBManager(chromaDB_path, collection_name, sentence_transformer_model)
            text_processor = TextProcessor()

            chunk_size = 1500
            chunk_overlap = 0
            text_chunksinChar = text_processor.convert_page_chunk_in_char(file_path, chunk_size, chunk_overlap)
            text_chunksinTokens = text_processor.convert_chunk_token(text_chunksinChar, sentence_transformer_model)
            ids, metadatas = text_processor.add_meta_data(text_chunksinTokens, title="LMS_Content", category="PDF", initial_id=0)
            chroma_manager.add_document_to_collection(ids, metadatas, text_chunksinTokens)
            st.success(f"Processed file: {uploaded_file.name}")
    except Exception as e:
        st.error(f"Error processing files: {str(e)}")

def main():
    st.set_page_config(page_title="LMS Content Management System", layout="wide")

    if not st.session_state.logged_in:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.title("LMS Content Management System")
            tab1, tab2 = st.tabs(["Sign In", "Sign Up"])

            with tab1:
                st.header("Sign In")
                login_username = st.text_input("Username", key="login_username")
                login_password = st.text_input("Password", type="password", key="login_password")

                if st.button("Sign In", type="primary"):
                    if login_username and login_password:
                        success, result = sign_in(login_username, login_password)
                        if success:
                            st.session_state.logged_in = True
                            st.session_state.username = result['username']
                            st.session_state.user_id = result['user_id']
                            st.session_state.moodle_key = result['moodle_user_key']
                            st.session_state.moodle_id = result['moodle_user_id']
                            st.success("Login successful!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(result)
                    else:
                        st.error("Please fill in all fields")

            with tab2:
                st.header("Sign Up")
                new_username = st.text_input("Username", key="new_username")
                new_password = st.text_input("Password", type="password", key="new_password")
                moodle_key = st.text_input("Moodle Security Key")
                moodle_id = st.text_input("Moodle User ID")

                if st.button("Sign Up", type="primary"):
                    if new_username and new_password and moodle_key and moodle_id:
                        success, message = sign_up(new_username, new_password, moodle_key, moodle_id)
                        if success:
                            st.success(message)
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error(message)
                    else:
                        st.error("Please fill in all fields")

    else:
        st.sidebar.write(f"Welcome, {st.session_state.username}!")

        if st.sidebar.button("Process LMS Content"):
            # Get Moodle credentials from environment variables
            moodle_token = os.getenv('MOODLE_TOKEN')
            moodle_user_id = os.getenv('MOODLE_USER_ID')
            
            if not moodle_token or not moodle_user_id:
                st.sidebar.error("Moodle credentials not found in .env file. Please set MOODLE_TOKEN and MOODLE_USER_ID.")
            else:
                success, message = process_lms_content(
                    st.session_state.user_id,
                    moodle_token,
                    moodle_user_id
                )
            if success:
                st.sidebar.success(message)
            else:
                st.sidebar.error(message)

        if st.sidebar.button("Sign Out"):
            for key in ['logged_in', 'username', 'user_id', 'moodle_key', 'moodle_id', 'current_page', 'selected_course', 'assistant_page', 'selected_agent']:
                if key in st.session_state:
                    del st.session_state[key]
            st.success("Signed out successfully!")
            time.sleep(1)
            st.rerun()

        # Page navigation
        if st.session_state.assistant_page:
            display_assistant_page()
        elif st.session_state.current_page == 'main':
            display_course_list()
        elif st.session_state.current_page == 'course' and st.session_state.selected_course:
            display_course_content(
                st.session_state.selected_course['id'],
                st.session_state.selected_course['name']
            )

if __name__ == "__main__":
    main()