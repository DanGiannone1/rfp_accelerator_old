import os
import time
import threading
from fastapi import FastAPI, UploadFile, File, Form, Request, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from io import BytesIO
from threading import Lock, Thread
from openai import AzureOpenAI
from azure.storage.blob import BlobServiceClient, ContentSettings
from dotenv import load_dotenv



# Custom Imports
from Classes.rfp_processor import RFPProcessor, OpenAIClient, AzureCosmosDB

from Classes.azure_cosmos_db import AzureCosmosDB  
from Classes.openai_client import OpenAIClient  

from Classes.extract_requirements import ExtractRequirementsProcessor
from Common.global_vars import status_updates, status_lock, add_status_update, clear_status_updates
from Common.prompts import *
from Common.rfp import RFP
from Models.SelectRfpResuest import SelectRFPRequest
from Models.ExtractRequirementsRequest import ExtractRequirementsRequest
from Models.ChatRequest import ChatRequest
from Models.ChatStreamRequest import ChatStreamRequest



def rfp_chat(rfp, message):


    openai_client = OpenAIClient()  
    user_input = message


    chat_decision = openai_client.inference(user_input, chat_decision_prompt, 100)
    print("Function call: " + chat_decision)
    

    content = "\n<Start of RFP Content> "
    
    content = content + eval(chat_decision)
  

    if chat_decision == 'rfp.get_full_text()':
        #Since we are looking at the entire RFP, we add the user input at the end to remind the LLM what the original question was. This helps us avoid the "lost in the middle" problem.
        #We also set the model to gpt4 turbo to accomodate token limits
        content = content + "\n<End of RFP Content>\n\n" + user_input
        token_limit = 4000
   

    user_input = user_input + content
   #print("LLM Input: " + user_input)
    response = openai_client.inference(user_input, rfp_chat_prompt, token_limit)

    print(response)
    #add_status_update("Successfully extracted requirements\n\n")

def test_rfp_chat():
    message = "Please summarize the RFP."
    rfp = RFP("MD_RFP_SUBSET")
    rfp.initialize()
    rfp_chat(rfp, message)

def test_extract_requirements():
    extract_requirements_processor = ExtractRequirementsProcessor()
    extract_requirements_processor.run(
        input_file="D:/temp/conduent/MD_RFP.pdf",
        output_file_path="D:/temp/conduent/",
        filename="MD_RFP_SUBSET",
        message="Extract requirements from section 2.1"
    )

if __name__ == '__main__':
    
    #test_extract_requirements()
    test_rfp_chat()