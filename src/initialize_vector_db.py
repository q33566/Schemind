from tqdm import tqdm
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from pathlib import Path
from pydantic import BaseModel, Field, RootModel, EmailStr
import json
from dotenv import load_dotenv
from typing import List, Optional, Dict, Any
import os
load_dotenv()


from pydantic import BaseModel, Field, RootModel, EmailStr

class Feature(BaseModel):
    title: str = Field(
        ..., 
        description="The name of the feature, e.g., 'Student Zone', 'Email Services'."
    )
    description: str = Field(
        ..., 
        description="A detailed explanation of the feature, its purpose, and how it helps users."
    )
class FeatureItem(BaseModel):
    feature: Feature = Field(..., description="An object containing feature details.")
class FeatureList(RootModel[List[FeatureItem]]):
    pass 
def store_web_user_manual_to_vector_db(delay: int = 4) -> Chroma:
    pdf_data_folder = Path("../data/pdf_data")
    web_data_folder = Path("../data/web_data")
    pdf_data_folder.mkdir(parents=True, exist_ok=True)
    web_data_folder.mkdir(parents=True, exist_ok=True)
    vectorstore_dir: str = "../data/web_user_manual_db"

    embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
    vectorstore = Chroma(
        collection_name="web_user_manual",
        embedding_function=embeddings,
        persist_directory=vectorstore_dir,
    )
    
    json_files: list[Path] = list(pdf_data_folder.glob("*.json")) + list(web_data_folder.glob("*.json"))
    documents: list[Document] = []
    for json_file in tqdm(json_files, desc="Processing JSON files", unit="file"):
        with json_file.open("r", encoding="utf-8") as f:
            data = json.load(f)
            featurelist = FeatureList.model_validate(data)
        for idx, feature_item in enumerate(featurelist.root):
            if isinstance(feature_item, FeatureItem):
                content = f"{feature_item.feature.title}\n\n{feature_item.feature.description}"
                metadata = {
                    "source_file": json_file.name,
                    "feature_index": idx,
                    "title": feature_item.feature.title,
                }
                doc = Document(page_content=content, metadata=metadata)
                documents.append(doc)
    vectorstore.add_documents(documents)

    




class EmailContact(BaseModel):
    name: str = Field(..., description="The full name of the user, e.g., 'Amy Liu'")
    email: EmailStr = Field(..., description="The user's email address in valid format")

class EmailContactList(RootModel[List[EmailContact]]):
    pass    
    
def store_email_contact_to_vector_db() -> Chroma:
    vectorstore_dir: str = "../data/email_contact_db"
    #embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
    embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")

    vectorstore = Chroma(
        collection_name="email_contact",
        embedding_function=embeddings,
        persist_directory=vectorstore_dir,
    )
    email_contact_file = Path("../data/email_contact.json")
    with email_contact_file.open("r", encoding="utf-8") as f:
        email_contacts: EmailContactList = EmailContactList.model_validate(json.load(f))
    
    documents: list[Document] = []
    for idx, email_contact in enumerate(email_contacts.root):
        content = f"email: {email_contact.email}, name:{email_contact.name}"
        metadata = {
            "source_file": email_contact_file.name,
        }
        doc = Document(page_content=content, metadata=metadata)
        documents.append(doc)
    vectorstore.add_documents(documents)


if __name__ == "__main__":
    #store_email_contact_to_vector_db()
    store_web_user_manual_to_vector_db()
