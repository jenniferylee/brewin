
import copy
from enum import Enum

from brewparse import parse_program
from newenv_v4 import EnvironmentManager
from intbase import InterpreterBase, ErrorType
from newtype_valuev4 import Type, Value, LazyValue, create_value, get_printable


class ExecStatus(Enum):
    CONTINUE = 1
    RETURN = 2


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
        self.__call_func_aux("main", [])

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
            status, return_val = self.__run_statement(statement)
            if status == ExecStatus.RETURN:
                self.env.pop_block()
                return (status, return_val)

        self.env.pop_block()
        return (ExecStatus.CONTINUE, Interpreter.NIL_VALUE)

    def __run_statement(self, statement):
        status = ExecStatus.CONTINUE
        return_val = None
        if statement.elem_type == InterpreterBase.FCALL_NODE:
            self.__call_func(statement)
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

        return (status, return_val)
    
    def __call_func(self, call_node):
        func_name = call_node.get("name")
        actual_args = call_node.get("args")
        return self.__call_func_aux(func_name, actual_args)

    def __call_func_aux(self, func_name, actual_args):
        # eagerly evaluate arguments for print/input, lazy for user-defined functions
        if func_name in {"print", "inputi", "inputs"}:
            evaluated_args = [self.evaluate_expression(arg) for arg in actual_args]
        else:
            evaluated_args = [
                LazyValue(arg, self.env.snapshot(), self.evaluate_expression)
                for arg in actual_args
            ]
        
        if func_name == "print":
            return self.__call_print(evaluated_args)
        if func_name == "inputi" or func_name == "inputs":
            return self.__call_input(func_name, evaluated_args)

        # user defined function logic
        func_ast = self.__get_func_by_name(func_name, len(actual_args))
        formal_args = func_ast.get("args")
        '''if len(actual_args) != len(formal_args):
            super().error(
                ErrorType.NAME_ERROR,
                f"Function {func_ast.get('name')} with {len(actual_args)} args not found",
            )'''

        # first evaluate all of the actual parameters and associate them with the formal parameter names
        args = {}
        for formal_arg, actual_arg in zip(formal_args, evaluated_args):
            args[formal_arg.get("name")] = actual_arg 

        # then create the new activation record ; push new function environemnt
        self.env.push_func()
        # and add the formal arguments to the activation record
        for arg_name, value in args.items():
          self.env.create(arg_name, value)
        _, return_val = self.__run_statements(func_ast.get("statements"))
        self.env.pop_func()
        return return_val

    def __call_print(self, args):
        output = ""
        for arg in args:
            # Evaluate only if it's LazyValue; otherwise, use directly
            if isinstance(arg, LazyValue):
                result = arg.evaluate()
            else:
                result = arg
            output = output + get_printable(result)
        super().output(output)
        return Interpreter.NIL_VALUE

    def __call_input(self, name, args):
        if args is not None and len(args) == 1:
            result = self.evaluate_expression(args[0])
            super().output(get_printable(result))
        elif args is not None and len(args) > 1:
            super().error(
                ErrorType.NAME_ERROR, "No inputi() function that takes > 1 parameter"
            )
        inp = super().get_input()
        if name == "inputi":
            return Value(Type.INT, int(inp))
        if name == "inputs":
            return Value(Type.STRING, inp)

    def __assign(self, assign_ast):
        var_name = assign_ast.get("name")
        expr_ast = assign_ast.get("expression")
    
        # capture environment snapshot and create a LazyValue
        env_snapshot = self.env.snapshot()  # capture the current environment
        lazy_value = LazyValue(expr_ast, env_snapshot, self.evaluate_expression)
        
        # store the LazyValue in the environment
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

    def evaluate_expression(self, ast_node, env_snapshot=None):
        # If the node is already a LazyValue, evaluate it
        if isinstance(ast_node, LazyValue):
            return ast_node.evaluate()
        
        # eager evaluation -- an AST node in a specified environment or the current one
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
                if isinstance(val, LazyValue):
                    val = val.evaluate()
                    self.env.set(var_name, val)  # Cache the evaluated value
                return val
            if ast_node.elem_type == InterpreterBase.FCALL_NODE:
                return self.__call_func(ast_node)
            if ast_node.elem_type in Interpreter.BIN_OPS:
                return self.__eval_op(ast_node)
            if ast_node.elem_type == Interpreter.NEG_NODE:
                return self.__eval_unary(ast_node, Type.INT, lambda x: -1 * x)
            if ast_node.elem_type == Interpreter.NOT_NODE:
                return self.__eval_unary(ast_node, Type.BOOL, lambda x: not x)
            super().error(ErrorType.TYPE_ERROR, "Unexpected AST node type")
        finally:
            if original_env is not None:
                # Restore the original environment
                self.env = original_env


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
                super().error(ErrorType.NAME_ERROR, f"Variable {var_name} not found")
            # Check if the value is a LazyValue and evaluate it if needed
            if isinstance(val, LazyValue):
                evaluated_val = val.evaluate()
                self.env.set(var_name, evaluated_val)  # Cache the evaluated value
                return evaluated_val
            return val
        if expr_ast.elem_type == InterpreterBase.FCALL_NODE:
            return self.__call_func(expr_ast)
        if expr_ast.elem_type in Interpreter.BIN_OPS:
            return self.__eval_op(expr_ast)
        if expr_ast.elem_type == Interpreter.NEG_NODE:
            return self.__eval_unary(expr_ast, Type.INT, lambda x: -1 * x)
        if expr_ast.elem_type == Interpreter.NOT_NODE:
            return self.__eval_unary(expr_ast, Type.BOOL, lambda x: not x)

    def __eval_op(self, arith_ast):
        # step 1:evaluate the left operand
        left_value = self.__eval_expr(arith_ast.get("op1"))
        if isinstance(left_value, LazyValue):
            left_value = left_value.evaluate()

        # step 2: handle logical short-circuiting
        if arith_ast.elem_type == "||" and left_value.type() == Type.BOOL:
            if left_value.value():  # Short-circuit for OR
                return Value(Type.BOOL, True)

        if arith_ast.elem_type == "&&" and left_value.type() == Type.BOOL:
            if not left_value.value():  # Short-circuit for AND
                return Value(Type.BOOL, False)

        # step 3: evaluate the right operand
        right_value = self.__eval_expr(arith_ast.get("op2"))
        if isinstance(right_value, LazyValue):
            right_value = right_value.evaluate()

        # step 4: check type compatibility
        if not self.__compatible_types(arith_ast.elem_type, left_value, right_value):
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible types for {arith_ast.elem_type} operation",
            )

        # step 5: ensure the operation is valid for the type
        if arith_ast.elem_type not in self.op_to_lambda[left_value.type()]:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible operator {arith_ast.elem_type} for type {left_value.type()}",
            )

        # step 6: perform the operation
        operation = self.op_to_lambda[left_value.type()][arith_ast.elem_type]
        return operation(left_value, right_value)


    def __compatible_types(self, oper, obj1, obj2):
        # DOCUMENT: allow comparisons ==/!= of anything against anything
        if oper in ["==", "!="]:
            return True
        return obj1.type() == obj2.type()

    def __eval_unary(self, arith_ast, t, f):
        value_obj = self.__eval_expr(arith_ast.get("op1"))
        # Evaluate the value if it's lazy
        if isinstance(value_obj, LazyValue):
            value_obj = value_obj.evaluate()
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
        if isinstance(result, LazyValue):
            result = result.evaluate()
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

        # step 1: initialize the loop variable
        self.__run_statement(init_ast)

        while True:
            # step 2: evaluate the loop condition
            condition_value = self.__eval_expr(cond_ast)

            # step 3: handle lazy evaluation
            if isinstance(condition_value, LazyValue):
                condition_value = condition_value.evaluate()

            # step 4: ensure the condition evaluates to a boolean
            if condition_value.type() != Type.BOOL:
                super().error(
                    ErrorType.TYPE_ERROR,
                    "Condition must evaluate to a boolean in for loop",
                )

            # step 5: check the condition's value
            if not condition_value.value():  # Exit the loop if condition is False
                break

            # step 6: execute the loop body
            status, return_val = self.__run_statements(for_ast.get("statements"))
            if status == ExecStatus.RETURN:
                return (status, return_val)

            # step 7: update the loop variable
            self.__run_statement(update_ast)

        return (ExecStatus.CONTINUE, Interpreter.NIL_VALUE)


    def __do_return(self, return_ast):
        expr_ast = return_ast.get("expression")
        if expr_ast is None:
            return (ExecStatus.RETURN, Interpreter.NIL_VALUE)
        # Create a LazyValue for the return expression
        lazy_value = LazyValue(expr_ast, self.env.snapshot(), self.evaluate_expression)
        return (ExecStatus.RETURN, lazy_value)


def main():
    program_source = """
func main() {
 var a;
 a = "a" <= "b";
 print("---");
 print(a);
}
    """
    interpreter = Interpreter()
    interpreter.run(program_source)

if __name__ == "__main__":
    main()