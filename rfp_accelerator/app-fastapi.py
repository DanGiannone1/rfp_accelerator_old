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
from Classes.extract_requirements import ExtractRequirementsProcessor
from Common.global_vars import status_updates, status_lock, add_status_update, clear_status_updates
from Common.prompts import decision_prompt
from Common.rfp import RFP
from Models.SelectRfpResuest import SelectRFPRequest
from Models.ExtractRequirementsRequest import ExtractRequirementsRequest
from Models.ChatRequest import ChatRequest
from Models.ChatStreamRequest import ChatStreamRequest
# from classes.openai_client import OpenAIClient
# from classes.azure_cosmos_db import AzureCosmosDB

load_dotenv()

# Azure Cosmos DB configuration
COSMOS_HOST = os.getenv("COSMOS_HOST")
COSMOS_MASTER_KEY = os.getenv("COSMOS_MASTER_KEY")
COSMOS_DATABASE_ID = os.getenv("COSMOS_DATABASE_ID")
COSMOS_CONTAINER_ID = os.getenv("COSMOS_CONTAINER_ID")

# Azure Blob Storage configuration
AZURE_CONNECTION_STRING = os.getenv("RFP_STORAGE_CONNECTION_STRING2")
AZURE_CONTAINER_NAME = os.getenv("RFP_AZURE_CONTAINER_NAME2")

# Initialize the BlobServiceClient
blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
container_client = blob_service_client.get_container_client(AZURE_CONTAINER_NAME)

# Temporary folder to store uploaded files before processing
UPLOAD_FOLDER = "D:/temp/tmp/"
uploaded_file_path = None
selected_rfp = None

app = FastAPI()

# Enable CORS
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def inference(content, prompt, max_tokens, model):
    messages = [{"role": "system", "content": prompt}, {"role": "user", "content": content}]
    client = AzureOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_KEY"),
        api_version="2023-05-15"
    )
    raw_response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0,
        max_tokens=max_tokens
    )
    return raw_response.choices[0].message.content

@app.get("/status")
async def get_status():
    with status_lock:
        updates = status_updates.copy()
    return JSONResponse(content=updates)

@app.post("/uploadtoblob")
async def upload_file_to_blob(file: UploadFile = File(...)):
    if file.filename == '':
        raise HTTPException(status_code=400, detail="No file selected for uploading")
    try:
        blob_client = container_client.get_blob_client(file.filename)
        content_settings = ContentSettings(content_type=file.content_type)
        blob_client.upload_blob(file.file, overwrite=True, content_settings=content_settings)
        
        rfp_processor = RFPProcessor()
        thread = threading.Thread(target=rfp_processor.process_rfp, args=(blob_client.url,))
        thread.start()
        return JSONResponse(content={"message": f"File {file.filename} uploaded successfully!", "blob_uri": blob_client.url})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat(data: ChatRequest):
    message = data.message
    raw_response = inference(message, decision_prompt, 250, "djg-4o")
    raw_response, function = raw_response.split('Function:', 1)
    response = raw_response.split('Response:', 1)[-1].strip()
    ai_response_message = f"AI: {response}"
    function = function.strip()
    return JSONResponse(content={"ai_response": ai_response_message, "function": function})

@app.post("/stream_chat") # ChatStreamRequest
async def stream_chat(data: ChatStreamRequest):
    message = data.message
    prompt = "Why is the sky blue? Go into detail please."
    max_tokens = 1000
    model = "djg-4o"

    def generate():
        openai_client = OpenAIClient()
        raw_response = openai_client.inferencestream(message, prompt, max_tokens, model)
        full_response = ""
        for chunk in raw_response:
            full_response += chunk
            yield chunk

    return StreamingResponse(generate(), media_type='text/plain')

@app.post("/task") # ExtractRequirementsRequest
async def task(data: ExtractRequirementsRequest):
    message = data.message
    extract_requirements = ExtractRequirementsProcessor()
    if 'requirements' in message:
        status_message = "Starting requirements extraction..."
        add_status_update(status_message)
        if selected_rfp is None:
            raise HTTPException(status_code=400, detail="No RFP selected")
        try:
            thread = Thread(target=extract_requirements.extract_requirements, args=(selected_rfp, message))
            thread.start()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        status_message = "No task to perform"
    return JSONResponse(content={"message": status_message})

@app.get("/rfps")
async def get_rfps():
    cosmosdb_util = AzureCosmosDB()
    rfp_list = cosmosdb_util.get_rfp_list()
    return JSONResponse(content=rfp_list)

@app.get("/artifacts")
async def get_artifacts():
    artifacts = ['requirements', 'responses', 'red team review', 'executive memo']
    return JSONResponse(content=artifacts)

# @app.post("/select-rfp", response_model=JSONResponse)
# async def select_rfp(data: SelectRFPRequest):
#     global selected_rfp
#     data = await data.json()
#     rfp_name = data['rfpId']
#     add_status_update(f"Loading {rfp_name}...")
#     try:
#         selected_rfp = RFP(rfp_name)
#         selected_rfp.initialize()
#         add_status_update(f"Successfully loaded RFP {rfp_name}")
#         return JSONResponse(content={'name': rfp_name})
#     except Exception as e:
#         add_status_update(f"Error loading RFP {rfp_name}: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/select-rfp")
async def select_rfp(data: SelectRFPRequest):
    global selected_rfp
    rfp_name = data.rfpId
    add_status_update(f"Loading {rfp_name}...")
    try:
        selected_rfp = RFP(rfp_name)
        selected_rfp.initialize()
        add_status_update(f"Successfully loaded RFP {rfp_name}")
        return JSONResponse(content={'name': rfp_name})
    except Exception as e:
        add_status_update(f"Error loading RFP {rfp_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/artifact-data")
async def artifact_data(artifactType: str = Query(..., example="requirements")):
    if not selected_rfp:
        raise HTTPException(status_code=400, detail="No RFP selected")
    try:
        artifact_data = ""
        clear_status_updates()
        if artifactType == 'requirements':
            for key in selected_rfp.requirements_dict:
                artifact_data += selected_rfp.requirements_dict[key] + "\n"
                add_status_update(selected_rfp.requirements_dict[key] + "\n")
        else:
            artifact_data = f"No data found for artifact type {artifactType}"
            add_status_update(artifact_data)
        return JSONResponse(content={'details': artifact_data})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
