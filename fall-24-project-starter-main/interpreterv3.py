# document that we won't have a return inside the init/update of a for loop

# this is from carey's interpreterv2.py solution!

import copy
from enum import Enum

from brewparse import parse_program
from env_v3 import EnvironmentManager
from intbase import InterpreterBase, ErrorType
from type_valuev3 import Type, Value, create_value, get_printable


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
        self.return_type_stack = [] #stack to keep track of function return types

    # run a program that's provided in a string
    # usese the provided Parser found in brewparse.py to parse the program
    # into an abstract syntax tree (ast)
    def run(self, program):
        ast = parse_program(program)
        #also setup the struct table
        self.__set_up_struct_table(ast)
        self.validate_structs() # also have to validate structs (make sure fields have valid types and reference only valid primitive types or other alr defined structs)
        self.__set_up_function_table(ast)
        self.env = EnvironmentManager()
        self.__call_func_aux("main", [])
    
    def __set_up_struct_table(self, ast):
        self.struct_name_to_def = {} # dictionary stores struct definitions
        for struct_def in ast.get("structs"):
            struct_name = struct_def.get("name")
            if struct_name in self.struct_name_to_def:
                super().error(ErrorType.NAME_ERROR, f"Duplicate struct definition of {struct_name}")
            self.struct_name_to_def[struct_name] = struct_def

    def validate_structs(self):
        for struct_name, struct_def in self.struct_name_to_def.items():
            for field in struct_def.get("fields"):
                field_type = field.get("var_type")
                #now check if field type is a vlaid primitive (int, bool, string) or previously defined struct
                if field_type not in [Type.INT, Type.BOOL, Type.STRING] and field_type not in self.struct_name_to_def:
                    super().error(ErrorType.TYPE_ERROR, f"Not a valid field for struct {field_type}")

    def __set_up_function_table(self, ast):
        self.func_name_to_ast = {}
        for func_def in ast.get("functions"):
            func_name = func_def.get("name")
            num_params = len(func_def.get("args"))

            #validate return type? undefined_ret_type case
            return_type = func_def.get("return_type")
            if return_type is None:
                super().error(ErrorType.TYPE_ERROR, f"Function {func_name} has no defined return type")
            elif return_type not in [Type.INT, Type.STRING, Type.BOOL, Type.NIL, "void"] and return_type not in self.struct_name_to_def:
                super().error(ErrorType.TYPE_ERROR, f"Invalid return type {return_type} for function {func_name}")
           
            #also have to validate parameter types! for the invalid_param_type test case
            for param in func_def.get("args"):
                param_type = param.get("var_type")
                if param_type is None:
                    super().error(ErrorType.TYPE_ERROR, f"Parameter {param.get('name')} in function {func_name} has no defined type")
                #if the type of paramter isnot one of the primitves or not self defined struct
                elif param_type not in [Type.INT, Type.STRING, Type.BOOL] and param_type not in self. struct_name_to_def:
                    super().error(ErrorType.TYPE_ERROR, f"Invalid parameter type {param_type} for function {func_name}")


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


    # seems like this function is for handling function calls
    # 
    def __call_func_aux(self, func_name, actual_args):
        if func_name == "print":
            return self.__call_print(actual_args)
        if func_name == "inputi" or func_name == "inputs":
            return self.__call_input(func_name, actual_args)

        func_ast = self.__get_func_by_name(func_name, len(actual_args))
        formal_args = func_ast.get("args")

        # Validate return type only if specified; it may be None
        return_type = func_ast.get("return_type")
        if return_type is None:
            super().error(ErrorType.TYPE_ERROR, f"Function {func_name} has no defined return type")

        if len(actual_args) != len(formal_args):
            super().error(
                ErrorType.NAME_ERROR,
                f"Function {func_ast.get('name')} with {len(actual_args)} args not found",
            )

        # push function's return type onto the stack
        self.return_type_stack.append(func_ast.get("return_type"))

        # first evaluate all of the actual parameters and associate them with the formal parameter names
        args = {}
        for formal_ast, actual_ast in zip(formal_args, actual_args):
            result = copy.copy(self.__eval_expr(actual_ast))
            expected_type = formal_ast.get("var_type") #wait check this var_type or return_type

            # Allow nil for struct types
            if expected_type in self.struct_name_to_def:
                #if expectec type is struct, allow nil values to be passed
                if result.type() == Type.NIL:
                    pass #allow nil assignment ot structs
                elif result.type() != expected_type:
                    #error, types have to match
                    super().error(ErrorType.TYPE_ERROR, f"Function {func_name} has an expected return type of {expected_type} but seems to be actually {result.type()}")
            
            else: #for non-struct types
                # if expected type is bool, call coercion function to coerce int --> bool
                if expected_type == Type.BOOL and result.type() == Type.INT:
                    result = self.__do_int_to_bool_coercion(result)
                #also have to check for type compatilbity after coercin
                if result.type() != expected_type:
                    super().error(ErrorType.TYPE_ERROR,f"Function {func_name} has an expected return type of {expected_type} but seems to be actually {result.type()}")
            
            arg_name = formal_ast.get("name")
            args[arg_name] = result

        # then create the new activation record 
        self.env.push_func()
        # and add the formal arguments to the activation record
        for arg_name, value in args.items():
          self.env.create(arg_name, value)
        
        #execute function body
        status, return_val = self.__run_statements(func_ast.get("statements")) #instead of _ add variable status bc we need it for checking default return 
        self.env.pop_func()

        # pop the function return type as well
        self.return_type_stack.pop()

        #now, have to check for if we need to return default return value!
        if status != ExecStatus.RETURN:
            func_return_type = func_ast.get("return_type")
            if func_return_type == "void":
                return Value(Type.VOID)
            elif func_return_type == Type.INT:
                return Value(Type.INT, 0) #int default value is 0
            elif func_return_type == Type.STRING:
                return Value(Type.STRING, "") #string default value is ""
            elif func_return_type == Type.BOOL:
                return Value(Type.BOOL, False) #bool default value is False
            elif func_return_type in self.struct_name_to_def:
                return Interpreter.NIL_VALUE #we refer to nil value with NIL_VALUE instead of None? check this

        return return_val
    

    def __call_print(self, args):
        output = ""
        for arg in args:
            result = self.__eval_expr(arg)  # result is a Value object

            if not isinstance(result, Value):
                #print(f"DEBUG: Expected Value object but got {type(result)}")
                super().error(ErrorType.TYPE_ERROR, "Expectd a Value object in the print funciotn")
            # for brewin++ have to check if the value is None or nil type
            if result.type() == Type.NIL or result.value() is None:
                output += "nil"
                # Properly handle known types
            elif result.type() in [Type.INT, Type.BOOL, Type.STRING]:
                output += get_printable(result)
            else:
                output += f"<unknown type>"
            #else:
                #output = output + get_printable(result)
        super().output(output)
        return Interpreter.NIL_VALUE

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
            return Value(Type.INT, int(inp))
        if name == "inputs":
            return Value(Type.STRING, inp)

    #split up assign function for better readability
    def __assign(self, assign_ast):
        var_name = assign_ast.get("name")
        value_obj = self.__eval_expr(assign_ast.get("expression"))

        if '.' in var_name:
            self.__assign_to_struct_field(var_name, value_obj)
        else:
            self.__assign_to_variable(var_name, value_obj)

    #assignment logic for structs
    def __assign_to_struct_field(self, var_name, value_obj):
        parts = var_name.split('.')
        base_var_name = parts[0]
        field_names = parts[1:]

        base_var = self.env.get(base_var_name)
        if base_var is None:
            super().error(ErrorType.NAME_ERROR, f"Variable {base_var_name} is not found")
        if base_var.value() is None:
            super().error(ErrorType.FAULT_ERROR, f"Variable {base_var_name} is nil")
        if base_var.type() not in self.struct_name_to_def:
            super().error(ErrorType.TYPE_ERROR, f"{base_var_name} is not a struct!")


        struct_value = base_var.value()
        for field_name in field_names[:-1]:
            if field_name not in struct_value:
                super().error(ErrorType.NAME_ERROR, f"Field {field_name} not found in struct {base_var.type()}")
            struct_value = struct_value[field_name]
            if struct_value.type() not in self.struct_name_to_def:
                super().error(ErrorType.TYPE_ERROR, f"{field_name} is not a struct")
            if struct_value.value() is None:
                super().error(ErrorType.FAULT_ERROR, f"Field {field_name} is nil")
            struct_value = struct_value.value()

        final_field_name = field_names[-1]
        if final_field_name not in struct_value:
            super().error(ErrorType.NAME_ERROR, f"Field {final_field_name} not found in struct {base_var.type()}")
        field_value = struct_value[final_field_name]

        if field_value.type() == Type.NIL:
            # Allow assignment if the value being assigned is either a nil value or matches the expected struct type
            #if value_obj.type() == Type.NIL or value_obj.type() == base_var.type():
            if value_obj.type() in self.struct_name_to_def or value_obj.type() == Type.NIL:
                struct_value[final_field_name] = value_obj
            else:
                super().error(ErrorType.TYPE_ERROR, f"Cannot assign value of type {value_obj.type()} to field {final_field_name} of type nil")
        else:
            if value_obj.type() == Type.NIL:
                #allow assigning nil to fields of struct type
                struct_value[final_field_name] = value_obj
                return
            if field_value.type() == Type.BOOL and value_obj.type() == Type.INT:
                value_obj = self.__do_int_to_bool_coercion(value_obj)
            if field_value.type() != value_obj.type():
                super().error(ErrorType.TYPE_ERROR, f"Type mismatch: cannot assign {value_obj.type()} to field {final_field_name} of type {field_value.type()}")

        struct_value[final_field_name] = value_obj

    #regular variable assignment 
    def __assign_to_variable(self, var_name, value_obj):
        curr_val = self.env.get(var_name)

        if curr_val.type() == Type.NIL and value_obj.type() in self.struct_name_to_def:
            self.env.set(var_name, value_obj)
            return

        if curr_val.type() == Type.BOOL and value_obj.type() == Type.INT:
            value_obj = self.__do_int_to_bool_coercion(value_obj)

        if value_obj.type() == Type.NIL and curr_val.type() in self.struct_name_to_def:
            self.env.set(var_name, value_obj)
            return

        if curr_val.type() != value_obj.type():
            super().error(ErrorType.TYPE_ERROR, f"Types are not the same! {var_name} is {curr_val.type()} but got {value_obj.type()}")

        if not self.env.set(var_name, value_obj):
            super().error(ErrorType.NAME_ERROR, f"Undefined variable {var_name} in assignment")


    def __var_def(self, var_ast):
        var_name = var_ast.get("name")
        #add variable type!
        var_type = var_ast.get("var_type") # var_type is the second key in vardef statement node's dictionary
        
        #check if variable is a user defined struct
        if var_type in self.struct_name_to_def:
            #then initialize default nil value to the structs
            default_value = Value(Type.NIL, None)
        elif var_type == Type.INT:
            default_value = Value(Type.INT, 0)
        elif var_type == Type.STRING:
            default_value = Value(Type.STRING, "") 
        elif var_type == Type.BOOL:
            default_value = Value(Type.BOOL, False)
        else:
            super().error(ErrorType.TYPE_ERROR, f"Invalid type for variable {var_name}")
        
        #if not self.env.create(var_name, Value(var_type, None)):
        if not self.env.create(var_name, default_value):
            super().error(
                ErrorType.NAME_ERROR, f"Duplicate definition for variable {var_name}"
            )

    def __eval_expr(self, expr_ast):
        # add the handling for the struct isntances --> use 'new' to create new struct instances
        if expr_ast.elem_type == InterpreterBase.NEW_NODE:
            #print(f"DEBUG: Full NEW_NODE expression: {expr_ast}")
            #print(f"DEBUG: Creating new struct of type {expr_ast.get('var_type')}")

            struct_type = expr_ast.get("var_type")
            if struct_type not in self.struct_name_to_def:
                super().error(ErrorType.TYPE_ERROR, f"Undefined struct type of {struct_type}")
            fields = {}
            #now we will initialize struct fields
            for field in self.struct_name_to_def[struct_type].get("fields"):
                field_name = field.get("name")
                field_type = field.get("var_type")
                if field_type == Type.INT:
                    fields[field_name] = Value(Type.INT, 0) #initilaize with default values
                elif field_type == Type.STRING:
                    fields[field_name] = Value(Type.STRING, "") #default
                elif field_type == Type.BOOL:
                    fields[field_name] = Value(Type.BOOL, False)
                elif field_type in self.struct_name_to_def: #this checks if it is a struct type (one of the valid types)
                    fields[field_name] = Value(Type.NIL, None)
                else:
                    super().error(ErrorType.TYPE_ERROR, f"Invalid field type {field_type}")
            return Value(struct_type, fields) #returning a Value object that represents the new struct instance!! (this is important because fixes error of accessing raw dict instances)
        
        #Variable nodes: also now have to handle accessing struct fields using the dot operator
        if expr_ast.elem_type == InterpreterBase.VAR_NODE:
            var_name = expr_ast.get("name")
            #check if this is a field access that uses the dot operator notaiton
            if '.' in var_name: # wait maybe checknthis part
                parts = var_name.split('.')
                base_var_name = parts[0]
                field_names = parts[1:]
                #get base variable -- struct isntance
                base_var = self.env.get(base_var_name)
                #print(f"DEBUG: Trying to access base variable '{base_var_name}' from environment.")
                if base_var is None:
                    super().error(ErrorType.NAME_ERROR, f"Variable {base_var_name} is not found")
                
                if base_var.value() is None:
                    #print(f"DEBUG: base_var '{base_var_name}' retrieved as nil. Type: {base_var.type()}. Potential Issue: Was it created or set properly?")
                    super().error(ErrorType.FAULT_ERROR, f"Variable{base_var_name} is nil (in eval_expr)")
                
                if base_var.type() not in self.struct_name_to_def:
                    super().error(ErrorType.TYPE_ERROR, f"{base_var_name} is not a struct, cannot access field!")
                
              
               
            
                # Traverse through the fields
                #struct_value = base_var.value()
                #Citation: The following code is from ChatGPT
                struct_value = base_var
                for field_name in field_names:
                    if not isinstance(struct_value, Value):
                        super().error(ErrorType.TYPE_ERROR, f"Expected a Value object, got {type(struct_value)}")
                    
                    # Unwrap to access underlying struct or value map (dictionary of fields)
                    struct_data = struct_value.value()
                    if struct_data is None:
                         super().error(ErrorType.FAULT_ERROR, f"Attempted to access a field on a nil value in {base_var_name}.{'.'.join(field_names)}")

                    if not isinstance(struct_data, dict):  # Ensure you are working with a dictionary
                        super().error(ErrorType.TYPE_ERROR, f"Expected a struct dictionary, got {type(struct_data)}")
                    
                    if field_name not in struct_data:
                        super().error(ErrorType.NAME_ERROR, f"Field {field_name} is not found in the struct {struct_value.type()}")
                # End of copied code   
                    # Ensure struct_value remains a Value for the next iteration (if applicable)
                    #if not isinstance(struct_value, Value):
                        #struct_value = Value(struct_value.type(), struct_value)

                    
                    struct_value = struct_data[field_name]  # Move to the next field (which should be another Value)

                # Return the final field's value
                if not isinstance(struct_value, Value):
                    super().error(ErrorType.TYPE_ERROR, f"Expected a Value object, got {type(struct_value)}")
                return struct_value
            
            #just the regular variable node access from below
            val = self.env.get(var_name)
            #print(f"DEBUG: Retrieved '{var_name}' from environment: {val}")
            if val is None:
                super().error(ErrorType.NAME_ERROR, f"Variable {var_name} not found")

            if not isinstance(val, Value):
                #print(f"DEBUG: Unexpected type in __eval_expr for var {var_name}: {type(val)}")
                super().error(ErrorType.TYPE_ERROR, "Expected Value object")
            return val


        if expr_ast.elem_type == InterpreterBase.NIL_NODE:
            return Interpreter.NIL_VALUE
        if expr_ast.elem_type == InterpreterBase.INT_NODE:
            return Value(Type.INT, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.STRING_NODE:
            return Value(Type.STRING, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.BOOL_NODE:
            return Value(Type.BOOL, expr_ast.get("val"))
        #moved var_node up to handle with the struct dot operator access

        if expr_ast.elem_type == InterpreterBase.FCALL_NODE:
            # Call the function and get the return value
            return_val = self.__call_func(expr_ast)
            print(f"return value type {return_val.type()}")

            #THIS FIXED THE VOID RETURN TEST CASE!!! HAVE TO MAKE SURE function of void type can't be used in expression where value is expected
            if return_val.type() == Type.VOID:
                super().error(ErrorType.TYPE_ERROR, '')


            # Check if the function has a void/nil return type but was used in an invalid way
            if return_val.type() == Type.NIL:
                # Check if the function return type was a struct or explicitly expected to be nil
                print("check")
                if self.return_type_stack:
                    func_return_type = self.return_type_stack[-1]
                    print(f"nil return type's function {func_return_type}")

                    if func_return_type in self.struct_name_to_def:
                        # Allow usage since structs can return nil
                        return return_val
                    # If it's a void/nil but the function has a non-struct expected return type
                    if func_return_type == Type.NIL:
                        # Allow usage in expressions if it's explicitly of nil type
                        return return_val

                # If it reached here, it's an invalid usage of a void function in an expression
                #super().error(ErrorType.TYPE_ERROR, "Cannot use a void function in an expression")


            return return_val 

           

        
        if expr_ast.elem_type in Interpreter.BIN_OPS:
            return self.__eval_op(expr_ast)
        if expr_ast.elem_type == Interpreter.NEG_NODE:
            return self.__eval_unary(expr_ast, Type.INT, lambda x: -1 * x)
        if expr_ast.elem_type == Interpreter.NOT_NODE:
            return self.__eval_unary(expr_ast, Type.BOOL, lambda x: not x)
        
        super().error(ErrorType.TYPE_ERROR, "Invalid expression node")

    def __eval_op(self, arith_ast):
        left_value_obj = self.__eval_expr(arith_ast.get("op1"))
        right_value_obj = self.__eval_expr(arith_ast.get("op2"))

        #have to check if either is void type --> error
        print(f"DEBUG: left value type: {left_value_obj.type()} rigth type {right_value_obj.type()}")
        #if left_value_obj.type() == Type.NIL or right_value_obj.type() == Type.NIL:
            #super().error(ErrorType.TYPE_ERROR, "Cannot compare with void types")
        
        if left_value_obj.type() == Type.NIL or right_value_obj.type() == Type.NIL:
            # Ensure comparison is only allowed if the other value is a struct or nil itself
            if not ((left_value_obj.type() in self.struct_name_to_def or left_value_obj.type() == Type.NIL) and
                    (right_value_obj.type() in self.struct_name_to_def or right_value_obj.type() == Type.NIL)):
                super().error(ErrorType.TYPE_ERROR, "Only structs or nil may be compared with nil")

            # Allow comparisons using == and != for structs and nil
            if arith_ast.elem_type in {"==", "!="}:
                result = (left_value_obj.type() == right_value_obj.type() and left_value_obj.value() == right_value_obj.value()) if arith_ast.elem_type == "==" else (left_value_obj.type() != right_value_obj.type() or left_value_obj.value() != right_value_obj.value())
                return Value(Type.BOOL, result)
            else:
                # Disallow any other operations involving nil
                super().error(ErrorType.TYPE_ERROR, "Invalid operation with nil")
            
        #also handle struct comparisons!
        #Citation: following code generated by ChatGPT
        if left_value_obj.type() in self.struct_name_to_def and right_value_obj.type() in self.struct_name_to_def:
            if left_value_obj.type() != right_value_obj.type():
                super().error(ErrorType.TYPE_ERROR, "Cannot compare structs of different types")
            # Allow struct comparison logic for `==` and `!=` if they are of the same type
            if arith_ast.elem_type in {"==", "!="}:
                result = (left_value_obj.value() == right_value_obj.value()) if arith_ast.elem_type == "==" else (left_value_obj.value() != right_value_obj.value())
                return Value(Type.BOOL, result)
        #end of copied code


        #first, coerce int to bool for the logical operations of && and || 
        if arith_ast.elem_type in {"&&", "||"}:
            left_value_obj = self.__do_int_to_bool_coercion(left_value_obj)
            right_value_obj = self.__do_int_to_bool_coercion(right_value_obj)

        # also do coercion for the comparison operations == and !=
        if arith_ast.elem_type in {"==", "!="}:
            #you can only do coercion of one of them is int and the other is bool
            if left_value_obj.type() == Type.INT and right_value_obj.type() == Type.BOOL:
                left_value_obj = self.__do_int_to_bool_coercion(left_value_obj)
            elif left_value_obj.type() == Type.BOOL and right_value_obj.type() == Type.INT:
                right_value_obj = self.__do_int_to_bool_coercion(right_value_obj)

            #now compare once coerced
            if arith_ast.elem_type == "==":
                return Value(Type.BOOL, left_value_obj.value() == right_value_obj.value())
            elif arith_ast.elem_type == "!=":
                return Value(Type.BOOL, left_value_obj.value() != right_value_obj.value())

        #now back to regular compability no coercions for different types:
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

        #coercion int->bool
        if t == Type.BOOL and value_obj.type() == Type.INT:
            value_obj = self.__do_int_to_bool_coercion(value_obj)
    

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

        # coerce from int to bool if applicable
        result = self.__do_int_to_bool_coercion(result) #no additional check needed first because coercion function will just return value if not int

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
        run_for = Interpreter.TRUE_VALUE
        while run_for.value():
            run_for = self.__eval_expr(cond_ast)  # check for-loop condition

            # first apply coercion if int
            if run_for.type() == Type.INT:
                run_for = self.__do_int_to_bool_coercion(run_for)

            if run_for.type() != Type.BOOL:
                super().error(
                    ErrorType.TYPE_ERROR,
                    "Incompatible type for for condition",
                )
            if run_for.value():
                statements = for_ast.get("statements")
                status, return_val = self.__run_statements(statements)
                if status == ExecStatus.RETURN:
                    return status, return_val
                self.__run_statement(update_ast)  # update counter variable

        return (ExecStatus.CONTINUE, Interpreter.NIL_VALUE)

    def __do_return(self, return_ast):
        expr_ast = return_ast.get("expression")
        if expr_ast is None:
            # got to check when no return type is specified --> then return default
            if self.return_type_stack:
                func_return_type = self.return_type_stack[-1] #the current function return type is the latest one, at top of stack
                if func_return_type == Type.INT:
                    return (ExecStatus.RETURN, Value(Type.INT, 0)) #int default value is 0
                elif func_return_type == Type.STRING:
                    return (ExecStatus.RETURN, Value(Type.STRING, "")) #string default value is ""
                elif func_return_type == Type.BOOL:
                    return (ExecStatus.RETURN, Value(Type.BOOL, False)) #bool default value is False
                elif func_return_type in self.struct_name_to_def:
                    print("we here")
                    return (ExecStatus.RETURN, Interpreter.NIL_VALUE)
                elif func_return_type == "void":
                    return (ExecStatus.RETURN, Value(Type.VOID)) #we refer to nil value with NIL_VALUE instead of None? check this
                elif func_return_type is None:
                    super().error(ErrorType.TYPE_ERROR, "Return type is undefined for this function")
            return (ExecStatus.RETURN, Interpreter.NIL_VALUE)

        value_obj = copy.copy(self.__eval_expr(expr_ast))

        if self.return_type_stack:
            func_return_type = self.return_type_stack[-1]
            #check if a struct type allows returning nil
            if func_return_type in self.struct_name_to_def and value_obj.type() == Type.NIL:
                return (ExecStatus.RETURN, value_obj)

            # do coercion from int to bool if the function's return type is bool
            if func_return_type == Type.BOOL and value_obj.type() == Type.INT:
                value_obj = self.__do_int_to_bool_coercion(value_obj)

            #type check the return value
            if func_return_type != value_obj.type():
                super().error(ErrorType.TYPE_ERROR, f"Return type mismatches! We expect {func_return_type} but we got {value_obj.type()}")

        return (ExecStatus.RETURN, value_obj)
    
    def __do_int_to_bool_coercion(self, value_obj):
        if value_obj.type() == Type.INT:
            return Value(Type.BOOL, value_obj.value() != 0) #this is the coercion-- 0 goes to False and non-zero coerced to True
        return value_obj # if the type is not int, just return the origional value
    

def main():

    program_source1 = """
struct X {i: int; b: bool; s:string;}
struct Y {i: int; b: bool; s:string;}
struct Z {x: X; y: Y; z: Z;}

func main(): void {
  var v: Z;
  v = new Z;
  setZ(v, 42, true, "marco");
  v.z.z.z.z = nil;
  print("v.x.i: ", v.x.i);
  print("v.x.b: ", v.x.b);
  print("v.x.s: ", v.x.s);
  print("v.y.i: ", v.y.i);
  print("v.y.b: ", v.y.b);
  print("v.y.s: ", v.y.s);
  print(v.z.z.z.z.y.b);
}

func setZ(v: Z, i: int, b: bool, s:string): void {
  v.z = v;
  v.x = new X;
  v.y = new Y;
  v.z.z.z.z.z.z.x.i = i;
  v.x.b = b;
  v.z.z.z.z.x.s = s;
  v.z.z.z.z.z.z.y.i = 100 - i;
  v.y.b = !b;
  v.z.z.z.z.y.s = s + " polo";
}

    """
    interpreter = Interpreter()
    interpreter.run(program_source1)

if __name__ == "__main__":
    main()