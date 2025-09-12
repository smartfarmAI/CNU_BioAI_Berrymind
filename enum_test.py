from action_compose.action_io_component.ksconstants import STATCODE, CMDCODE

WORKING_CODES = frozenset({
    STATCODE.WORKING, STATCODE.OPENING, STATCODE.CLOSING,
    STATCODE.PREPARING, STATCODE.SUPPLYING, STATCODE.FINISHING
})

def is_working_code(code: STATCODE) -> bool:
    try:
        return code in WORKING_CODES
    except Exception:
        return False
    

print(is_working_code(STATCODE["OPENING"]))
print(is_working_code(STATCODE(201)))
print(is_working_code(STATCODE["SUPPLYING"]))
print(is_working_code(STATCODE(403)))
print(is_working_code(STATCODE["PREPARING"]))
print(is_working_code(STATCODE(401)))