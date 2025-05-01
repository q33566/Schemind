from pydantic import BaseModel, Field
from typing import List, Optional
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from typing import Literal


class State(TypedDict):
    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages: Annotated[list, add_messages]
    retrieved_file_path: str
    user_query: str
    task_classification: Literal["file", "web", "web_record"]
    web_manual: str
    browser_use_is_done: bool


class FileSnapshot(BaseModel):
    file_name: str = Field(..., title="File Name", description="The name of the file.")
    last_modified_time: int = Field(
        ...,
        title="Last Modified Time",
        description="The last modified time of the file.",
    )


class FileDescription(BaseModel):
    file_name: str = Field(
        ...,
        title="File Name",
        description="The name of the file.",
    )
    description: str = Field(
        ...,
        title="File Description",
        description="A concise yet informative summary of the file's content.",
    )


class GeneratedDescription(BaseModel):
    description: str = Field(
        ..., title="File Description", description="A detailed description of the file."
    )
    is_understood: bool = Field(
        ...,
        title="LLM Understanding",
        description="Indicates if the LLM fully understands the file.",
    )
    file_path: str = Field(
        ...,
        title="File Path",
        description="The path of the file being analyzed.",
    )
    last_modified_time: str = Field(
        ...,
        title="Last Modified Time",
        description="The last modified time of the file.",
    )


class WebvoyagerInputFormatterResponse(BaseModel):
    web_name: str = Field(
        ...,
        title="Website Name",
        description="The display name or organization name of the target website.",
    )
    id: str = Field(
        ...,
        title="Task ID",
        description="A unique identifier for this specific webvoyager task. Often includes a prefix (e.g., NCUCC--29).",
    )
    ques: str = Field(
        ...,
        title="Task Question",
        description="The specific question or instruction that the webvoyager agent needs to accomplish using the website.",
    )
    web: str = Field(
        ...,
        title="Website URL",
        description="The base URL of the website where the task should be performed.",
    )
    is_enough_info: bool = Field(
        ...,
        title="Is Sufficient Info",
        description="Set to true if the provided input contains enough information for WebVoyager to perform the task; otherwise, false.",
    )
    missing_fields: Optional[List[str]] = Field(
        default_factory=list,
        title="Missing Fields",
        description=(
            "List of fields that are missing or insufficient. "
            "Leave empty when is_enough_info is True. "
            "Possible values: 'web', 'ques'."
        ),
    )
