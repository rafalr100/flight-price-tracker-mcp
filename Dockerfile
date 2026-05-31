FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
WORKDIR /app/src
# stdio MCP server; Glama starts it and introspects (tools/list) over stdio.
CMD ["python", "server.py"]
