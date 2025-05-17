import asyncio
from node import (
    Synchronizer,
    FileRetriever,
    BrowserUse,
    Dispatcher,
    WebGuider,
    UserActionRecorder,
    MessageSender,
    ActionReasoner,
)
from schemas import State
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langgraph.graph import StateGraph, START, END
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
embeddings2 = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
vectorstore_filesystem_manager = Chroma(
    collection_name="filesystem_manager",
    embedding_function=embeddings2,
    persist_directory="../data/filesystem_manager_db",
)
vectorstore_web_manual = Chroma(
    collection_name="web_user_manual",
    embedding_function=embeddings2,
    persist_directory="../data/web_user_manual_db",
)
vectorstore_email_contact = Chroma(
    collection_name="email_contact",
    embedding_function=embeddings2,
    persist_directory="../data/email_contact_db",
)

llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)

synchronizer: Synchronizer = Synchronizer(
    observed_directory="../data/mock_filesystem",
    vectorstore=vectorstore_filesystem_manager,
    llm=llm,
    sleep_time_each_file_when_embedding=4,
)

file_retriever: FileRetriever = FileRetriever(
    vectorstore=vectorstore_filesystem_manager,
    llm=llm,
)

dispatcher: Dispatcher = Dispatcher(llm=llm)

browser_use: BrowserUse = BrowserUse(
    llm=llm,
)
messenge_sender: MessageSender = MessageSender(
    llm=llm,
    vectorstore=vectorstore_email_contact,
)
action_reasoner: ActionReasoner = ActionReasoner(
    llm=llm,
    vectorstore=vectorstore_web_manual,
)
webguider: WebGuider = WebGuider(vectorstore=vectorstore_web_manual, llm=llm, k=2)
recorder: UserActionRecorder = UserActionRecorder()
graph_builder = StateGraph(State)
graph_builder.add_node(synchronizer.name, synchronizer.run)
graph_builder.add_node(file_retriever.name, file_retriever.run)
graph_builder.add_node(browser_use.name, browser_use.run)
graph_builder.add_node(dispatcher.name, dispatcher.run)
graph_builder.add_node(webguider.name, webguider.run)
graph_builder.add_node(recorder.name, recorder.run)
graph_builder.add_node(messenge_sender.name, messenge_sender.run)
graph_builder.add_node(action_reasoner.name, action_reasoner.run)
graph_builder.add_edge(file_retriever.name, messenge_sender.name)
graph_builder.add_edge(START, dispatcher.name)
graph_builder.add_conditional_edges(
    dispatcher.name,
    path=dispatcher.branch,
    path_map=[webguider.name, synchronizer.name, recorder.name],
)
graph_builder.add_edge(synchronizer.name, file_retriever.name)
graph_builder.add_edge(messenge_sender.name, END)
graph_builder.add_edge(webguider.name, browser_use.name)
graph_builder.add_edge(browser_use.name, END)
graph_builder.add_edge(recorder.name, action_reasoner.name)
graph_builder.add_edge(action_reasoner.name, END)
graph = graph_builder.compile()


async def main():
    user_query = input("請輸入指令: ")
    output = await graph.ainvoke(
        {
            "user_query": user_query,
        }
    )
    print(output)


if __name__ == "__main__":
    asyncio.run(main())