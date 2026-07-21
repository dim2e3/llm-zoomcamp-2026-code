import sys

from jdg_assistant.assistant import create_assistant

if __name__ == "__main__":
    assistant = create_assistant()
    query = sys.argv[1] if len(sys.argv) > 1 else "Как зарегистрировать JDG?"
    answer = assistant.rag(query, lang="ru")
    print(answer)
