from intbase import InterpreterBase


# Enumerated type for our different language data types
class Type:
    INT = "int"
    BOOL = "bool"
    STRING = "string"
    NIL = "nil"


# Represents a value, which has a type and its value
class Value:
    def __init__(self, type, value=None):
        self.t = type
        self.v = value

    def value(self):
        return self.v

    def type(self):
        return self.t
    
class LazyValue:
    def __init__(self, ast_node, env_snapshot, evaluator):
        self.ast_node = ast_node  # AST representation of the expression
        self.env_snapshot = env_snapshot  # environment snapshot
        self.evaluator = evaluator  # function to evaluate expressions
        self.cached_value = None
        self.is_evaluated = False # to check if already evalauted --> for need semantics
 
    def evaluate(self):
        if not self.is_evaluated:
            # evaluate the AST node in the captured environment
            self.cached_value = self.evaluator(self.ast_node, self.env_snapshot)
            self.is_evaluated = True
        return self.cached_value


def create_value(val):
    if val == InterpreterBase.TRUE_DEF:
        return Value(Type.BOOL, True)
    elif val == InterpreterBase.FALSE_DEF:
        return Value(Type.BOOL, False)
    elif val == InterpreterBase.NIL_DEF:
        return Value(Type.NIL, None)
    elif isinstance(val, str):
        return Value(Type.STRING, val)
    elif isinstance(val, int):
        return Value(Type.INT, val)
    else:
        raise ValueError("Unknown value type")


def get_printable(val):
    if val.type() == Type.INT:
        return str(val.value())
    if val.type() == Type.STRING:
        return val.value()
    if val.type() == Type.BOOL:
        if val.value() is True:
            return "true"
        return "false"
    return None