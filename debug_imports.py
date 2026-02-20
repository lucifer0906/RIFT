try:
    print("Attempting to import contracts.campus_bank...")
    from contracts.campus_bank import app as bank_beaker_app
    print("Success: contracts.campus_bank")
except Exception as e:
    import traceback
    traceback.print_exc()

try:
    print("Attempting to import contracts.campus_dao...")
    from contracts.campus_dao import app as dao_beaker_app
    print("Success: contracts.campus_dao")
except Exception as e:
    import traceback
    traceback.print_exc()
