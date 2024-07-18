from pydantic import BaseModel

class SelectRFPRequest(BaseModel):
    rfpId: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "rfpId": "dummy_rfp_3"
            }
        }