import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient
from openai import AzureOpenAI
import azure.cosmos.documents as documents
import azure.cosmos.cosmos_client as cosmos_client
import azure.cosmos.exceptions as exceptions
from azure.cosmos.partition_key import PartitionKey
from Common.prompts import *
from Common.rfp import *
from Common.global_vars import *
from Classes.azure_cosmos_db import AzureCosmosDB  
from Classes.openai_client import OpenAIClient  
import json

class ExtractRequirementsProcessor:
    def __init__(self):
        load_dotenv()
        
        self.form_recognizer_endpoint = os.getenv("FORM_RECOGNIZER_ENDPOINT")
        self.form_recognizer_key = os.getenv("FORM_RECOGNIZER_KEY")
        self.document_analysis_client = DocumentAnalysisClient(
            endpoint=self.form_recognizer_endpoint, 
            credential=AzureKeyCredential(self.form_recognizer_key)
        )

        self.azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.azure_openai_key = os.getenv("AZURE_OPENAI_KEY")
        
        self.cosmos_host = os.getenv("COSMOS_HOST")
        self.cosmos_master_key = os.getenv("COSMOS_MASTER_KEY")
        self.cosmos_database_id = os.getenv("COSMOS_DATABASE_ID")
        self.cosmos_container_id = os.getenv("COSMOS_CONTAINER_ID")

        self.client = AzureOpenAI(
            azure_endpoint=self.azure_openai_endpoint,   
            api_key=self.azure_openai_key,    
            api_version="2023-05-15"
        )
        self.cosmos_db = AzureCosmosDB()  
        self.openai_client = OpenAIClient()  
        self.cosmos_client = cosmos_client.CosmosClient(self.cosmos_host, {'masterKey': self.cosmos_master_key}, user_agent="CosmosDBPythonQuickstart", user_agent_overwrite=True)
        self.db = self._get_or_create_database()
        self.container = self._get_or_create_container()

    def _get_or_create_database(self):
        try:
            return self.cosmos_client.create_database(id=self.cosmos_database_id)
        except exceptions.CosmosResourceExistsError:
            return self.cosmos_client.get_database_client(self.cosmos_database_id)

    def _get_or_create_container(self):
        try:
            return self.db.create_container(id=self.cosmos_container_id, partition_key=PartitionKey(path='/partitionKey'))
        except exceptions.CosmosResourceExistsError:
            return self.db.get_container_client(self.cosmos_container_id)


    def dict_to_json(self, filename, key, value):
        id = filename + " - " + key
        id = re.sub(r'[/#]', ' ', id)
        return {'id' : filename + " - " + key,
                'partitionKey' : filename,
                'section_id' : key,
                'section_content' : value}

    def write_to_cosmos(self, json):
        try:
            self.container.create_item(body=json)
        except Exception as e:
            print("Error writing to cosmos:", str(e))

    def extract_requirements(self, rfp, message):
        user_input = message
        section = self.openai_client.inference(user_input, query_prompt_2, 50)
        print(f"Parsing content for section {section}")

        for key in rfp.content_dict:
            if key and re.match(r'^' + re.escape(section), key):
                print(f"Key match in for loop Key: {key}")
                temp_input = f"Please parse the content. Content: {rfp.content_dict[key]} <end content>. "
                response = self.openai_client.inference(temp_input, content_parsing_prompt, 4096, response_format={ "type": "json_object" })
                print(f"***Raw LLM Response***\n {response}")
                data = json.loads(response)
                content = data['content']
                print(f"***Content***\n {content}")

                
                rfp.requirements_dict[key] = content

                partition_key_value = rfp.filename
                document_id = partition_key_value + " - " + key
                read_item = self.container.read_item(item=document_id, partition_key=partition_key_value)
                read_item['requirements'] = content
                self.container.replace_item(item=read_item, body=read_item)


        print(f"Extraction Logic Completed")
    
    # Allows you to run the requirements extraction process using a local file. 
    def run(self, input_file, output_file_path, filename, message):
        rfp = RFP(filename)
        rfp.initialize()
        self.extract_requirements(rfp, message)


if __name__ == "__main__":
    extract_requirements_processor = ExtractRequirementsProcessor()
    extract_requirements_processor.run(
        input_file="D:/temp/conduent/MD_RFP.pdf",
        output_file_path="D:/temp/conduent/",
        filename="MD_RFP_SUBSET",
        message="Extract requirements from section 2.3"
    )
    
    
    #Create new RFP class instance 
    # rfp = RFP(filename)
    # rfp.read_pdf()
    # rfp.set_table_of_contents(md_toc)
    #rfp.set_valid_sections()
    #rfp.populate_sections()
    # rfp.initialize()


    # extract_requirements(rfp, "Extract requirements from section 1")
