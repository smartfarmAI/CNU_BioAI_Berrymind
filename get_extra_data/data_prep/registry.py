# data_prep/registry.py
REGISTRY = {}
def register(name):
    def deco(fn): REGISTRY[name] = fn; return fn
    return deco
