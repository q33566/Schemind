from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
from uvicorn import Config, Server
from fastapi.staticfiles import StaticFiles
from schemas import State
from main import run_agent, messenge_sender
from pathlib import Path
import re

app = FastAPI()
static_dir = Path(__file__).resolve().parent.parent / "data" / "mock_filesystem"
print("📁 掛載資料夾：", static_dir)
print("🧪 PDF 是否存在：", (static_dir / "Unix_account_en_109.pdf").exists())
app.mount("/files", StaticFiles(directory=static_dir), name="files")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    user_query: str

class ContactEntry(BaseModel):
    name: str
    description: str
    email: str

class ContactUpdateRequest(BaseModel):
    contacts: list[ContactEntry]
    
@app.post("/run")
async def run_query(request: QueryRequest):
    try:
        result: State = await run_agent(request.user_query)
        print("task finish")
        file_name = result.get("file_name")
        if file_name:
            result["download_file_url"] = f"http://127.0.0.1:8000/files/{file_name}"
        return {"output": result}
    except Exception as e:
        print(str(e))
        raise HTTPException(status_code=500, detail=str(e))
    

@app.post("/update_contacts")
async def update_contacts(request: ContactUpdateRequest):
    try:
        messenge_sender.update_contact(request.contacts)
        return {"status": "success", "message": "聯絡人已更新"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/contacts")
async def list_contacts():
    try:
        docs = messenge_sender._vectorstore.get()

        print("📦 vectorstore.get() 結果：", docs)  # DEBUG: 印出完整物件

        raw_docs = docs.get("documents", [])
        print("📄 取得 documents：", raw_docs)  # DEBUG: 印出文件清單

        contacts = []
        for doc in raw_docs:
            print("🔍 處理 document：", doc)  # DEBUG: 每一筆文檔
            match = re.match(r"名稱: (.*?) 描述: (.*?) email: (.*)", doc)
            if match:
                contacts.append({
                    "name": match.group(1),
                    "description": match.group(2),
                    "email": match.group(3)
                })
            else:
                print("❌ 無法解析格式：", doc)

        print("✅ 回傳 contacts：", contacts)
        return contacts

    except Exception as e:
        print("❗ 例外錯誤：", e)
        raise HTTPException(status_code=500, detail=str(e))
    
class ProactorServer(Server):
    def run(self, sockets=None):
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)
        asyncio.run(self.serve(sockets=sockets))

if __name__ == '__main__':
    config = Config(app=app, host="127.0.0.1", port=8000, reload=False)
    server = ProactorServer(config=config)
    server.run()
