# VS Code - Setup
If using VS Code, you will need the .vscode directory and files found in this directory.  If running on a Mac you may need to change things, but the bottom line is you run the FastAPI via the following commend: 

   ~~~
       uvicorn main:app --reload 
   ~~~

## Setup your Virtual Environment
I am currently using Python 3.12. so create your virtual environment before you do anything.  Then run the following to install the dependencies:

   ~~~
      pip install -r requirements.txt
   ~~~

If you don't have pip installed you can run the following command:

   ~~~
      python -m ensurepip --upgrade 
   ~~~

Once pip is installed then you run the **pip install -r requirments**

## Debuging the FastAPI
Your launch.json file should point to the app-fastapi.py file and should look like this:

   ~~~
      {
         "version": "0.2.0",
         "configurations": [
               {
                  "name": "Python: FastAPI",
                  "type": "debugpy",
                  "request": "launch",
                  "module": "uvicorn",
                  "args": [
                     "app-fastapi:app",
                     "--reload",
                     "--port",
                        "5000"
                  ],
                  "env": {
                     "PYTHONPATH": "${workspaceFolder}"
                  },
                  "console": "integratedTerminal"
               }
         ]
      }
   ~~~

This will allow you to debug the FastAPI using VS Code.


