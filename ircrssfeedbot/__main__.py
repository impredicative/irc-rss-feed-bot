"""Package entrypoint."""
import multiprocessing

if __name__ == "__main__":
    multiprocessing.set_start_method("spawn")
    from .main import main

    main()
