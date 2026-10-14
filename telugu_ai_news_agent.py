"""
Telugu AI News Agent
Scans top AI news sources, curates business/money-making AI stories,
and produces a bilingual Telugu+English newsletter.

Usage:
    pip install anthropic
    export ANTHROPIC_API_KEY=your_key_here
    python telugu_ai_news_agent.py
"""

import anthropic
import datetime

client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are a bilingual AI news curator for a Telugu-speaking community.

Your job:
1. Search for the LATEST AI news (last 7 days) that is relevant to making money or building a business using AI — no deep technical stuff.
2. Curate the TOP 5-7 most exciting and actionable stories.
3. Present each story in BOTH Telugu AND English side-by-side.

Focus areas (pick stories about these):
- AI tools anyone can use to earn money (freelancing, content creation, etc.)
- New AI products or platforms businesses can use
- Real people / small businesses making money with AI
- New AI features in popular apps (ChatGPT, Canva, etc.) that save time or money
- AI job opportunities or new roles
- Easy-to-start AI side hustles or business ideas

Avoid:
- Deep research papers or technical benchmarks
- AI safety debates
- Stock market speculation
- Anything requiring coding knowledge

Output format for EACH story:
---
📌 **Story Title (English)**

🇬🇧 **English Summary** (2-3 sentences, clear and simple)

🇮🇳 **Telugu Summary / తెలుగు సారాంశం** (2-3 sentences in Telugu script)

💡 **How you can use this / మీరు దీన్ని ఎలా ఉపయోగించవచ్చు** (1-2 actionable sentences in both languages)

🔗 Source: [publication name]
---

At the end, add a short closing message in both Telugu and English encouraging the community.
"""


def run_news_agent():
    today = datetime.date.today().strftime("%B %d, %Y")

    print(f"\n🤖 Telugu AI News Agent — {today}")
    print("=" * 60)
    print("Scanning latest AI news... (this may take a minute)\n")

    messages = [
        {
            "role": "user",
            "content": (
                f"Today is {today}. Please search for the latest AI news "
                "from the past 7 days that helps people make money or build "
                "a business using AI. Focus on practical, accessible stories "
                "— not technical research. Find at least 5 good stories, "
                "then produce the bilingual Telugu+English newsletter."
            ),
        }
    ]

    # Use streaming — web search + long output benefits from it
    with client.messages.stream(
        model="claude-opus-4-7",
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        tools=[
            {"type": "web_search_20260209", "name": "web_search"},
        ],
        messages=messages,
    ) as stream:
        full_response = ""
        searching = False

        for event in stream:
            # Show search activity indicator
            if event.type == "content_block_start":
                block = event.content_block
                if hasattr(block, "type") and block.type == "server_tool_use":
                    if not searching:
                        print("🔍 Searching news sources...\n")
                        searching = True

            # Stream the text output
            elif event.type == "content_block_delta":
                delta = event.delta
                if hasattr(delta, "type") and delta.type == "text_delta":
                    print(delta.text, end="", flush=True)
                    full_response += delta.text

        final = stream.get_final_message()

    print("\n\n" + "=" * 60)
    print(f"✅ Newsletter generated! ({final.usage.output_tokens} tokens used)")

    # Save to file
    output_file = f"ai_news_{datetime.date.today().strftime('%Y_%m_%d')}.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"# AI News for Telugu Community — {today}\n\n")
        f.write(full_response)
    print(f"📄 Saved to: {output_file}")


if __name__ == "__main__":
    run_news_agent()
