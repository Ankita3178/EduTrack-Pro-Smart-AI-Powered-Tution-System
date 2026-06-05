"""
EduTrack Chatbot — calls Anthropic API server-side.
Falls back to rule-based responses if no API key provided.
"""

import json, re

SYSTEM_PROMPT_TEMPLATE = """You are EduTrack AI, a helpful assistant for a tuition centre management app.
Here is the LIVE DATA from the database:
---
{context}
---
Answer questions about students, attendance, marks, fees. Be concise and specific with names and numbers.
If asked about predictions or ML insights, suggest using the ML Analysis page.
"""

def get_chatbot_response(message: str, history: list, context: str, api_key: str = "") -> dict:
    """
    Call Anthropic API server-side if api_key provided,
    else use rule-based fallback.
    """
    if api_key:
        return _anthropic_response(message, history, context, api_key)
    else:
        return _rule_based_response(message, context)

def _anthropic_response(message, history, context, api_key):
    try:
        import urllib.request

        system = SYSTEM_PROMPT_TEMPLATE.format(context=context)
        messages = [{"role": m["role"], "content": m["content"]} for m in history[-10:]]
        messages.append({"role": "user", "content": message})

        payload = json.dumps({
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 1000,
            "system": system,
            "messages": messages
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01",
                "x-api-key": api_key
            }
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
        reply = result["content"][0]["text"] if result.get("content") else "No response."
        return {"ok": True, "reply": reply, "method": "anthropic"}
    except Exception as e:
        # Fallback to rule-based
        fallback = _rule_based_response(message, context)
        fallback["method"] = "rule-based (API error)"
        fallback["api_error"] = str(e)[:120]
        return fallback

def _rule_based_response(message: str, context: str) -> dict:
    """Simple keyword-based chatbot for when no API key is set."""
    msg = message.lower().strip()
    lines = context.split("\n")

    # Parse student data from context
    students = []
    for line in lines:
        if line.startswith("Student:"):
            students.append(line)

    def student_data(name):
        name_l = name.lower()
        for s in students:
            if name_l in s.lower():
                return s
        return None

    # Greet
    if any(w in msg for w in ["hi", "hello", "hey", "greetings"]):
        return {"ok": True, "reply": "Hi! I'm EduTrack AI 👋\nI can answer questions about students, attendance, marks, and fees.\n\n⚠️ For full AI responses, set your Anthropic API key in Settings.", "method": "rule-based"}

    # Total students
    if "how many student" in msg or "total student" in msg:
        count = len(students)
        return {"ok": True, "reply": f"There are currently **{count}** students enrolled.", "method": "rule-based"}

    # Attendance for specific student
    m = re.search(r"attendance.{0,20}?([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)", message)
    if m:
        sd = student_data(m.group(1))
        if sd:
            att_part = [p for p in sd.split("|") if "Attendance" in p]
            return {"ok": True, "reply": f"📅 {att_part[0].strip() if att_part else sd}", "method": "rule-based"}

    # Marks for student
    m = re.search(r"marks?.{0,20}?([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)", message)
    if not m:
        m = re.search(r"([A-Z][a-z]+(?:\s[A-Z][a-z]+)?).{0,20}?marks?", message)
    if m:
        sd = student_data(m.group(1))
        if sd:
            mark_part = [p for p in sd.split("|") if "Latest" in p or "No marks" in p]
            return {"ok": True, "reply": f"📊 {mark_part[0].strip() if mark_part else 'No mark data found.'}", "method": "rule-based"}

    # Fee info
    if "fee" in msg or "due" in msg:
        fee_lines = []
        for s in students:
            parts = {p.split(":")[0].strip(): p.split(":",1)[1].strip() if ":" in p else "" for p in s.split("|")}
            name_part = s.split("|")[0].replace("Student:", "").strip()
            fees_part = [p for p in s.split("|") if "Due" in p]
            if fees_part:
                fee_lines.append(f"• {name_part}: {fees_part[0].strip()}")
        if fee_lines:
            return {"ok": True, "reply": "💰 Fee due dates:\n" + "\n".join(fee_lines[:10]), "method": "rule-based"}

    # List all students
    if "list" in msg and "student" in msg or "all student" in msg:
        names = []
        for s in students:
            name_part = s.replace("Student:", "").split("|")[0].strip()
            names.append(f"• {name_part}")
        if names:
            return {"ok": True, "reply": "👥 Students:\n" + "\n".join(names), "method": "rule-based"}

    # Help
    if "help" in msg or "what can" in msg:
        return {"ok": True, "reply": (
            "I can help with:\n"
            "• Student attendance (e.g. 'attendance for Aarav')\n"
            "• Test marks (e.g. 'marks for Priya')\n"
            "• Fee due dates (e.g. 'show fees')\n"
            "• Student list (e.g. 'list all students')\n\n"
            "💡 For full AI conversations, add your Anthropic API key in ⚙️ Settings."
        ), "method": "rule-based"}

    # Default
    return {"ok": True, "reply": (
        "I'm running in rule-based mode (no API key set).\n\n"
        "Try asking:\n• 'list all students'\n• 'show fees'\n• 'attendance for [name]'\n• 'marks for [name]'\n\n"
        "Or set your Anthropic API key in ⚙️ Settings for full AI responses."
    ), "method": "rule-based"}
