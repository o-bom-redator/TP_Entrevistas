#!/usr/bin/env python3
"""TP Entrevistas: AI teleprompter server.

Serves the teleprompter page and streams spoken answers from the `claude` CLI
(Claude Code), so it runs on your Claude Pro/Max subscription with no API key.
Everything you set up in the page is saved in data/ (git-ignored).

Run:  python3 server.py   then open http://localhost:8765
"""
import base64
import io
import json
import os
import re
import subprocess
import tempfile
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from xml.etree import ElementTree

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
SETTINGS = DATA / "settings.json"
CARD_FILES = {"generate": DATA / "cards.md", "script": DATA / "script.md"}
PORT = int(os.environ.get("PORT", 8765))

DEFAULT_SETTINGS = {
    "mode": "",           # "generate" (AI cards + live answers) or "script" (your own text)
    "language": "en",     # "en" or "pt"
    "level": "B2",        # speaker level for English answers
    "minutes": 2,         # answer length
    "background": "",     # resume / bio
    "target": "",         # job description or area
}

RULES = """You write spoken answers that the speaker will READ aloud from a teleprompter, usually in a job interview.
Everything you know about the speaker and the situation is in the profile below.

# How to write the answer
- First person, as the speaker. Natural spoken language, friendly and confident.
- Structure: one-sentence direct answer, then 2–4 concrete points or steps, with ONE real example from the profile, then a short closing sentence.
- If the question asks to "show" or "walk through" something, describe clear numbered steps ("Step one…") with a quick concrete example.
- Mark 1–3 key words per paragraph in **bold**. One idea per line; separate lines with a single newline.
- Only use facts from the profile. Never invent numbers, names, durations or frequencies. Keep each number tied to the right job.
- If a needed fact is unknown (salary, start date, a personal example the profile doesn't have), write a placeholder like [YOUR NUMBER] or [YOUR EXAMPLE].
- Output ONLY the answer text. No title, no preamble, no notes.
- Exception: when the question comes as a screenshot, the very first line MUST be "Q: " + the exact question text, then the answer.

# Sound like a real person talking, not like AI
NEVER use these patterns (in any language):
- Contrast framing, the #1 AI tell. Any sentence that sets up "not X" against "Y" is FORBIDDEN, in any form: "X, not just Y", "not only X but also Y", "it's not about X, it's about Y", "I don't just X, I Y", "as X, not as Y", "more than just", "rather than simply", "instead of just". In Portuguese: "não só X, mas também Y", "não é sobre X, é sobre Y", "não apenas X, mas Y", "mais do que X", "em vez de apenas". Write only the positive part.
  Bad: "I read it as a reader, not as a writer." Good: "I read it like a normal reader would."
  Bad: "I don't just use AI, I understand how to guide it." Good: "I use AI every day, and I know how to write good instructions for it."
  Ruim: "Mantenho a consistência ao longo do ano, não só em meses bons." Bom: "Mantenho a consistência o ano inteiro."
- Rule of three everywhere (lists of exactly three adjectives or nouns: "fast, accurate, and consistent").
- Opening by restating or reframing the question ("Making an AI draft sound human is about…", "Great question", "When it comes to…", "Ótima pergunta", "Quando falamos de…").
- Grand closing lines and slogans ("That's what makes content truly ready", "This is exactly what you need").
- Em dashes (—). Use a period or a comma instead.
- Buzzwords: seamless, leverage, robust, elevate, delve, crucial, pivotal, landscape, journey, game-changer, intentional, at the end of the day, in today's world, resonate, tailored, ensure, streamline, holistic. In Portuguese: alavancar, robusto, jornada, crucial, fundamental, no cenário atual, nos dias de hoje, potencializar, sinergia.
- Colon reveals ("The result? …", "Here's the thing: …", "O resultado? …").
Instead: start with a plain, direct sentence ("I usually do it in four steps."). Use "I" and concrete actions from real work. Vary sentence length a little. Small natural connectors are good ("so", "then", "for example", "in my case", "honestly" / "então", "por exemplo", "no meu caso", "sinceramente"). End with a simple, modest sentence, like a person would.
Before writing each sentence, check it: does it compare two things with "not"/"just" ("não"/"só")? If yes, rewrite it without the comparison.
"""

CARDS_TASK = """Write the {n} questions this speaker is most likely to be asked in this interview, each with its answer.
Mix classic questions (tell me about yourself, why this role, strengths and weaknesses, a challenge you solved) with questions specific to the job or area.
Use EXACTLY this format for each card, with nothing before the first card and no "---" separators:

## <question>
keywords: <6-10 lowercase words someone might type to find this question>

<answer, following all the rules>
"""

# Env vars from a parent Claude Code session that would break the CLI's own login.
STRIP_ENV = {"ANTHROPIC_BASE_URL", "ANTHROPIC_API_KEY", "CLAUDECODE"}
CLEAN_ENV = {k: v for k, v in os.environ.items()
             if k not in STRIP_ENV and not k.startswith("CLAUDE_CODE_")}
CLEAN_ENV["MAX_THINKING_TOKENS"] = "0"  # no thinking: text starts sooner
WORKDIR = tempfile.mkdtemp(prefix="teleprompter-")


def load_settings():
    settings = dict(DEFAULT_SETTINGS)
    if SETTINGS.exists():
        settings.update(json.loads(SETTINGS.read_text(encoding="utf-8")))
    return settings


def save_settings(settings):
    DATA.mkdir(exist_ok=True)
    SETTINGS.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")


def system_prompt():
    s = load_settings()
    words = f"{95 * s['minutes'] - 20}–{115 * s['minutes']}"
    if s["language"] == "pt":
        lang = (f"Language: Brazilian Portuguese, natural spoken style. Length: {words} words "
                f"(about {s['minutes']} minutes read aloud). Never longer.")
    else:
        lang = (f"Language: English. Speaker level {s['level']}: "
                + ("short sentences (max ~15 words), common words, no idioms, no tongue-twisters. "
                   if s["level"] in ("B1", "B2") else "natural professional English. ")
                + f"Length: {words} words (about {s['minutes']} minutes read aloud). Never longer.")
    return (RULES
            + "\n# Answer settings\n" + lang
            + "\n\n# Speaker\n" + (s["background"].strip() or "No background given. Keep answers general and use placeholders for personal facts.")
            + "\n\n# Job or area\n" + (s["target"].strip() or "Not specified."))


def parse_cards(text):
    """'## Question', optional 'keywords: …' line, then the body."""
    cards = []
    for block in re.split(r"^## ", text, flags=re.M)[1:]:
        question, _, body = block.partition("\n")
        keywords = ""
        m = re.match(r"\s*keywords:(.*)\n", body)
        if m:
            keywords, body = m.group(1).strip(), body[m.end():]
        body = re.sub(r"^\s*-{3,}\s*$", "", body, flags=re.M)  # stray markdown separators
        cards.append({"q": question.strip(), "k": keywords, "a": body.strip()})
    return cards


def script_to_cards_md(text):
    """Your own text: '## Title' lines split it into cards; otherwise it is one card."""
    text = text.strip()
    if re.search(r"^## ", text, flags=re.M):
        return text if text.startswith("## ") else "## Intro\n\n" + text
    return "## Script\n\n" + text


def docx_to_text(data):
    """Plain text of a .docx (stdlib only). Headings become '## ' lines: paragraphs with a
    heading style (Word in Portuguese names it 'Ttulo1'), or short lines that are all bold."""
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        root = ElementTree.fromstring(z.read("word/document.xml"))
    lines = []
    for p in root.iter(f"{{{ns['w']}}}p"):
        text = "".join(t.text or "" for t in p.iter(f"{{{ns['w']}}}t")).strip()
        if not text:
            continue
        style = p.find("w:pPr/w:pStyle", ns)
        styled = style is not None and re.match(r"(Heading|T\w?tulo|Title)", style.get(f"{{{ns['w']}}}val", ""), re.I)
        runs = [r for r in p.iter(f"{{{ns['w']}}}r") if (r.findtext("w:t", "", ns) or "").strip()]
        all_bold = runs and all(r.find("w:rPr/w:b", ns) is not None for r in runs)
        is_heading = styled or (all_bold and len(text) < 100 and not text.endswith("."))
        lines.append(("## " if is_heading else "") + text)
    return "\n\n".join(lines)


def run_claude(model, content, write):
    """Stream the answer text to write(); returns the full text."""
    user_msg = json.dumps({"type": "user", "message": {"role": "user", "content": content}})
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
    full = ""
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
                    full += text
                    write(text)
            elif msg.get("type") == "result":
                if msg.get("is_error"):
                    write(f"\n[ERROR] {msg.get('result', '')}")
                break  # with stream-json input the CLI waits for more input after the result
    finally:
        proc.kill()
    return full


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send_body(self, body, content_type="application/json"):
        if not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def start_stream(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        def write(text):
            self.wfile.write(text.encode())
            self.wfile.flush()
        return write

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/":
            self.send_body((HERE / "static" / "index.html").read_bytes(), "text/html; charset=utf-8")
        elif path == "/settings":
            self.send_body(load_settings())
        elif path == "/cards":
            f = CARD_FILES.get(load_settings()["mode"])
            self.send_body(parse_cards(f.read_text(encoding="utf-8")) if f and f.exists() else [])
        else:
            self.send_error(404)

    def do_POST(self):
        data = json.loads(self.rfile.read(int(self.headers["Content-Length"])) or b"{}")
        model = data.get("model") if data.get("model") in ("haiku", "sonnet", "opus") else "sonnet"

        if self.path == "/settings":
            settings = load_settings()
            settings.update({k: v for k, v in data.items() if k in DEFAULT_SETTINGS})
            save_settings(settings)
            self.send_body(settings)

        elif self.path == "/extract":  # attached file -> plain text
            raw = base64.b64decode(data["data"].split(",", 1)[-1])
            if data.get("name", "").lower().endswith(".docx"):
                text = docx_to_text(raw)
            else:
                text = raw.decode("utf-8", errors="replace")
            self.send_body({"text": text})

        elif self.path == "/script":  # your own text becomes the cards
            DATA.mkdir(exist_ok=True)
            CARD_FILES["script"].write_text(script_to_cards_md(data.get("text", "")), encoding="utf-8")
            self.send_body({"ok": True})

        elif self.path == "/generate-cards":
            write = self.start_stream()
            n = max(3, min(15, int(data.get("count", 8))))
            content = [{"type": "text", "text": CARDS_TASK.format(n=n)}]
            try:
                full = run_claude(model, content, write)
                if parse_cards(full):
                    DATA.mkdir(exist_ok=True)
                    CARD_FILES["generate"].write_text(full.strip() + "\n", encoding="utf-8")
            except (BrokenPipeError, ConnectionResetError):
                pass

        elif self.path == "/ask":
            if data.get("image"):  # data URL of a pasted screenshot
                media_type, b64 = data["image"][5:].split(";base64,", 1)
                content = [
                    {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
                    {"type": "text", "text": "The screenshot shows the question. First line: write 'Q: ' followed by the "
                                             "exact question text. Then answer it following all the rules."},
                ]
            else:
                content = [{"type": "text", "text": "Question:\n" + data.get("q", "").strip()}]
            write = self.start_stream()
            try:
                run_claude(model, content, write)
            except (BrokenPipeError, ConnectionResetError):
                pass
        else:
            self.send_error(404)


if __name__ == "__main__":
    print(f"TP Entrevistas: http://localhost:{PORT}  (Ctrl+C to stop)")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
