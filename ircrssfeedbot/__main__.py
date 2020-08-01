"""Package entrypoint."""
import multiprocessing

if __name__ == "__main__":
    multiprocessing.set_start_method("spawn")  # Prevents freeze-up after 1 to 2 days of running
    from ircrssfeedbot.main import main

    main()
