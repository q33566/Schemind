from tqdm import tqdm
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from pathlib import Path
import json

# 資料夾設定
pdf_data_folder = Path("../data/pdf_data")
web_data_folder = Path("../data/web_data")
output_vectorstore_dir = "../data/web_user_manual_db"

# 確保資料夾存在
for folder in [pdf_data_folder, web_data_folder]:
    if not folder.exists():
        raise ValueError(f"資料夾不存在: {folder.resolve()}")
    else:
        print(f"✅ 資料夾存在: {folder.resolve()}")

# 建立 embeddings 和 vectorstore
embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
vectorstore = Chroma(
    collection_name="web_user_manual",
    embedding_function=embeddings,
    persist_directory=output_vectorstore_dir,
)

# 把兩個資料夾裡所有 JSON 檔都讀出來
all_json_files = list(pdf_data_folder.glob("*.json")) + list(web_data_folder.glob("*.json"))

documents: list[Document] = []

for json_file in tqdm(all_json_files, desc="處理 JSON 檔案"):
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # data 應該是一個 list of feature
    if isinstance(data, list):
        for idx, feature_item in enumerate(data):
            # 安全地抓 feature.title, feature.description
            try:
                title = feature_item["feature"]["title"]
                description = feature_item["feature"]["description"]
            except KeyError:
                print(f"⚠️ JSON格式有問題: {json_file.name}")
                continue

            # 把每個 feature 建成一個 Document
            content = f"{title}\n\n{description}"
            metadata = {
                "source_file": json_file.name,
                "feature_index": idx,
                "title": title,
            }
            doc = Document(page_content=content, metadata=metadata)
            documents.append(doc)
    else:
        print(f"⚠️ {json_file.name} 內容不是 list，跳過")

# 全部加進向量資料庫
print(f"✅ 總共要加入 {len(documents)} 個 documents 進向量資料庫")
vectorstore.add_documents(documents)
print("🎯 所有資料已成功送入 Vectorstore！")
