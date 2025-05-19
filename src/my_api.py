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

@app.get("/contacts", response_model=list[ContactEntry])
async def list_contacts():
    try:
        docs = messenge_sender._vectorstore.get(include=["metadatas"])
        metadatas = docs.get("metadatas", [])
        # 過濾出不是 None 且是 dict 的項目
        contacts = [m for m in metadatas if isinstance(m, dict)]
        return contacts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.delete("/contacts/{name}")
async def delete_contact(name: str):
    try:
        messenge_sender.delete_contact_by_name(name)
        return {"status": "success", "message": f"聯絡人 {name} 已刪除（若存在）"}
    except Exception as e:
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
