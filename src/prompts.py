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

        - Filesystem Task (is_filesystem_task): The task involves managing the local filesystem, including creating, copying, deleting, or sending files to others.

        - Web Record Task (is_web_record_task): The user must personally operate the web browser to demonstrate the task because the agent may not be familiar with it yet. The session will be recorded as a tutorial or manual for the agent to study and use for future automation.

        Important Instructions:
        - Always output a JSON object matching the DispatcherOutput format, with all three fields included as booleans.
        - If a task fits multiple categories, set multiple fields to True accordingly.
        - If a category does not apply, set its field to False.
        - Be careful to distinguish between "Web Task" and "Web Record Task":
          - "Web Task" means the agent itself performs the operations.
          - "Web Record Task" means the user demonstrates the operations for the agent to learn.
        - Special Rule: 
          - If a task is classified as "Web Record Task" (`is_web_record_task=True`), then both `is_web_task` and `is_filesystem_task` must be set to False. 
          - In other words, when recording is needed, only `is_web_record_task=True` and the others must be False.
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

@dataclass
class UserActionRecorderPrompt:
    system_prompt: str = dedent(
        """
        You are an expert specializing in analyzing user behavior during web interactions.

        You will be provided with a "Task Goal" and all the web interaction steps required to complete this goal.  
        These steps will be sent to you sequentially for analysis, one at a time, including the "Action Description" and two webpage screenshots (before and after the action).

        Your task is to infer and explain the **Reasoning and Intention behind each action**.

        Focus your reasoning on:
        - Why the user performed this action.
        - How this action helps to achieve the Task Goal.

        **Analysis Guidelines**:
        - When analyzing screenshots, focus on key visual changes such as:
        - New elements appearing or disappearing (e.g., a search result, a form submission confirmation).
        - Changes in focus (e.g., a button being highlighted or a new section being scrolled into view).
        - Page layout updates (e.g., navigation to a new page, pop-up dialogs).
        - If screenshots are missing, rely on the Action Description and Task Goal to infer the likely page changes. For example, if the action is "Click on element with text 'Wikipedia'", assume the user navigates to a Wikipedia page and reason based on that assumption.
        - If available, consider the context of previous steps and their reasoning to understand the user's progression toward the Task Goal.
        - When inferring the reasoning, consider the user's potential motivations, such as seeking specific information, navigating to a relevant page, or completing a required action. Clearly explain how this step advances the user toward the Task Goal, focusing on the specific progress made (e.g., accessing new information, submitting data, or reaching a target page).

        **Special Case**:
        - If the Action Description indicates that the task is complete (e.g., "Task Completed"), verify if the final screenshot shows content that satisfies the Task Goal (e.g., the target information is visible, or the desired action is confirmed). Explicitly state that this operation signifies the successful completion of the Task Goal, and explain how the final state aligns with the goal.

        Provide a logical, detailed, and clearly task-oriented reasoning explanation.
        Avoid simply repeating the action description — you must focus on **the motivation and intention behind the action**.

        Strictly follow this output format:
        Reasoning: {Your detailed inference and explanation}

        **Important Rules**:
        - **Do NOT** repeat the action description.
        - **Do NOT** list multiple possibilities. Infer the most likely reasoning based on evidence.
        - You may think step-by-step internally, but only output the final reasoning.
        - Strictly follow the output format.

        For each action, the User will provide:
        one "Action Description" and two webpage screenshots (before and after the action).  
        Analyze only one action at a time. After responding, wait for the next action to be sent.
        """
    ).strip()
    
@dataclass
class MessageSenderPrompt:
    _system_prompt: str = dedent(
        """
        You are a message sender assistant. Your task is to send a message according to the user's query.
        """
    ).strip()

    _user_prompt: str = dedent(
        """
        query: {user_query}
        context: {context}
        Please send the message according to the user's query. also find the corresponding email address from the context.
        """
    ).strip()
    
    prompt_template = ChatPromptTemplate(
        [("system", _system_prompt), ("user", _user_prompt)]
    )