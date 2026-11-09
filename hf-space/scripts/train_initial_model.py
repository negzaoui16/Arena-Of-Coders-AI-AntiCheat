"""
Script pour créer le modèle initial (v1) à partir d'exemples de code humain / IA.
À exécuter une fois pour avoir un modèle de base (sinon l'API retourne score_ia = 0).
"""
import sys
from pathlib import Path

# Ajouter la racine du projet au path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.features import extract_all_features, features_to_vector
from src.model_ia import train_model, save_model
from sklearn.ensemble import RandomForestClassifier
import numpy as np


# Exemples minimalistes : code "humain" vs "IA-like" (pour démo / PFE)
SAMPLES_HUMAN = [
    '''
def fib(n):
    if n < 2:
        return n
    return fib(n-1) + fib(n-2)
''',
    '''
x = 1
y = 2
# swap
t = x
x = y
y = t
''',
    '''
for i in range(10):
    print(i*i)
''',
    '''
def f():
    a=1
    b=2
    return a+b
''',
    '''
# TODO fix this
if x:
    do_something()
''',
]

SAMPLES_IA = [
    '''
def fibonacci(n: int) -> int:
    """
    Calculate the nth Fibonacci number using dynamic programming.
    """
    if n <= 0:
        return 0
    if n == 1:
        return 1
    dp = [0] * (n + 1)
    dp[1] = 1
    for i in range(2, n + 1):
        dp[i] = dp[i - 1] + dp[i - 2]
    return dp[n]
''',
    '''
def swap_variables(x: int, y: int) -> tuple[int, int]:
    """
    Swap two variables and return the new values.
    """
    x, y = y, x
    return (x, y)
''',
    '''
def print_squares(limit: int) -> None:
    """
    Print the squares of numbers from 0 to limit-1.
    """
    for i in range(limit):
        print(i ** 2)
''',
    '''
def add_numbers(a: int, b: int) -> int:
    """
    Add two numbers and return the result.
    """
    return a + b
''',
    '''
def process_condition(x: bool) -> None:
    """
    Process the condition and execute the appropriate action.
    """
    if x:
        do_something()
''',
]


def main():
    X = []
    y = []
    for code in SAMPLES_HUMAN:
        features = extract_all_features(code)
        X.append(features)
        y.append(0)
    for code in SAMPLES_IA:
        features = extract_all_features(code)
        X.append(features)
        y.append(1)
    result = train_model(X, y, version="v1")
    print("Modèle initial v1 créé. Accuracy (test):", result["accuracy"])
    return 0


if __name__ == "__main__":
    exit(main())
