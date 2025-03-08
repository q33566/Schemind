import chromadb
class FileDatabase:
    def __init__(self, name):
        self.name = name
        self.chroma_client = chromadb.Client()
        self.collection = self.chroma_client.create_collection(name=self.name)
    
    def add(self, file_description: str, file_path: str):
        self.collection.add(documents=[file_description], ids=[self.collection.count()], metadata={"path": file_path})
    
    def update(self, file_path: str, new_file_path: str):
        id = self._get_id(file_path)
        self.collection.update(ids=[id], metadata={"path": new_file_path})
    
    def query(self, file_description: str, n_results: int = 1):
        return self.collection.query(query_texts=file_description, n_results=n_results)['ids'][0][0]
    
    def delete(self, file_path: str):
        self.collection.remove(ids=[file_path])
        
    def _get_id(self, file_path: str):
        ids: list = self.collection.collection.get(where={"path": file_path})["ids"]
        assert ids is not None, f"File path {file_path} not found."
        assert len(ids) == 1, f"Expected 1 id, got {len(ids)}."
        return ids[0]
        
        
if __name__ == '__main__':
    chroma_client = chromadb.PersistentClient("file_db")
    collection = chroma_client.get_or_create_collection(name="file_db", metadata={"description": "A database for storing file descriptions and paths."})
    
    

   