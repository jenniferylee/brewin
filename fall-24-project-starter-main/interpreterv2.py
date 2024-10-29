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


from intbase import ErrorType, InterpreterBase
from brewparse import parse_program
from env_v2 import EnvironmentManager

class Interpreter (InterpreterBase):
    def __init__ (self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)

    #run() method
    def run(self, program):
        #use parser to parse the program source code, processing nodes of AST to run program
        ast = parse_program(program)

        #keep track of variables and their values --> incorporate EnvironmentManager class from Carey's solution
        self.env = EnvironmentManager()

        #process function nodes: since there's not just main() as the function, incorporate Carey's function table idea
        self.setup_function_table(ast)
        main_function_node = self.get_function_by_name("main")

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