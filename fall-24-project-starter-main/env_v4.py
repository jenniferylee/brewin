# from carey's v2 solution

# The EnvironmentManager class keeps a mapping between each variable name (aka symbol)
# in a brewin program and the Value object, which stores a type, and a value.
class EnvironmentManager:
    def __init__(self):
        self.environment = []

    # returns a VariableDef object
    def get(self, symbol, evaluator=None):
        cur_func_env = self.environment[-1]
        for env in reversed(cur_func_env):
            if symbol in env:
                value = env[symbol]
                if value.is_lazy and evaluator is not None:
                    # Evaluate lazy value and update the environment
                    evaluated_value = value.evaluate(evaluator)
                    env[symbol] = evaluated_value  # Cache the evaluated value
                    return evaluated_value
                return value
        return None

    def set(self, symbol, value):
        cur_func_env = self.environment[-1]
        for env in reversed(cur_func_env):
            if symbol in env:
                #print(f"DEBUG: Updated variable '{symbol}' with value: {value}")
                env[symbol] = value
                # print(f"DEBUG: Stored {symbol} as {value} (Lazy: {value.is_lazy})")  # Debugging
                return True
        #print(f"DEBUG: {symbol} not found for setting!")
        return False

    # create a new symbol in the top-most environment, regardless of whether that symbol exists
    # in a lower environment
    def create(self, symbol, value):
        cur_func_env = self.environment[-1]
        if symbol in cur_func_env[-1]:   # symbol already defined in current scope
            return False
        cur_func_env[-1][symbol] = value
        return True

    # used when we enter a new function - start with empty dictionary to hold parameters.
    def push_func(self):
        self.environment.append([{}])  # [[...]] -> [[...], [{}]]

    def push_block(self):
        cur_func_env = self.environment[-1]
        cur_func_env.append({})  # [[...],[{....}] -> [[...],[{...}, {}]]

    def pop_block(self):
        cur_func_env = self.environment[-1]
        cur_func_env.pop() 

    # used when we exit a nested block to discard the environment for that block
    def pop_func(self):
        self.environment.pop()

    # support for lazy eval: snapshot function to capture deep copy of current environment
    # Citation: code from chatgpt
    def snapshot(self):
        #return [[env.copy() for env in func_env] for func_env in self.environment]
        from copy import deepcopy
        return deepcopy(self.environment)
    # End of copied code

    # checks whether we are in global scope
    def is_global_scope(self):
        is_global = len(self.environment) == 1
        return is_global
