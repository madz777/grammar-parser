from lark import Lark, Transformer, v_args
import sys

grammar = """
    start: funcdef+

    funcdef: "def" NAME "(" ")" "{" statement_block "}" -> define_func

    ?statement: conditional
              | expr ";"
              | loop ":"

    statement_block: statement*

    conditional: "if" "(" expr ")" "{" statement_block "}" -> conditional_if
               | "if" "(" expr ")" "{" statement_block "}" "else" "{" statement_block "}" -> conditional_if_else

    expr: NUMBER -> number
        | NAME -> load_var
        | expr "+" expr -> add
        | expr "<" expr -> less_than
        | expr ">" expr -> greater_than
        | NAME "=" expr -> assignment
        | NAME "(" ")" -> call_func

    loop: "for" "(" expr ";" expr ";" conditional ")" "{" statement_block "}" -> for_loop

    NAME: /[A-Za-z_]+/

    %import common.NUMBER
    %import common.WS
    %ignore WS
"""

@v_args(inline=True)
class ParseTree(Transformer):

    def __init__(self):
        self.freeregs = set(["x"+str(i) for i in range(5,32)])
        self.vars = {}
        self.labels = set()

    def choose_reg(self):
        if len(self.freeregs) == 0:
            raise Exception("out of registers")
        else:
            reg = self.freeregs.pop()
            return reg

    def yield_reg(self, reg):
        self.freeregs.add(reg)

    def locate_var(self, name):
        if name not in self.vars:
            self.vars[name] = 4*len(self.vars)
            return self.vars[name]
        else:
            return self.vars[name]

    def make_label(self):
        label_num = len(self.labels) + 1
        self.labels.add(f"L{label_num}")
        return f"L{label_num}"

    def define_func(self, name, statement_block):
        statements = statement_block.children
        statement_code = []
        for s in statements:
            statement_code += s[1]
        output_code = [f"F{name}:"] + statement_code
        if name != 'main':
            output_code += [f"jalr ra, ra, 0"]
        return (None, output_code)

    def call_func(self, name):
        output_code = [f"jal ra, F{name}"]
        return ("x10", output_code)

    def number(self, n):
        reg = self.choose_reg()
        return (reg, [f"addi {reg}, zero, {n}"])

    def add(self, left, right):
        left_reg = left[0]
        left_code = left[1]
        right_reg = right[0]
        right_code = right[1]
        reg = self.choose_reg()
        self.yield_reg(left_reg)
        self.yield_reg(right_reg)
        return (reg, left_code + right_code + [f"add {reg}, {left_reg}, {right_reg}"])

    def less_than(self, left, right):
        # returns 0 or 1
        # if left<right then right-left is positive
        reg = self.choose_reg()
        label_true = self.make_label()
        label_done = self.make_label()
        code = left[1] + right[1] + [f"sub {reg}, {right[0]}, {left[0]}"] + \
            [f"blt zero, {reg}, {label_true}"] + \
            [f"addi {reg}, zero, 0"] + \
            [f"jal ra, {label_done}"] + \
            [f"{label_true}:"] + \
            [f"addi {reg}, zero, 1"] + \
            [f"{label_done}:"]
        self.yield_reg(left[0])
        self.yield_reg(right[0])
        return (reg, code)

    def greater_than(self, left, right):
        return self.less_than(right, left)

    def assignment(self, name, left):
        reg = left[0]
        code = left[1]
        loc = self.locate_var(name)        
        self.yield_reg(reg)
        return (reg, code + [f"sw {reg}, {loc}(sp)"])

    def load_var(self, name):
        loc = self.locate_var(name)
        reg = self.choose_reg()
        return (reg, [f"lw {reg}, {loc}(sp)"])

    def conditional_if(self, bool_expr, statement_block):
        statements = statement_block.children
        label_skip = self.make_label()
        statement_code = []
        for s in statements:
            statement_code += s[1]
        output_code = bool_expr[1] + [f"beq zero, {bool_expr[0]}, {label_skip}"] + statement_code + [f"{label_skip}:"]
        self.yield_reg(bool_expr[0])
        return (None, output_code)

    def conditional_if_else(self, bool_expr, if_statement_block, else_statement_block):
        if_statements = if_statement_block.children
        else_statements = else_statement_block.children
        label_done = self.make_label()
        label_else = self.make_label()
        if_statement_code = []
        for s in if_statements:
            if_statement_code += s[1]
        else_statement_code = []
        for s in else_statements:
            else_statement_code += s[1]
        output_code = bool_expr[1] + [f"beq zero, {bool_expr[0]}, {label_else}"] + if_statement_code + \
            [f"jal ra, {label_done}"] + [f"{label_else}:"] + else_statement_code + [f"{label_done}:"]
        self.yield_reg(bool_expr[0])
        return (None, output_code)

    def for_loop(counter, iteration, stop):
        label_start = self.make_label()
        loop_code = []
        
        

def do_parse(source):
    parser = Lark(grammar, parser='lalr', transformer=ParseTree())
    print(f"jal ra, Fmain")
    print()
    for statement in parser.parse(source).children:
        print('\n'.join(statement[1]))
        print()

if len(sys.argv) == 2:
    with open(sys.argv[1]) as f:
        source = f.read()
        do_parse(source)
else:
    while True:
        try:
            s = input("> ").strip()
            if s == "":
                break
            do_parse(s)
        except Exception as e:
            print(e)