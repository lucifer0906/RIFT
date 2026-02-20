from pyteal import *

try:
    print("App.box_put returns:", App.box_put(Bytes("key"), Bytes("val")).type_of())
except Exception as e:
    print("App.box_put type_of error:", e)

try:
    print("App.box_delete returns:", App.box_delete(Bytes("key")).type_of())
except Exception as e:
    print("App.box_delete type_of error:", e)

try:
    print("App.box_length returns:", App.box_length(Bytes("key")).type_of())
except Exception as e:
    print("App.box_length type_of error:", e)
