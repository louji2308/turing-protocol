import asyncio
import os
import sys
import argparse
from loguru import logger
from dotenv import load_dotenv

load_dotenv()


def setup_logging():
    logger.remove()
    logger.add(
        sys.stdout,
        format="<g>{time:HH:mm:ss}</g> | <c>{level}</c> | {message}",
        level=os.getenv("LOG_LEVEL", "INFO"),
        colorize=True,
    )
    logger.add(
        "logs/ghost_agent.log",
        rotation="10 MB",
        retention=3,
        level="DEBUG",
    )


async def run_ghost(enable_telemetry: bool = True, dry_run: bool = False):
    from ghost_agent.ghost import GhostAgent

    ghost = GhostAgent()
    logger.info("Ghost Agent initialized")

    if dry_run:
        logger.warning("DRY RUN MODE - No real transactions will be executed")
        original_execute = ghost._execute_transaction

        async def dry_execute(action):
            await asyncio.sleep(0.1)
            return {
                "status": "dry_run",
                "action_type": action.get("type", "unknown"),
                "note": "dry_run - no real transaction"
            }

        ghost._execute_transaction = dry_execute

    if enable_telemetry:
        telemetry_task = asyncio.create_task(
            _run_telemetry_server(ghost)
        )
        logger.info("Telemetry HTTP server started on port 9100")

    try:
        await ghost.run()
    except KeyboardInterrupt:
        logger.info("Shutdown signal received")
    finally:
        ghost.stop()
        if enable_telemetry:
            telemetry_task.cancel()


async def _run_telemetry_server(ghost):
    import json
    from aiohttp import web

    async def handle_status(request):
        return web.json_response(ghost.get_status())

    async def handle_telemetry(request):
        queue = ghost.get_telemetry_queue()
        items = []
        while not queue.empty():
            try:
                items.append(queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        return web.json_response({"telemetry": items[-20:]})

    app = web.Application()
    app.router.add_get("/status", handle_status)
    app.router.add_get("/telemetry", handle_telemetry)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "localhost", 9100)
    await site.start()

    while ghost.is_running:
        await asyncio.sleep(1)

    await runner.cleanup()


def main():
    parser = argparse.ArgumentParser(description="Turing Protocol Ghost Agent")
    parser.add_argument(
        "--no-telemetry", action="store_true",
        help="Disable the telemetry HTTP server"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Simulation mode - no real transactions"
    )
    args = parser.parse_args()

    setup_logging()

    logger.info("=" * 50)
    logger.info("TURING PROTOCOL - GHOST AGENT")
    logger.info("=" * 50)

    asyncio.run(run_ghost(
        enable_telemetry=not args.no_telemetry,
        dry_run=args.dry_run,
    ))


if __name__ == "__main__":
    main()
