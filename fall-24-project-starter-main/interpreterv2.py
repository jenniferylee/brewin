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

class Interpreter (InterpreterBase):

    #constants
    BIN_OPS = {"+", "-", "*", "/", "&&", "||", "==", "!="}

    def __init__ (self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)
        self.setup_ops() #initialize operations

    #run() method
    def run(self, program):
        #use parser to parse the program source code, processing nodes of AST to run program
        ast = parse_program(program)

        #process function nodes: since there's not just main() as the function, incorporate Carey's function table idea
        self.setup_function_table(ast)
        main_function_node = self.get_function_by_name("main")

        #keep track of variables and their values --> incorporate EnvironmentManager class from Carey's solution
        self.env = EnvironmentManager() #initialization
        self.run_statements(main_function_node.get("statements")) #need to update to handle multifunction


    #Carey's function table function
    def setup_function_table(self, ast):
        self.function_name_to_ast = {}
        #maps the function name to the function
        for function_def in ast.get("functions"):
            self.function_name_to_ast[function_def.get("name")] = function_def

    #Carey's function name function
    def get_function_by_name(self, name):
        if name not in self.function_name_to_ast:
            super().error(ErrorType.NAME_ERROR, f"Function {name} not found")
        return self.function_name_to_ast[name]
    

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
            else:
                #not valid statement
                super().error(ErrorType.NAME_ERROR, "Not a valid statement",)
            

    
    def variable_definition(self, statement):
        var_name = statement.get('name')
        #error if variable being defined has already been defined *check by using EnvironmentManger initialized as env from Carey's solution*
        if not self.env.create(var_name, Value(Type.INT, 0)):
            super().error(ErrorType.NAME_ERROR, f"Variable {var_name} defined more than once",)
    
    
    def do_assignment(self, statement):
        var_name = statement.get('name')
        expression_node = statement.get('expression')
        value_obj = self.solve_expression(expression_node) #returns a Value object
        # Error check: that variable is defined; *incorporate env*
        if not self.env.set(var_name, value_obj):
            super().error(ErrorType.NAME_ERROR, f"Undefined variable {var_name} in assignment")
        


    def solve_expression(self, node):
        node_type = node.elem_type
         
        #expression- binary operation
        if node_type in Interpreter.BIN_OPS:
            return self.eval_operation(node)
            
        #variable
        elif node_type == 'var':
            var_name = node.get('name')
            val = self.env.get(var_name)
            if val is None:
                super().error(ErrorType.NAME_ERROR, f"Variable {var_name} not defined",)
            return val #returns Value object

        #value
        elif node_type in {'int', 'string', 'bool'}:
            return create_value(node.get('val'))
        
        #expression - function call (the only valid function call in expressions is inputi, not print!)
        elif node_type == InterpreterBase.FCALL_NODE:
            function_name = node.get('name')
            if function_name == 'inputi':
                return self.do_inputi(node)
            else:
                super().error(ErrorType.NAME_ERROR, "only inputi is valid function call!")
        
        else:
            super().error(ErrorType.TYPE_ERROR, "Not one of the valid expressions",)
        

    def eval_operation(self, node):
        left_value_obj = self.solve_expression(node.get("op1")) #updated from Carey's solution
        right_value_obj = self.solve_expression(node.get("op2"))

        if left_value_obj.type() != right_value_obj.type():
            super().error(ErrorType.TYPE_ERROR, "Incompatible types for arithmetic operation",)


        #Arithmetic operations
        f = self.op_to_lambda[left_value_obj.type()][node.elem_type]
        return f(left_value_obj, right_value_obj)
        

   

    
    def function_call(self, statement):
        #get name of function: two functions in v1, inputi and print
        function_name = statement.get('name')

        if function_name == 'inputi':
            return self.do_inputi(statement)
        elif function_name == 'print':
            return self.do_print(statement) 
        else:
            #error p16 of spec
            super().error(ErrorType.NAME_ERROR, "Not one of the valid functions: print() or inputi()",) 



    def do_inputi(self, node):
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


    #print function accepts 0+ arguments, which it will evaluate to get a resulting value, then concatenate without spaces into a string
    # it will then output the string with the output() method in the InterpreterBase base class
    def do_print(self, node):
        #the node (statement node)
        #there can be multiple arguments that you have to print
        arguments = node.get('args') #list of the arguments
        result = []
        for argument in arguments:
            # Citation: the following code was generated from ChatGPT
            solved_result = self.solve_expression(argument)
            result.append(str(solved_result))
        
        result_string = ''.join(result)
        # End of copied code

        super().output(result_string)


    #carey's setup_ops function: each operation represented by a lambda function that returns new Value object 
    def setup_ops(self):
        self.op_to_lambda = {}
        # set up operations on integers
        self.op_to_lambda[Type.INT] = {}
        self.op_to_lambda[Type.INT]["+"] = lambda x, y: Value(
            x.type(), x.value() + y.value()
        )
        self.op_to_lambda[Type.INT]["-"] = lambda x, y: Value(
            x.type(), x.value() - y.value()
        )
        # add other operators here later for int, string, bool, etc
        self.op_to_lambda[Type.INT]["*"] = lambda x, y: Value(
            x.type(), x.value() * y.value()
        )
        self.op_to_lambda[Type.INT]["/"] = lambda x, y: Value(
            x.type(), x.value() // y.value()
        )
        #bool return types
        self.op_to_lambda[Type.INT]["=="] = lambda x, y: Value(
            Type.BOOL, x.value() == y.value()
        )
        self.op_to_lambda[Type.INT][">"] = lambda x, y: Value(
            Type.BOOL, x.value() > y.value()
        )
        self.op_to_lambda[Type.INT]["<"] = lambda x, y: Value(
            Type.BOOL, x.value() < y.value()
        )
        self.op_to_lambda[Type.INT][">="] = lambda x, y: Value(
            Type.BOOL, x.value() >= y.value()
        )
        self.op_to_lambda[Type.INT]["<="] = lambda x, y: Value(
            Type.BOOL, x.value() <= y.value()
        )
        self.op_to_lambda[Type.INT]["!="] = lambda x, y: Value(
            Type.BOOL, x.value() != y.value()
        )


        #boolean operations
        


        #string operations
        self.op_to_lambda[Type.STRING]["<"] = lambda x, y: Value(
            Type.BOOL, x.value() < y.value()
        )













