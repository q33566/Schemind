# 🤖 Schemind: Let AI Use Computer for You

## 🚀 Project Overview

This project aims to simplify how humans interact with computers by enabling them to perform simple tasks without using a keyboard or mouse. Instead, users can directly tell an AI Agent—powered by a Large Language Model (LLM)—what they want to do.

For example:
- Say "Help me download the email form from the Computer Center at National Central University," and the AI will autonomously operate the browser to retrieve the file.
- Say "Send the email form from the Computer Center to David Wang," and the AI will find the file in your system and send it to the recipient automatically.

The goal is to **liberate users from manual, repetitive tasks** and allow them to control their computers in a natural and intuitive way, simply by expressing their intent.
>  **Browser automation functionality** is based on the open-source project  
> 👉 [`browser-use`](https://github.com/browser-use/browser-use)  
> This enables the AI agent to perform real browser interactions like clicking and typing like a human user.
### 🔍 Key Capabilities

Schemind features several advanced capabilities that enhance its effectiveness and flexibility in task automation:

1. **Learning from User Demonstration**  
   The agent supports a learning mode where users can **perform a task once**, and the system will **learn from that demonstration** to replicate the behavior in the future. This eliminates the need for users to write code or manually define workflows.

2. **Manual-Aware Execution**  
   We’ve added a feature that allows the agent to **consult operation manuals or task-specific instructions** when needed. This increases the agent’s ability to understand and correctly execute complex or domain-specific tasks by referencing step-by-step guides 

3. **Local Filesystem Access**  
   The system can interact directly with the user's local environment—**locating, reading, or using files** as part of a task. This allows for complete workflows such as attaching files, uploading documents, all triggered by natural commands.




---

## 🛠️ Environment Setup

This project uses [`uv`](https://github.com/astral-sh/uv) as the Python package manager. Please install `uv` first:

```bash
pip install uv
```

This project also uses [`pnpm`](https://github.com/pnpm/pnpm) as the Node.js package manager. Please install `pnpm` globally:

```bash
npm install -g pnpm
```

Once installed, you can install dependencies by running:

```bash
pnpm install
```
## 🧪 How to RUN?

You can run the front end and back end separately:

```bash
pnpm dev:next     # Run the frontend (Next.js)
pnpm dev:api      # Run the backend (API server)
```

Or run both together:

```bash
pnpm dev
```

Alternatively, you can run the backend directly using Python and see the output in the terminal:

```bash
uv run python ./src/main.py
```
