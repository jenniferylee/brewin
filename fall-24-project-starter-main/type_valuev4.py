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
    
    '''def evaluate(self, evaluator):
        # evaluates the lazy value if not alr evaluated
        # evaluator is a function that takes the ast_node and environment and evaluates it

        # Return the cached value if already evaluated
        # Return the cached value if already evaluated
        if self.is_evaluated:
            print(f"DEBUG: Using cached value: {self.cached_value}")
            return self.cached_value

        if self.is_lazy:
            print(f"DEBUG: Evaluating lazy value: {self.ast_node} in captured environment")
            try:
                # Evaluate using the evaluator
                result = evaluator(self.ast_node, self.env_snapshot)
                if not isinstance(result, Value):
                    raise Exception(f"Unexpected evaluation result type: {type(result)}")

                self.cached_value = result  # cache the evaluated result
                self.is_evaluated = True
                self.t = result.type()  # Update type to reflect the evaluated value
                self.v = result.value()  # Update value to reflect the evaluated result

                # Replace the lazy variable in the captured environment
                var_name = self.ast_node.get("name")
                if var_name:
                    for scope in reversed(self.env_snapshot[-1]):  # Look for the variable in the captured environment
                        if var_name in scope:
                            scope[var_name] = result
                            break
            except Exception as e:
                # cache exception as a string-wrapped Value
                self.cached_value = Value(Type.STRING, str(e))
                self.is_evaluated = True  # mark as evaluated

        return self.cached_value'''
    def evaluate(self, evaluator):
        if self.is_evaluated:
            return self.cached_value

        if self.is_lazy:
            try:
                result = evaluator(self.ast_node, self.env_snapshot)
                if not isinstance(result, Value):
                    raise Exception("Evaluation did not return a Value object.")
                self.cached_value = result
                self.is_evaluated = True

                # Update the type and value directly for caching
                self.t = result.type()
                self.v = result.value()
            except Exception as e:
                self.cached_value = Value(Type.STRING, str(e))
                self.is_evaluated = True
                raise

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
    '''if val.type() == Type.NIL:
        return "nil"
    raise ValueError("Unsupported value type")  # explicit error handling'''