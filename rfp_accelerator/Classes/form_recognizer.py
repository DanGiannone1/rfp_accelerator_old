import os  
from azure.core.credentials import AzureKeyCredential  
from azure.ai.formrecognizer import DocumentAnalysisClient  
  
class FormRecognizer:  
    def __init__(self):  
        self.endpoint = os.getenv("FORM_RECOGNIZER_ENDPOINT")  
        self.api_key = os.getenv("FORM_RECOGNIZER_KEY")  
        self.credential = AzureKeyCredential(self.api_key)
        self.client = DocumentAnalysisClient(  
            endpoint=self.endpoint,   
            credential=self.credential  
        )  
  
    def analyze_document(self, file_path):  
        with open(file_path, "rb") as f:  
            poller = self.client.begin_analyze_document("prebuilt-layout", f)  
            result = poller.result()  
            print("Successfully read the RFP")  
        return result  
  
    def analyze_document_from_url(self, blob_url): 
        poller = self.client.begin_analyze_document_from_url("prebuilt-layout", blob_url)  
        result = poller.result()  
        print("Successfully read the PDF from blob storage and analyzed.")  
        return result  
