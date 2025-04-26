from langchain_core.prompts import ChatPromptTemplate
from dataclasses import dataclass
from textwrap import dedent


@dataclass
class FileDescriptorPrompt:
    _file_descriptor_system_prompt: str = dedent("""
    You are an AI assistant specialized in semantic search. Your task is to read a given file content and generate a **concise yet informative** {word_number}-word summary in traditional chinese that best captures its **key topics, themes, and context**. 

    Focus on:
    - The **core subject** of the file
    - **Main keywords** that help with semantic search
    - Important **concepts, events, or insights**
    - If applicable, mention **file type** (e.g., document, code, report)

    Ensure that the summary is **clear, precise, and relevant for search indexing** and is written in traditional chinese. Avoid unnecessary filler words. Keep it **exactly {word_number} words**.
    """).strip()

    _file_descriptor_user_prompt: str = dedent("""
    file_content:
    {file_content}
    """).strip()

    file_descriptor_prompt = ChatPromptTemplate(
        [
            ("system", _file_descriptor_system_prompt),
            ("user", _file_descriptor_user_prompt),
        ]
    )


@dataclass
class FileRankerPrompt:
    _file_ranker_system_prompt: str = dedent(
        """
        You are a file retrieval assistant.

        Given a user query and a list of file paths with descriptions:
        - Select the single file path that is most relevant to the query.
        - Explain briefly why you chose this file.
        - If no file matches well, indicate that no file was found.

        Only answer according to the provided file descriptions. Do not guess or create information.
        """
    ).strip()

    _file_ranker_user_prompt: str = dedent(
        """
        User Query: {user_query}

        Candidate Files:
        {context}

        Please select and return the file paths that best match the user query based on the given descriptions."""
    ).strip()

    file_ranker_prompt = ChatPromptTemplate(
        [("system", _file_ranker_system_prompt), ("user", _file_ranker_user_prompt)]
    )
