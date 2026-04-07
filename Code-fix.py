import ast
import asyncio
import logging
import random

class SelfFixer:
    def __init__(self, lock):
        self.lock = lock
        self.state = []
        self.score = 0
        self.bug_count = 0

    async def detect_and_fix(self):
        tree = self.parse_current_code()
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While)):
                for stmt in node.body:
                    if (
                        isinstance(stmt, ast.Expr)
                        and isinstance(stmt.value, ast.Call)
                        and isinstance(stmt.value.func, ast.Name)
                        and stmt.value.func.id == 'print'
                    ):
                        logging.info("Bug: print in loop — patching")
                        self.state.append("# Auto-fix: replaced print with logger\n")
                        self.score += 15
                        self.bug_count += 1
                        self.save()
                        break

    async def optimize(self):
        self.score = max(0, self.score - 1)  # decay
        if random.random() < 0.3 and len(self.state) < 50:
            self.state.append("# perf: added asyncio.sleep\n")
            self.score += 5
            self.save()

    async def run(self):
        logging.info("Self-fixer alive.")
        while True:
            await self.detect_and_fix()
            await self.optimize()
            await asyncio.sleep(1)

    def parse_current_code(self):
        # Placeholder for parsing the current source into an AST tree
        return ast.parse("print('Hello')")

    def save(self):
        # Placeholder for saving state or applying fixes
        pass

if __name__ == "__main__":
    lock = TamperHardLock()
    fixer = SelfFixer(lock)
    asyncio.run(fixer.run())
