{
  "mcpServers": {
    "google-drive-mcp2": {
      "command": "npx",
      "args": [
        "-y",
        "@smithery/cli@latest",
        "run",
        "@mdornich/google-drive-mcp2",
        "--key",
        "be4222ff-652a-45d5-9a93-56a29a6f3c55",
        "--profile",
        "alleged-mollusk-VH4v7j"
      ]
    },
    
    "fastapi-mcp-client": {
        "command": "npx",
        "args": [
          "mcp-remote",
          "http://localhost:8000/mcp",
            "--header",
            "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJTcmkiLCJleHAiOjE3NTIyNDEwNjh9.2WCBzXsRErVwRf8givKY5TnJQmivkWwU5HLZhtGNZMU",
            "--header",
            "Content-Type: application/json"
          ]
        }
  }
}
