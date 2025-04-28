from tqdm import tqdm
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader
from tqdm import tqdm
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from pathlib import Path

folders_to_check = [
    Path("../data/web_user_manual"),
    Path("../data/mock_filesystem"),
    Path("../data/logs"),
]

for folder in folders_to_check:
    if not folder.exists():
        folder.mkdir(parents=True, exist_ok=True)
        print(f"Folder created: {folder.resolve()}")
    else:
        print(f"Filder exist: {folder.resolve()}")

embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
vectorstore = Chroma(
    collection_name="web_user_manual",
    embedding_function=embeddings,
    persist_directory="../data/web_user_manual_db",
)
loader = PyPDFLoader(
    file_path=r"..\data\web_user_manual\NCUOP1共用-承辦-製作1061027.pdf",
    mode="page",
)
documents: list[Document] = []
docs_lazy = loader.lazy_load()

# for testing
documents = documents[:10]

for document in tqdm(docs_lazy):
    documents.append(document)

vectorstore.add_documents(documents)
