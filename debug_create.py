from algokit_utils import ApplicationClient
import inspect

try:
    print("ApplicationClient.create signature:")
    print(inspect.signature(ApplicationClient.create))
except Exception as e:
    print("Error:", e)
