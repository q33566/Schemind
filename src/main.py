import asyncio
from node import Synchronizer, FileRetriever, BrowserUse, Dispatcher
from schemas import State
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langgraph.graph import StateGraph, START, END


embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
vectorstore = Chroma(
    collection_name="filesystem_manager",
    embedding_function=embeddings,
    persist_directory="../data/filesystem_manager_db",
)
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)

synchronizer: Synchronizer = Synchronizer(
    observed_directory="../data/mock_filesystem",
    vectorstore=vectorstore,
    llm=llm,
)

file_retriever: FileRetriever = FileRetriever(
    vectorstore=vectorstore,
    llm=llm,
)

dispatcher: Dispatcher = Dispatcher(llm=llm)

browser_use: BrowserUse = BrowserUse(
    llm=llm,
)
    
graph_builder = StateGraph(State)
graph_builder.add_node(synchronizer.name, synchronizer.run)
graph_builder.add_node(file_retriever.name, file_retriever.run)
graph_builder.add_node(browser_use.name, browser_use.run)
graph_builder.add_node(dispatcher.name, dispatcher.run)
graph_builder.add_edge(START, dispatcher.name)
graph_builder.add_conditional_edges(
    dispatcher.name, 
    path=dispatcher.branch, 
    path_map=[browser_use.name, synchronizer.name]
)
graph_builder.add_edge(synchronizer.name, file_retriever.name)
graph_builder.add_edge(file_retriever.name, END)
graph_builder.add_edge(browser_use.name, END)
graph = graph_builder.compile()

async def main():
    output = await graph.ainvoke({
    "user_query": "去中央大學計算機中心網站下載email申請單，下載完才能結束",
    })
    print(output)

if __name__ == "__main__":
    asyncio.run(main())