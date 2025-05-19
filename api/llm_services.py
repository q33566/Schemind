from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from utils import send_email_with_attachment
from prompts import (
    FileDescriptorPrompt,
    FileRetrieverLLMServicePrompt,
    DispatcherPrompt,
    WebManualLLMServicePrompt,
    MessageSenderPrompt,
    ActionReasoningPrompt,
    SummarizerPrompt
)
from markitdown import MarkItDown
from langchain_core.runnables import RunnablePassthrough, RunnableMap, RunnableLambda
from langchain_core.vectorstores import VectorStoreRetriever
from schemas import FileDescription
from abc import ABC, abstractmethod
from langchain_chroma import Chroma
from typing import Optional
from browser_use import Agent, Controller, AgentHistoryList


class BaseLLMService(ABC):
    def __init__(
        self,
        llm: BaseChatModel,
        base_model: Optional[BaseModel] = None,
        name: str = None,
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
    class OutputFormat(BaseModel):
        content: str = Field(
            ...,
            title="File Description",
            description="A concise yet informative summary of the file's content.",
        )

    def __init__(self, llm: BaseChatModel, max_content_length: int = 200):
        super().__init__(llm, self.OutputFormat, name=self.__class__.__name__)
        self._prompt: ChatPromptTemplate = FileDescriptorPrompt.prompt_templace
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

class FileRetrieverLLMService(BaseLLMService):
    class OutputFormat(BaseModel):
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

    def __init__(self, llm: BaseChatModel):
        super().__init__(llm, self.OutputFormat, name=self.__class__.__name__)
        self._prompt: ChatPromptTemplate = FileRetrieverLLMServicePrompt.prompt_template
        self._chain = self._prompt | self._llm

    def run(self, user_query: str, retriever: VectorStoreRetriever) -> str:
        chain = {
            "context": retriever,
            "user_query": RunnablePassthrough(),
        } | self._chain
        result: FileRetrieverLLMService.OutputFormat = chain.invoke(user_query)
        return result.file_path

class BrowserUseLLMService(BaseLLMService):
    class Result(BaseModel):
        download_file_url: str
        extracted_content: str
    
    def __init__(self, llm: BaseChatModel, planner_llm: Optional[BaseChatModel] = None):
        super().__init__(llm, name=self.__class__.__name__)
        self._planner_llm: Optional[BaseChatModel] = planner_llm
        self._controler = Controller(output_model=self.Result)

    async def run(self, state, user_query: str):
        """Run the browser agent with the given task."""
        agent = Agent(
            task=user_query,
            llm=self._llm,
            use_vision=True,
            planner_llm=self._planner_llm,
            planner_interval=4,
            max_actions_per_step=8,
            use_vision_for_planner=False,
            save_conversation_path=r"..\data\logs\browser_use_conversation",
            extend_system_message=f"If the following information is useful then you can reference it, if not, just ignore it. {state['web_manual']}",
            controller=self._controler,
        )
        history_list: AgentHistoryList = await agent.run(max_steps=25)
        is_successful: bool = history_list.is_successful()
        result = self.Result.model_validate_json(history_list.final_result())
        return result, is_successful

class DispatcherLLMService(BaseLLMService):
    class OutputFormat(BaseModel):
        is_web_task: bool = Field(
            ...,
            title="Is Web Task",
            description="True if the task requires the agent itself to operate a web browser to complete the task, such as clicking links, filling forms, scraping data, or downloading files from websites.",
        )
        is_filesystem_task: bool = Field(
            ...,
            title="Is Filesystem Task",
            description="True if the task involves managing the local filesystem, including creating, copying, deleting, or sending files to others.",
        )
        is_web_record_task: bool = Field(
            ...,
            title="Is Web Record Task",
            description="True if the user must personally operate the web browser to demonstrate how a task is performed, so the agent can learn from the recording for future automation.",
        )

    def __init__(self, llm: BaseChatModel):
        super().__init__(
            llm, name=self.__class__.__name__, base_model=self.OutputFormat
        )
        self._prompt: ChatPromptTemplate = DispatcherPrompt.prompt_template
        self._chain = self._prompt | self._llm

    def run(self, user_query: str) -> str:
        result: DispatcherLLMService.OutputFormat = self._chain.invoke(
            {"user_task_description": user_query}
        )
        if result.is_web_task:
            return "web"
        elif result.is_filesystem_task:
            return "filesystem"
        elif result.is_web_record_task:
            return "recorder"
        return "unknown"

class WebGuiderLLMService(BaseLLMService):
    class OutputFormat(BaseModel):
        content: str = Field(
            ...,
            title="User Instructions",
            description="Clear and actionable user instructions derived from the website manual, summarizing how to operate or use the system effectively.",
        )

    def __init__(self, llm: BaseChatModel):
        super().__init__(llm, self.OutputFormat, name=self.__class__.__name__)
        self._prompt: ChatPromptTemplate = WebManualLLMServicePrompt.prompt_template
        self._chain = self._prompt | self._llm

    def run(self, user_query: str, retriever: VectorStoreRetriever) -> str:
        chain = {
            "context": retriever,
            "user_query": RunnablePassthrough(),
        } | self._chain
        result: WebGuiderLLMService.OutputFormat = chain.invoke(user_query)
        return result.content

class MessageSenderLLMService(BaseLLMService):
    def __init__(self, llm: BaseChatModel):
        super().__init__(llm, name=self.__class__.__name__)
        self._prompt: ChatPromptTemplate = MessageSenderPrompt.prompt_template
        self._tools = [send_email_with_attachment]
        self._llm = self._llm.bind_tools(self._tools)
        self._chain = self._prompt | self._llm

    def run(
        self, retriever: VectorStoreRetriever, user_query: str, file_path: str
    ) -> str:
        chain = (
            RunnableMap(
                {
                    "context": RunnableLambda(
                        lambda x: retriever.invoke(x["user_query"])
                    ),  # retriever 只拿到 user_query
                    "user_query": lambda x: x["user_query"],
                    "file_path": lambda x: x["file_path"],
                }
            )
            | self._chain
        )
        result = chain.invoke({"user_query": user_query, "file_path": file_path})
        args = result.tool_calls[0]["args"]
        return args

class ActionReasoningLLMService(BaseLLMService):
    class OutputFormat(BaseModel):
        reasoning: str = Field(
            ...,
            title="Reasoning",
            description="The reasoning behind the action taken by the user.",
        )

    def __init__(self, llm: BaseChatModel):
        super().__init__(llm, self.OutputFormat, name=self.__class__.__name__)
        self._prompt: ChatPromptTemplate = ActionReasoningPrompt.prompt_template
        self._chain = self._prompt | self._llm

    def run(
        self, user_query: str, before_image_url, after_image_url, step, step_text
    ) -> str:
        result: ActionReasoningLLMService.OutputFormat = self._chain.invoke(
            {
                "before_image_url": before_image_url,
                "after_image_url": after_image_url,
                "step": step,
                "step_text": step_text,
                "user_query": user_query,
            }
        )
        return result.reasoning

class SummarizerLLMService(BaseLLMService):
    def __init__(self, llm: BaseChatModel):
        super().__init__(llm, name=self.__class__.__name__)
        self._prompt: ChatPromptTemplate = SummarizerPrompt.prompt_template
        self._chain = self._prompt | self._llm

    def run(self, user_query: str, extracted_content: str) -> str:
        result: str = self._chain.invoke(
            {
                "user_query": user_query,
                "extracted_content": extracted_content,
            }
        )
        return result