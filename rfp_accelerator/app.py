from flask import Flask, Response, request, jsonify, render_template, send_from_directory, stream_with_context  
import time
from io import BytesIO 
import os
import tempfile
from werkzeug.utils import secure_filename
from openai import AzureOpenAI  
from threading import Lock, Thread
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from azure.storage.blob import ContentSettings

import sys 
# not sure why, but classes folder has to be on the same level as the App2 folder.
# I don't have time to look into this, leaving it for Dan
from classes.rfp_processor import RFPProcessor 
from classes.openai_client import OpenAIClient

base_dir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__,
            static_folder=os.path.join(base_dir, 'static'),
            template_folder=os.path.join(base_dir, 'templates'))

print("Starting Flask App")
print("Base directory:", os.path.abspath(os.curdir))
print("Static folder path:", app.static_folder)
print("Template folder path:", app.template_folder)

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from upload.upload import process_rfp
# RDC Refactor 
# upload.py has been refactored into the RFPProcessor class in the classes folder so it is no longer needed
from upload.upload import process_rfp2
from common.rfp import RFP
from common.prompts import *
from common.global_vars import *
from requirements_extraction.extract_requirements import extract_requirements
# RDC new ComsmosDB class to handle all the CosmosDB operations
from classes.azure_cosmos_db import AzureCosmosDB


from dotenv import load_dotenv  
load_dotenv()
import azure.cosmos.documents as documents
import azure.cosmos.cosmos_client as cosmos_client
import azure.cosmos.exceptions as exceptions
from azure.cosmos.partition_key import PartitionKey


COSMOS_HOST = os.getenv("COSMOS_HOST")
COSMOS_MASTER_KEY = os.getenv("COSMOS_MASTER_KEY")
COSMOS_DATABASE_ID = os.getenv("COSMOS_DATABASE_ID")
COSMOS_CONTAINER_ID = os.getenv("COSMOS_CONTAINER_ID")
# RDC - Added these environment variables to store the Azure Blob Storage connection string and container name
AZURE_CONNECTION_STRING = os.getenv("RFP_STORAGE_CONNECTION_STRING2")
AZURE_CONTAINER_NAME = os.getenv("RFP_AZURE_CONTAINER_NAME2")
print("Azure Connection String: ", AZURE_CONNECTION_STRING)

# RDC Initialize the BlobServiceClient to be used in the upload_file_to_blob function
blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
container_client = blob_service_client.get_container_client(AZURE_CONTAINER_NAME)


#Get unique RFPs from Cosmos
# RDC - Refactored this function to use the AzureCosmosDB class to handle all the CosmosDB operations
def get_rfp_list():
    cosmosdb_util = AzureCosmosDB()
    rfp_list = []
    rfp_list = cosmosdb_util.get_rfp_list()

    return rfp_list

rfp_list = get_rfp_list()

     
#Temp folder to store uploaded files before kicking off processing
#TO DO: Use ADLS instead or hold in memory
UPLOAD_FOLDER = "D:/temp/tmp/"  
uploaded_file_path = None  
selected_rfp = None



def inference(content, prompt, max_tokens, model):  
    """  
    Function to generate response from OpenAI  
    """  
    messages = [{"role": "system", "content": prompt}]  
    messages.append({"role": "user", "content": content})  
  
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



@app.route('/status', methods=['GET'])
def get_status():
    with status_lock:
        updates = status_updates.copy()
    return jsonify(updates)

@app.route('/')
def index():
    return render_template('index.html')  # Use render_template for better integration with Flask

#Receive uploaded RFP from the client
@app.route('/upload', methods=['POST'])
def upload_file():
    global uploaded_file_path  
    if 'file' not in request.files:  
        return 'No file part'  
    file = request.files['file']  
    if file.filename == '':  
        return 'No selected file'  
    if file:  
        filename = secure_filename(file.filename)  
        uploaded_file_path = os.path.join(UPLOAD_FOLDER, filename)  
        file.save(uploaded_file_path)  

        # Start a new thread to process the file in the background
        Thread(target=process_rfp, args=(uploaded_file_path,)).start()
        return '', 200

# RDC: Added this route to allow the client to upload the RFP tp Blob storage    
@app.route('/uploadtoblob', methods=['POST'])
def upload_file_to_blob():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No file selected for uploading"}), 400

    try:
        # Create a BlobClient
        blob_client = container_client.get_blob_client(file.filename)
         # Create ContentSettings and set content_type
        content_settings = ContentSettings(content_type=file.content_type)
        
        # Upload the file to Azure Blob Storage
        blob_client.upload_blob(file.stream, overwrite=True, content_settings=content_settings)
        
        print(f"File {file.filename}, blob_url: {blob_client.url}")
        # Start a new thread to process the file in the background
        # RDC New Code - See Main.Py for an example of how the class replicates the behavior of process_rfp 
        # This means that upload.py can be deleted as all the logic has been moved into the RFPProcessor class and refactored to be cleaner
        rfp_processor = RFPProcessor() 
        thread = threading.Thread(target=rfp_processor.process_rfp, args=(blob_client.url,))
        thread.start()
        # Can use the thread.join() method to wait for the thread to finish processing can help with debugging but not needed in production
        # thread.join()
        # RDC Old code
        # Thread(target=process_rfp2, args=(file.filename,)).start()
        
        return jsonify({"message": f"File {file.filename} uploaded successfully!", "blob_uri": blob_client.url}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
 
# Endpoint to Test background thread    
@app.route('/threadstart', methods=['GET'])
def start_thread():
    rfp_processor = RFPProcessor() 
    result = rfp_processor.start_job()
    print("Test Thread Start: ", result)
    for i in range(5):
        time.sleep(1)
        result = rfp_processor.check_status()
        print(f"Test Thread Status: {result}")
    print("Test Thread Complete")
    return jsonify({"message": "Thread testing complete"}), 200 
           
#Receive a chat message from the client
@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    message = data['message']
    # RDC looks like the model is hardcoded to djg-gpt4 again, changing to djg-4o
    raw_response = inference(message, decision_prompt, 250, "djg-4o")

    raw_response, function = raw_response.split('Function:', 1)
    # Strip leading/trailing whitespace
    response = raw_response.split('Response:', 1)[-1].strip()
    ai_response_message = f"AI: {response}"
    function = function.strip()
    
    print(function)
    print(ai_response_message)

    return jsonify(ai_response=ai_response_message, function=function)

# RDC - Added this route to allow the client to stream the chat messages
@app.route('/stream_chat', methods=['POST'])
def stream_chat():
    openai_client = OpenAIClient() 
    data = request.get_json()
    message = data['message']
    prompt = "Why is the sky blue?  Go into detail please." # system prompt
    max_tokens = 1000
    model = "djg-4o"  # we need to pull this from the environment variables

    def generate():
        openai_client = OpenAIClient() 
        raw_response = openai_client.inferencestream(message, prompt, max_tokens, model)
        full_response = ""
        for chunk in raw_response:
            full_response += chunk
            print(chunk)
            yield chunk
            
    return Response(generate(), content_type='text/plain')


import threading
@app.route('/task', methods=['POST'])
def task():
    data = request.get_json()
    message = data['message']
    print("Message: ", message)

    if 'requirements' in message:
        print("Extracting requirements")
        status_message = "Starting requirements extraction..."
        add_status_update(status_message)
        if select_rfp is None:
            print("No RFP selected")
            return "No RFP selected", 400


        try:
            thread = Thread(target=extract_requirements, args=(selected_rfp,message))
            thread.start()
            print("Started thread")
        except Exception as e:
            print(e)
        for thread in threading.enumerate():
            print(thread.name)
    else:
        print("No task to perform")
        status_message = "No task to perform"
    return status_message, 200

 #Return list of RFPs to client
@app.route('/rfps', methods=['GET'])  
def get_rfps(): 
    cosmosdb_util = AzureCosmosDB()
    rfp_list = cosmosdb_util.get_rfp_list() 
    return jsonify(rfp_list) 

#Kick off processing of RFP after receiving it from client


@app.route('/artifacts', methods=['GET'])
def get_artifacts():

    # Assuming a function get_rfp_artifacts which queries Cosmos DB and checks for 'requirements'
    artifacts = ['requirements', 'responses', 'red team review', 'executive memo']
    return jsonify(artifacts)

#User selects an RFP
#Load RFP into memory
@app.route('/select-rfp', methods=['POST'])
def select_rfp():

    data = request.get_json()
    rfp_name = data['rfpId']  # Assuming this is the RFP name
    print(rfp_name)
    add_status_update(f"Loading {rfp_name}...")
    global selected_rfp 
    
    try:
         selected_rfp = RFP(rfp_name)
         selected_rfp.initialize()
         add_status_update(f"Successfully loaded RFP {rfp_name}")
         return jsonify({'name': rfp_name})  # Return the RFP name within a JSON object
    except Exception as e:
        add_status_update(f"Error loading RFP {rfp_name}: {str(e)}")
        return jsonify({'error': str(e)}), 500



@app.route('/artifact-data', methods=['GET'])
def artifact_data():
    artifact_type = request.args.get('artifactType')
    print("Artifact type:", artifact_type)

    if not selected_rfp:
        return jsonify({'error': 'No RFP selected'}), 400

    try:
        artifact_data = ""
        clear_status_updates()
        if artifact_type == 'requirements':
            for key in selected_rfp.requirements_dict:
                print("Key: ", key)
                print("Requirements: ", selected_rfp.requirements_dict[key])
                artifact_data += selected_rfp.requirements_dict[key] + "\n"
                add_status_update(selected_rfp.requirements_dict[key] + "\n")
        else:
            artifact_data = "No data found for artifact type " + artifact_type
            add_status_update(artifact_data)
        
        return jsonify({'details': artifact_data})  # Return a single string
    except Exception as e:
        print(e)
        return jsonify({'error': str(e)}), 500


# RDC cahnged debug=true to debug=False otherwise it causes debugpy to crash when debugging.
if __name__ == '__main__':
    app.run(debug=False, threaded=True)