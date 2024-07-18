from pydantic import BaseModel

class ChatStreamRequest(BaseModel):
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Why is the sky blue?"
            }
        }