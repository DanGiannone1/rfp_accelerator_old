import os  
import re
# Used for testing thread operations
import threading
import time 
# end used for testing
  
from concurrent.futures import ThreadPoolExecutor  
from Classes.azure_blob_storage import AzureBlobStorage  
from Classes.azure_cosmos_db import AzureCosmosDB  
from Classes.openai_client import OpenAIClient  
from Classes.form_recognizer import FormRecognizer
from Common.prompts import *  
from Common.global_vars import status_lock, add_status_update, thread, test_counter_lock, test_counter, stop_event  

  
class RFPProcessor:  
    def __init__(self):  
        self.blob_storage = AzureBlobStorage()  
        self.cosmos_db = AzureCosmosDB()  
        self.openai_client = OpenAIClient()  
        self.form_recognizer = FormRecognizer()
        self.content_dict = {}  # Initialize content_dict here    
    
    # Functions to test threading, this could be a better way to handle threading
    def background_job(self):
        global test_counter
        while test_counter < 10:
            with test_counter_lock:
                test_counter += 1
            time.sleep(1)
        print("Thread: Job completed")
    
    def start_job(self):
        global thread
        if thread is None or not thread.is_alive():
            thread = threading.Thread(target=self.background_job)
            thread.daemon = True
            thread.start()
            return "Job started"
        else:
            return "Job already running"

    def stop_job(self):
       global stop_event
       global thread
       if thread is not None and thread.is_alive():
            stop_event.set()  # Signal the thread to stop
            thread.join(timeout=10)  # Wait for the thread to finish
            if thread.is_alive():
                print("Thread_Stop: Thread still alive")
                return "Failed to stop job (thread still alive)"
            else:
                print("Thread_Stop: Thread Stopped")
                return "Job stopped"
       else:
            return "No job running"
           
    def check_status(self):
        global test_counter
        with test_counter_lock:
           current_counter = test_counter 
        return current_counter
    # End of functions to test threading
        
    def inference(self, content, prompt, max_tokens, model):  
        return self.openai_client.inference(content, prompt, max_tokens, model)  
  
    def dict_to_json(self, filename, key, value):  
        id = re.sub(r'[/#]', ' ', f"{filename} - {key}")  
        print(f"Generating JSON for {filename} - {key}")  
        return {  
            'id': id,  
            'partitionKey': filename,  
            'section_id': key,  
            'section_content': value  
        }  
  
    def upload_to_cosmos(self, filename, content_dict, table_of_contents):  
        print("Loading sections to Cosmos...")  
        for key, value in content_dict.items():  
            json_data = self.dict_to_json(filename, key, value)  
            self.cosmos_db.write_to_cosmos(json_data)  
  
        toc_json = {  
            'id': f"{filename} - TOC",  
            'partitionKey': filename,  
            'table_of_contents': table_of_contents  
        }  
        self.cosmos_db.write_to_cosmos(toc_json)  
        print("Loading table of contents to Cosmos...")  
  
    def read_pdf(self, file_path):  
        return self.form_recognizer.analyze_document(file_path)  
  
    def read_pdf_from_url(self, blob_url):  
        return self.form_recognizer.analyze_document_from_url(blob_url)  
    
    def process_rfp(self, file_path): 
        add_status_update("Reading the RFP...")
        print("Reading the RFP...")
        adi_result_object = self.read_pdf_from_url(file_path)  
        add_status_update("Analyzing the RFP...")
        print("Analyzing the RFP...")
        table_of_contents = self.get_table_of_contents(adi_result_object)  
        add_status_update("Breaking the RFP into sections...")
        print("Breaking the RFP into sections...")
        self.set_valid_sections(adi_result_object, table_of_contents)  
        # Access the content_dict using the getter method  
        content_dict = self.get_content_dict() 
        add_status_update("Validating the sections...")
        print("Validating the sections...")
        content_dict = self.populate_sections(adi_result_object)  
        filename = os.path.splitext(os.path.basename(file_path))[0]  
        add_status_update("Uploading RFP to the database...")
        print("Uploading RFP to the database...")
        self.upload_to_cosmos(filename, content_dict, table_of_contents) 
        add_status_update("RFP upload completed successfully") 
        print("RFP upload completed successfully")  
        return
  
    def validate_section(self, section, table_of_contents):  
        content = f"Table of Contents: {table_of_contents} \n\nSection to validate: {section}"  
        is_valid = self.inference(content, section_validator_prompt, 50, "djg-4o")  
        print(f"{section}: {is_valid}")
        return is_valid
  
    def get_table_of_contents(self, adi_result_object):  
        first_pages = self.get_pages(adi_result_object, 1, 12)  
        return self.inference(first_pages, toc_prompt, 3000, "djg-4o")  
  
    def get_pages(self, adi_result_object, x, y):  
        page_range_text = ""
        for page in adi_result_object.pages[x:y]:  
            for line in page.lines:  
                page_range_text += line.content + "\n"
        return page_range_text

    def set_valid_sections(self, adi_result_object, table_of_contents):  
        invalid_sections = set()  
          
        # Populate content_dict  
        for paragraph in adi_result_object.paragraphs:  
            if paragraph.role == "title" or paragraph.role == "sectionHeading":  
                self.content_dict[paragraph.content] = ""  
          
        # Create a ThreadPoolExecutor  
        with ThreadPoolExecutor(max_workers=1) as executor:  
            # Run validate_section for each section heading in parallel  
            # Prepare a tuple of (section, table_of_contents) for each key in content_dict  
            section_args = ((section, table_of_contents) for section in self.content_dict.keys())  
            validation_results = list(executor.map(lambda args: self.validate_section(*args), section_args))  
              
            # Collect invalid sections based on validation results  
            for section, is_valid in zip(self.content_dict.keys(), validation_results):  
                if not is_valid:  
                    invalid_sections.add(section)  
          
        # Remove invalid sections from content_dict  
        for invalid_section in invalid_sections:  
            del self.content_dict[invalid_section]  
    
    # RDC Why is his hard coding the model name to djg-gpt35-turbo?
    # this needs to be refactor to not use hard coded model names
    def standardize_page_number(self, page_number):   
        standardized_page_number = self.inference(page_number, page_number_prompt, 50, "djg-4o")  
        return standardized_page_number 
    
    def populate_sections(self, adi_result_object):   
        current_key = None  
        page_number = ""  
        page_number_found = False  
        for paragraph in adi_result_object.paragraphs:  
            # Check if we see a new section heading. If it is in self.content_dict, we know it is a valid heading.   
            if (paragraph.role == "title" or paragraph.role == "sectionHeading") and paragraph.content in self.content_dict:  
                # If the section heading is valid, set the current key to the section heading  
                if current_key is not None:  
                    # We have reached the start of a new section. If we haven't found a page number for the last section, append it.  
                    if not page_number_found:  
                        self.content_dict[current_key] += "Page Number: " + str(page_number) + "\n"  
                else:  
                    print("Current key is none so this is the first section: " + paragraph.content)  
                  
                current_key = paragraph.content  
                self.content_dict[current_key] = ""  
                page_number_found = False  
            # Process each paragraph. Headers and Footers are skipped as they do not contain anything of value generally.  
            # When we find a page number, we add it to the content of the current section and then add 1 to it (since we are then on the next page).  
            if current_key is not None:  
                if paragraph.role == "pageHeader" or paragraph.role == "pageFooter":  
                    continue  
                if paragraph.role == "pageNumber":  
                    page_number_found = True  
                    page_number = self.standardize_page_number(paragraph.content)  
                    self.content_dict[current_key] += "Page Number: " + page_number + "\n"  
                    try:  
                        page_number = int(page_number) + 1  
                    except ValueError as e:  
                        pass  
                    continue  
                self.content_dict[current_key] += paragraph.content + "\n"  
        return self.content_dict
     
  
    def get_content_dict(self):  
        return self.content_dict  
 