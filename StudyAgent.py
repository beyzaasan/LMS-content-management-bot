from Agent import Agent
from RAG import RetrieveDocuments
import json
import os

class StudyAgent(Agent):
    def __init__(self, course_id, model_name: str = "gemini-1.5-flash"):
        """
        Initialize the StudyAgent with updated question generation capabilities.
        """
        self.n_results = 7
        self.generation_config = {
            "temperature": 0.6,
            "top_p": 0.85,
            "top_k": 10,
            "response_mime_type": "application/json"
        }

        self.role_instruction = """
                You are an AI question generator and evaluator for students preparing for exams and quizzes.
                Your task is to:
                1. Generate diverse and relevant practice questions with correct answers and explanations.
                2. Evaluate user answers and provide detailed feedback.
                3. Base all content on retrieved documents but present questions naturally without referencing the source.

                ## KEY RESPONSIBILITIES:
                1. Generate questions that test understanding of the content without explicitly mentioning source snippets.
                2. Create engaging, clear questions that flow naturally.
                3. Ensure questions accurately reflect the content material.

                # ACTION RULES:

                ## Action 1: Generate Questions
                - When generating questions:
                    - Focus on the key concepts and information from the source material
                    - Present questions naturally as if in a regular exam
                    - DO NOT mention snippets or source references in questions
                    - Include complete context within each question
                - Format questions in this JSON structure:
                {
                    "multiple_choice": [
                        {
                            "question": "...",
                            "options": ["A", "B", "C", "D"],
                            "correct_answer": "A",
                            "explanation": "Detailed explanation why this is correct..."
                        }
                    ],
                    "true_false": [
                        {
                            "question": "...",
                            "correct_answer": true,
                            "explanation": "Detailed explanation why this is true/false..."
                        }
                    ],
                    "open_ended": [
                        {
                            "question": "...",
                            "sample_answer": "...",
                            "key_points": ["point 1", "point 2", "point 3"],
                            "explanation": "Explanation of the key concepts..."
                        }
                    ]
                }

                ## Action 2: Evaluate Answers
                - For each answer, provide:
                    - Whether it's correct
                    - The correct answer if wrong
                    - Detailed explanation
                - Format evaluation response as:
                {
                    "evaluation": {
                        "is_correct": boolean,
                        "correct_answer": "...",
                        "explanation": "...",
                        "feedback": "..."
                    }
                }
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

    def prepare_exam_question(self, query: str) -> str:
        try:
            retrieved_docs = self.retriever.retrieve_documents(query, n_results=self.n_results)
            
            if not retrieved_docs or not isinstance(retrieved_docs, list):
                return json.dumps({
                    "Error": "No relevant course materials found to generate questions."
                })

            # Combine retrieved documents into a single context
            combined_content = " ".join([doc for doc in retrieved_docs if isinstance(doc, str)])
            if not combined_content.strip():
                return json.dumps({
                    "Error": "No valid content in retrieved documents for question generation."
                })

            context_prompt = f"""
                Using the following course material content:
                {combined_content}
                
                Generate questions about: "{query}"
                
                Important instructions:
                1. Create questions that test understanding of the content material
                2. Do not reference or mention source documents or snippets in the questions
                3. Present questions naturally as if they were part of a regular exam
                4. Ensure questions are clear and self-contained
                5. Include all necessary context within each question
                
                Format the response according to the specified JSON structure.
            """

            response = self.chat(context_prompt)

            try:
                parsed_response = json.loads(response)
                return json.dumps(parsed_response, indent=4)
            except Exception as e:
                return json.dumps({
                    "Error": "Failed to parse response into JSON format.",
                    "Raw_Response": response
                })

        except Exception as e:
            return json.dumps({
                "Error": f"Error generating questions: {str(e)}"
            })

    def evaluate_answer(self, question_data: dict, user_answer: str) -> str:
        """
        Evaluate a user's answer to a question.
        """
        try:
            if not question_data or not user_answer:
                return json.dumps({
                    "Error": "Missing question data or user answer"
                })

            # Create evaluation prompt based on question type
            question_type = next(iter(question_data.keys()))
            question = question_data[question_type][0]  # Get first question of the type
            
            evaluation_prompt = f"""
                Question: {question['question']}
                User's Answer: {user_answer}
                Correct Answer: {question.get('correct_answer', question.get('sample_answer', ''))}
                
                Evaluate this answer and provide feedback in the specified JSON format.
            """

            response = self.chat(evaluation_prompt)
            
            try:
                parsed_response = json.loads(response)
                return json.dumps(parsed_response, indent=4)
            except Exception as e:
                return json.dumps({
                    "Error": "Failed to parse evaluation response",
                    "Raw_Response": response
                })

        except Exception as e:
            return json.dumps({
                "Error": f"Error evaluating answer: {str(e)}"
            })