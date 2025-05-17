from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import asyncio

from main import graph  

app = FastAPI()


class QueryRequest(BaseModel):
    user_query: str


@app.post("/run")
async def run_query(request: QueryRequest):
    try:
        result = await graph.ainvoke({"user_query": request.user_query})
        return {"output": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))