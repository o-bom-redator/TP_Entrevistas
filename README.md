# AI Teleprompter

A small local teleprompter that writes what you're going to say, live. Paste a question (or a screenshot of it) and a spoken answer, based on your own profile, scrolls on screen in a couple of seconds.

It's made for people speaking in a second language who know their subject but want support to avoid freezing or rambling: practicing for interviews, recording videos, presentations, and Q&A sessions.

- **Runs on your Claude subscription.** It calls the [Claude Code](https://claude.com/claude-code) CLI, so a Claude Pro/Max plan is enough. No API key, no per-token cost.
- **Paste a screenshot.** Press Cmd+V with an image of the question and it reads the text and answers it, even when the page doesn't let you copy.
- **Answers sound like a person talking.** Short sentences at your language level, only facts from your profile, and a filter against the usual AI tells ("not just X, but Y", buzzwords, em dashes).
- **Camera-friendly compact mode.** A narrow column right under the webcam with a fixed reading zone and auto-scroll, so your eyes barely move.
- **Prepared answers.** Write answers in advance and pull them up by typing one or two words.

No dependencies: one Python file using only the standard library, plus one HTML page.

## Requirements

- macOS (the `start.sh` window helper is macOS-only; the server runs anywhere Python and Claude Code run)
- Python 3.9+
- [Claude Code](https://claude.com/claude-code) installed and logged in with your Claude account (`claude auth login`)
- Google Chrome (optional, for the borderless window)

## Setup

```bash
git clone https://github.com/<your-user>/ai-teleprompter.git
cd ai-teleprompter
cp profile.example.md profile.md
cp answers.example.md answers.md   # optional
```

Edit **`profile.md`**: who you are (paste your resume with real numbers), what the situation is (for example, the job description), and the answer settings (language, your level, length). The model only uses facts written there.

Edit **`answers.md`** (optional): prepared answers in this format:

```markdown
## Tell me about yourself
keywords: about yourself introduce background

Your answer. One idea per line, **key words** in bold.
```

Both files are in `.gitignore`, so your personal data never gets committed. Changes apply on the next question, with no restart needed.

## Use

```bash
./start.sh
```

This starts the server and opens a small window centered at the top of the screen. You can also run `python3 server.py` and open http://localhost:8765.

| Action | How |
|---|---|
| Answer from a screenshot | Cmd+Ctrl+Shift+4 (copies the area to the clipboard), click the teleprompter, Cmd+V |
| Answer from text | Paste the question in the field and press Enter |
| Prepared answer | Type 1–2 words from the question |
| Auto-scroll on/off | Space |
| Scroll speed | ↑ / ↓ |
| Font size | A− / A+ |
| Compact mode | C |
| Back to the field | Esc |

The model picker switches between **Sonnet** (default, better at sticking to your facts) and **Haiku** (a bit faster). The text usually starts appearing in about 3 seconds.

## Tips for looking at the camera

- Keep the window as close to the webcam as possible: `./start.sh 600 220` sets width and height. Hiding the macOS menu bar gains about 3 cm.
- Sit a bit farther back and increase the font. The farther you sit, the smaller your eye movement looks on camera.
- Use auto-scroll so the line you're reading stays in the same spot.
- Use the text as a guide: read a sentence, look at the camera, say it.

## Responsible use

Use it for practice, rehearsal and situations where reading notes is fine. Many interview and exam platforms forbid scripted or AI-assisted answers, so check the rules before using it in a real assessment. Always check every generated fact before you say it.

## Troubleshooting

- **`[ERROR] … OAuth access token has expired`**: run `claude auth login`.
- **Slow first answer**: the server already skips your MCP servers, hooks and plugins. If it's still slow, run `claude -p hi` once in a terminal to warm up the login.
- **Window doesn't open in the right place**: Chrome ignores size flags if it reuses a running window. `start.sh` uses a separate profile (`~/.ai-teleprompter-chrome`) to avoid that.

## License

MIT
