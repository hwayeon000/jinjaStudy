# print("Test script running")
# import uvicorn
# from fastapi import FastAPI

# app = FastAPI()

# @app.get("/")
# async def root():
#     print("Accessing root")
#     return {"message": "Hello, World!"}

# if __name__ == "__main__":
#     print("Starting server...")
#     uvicorn.run("test_main:app", host="127.0.0.1", port=8000, reload=True)

import webbrowser
print("Opening browser...")
webbrowser.open("http://www.google.com")