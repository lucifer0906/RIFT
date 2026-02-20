import algokit_utils
import inspect

try:
    print("algokit-utils version:", algokit_utils.__version__)
except:
    pass

try:
    from algokit_utils import ApplicationClient
    print("ApplicationClient signature:")
    print(inspect.signature(ApplicationClient.__init__))
except ImportError:
    print("ApplicationClient not found in algokit_utils")
