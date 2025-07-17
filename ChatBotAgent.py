import os
from Agent import Agent
from RAG import RetrieveDocuments
import json

class ChatBotAgent(Agent):
    """
    Chatbot agent for discussing course materials with improved response handling
    """
    def __init__(self, course_id, model_name: str = "gemini-1.5-flash"):
        self.n_results = 7  # Number of top documents to retrieve
        self.generation_config = {
            "temperature": 0.6,
            "top_p": 0.85,
            "top_k": 10,
            "response_mime_type": "application/json"
        }
        
       
        self.chat_history = []

        self.role_instruction = """
        You are an advanced AI study coach with expertise in academic subjects and pedagogical methods.
        Your primary responsibility is to assist students in understanding course materials through:

        1. ACCURATE INFORMATION:
           - Always ground responses in the provided course materials
           - Cite specific sections or pages when possible
           - Clearly indicate when information comes from course materials vs. general knowledge

        2. STRUCTURED RESPONSES:
           Your responses should follow this JSON structure:
           {
               "summary": "Brief, clear summary of the main answer",
               "key_concepts": ["List of important concepts"],
               "detailed_explanation": "In-depth explanation with examples",
               "related_topics": ["Related concepts worth exploring"],
               "source_reference": "Reference to specific course material sections",
               "confidence_level": "HIGH/MEDIUM/LOW based on source material coverage"
           }

        3. QUALITY GUIDELINES:
           - Maintain academic tone while being accessible
           - Use examples to illustrate complex concepts
           - Break down difficult topics into manageable parts
           - Highlight connections between different concepts
           - Include relevant formulas or diagrams when appropriate

        4. LIMITATIONS:
           - If information isn't in the course materials, respond with:
             {"error": "Information not found in course materials",
              "suggestion": "Consider consulting specific course materials or instructor"}
           - For ambiguous questions, ask for clarification
           - Always indicate uncertainty when appropriate

        5. LEARNING SUPPORT:
           - Encourage critical thinking
           - Provide study tips when relevant
           - Suggest additional resources within course materials
        """

        super().__init__(
            role_instruction=self.role_instruction,
            model_name=model_name,
            generation_config=self.generation_config
        )

        # Initialize RAG components with proper path
        chromadb_path = os.path.join(os.getcwd(), 'ChromaDbPersistent')
        self.retriever = RetrieveDocuments(
            collection_name=course_id,
            model_name="distiluse-base-multilingual-cased-v1",
            chromadb_path=chromadb_path
        )

    def respond(self, query: str) -> str:
        """
        Process a user query and return a response based on retrieved documents.
        
        Args:
            query (str): User's question or request
            
        Returns:
            str: JSON formatted response string
        """
        try:
            
            # Retrieve relevant documents
            retrieved_docs = self.retriever.retrieve_documents(query, n_results=self.n_results)
            print(f"Retrieved Documents: {retrieved_docs}")

            if not retrieved_docs or not isinstance(retrieved_docs, list):
                return json.dumps({
                    "error": "Information not found in course materials",
                    "suggestion": "Consider consulting specific course materials or instructor."
                })

            # Step 2: Prepare prompt with context
            snippets = "\n\n".join([f"Snippet {i + 1}: {doc}" for i, doc in enumerate(retrieved_docs) if isinstance(doc, str)])
            if not snippets.strip():
                return json.dumps({
                    "error": "No valid content in retrieved documents",
                    "suggestion": "Please try rephrasing your question"
                })

            # Step 3: Create enhanced prompt
            context_prompt = f"""
            ## Retrieved Document Snippets:
            {snippets}
            
            ## User Query:
            "{query}"
            
            Please provide a response following the specified JSON structure in the role instructions.
            """
            print(f"Context Prompt:\n{context_prompt}")

            # Step 4: Generate response using the LLM
            response = self.chat(context_prompt)
            print(f"LLM Response: {response}")

            # Step 5: Ensure response is properly formatted
            try:
                # Try to parse the response to validate JSON
                parsed_response = json.loads(response)
                return json.dumps(parsed_response, indent=4)
            except json.JSONDecodeError:
                # If response isn't valid JSON, format it properly
                formatted_response = {
                    "summary": response[:200] + "...",
                    "detailed_explanation": response,
                    "confidence_level": "MEDIUM",
                    "error": "Response formatting was adjusted for compatibility"
                }
                return json.dumps(formatted_response, indent=4)

        except Exception as e:
            error_response = {
                "error": "An unexpected error occurred",
                "details": str(e),
                "suggestion": "Please try again with a different question"
            }
            return json.dumps(error_response)