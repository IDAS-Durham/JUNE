import sys

sys.path.append("../covid")
from covid.groups import Group

if __name__ == "__main__":
    import person as Person
    import random
    import matplotlib
    import matplotlib.pyplot as plt

    group = Group.Group("test", "Random", 100)
