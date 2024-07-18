import os  
from openai import AzureOpenAI  
  
class OpenAIClient:  
    def __init__(self):  
        self.client = AzureOpenAI(  
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),  
            api_key=os.getenv("AZURE_OPENAI_KEY"),  
            api_version="2023-05-15"  
        )
        self.primary_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")  
  
    def inference(self, content, prompt, max_tokens, deployment=None, response_format=None):  
        deployment = deployment if deployment is not None else self.primary_deployment
        messages = [{"role": "system", "content": prompt}, {"role": "user", "content": content}]  
        # Parameters that are always included
        params = {
            "model": deployment,
            "messages": messages,
            "temperature": 0,
            "max_tokens": max_tokens
        }
        
        # Conditionally include response_format if it's specified
        if response_format is not None:
            params["response_format"] = response_format
        
        # Make the call with the dynamically constructed parameters
        raw_response = self.client.chat.completions.create(**params)
        return raw_response.choices[0].message.content  
    
    def inferencestream(self, content, prompt, max_tokens, deployment=None):
        deployment = deployment if deployment is not None else self.primary_deployment
        messages = [{"role": "system", "content": prompt}, {"role": "user", "content": content}]
        response = self.client.chat.completions.create(
            model=deployment,
            messages=messages,
            temperature=0,
            max_tokens=max_tokens,
            stream=True  # Enable streaming
        )

        for chunk in response:
            if chunk.choices[0].finish_reason  is not None:
                break
            if chunk.choices[0].delta.content != None:
                yield chunk.choices[0].delta.content

    