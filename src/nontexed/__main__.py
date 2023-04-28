from . import main
import sys

if __name__ == '__main__':
    assert len(sys.argv) == 3, "usage: nontexed <src> <dst_dir>"
    main(*sys.argv[1:])
