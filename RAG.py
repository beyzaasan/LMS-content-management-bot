import google.generativeai as genai
import textwrap
from IPython.display import display
from IPython.display import Markdown
from fpdf import FPDF
from docx import Document
import os
from langchain.text_splitter import RecursiveCharacterTextSplitter
from chromadb.config import DEFAULT_TENANT, DEFAULT_DATABASE, Settings
from chromadb import Client, PersistentClient
from chromadb.utils import embedding_functions
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import SentenceTransformersTokenTextSplitter

class RetrieveDocuments:
    def __init__(self, chromadb_path, collection_name, model_name):
        """Initialize RetrieveDocuments with ChromaDB configuration"""
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=model_name
        )
        self.chroma_client = PersistentClient(
            path=chromadb_path,
            settings=Settings(),
            tenant=DEFAULT_TENANT,
            database=DEFAULT_DATABASE
        )
        self.chroma_collection = self.chroma_client.get_or_create_collection(
            collection_name,
            embedding_function=self.embedding_function
        )

    def retrieve_documents(self, query, n_results=5, return_only_docs=False):
        try:
            print(f"Querying collection with: {query}")
            results = self.chroma_collection.query(
                query_texts=[query],
                include=["documents", "metadatas", "distances"],
                n_results=n_results
            )
            
            if results['documents'] and results['documents'][0]:
                print(f"Found {len(results['documents'][0])} matching documents")
                if return_only_docs:
                    return results['documents'][0]
                return results['documents'][0]  # Return just the documents list
            else:
                print("No matching documents found")
                return [] if return_only_docs else []
                
        except Exception as e:
            print(f"Error during document retrieval: {str(e)}")
            return [] if return_only_docs else []

class ChromaDBManager:
    def __init__(self, chromaDB_path, collection_name, model_name):
        self.chromaDB_path = chromaDB_path
        self.collection_name = collection_name
        self.model_name = model_name
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=self.model_name
        )
        self.chroma_client, self.chroma_collection = self.create_chroma_client()

    def create_chroma_client(self):
        if self.chromaDB_path is not None:
            chroma_client = PersistentClient(
                path=self.chromaDB_path,
                settings=Settings(),
                tenant=DEFAULT_TENANT,
                database=DEFAULT_DATABASE
            )
        else:
            chroma_client = Client()

        chroma_collection = chroma_client.get_or_create_collection(
            self.collection_name,
            embedding_function=self.embedding_function
        )

        return chroma_client, chroma_collection

    def add_document_to_collection(self, ids, metadatas, text_chunksinTokens):
        print("Before inserting, the size of the collection: ", self.chroma_collection.count())
        self.chroma_collection.add(ids=ids, metadatas=metadatas, documents=text_chunksinTokens)
        print("After inserting, the size of the collection: ", self.chroma_collection.count())
        return self.chroma_collection

class TextProcessor:
    @staticmethod
    def convert_page_chunk_in_char(pdf_file, chunk_size=1500, chunk_overlap=0):
        loader = PyPDFLoader(pdf_file)
        pdf_texts = loader.load()

        character_splitter = RecursiveCharacterTextSplitter(
            separators=["\n\n", "\n", ". ", " ", ""],
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

        pdf_text_content = '\n\n'.join([doc.page_content for doc in pdf_texts])
        character_split_texts = character_splitter.split_text(pdf_text_content)

        print(f"\nTotal number of chunks (document split by max char = {chunk_size}): {len(character_split_texts)}")
        return character_split_texts

    @staticmethod
    def convert_chunk_token(text_chunksinChar, sentence_transformer_model, chunk_overlap=0, tokens_per_chunk=128):
        token_splitter = SentenceTransformersTokenTextSplitter(
            chunk_overlap=chunk_overlap,
            model_name=sentence_transformer_model,
            tokens_per_chunk=tokens_per_chunk
        )

        text_chunksinTokens = []
        for text in text_chunksinChar:
            text_chunksinTokens += token_splitter.split_text(text)
        print(f"\nTotal number of chunks (document split by 128 tokens per chunk): {len(text_chunksinTokens)}")
        return text_chunksinTokens

    @staticmethod
    def add_meta_data(text_chunksinTokens, title, category, initial_id):
        ids = [str(i + initial_id) for i in range(len(text_chunksinTokens))]
        metadata = {
            'document': title,
            'category': category
        }
        metadatas = [metadata for _ in range(len(text_chunksinTokens))]
        return ids, metadatas

class GeminiManager:
    def __init__(self, api_key):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")

    def chat(self, query, retrieved_documents):
        context = "\n".join(retrieved_documents)
        prompt = f"Based on the following context, answer the query:\n\nContext:\n{context}\n\nQuery:\n{query}"
        response = self.model.generate_content(prompt)
        return response.text