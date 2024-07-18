from pydantic import BaseModel

class ExtractRequirementsRequest(BaseModel):
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Extract requirements from section 1"
            }
        }