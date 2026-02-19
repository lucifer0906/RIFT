from pyteal import *

def approval_program():
    add = Seq([
        App.box_put(Txn.application_args[1], Txn.application_args[2]),
        Approve()
    ])
    
    verify = Seq([
        App.box_length(Txn.application_args[1]),
        Approve()
    ])

    handle_noop = Cond(
        [Txn.application_args[0] == Bytes("add"), add],
        [Txn.application_args[0] == Bytes("verify"), verify] 
    )

    program = Cond(
        [Txn.application_id() == Int(0), Approve()],
        [Txn.on_completion() == OnComplete.NoOp, handle_noop],
        [Txn.on_completion() == OnComplete.DeleteApplication, Return(Txn.sender() == Global.creator_address())],
        [Txn.on_completion() == OnComplete.UpdateApplication, Return(Txn.sender() == Global.creator_address())],
        [Txn.on_completion() == OnComplete.OptIn, Approve()],
        [Txn.on_completion() == OnComplete.CloseOut, Approve()],
    )

    return compileTeal(program, Mode.Application, version=8)

if __name__ == "__main__":
    print(approval_program())
