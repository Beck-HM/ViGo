class ASTNode: pass


class Program(ASTNode):
    def __init__(self, stmts): self.statements = stmts


class VarDecl(ASTNode):
    def __init__(self, name, value, is_const=False): self.name = name; self.value = value; self.is_const = is_const


class DestructureDecl(ASTNode):
    def __init__(self, names, value): self.names = names; self.value = value


class AssignStmt(ASTNode):
    def __init__(self, target, op, value): self.target = target; self.op = op; self.value = value


class IfStmt(ASTNode):
    def __init__(self, cond, then_body, else_body): self.condition = cond; self.then_body = then_body; self.else_body = else_body


class SkipStmt(ASTNode):
    def __init__(self, cond, body): self.condition = cond; self.body = body


class TernaryExpr(ASTNode):
    def __init__(self, cond, t, e): self.condition = cond; self.then_expr = t; self.else_expr = e


class SwitchStmt(ASTNode):
    def __init__(self, expr, cases, default_body): self.expr = expr; self.cases = cases; self.default_body = default_body


class ForInStmt(ASTNode):
    def __init__(self, var, iterable, body): self.var_name = var; self.iterable = iterable; self.body = body


class LoopStmt(ASTNode):
    def __init__(self, cond, body): self.condition = cond; self.body = body


class DoWhileStmt(ASTNode):
    def __init__(self, body, condition): self.body = body; self.condition = condition


class BreakStmt(ASTNode): pass
class ContinueStmt(ASTNode): pass


class FuncDef(ASTNode):
    def __init__(self, name, params, defaults, rest_param, body):
        self.name = name; self.params = params; self.defaults = defaults
        self.rest_param = rest_param; self.body = body


class LambdaExpr(ASTNode):
    def __init__(self, params, body): self.params = params; self.body = body


class StaticMethodDef(ASTNode):
    def __init__(self, func_def): self.func_def = func_def


class AbstractMethodDef(ASTNode):
    def __init__(self, name, params): self.name = name; self.params = params


class InterfaceDef(ASTNode):
    def __init__(self, name, methods): self.name = name; self.methods = methods


class ReturnStmt(ASTNode):
    def __init__(self, value): self.value = value


class FuncCall(ASTNode):
    def __init__(self, name, args): self.name = name; self.args = args


class BinaryOp(ASTNode):
    def __init__(self, left, op, right): self.left = left; self.op = op; self.right = right


class InExpr(ASTNode):
    def __init__(self, left, right, negated=False): self.left = left; self.right = right; self.negated = negated


class UnaryOp(ASTNode):
    def __init__(self, op, operand): self.op = op; self.operand = operand


class LogicalOp(ASTNode):
    def __init__(self, left, op, right): self.left = left; self.op = op; self.right = right


class PipeExpr(ASTNode):
    def __init__(self, left, right): self.left = left; self.right = right


class RangeExpr(ASTNode):
    def __init__(self, start, end): self.start = start; self.end = end


class ExpandExpr(ASTNode):
    def __init__(self, expr): self.expr = expr


class OptionalChain(ASTNode):
    def __init__(self, obj, chain): self.object = obj; self.chain = chain


class NullCoalesce(ASTNode):
    def __init__(self, left, right): self.left = left; self.right = right


class ListCompExpr(ASTNode):
    def __init__(self, expr, var, iterable, condition):
        self.expr = expr; self.var = var; self.iterable = iterable; self.condition = condition


class ChainedCompare(ASTNode):
    def __init__(self, ops, operands): self.ops = ops; self.operands = operands


class SureStmt(ASTNode):
    def __init__(self, condition, message): self.condition = condition; self.message = message


class Literal(ASTNode):
    def __init__(self, value): self.value = value


class Variable(ASTNode):
    def __init__(self, name): self.name = name


class ListLiteral(ASTNode):
    def __init__(self, elements): self.elements = elements


class DictLiteral(ASTNode):
    def __init__(self, pairs): self.pairs = pairs


class SetLiteral(ASTNode):
    def __init__(self, elements): self.elements = elements


class IndexAccess(ASTNode):
    def __init__(self, obj, idx): self.object = obj; self.index = idx


class SliceAccess(ASTNode):
    def __init__(self, obj, start, end): self.object = obj; self.start = start; self.end = end


class DotAccess(ASTNode):
    def __init__(self, obj, attr): self.object = obj; self.attr = attr


class InterpolatedString(ASTNode):
    def __init__(self, parts): self.parts = parts


class LoadStmt(ASTNode):
    def __init__(self, filepath, alias): self.filepath = filepath; self.alias = alias


class ClassDef(ASTNode):
    def __init__(self, name, parent, body): self.name = name; self.parent = parent; self.body = body


class NewExpr(ASTNode):
    def __init__(self, class_name, args): self.class_name = class_name; self.args = args


class ThisExpr(ASTNode): pass


class TryStmt(ASTNode):
    def __init__(self, try_body, catch_var, catch_body):
        self.try_body = try_body; self.catch_var = catch_var; self.catch_body = catch_body


class ThrowStmt(ASTNode):
    def __init__(self, value): self.value = value


class AwaitExpr(ASTNode):
    def __init__(self, value): self.value = value


class EnumDef(ASTNode):
    def __init__(self, name, members): self.name = name; self.members = members