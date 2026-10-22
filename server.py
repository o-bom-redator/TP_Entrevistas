#!/usr/bin/env python3
"""AI Teleprompter server.

Serves the teleprompter page and streams spoken answers from the `claude` CLI
(Claude Code), so it runs on your Claude Pro/Max subscription with no API key.

  profile.md   who is speaking and for what (falls back to profile.example.md)
  answers.md   optional prepared answers (falls back to answers.example.md)

Run:  python3 server.py   then open http://localhost:8765
"""
import json
import os
import re
import subprocess
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
PORT = int(os.environ.get("PORT", 8765))

RULES = """You write spoken answers that the speaker will READ aloud from a teleprompter.
Everything you know about the speaker and the situation is in the profile below.

# How to write the answer
- First person, as the speaker. Natural spoken language, friendly and confident.
- Follow the language, level and length in "Answer settings". If missing: English, short sentences, 190–230 words.
- Structure: one-sentence direct answer, then 2–4 concrete points or steps, with ONE real example from the profile, then a short closing sentence.
- If the question asks to "show" or "walk through" something, describe clear numbered steps ("Step one…") with a quick concrete example.
- Mark 1–3 key words per paragraph in **bold**. One idea per line; separate lines with a single newline.
- Only use facts from the profile. Never invent numbers, names, durations or frequencies. Keep each number tied to the right job.
- If a needed fact is unknown (salary, start date, etc.), write a placeholder like [YOUR NUMBER].
- Output ONLY the answer text. No title, no preamble, no notes.
- Exception: when the question comes as a screenshot, the very first line MUST be "Q: " + the exact question text, then the answer.

# Sound like a real person talking, not like AI
NEVER use these patterns:
- Contrast framing, the #1 AI tell. Any sentence that sets up "not X" against "Y" is FORBIDDEN, in any form: "X, not just Y", "not only X but also Y", "it's not about X, it's about Y", "I don't just X, I Y", "as X, not as Y", "not as theory, but as practice", "more than just", "rather than simply", "instead of just". Write only the positive part.
  Bad: "I read it as a reader, not as a writer." Good: "I read it like a normal reader would."
  Bad: "I don't just use AI, I understand how to guide it." Good: "I use AI every day, and I know how to write good instructions for it."
- Rule of three everywhere (lists of exactly three adjectives or nouns: "fast, accurate, and consistent").
- Opening by restating or reframing the question ("Making an AI draft sound human is about…", "Great question", "When it comes to…").
- Grand closing lines and slogans ("That's what makes content truly ready", "This is exactly what you need").
- Em dashes (—). Use a period or a comma instead.
- Buzzwords: seamless, leverage, robust, elevate, delve, crucial, pivotal, landscape, journey, game-changer, intentional/with intention, at the end of the day, in today's world, resonate, tailored, ensure, streamline, holistic.
- Colon reveals ("The result? …", "Here's the thing: …").
Instead: start with a plain, direct sentence ("I usually do it in four steps."). Use "I" and concrete actions from real work. Vary sentence length a little. Small natural connectors are good: "so", "then", "for example", "in my case", "honestly". End with a simple, modest sentence, like a person would.
Before writing each sentence, check it: does it contain "not" or "just" comparing two things? If yes, rewrite it without the comparison.
"""

# Env vars from a parent Claude Code session that would break the CLI's own login.
STRIP_ENV = {"ANTHROPIC_BASE_URL", "ANTHROPIC_API_KEY", "CLAUDECODE"}
CLEAN_ENV = {k: v for k, v in os.environ.items()
             if k not in STRIP_ENV and not k.startswith("CLAUDE_CODE_")}
CLEAN_ENV["MAX_THINKING_TOKENS"] = "0"  # no thinking: text starts sooner
WORKDIR = tempfile.mkdtemp(prefix="teleprompter-")


def read_user_file(name):
    """Your own file if it exists, else the committed example."""
    path = HERE / f"{name}.md"
    if not path.exists():
        path = HERE / f"{name}.example.md"
    return path.read_text(encoding="utf-8")


def system_prompt():
    # Read on every request, so edits to profile.md apply without a restart.
    return RULES + "\n# Profile\n" + read_user_file("profile")


def prepared_answers():
    """Parse answers.md: '## Question', optional 'keywords: …' line, then the answer."""
    answers = []
    for block in re.split(r"^## ", read_user_file("answers"), flags=re.M)[1:]:
        question, _, body = block.partition("\n")
        keywords = ""
        m = re.match(r"\s*keywords:(.*)\n", body)
        if m:
            keywords, body = m.group(1).strip(), body[m.end():]
        answers.append({"q": question.strip(), "k": keywords, "a": body.strip()})
    return answers


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send_body(self, body, content_type):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/":
            self.send_body((HERE / "static" / "index.html").read_bytes(), "text/html; charset=utf-8")
        elif path == "/answers":
            self.send_body(json.dumps(prepared_answers()).encode(), "application/json")
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path != "/ask":
            self.send_error(404)
            return
        data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        question = data.get("q", "").strip()
        image = data.get("image", "")  # data URL of a pasted screenshot
        model = data.get("model") if data.get("model") in ("haiku", "sonnet", "opus") else "sonnet"

        if image:
            media_type, b64 = image[5:].split(";base64,", 1)
            content = [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
                {"type": "text", "text": "The screenshot shows the question. First line: write 'Q: ' followed by the "
                                         "exact question text. Then answer it following all the rules."},
            ]
        else:
            content = [{"type": "text", "text": "Question:\n" + question}]
        user_msg = json.dumps({"type": "user", "message": {"role": "user", "content": content}})

        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        proc = subprocess.Popen(
            ["claude", "-p", "--model", model, "--system-prompt", system_prompt(),
             "--input-format", "stream-json",
             "--output-format", "stream-json", "--include-partial-messages", "--verbose",
             "--tools", "", "--no-session-persistence",
             # skip your MCP servers, hooks and plugins: they add a long startup delay
             "--strict-mcp-config", "--setting-sources", ""],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            env=CLEAN_ENV, cwd=WORKDIR, text=True)
        proc.stdin.write(user_msg + "\n")
        proc.stdin.close()

        try:
            for line in proc.stdout:
                try:
                    msg = json.loads(line)
                except ValueError:
                    continue
                if msg.get("type") == "stream_event":
                    delta = msg["event"].get("delta", {})
                    if delta.get("type") == "text_delta":
                        text = delta["text"].replace(" — ", ", ").replace("—", ", ")
                        self.wfile.write(text.encode())
                        self.wfile.flush()
                elif msg.get("type") == "result":
                    if msg.get("is_error"):
                        self.wfile.write(f"\n[ERROR] {msg.get('result', '')}".encode())
                    break  # with stream-json input the CLI waits for more input after the result
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            proc.kill()


if __name__ == "__main__":
    print(f"AI Teleprompter: http://localhost:{PORT}  (Ctrl+C to stop)")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
