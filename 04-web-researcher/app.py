"""
04-web-researcher/app.py
════════════════════════════════════════════════════════════════════════════════
APP 04 — Web Researcher

What this does:
  You type any research question. Claude searches the web, reads pages,
  and synthesizes a clear, sourced answer — all autonomously.

New concept introduced in this app:

  1. TOOL USE
     Claude can't browse the internet on its own. But you can give it
     "tools" — functions your code provides — that it can call whenever
     it decides they're useful.

     You define tools by describing them in a structured format:
       - name:         what to call the function
       - description:  when Claude should use it (critical — Claude reads this)
       - input_schema: the JSON schema for the function's arguments

     When Claude wants to use a tool, it stops generating text and instead
     produces a tool_use content block with the function name and arguments.
     Your code executes the function and sends the result back to Claude.
     Claude then continues its response using that result.

  2. THE AGENTIC LOOP
     Apps 01–03 made one API call per user input. App 04 makes *many*:

       You: "What is the James Webb telescope?"
       →  Claude decides to search                  [stop_reason: "tool_use"]
       →  Your code runs web_search("James Webb telescope")
       →  Your code sends the result back to Claude
       →  Claude decides to fetch a specific page    [stop_reason: "tool_use"]
       →  Your code runs fetch_webpage("https://...")
       →  Your code sends the result back to Claude
       →  Claude writes and returns the final answer  [stop_reason: "end_turn"]

     This loop — call Claude, check stop_reason, execute tools, repeat —
     is the foundation of every agentic AI system.

  3. stop_reason: "tool_use" vs "end_turn"
     The stop_reason field tells you WHY Claude stopped generating:
       "end_turn"  → Claude is done. Read response.content for the answer.
       "tool_use"  → Claude wants to call a tool. Find the tool_use blocks,
                     execute them, and send results back as a "user" message.

  4. THE messages ARRAY GROWS
     Each loop iteration adds to the messages list:
       [user question]
       [assistant: tool_use block(s)]      ← Claude's tool requests
       [user: tool_result block(s)]        ← your code's results
       [user: tool_use block(s)]           ← Claude might search again
       [user: tool_result block(s)]
       [assistant: final text answer]      ← end_turn

     The full history is sent every time, so Claude sees everything it
     searched and read before writing its answer.

Run it:
  python 04-web-researcher/app.py
════════════════════════════════════════════════════════════════════════════════
"""

import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))
from shared.claude_client import client, MODEL
from shared.helpers import get_user_input, print_header, print_section


# ── Tool definitions ──────────────────────────────────────────────────────────
#
# These dicts are passed to client.messages.create(tools=TOOLS).
# Claude reads the name and description to decide when to use each tool.
# The input_schema tells Claude what arguments to provide (JSON Schema format).
#
# IMPORTANT: Write descriptions carefully. Claude uses them to decide WHEN
# to call the tool. Vague descriptions = wrong tool choices.
#
TOOLS = [
    {
        "name": "web_search",
        "description": (
            "Search the web for information on any topic. Returns titles, "
            "URLs, and short descriptions from search results. Use this first "
            "to discover relevant sources. If results are thin, try a more "
            "specific query or different keywords."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query. Be specific for best results."
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "fetch_webpage",
        "description": (
            "Fetch and read the full text of a webpage. Returns the page "
            "content cleaned of HTML, up to ~3000 words. Use this after "
            "web_search to read articles, Wikipedia pages, or any URL in full."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The full URL to fetch (must start with http:// or https://)."
                }
            },
            "required": ["url"]
        }
    }
]


SYSTEM_PROMPT = """You are a thorough research assistant with web access.

When asked a question:
1. Search the web to find relevant sources
2. Fetch and read the most relevant pages in full
3. Synthesize what you found into a clear, well-sourced answer
4. Cite your sources with URLs at the end

Be thorough — search multiple times with different queries if needed.
Prefer specific, factual answers with concrete details over vague summaries.
If initial search results are sparse, search again with refined keywords."""


# ── Tool implementations ───────────────────────────────────────────────────────

def web_search(query: str) -> str:
    """
    Search via DuckDuckGo's Instant Answer API.

    This API returns Wikipedia-sourced abstracts and related topics for most
    queries. It's free and requires no API key — ideal for learning.

    For queries with no instant answer (very specific or obscure topics),
    it returns related topics which still give Claude useful starting URLs.
    """
    try:
        resp = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"},
            headers={"User-Agent": "cc-sandbox-learning-app/1.0"},
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()

        results = []

        # Main abstract (usually from Wikipedia)
        if data.get("AbstractText"):
            results.append(f"Summary: {data['AbstractText']}")
            if data.get("AbstractURL"):
                results.append(f"Source: {data['AbstractURL']}")

        # Related topics — each has a short description and a URL
        for topic in data.get("RelatedTopics", [])[:6]:
            if isinstance(topic, dict) and topic.get("Text"):
                line = topic["Text"]
                if topic.get("FirstURL"):
                    line += f"\n  URL: {topic['FirstURL']}"
                results.append(line)

        # Infobox data (structured facts — e.g., population, founded date)
        infobox = data.get("Infobox", {})
        if infobox and infobox.get("content"):
            facts = []
            for item in infobox["content"][:5]:
                if item.get("label") and item.get("value"):
                    facts.append(f"  {item['label']}: {item['value']}")
            if facts:
                results.append("Key facts:\n" + "\n".join(facts))

        if results:
            return "\n\n".join(results)

        return (
            f"No instant answer found for '{query}'. "
            "Try fetching a specific URL like a Wikipedia article "
            "(e.g. https://en.wikipedia.org/wiki/Topic_Name), "
            "or try a different search query."
        )

    except requests.RequestException as e:
        return f"Search request failed: {e}"
    except Exception as e:
        return f"Search error: {e}"


def fetch_webpage(url: str) -> str:
    """
    Fetch a webpage and return its text content, cleaned of HTML.

    Truncates at 3000 words to stay within a reasonable context budget.
    Uses BeautifulSoup if available for cleaner extraction; falls back
    to regex-based stripping otherwise.
    """
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": "cc-sandbox-learning-app/1.0"},
            timeout=15
        )
        resp.raise_for_status()

        # Extract text — prefer BeautifulSoup for clean results
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")
            # Remove noise elements
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
            text = soup.get_text(separator="\n")
        except ImportError:
            import re
            text = re.sub(r"<[^>]+>", " ", resp.text)

        # Clean up whitespace — keep only lines with real content
        lines = [line.strip() for line in text.splitlines()]
        lines = [line for line in lines if len(line) > 25]
        text = "\n".join(lines)

        # Truncate to ~3000 words to control context cost
        words = text.split()
        if len(words) > 3000:
            text = " ".join(words[:3000]) + "\n\n[content truncated at 3000 words]"

        return text.strip() or "Page fetched but no readable text found."

    except requests.HTTPError as e:
        return f"HTTP error fetching {url}: {e}"
    except requests.RequestException as e:
        return f"Network error fetching {url}: {e}"
    except Exception as e:
        return f"Error fetching {url}: {e}"


def execute_tool(name: str, inputs: dict) -> str:
    """Dispatch a tool call by name to the correct function."""
    if name == "web_search":
        return web_search(inputs["query"])
    elif name == "fetch_webpage":
        return fetch_webpage(inputs["url"])
    else:
        return f"Unknown tool: '{name}'"


# ── The agentic loop ───────────────────────────────────────────────────────────
#
# This is the core pattern of every tool-using agent.
# Study this loop carefully — you will write variations of it in every app
# from here on.
#
def research(question: str) -> str:
    """
    Run the agentic research loop until Claude reaches a final answer.

    The loop:
      1. Send the current messages to Claude
      2. If stop_reason == "end_turn": extract and return the final text
      3. If stop_reason == "tool_use":
           a. Append Claude's full response (including tool_use blocks) to messages
           b. Execute each requested tool
           c. Append all tool results as a new "user" message
           d. Go to step 1

    The messages list grows on every iteration — Claude sees everything it
    has searched and read when it decides what to do next.
    """
    messages = [{"role": "user", "content": question}]
    iteration = 0
    max_iterations = 10  # prevent runaway loops

    print("\n  Researching", end="", flush=True)

    while iteration < max_iterations:
        iteration += 1

        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages
        )

        # ── Case 1: Claude finished — return the answer ────────────────────
        if response.stop_reason == "end_turn":
            print(" done.\n")
            # Extract all text blocks from the response
            answer_parts = [block.text for block in response.content if hasattr(block, "text")]
            return "\n".join(answer_parts)

        # ── Case 2: Claude wants to use one or more tools ──────────────────
        elif response.stop_reason == "tool_use":

            # Step A: Append Claude's response (with tool_use blocks) to history.
            # Claude's tool requests must be in the history before the results.
            messages.append({"role": "assistant", "content": response.content})

            # Step B: Execute each tool and collect results
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    # Show the user what Claude is doing
                    arg_preview = str(list(block.input.values())[0])[:55]
                    print(f"\n  [{block.name}: {arg_preview}]", end="", flush=True)

                    result = execute_tool(block.name, block.input)

                    # tool_result blocks must reference the tool_use id they answer
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,   # ← must match the tool_use block's id
                        "content": result
                    })

            # Step C: Send results back as a user message. Claude treats tool
            # results as "user" role — it's always user/assistant alternating.
            messages.append({"role": "user", "content": tool_results})

        else:
            print(f"\n  Unexpected stop_reason: {response.stop_reason}")
            break

    return "Research exceeded the maximum number of iterations. The answer may be incomplete."


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print_header("App 04 — Web Researcher")
    print(f"  Model: {MODEL}")
    print("\n  Ask any research question. Claude will search the web,")
    print("  read relevant pages, and give you a sourced answer.")
    print("  Type 'quit' to exit.\n")

    while True:
        question = get_user_input("Your research question")

        if question.lower() in ("quit", "exit", "q"):
            print("\nGoodbye!")
            break

        if not question:
            print("  Please enter a question.")
            continue

        answer = research(question)
        print_section("Answer", answer)
        print()


if __name__ == "__main__":
    main()
