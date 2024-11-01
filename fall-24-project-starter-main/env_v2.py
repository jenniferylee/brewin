# The EnvironmentManager class keeps a mapping between each variable (aka symbol)
# in a brewin program and the value of that variable - the value that's passed in can be
# anything you like. In our implementation we pass in a Value object which holds a type
# and a value (e.g., Int, 10).


#update EnvironmentManager to work with scoping:

class EnvironmentManager:
    def __init__(self, enclosing=None):
        self.environment = {}
        #give each environment reference to its enclosing one --> if no enclosing environment, it is None aka global scope
        self.enclosing = enclosing


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