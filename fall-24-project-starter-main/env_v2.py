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
- main() is the outermost/top level/"global" scope 
'''

class EnvironmentManager:
    def __init__(self, enclosing=None):
        self.function_stack = [] #tracking isolated function call scopes
        self.block_stack = [{}] #tracking nested block scopes (like if/for statements) within function
        self.top_scope = {} #for main function

    
    def push_function_scope(self):
        self.function_stack.append(list(self.block_stack)) #save copy of block stack for isolation
        self.block_stack.append({}) #add new scope for  a new function call! 
        #save the current block stack as a separate, isolated scope
        #self.function_stack.append(self.block_stack.copy())  # Ensures isolation
        #initialize a new isolated block stack for the new function call
        #self.block_stack = [{}]


    def pop_function_scope(self):
        #restore preivious function's block stack --> from the function stack
        if self.function_stack:
            self.block_stack = self.function_stack.pop()
        else:
            self.block_stack = [{}] #or if the function stack is empty, reset to single global scope 

    def push_block_scope(self):
        self.block_stack.append({}) #add new dict to current block stack (to isolate block scope)
    
    def pop_block_scope(self):
        #remove most recent block dict from stack
        if len(self.block_stack) > 1: #add this to pass test case where u ensure top level scope
            self.block_stack.pop()


    def get(self, symbol):
        #check block and function scopes first *make sure going reversed so checking most recent
        for scope in reversed(self.block_stack):
            if symbol in scope:
                return scope[symbol]
        #if not found, check the top level scope "global"
        if symbol in self.top_scope:
            return self.top_scope[symbol]
        return None


    def set(self, symbol, value):
        #modify innermost scope where symbol is found
        for scope in reversed(self.block_stack):
            if symbol in scope:
                scope[symbol] = value
                return True
        #also in set: if not found in local scope, check top level, outermost scope
        if symbol in self.top_scope:
            self.top_scope[symbol] = value
            return True
        return False


    def create(self, symbol, value):
        #check that variable is not already 
        if symbol in self.block_stack[-1]:
            return False
        #then you can add it to scope
        self.block_stack[-1][symbol] = value
        return True


    def create_top(self, symbol, value):
        #creating variable in the otuermost scope
        self.top_scope[symbol] = value
    
        