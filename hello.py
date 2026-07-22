#!/usr/bin/env python3
import sys

# 1. Output the Spartan response header (Code 2 = Success, followed by MIME type)
sys.stdout.write("2 text/gemini\r\n")

# 2. Output the Gemini-formatted body content
print("# Hello, World!")
print("This page was generated dynamically by a Python CGI script.")
