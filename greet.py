#!/usr/bin/env python3
import os
import sys

# 1. Read input payload if sent by the client
content_length = int(os.environ.get("CONTENT_LENGTH", "0"))
user_name = ""

if content_length > 0:
    # Read the name sent in the request body
    user_name = sys.stdin.read(content_length).strip()

# 2. Always output a Successful Spartan status header (Code 2)
sys.stdout.write("2 text/gemini\r\n")

if not user_name:
    # 3a. If no payload was provided, show the Spartan prompt line (=:)
    print("# Welcome to the Greeting Service")
    print("Please enter your name below to continue:\n")
    print("=: /greet.py Enter your name:")
else:
    # 3b. If a name was submitted in the payload, show the greeting
    print(f"# Hello, {user_name}!")
    print(f"Welcome to the Spartan network, {user_name}. It's great to meet you!\n")
    print("=> /greet.py Go back home")