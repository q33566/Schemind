from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from filesystem_manager.prompt import FileDescriptorPrompt, FileRankerPrompt
from markitdown import MarkItDown
from langchain_core.runnables import RunnablePassthrough
from langchain_core.vectorstores import VectorStoreRetriever
from filesystem_manager.schemas import FileDescription
from abc import ABC, abstractmethod
from langchain_chroma import Chroma


class BaseLLMService(ABC):
    def __init__(
        self, llm: BaseChatModel, base_model: BaseModel = None, name: str = None
    ):
        if base_model is None:
            self._llm = llm
        else:
            self._llm = llm.with_structured_output(base_model)
        self.name = name

    @abstractmethod
    def run(self, *args, **kwargs):
        pass


class FileDescriptor(BaseLLMService):
    class FileDescriptorOutput(BaseModel):
        content: str = Field(
            ...,
            title="File Description",
            description="A concise yet informative summary of the file's content.",
        )

    def __init__(self, llm: BaseChatModel, max_content_length: int = 200):
        super().__init__(llm, self.FileDescriptorOutput, name=self.__class__.__name__)
        self._prompt: ChatPromptTemplate = FileDescriptorPrompt.file_descriptor_prompt
        self._chain = self._prompt | self._llm
        self.max_content_length: int = (
            max_content_length  # Maximum content length for the readed content
        )

    def _read_content(self, file_path: str) -> str:
        """_summary_

        preserve the first "truncation_number" characters

        Args:
            file_path (str): _description_

        Returns:
            str: _description_
        """
        md = MarkItDown(enable_plugins=False)
        result = md.convert(file_path)
        return result.text_content[: self.max_content_length]

    def run(self, file_path: str) -> str:
        f"""
        Summary:
            this function reads the content of a file and generates a description using the LLM.

        Args:
            file_path (str): the path of the file to be analyzed

        Returns:
            str: file description with "max_content_length" characters
        """
        # read content from file_path
        content = self._read_content(file_path)
        # get description from chain
        result: FileDescriptor.FileDescriptorOutput = self._chain.invoke(
            {"word_number": 100, "file_content": content}
        )
        return result.content


class FileRanker(BaseLLMService):
    class FileRankerOutput(BaseModel):
        file_path: str = Field(
            ...,
            title="File Path",
            description="The File Path that is most relevant to the query.",
        )
        reason: str = Field(
            ...,
            title="Reason",
            description="The reason why you choose thie file.",
        )
        has_found: bool = Field(
            ...,
            title="File Found",
            description="Indicates if the file was found in the filesystem.",
        )

    def __init__(self, llm: BaseChatModel, vectorstore: Chroma = None):
        super().__init__(llm, self.FileRankerOutput, name=FileRanker.__class__.__name__)
        self._prompt: ChatPromptTemplate = FileRankerPrompt.file_ranker_prompt
        self._chain = self._prompt | self._llm

    def run(self, user_query: str, retriever: VectorStoreRetriever) -> str:
        chain = {
            "context": retriever,
            "user_query": RunnablePassthrough(),
        } | self._chain
        result: FileRanker.FileRankerOutput = chain.invoke(user_query)
        return result.file_path
