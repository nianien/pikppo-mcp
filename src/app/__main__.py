import argparse

from app.server import mcp

parser = argparse.ArgumentParser()
parser.add_argument("--transport", choices=["stdio", "sse", "streamable-http"], default="sse")
parser.add_argument("--host", default="0.0.0.0")
parser.add_argument("--port", type=int, default=8000)
args = parser.parse_args()

mcp.settings.host = args.host
mcp.settings.port = args.port
mcp.run(transport=args.transport)
