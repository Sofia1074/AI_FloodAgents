import asyncio
from pathlib import Path
import spade
from spade_bdi.bdi import BDIAgent

# Garante o caminho exato para a mesma pasta do script
CURRENT_DIR = Path(__file__).parent.resolve()
ASL_FILE = str(CURRENT_DIR / "test_agent.asl")

async def main():
    # Passa o caminho completo do ficheiro .asl
    agent = BDIAgent("student@localhost", "student_password", ASL_FILE)

    await agent.start(auto_register=True)
    print("BDI agent started.")

    await asyncio.sleep(2)

    print("\nCurrent beliefs:")
    agent.bdi.print_beliefs()

    await agent.stop()

if __name__ == "__main__":
    spade.run(main())