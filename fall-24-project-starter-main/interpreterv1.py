'''
High level features:
- One function: main
*If not, ErrorType.NAME_ERROR

- Statements
    - New variable definition
    *ErrorType.NAME_ERROR if variable being defined has already been defined
        - give variable initial type/value when adding to main function's environment
    - Assignment
    *ErrorType.NAME_ERROR if variable being assigned has NOT been DEFINED in the "var" statement
        - Use Python dict to evaluate righthand expression/value/variable and assoiate with the variable name on the left
    - Function Calls
        - print()
            must accept 0+ arguments, then evaluate and concatenate to string, then output using super().output()
            if program tries to print out a not yet initialized variable yet, just print any value of any type
        - inputi()
            it's valid to have inputi in print's args
        - automatic call to main
        *ErrorType.NAME_ERROR if calling any other function not above

- Expressions
    - Arithmetic 
        Same as Python, C++
        - only support addition and subtraction + and - 
        - only operate on integers
        *ErrorType.TYPE_ERROR if expression attempts to operate on a string
    - Function call
        Only valid function call is a call to the inputi() function
        inputi() function may take one or no parameters (which is of type string)
        *ErrorType.NAME_ERROR if inputi() has more than one parameter passed to it
        - If there is a prompt parameter, must first output using super().output() before obtaining input
        - To get input, call super().get_input()
        *ErrorType.NAME_ERROR if expression refers to a variable that has not yet been defined
    To evaluate expressions, use post-order tree traversal


- Constants
    Integers/strings enclosed in double quotes

- Variables
    - Must always be defined with a "var" statement before assignment/usage
    *ErrorType.NAME_ERROR if not
    - not of fixed type
    

'''


from intbase import ErrorType, InterpreterBase
from brewparse import parse_program

class Interpreter (InterpreterBase):
    def __init__ (self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)

    
    #run() method will be called with a string that represents Brewin program
    def run(self, program):
        
        #uses the parser to parse the program source code, and then process the nodes of the AST to run the program
        ast = parse_program(program)

        #interpreter creates any data structures it needs to track things like variables...?
        self.variables = {} #map to keep track of variables and their value
        
        #then we can traverse the list

        #top level/root node is program node, first/only element in its dict points to the single function node -- main
        main_function_node = ast.get('functions')[0]
        #error catching if program doesn't have main function defined, must generate an error of type ErrorType.NAME_ERROR
        if main_function_node is None:
            super().error(ErrorType.NAME_ERROR, "No main() function was found",)

        
        #each function node has a field that holds the functions name and another field that holds a list of statement nodes representing statements that must be run when this function is called
        #statement nodes(category, relevant fields - name, expression), variable nodes(name), value nodes(int or string value), expression nodes(binary operator; two fields for two operands)

        statements = main_function_node.get('statements')
        self.run_statements(statements) #list of statements

    
    #elem_type tells you what kind of node it is 
    #three kinds of statements: variable definitions, assignment (inputi), func call (print)
    def run_statements(self, statements):
        for statement in statements:
            #if variable definition
            if statement.elem_type == 'vardef':
                self.variable_definition(statement)     

            #if assignment
            elif statement.elem_type == '=':
                self.do_assignment(statement)

            #if function call
            elif statement.elem_type == 'fcall':
                self.function_call(statement)
            else:
                #error??????
            

    
    def variable_definition(self, statement):
        #define variable
        #each variable has a field that specifies the name of the variable
        #there is one key, name, that maps to a string holding the name of the variable to be defined
        var_name = statement.get('name')
        #error if variable being defined has already been defined
        if var_name in self.variables:
            super().error(ErrorType.NAME_ERROR, "Variable already defined",)

        #add variable to main function's environment and give initial type/value
        self.variables[var_name] = None #initial type doesn't matter -- just assign None

        
    
    
    def do_assignment(self, statement):
        var_name = statement.get('name')
        if var_name not in self.variables:
            super().error(ErrorType.NAME_ERROR, "Can't assign a non-defined variable to an expression",)
        
        expression_node = statement.get('expression')

        thing_to_be_assigned = solve_expression(expression_node)

        self.variables[var_name] = thing_to_be_assigned
        


    def solve_expression(self, node):
        node_type = node.elem_type
         
        #expression- binary operation
        if node_type == '+' or node_type == '-':
            op1 = self.solve_expression(node.get('op1'))
            op2 = self.solve_expression(node.get('op2'))


            #syntax for checking both operands are integers from chatgpt
            if not isinstance(op1, int) or not isinstance(op2, int):
                super().error(ErrorType.TYPE_ERROR, "Operators must be integers")

            if node_type == '+':
                return op1 + op2
            else:
                return op1 - op2            
            
        #variable
        elif node_type == 'var':
            return node.get('name')

        #value
        elif node_type == 'int' or node_type == 'string':
            return node.get('val')
        
        #expression - function call (the only valid function call in expressions is inputi, not print)
        elif node_type == 'fcall':
            function_name = node.get('name')
            if function_name == 'inputi':
                return self.do_inputi(node)
            else:
                super().error(ErrorType.NAME_ERROR, "only inputi is valid function call!")
        
        else:
            super().error(ErrorType.TYPE_ERROR, "not one of the valid expressions")
        

    
    def function_call(self, statement):
        #get name of function: ex. 'inputi'
        function_name = statement.get('name')

        if function_name == 'inputi':
            return self.do_inputi(statement)
        elif function_name == 'print':
            return self.do_print(statement) #?
        else:
            #error
            super().error(ErrorType.NAME_ERROR) #check this????



    def do_inputi(self, node):
        #inputi
        arguments = node.get('args') #list containing 0+ expressoin, var, or value nodes that represent arguments

        #either 0 or 1 parameter

        #if 1 parameter, it is of type string. need to output prompt
        if len(arguments) == 1:
            super().output(self.solve_expression(arguments[0])) #have to evaluate/solve prompt first
            #maybe have to edit to do error checking that the prompt is a string (not relevant for v1??)

        #if more than one parameter, must generate error name error
        elif len(arguments) > 1:
            super().error(ErrorType.NAME_ERROR, f"No inputi() function found that takes >1 parameter",)

        #to get user input:
        user_input = super().get_input() #any error handling here??
        return int(user_input)



        

    



    