# Major Refactor
**Updates:** Rickcau 7/3/24 - I a major refactor of the solution over all.  Changes are listed below...

## Folder Restructure 
This new folder structure is more suitable for a Python Backend solution and Web UI.  The Python structure should have the main app in the root of the folder with all other artifacts in subfolders. 

### rfp_accelerator folder
This is the root folder for the Python API and is where the following files reside: App.py, Requirements.txt, .env, .gitignore, README.md, New-Structure.MD (this file).

### Classes    

## Changed the API to FastAPI over Flask
Converting the API to use FastAPI as compared to Flask as FastAPI is the primary choice for Python REST APIs.

## Abstracted a all the Upload.py code into rfp_processor.py
Now, rfp_processor includes all the logic that Upload.py had, plus it has been simplified and cleaned out and much of the logic as been abstracted in to separate Classes for reuse purposes

## Web UI is now a Blazor Server App
This allows us to provide a richer UI as compared to the old Flask UI

The rfp_accelerator folder follows the conventions outline at [this guide](https://climbtheladder.com/10-python-folder-structure-best-practices/#:~:text=10%20Python%20Folder%20Structure%20Best%20Practices%201%201.,the%20PEP%208%20style%20guide%20...%20More%20items).

### App.Py
This file is in the Root **rfp_accelerator** folder and is the program that implements the **Fast API**

