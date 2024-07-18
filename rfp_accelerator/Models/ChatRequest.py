from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Why is the sky blue?"
            }
        }