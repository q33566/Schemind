from filesystem_manager.llm_services import FileDescriptor, FileRanker
from filesystem_manager.node_services import Synchronizer, FileRetriever
from filesystem_manager.schemas import State
from langchain_chroma import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import OpenAIEmbeddings
from langgraph.graph import StateGraph, START, END


embeddings = OpenAIEmbeddings(model="text-embedding-3-large")


vectorstore = Chroma(
    collection_name="filesystem_manager",
    embedding_function=embeddings,
    persist_directory="../data/filesystem_manager_db",
)
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)
file_descriptor: FileDescriptor = FileDescriptor(llm=llm, max_content_length=100)
file_ranker: FileRanker = FileRanker(
    llm=llm,
    vectorstore=vectorstore,
)
synchronizer: Synchronizer = Synchronizer(
    observed_directory="../data/mock_filesystem",
    vectorstore=vectorstore,
    file_descriptor=file_descriptor,
)
file_retriever: FileRetriever = FileRetriever(
    vectorstore=vectorstore,
    file_ranker=file_ranker,
)

graph_builder = StateGraph(State)
graph_builder.add_node(synchronizer.name, synchronizer.run)
graph_builder.add_node(file_retriever.name, file_retriever.run)
graph_builder.add_edge(START, synchronizer.name)
graph_builder.add_edge(synchronizer.name, file_retriever.name)
graph_builder.add_edge(file_retriever.name, END)
graph = graph_builder.compile()
output = graph.invoke({})
print(output["retrieved_file_path"])
