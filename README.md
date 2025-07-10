# FastAPI MCP Client

A FastAPI application implementing MCP (Model Control Protocol) Client for LLM integration. This project demonstrates how to expose FastAPI endpoints as MCP tools for language model interaction.

## Features

- FastAPI-based web server with MCP integration
- JWT-based authentication
- Automatic MCP tool generation from FastAPI endpoints
- Containerized with Docker
- Environment-based configuration

## Prerequisites

- Python 3.10+
- Docker (optional, for containerized deployment)
- Google Cloud credentials (if using Google Drive integration)

## Getting Started

### Local Development

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/fast-mcp-client.git
   cd fast-mcp-client
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. Run the development server:
   ```bash
   uvicorn main:app --reload
   ```

### Docker

1. Build the Docker image:
   ```bash
   docker build -t fast-mcp-client .
   ```

2. Run the container:
   ```bash
   docker run -p 8000:8000 --env-file .env fast-mcp-client
   ```

## Environment Variables

Create a `.env` file in the root directory with the following variables:

```
# Server
PORT=8000
DEBUG=True

# Authentication
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Google Drive API (if used)
GOOGLE_DRIVE_CREDENTIALS=path/to/credentials.json
```

## API Documentation

Once the server is running, you can access the following endpoints:

- **Interactive API Docs**: http://localhost:8000/docs
- **Alternative API Docs**: http://localhost:8000/redoc
- **MCP Endpoint**: http://localhost:8000/mcp

## MCP Integration

This application uses `fastapi-mcp` to automatically expose FastAPI endpoints as MCP tools. The following endpoints are exposed as MCP tools:

- `query` - Main query endpoint for MCP interactions
- `register` - User registration
- `login` - User authentication
- `read_users_me` - Get current user info
- `update_user_me` - Update current user info
- `delete_user_me` - Delete current user

## Project Structure

```
.
├── .dockerignore
├── .env.example
├── .gitignore
├── Dockerfile
├── README.md
├── auth_setup.py      # Authentication setup and middleware
├── client.py          # Main FastAPI application
├── main.py            # Application entry point with MCP setup
├── requirements.txt   # Python dependencies
└── tools/             # Custom MCP tools
    ├── __init__.py
    └── gdrive_search.py  # Google Drive search tool
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## License

MIT

## Acknowledgments

- Inspired by [aswincandra/fast-mcp-client](https://github.com/aswincandra/fast-mcp-client)