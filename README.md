# Agent AI LangGraph

Agent AI LangGraph is a **Multi-Agent Autonomous GitHub Manager** designed to automate the entire software development lifecycle on GitHub. From issue tracking and code implementation to code review and documentation, this project leverages a coordinated team of AI agents to streamline development workflows.

## 🚀 Purpose
The primary goal of `agent-ai-langraph` is to reduce the manual overhead of managing GitHub repositories. Instead of relying on a single monolithic agent, it employs a **Coordinator-Worker architecture**. This ensures that specialized tasks are handled by agents equipped with the specific tools and prompts required for their domain, increasing reliability and reducing "prompt noise."

## 🏗️ Core Architecture
The project is built using a graph-based orchestration pattern (leveraging `deepagents`, which utilizes LangGraph principles).

### Orchestration Flow
1. **User Input**: The user provides a high-level goal (e.g., *"Review the code and update the README"*).
2. **Coordinator Agent**: Acts as the "brain" or router. It analyzes the request and delegates it to one or more specialized subagents. The coordinator is strictly forbidden from calling GitHub tools directly; its sole responsibility is delegation.
3. **Subagents**: Specialized workers that execute the actual tasks using a subset of GitHub tools.
4. **Memory & Skills**: 
   - **Memory**: The agent uses `AGENTS.md` as a persistent knowledge base to ensure it follows specific project conventions (e.g., branching naming schemes).
   - **Skills**: The system can load specialized "Skill" files (like the PR review checklist in `/skills/github-review/SKILL.md`) to provide domain-specific expertise during execution.
5. **Backend**: Uses a `FilesystemBackend` to manage state and virtualize the working environment.

## 🛠️ Key Components

### Agents
| Agent | Role | Key Responsibilities |
| :--- | :--- | :--- |
| **Coordinator** | Router | Task analysis, subagent delegation, and final response synthesis. |
| **Documentation Agent** | Technical Writer | Writing/updating `README.md` and API documentation. |
| **Release Notes Agent** | Release Manager | Inspecting PRs and tags to generate clear release notes. |
| **Issue Agent** | Triage Specialist | Searching, reading, and commenting on GitHub issues. |
| **Code Review Agent** | Quality Assurance | Reviewing PR diffs against a security and performance checklist. |
| **Coding Agent** | Software Engineer | Creating branches, implementing code changes, and opening PRs. |

### Supporting Files
- `agent.py`: The main entry point. Defines the LLM (Gemma 4), initializes the GitHub toolkit, configures the subagents, and invokes the coordinator.
- `utils.py`: A utility layer that maps verbose GitHub tool names to clean `snake_case` identifiers and filters the toolset for each subagent to prevent tool-overload in the LLM context.
- `AGENTS.md`: A "Convention Guide" used by the agents to maintain consistency in branching (`feat/`, `fix/`), PR labeling, and issue triaging.
- `/skills/`: A directory of specialized knowledge modules (e.g., `github-review`) that provide detailed checklists for the agents to follow.

## 📦 Installation and Execution Guide

### Prerequisites
- **Python 3.10+**
- **API Keys**:
  - `GOOGLE_API_KEY`: For the Gemma 4 LLM.
  - `GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY`, `GITHUB_REPOSITORY`: For GitHub App authentication.

### Setup
1. **Clone the repository**:
   ```bash
   git clone https://github.com/sachingarg123/agent-ai-langraph.git
   cd agent-ai-langraph
   ```
2. **Install Dependencies**:
   ```bash
   pip install deepagents langchain langchain-community langchain-google-genai python-dotenv
   ```
3. **Configure Environment**:
   Create a `.env` file in the root directory:
   ```env
   GOOGLE_API_KEY=your_google_api_key
   GITHUB_APP_ID=your_app_id
   GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"
   GITHUB_REPOSITORY=username/repo-name
   ```

### Running the Agent
Execute the main script to start the coordinator:
```bash
python agent.py
```
