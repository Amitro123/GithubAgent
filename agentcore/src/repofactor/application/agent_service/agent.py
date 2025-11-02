import os
from typing import List
import difflib

class AgentCore:
    def __init__(self, repo_path: str):
        self.repo_path = repo_path

    def list_py_files(self) -> List[str]:
        # שלוף כל קבצי ה-python ב-repo
        py_files = []
        for root, _, files in os.walk(self.repo_path):
            for file in files:
                if file.endswith(".py"):
                    py_files.append(os.path.join(root, file))
        return py_files

    def analyze_dependencies(self):
        # כאן אפשר לנתח imports ולבנות מפה ראשונית
        pass

    def refactor_file(self, file_path: str, instruction: str) -> str:
        # קריאה ל-LLM/סוכן/פונקציית ריפקטור, החזרת הקוד החדש
        with open(file_path, encoding='utf-8') as f:
            old_code = f.read()
        # כאן שמש ב-API שלך (דמה לדוג'):
        new_code = self.llm_refactor(old_code, instruction)
        return new_code

    def llm_refactor(self, code: str, instruction: str) -> str:
        # קריאה למודל חיצוני/LLM (נשתמש במוק דוגמא)
        return f"# Refactored according to: {instruction}\n{code}"

    def show_diff(self, old_code: str, new_code: str):
        diff = difflib.unified_diff(
            old_code.splitlines(), new_code.splitlines(), lineterm=""
        )
        print('\n'.join(diff))

# שימוש לדוגמה (לבדיקה ראשונית בלבד):
if __name__ == "__main__":
    agent = AgentCore(repo_path=".")
    files = agent.list_py_files()
    print("Python files:", files)
    if files:
        new_code = agent.refactor_file(files[0], "convert all functions to async and add logging")
        with open(files[0], encoding="utf-8") as f:
            old_code = f.read()
        agent.show_diff(old_code, new_code)
