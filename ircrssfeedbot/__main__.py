"""Package entrypoint."""
import multiprocessing
import os

if __name__ == "__main__":
    if os.getenv("IRCRSSFEEDBOT_TRACEMALLOC"):
        multiprocessing.set_start_method("spawn")
    from ircrssfeedbot.main import main

    main()
