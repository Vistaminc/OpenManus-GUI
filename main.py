import asyncio

from app.agent.manus import Manus
from app.logger import logger
import sys
import asyncio
from PySide6.QtWidgets import QApplication
from app.ui.main_ui import MainWindow
import qasync


async def main():
    agent = Manus()
    while True:
        try:
            prompt = input("Enter your prompt (or 'exit' to quit): ")
            if prompt.lower() == "exit":
                logger.info("Goodbye!")
                break
            if prompt.strip().isspace():
                logger.warning("Skipping empty prompt.")
                continue
            logger.warning("Processing your request...")
            await agent.run(prompt)
        except KeyboardInterrupt:
            logger.warning("Goodbye!")
            break

if __name__ == "__main__":
    app = QApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    window = MainWindow()
    window.show()
    

    app_window = window
    
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
    # sys.exit(app.exec())