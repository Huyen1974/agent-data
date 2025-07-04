class MemoryManager:
    def __init__(self):
        # Simple in-memory storage for conversation history per session
        self.history = {}  # { session_id: [{"role": "user/assistant", "content": "..."}] }

    def add_message(self, session_id: str, role: str, content: str):
        if session_id not in self.history:
            self.history[session_id] = []
        self.history[session_id].append({"role": role, "content": content})
        print(f"MemoryManager: Added message for session {session_id}. History length: {len(self.history[session_id])}")

    def get_history(self, session_id: str) -> list:
        return self.history.get(session_id, [])

    def clear_session(self, session_id: str):
        if session_id in self.history:
            del self.history[session_id]
            print(f"MemoryManager: Cleared history for session {session_id}.")
