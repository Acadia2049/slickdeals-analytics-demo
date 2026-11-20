"""Comment report on the selected immutable local release."""
import sys
sys.dont_write_bytecode = True

from report_query import main


if __name__ == "__main__":
    main("comment_velocity")
