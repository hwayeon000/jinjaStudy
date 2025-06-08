import sys
import traceback
from fastapi import FastAPI, Form, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List
import uvicorn
import webbrowser
import threading
import time
import logging
# 수정: 검색 기능 처리를 위해 ThreadPoolExecutor 추가
from concurrent.futures import ThreadPoolExecutor
import asyncio
# 수정: 정적 파일에 캐싱 헤더를 추가하기 위해 Starlette 미들웨어와 Response 임포트
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# 스크립트 시작을 알리는 로그
print("Loading main.py...")

# Uvicorn 로그 필터링 설정
logging.getLogger("uvicorn.access").addFilter(
    lambda record: "favicon.ico" not in record.getMessage() and "apple-touch-icon" not in record.getMessage()
)

# FastAPI 애플리케이션 초기화
app = FastAPI()

# 수정: StaticFiles의 headers 파라미터 제거, 캐싱은 미들웨어로 처리
# 정적 파일 디렉토리 마운트: static 디렉토리의 파일 제공
app.mount(
    "/static",
    StaticFiles(directory="static"),  # headers 파라미터 제거: FastAPI 0.115.0에서 지원되지 않음
    name="static"
)

# 수정: 정적 파일에 Cache-Control 헤더를 추가하는 미들웨어
# /static 경로의 응답에 캐싱 헤더 적용
class CacheControlMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # /static 경로에만 Cache-Control 헤더 추가
        if request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "public, max-age=31536000"  # 1년 캐싱
        return response

# 미들웨어 등록
app.add_middleware(CacheControlMiddleware)

# Jinja2 템플릿 엔진 초기화, templates 디렉토리에서 HTML 파일 로드
try:
    templates = Jinja2Templates(directory="templates")
    print("Jinja2Templates initialized successfully")
except Exception as e:
    print(f"Error initializing Jinja2Templates: {e}", file=sys.stderr)
    sys.exit(1)

# apple-touch-icon-precomposed.png 요청을 apple-touch-icon.png로 리다이렉트
@app.get("/apple-touch-icon-precomposed.png")
async def apple_touch_icon_precomposed():
    return RedirectResponse(url="/static/apple-touch-icon.png")

# 데이터 모델 정의: 이름과 메시지를 저장
class DataItem(BaseModel):
    name: str
    message: str

# 메모리 기반 임시 데이터 저장소 (데이터베이스 대체)
data_store: List[DataItem] = []

# 검색 처리 함수: 스레드에서 실행 가능
# query를 받아 data_store에서 이름 또는 메시지에 포함된 항목 필터링
def search_data(query: str) -> List[DataItem]:
    print(f"Searching for query: {query}")  # 디버깅 로그
    if not query:
        return data_store
    return [item for item in data_store if query.lower() in item.name.lower() or query.lower() in item.message.lower()]

# 스레드 풀 설정: 검색 작업을 별도 스레드에서 처리
# max_workers=2로 제한해 리소스 사용 최적화
executor = ThreadPoolExecutor(max_workers=2)

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

# 검색 라우트: GET 요청으로 /search 경로 처리
# query 파라미터를 받아 스레드에서 검색 처리
@app.get("/search", response_class=HTMLResponse)
async def search(request: Request, query: str = ""):
    print(f"Accessing search route with query={query}")
    # 검색 작업을 스레드 풀에서 실행
    loop = asyncio.get_running_loop()
    filtered_data = await loop.run_in_executor(executor, search_data, query)
    # list.html 렌더링, 검색 결과와 쿼리 전달
    return templates.TemplateResponse("list.html", {"request": request, "data": filtered_data, "query": query})

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
            time.sleep(3)  # 서버 시작 후 3초 대기, 서버가 준비될 시간 확보
            print("Opening browser at http://127.0.0.1:8000")  # 디버깅 로그
            webbrowser.open("http://127.0.0.1:8000")  # 기본 브라우저로 홈페이지 열기

        print("Starting FastAPI server...")  # 디버깅 로그
        # 별도 스레드에서 브라우저 열기 실행
        # threading.Thread: 새로운 스레드 생성
        # target=open_browser: 실행할 함수 지정
        # daemon=True: 메인 프로그램 종료 시 스레드도 자동 종료, 리소스 누수 방지. !!주의:데몬 스레드는 강제 종료되므로 중요한 작업(예:데이터 저장)을 수행하는 스레드에는 적합하지 않음!!
        # start(): 스레드 시작
        threading.Thread(target=open_browser, daemon=True).start()
        # Uvicorn 서버 실행, reload=True로 개발 모드 활성화
        # 개발 단계에서만 reload=True 사용하고, 프로덕션 환경에서는 reload=False로 설정.
        # uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
        uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True, reload_dirs=["templates", "static"])
    except Exception as e:
        # 서버 시작 중 에러 발생 시 출력 및 프로그램 종료
        print(f"Error occurred: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)