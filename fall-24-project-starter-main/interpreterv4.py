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

        try:
            # Call main and handle top-level exceptions
            status, return_val = self.__call_func_aux("main", [])
            
            if status == ExecStatus.EXCEPTION:
                print(f"DEBUG: Exception status returned, value = {return_val}, type = {type(return_val)}")
                # Unwrap Value object if needed
                if isinstance(return_val, Value) and return_val.type() == Type.STRING:
                    return_val = return_val.value()
                if not isinstance(return_val, str):
                    print(f"DEBUG: Converting return_val to string: {return_val}")
                    return_val = str(return_val)
                error_message = f"ErrorType.{return_val.strip()}"
                print(f"DEBUG: Outputting exception: {error_message}")
                super().output(error_message)  # Explicitly print the error message
                raise Exception(error_message)

        except Exception as e:
            if "ErrorType" in str(e):  # This ensures only `ErrorType` exceptions are caught
                # Extract only the error type for consistency with expected output
                simplified_error = str(e).split(":")[0].strip()
                super().output(simplified_error.strip())
            else:
                raise

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

                # Ensure `return_val` is a Value object
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

        # first evaluate all of the actual parameters and associate them with the formal parameter names
        args = {}
        for formal_ast, actual_ast in zip(formal_args, actual_args):
            result = copy.copy(self.__eval_expr(actual_ast))
            arg_name = formal_ast.get("name")
            args[arg_name] = result

        # then create the new activation record 
        self.env.push_func()
        # and add the formal arguments to the activation record
        for arg_name, value in args.items():
          self.env.create(arg_name, value)
        
        try:
            status, return_val = self.__run_statements(func_ast.get("statements"))

            if status == ExecStatus.EXCEPTION:
                print(f"DEBUG: Exception '{return_val}' propagated from function '{func_name}'")
                if not isinstance(return_val, Value):
                    return_val = Value(Type.STRING, str(return_val))  # wrap in Value
                self.env.pop_func()
                return (ExecStatus.EXCEPTION, return_val)

            # wrap normal return values
            if not isinstance(return_val, Value):
                return_val = Value(Type.INT, return_val)  # adjust Type.INT as needed???
            
            self.env.pop_func()
            return (ExecStatus.CONTINUE, return_val)

        except Exception as e:
            self.env.pop_func()
            if "ErrorType" in str(e):
                raise  # this is fatal error
            return (ExecStatus.EXCEPTION, Value(Type.STRING, str(e)))  # wrap unexpected exceptions

    def __call_print(self, args):
        output = ""
        for arg in args:
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
        return (ExecStatus.CONTINUE, Interpreter.NIL_VALUE)

    def __call_input(self, name, args):
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
            return (ExecStatus.CONTINUE, Value(Type.STRING, inp))

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
                print("bello")
                return Value(Type.STRING, expr_ast.get("val"))
            if expr_ast.elem_type == InterpreterBase.BOOL_NODE:
                return Value(Type.BOOL, expr_ast.get("val"))
            if expr_ast.elem_type == InterpreterBase.VAR_NODE:
                var_name = expr_ast.get("name")
                val = self.env.get(var_name)
                if val is None:
                    # super().error(ErrorType.NAME_ERROR, f"Variable {var_name} not found")
                    raise Exception("Variable not found") # raise exception here
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

            # short circuiting time!!
            
            # Check for exceptions in the left operand and propagate
            if isinstance(left_value_obj, tuple) and left_value_obj[0] == ExecStatus.EXCEPTION:
                return left_value_obj  # Propagate exception

            # Evaluate lazy operand
            if isinstance(left_value_obj, Value) and left_value_obj.is_lazy:
                left_value_obj = left_value_obj.evaluate(self.evaluate_expression)
            
            # short circuit for logical or (||)
            if arith_ast.elem_type == "||":
                if left_value_obj.type() != Type.BOOL:
                    super().error(ErrorType.TYPE_ERROR, "left op of || is not a bool")
                if left_value_obj.value():
                    return Value(Type.BOOL, True) # short circuiting to true since left is true
                right_value_obj = self.__eval_expr(arith_ast.get("op2"))
                if isinstance(right_value_obj, tuple) and right_value_obj[0] == ExecStatus.EXCEPTION:
                    return right_value_obj  # Propagate exception
                if isinstance(right_value_obj, Value) and right_value_obj.is_lazy:
                    right_value_obj = right_value_obj.evaluate(self.evaluate_expression)
                return right_value_obj
            
            # short circuit for logical and (&&)
            if arith_ast.elem_type == "&&":
                if left_value_obj.type() != Type.BOOL:
                    super().error(ErrorType.TYPE_ERROR, "left op of && is not a bool")
                if not left_value_obj.value():
                    return Value(Type.BOOL, False) # short circuiting to false since left is alr false
                right_value_obj = self.__eval_expr(arith_ast.get("op2"))
                if isinstance(right_value_obj, tuple) and right_value_obj[0] == ExecStatus.EXCEPTION:
                    return right_value_obj  # Propagate exception
                if isinstance(right_value_obj, Value) and right_value_obj.is_lazy:
                    right_value_obj = right_value_obj.evaluate(self.evaluate_expression)
                return right_value_obj


            # og for other bin ops (besides OR and AND above for short circuiting)
            right_value_obj = self.__eval_expr(arith_ast.get("op2"))
            # Check for exceptions in the right operand and propagate
            if isinstance(right_value_obj, tuple) and right_value_obj[0] == ExecStatus.EXCEPTION:
                return right_value_obj  # Propagate exception

            # Evaluate lazy operands
            if isinstance(right_value_obj, Value) and right_value_obj.is_lazy:
                right_value_obj = right_value_obj.evaluate(self.evaluate_expression)

            # check div by 0
            if arith_ast.elem_type == "/" and right_value_obj.value() == 0:
                raise Exception("Division by zero") # raise exception explicitly for divby0
            
            # reject string comparisons with unsupported operators
            if left_value_obj.type() == Type.STRING or right_value_obj.type() == Type.STRING:
                if arith_ast.elem_type not in ["==", "!="]:
                    print(f"DEBUG: Raising error elem type is {arith_ast.elem_type}")
                    super().error(
                        ErrorType.TYPE_ERROR,
                        f"Incompatible operator {arith_ast.elem_type} for type string",
                    )


            # checking for type compatibility
            if not self.__compatible_types(
                arith_ast.elem_type, left_value_obj, right_value_obj
            ):
                print(f"DEBUG: Raising TYPE_ERROR for operation {arith_ast.elem_type} with incompatible types")
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Incompatible types for {arith_ast.elem_type} operation",
                )
            if arith_ast.elem_type not in self.op_to_lambda[left_value_obj.type()]:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Incompatible operator {arith_ast.elem_type} for type {left_value_obj.type()}",
                )
            f = self.op_to_lambda[left_value_obj.type()][arith_ast.elem_type]
            return f(left_value_obj, right_value_obj)
        
        except ValueError as e:
            print(f"DEBUG: Raising TYPE_ERROR: {e}")
            raise Exception(f"ErrorType.TYPE_ERROR: {e}")

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

        self.__run_statement(init_ast)  # initialize counter variable

        # store update as a lazy action
        update_var = update_ast.get("name")
        update_expr = update_ast.get("expression")

        while True:
            # evaluate loop condition
            print("DEBUG: Evaluating loop condition")
            run_for = self.__eval_expr(cond_ast)

            # eval lazy condition
            if isinstance(run_for, Value) and run_for.is_lazy:
                run_for = run_for.evaluate(self.evaluate_expression)

            if run_for.type() != Type.BOOL:
                super().error(ErrorType.TYPE_ERROR, "Condition must evaluate to bool")

            # if condition is false, have to breka out of the loop
            if not run_for.value():
                break

            # Step 4: Execute loop body
            status, return_val = self.__run_statements(for_ast.get("statements"))
            if status in [ExecStatus.RETURN, ExecStatus.EXCEPTION]:
                return (status, return_val)

            # defer evaluation of the update!! 
            # create a lazy Value for the update expression
            lazy_update = Value(None, None)
            lazy_update.set_lazy(update_expr, self.env.snapshot())
            self.env.set(update_var, lazy_update)  # store the lazy Value

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
        print(f"debug exception type is {exception_type_ast}")
        if exception_type_ast is None:
            super().error(ErrorType.NAME_ERROR, "Raise statement missing exception type!")

        # eval excpetion type
        error_value = self.__eval_expr(exception_type_ast)
        print(f"errof value {error_value}")

        # lazy value handling
        if isinstance(error_value, Value) and error_value.is_lazy:
            error_value = error_value.evaluate(self.evaluate_expression)

        if error_value.type() != Type.STRING:
            print("DEBUG: TYPE_ERROR in raise statement - value is not a string")
            super().error(ErrorType.TYPE_ERROR, "Raised value not string!")
        
        # propagate execption --> just like how we did return
        #return (ExecStatus.EXCEPTION, error_value.value())
        # Wrap exception in a Value object
        #return (ExecStatus.EXCEPTION, Value(Type.STRING, error_value.value()))
        return (ExecStatus.EXCEPTION, error_value)  # No need to wrap again
    
    # function for try statement
    # try node is a statement node with elem_type 'try' and two keys in dictionary: 'statements' and 'catchers'
    def __do_try(self, try_ast):
        # execute try block
        try_statements = try_ast.get("statements")
        print("DEBUG: Entering try block")
        status, return_val = self.__run_statements(try_statements)

        # if no excpetion, return normally
        if status != ExecStatus.EXCEPTION:
            return (status, return_val)
        
        
        #exception_type = return_val  # string exception value

        # if exception occurs, handle it
        print(f"DEBUG: Exception '{return_val}' caught in try block")

        # unwrap the exception if it's a Value object
        if isinstance(return_val, Value) and return_val.type() == Type.STRING:
            exception_type = return_val.value()
        else:
            exception_type = str(return_val)  # Fallback to raw exception value
        
        # if exception, look for matching catcher
        for catch_node in try_ast.get("catchers"):
            if catch_node.get("exception_type") == exception_type:
                print(f"DEBUG: Exception '{exception_type}' matched with catch block")
                # execute statements in the catch block
                catch_statements = catch_node.get("statements")
                self.env.push_block()
                status, return_val = self.__run_statements(catch_statements)
                self.env.pop_block()
                
                return (status, return_val)

        # if no matching catch block found, propagate exception
        # but if top level, raise FAULT_ERROR (check one function level scope but also second part ensures within function level scope only one block level scope)
        if len(self.env.environment) == 1 and len(self.env.environment[0]) == 1:
            print("hi??")
            super().error(ErrorType.FAULT_ERROR, f"Unhandled exception: {exception_type}")

        # if no matching catcher, propagate exception
        #return (ExecStatus.EXCEPTION, exception_type)
        return (ExecStatus.EXCEPTION, Value(Type.STRING, exception_type))
    

def main():
    program_source = """
func foo() {
  raise "foo_cond_error";
}

func main() {
  try {
     if (foo()) {
       print("This will not execute");
     }
  }
  catch "foo_cond_error" {
    print("Caught foo_cond_error");
  }
}


    """
    interpreter = Interpreter()
    interpreter.run(program_source)

if __name__ == "__main__":
    main()

