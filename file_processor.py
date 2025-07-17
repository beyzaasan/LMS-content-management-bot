import os
from typing import List, BinaryIO
import pythoncom
from win32com import client
import tempfile
import fitz  # PyMuPDF
from pdf2image import convert_from_path
from docx import Document
from pptx import Presentation
from io import BytesIO
import requests

class FileProcessor:
    def __init__(self):
        self.supported_extensions = ['.txt', '.pdf', '.docx', '.pptx']
        
    def convert_to_pdf(self, file_url: str) -> BytesIO:
        """Convert various file formats to PDF"""
        response = requests.get(file_url)
        file_content = BytesIO(response.content)
        file_extension = os.path.splitext(file_url)[1].lower()
        
        if file_extension == '.pdf':
            return file_content
        elif file_extension == '.txt':
            return self._convert_txt_to_pdf(file_content)
        elif file_extension == '.docx':
            return self._convert_docx_to_pdf(file_content)
        elif file_extension == '.pptx':
            return self._convert_pptx_to_pdf(file_content)
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")

    def _convert_txt_to_pdf(self, file_content: BytesIO) -> BytesIO:
        doc = fitz.open()
        text = file_content.read().decode('utf-8')
        page = doc.new_page()
        page.insert_text((50, 50), text)
        pdf_bytes = BytesIO(doc.tobytes())
        doc.close()
        return pdf_bytes

    def _convert_docx_to_pdf(self, file_content: BytesIO) -> BytesIO:
        # Save temporary DOCX file
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp_docx:
            tmp_docx.write(file_content.getvalue())
            tmp_docx_path = tmp_docx.name

        # Initialize COM objects
        pythoncom.CoInitialize()
        word = client.Dispatch('Word.Application')
        doc = word.Documents.Open(tmp_docx_path)
        
        # Save as PDF
        pdf_path = tmp_docx_path.replace('.docx', '.pdf')
        doc.SaveAs(pdf_path, FileFormat=17)  # 17 represents PDF format
        
        # Clean up
        doc.Close()
        word.Quit()
        
        # Read PDF content
        with open(pdf_path, 'rb') as pdf_file:
            pdf_content = BytesIO(pdf_file.read())
        
        # Remove temporary files
        os.unlink(tmp_docx_path)
        os.unlink(pdf_path)
        
        return pdf_content

    def _convert_pptx_to_pdf(self, file_content: BytesIO) -> BytesIO:
        # Save temporary PPTX file
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp_pptx:
            tmp_pptx.write(file_content.getvalue())
            tmp_pptx_path = tmp_pptx.name

        # Initialize COM objects
        pythoncom.CoInitialize()
        powerpoint = client.Dispatch('Powerpoint.Application')
        presentation = powerpoint.Presentations.Open(tmp_pptx_path)
        
        # Save as PDF
        pdf_path = tmp_pptx_path.replace('.pptx', '.pdf')
        presentation.SaveAs(pdf_path, 32)  # 32 represents PDF format
        
        # Clean up
        presentation.Close()
        powerpoint.Quit()
        
        # Read PDF content
        with open(pdf_path, 'rb') as pdf_file:
            pdf_content = BytesIO(pdf_file.read())
        
        # Remove temporary files
        os.unlink(tmp_pptx_path)
        os.unlink(pdf_path)
        
        return pdf_content

def chunk_text(text: str, chunk_size: int = 1500, overlap: int = 100) -> List[str]:
    """Split text into chunks with specified size and overlap"""
    words = text.split()
    chunks = []
    start = 0
    
    while start < len(words):
        # Calculate end position for current chunk
        end = start + chunk_size
        
        # If this is not the last chunk, adjust end to include overlap
        if end < len(words):
            # Find the last period in the overlap region
            overlap_start = end - overlap
            overlap_text = ' '.join(words[overlap_start:end])
            last_period = overlap_text.rfind('.')
            
            if last_period != -1:
                # Adjust end to the last sentence boundary in overlap
                end = overlap_start + last_period + 1
        else:
            end = len(words)
        
        # Create chunk
        chunk = ' '.join(words[start:end])
        chunks.append(chunk)
        
        # Move start position for next chunk
        start = end - overlap if end < len(words) else end
    
    return chunks