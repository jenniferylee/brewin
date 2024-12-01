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
        #self.__call_func_aux("main", [])

        try:
            # Call main and handle top-level exceptions
            status, return_val = self.__call_func_aux("main", [])
            
            if status == ExecStatus.EXCEPTION:
                #super().error(ErrorType.FAULT_ERROR, f"Unhandled exception: {return_val}")
                raise Exception(f"ErrorType.FAULT_ERROR: Unhandled exception: {return_val}")

        except Exception as e:
            if "ErrorType" in str(e):  # This ensures only `ErrorType` exceptions are caught
                print(e)
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
            '''if status in [ExecStatus.RETURN, ExecStatus.EXCEPTION]:
                self.env.pop_block()
                return (status, return_val)'''
            
            if status == ExecStatus.EXCEPTION:
                self.env.pop_block()
                return (status, return_val)  # Propagate the exception

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

            # propagte exception if occurred
            if status == ExecStatus.EXCEPTION:
                self.env.pop_func()
                return (ExecStatus.EXCEPTION, return_val)

            self.env.pop_func()
            return (ExecStatus.CONTINUE, return_val)
        except Exception as e:
            # Check if the exception is a fatal interpreter error
            if isinstance(e, Exception) and "ErrorType" in str(e):
                raise  # Reraise fatal errors to be handled at the top level
            else:
                self.env.pop_func()
                return (ExecStatus.EXCEPTION, str(e))

    def __call_print(self, args):
        output = ""
        for arg in args:
            result = self.__eval_expr(arg)  # result is a Value object

            # Evaluate lazy values
            if result.is_lazy:
                result = result.evaluate(self.evaluate_expression)

            output = output + get_printable(result) # converting to printable form
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
                return self.__call_func(ast_node)
        finally:
            if original_env is not None:
                # Restore the original environment
                self.env = original_env

    # og eval expr function for eager eval in current env context
    def __eval_expr(self, expr_ast):
        if expr_ast.elem_type == InterpreterBase.NIL_NODE:
            return Interpreter.NIL_VALUE
        if expr_ast.elem_type == InterpreterBase.INT_NODE:
            return Value(Type.INT, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.STRING_NODE:
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
                raise Exception(f"Unhandled exception: {return_val}")
            return return_val  # Ensure we return the value here
        if expr_ast.elem_type in Interpreter.BIN_OPS:
            return self.__eval_op(expr_ast)
        if expr_ast.elem_type == Interpreter.NEG_NODE:
            return self.__eval_unary(expr_ast, Type.INT, lambda x: -1 * x)
        if expr_ast.elem_type == Interpreter.NOT_NODE:
            return self.__eval_unary(expr_ast, Type.BOOL, lambda x: not x)

    def __eval_op(self, arith_ast):
        left_value_obj = self.__eval_expr(arith_ast.get("op1"))

        # short circuiting time!!
        
        # eval lazy operands
        if left_value_obj.is_lazy:
            left_value_obj = left_value_obj.evaluate(self.evaluate_expression)
        
        # short circuit for logical or (||)
        if arith_ast.elem_type == "||":
            if left_value_obj.type() != Type.BOOL:
                super().error(ErrorType.TYPE_ERROR, "left op of || is not a bool")
            if left_value_obj.value():
                return Value(Type.BOOL, True) # short circuiting to true since left is true
            right_value_obj = self.__eval_expr(arith_ast.get("op2"))
            if right_value_obj.is_lazy:
                right_value_obj = right_value_obj.evaluate(self.evaluate_expression)
            if right_value_obj.type() != Type.BOOL:
                super().error(ErrorType.TYPE_ERROR, "right op of || not a bool")
            return right_value_obj
        
        # short circuit for logical and (&&)
        if arith_ast.elem_type == "&&":
            if left_value_obj.type() != Type.BOOL:
                super().error(ErrorType.TYPE_ERROR, "left op of && is not a bool")
            if not left_value_obj.value():
                return Value(Type.BOOL, False) # short circuiting to false since left is alr false
            right_value_obj = self.__eval_expr(arith_ast.get("op2"))
            if right_value_obj.is_lazy:
                right_value_obj = right_value_obj.evaluate(self.evaluate_expression)
            if right_value_obj.type() != Type.BOOL:
                super().error(ErrorType.TYPE_ERROR, "right op of && not a bool")
            return right_value_obj


        # og for other bin ops (besides OR and AND above for short circuiting)
        right_value_obj = self.__eval_expr(arith_ast.get("op2"))
        
        # evaluate lazy operands
        if right_value_obj.is_lazy:
            right_value_obj = right_value_obj.evaluate(self.evaluate_expression)

        # check div by 0
        if arith_ast.elem_type == "/" and right_value_obj.value() == 0:
            raise Exception("Division by zero") # raise exception explicitly for divby0

        # checking for type compatibility
        if not self.__compatible_types(
            arith_ast.elem_type, left_value_obj, right_value_obj
        ):
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

    def __compatible_types(self, oper, obj1, obj2):
        # DOCUMENT: allow comparisons ==/!= of anything against anything
        if oper in ["==", "!="]:
            return True
        return obj1.type() == obj2.type()

    def __eval_unary(self, arith_ast, t, f):
        value_obj = self.__eval_expr(arith_ast.get("op1"))
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

        # Evaluate lazy condition - conditionals
        if result.is_lazy:
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
        # run_for = Interpreter.TRUE_VALUE
        while True:
            # eval loop condition
            try: 
                run_for = self.__eval_expr(cond_ast)  # check for-loop condition

                # Evaluate lazy condition - conditionals
                if result.is_lazy:
                    result = result.evaluate(self.evaluate_expression)

                if run_for.type() != Type.BOOL:
                    raise Exception("Condition must eval to bool")
                
                # exit loop if condition false
                if not run_for.value():
                    break

            except Exception as e:
                # propagate excpetions from condition evaluation
                return (ExecStatus.EXCEPTION, str(e))
            
            # now run the loop body
            try:
                status, return_val = self.__run_statements(for_ast.get("statements"))

                #if RETURN or EXCEPTIOn, propagate
                if status in [ExecStatus.RETURN, ExecStatus.EXCEPTION]:
                    return (status, return_val)
                
            finally:
                # execute update satement
                self.__run_statement(update_ast) # update counster variable


           

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
        if exception_type_ast is None:
            super().error(ErrorType.NAME_ERROR, "Raise statement missing exception type!")

        # eval excpetion type
        error_value = self.__eval_expr(exception_type_ast)

        # lazy value handling
        if error_value.is_lazy:
            error_value = error_value.evaluate(self.evaluate_expression)

        if error_value.type() != Type.STRING:
            super().error(ErrorType.TYPE_ERROR, "Raised value not string!")
        
        # propagate execption --> just like how we did return
        return (ExecStatus.EXCEPTION, error_value.value())
    
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
        
        # if exception, look for matching catcher
        exception_type = return_val  # string exception value
        for catch_node in try_ast.get("catchers"):
            if catch_node.get("exception_type") == exception_type:
                # execute statements in the catch block
                catch_statements = catch_node.get("statements")
                self.env.push_block()
                status, return_val = self.__run_statements(catch_statements)
                self.env.pop_block()
                return (status, return_val)

        # if no matching catch block found, propagate exception
        # but if top level, raise FAULT_ERROR (check one function level scope but also second part ensures within function level scope only one block level scope)
        if len(self.env.environment) == 1 and len(self.env.environment[0]) == 1:
            super().error(ErrorType.FAULT_ERROR, f"Unhandled exception: {exception_type}")

        # if no matching catcher, propagate exception
        return (ExecStatus.EXCEPTION, exception_type)
    

def main():
    program_source = """
func main() {
    let x = true;
    let y = print("This should not print");
    let result = x || y;
    print(result);
}
    """
    interpreter = Interpreter()
    interpreter.run(program_source)

if __name__ == "__main__":
    main()

