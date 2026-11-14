"""Run every download in priority order.  python -m data.download.all"""
from data.download import census, lodes, detroit

if __name__ == "__main__":
    detroit.main()
    census.main()
    lodes.main()
