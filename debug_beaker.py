import inspect
try:
    from beaker.state import GlobalStateValue
    print("GlobalStateValue found in beaker.state")
    print(inspect.signature(GlobalStateValue.__init__))
except ImportError:
    print("GlobalStateValue NOT found in beaker.state")

try:
    from beaker.lib.storage import GlobalStateValue
    print("GlobalStateValue found in beaker.lib.storage")
    print(inspect.signature(GlobalStateValue.__init__))
except ImportError:
    print("GlobalStateValue NOT found in beaker.lib.storage")

try:
    import beaker
    print("beaker contents:", dir(beaker))
except:
    pass
