_STUB_REPLIES = [
    "Ward 4 (Asilmetta) has the highest concentration — 7 pending new builds with a combined area of ~2,800 sqm.",
    "Total revenue leakage estimate across all wards is approximately ₹48.2 lakhs/year based on current pending detections.",
    "The NDBI threshold is currently 0.15. Properties with delta above this are flagged as new built-up areas.",
    "18 properties are in pending verification status. Prioritise Ward 4 for field inspection this week.",
    "prop-w4-001 in Asilmetta has 96% confidence — 789 sqm new build. Highest priority for field verification.",
]


class ChatService:

    def chat(self, obj, **_):
        message = (obj.get("message") or "").strip()
        if not message:
            return 400, {"message": "message is required"}

        idx   = len(message) % len(_STUB_REPLIES)
        reply = _STUB_REPLIES[idx]
        return 200, {"response": reply}
