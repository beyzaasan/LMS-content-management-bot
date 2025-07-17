from Agent import Agent
from RAG import ChromaDBManager, RetrieveDocuments, GeminiManager
import os
from dotenv import load_dotenv
import json
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

class ReminderAgent(Agent):
    def __init__(self, course_id: str, model_name: str = "gemini-1.5-flash"):
        """
        Initialize the ReminderAgent with required capabilities.
        """
        self.n_results = 30  # Number of top documents to retrieve
        self.generation_config = {
            "temperature": 0.6,
            "top_p": 0.85,
            "top_k": 10,
            "response_mime_type": "application/json"
        }

        self.role_instruction = """
        You are an AI Reminder Agent designed to help students track and manage their academic deadlines and activities.
        Your task is to:
        1. Search for and identify upcoming activities, deadlines, and important dates from course materials
        2. Present the information in a clear, organized format
        3. Provide timely reminders about approaching deadlines
        4. Only show activities that are upcoming based on the current week number provided

        ## KEY RESPONSIBILITIES:
        1. Track upcoming academic deadlines and activities from course materials
        2. Generate clear, organized reminders for future events only
        3. Filter out past events based on the current week
        4. Only provide information that is explicitly stated in the retrieved documents

        # ACTION RULES:

        ## Action 1: Search Upcoming Activities
        - When searching for activities, ONLY include events that:
          * Are in the current week or future weeks
          * Have not passed based on the current week number
        - Look for keywords such as:
          * Assignments/Homework (HW)
          * Projects/Reports
          * Presentations
          * Exams (Midterm/Final)
          * Due dates
          * Lab work
        - Format activities in chronological order
        - Include specific dates when available
        - Filter out any activities from past weeks

        ## Action 2: Format Responses
        - Present information in the following format:
        {
            "activities": [
                {
                    "date": "DD.MM.YYYY",
                    "type": "assignment/exam/project/etc",
                    "description": "detailed description",
                    "week_number": "Week X"
                }
            ],
            "reminders": [
                {
                    "type": "general/urgent",
                    "message": "reminder message"
                }
            ]
        }

        ## Action 3: Priority Handling
        - Only include and categorize upcoming activities by urgency:
          * Immediate (current week)
          * Short-term (next 2 weeks)
          * Long-term (beyond 2 weeks)
        - Always include a reminder to check course announcements
        - Highlight any deadlines occurring in the current week
        - IMPORTANT: Filter out and DO NOT include any activities from weeks before the current week

        # INTERACTION RULES:
        1. Use the provided current week number to filter activities
        2. Only show activities from the current week onwards
        3. Include a standard reminder about checking course announcements
        4. Maintain a clear distinction between confirmed dates and tentative schedules
        5. If no upcoming activities are found, clearly state this while encouraging checking official announcements

        # RESPONSE FORMAT:
        - Only include upcoming events (current week and beyond)
        - Sort activities by date
        - Clearly indicate the week number for each activity
        - Mark urgent items for the current and next week

        Remember to check course announcements regularly for any updates or changes to the schedule.
        """

        super().__init__(
            role_instruction=self.role_instruction,
            model_name=model_name,
            generation_config=self.generation_config
        )
        
        chromadb_path = os.path.join(os.getcwd(), 'ChromaDbPersistent')
        self.retriever = RetrieveDocuments(
            collection_name=course_id,
            model_name="distiluse-base-multilingual-cased-v1",
            chromadb_path=chromadb_path
        )
    
    def _extract_week_number(self, week_str: str) -> int:
        """
        Extract week number from week string.
        """
        try:
            return int(week_str.lower().replace('week', '').strip())
        except ValueError:
            return 0

    def _is_upcoming(self, activity_week: str, current_week: str) -> bool:
        """
        Check if an activity is upcoming based on week numbers.
        """
        activity_week_num = self._extract_week_number(activity_week)
        current_week_num = self._extract_week_number(current_week)
        return activity_week_num >= current_week_num

    def search_upcoming_activities(self, query: str, current_week: str) -> str:
        """
        Search for upcoming activities based on the uploaded syllabi and user query.
        """
        try:
            # Step 1: Retrieve relevant documents
            retrieved_docs = self.retriever.retrieve_documents(query=query, n_results=self.n_results)

            # Debugging response structure
            print("Retrieved Docs:", retrieved_docs)

            # Check if the response is a dictionary or list
            if isinstance(retrieved_docs, dict):
                documents = retrieved_docs.get('documents', [])
            elif isinstance(retrieved_docs, list):
                documents = retrieved_docs
            else:
                documents = []

            if not documents:
                return json.dumps({
                    "Error": "No relevant syllabus data found for the provided query."
                })

            # Step 2: Prepare prompt with context and emphasize upcoming filter
            context_prompt = f"""
            ## Current Week:
            "{current_week}"
            
            ## Filter Instructions:
            - Only include activities from week {self._extract_week_number(current_week)} onwards
            - Sort activities by date
            - Mark activities in the current week as urgent
            
            ## Retrieved Document Snippets:
            {" ".join([f"Snippet {i + 1}: {doc}" for i, doc in enumerate(documents)])}
            
            ## User Query:
            "{query}"
            """

            # Step 3: Use GeminiManager to generate response
            response = self.chat(context_prompt)

            # Step 4: Parse and filter response
            try:
                parsed_response = json.loads(response)
                
                # Filter activities to only include upcoming ones
                if "activities" in parsed_response:
                    parsed_response["activities"] = [
                        activity for activity in parsed_response["activities"]
                        if self._is_upcoming(activity["week_number"], current_week)
                    ]
                    
                    # Sort activities by date
                    parsed_response["activities"].sort(
                        key=lambda x: datetime.strptime(x["date"], "%d.%m.%Y")
                    )

                return json.dumps(parsed_response, indent=4)
                
            except Exception as e:
                return json.dumps({
                    "Error": "The response from the model could not be parsed into the expected JSON format.",
                    "Raw_Response": response
                })

        except Exception as e:
            return json.dumps({
                "Error": f"An error occurred while searching for upcoming activities: {str(e)}"
            })

    def urge_to_check_announcements(self) -> str:
        """
        Generate a reminder for the user to check announcements.
        """
        return "Please ensure to check course announcements for any recent updates regarding upcoming tasks or activities."