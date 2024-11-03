# The EnvironmentManager class keeps a mapping between each variable (aka symbol)
# in a brewin program and the value of that variable - the value that's passed in can be
# anything you like. In our implementation we pass in a Value object which holds a type
# and a value (e.g., Int, 10).


#update EnvironmentManager to work with scoping:
'''
new update: changing how to manage scope
Old way:
- Used a recursive structure where each function call created a new instance of EnvironmentManager class and used an 'enclosing' attribute to keep track/point to previous instance
- Therefore, new instances would be able to walk up the enclosing chain to refer to previously/outer defined variables (inner->outer)
- Problems: not distinguishing/hard to distinguish between function call blocks versus if/for blocks (if and for you can traverse to outer scopes but not for function calls)
            Also did not make sure that main is the outermost/top-level scope!

Learned in discussion that it would be better to implement scope with a stack of dictionaries and make sure to distinguish scoping between function call blocks and if/for blocks

Updated way:
- Use stack
    function_stack: isolates scope of a function by saving the current block_stack before each new function call --> allows recursion to work
    block_stack: tracking inner scopes within a function (tackles if/for scope blocks) --> do so by popping/appending dictionaries to the stack
- Basically adding a new scope (dictionary) for new function calls
'''

class EnvironmentManager:
    def __init__(self, enclosing=None):
        self.function_stack = [] #tracking isolated function call scopes
        self.block_stack = [{}] #tracking nested block scopes (like if/for statements) within function

    
    def push_function_scope(self):
        self.function_stack.append(list(self.block_stack)) #save copy of block stack for isolation
        self.block_stack.append({}) #add new scope for  a new function call! 

    def pop_function_scope(self):
        #restore preivious function's block stack --> from the function stack
        if self.function_stack:
            self.block_stack = self.function_stack.pop()
        else:
            self.block_stack = [{}] #or if the function stack is empty, reset to single global scope 


    # Gets the data associated a variable name
    # Update variable lookup: walk the enclosing chain innermost->outer until var found
    def get(self, symbol):
        if symbol in self.environment:
            return self.environment[symbol]
        elif self.enclosing: #if has an enclosing environment, check them inner->outer recursively until found
            return self.enclosing.get(symbol)
        else:
            return None

    # Sets the data associated with a variable name
    # Update variable assignment: if variable ins't in this environment, walk enclosing chain inner->outer until var found and then assign
    def set(self, symbol, value):
        if symbol in self.environment:
            self.environment[symbol] = value
            return True
        elif self.enclosing:
            return self.enclosing.set(symbol, value) #recursively call set method until var found in enclosing
        else:
            return False

    #not changed-- new var is always declared in the current innermost scope
    def create(self, symbol, start_val):
        if symbol not in self.environment: 
          self.environment[symbol] = start_val 
          return True
        return False
    
        



'''
class EnvironmentManager:
    def __init__(self):
        self.environment = {}

    # Gets the data associated a variable name
    def get(self, symbol):
        if symbol in self.environment:
            return self.environment[symbol]
        return None

    # Sets the data associated with a variable name
    def set(self, symbol, value):
        if symbol not in self.environment:
            return False
        self.environment[symbol] = value
        return True

    def create(self, symbol, start_val):
        if symbol not in self.environment: 
          self.environment[symbol] = start_val 
          return True
        return False
'''