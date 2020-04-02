import sys
sys.path.append("../covid")
import group as Group

if __name__=="__main__":
    import person as Person
    import random
    import matplotlib
    import matplotlib.pyplot as plt

    group = Group.Group("test", "Random", 100)
