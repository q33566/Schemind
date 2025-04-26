from langchain_chroma import Chroma
from filesystem_manager.schemas import FileSnapshot
from pathlib import Path
from tqdm import tqdm
from typing import List, Dict, Tuple
from filesystem_manager.llm_services import FileDescriptor, FileRanker
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.documents import Document
from abc import ABC, abstractmethod
from filesystem_manager.schemas import FileDescription
from filesystem_manager.schemas import State


class BaseService(ABC):
    def __init__(self, name: str = None):
        self.name = name

    @abstractmethod
    def run(self, *args, **kwargs):
        pass


class Synchronizer(BaseService):
    def __init__(
        self,
        observed_directory: str = "../data/mock_filesystem",
        vectorstore: Chroma = None,
        file_descriptor: FileDescriptor = None,
    ):
        super().__init__(name=self.__class__.__name__)
        self._observed_directory: str = observed_directory
        self._vectorstore: Chroma = vectorstore
        self._file_descriptor: FileDescriptor = file_descriptor

    def _get_last_modified_time(self, file: Path) -> int:
        """Get the last modified time of a file."""
        return int(file.stat().st_mtime)

    def _get_file_snapshots_from_filesystem_dict(self) -> Dict[str, FileSnapshot]:
        """Get current file snapshots from the filesystem."""
        # Assuming the mock filesystem is located at "../data/mock_filesystem"
        files: List[Path] = [
            path for path in Path(self._observed_directory).rglob("*") if path.is_file()
        ]
        file_snapshots: Dict[str, FileSnapshot] = {
            str(file): FileSnapshot(
                file_name=str(file),
                last_modified_time=self._get_last_modified_time(file),
            )
            for file in files
        }
        return file_snapshots

    # def _get_file_snapshots_from_filesystem_list(
    #     self
    # ) -> List[FileSnapshot]:
    #     files: List[Path] = [path for path in Path(self._observed_directory).rglob("*") if path.is_file()]
    #     file_snapshots: List[FileSnapshot] = [
    #         FileSnapshot(
    #             file_name=str(file), last_modified_time=self._get_last_modified_time(file)
    #         )
    #         for file in files
    #     ]
    #     return file_snapshots

    def _get_file_snapshots_from_vectorstore_dict(self) -> Dict[str, FileSnapshot]:
        metadatas = self._vectorstore.get(include=["metadatas"])["metadatas"]
        file_snapshots: Dict[str, FileSnapshot] = {
            metadata["file_name"]: FileSnapshot.model_validate(metadata)
            for metadata in metadatas
        }
        return file_snapshots

    # def _get_file_snapshots_from_vectorstore_list(self) -> list[FileSnapshot]:
    #     metadatas = self._vectorstore.get(include=["metadatas"])["metadatas"]
    #     vector_db_snapshots: List[FileSnapshot] = [
    #         FileSnapshot.model_validate(metadata) for metadata in metadatas
    #     ]
    #     return vector_db_snapshots

    def _get_need_sync_files(
        self,
    ) -> Tuple[Dict[str, FileSnapshot], Dict[str, FileSnapshot]]:
        """
        Summary:
            Extracts deleated file, new files and modified files by comparing current and previous file snapshots.

            A file is considered deleated if it no longer exists in the filesystem.
            A file is considered modified if the timestamp of the file has changed.
            A file is considered new if it appears in the current snapshot but not in
            the previous one.

            These files need to be synchronized with vector database which store the previous file data.

        Returns:
            List[FileSnapshot]: A list of `FileSnapshot` instances representing files
            that are either outdated or newly added.
        """

        # Load the previous file snapshots
        previous_file_snapshots: Dict[str, FileSnapshot] = (
            self._get_file_snapshots_from_vectorstore_dict()
        )

        # extract files thar are no longer exist
        outdated_files: List[str, FileSnapshot] = {
            file.file_name: file
            for file in previous_file_snapshots.values()
            if not Path(file.file_name).exists()
        }
        previous_file_snapshots = {
            file.file_name: file
            for file in previous_file_snapshots.values()
            if Path(file.file_name).exists()
        }

        # extract new files and modified files
        current_file_snapshot: Dict[str, FileSnapshot] = (
            self._get_file_snapshots_from_filesystem_dict()
        )
        new_files: Dict[str, FileSnapshot] = {
            file.file_name: file
            for file in current_file_snapshot.values()
            if file.file_name not in previous_file_snapshots.keys()
        }

        # extract modified files
        modified_files: Dict[str, FileSnapshot] = {
            file.file_name: file
            for file in previous_file_snapshots.values()
            if file.last_modified_time
            != current_file_snapshot.get(file.file_name).last_modified_time
        }

        need_update_files: List[FileSnapshot] = list(modified_files.values()) + list(
            new_files.values()
        )
        need_delete_files: List[FileSnapshot] = list(outdated_files)

        return need_update_files, need_delete_files

    def run(self, state: State) -> None:
        need_delete_files: List[FileSnapshot] = []
        need_update_files: List[FileSnapshot] = []

        need_update_files, need_delete_files = self._get_need_sync_files()

        if need_delete_files:
            for file_snapshot in tqdm(
                need_delete_files, desc="Deleting files from vector database"
            ):
                self._vectorstore.delete(where={"file_name": file_snapshot.file_name})

        if need_update_files:
            documents = [
                Document(
                    page_content=self._file_descriptor.run(file_snapshot.file_name),
                    metadata={
                        "file_name": file_snapshot.file_name,
                        "last_modified_time": file_snapshot.last_modified_time,
                    },
                )
                for file_snapshot in tqdm(
                    need_update_files, desc="Creating files description"
                )
            ]
            self._vectorstore.add_documents(documents)
        return


class FileRetriever(BaseService):
    def __init__(
        self,
        vectorstore: Chroma,
        file_ranker: BaseChatModel,
        serch_type: str = "similarity",
        k: int = 10,
    ):
        super().__init__(name=self.__class__.__name__)
        self._file_ranker: FileRanker = file_ranker
        self._retriever = vectorstore.as_retriever(
            search_type=serch_type, search_kwargs={"k": k}
        )

    def run(self, state: State) -> str:
        """Retrieve files from the vector database based on the query."""
        query = input("Enter your query: ")
        result: str = self._file_ranker.run(user_query=query, retriever=self._retriever)
        return {"retrieved_file_path": result}
