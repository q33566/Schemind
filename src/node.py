from langchain_chroma import Chroma
from schemas import FileSnapshot
from pathlib import Path
from tqdm import tqdm
import time
import base64
import json
from mimetypes import guess_type
from typing import List, Dict, Tuple
from llm_services import (
    FileDescriptor,
    FileRetrieverLLMService,
    BrowserUseLLMService,
    DispatcherLLMService,
    WebGuiderLLMService,
    MessageSenderLLMService,
    ActionReasoningLLMService,
    SummarizerLLMService,
)
from user_action_recorder_service import run_recorder
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStoreRetriever

from abc import ABC, abstractmethod
from schemas import State
from utils import send_email_with_attachment


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
        llm: BaseChatModel = None,
        max_content_length: int = 100,
        sleep_time_each_file_when_embedding: int = 0,
    ):
        super().__init__(name=self.__class__.__name__)
        self._observed_directory: str = observed_directory
        self._vectorstore: Chroma = vectorstore
        self._file_descriptor: FileDescriptor = FileDescriptor(
            llm=llm, max_content_length=max_content_length
        )
        self._sleep_time_each_file_when_embedding: int = (
            sleep_time_each_file_when_embedding
        )

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
            documents: list[Document] = []
            for file_snapshot in tqdm(
                need_update_files, desc="Creating files description"
            ):
                content = self._file_descriptor.run(file_snapshot.file_name)
                metadata = {
                    "file_name": file_snapshot.file_name,
                    "last_modified_time": file_snapshot.last_modified_time,
                }
                time.sleep(4)
                documents.append(Document(page_content=content, metadata=metadata))
                self._vectorstore.add_documents(
                    [Document(page_content=content, metadata=metadata)]
                )
        return


class FileRetriever(BaseService):
    def __init__(
        self,
        vectorstore: Chroma,
        llm: BaseChatModel,
        serch_type: str = "similarity",
        k: int = 10,
    ):
        super().__init__(name=self.__class__.__name__)
        self._file_retriever_llm_service: FileRetrieverLLMService = (
            FileRetrieverLLMService(
                llm=llm,
            )
        )
        self._retriever = vectorstore.as_retriever(
            search_type=serch_type, search_kwargs={"k": k}
        )

    def run(self, state: State) -> str:
        """Retrieve files from the vector database based on the query."""
        query = state["user_query"]
        result: str = self._file_retriever_llm_service.run(
            user_query=query, retriever=self._retriever
        )
        return {"retrieved_file_path": result}


class BrowserUse(BaseService):
    def __init__(self, llm: BaseChatModel, planner_llm: BaseChatModel = None):
        super().__init__(name=self.__class__.__name__)
        self._browser_use_llm_service: BrowserUseLLMService = BrowserUseLLMService(
            llm=llm,
            planner_llm=planner_llm,
        )

    async def run(self, state: State) -> None:
        user_query = state["user_query"]
        history = await self._browser_use_llm_service.run(
            user_query=user_query, state=state
        )
        return {
            "browser_use_is_done": history.is_successful(),
            "extracted_content": history.extracted_content(),
        }


class Dispatcher(BaseService):
    def __init__(self, llm: BaseChatModel = None):
        super().__init__(name=self.__class__.__name__)
        self._llm_service: DispatcherLLMService = DispatcherLLMService(
            llm=llm,
        )

    def branch(self, state: State) -> str:
        print("tast_classification:", state["task_classification"])
        if state["task_classification"] == "filesystem":
            return Synchronizer.__name__
        elif state["task_classification"] == "web":
            return WebGuider.__name__
        elif state["task_classification"] == "recorder":
            return UserActionRecorder.__name__
        else:
            raise ValueError("Invalid task classification.")

    def run(self, state: State):
        user_query = state["user_query"]
        task: str = self._llm_service.run(user_query=user_query)
        return {"task_classification": task}


class WebGuider(BaseService):
    def __init__(
        self,
        vectorstore: Chroma,
        llm: BaseChatModel,
        serch_type: str = "similarity",
        k: int = 2,
    ):
        super().__init__(name=self.__class__.__name__)
        self._web_guider_llm_service: WebGuiderLLMService = WebGuiderLLMService(
            llm=llm,
        )
        self._retriever = vectorstore.as_retriever(
            search_type=serch_type, search_kwargs={"k": k}
        )

    def run(self, state: State) -> str:
        user_query = state["user_query"]
        result: str = self._web_guider_llm_service.run(
            user_query=user_query, retriever=self._retriever
        )
        return {"web_manual": result}


class UserActionRecorder(BaseService):
    def __init__(self):
        super().__init__(name=self.__class__.__name__)

    def run(self, state: State) -> None:
        run_recorder(state=state)


class MessageSender(BaseService):
    def __init__(
        self,
        vectorstore: Chroma,
        llm: BaseChatModel,
        serch_type: str = "similarity",
        k: int = 4,
    ):
        super().__init__(name=self.__class__.__name__)
        self._vectorstore = vectorstore
        self._llm_service: MessageSenderLLMService = MessageSenderLLMService(
            llm=llm,
        )
        self._retriever: VectorStoreRetriever = vectorstore.as_retriever(
            search_type=serch_type, search_kwargs={"k": k}
        )

    def run(self, state: State) -> None:
        user_query: str = state["user_query"]
        file_path: str = state["retrieved_file_path"]
        args: dict = self._llm_service.run(
            user_query=user_query, file_path=file_path, retriever=self._retriever
        )
        send_email_with_attachment.invoke(args)


class ActionReasoner(BaseService):
    def __init__(self, llm: BaseChatModel = None, vectorstore: Chroma = None):
        super().__init__(name=self.__class__.__name__)
        self._llm_service: ActionReasoningLLMService = ActionReasoningLLMService(
            llm=llm,
        )
        self._vectorstore: Chroma = vectorstore

    def _local_image_to_data_url(self, image_path):
        mime_type, _ = guess_type(image_path)
        # Default to png
        if mime_type is None:
            mime_type = "image/png"

        # Read and encode the image file
        with open(image_path, "rb") as image_file:
            base64_encoded_data = base64.b64encode(image_file.read()).decode("utf-8")
        # Construct the data URL
        return f"data:{mime_type};base64,{base64_encoded_data}"

    def _get_latest_recording_dir(self) -> Path:
        root = Path(r"..\data\userInteraction_recording")

        recording_folders = [
            (int(p.name.split("_")[1]), p)
            for p in root.iterdir()
            if p.is_dir()
            and p.name.startswith("recording_")
            and p.name.split("_")[1].isdigit()
        ]
        latest_recording: Path = (
            max(recording_folders, key=lambda x: x[0])[1] if recording_folders else None
        )
        return latest_recording

    def _load_latest_recording_data(self) -> Tuple[List[Path], Dict]:
        latest = self._get_latest_recording_dir()
        if not latest:
            raise FileNotFoundError("No valid recording folder found.")

        screenshot_dir = latest / "screenshot_recording"
        screenshots = sorted(
            screenshot_dir.glob("screenshot_*.png"),
            key=lambda p: int(p.stem.split("_")[1]),
        )

        json_path = latest / "Interactions_recording.json"
        with open(json_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)

        return screenshots, json_data

    def _store_to_vectorstore(self, latest_recording_json: Dict) -> None:
        task_question = latest_recording_json["task_question"]
        doc = Document(
            page_content=json.dumps(latest_recording_json),
            metadata={"task_question": task_question},
        )
        self._vectorstore.add_documents([doc])

    def run(self, state: State) -> str:
        latest_recording_screenshots, latest_recording_json = (
            self._load_latest_recording_data()
        )
        user_query = state["user_query"]
        del latest_recording_json["userInteraction_recording"][0]
        for i, step_info in tqdm(
            enumerate(latest_recording_json["userInteraction_recording"], start=0),
            desc="thinking action steps..",
        ):
            step = i
            step_text = step_info["Actual_Interaction"]
            print(step, step_text)
            before_image_url = self._local_image_to_data_url(
                latest_recording_screenshots[i]
            )
            after_image_url = self._local_image_to_data_url(
                latest_recording_screenshots[
                    min(i + 1, len(latest_recording_screenshots) - 1)
                ]
            )

            step_description: str = self._llm_service.run(
                user_query=user_query,
                before_image_url=before_image_url,
                after_image_url=after_image_url,
                step_text=step_text,
                step=step,
            )
            latest_recording_json["userInteraction_recording"][i]["llm_result"] = (
                step_description
            )
        self._store_to_vectorstore(latest_recording_json)
        with open(
            f"../data/userInteraction_recording/llm_result.json", "w", encoding="utf-8"
        ) as f:
            json.dump(latest_recording_json, f, ensure_ascii=False, indent=4)


class Summarizer(BaseService):
    def __init__(self, llm: BaseChatModel = None):
        super().__init__(name=self.__class__.__name__)
        self._llm_service: SummarizerLLMService = SummarizerLLMService(
            llm=llm,
        )

    def run(self, state: State):
        user_query = state["user_query"]
        extracted_content = state["extracted_content"]
        result: str = self._llm_service.run(
            user_query=user_query, extracted_content=extracted_content
        )
        return {"summarizer_answer": result}
