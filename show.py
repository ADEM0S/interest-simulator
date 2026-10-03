import matplotlib.pyplot as plt
import pandas as pd
import argparse
import pickle

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--pickle-file", "-pf", default="history.pickle", type=str)
    args = parser.parse_args()

    with open(args.pickle_file, "rb") as pf:
        history = pickle.load(pf)

    df = pd.DataFrame.from_dict(history)
    plt.plot(df["date"], df["balance"])
    plt.show()

if __name__ == "__main__":
    main()
