import os  
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient  
  
class AzureBlobStorage:  
    def __init__(self):  
        self.connection_string = os.getenv("RFP_STORAGE_CONNECTION_STRING")  
        self.container_name = os.getenv("RFP_AZURE_CONTAINER_NAME")  
        self.blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)  
        self.container_client = self.blob_service_client.get_container_client(self.container_name)  
  
    def upload_file(self, file_path, blob_name):  
        blob_client = self.container_client.get_blob_client(blob_name)  
        with open(file_path, "rb") as data:  
            blob_client.upload_blob(data)  
        print(f"Successfully uploaded {file_path} to {blob_name}")  
