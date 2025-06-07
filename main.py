import sys
import traceback
from fastapi import FastAPI, Form, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from typing import List
import uvicorn
import webbrowser
import threading
import time

# 스크립트 시작을 알리는 로그
print("Loading main.py...")

# FastAPI 애플리케이션 초기화
app = FastAPI()

# Jinja2 템플릿 엔진 초기화, templates 디렉토리에서 HTML 파일 로드
try:
    templates = Jinja2Templates(directory="templates")
    print("Jinja2Templates initialized successfully")
except Exception as e:
    print(f"Error initializing Jinja2Templates: {e}", file=sys.stderr)
    sys.exit(1)

# 데이터 모델 정의: 이름과 메시지를 저장
class DataItem(BaseModel):
    name: str
    message: str

# 메모리 기반 임시 데이터 저장소 (데이터베이스 대체)
data_store: List[DataItem] = []

# 홈페이지 라우트: index.html 렌더링
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    print("Accessing home route")
    return templates.TemplateResponse("index.html", {"request": request})

# 데이터 입력 폼 라우트: form.html 렌더링
@app.get("/form", response_class=HTMLResponse)
async def get_form(request: Request):
    print("Accessing form route")
    return templates.TemplateResponse("form.html", {"request": request})

# 폼 데이터 제출 처리: 입력 데이터를 data_store에 저장하고 form.html 재렌더링
@app.post("/submit", response_class=HTMLResponse)
async def submit_form(request: Request, name: str = Form(...), message: str = Form(...)):
    print(f"Submitting form: name={name}, message={message}")
    data_store.append(DataItem(name=name, message=message))
    return templates.TemplateResponse("form.html", {"request": request, "success": True})

# 데이터 목록 라우트: list.html 렌더링, 저장된 데이터 표시
@app.get("/list", response_class=HTMLResponse)
async def list_data(request: Request):
    print("Accessing list route")
    return templates.TemplateResponse("list.html", {"request": request, "data": data_store})

# 데이터 수정 폼 라우트: edit.html 렌더링, 선택한 데이터 로드
@app.get("/edit/{index}", response_class=HTMLResponse)
async def edit_form(request: Request, index: int):
    print(f"Accessing edit route for index={index}")
    if 0 <= index < len(data_store):
        item = data_store[index]
        return templates.TemplateResponse("edit.html", {"request": request, "item": item, "index": index})
    print(f"Invalid index {index}, redirecting to list")
    return RedirectResponse(url="/list", status_code=303)

# 데이터 수정 처리: 수정된 데이터를 data_store에 업데이트하고 edit.html 재렌더링
@app.post("/update/{index}", response_class=HTMLResponse)
async def update_data(request: Request, index: int, name: str = Form(...), message: str = Form(...)):
    print(f"Updating data for index={index}: name={name}, message={message}")
    if 0 <= index < len(data_store):
        data_store[index] = DataItem(name=name, message=message)
        return templates.TemplateResponse("edit.html", {"request": request, "item": data_store[index], "index": index, "success": True})
    print(f"Invalid index {index}, redirecting to list")
    return RedirectResponse(url="/list", status_code=303)

# 데이터 삭제 처리: data_store에서 데이터 삭제 후 목록 페이지로 리다이렉트
@app.post("/delete/{index}", response_class=HTMLResponse)
async def delete_data(request: Request, index: int):
    print(f"Deleting data for index={index}")
    if 0 <= index < len(data_store):
        data_store.pop(index)
    return RedirectResponse(url="/list", status_code=303)

# 메인 실행 블록: 서버 시작 및 브라우저 자동 실행
if __name__ == "__main__":
    print("Starting execution of main.py...")
    try:
        # 브라우저를 3초 후에 여는 함수
        def open_browser():
            time.sleep(3)
            print("Opening browser at http://127.0.0.1:8000")
            webbrowser.open("http://127.0.0.1:8000")

        print("Starting FastAPI server...")
        threading.Thread(target=open_browser, daemon=True).start()
        # Uvicorn 서버 실행, reload=True로 개발 모드 활성화
        uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
    except Exception as e:
        print(f"Error occurred: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)