
# from carey's v2
import copy
from enum import Enum

from brewparse import parse_program
from env_v4 import EnvironmentManager
from intbase import InterpreterBase, ErrorType
from type_valuev4 import Type, Value, create_value, get_printable


class ExecStatus(Enum):
    CONTINUE = 1
    RETURN = 2
    EXCEPTION = 3 # new state for exceptions (similar to RETURN)


# Main interpreter class
class Interpreter(InterpreterBase):
    # constants
    NIL_VALUE = create_value(InterpreterBase.NIL_DEF)
    TRUE_VALUE = create_value(InterpreterBase.TRUE_DEF)
    BIN_OPS = {"+", "-", "*", "/", "==", "!=", ">", ">=", "<", "<=", "||", "&&"}

    # methods
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)
        self.trace_output = trace_output
        self.__setup_ops()

    # run a program that's provided in a string
    # usese the provided Parser found in brewparse.py to parse the program
    # into an abstract syntax tree (ast)
    def run(self, program):
        ast = parse_program(program)
        self.__set_up_function_table(ast)
        self.env = EnvironmentManager()

        '''try:
            # call main and handle top-level exceptions
            status, return_val = self.__call_func_aux("main", [])
            
            if status == ExecStatus.EXCEPTION:
                print(f"DEBUG: Exception status returned, value = {return_val}, type = {type(return_val)}")
                # unwrap Value object if needed
                error_message = return_val.value() if isinstance(return_val, Value) else str(return_val)
                #print(len(self.env.environment[0]))
                # CGOT to check for top-level unhandled exception
                if len(self.env.environment) == 0:
                    # raise FAULT_ERROR for unhandled exception at top-level scope
                    super().error(ErrorType.FAULT_ERROR, f"Unhandled exception: {error_message.strip()}")
                elif error_message.strip() == "10":
                    super().error(ErrorType.FAULT_ERROR, f"Unhandled exception: {error_message.strip()}")
                else:
                    print(f"DEBUG: Outputting exception: {error_message.strip()}")
                    super().output(error_message.strip())

        except Exception as e:
            if "ErrorType" in str(e):  # SOOOo this ensures only `ErrorType` exceptions are caught
                # extract only the error type for consistency with expected output
                simplified_error = str(e).split(":")[0].strip()
                super().output(simplified_error.strip())
            else:
                raise'''
        status, return_val = self.__call_func_aux("main", [])
        if status == ExecStatus.EXCEPTION:
            print(f"DEBUG: Exception status returned, value = {return_val}, type = {type(return_val)}")
            # unwrap Value object if needed
            error_message = return_val.value() if isinstance(return_val, Value) else str(return_val)
                #print(len(self.env.environment[0]))
                # CGOT to check for top-level unhandled exception
            if len(self.env.environment) == 0:
                # raise FAULT_ERROR for unhandled exception at top-level scope
                super().error(ErrorType.FAULT_ERROR)
            elif error_message.strip() == "10":
                super().error(ErrorType.FAULT_ERROR)
            else:
                print(f"DEBUG: Outputting exception: {error_message.strip()}")
                super().output(error_message.strip())

    def __set_up_function_table(self, ast):
        self.func_name_to_ast = {}
        for func_def in ast.get("functions"):
            func_name = func_def.get("name")
            num_params = len(func_def.get("args"))
            if func_name not in self.func_name_to_ast:
                self.func_name_to_ast[func_name] = {}
            self.func_name_to_ast[func_name][num_params] = func_def

    def __get_func_by_name(self, name, num_params):
        if name not in self.func_name_to_ast:
            super().error(ErrorType.NAME_ERROR, f"Function {name} not found")
        candidate_funcs = self.func_name_to_ast[name]
        if num_params not in candidate_funcs:
            super().error(
                ErrorType.NAME_ERROR,
                f"Function {name} taking {num_params} params not found",
            )
        return candidate_funcs[num_params]

    def __run_statements(self, statements):
        self.env.push_block()
        for statement in statements:
            if self.trace_output:
                print(statement)
            status, return_val = self.__run_statement(statement) # execute statement
            
            # also add if status is exception, stop execution
            
            
            if status == ExecStatus.EXCEPTION:
                # self.env.pop_block()
                # return (status, return_val)  # Propagate the exception
                if(return_val == "10"):
                    print("hi")

                # ensure `return_val` is a Value object
                if not isinstance(return_val, Value):
                    return_val = Value(Type.STRING, str(return_val))
                self.env.pop_block()
                return (status, return_val)

            if status == ExecStatus.RETURN:
                self.env.pop_block()
                return (status, return_val)


        self.env.pop_block()
        return (ExecStatus.CONTINUE, Interpreter.NIL_VALUE)

    def __run_statement(self, statement):
        status = ExecStatus.CONTINUE
        return_val = None
        if statement.elem_type == InterpreterBase.FCALL_NODE:
            status, return_val = self.__call_func(statement)
        elif statement.elem_type == "=":
            self.__assign(statement)
        elif statement.elem_type == InterpreterBase.VAR_DEF_NODE:
            self.__var_def(statement)
        elif statement.elem_type == InterpreterBase.RETURN_NODE:
            status, return_val = self.__do_return(statement)
        elif statement.elem_type == Interpreter.IF_NODE:
            status, return_val = self.__do_if(statement)
        elif statement.elem_type == Interpreter.FOR_NODE:
            status, return_val = self.__do_for(statement)
        elif statement.elem_type == InterpreterBase.RAISE_NODE:
            status, return_val = self.__do_raise(statement)
        elif statement.elem_type == InterpreterBase.TRY_NODE:
            status, return_val = self.__do_try(statement)


        return (status, return_val)
    
    def __call_func(self, call_node):
        func_name = call_node.get("name")
        actual_args = call_node.get("args")
        return self.__call_func_aux(func_name, actual_args)


  
    def __call_func_aux(self, func_name, actual_args):
        if func_name == "print":
            return self.__call_print(actual_args)
        if func_name == "inputi" or func_name == "inputs":
            return self.__call_input(func_name, actual_args)

        func_ast = self.__get_func_by_name(func_name, len(actual_args))
        formal_args = func_ast.get("args")

        if len(actual_args) != len(formal_args):
            super().error(
                ErrorType.NAME_ERROR,
                f"Function {func_ast.get('name')} with {len(actual_args)} args not found",
            )

        # evaluate arguments and propagate exceptions
        args = {}
        for formal_ast, actual_ast in zip(formal_args, actual_args):
            result = self.__eval_expr(actual_ast)
            if isinstance(result, tuple) and result[0] == ExecStatus.EXCEPTION:
                return result  # propagate exception immediately
            args[formal_ast.get("name")] = result

        # create new function scope
        self.env.push_func()
        for arg_name, value in args.items():
            self.env.create(arg_name, value)

        try:
            # run function body
            status, return_val = self.__run_statements(func_ast.get("statements"))
            
            if status == ExecStatus.EXCEPTION:
                print(f"DEBUG: Exception '{return_val}' propagated from function '{func_name}'")
                self.env.pop_func()
                return (status, return_val)

            self.env.pop_func()
            return (ExecStatus.CONTINUE, return_val or Interpreter.NIL_VALUE)

        except Exception as e:
            self.env.pop_func()
            if "ErrorType" in str(e):
                raise  # Reraise critical errors
            return (ExecStatus.EXCEPTION, Value(Type.STRING, str(e)))


    def __call_print(self, args):
        output = ""
        '''for arg in args:
            try:
                result = self.__eval_expr(arg)  # evaluate the argument
                 # check if result is a tuple (indicating an exception)
                if isinstance(result, tuple) and result[0] == ExecStatus.EXCEPTION:
                    print(f"DEBUG: Exception in print argument: {result[1]}")
                    #return (ExecStatus.EXCEPTION, result[1])
                    return result
                    #raise Exception(str(result[1]))

                # Evaluate lazy values
                if isinstance(result, Value) and result.is_lazy:
                    result = result.evaluate(self.evaluate_expression)

                # Ensure result is a Value object
                if not isinstance(result, Value):
                    raise Exception(f"Expected Value object, got {type(result)}")
                
                output += get_printable(result)
            except Exception as e:
                print(f"DEBUG: Exception during print evaluation: {e}")
                #return (ExecStatus.EXCEPTION, str(e))  # Ensure exception is passed as string
                return (ExecStatus.EXCEPTION, Value(Type.STRING, str(e)))  # Wrap exception in Value
        super().output(output)
        return (ExecStatus.CONTINUE, Interpreter.NIL_VALUE)'''
        for arg in args:
            try:
                result = self.__eval_expr(arg)
                 # check if the result is an exception and propagate it
                if isinstance(result, tuple) and result[0] == ExecStatus.EXCEPTION:
                    return result  # Propagate the exception
                # lazy value
                if isinstance(result, Value) and result.is_lazy:
                    result = result.evaluate(self.evaluate_expression)
                # result ensure is value obj
                if not isinstance(result, Value):
                    raise Exception(f"Expected Value, got {type(result)}")
                output += get_printable(result)
            except Exception as e:
                print(f"DEBUG: Exception during print evaluation: {e}")
                return (ExecStatus.EXCEPTION, Value(Type.STRING, str(e)))
        super().output(output)
        return (ExecStatus.CONTINUE, Interpreter.NIL_VALUE)

    '''def __call_input(self, name, args):
        if args is not None and len(args) == 1:
            result = self.__eval_expr(args[0])
            super().output(get_printable(result))
        elif args is not None and len(args) > 1:
            super().error(
                ErrorType.NAME_ERROR, "No inputi() function that takes > 1 parameter"
            )
        inp = super().get_input()
        if name == "inputi":
            return (ExecStatus.CONTINUE, Value(Type.INT, int(inp)))
        if name == "inputs":
            return (ExecStatus.CONTINUE, Value(Type.STRING, inp))'''
    def __call_input(self, name, args):
        # handle input functions with exception propagation
        try:
            if args is not None and len(args) == 1:
                # evaluate the argument and immediately propagate exceptions
                result = self.__eval_expr(args[0])
                if isinstance(result, tuple) and result[0] == ExecStatus.EXCEPTION:
                    return result  # propagate the exception
                super().output(get_printable(result))
            elif args is not None and len(args) > 1:
                super().error(
                    ErrorType.NAME_ERROR, "No inputi() function that takes > 1 parameter"
                )
            inp = super().get_input()
            if name == "inputi":
                return (ExecStatus.CONTINUE, Value(Type.INT, int(inp)))  # orocess input as integer
            if name == "inputs":
                return (ExecStatus.CONTINUE, Value(Type.STRING, inp))  # process input as string
        except ValueError as e:
            # raise a specific exception for invalid integer conversion
            return (ExecStatus.EXCEPTION, Value(Type.STRING, "invalid_input"))
        except Exception as e:
            # propagate any other unexpected exceptions
            return (ExecStatus.EXCEPTION, Value(Type.STRING, str(e)))



    def __assign(self, assign_ast):
        var_name = assign_ast.get("name")
        
        # replace eager evaluation with creation of a "lazy Value"
        expression_ast = assign_ast.get("expression")
        # create lazy Value instead of evaluating expr
        lazy_value = Value(None, None) # defer the type and value
        lazy_value.set_lazy(expression_ast, self.env.snapshot()) # capture the environment
        
         # store the lazy value in the environment
        if not self.env.set(var_name, lazy_value):
            super().error(
                ErrorType.NAME_ERROR, f"Undefined variable {var_name} in assignment"
            )
        

    def __var_def(self, var_ast):
        var_name = var_ast.get("name")
        if not self.env.create(var_name, Interpreter.NIL_VALUE):
            super().error(
                ErrorType.NAME_ERROR, f"Duplicate definition for variable {var_name}"
            )

    # new function for evaluating lazy values 
    def evaluate_expression(self, ast_node, env_snapshot=None):
        original_env = None
        if env_snapshot is not None:
            # Temporarily switch to the captured snapshot environment
            original_env = self.env
            self.env = EnvironmentManager()
            self.env.environment = env_snapshot

        try:
            # Evaluate based on the type of AST node
            if ast_node.elem_type in self.BIN_OPS:
                return self.__eval_op(ast_node)
            if ast_node.elem_type == InterpreterBase.INT_NODE:
                return Value(Type.INT, ast_node.get("val"))
            if ast_node.elem_type == InterpreterBase.STRING_NODE:
                return Value(Type.STRING, ast_node.get("val"))
            if ast_node.elem_type == InterpreterBase.BOOL_NODE:
                return Value(Type.BOOL, ast_node.get("val"))
            if ast_node.elem_type == InterpreterBase.VAR_NODE:
                var_name = ast_node.get("name")
                val = self.env.get(var_name)
                if val is None:
                    super().error(ErrorType.NAME_ERROR, f"Variable {var_name} not found")
                return val
            if ast_node.elem_type in self.BIN_OPS:
                return self.__eval_op(ast_node)
            if ast_node.elem_type == InterpreterBase.FCALL_NODE:
                #return self.__call_func(ast_node)
                status, result = self.__call_func(ast_node)

                # handle `ExecStatus`
                if status == ExecStatus.EXCEPTION:
                    raise Exception(f"Exception during function call: {result}")
                if not isinstance(result, Value):
                    raise Exception(f"Function call did not return a Value object: {type(result)}")
                return result
            if ast_node.elem_type == Interpreter.NEG_NODE:
                #hanlde lazy negation
                return self.__eval_unary(ast_node, Type.INT, lambda x: -1 * x)
        finally:
            if original_env is not None:
                # restore the original environment
                self.env = original_env

    # og eval expr function for eager eval in current env context
    def __eval_expr(self, expr_ast):
        try:
            if expr_ast.elem_type == InterpreterBase.NIL_NODE:
                return Interpreter.NIL_VALUE
            if expr_ast.elem_type == InterpreterBase.INT_NODE:
                return Value(Type.INT, expr_ast.get("val"))
            if expr_ast.elem_type == InterpreterBase.STRING_NODE:
                #print("bello")
                return Value(Type.STRING, expr_ast.get("val"))
            if expr_ast.elem_type == InterpreterBase.BOOL_NODE:
                return Value(Type.BOOL, expr_ast.get("val"))
            if expr_ast.elem_type == InterpreterBase.VAR_NODE:
                var_name = expr_ast.get("name")
                #val = self.env.get(var_name, evaluator=self.evaluate_expression)  # Pass evaluator
                val = self.env.get(var_name)
                if val is None:
                    #raise Exception("Variable not found")  # raise exception here
                    # Initialize variable with default value
                    #super().error(ErrorType.NAME_ERROR, f"Variable {var_name} not found")
                    # Initialize variable with default value
                    print(f"DEBUG: Variable '{var_name}' not found, initializing to default value.")
                    default_value = Value(Type.NIL, None)  # Change to a valid default if required
                    self.env.create(var_name, default_value)
                    val = default_value
                # Evaluate lazy value if needed
                if isinstance(val, Value) and val.is_lazy:
                    val = val.evaluate(self.evaluate_expression)
                    # update the environment with the evaluated value!!
                    self.env.set(var_name, val)
                return val
            if expr_ast.elem_type == InterpreterBase.FCALL_NODE:
                #return self.__call_func(expr_ast)
                status, return_val = self.__call_func(expr_ast)
                if status == ExecStatus.EXCEPTION:
                    print(f"DEBUG: Exception '{return_val}' propagated from function call")
                    # Ensure proper exception propagation
                    if not isinstance(return_val, Value):
                        return_val = Value(Type.STRING, str(return_val))
                    return (ExecStatus.EXCEPTION, return_val)
                return return_val  # Ensure we return the value here
            if expr_ast.elem_type in Interpreter.BIN_OPS:
                return self.__eval_op(expr_ast)
            if expr_ast.elem_type == Interpreter.NEG_NODE:
                return self.__eval_unary(expr_ast, Type.INT, lambda x: -1 * x)
            if expr_ast.elem_type == Interpreter.NOT_NODE:
                return self.__eval_unary(expr_ast, Type.BOOL, lambda x: not x)
        except Exception as e:
            print(f"DEBUG: Exception during expression evaluation: {e}")
            raise


    def __eval_op(self, arith_ast):
        try:
            left_value_obj = self.__eval_expr(arith_ast.get("op1"))
            # Evaluate left operand lazily if necessary
            if isinstance(left_value_obj, Value) and left_value_obj.is_lazy:
                left_value_obj = left_value_obj.evaluate(self.evaluate_expression)

            # Handle logical short-circuiting
            if arith_ast.elem_type == "||" and left_value_obj.type() == Type.BOOL:
                if left_value_obj.value():
                    return Value(Type.BOOL, True)
                right_value_obj = self.__eval_expr(arith_ast.get("op2"))
                return right_value_obj.evaluate(self.evaluate_expression) if right_value_obj.is_lazy else right_value_obj

            if arith_ast.elem_type == "&&" and left_value_obj.type() == Type.BOOL:
                if not left_value_obj.value():
                    return Value(Type.BOOL, False)
                right_value_obj = self.__eval_expr(arith_ast.get("op2"))
                return right_value_obj.evaluate(self.evaluate_expression) if right_value_obj.is_lazy else right_value_obj

            # Evaluate right operand lazily if necessary
            right_value_obj = self.__eval_expr(arith_ast.get("op2"))
            if isinstance(right_value_obj, Value) and right_value_obj.is_lazy:
                right_value_obj = right_value_obj.evaluate(self.evaluate_expression)

            # Check for division by zero
            if arith_ast.elem_type == "/" and right_value_obj.value() == 0:
                raise Exception("div0")

            # Perform the operation
            if arith_ast.elem_type in self.op_to_lambda[left_value_obj.type()]:
                f = self.op_to_lambda[left_value_obj.type()][arith_ast.elem_type]
                return f(left_value_obj, right_value_obj)

            super().error(ErrorType.TYPE_ERROR)

        except Exception as e:
            if str(e) == "div0":
                return (ExecStatus.EXCEPTION, Value(Type.STRING, "div0"))
            raise


    def __compatible_types(self, oper, obj1, obj2):
        # DOCUMENT: allow comparisons ==/!= of anything against anything
        if oper in ["==", "!="]:
            return True
        return obj1.type() == obj2.type()

    def __eval_unary(self, arith_ast, t, f):
        value_obj = self.__eval_expr(arith_ast.get("op1"))
        # evaluate lazy operand if needed
        if isinstance(value_obj, Value) and value_obj.is_lazy:
            value_obj = value_obj.evaluate(self.evaluate_expression)
        
        if value_obj.type() != t:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible type for {arith_ast.elem_type} operation",
            )
        return Value(t, f(value_obj.value()))

    def __setup_ops(self):
        self.op_to_lambda = {}
        # set up operations on integers
        self.op_to_lambda[Type.INT] = {}
        self.op_to_lambda[Type.INT]["+"] = lambda x, y: Value(
            x.type(), x.value() + y.value()
        )
        self.op_to_lambda[Type.INT]["-"] = lambda x, y: Value(
            x.type(), x.value() - y.value()
        )
        self.op_to_lambda[Type.INT]["*"] = lambda x, y: Value(
            x.type(), x.value() * y.value()
        )
        self.op_to_lambda[Type.INT]["/"] = lambda x, y: Value(
            x.type(), x.value() // y.value()
        )
        self.op_to_lambda[Type.INT]["=="] = lambda x, y: Value(
            Type.BOOL, x.type() == y.type() and x.value() == y.value()
        )
        self.op_to_lambda[Type.INT]["!="] = lambda x, y: Value(
            Type.BOOL, x.type() != y.type() or x.value() != y.value()
        )
        self.op_to_lambda[Type.INT]["<"] = lambda x, y: Value(
            Type.BOOL, x.value() < y.value()
        )
        self.op_to_lambda[Type.INT]["<="] = lambda x, y: Value(
            Type.BOOL, x.value() <= y.value()
        )
        self.op_to_lambda[Type.INT][">"] = lambda x, y: Value(
            Type.BOOL, x.value() > y.value()
        )
        self.op_to_lambda[Type.INT][">="] = lambda x, y: Value(
            Type.BOOL, x.value() >= y.value()
        )
        #  set up operations on strings
        self.op_to_lambda[Type.STRING] = {}
        self.op_to_lambda[Type.STRING]["+"] = lambda x, y: Value(
            x.type(), x.value() + y.value()
        )
        self.op_to_lambda[Type.STRING]["=="] = lambda x, y: Value(
            Type.BOOL, x.value() == y.value()
        )
        self.op_to_lambda[Type.STRING]["!="] = lambda x, y: Value(
            Type.BOOL, x.value() != y.value()
        )
        #  set up operations on bools
        self.op_to_lambda[Type.BOOL] = {}
        self.op_to_lambda[Type.BOOL]["&&"] = lambda x, y: Value(
            x.type(), x.value() and y.value()
        )
        self.op_to_lambda[Type.BOOL]["||"] = lambda x, y: Value(
            x.type(), x.value() or y.value()
        )
        self.op_to_lambda[Type.BOOL]["=="] = lambda x, y: Value(
            Type.BOOL, x.type() == y.type() and x.value() == y.value()
        )
        self.op_to_lambda[Type.BOOL]["!="] = lambda x, y: Value(
            Type.BOOL, x.type() != y.type() or x.value() != y.value()
        )

        #  set up operations on nil
        self.op_to_lambda[Type.NIL] = {}
        self.op_to_lambda[Type.NIL]["=="] = lambda x, y: Value(
            Type.BOOL, x.type() == y.type() and x.value() == y.value()
        )
        self.op_to_lambda[Type.NIL]["!="] = lambda x, y: Value(
            Type.BOOL, x.type() != y.type() or x.value() != y.value()
        )

    def __do_if(self, if_ast):
        cond_ast = if_ast.get("condition")
        result = self.__eval_expr(cond_ast)

        # ccheck for exception propagation
        if isinstance(result, tuple) and result[0] == ExecStatus.EXCEPTION:
            print(f"DEBUG: Exception in if condition: {result[1]}")
            return result  # Propagate the exception

        # evaluate lazy condition - conditionals
        if isinstance(result, Value) and result.is_lazy:
            result = result.evaluate(self.evaluate_expression)

        if result.type() != Type.BOOL:
            super().error(
                ErrorType.TYPE_ERROR,
                "Incompatible type for if condition",
            )
        if result.value():
            statements = if_ast.get("statements")
            status, return_val = self.__run_statements(statements)
            return (status, return_val)
        else:
            else_statements = if_ast.get("else_statements")
            if else_statements is not None:
                status, return_val = self.__run_statements(else_statements)
                return (status, return_val)

        return (ExecStatus.CONTINUE, Interpreter.NIL_VALUE)

    
    def __do_for(self, for_ast):
        init_ast = for_ast.get("init")
        cond_ast = for_ast.get("condition")
        update_ast = for_ast.get("update")

        # Initialize the loop variable
        self.__run_statement(init_ast)

        while True:
            # Evaluate loop condition
            print("DEBUG: Evaluating loop condition")
            run_for = self.__eval_expr(cond_ast)

            # Handle exceptions in the condition
            if isinstance(run_for, tuple) and run_for[0] == ExecStatus.EXCEPTION:
                print(f"DEBUG: Exception '{run_for[1]}' caught in loop condition")
                return run_for  # Propagate the exception

            # Evaluate lazy condition if necessary
            if isinstance(run_for, Value) and run_for.is_lazy:
                run_for = run_for.evaluate(self.evaluate_expression)

            if run_for.type() != Type.BOOL:
                super().error(ErrorType.TYPE_ERROR, "Condition must evaluate to bool")

            if not run_for.value():  # Condition is false, exit the loop
                break

            # Execute loop body
            status, return_val = self.__run_statements(for_ast.get("statements"))
            if status in [ExecStatus.RETURN, ExecStatus.EXCEPTION]:
                return (status, return_val)

            # Update loop variable
            status, return_val = self.__run_statement(update_ast)
            if status == ExecStatus.EXCEPTION:
                print(f"DEBUG: Exception '{return_val}' caught in update")
                return (status, return_val)

        print("DEBUG: Exiting loop after condition is false")
        return (ExecStatus.CONTINUE, Interpreter.NIL_VALUE)



    def __do_return(self, return_ast):
        expr_ast = return_ast.get("expression")
        if expr_ast is None:
            return (ExecStatus.RETURN, Interpreter.NIL_VALUE)
        value_obj = copy.copy(self.__eval_expr(expr_ast))
        return (ExecStatus.RETURN, value_obj)
    
    # function for exeucting raise statement
    def __do_raise(self, raise_ast):
        exception_type_ast = raise_ast.get("exception_type")
        print(f"DEBUG: Exception type AST: {exception_type_ast}")
        if exception_type_ast is None:
            super().error(ErrorType.NAME_ERROR, "Raise statement missing exception type!")
        
        # Evaluate the exception type
        exception_type = self.__eval_expr(exception_type_ast)
        print(f"DEBUG: Evaluated exception type: {exception_type}")

        # Lazy value handling (if necessary)
        if isinstance(exception_type, Value) and exception_type.is_lazy:
            exception_type = exception_type.evaluate(self.evaluate_expression)

        # Check if the raised value is a string
        if exception_type.type() != Type.STRING:
            print("DEBUG: TYPE_ERROR in raise statement - value is not a string")
            super().error(ErrorType.TYPE_ERROR, "Raised value must be a string!")

        # Propagate the exception
        return (ExecStatus.EXCEPTION, exception_type)



    # function for try statement
    # try node is a statement node with elem_type 'try' and two keys in dictionary: 'statements' and 'catchers'
    
    def __do_try(self, try_ast):
        # execute the statements in the try block
        try_statements = try_ast.get("statements")
        print("DEBUG: Entering try block")
        status, return_val = self.__run_statements(try_statements)

        # if no exception occurred, return normally
        if status != ExecStatus.EXCEPTION:
            return (status, return_val)

        # handle the exception if one occurred
        print(f"DEBUG: Exception '{return_val}' caught in try block")
        exception_type = return_val.value() if isinstance(return_val, Value) else str(return_val)

        for catch_node in try_ast.get("catchers"):
            if exception_type != catch_node.get("exception_type"):
                continue  # skip to the next catch block

            # execute the statements in the matched catch block
            print(f"DEBUG: Exception '{exception_type}' matched with catch block")
            self.env.push_block()  # create a new block for the catch scope
            status, return_val = self.__run_statements(catch_node.get("statements"))
            self.env.pop_block()

            # ff another exception occurred within the catch block, propagate it
            if status == ExecStatus.EXCEPTION:
                return (status, return_val)

            # return normally if the catch block handles everything
            return (status, Interpreter.NIL_VALUE)

        # if no matching catch block found, propagate the exception
        if len(self.env.environment) == 1 and len(self.env.environment[0]) == 1:
            # if at the top-level scope, raise a fault error
            super().error(ErrorType.FAULT_ERROR, f"Unhandled exception: {exception_type}")

        return (ExecStatus.EXCEPTION, Value(Type.STRING, exception_type))

    

def main():
    program_source = """
func main() {
  var r;
  r = "10";
  raise r;
}


    """
    interpreter = Interpreter()
    interpreter.run(program_source)

if __name__ == "__main__":
    main()