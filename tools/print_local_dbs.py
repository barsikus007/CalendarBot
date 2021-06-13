import pickle
from pprint import pprint


with open('../auds.pickle', 'rb') as f:
    pprint(pickle.load(f))
