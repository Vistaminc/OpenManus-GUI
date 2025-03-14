import asyncio

from app.agent.manus import Manus
from app.flow.base import FlowType
from app.flow.flow_factory import FlowFactory
from app.logger import logger


async def run_flow():
    agents = {
        "manus": Manus(),
    }

    while True:
        try:
            prompt = input("Enter your prompt (or 'exit' to quit): ")
            if prompt.lower() == "exit":
                logger.info("Goodbye!")
                break

            flow = FlowFactory.create_flow(
                flow_type=FlowType.PLANNING,
                agents=agents,
            )
            if prompt.strip().isspace():
                logger.warning("Skipping empty prompt.")
                continue
            logger.warning("Processing your request...")
            result = await flow.execute(prompt)
            logger.info(result)

        except KeyboardInterrupt:
            logger.warning("Goodbye!")
            break


if __name__ == "__main__":
    asyncio.run(run_flow())
