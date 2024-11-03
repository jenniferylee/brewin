'''
New additions to interpreterv1:
1. Support for 1+ function definitions (in addition to main())
2. Boolean variables (in addition to string/integer)
3. New value, "nil"
4. New expression types:
    - All binary arithmetic (including *, /, unary negation)
    - Integer, boolean, string comparison
    - Boolean AND/OR/NOT
    - String concatenation
5. New statements: if, if/else, for loops
6. inputs() function
7. Scoping

'''

from type_valuev2 import Type, Value, create_value, get_printable
from intbase import ErrorType, InterpreterBase
from brewparse import parse_program
from env_v2 import EnvironmentManager

class ReturnException(Exception):
    def __init__(self, value=None):
        self.value = value

class Interpreter (InterpreterBase):

    #constants
    BIN_OPS = {'+', '-', '*', '/', '&&', '||', '==', '!=', '>', '>=', '<', '<='}
    #separate operators 
    INT_ARITHMETIC_OPS = {'+', '-', '*', '/'}
    BOOL_LOGICAL_OPS = {'&&', '||'}
    COMP_OPS = {'==', '!=', '>', '>=', '<', '<='}

    def __init__ (self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)
        self.setup_ops() #initialize operations

    #run() method
    def run(self, program):
        #use parser to parse the program source code, processing nodes of AST to run program
        ast = parse_program(program)

        #process function nodes: since there's not just main() as the function, incorporate Carey's function table idea
        self.setup_function_table(ast)
        main_function_node = self.get_function_by_name("main", 0)

        #keep track of variables and their values --> incorporate EnvironmentManager class from Carey's solution
        self.env = EnvironmentManager() #initialization

        #run main function statements and handle early termination
        try:
            self.run_statements(main_function_node.get("statements")) #need to update to handle multifunction
        except ReturnException:
            pass #terminate program immediately when return in main


    #Carey's function table function
    def setup_function_table(self, ast):
        self.function_name_to_ast = {}
        #maps the function name to the function
        for function_def in ast.get("functions"):
            #self.function_name_to_ast[function_def.get("name")] = function_def
            
            #have to support overloading of functions with same name but diff parameter counts
            #Citation: Following code generated by ChatGPT:
            func_name = function_def.get('name')
            param_count = len(function_def.get('args'))
            composite_key = f"{func_name}_{param_count}" 
            self.function_name_to_ast[composite_key] = {
                "args": function_def.get('args'), #parameters
                "statements": function_def.get('statements'),
            }
            #End of copied code


    #Carey's function name function
    def get_function_by_name(self, name, param_count):
        '''
        if name not in self.function_name_to_ast:
            super().error(ErrorType.NAME_ERROR, f"Function {name} not found")
        return self.function_name_to_ast[name]
        '''
        composite_key = f"{name}_{param_count}"
        if composite_key not in self.function_name_to_ast:
            super().error(ErrorType.NAME_ERROR, f"Function {name} with {param_count} arguments was not found")
        return self.function_name_to_ast[composite_key]
    

    #going through and running the statements of a single function
    def run_statements(self, statements):
        for statement in statements:
            #if variable definition
            if statement.elem_type == InterpreterBase.VAR_DEF_NODE:
                self.variable_definition(statement)     

            #if assignment
            elif statement.elem_type == '=':
                self.do_assignment(statement)

            #if function call
            elif statement.elem_type == InterpreterBase.FCALL_NODE:
                self.function_call(statement)
            #new for v2! if statement
            elif statement.elem_type == 'if':
                self.do_ifstatement(statement)
            #new for v2! for loop
            elif statement.elem_type == 'for':
                self.do_forloop(statement)
            #new for v2! return statement
            elif statement.elem_type == InterpreterBase.RETURN_NODE:
                self.do_return(statement)
            else:
                #not valid statement
                super().error(ErrorType.NAME_ERROR, "Not a valid statement",)
            

    
    def variable_definition(self, statement):
        var_name = statement.get('name')
        if not self.env.create(var_name, Value(Type.INT, 0)):
            super().error(
                ErrorType.NAME_ERROR, f"Duplicate definition for variable {var_name}"
            )
    
    
    def do_assignment(self, statement):
        var_name = statement.get('name')
        expression_node = statement.get('expression')
        value_obj = self.solve_expression(expression_node) #returns a Value object
        # Error check: that variable is defined; *incorporate env*
        if not self.env.set(var_name, value_obj):
            super().error(ErrorType.NAME_ERROR, f"Undefined variable {var_name} in assignment")
        


    def solve_expression(self, node):
        node_type = node.elem_type
        #print(f"Solving expression: {node}") 

        #expression- binary operation
        if node_type in Interpreter.BIN_OPS:
            return self.eval_operation(node)
        
        #expression- unary operation 
        elif node_type == 'neg' or node_type == '!':
            op = self.solve_expression(node.get('op1'))
            if node_type == 'neg':
                if op.type() != Type.INT:
                    super().error(ErrorType.TYPE_ERROR, "Unary negation requires integer")
                else:
                    return Value(Type.INT, -op.value()) #negate the op value for new value
            else:
                if op.type() != Type.BOOL:
                    super().error(ErrorType.TYPE_ERROR, "Bool negation requires bool")
                else:
                    return Value(Type.BOOL, not op.value()) #negate the op value for new value (not for bool)
    
        #variable
        elif node_type == 'var':
            var_name = node.get('name')
            val = self.env.get(var_name)
            if val is None:
                super().error(ErrorType.NAME_ERROR, f"Variable {var_name} not defined",)
            return val #returns Value object

        #value
        elif node.elem_type == InterpreterBase.INT_NODE:
            return Value(Type.INT, node.get('val'))
        elif node.elem_type == InterpreterBase.STRING_NODE:
            return Value(Type.STRING, node.get('val'))
        elif node.elem_type == InterpreterBase.BOOL_NODE:
            return Value(Type.BOOL, node.get('val'))
        elif node.elem_type == InterpreterBase.NIL_NODE:
            return Value(Type.NIL, node.get('val'))
        
        #expression - function call (v2: no more restrictions on function calls from expression nodes)
        #Update: simplifying the function call handling by: removing redundant checks for inputi, print, and inputs, which should already be handled in function_call
        #and ensuring function_call is invoked with is_expression=True to handle calls within expressions, allowing it to treat return values correctly in those contexts
        elif node_type == InterpreterBase.FCALL_NODE:
            function_name = node.get('name')
            args = node.get('args') if 'args' in dir(node) else []
            
            # Call the function and mark as expression
            return self.function_call(node, is_expression=True)
        
        # If we reach here, the expression node is invalid
        else:
            super().error(ErrorType.TYPE_ERROR, "Not a valid expression")
        
    
    def eval_operation(self, node):
        left_value_obj = self.solve_expression(node.get("op1")) #updated from Carey's solution!! 
        right_value_obj = self.solve_expression(node.get("op2"))

        #BUT can compare diff types for == and !=
        if node.elem_type in {'==', '!='}:
            if left_value_obj.type() == right_value_obj.type():
                #perform operation bc types are compatible
                f = self.op_to_lambda[left_value_obj.type()][node.elem_type]
                return f(left_value_obj, right_value_obj)
            else:
                return Value(Type.BOOL, node.elem_type == '!=')


        if left_value_obj.type() != right_value_obj.type():
            super().error(ErrorType.TYPE_ERROR, "Incompatible types for arithmetic operation",)

        #boolean operations && and || must use strict evaluation- both arguments must be evaluated in all cases
        if node.elem_type in self.BOOL_LOGICAL_OPS:
             # Confirm both operands are of BOOL type
             #citation: generated by chatgpt
            if left_value_obj.type() != Type.BOOL or right_value_obj.type() != Type.BOOL:
                super().error(ErrorType.TYPE_ERROR, "Logical operations require boolean operands")
            # Perform the operation with strict evaluation
            f = self.op_to_lambda[Type.BOOL][node.elem_type]
            return f(left_value_obj, right_value_obj)
        
        #verify that the operation is valid for the type
        if left_value_obj.type() in self.op_to_lambda and node.elem_type in self.op_to_lambda[left_value_obj.type()]:
        #end of copied code
            f = self.op_to_lambda[left_value_obj.type()][node.elem_type]
            return f(left_value_obj, right_value_obj)
        else:
            super().error(ErrorType.TYPE_ERROR, f"Operation '{node.elem_type}' not supported for type '{left_value_obj.type()}'")



    
    def function_call(self, statement, is_expression=False):
        #get name of function: three functions in v2: inputi and print, inputs
        function_name = statement.get('name')
        args = statement.get('args')
        param_count = len(args)
        
        # Check if it's a built-in function
        if function_name in ['inputi', 'print', 'inputs']:
            if function_name == 'inputi':
                return self.do_inputi(statement)
            elif function_name == 'print':
                return self.do_print(statement)
            elif function_name == 'inputs':
                return self.do_inputs(statement)

        #check if a function exists and if the arugment count matches
        function_info = self.get_function_by_name(function_name, param_count)
        params = function_info['args']

        self.env.push_function_scope() #push new function (works! checked)

        #Citation: following code generated by ChatGPT
        #passing by value: bind each param to the evaluated argument value
        for param, arg in zip(params,args):
            value = self.solve_expression(arg) #eval the argument
            self.env.create(param.get('name'),value) #store param in the function's environment
        #end of copied code
        self.env.push_block_scope() #push an additional block scope for the function body to allowy shadowing
         
        try:
            self.run_statements(function_info["statements"])
        except ReturnException as e:
            return e.value #if return encountered, return its value
        finally:
            self.env.pop_block_scope()  #remove function body block scope
            self.env.pop_function_scope()  #remove function scope after function execution

        if is_expression:
            return Value(Type.NIL) #if no return statement, return nil value by default #if no return statement, return nil value by default
        #end of copied code

        '''
        if function_name == 'inputi':
            return self.do_inputi(statement)
        elif function_name == 'print':
            return self.do_print(statement) 
        elif function_name == 'inputs':
            return self.do_inputi(statement)
        else:
            #error p16 of spec
            super().error(ErrorType.NAME_ERROR, "Not one of the valid functions: print() or inputi()",) 
        '''


    def do_inputi(self, node):
        arguments = node.get('args') #list containing 0+ expressoin, var, or value nodes that represent arguments
        
        #either 0 or 1 parameter
        #if 1 parameter, it is of type string. need to output prompt
        if len(arguments) == 1:
            prompt_value = self.solve_expression(arguments[0])
            super().output(get_printable(prompt_value))  #ensures we print the actual string content --> have to call get_printable because we need to convert to printable string from value object 

        #if more than one parameter, must generate error name error
        elif len(arguments) > 1:
            super().error(ErrorType.NAME_ERROR, f"No inputi() function found that takes >1 parameter",)

        #to get user input:
        user_input = super().get_input() #any error handling here??
        return Value(Type.INT, int(user_input))


    #print function accepts 0+ arguments, which it will evaluate to get a resulting value, then concatenate without spaces into a string
    # it will then output the string with the output() method in the InterpreterBase base class
    def do_print(self, node):
        #the node (statement node)
        #there can be multiple arguments that you have to print
        arguments = node.get('args') #list of the arguments
        result = []
        for argument in arguments:
            solved_result = self.solve_expression(argument)
             # Citation: the following code was generated from ChatGPT (converting Value objects to their underlying types: int, bool, string before printing)
            if solved_result.type() == Type.INT:
                result.append(str(solved_result.value()))  # Use value() to get the raw value
            elif solved_result.type() == Type.BOOL:
                result.append(str(solved_result.value()).lower())  # Force lowercase for boolean
            elif solved_result.type() == Type.STRING:
                result.append(solved_result.value())  # Directly use the string value
            elif solved_result.type() == Type.NIL:
                result.append("nil")
            else:
                super().error(ErrorType.TYPE_ERROR, "Unsupported type for print")
            # End of copied code
        result_string = ''.join(result)

        super().output(result_string)

        return Value(Type.NIL) #test case where do_print needs to return a Value object of Type.NIL instead of Python None

    
    #inputs function- inputs and returns a string as its return value
    def do_inputs(self, node):
        arguments = node.get('args') #list containing 0+ expressoin, var, or value nodes that represent arguments
        
        #either 0 or 1 parameter
        #if 1 parameter, it is of type string. need to output prompt
        if len(arguments) == 1:
            super().output(self.solve_expression(arguments[0])) #have to evaluate/solve prompt first

        #if more than one parameter, must generate error name error??? (this is the case for inputi, check if it is for inputs)
        elif len(arguments) > 1:
            super().error(ErrorType.NAME_ERROR, f"No inputi() function found that takes >1 parameter",)

        #to get user input:
        user_input = str(super().get_input()) #must use InterpreterBase.get_input() function (just like in inputi)
        return Value(Type.STRING, user_input) #check if i can do this, or if i need to return a Value(Type.STRING or something?)


    def do_ifstatement(self, node):
        #dictionary has three keys: condition -> expr/val/var (eval to bool), statements -> list of statements, else_statements -> list of statements or None
        condition = node.get('condition')
        condition_result = self.solve_expression(condition)

        #check that the condition evaluates to bool, if not error
        if condition_result.type() != Type.BOOL:
            super().error(ErrorType.TYPE_ERROR, "Condition needs to evaluate to bool")

        #incorporate scope for if statements (can have nested) --> new cope for each if block, else block
        
        #incorporate scope for if statements (can have nested) --> new cope for each if block, else block
        self.env.push_block_scope()
        try:
            if condition_result.value():
                self.run_statements(node.get('statements'))
            else:
                if node.get('else_statements') is not None:
                    self.run_statements(node.get('else_statements'))
        finally:
            self.env.pop_block_scope()
            

    def do_forloop(self, node):
        #four keys: init, condition, update, statements
        #requirement: if the expr/val/var that is the condition of the statement does not evaluate to a boolean, you must generate an error

        #first, do the assignment for the intialization
        init = node.get('init')
        if init.elem_type == InterpreterBase.VAR_DEF_NODE:
            self.variable_definition(init)
        else:
            self.do_assignment(init)
        '''  
        #eval condition
        condition = node.get('condition')
        condition_result = self.solve_expression(condition)
        
        #check that the condition evaluates to bool, if not error
        if condition_result.type() != Type.BOOL:
            super().error(ErrorType.TYPE_ERROR, "Condition needs to evaluate to bool")
        '''
        #while the condition is true, execute statements-- also update the looping variable that we initialized
        while True:

            #make sure to re-evalualte hte ocndition each iteration to run the statements
            condition = node.get('condition')
            condition_result = self.solve_expression(condition)

            #check that the condition evaluates to bool, if not error
            if condition_result.type() != Type.BOOL:
                super().error(ErrorType.TYPE_ERROR, "Condition needs to evaluate to bool")


            if not condition_result.value():
                break #break out of loop if condition evals to False


            #setup new scope for inside for loop
            self.env.push_block_scope()
            #exit inner block scope after running statements to restore scope
            try:
                self.run_statements(node.get('statements'))
            finally:
                self.env.pop_block_scope()

            #do the update! after running statements
            #update maps to an assignment statement
            self.do_assignment(node.get('update'))



    def do_return(self, node):
        #there may be an expr/val/var to evaluate and return or may be None (one key)
        if node.get('expression'):
            return_value = self.solve_expression(node.get('expression'))
        else:
            return_value = Value(Type.NIL)

        #return termination/exception
        raise ReturnException(return_value)

    #carey's setup_ops function: each operation represented by a lambda function that returns new Value object 
    def setup_ops(self):
        self.op_to_lambda = {}
        # set up operations on integers
        self.op_to_lambda[Type.INT] = {} #key for int

        self.op_to_lambda[Type.INT]['+'] = lambda x, y: Value(
            x.type(), x.value() + y.value()
        )
        self.op_to_lambda[Type.INT]['-'] = lambda x, y: Value(
            x.type(), x.value() - y.value()
        )
        self.op_to_lambda[Type.INT]['*'] = lambda x, y: Value(
            x.type(), x.value() * y.value()
        )
        self.op_to_lambda[Type.INT]['/'] = lambda x, y: Value(
            x.type(), x.value() // y.value()
        )

        #add integer comparsion operations
        self.op_to_lambda[Type.INT]['=='] = lambda x, y: Value(
            Type.BOOL, x.value() == y.value()
        )
        self.op_to_lambda[Type.INT]['>'] = lambda x, y: Value(
            Type.BOOL, x.value() > y.value()
        )
        self.op_to_lambda[Type.INT]['<'] = lambda x, y: Value(
            Type.BOOL, x.value() < y.value()
        )
        self.op_to_lambda[Type.INT]['>='] = lambda x, y: Value(
            Type.BOOL, x.value() >= y.value()
        )
        self.op_to_lambda[Type.INT]['<='] = lambda x, y: Value(
            Type.BOOL, x.value() <= y.value()
        )
        self.op_to_lambda[Type.INT]['!='] = lambda x, y: Value(
            Type.BOOL, x.value() != y.value()
        )


        #boolean operations
        self.op_to_lambda[Type.BOOL] = {} #key for bool

        self.op_to_lambda[Type.BOOL]['&&'] = lambda x, y: Value(
            Type.BOOL, x.value() and y.value()
        )
        self.op_to_lambda[Type.BOOL]['||'] = lambda x, y: Value(
            Type.BOOL, x.value() or y.value()
        )

        #add bool comparsion operations
        self.op_to_lambda[Type.BOOL]['=='] = lambda x, y: Value(
            Type.BOOL, x.value() == y.value()
        )
        self.op_to_lambda[Type.BOOL]['!='] = lambda x, y: Value(
            Type.BOOL, x.value() != y.value()
        )
        

        #string operations
        self.op_to_lambda[Type.STRING] = {} #key for string

        self.op_to_lambda[Type.STRING]['=='] = lambda x, y: Value(
            Type.BOOL, x.value() == y.value()
        )
        self.op_to_lambda[Type.STRING]['!='] = lambda x, y: Value(
            Type.BOOL, x.value() != y.value()
        )
        #string concatenation
        self.op_to_lambda[Type.STRING]['+'] = lambda x, y: Value(
            Type.STRING, x.value() + y.value()
        )

        #nil perations
        self.op_to_lambda[Type.NIL] = {} #key for nil
        self.op_to_lambda[Type.NIL]['=='] = lambda x, y: Value(
            Type.BOOL, x.type() == Type.NIL and y.type() == Type.NIL
        )
        self.op_to_lambda[Type.NIL]['!='] = lambda x, y: Value(
            Type.BOOL, not (x.type() == Type.NIL and y.type() == Type.NIL)
        )







def main():
    program_source = """
    func main() {
        var foobar; 
        foobar = true;
        var foofoo; 
        foofoo = true;
        print(foobar && foofoo);
        
    }
    """
    program_source1 = """
    func main() {
    var b; 
    b = inputi("Hello");
    print(b);
    }


    """
    interpreter = Interpreter()
    interpreter.run(program_source1)

if __name__ == "__main__":
    main()










