from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import json
from typing import Dict, List, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import asyncio
from contextlib import AsyncExitStack
import os
from dotenv import load_dotenv
import re
import uuid
from fastapi.security import OAuth2PasswordBearer

from llms import AnthropicClient, OpenAIClient, GeminiClient

# Load environment variables
load_dotenv()

app = FastAPI()

# In-memory conversation store
conversations: Dict[str, List[Dict]] = {}

class Query(BaseModel):
    text: str
    conversation_id: Optional[str] = None

class ServerConfig:
    def __init__(self, command: str, args: List[str], env: Optional[Dict[str, str]] = None):
        self.command = command
        self.args = args
        self.env = env

def load_server_config_secrets(config):
    placeholder_pattern = re.compile(r"^<(.+)>$")
    if isinstance(config, dict):
        return {k: load_server_config_secrets(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [load_server_config_secrets(item) for item in config]
    elif isinstance(config, str):
        match = placeholder_pattern.match(config)
        if match:
            env_var = match.group(1)
            return os.getenv(env_var, f"<{env_var}_NOT_SET>")
    return config

def load_server_configs(config_path: str) -> Dict[str, ServerConfig]:
    try:
        with open(config_path, 'r') as f:
            config_data = json.load(f)

        config_data = load_server_config_secrets(config_data)

        server_configs = {}
        for server_name, server_info in config_data['mcpServers'].items():
            server_configs[server_name] = ServerConfig(
                command=server_info['command'],
                args=server_info.get('args', []),
                env=server_info.get('env')
            )
        return server_configs
    except Exception as e:
        print(f"Error loading server configs: {e}")
        raise

class MCPClientManager:
    def __init__(self, server_configs: Dict[str, ServerConfig]):
        self.server_configs = server_configs
        self.sessions: Dict[str, ClientSession] = {}
        self.exit_stack: Optional[AsyncExitStack] = None
        self.tools: List[Dict] = []

    async def initialize_sessions(self):
        self.exit_stack = AsyncExitStack()
        for server_name, config in self.server_configs.items():
            server_params = StdioServerParameters(
                command=config.command,
                args=config.args,
                env=config.env
            )
            try:
                transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
                read_stream, write_stream = transport
                session = await self.exit_stack.enter_async_context(ClientSession(read_stream, write_stream))
                await session.initialize()
                self.sessions[server_name] = session
                print(f"Connected to {server_name} MCP server")
            except Exception as e:
                print(f"Failed to connect to {server_name}: {e}")

    async def load_tools(self):
        for server_name, session in self.sessions.items():
            try:
                tools_result = await session.list_tools()
                self.tools.extend([
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "server": server_name,
                        "input_schema": tool.inputSchema
                    }
                    for tool in tools_result.tools
                ])
            except Exception as e:
                print(f"Error getting tools from {server_name}: {e}")

        print(f"Connected tools: {self.tools}")

    async def shutdown(self):
        if self.exit_stack:
            await self.exit_stack.aclose()
            self.exit_stack = None

    async def execute_tool(self, server_name: str, tool_name: str, arguments: dict) -> str:
        try:
            session = self.sessions[server_name]
            result = await session.call_tool(tool_name, arguments)
            return result
        except Exception as e:
            return f"Error executing tool: {str(e)}"

# Load MCP server configs
MCP_SERVERS = load_server_configs('server_config.json')
mcp_client_manager = MCPClientManager(MCP_SERVERS)

@app.on_event("startup")
async def startup_event():
    await mcp_client_manager.initialize_sessions()
    await mcp_client_manager.load_tools()

@app.on_event("shutdown")
async def shutdown_event():
    await mcp_client_manager.shutdown()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

@app.post("/query")
async def process_query(query: Query, token: str = Depends(oauth2_scheme)):
    try:
        conv_id = query.conversation_id or str(uuid.uuid4())
        if conv_id not in conversations:
            conversations[conv_id] = []
        messages = conversations[conv_id]
        messages.append({"role": "user", "content": query.text})

        responses = []
        MAX_STEPS = 4

        for _ in range(MAX_STEPS):
            from schema_utils import clean_openapi_schema
            function_declarations = [
                {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": clean_openapi_schema(tool["input_schema"])
                }
                for tool in mcp_client_manager.tools
                if all(k in tool for k in ("name", "description", "input_schema"))
            ]

            llm_client = GeminiClient(
                api_key=os.getenv('GEMINI_API_KEY'),
                function_declarations=function_declarations
            )

            def flatten_to_string(obj):
                if isinstance(obj, list):
                    if all(isinstance(x, dict) and x.get('type') == 'tool_result' for x in obj):
                        return "\n".join(flatten_to_string(x.get('content', '')) for x in obj)
                    return "\n".join(flatten_to_string(x) for x in obj)
                elif isinstance(obj, dict):
                    if "text" in obj and len(obj) == 1:
                        return str(obj["text"])
                    if obj.get('type') == 'tool_result' and 'content' in obj:
                        return flatten_to_string(obj['content'])
                    return "\n".join(flatten_to_string(v) for v in obj.values())
                else:
                    return str(obj)

            gemini_messages = [
                flatten_to_string(msg["content"]) if isinstance(msg, dict) and "content" in msg else flatten_to_string(msg)
                for msg in messages
            ]

            response = await llm_client.create_message(gemini_messages)
            parsed_response = llm_client.parse_response(response)

            if parsed_response.content:
                messages.append(flatten_to_string(parsed_response.content))

            if parsed_response.text_content:
                formatted_responses = []
                for text in parsed_response.text_content:
                    match = re.search(r"https://drive\.google\.com/\S+", text)
                    if match:
                        url = match.group()
                        text = text.replace(url, f"[Click to view file]({url})")
                    formatted_responses.append(text)
                responses.extend(formatted_responses)

            if not parsed_response.tool_calls:
                break

            for tool_call in parsed_response.tool_calls:
                tool_name = tool_call.name
                tool_args = tool_call.input

                tool_info = next(tool for tool in mcp_client_manager.tools if tool["name"] == tool_name)
                server_name = tool_info["server"]

                tool_result = await mcp_client_manager.execute_tool(
                    server_name=server_name,
                    tool_name=tool_name,
                    arguments=tool_args
                )

                responses.append(f"[Calling tool {tool_name} with args {tool_args}]")

                # 🔗 Manual link injection for drive_share
                if tool_name == "drive_share" and "fileId" in tool_args:
                    file_id = tool_args["fileId"]
                    link = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
                    responses.append(f"[Click to view file]({link})")
                    messages.append({"role": "assistant", "content": link})

                tool_result_msg = llm_client.parse_tool_result(tool_call=tool_call, tool_result=tool_result)
                messages.append(tool_result_msg)

        conversations[conv_id] = messages
        return {
            "conversation_id": conv_id,
            "responses": responses,
            "messages": messages
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
