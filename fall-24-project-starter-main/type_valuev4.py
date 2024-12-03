# from carey's v2 solution

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

        # new additions to support lazy evalution 
        self.is_lazy = False # flag to determine whether this value is lazy
        self.ast_node = None # deferred AST node for lazy eval
        self.env_snapshot = None # "snapshot" captured environment at creation
        self.is_evaluated = False # flag for whether value has been evaluated
        self.cached_value = None # cached result after eval

    def value(self):
        return self.v

    def type(self):
        return self.t
    
    # new functions of Value class to support lazy evaluation
    def set_lazy(self, ast_node, env_snapshot):
        self.is_lazy = True
        self.ast_node = ast_node
        self.env_snapshot = env_snapshot
    
    def evaluate(self, evaluator):
        # evaluates the lazy value if not alr evaluated
        # evaluator is a function that takes the ast_node and environment and evaluates it
        '''if not self.is_lazy:
            return self  # Return self if not lazy or alr eval
        if not self.is_evaluated:
            # Use the evaluator with the captured environment snapshot
            self.cached_value = evaluator(self.ast_node, self.env_snapshot)
            self.is_evaluated = True
        return self.cached_value'''
        # evaluate only if lazy and not already evaluated
        if self.is_lazy and not self.is_evaluated:
            print(f"DEBUG: Evaluating lazy value: {self.ast_node} in captured environment")
            try:
                result = evaluator(self.ast_node, self.env_snapshot)

                # ensure the evaluator always returns a Value
                if not isinstance(result, Value):
                    raise Exception(f"Evaluation returned unexpected type: {type(result)}")
                
                self.cached_value = result
                self.is_evaluated = True
            except Exception as e:
                self.cached_value = Value(Type.STRING, str(e))  # cache exception as a Value
                self.is_evaluated = True
        return self.cached_value
    
    '''def evaluate(self, evaluator):
        print(f"DEBUG: Evaluating lazy value: {self.ast_node} in captured environment")
        if not self.is_lazy:
            return self
        if not self.is_evaluated:
            try:
                result = evaluator(self.ast_node, self.env_snapshot)
                self.cached_value = result
            except Exception as e:
                self.cached_value = Value(Type.STRING, str(e))  # Wrap exception as a string
            self.is_evaluated = True
        return self.cached_value'''




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
    '''if val.type() == Type.NIL:
        return "nil"
    raise ValueError("Unsupported value type")  # explicit error handling'''