#!/usr/bin/env python3
"""
A reference spartan:// protocol server with CGI support.

Copyright (c) Michael Lazar
Blue Oak Model License 1.0.0
"""
import argparse
from datetime import datetime
import mimetypes
import os
import pathlib
import shutil
import subprocess
from socketserver import ThreadingTCPServer, StreamRequestHandler
from urllib.parse import unquote


class SpartanRequestHandler(StreamRequestHandler):
    def handle(self):
        try:
            self._handle()
        except ValueError as e:
            self.write_status(4, e)
        except Exception:
            self.write_status(5, "An unexpected error has occurred")
            raise

    def _handle(self):
        request = self.rfile.readline(4096)
        request = request.decode("ascii").strip("\r\n")
        print(f'{datetime.now().isoformat()} "{request}"')

        parts = request.split(" ")
        if len(parts) != 3:
            raise ValueError("Bad Request")

        hostname, path, content_length_str = parts
        try:
            content_length = int(content_length_str)
        except ValueError:
            raise ValueError("Bad Request")

        if not path:
            raise ValueError("Not Found")

        path = unquote(path)

        # Guard against breaking out of the directory
        safe_path = os.path.normpath(path.strip("/"))
        if safe_path.startswith(("..", "/")):
            raise ValueError("Not Found")

        filepath = root / safe_path

        # Read any incoming payload data sent by the client if content_length > 0
        input_data = b""
        if content_length > 0:
            input_data = self.rfile.read(content_length)

        if filepath.is_file():
            # Check if the file is executable; execute as CGI if so
            if os.access(filepath, os.X_OK):
                self.run_cgi(filepath, hostname, path, content_length, input_data)
            else:
                self.write_file(filepath)
        elif filepath.is_dir():
            if not path.endswith("/"):
                # Redirect to canonical path with trailing slash
                self.write_status(3, f"{path}/")
            elif (filepath / "index.gmi").is_file():
                self.write_file(filepath / "index.gmi")
            else:
                self.write_status(2, "text/gemini")
                self.write_line("=>..")
                for child in filepath.iterdir():
                    if child.is_dir():
                        self.write_line(f"=>{child.name}/")
                    else:
                        self.write_line(f"=>{child.name}")
        else:
            raise ValueError("Not Found")

    def run_cgi(self, filepath, hostname, path, content_length, input_data):
        """Executes a CGI script and pipes input/output."""
        env = os.environ.copy()
        env.update({
            "SERVER_SOFTWARE": "SpartanServer/1.0",
            "SERVER_NAME": hostname,
            "GATEWAY_INTERFACE": "CGI/1.1",
            "SERVER_PROTOCOL": "SPARTAN",
            "SERVER_PORT": str(self.server.server_address[1]),
            "REQUEST_METHOD": "POST" if content_length > 0 else "GET",
            "SCRIPT_FILENAME": str(filepath.resolve()),
            "SCRIPT_NAME": path,
            "QUERY_STRING": "",
            "REMOTE_ADDR": str(self.client_address[0]),
            "REMOTE_PORT": str(self.client_address[1]),
            "CONTENT_LENGTH": str(content_length),
        })

        try:
            proc = subprocess.Popen(
                [str(filepath)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(filepath.parent),
                env=env,
            )
            stdout_data, stderr_data = proc.communicate(input=input_data)

            if proc.returncode != 0:
                print(f"CGI script error ({filepath}): {stderr_data.decode('utf-8', errors='replace')}")
                self.write_status(5, "CGI execution failed")
                return

            # Write raw stdout output directly to the client socket
            self.wfile.write(stdout_data)

        except Exception as e:
            print(f"Failed to execute CGI script: {e}")
            self.write_status(5, "Internal Server Error")

    def write_file(self, filepath):
        mimetype, encoding = mimetypes.guess_type(filepath, strict=False)
        mimetype = mimetype or "application/octet-stream"
        with filepath.open("rb") as fp:
            self.write_status(2, mimetype)
            shutil.copyfileobj(fp, self.wfile)

    def write_line(self, text):
        self.wfile.write(f"{text}\n".encode("utf-8"))

    def write_status(self, code, meta):
        self.wfile.write(f"{code} {meta}\r\n".encode("ascii"))


mimetypes.add_type("text/gemini", ".gmi")

parser = argparse.ArgumentParser(description="A spartan server with CGI support")
parser.add_argument("dir", default=".", nargs="?", type=pathlib.Path)
parser.add_argument("--host", default="127.0.0.1")
parser.add_argument("--port", default=3000, type=int)
args = parser.parse_args()

root = args.dir.resolve(strict=True)
print(f"Root Directory {root}")

server = ThreadingTCPServer((args.host, args.port), SpartanRequestHandler)
print(f"Listening on {server.server_address}")

try:
    server.serve_forever()
except KeyboardInterrupt:
    pass