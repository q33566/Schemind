from langchain_core.prompts import ChatPromptTemplate
from dataclasses import dataclass
from textwrap import dedent


@dataclass
class FileDescriptorPrompt:
    _system_prompt: str = dedent("""
    You are an AI assistant specialized in semantic search. Your task is to read a given file content and generate a **concise yet informative** {word_number}-word summary in traditional chinese that best captures its **key topics, themes, and context**. 

    Focus on:
    - The **core subject** of the file
    - **Main keywords** that help with semantic search
    - Important **concepts, events, or insights**
    - If applicable, mention **file type** (e.g., document, code, report)

    Ensure that the summary is **clear, precise, and relevant for search indexing** and is written in traditional chinese. Avoid unnecessary filler words. Keep it **exactly {word_number} words**.
    """).strip()

    _user_prompt: str = dedent("""
    file_content:
    {file_content}
    """).strip()

    prompt_templace = ChatPromptTemplate(
        [
            ("system", _system_prompt),
            ("user", _user_prompt),
        ]
    )


@dataclass
class FileRetrieverLLMServicePrompt:
    _system_prompt: str = dedent(
        """
        You are a file retrieval assistant.

        Given a user query and a list of file paths with descriptions:
        - Select the single file path that is most relevant to the query.
        - Explain briefly why you chose this file.
        - If no file matches well, indicate that no file was found.

        Only answer according to the provided file descriptions. Do not guess or create information.
        """
    ).strip()

    _user_prompt: str = dedent(
        """
        User Query: {user_query}

        Candidate Files:
        {context}

        Please select and return the file paths that best match the user query based on the given descriptions."""
    ).strip()

    prompt_template = ChatPromptTemplate(
        [("system", _system_prompt), ("user", _user_prompt)]
    )


@dataclass
class DispatcherPrompt:
    _system_prompt: str = dedent(
        """
        You are a task dispatcher assistant.
        You will receive a description of a user's task. Based on the content, you must classify the task into one or more of the following categories by setting the corresponding fields to True:

        - Web Task (is_web_task): The user expects the agent itself to autonomously operate a web browser to complete the task. This includes actions like clicking links, filling out forms, scraping data, or downloading files from websites.

        - Filesystem Task (is_filesystem_task): The task involves managing the local filesystem, including creating, copying, deleting, or listing files and directories.

        - Web Record Task (is_web_record_task): The user must personally operate the web browser to demonstrate the task because the agent may not be familiar with it yet. The session will be recorded as a tutorial or manual for the agent to study and use for future automation.

        Important Instructions:
        - Always output a JSON object matching the DispatcherOutput format, with all three fields included as booleans.
        - If a task fits multiple categories, set multiple fields to True accordingly.
        - If a category does not apply, set its field to False.
        - Be careful to distinguish between "Web Task" and "Web Record Task":
        - "Web Task" means the agent itself performs the operations.
        - "Web Record Task" means the user demonstrates the operations for the agent to learn.
        """
    ).strip()

    _user_prompt: str = dedent(
        """
        User Task Description:
        {user_task_description}
        """
    ).strip()

    prompt_template = ChatPromptTemplate(
        [("system", _system_prompt), ("user", _user_prompt)]
    )


@dataclass
class WebManualLLMServicePrompt:
    _system_prompt: str = dedent(
        """
    You are a web manual assistant. Your task is to provide clear and actionable 
    user instructions based on the content of the website manual. 
    The instructions should summarize how to operate or use the system effectively.
    """
    ).strip()

    _user_prompt: str = dedent(
        """
        使用者任務：{user_query}
        相關操作手冊:{context}
        請問該如何進行？有什麼需要注意的規則？請詳細說明操作順序，告訴我目前畫面該怎麼操作。
        """
    ).strip()

    prompt_template = ChatPromptTemplate(
        [("system", _system_prompt), ("user", _user_prompt)]
    )
