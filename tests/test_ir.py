from vigo.lexer.lexer import Lexer
from vigo.parser.parser import Parser
from vigo.ir import IRBuilder, IROptimizer

source = "x = 2 + 3 * 4"
lexer = Lexer(source)
parser = Parser(lexer)
ast = parser.parse_program()

builder = IRBuilder()
ir = builder.build(ast)
print("Generated IR:")
for inst in ir:
    print(f"  {inst}")

optimizer = IROptimizer()
opt_ir = optimizer.optimize(ir)
print("Optimized IR:")
for inst in opt_ir:
    print(f"  {inst}")