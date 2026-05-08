from ..lexer.tokens import TokenType, Token
from ..lexer.lexer import Lexer
from .ast_nodes import *


class Parser:
    def __init__(self, lexer):
        self.lexer = lexer
        self.source = lexer.source  # Keep source for error display
        self.current_token = self.lexer.get_next_token()
        self._destructure_names = []

    def error(self, msg, help_text=None):
        t = self.current_token
        line_num = t.line
        col_num = t.column

        # Build the error header
        lines = [f"Syntax error [Line{line_num}, Column{col_num}]: {msg}"]

        # Show the source line with a pointer
        source_lines = self.source.split('\n')
        if line_num <= len(source_lines):
            offending_line = source_lines[line_num - 1]
            lines.append(f"  {offending_line}")
            # Point to the error column
            pointer = ' ' * (col_num + 1) + '^'
            lines.append(f"  {pointer}")

        # Add help text if provided
        if help_text:
            lines.append(f"Help: {help_text}")

        raise Exception('\n'.join(lines))

    def eat(self, tt):
        if self.current_token.type == tt:
            self.current_token = self.lexer.get_next_token()
        else:
            self.error(
                f"Expected {tt.name}, but got {self.current_token.type.name}('{self.current_token.value}')",
                f"Check that you used the correct delimiter here. Expected {tt.name}."
            )

    def match(self, tt):
        if self.current_token.type == tt:
            self.eat(tt); return True
        return False

    def optional_semicolon(self): self.match(TokenType.SEMICOLON)

    def _restore(self, state):
        self.lexer.pos, self.lexer.line, self.lexer.col, self.lexer.current_char = state[:4]
        self.current_token = state[4]

    # ── Block parsing helper ──
    def _parse_block(self, terminators=None):
        """Parse statements until a terminator token or Fin at depth 0.
        Returns (body, fin_consumed, stopped_on).
        terminators: set of token types that stop the block (e.g. {CATCH, EIF, EL}).
        """
        if terminators is None:
            terminators = set()
        body = []
        depth = 1
        fin_consumed = False
        stopped_on = None
        while depth > 0:
            t = self.current_token
            if t.type == TokenType.TS:
                depth += 1
                self.eat(TokenType.TS)
            elif t.type in terminators and depth == 1:
                stopped_on = t.type
                break
            elif t.type == TokenType.FIN:
                depth -= 1
                if depth == 0:
                    self.eat(TokenType.FIN)
                    fin_consumed = True
                    break
                self.eat(TokenType.FIN)
            elif t.type == TokenType.EOF:
                self.error(f"Missing Fin (unclosed block)")
            else:
                body.append(self.parse_statement())
        return body, fin_consumed, stopped_on

    def parse_program(self):
        stmts = []
        while self.current_token.type != TokenType.EOF:
            stmts.append(self.parse_statement())
        return Program(stmts)

    def parse_statement(self):
        t = self.current_token

        if t.type == TokenType.LOAD: return self.parse_load_stmt()
        if t.type == TokenType.CLASS: return self.parse_class_def()
        if t.type == TokenType.ENUM: return self.parse_enum_def()
        if t.type == TokenType.TRY: return self.parse_try_stmt()
        if t.type == TokenType.THROW: return self.parse_throw_stmt()
        if t.type == TokenType.SWITCH: return self.parse_switch_stmt()
        if t.type == TokenType.IF: return self.parse_if_stmt()
        if t.type == TokenType.SKIP: return self.parse_skip_stmt()
        if t.type == TokenType.GO: return self.parse_do_while_stmt()
        if t.type == TokenType.FOR: return self.parse_for_in_stmt()
        if t.type == TokenType.LOOP: return self.parse_loop_stmt()
        if t.type == TokenType.BREAK: self.eat(TokenType.BREAK); self.optional_semicolon(); return BreakStmt()
        if t.type == TokenType.CONTINUE: self.eat(TokenType.CONTINUE); self.optional_semicolon(); return ContinueStmt()
        if t.type == TokenType.FUN: return self.parse_func_def()
        if t.type == TokenType.RET: return self.parse_return_stmt()
        if t.type == TokenType.SPAWN: return self.parse_spawn()
        if t.type == TokenType.SURE: return self.parse_sure_stmt()

        if t.type == TokenType.STATIC:
            self.eat(TokenType.STATIC)
            return StaticMethodDef(self.parse_func_def())

        if t.type == TokenType.ABSTRACT:
            self.eat(TokenType.ABSTRACT)
            return self.parse_abstract_method()

        if t.type == TokenType.INTERFACE:
            return self.parse_interface_def()

        if t.type == TokenType.CONST:
            self.eat(TokenType.CONST)
            name = self.current_token.value; self.eat(TokenType.IDENTIFIER)
            self.eat(TokenType.ASSIGN); val = self.parse_expression()
            self.optional_semicolon(); return VarDecl(name, val, is_const=True)

        # this Assignment
        if t.type == TokenType.THIS:
            if self._lookahead_dot_assign():
                return self.parse_dot_assign()
            return self.parse_expr_stmt()

        if t.type == TokenType.IDENTIFIER:
            destructure = self._try_parse_destructure_v2()
            if destructure is not None: return destructure
            at = self._lookahead_for_assignment()
            if at: return self.parse_assign(at)
            if self._lookahead_dot_assign(): return self.parse_dot_assign()
            return self.parse_expr_stmt()

        return self.parse_expr_stmt()

    def _try_parse_destructure_v2(self):
        if self.current_token.type != TokenType.IDENTIFIER: return None
        saved = (self.lexer.pos, self.lexer.line, self.lexer.col, self.lexer.current_char, self.current_token)
        names = [self.current_token.value]
        self.eat(TokenType.IDENTIFIER)
        if self.current_token.type != TokenType.COMMA:
            self._restore(saved); return None
        try:
            while True:
                self.eat(TokenType.COMMA)
                if self.current_token.type == TokenType.IDENTIFIER:
                    names.append(self.current_token.value); self.eat(TokenType.IDENTIFIER)
                elif self.current_token.type == TokenType.LPAREN:
                    names.append(self.parse_nested_destructure())
                else: raise Exception("expected name")
                if self.current_token.type != TokenType.COMMA: break
            self.eat(TokenType.ASSIGN); val = self.parse_expression()
            self.optional_semicolon(); return DestructureDecl(names, val)
        except Exception:
            self._restore(saved); return None

    def parse_nested_destructure(self):
        self.eat(TokenType.LPAREN)
        names = [self.current_token.value]; self.eat(TokenType.IDENTIFIER)
        while self.match(TokenType.COMMA): names.append(self.current_token.value); self.eat(TokenType.IDENTIFIER)
        self.eat(TokenType.RPAREN); return ('tuple', names)

    def parse_abstract_method(self):
        self.eat(TokenType.FUN); self.eat(TokenType.AS)
        name = self.current_token.value; self.eat(TokenType.IDENTIFIER)
        self.eat(TokenType.LPAREN)
        params = []
        if self.current_token.type != TokenType.RPAREN:
            params.append(self.current_token.value); self.eat(TokenType.IDENTIFIER)
            while self.match(TokenType.COMMA): params.append(self.current_token.value); self.eat(TokenType.IDENTIFIER)
        self.eat(TokenType.RPAREN); self.optional_semicolon(); return AbstractMethodDef(name, params)

    def parse_interface_def(self):
        self.eat(TokenType.INTERFACE)
        name = self.current_token.value; self.eat(TokenType.IDENTIFIER)
        self.eat(TokenType.TS)
        methods = []
        depth = 1
        while depth > 0:
            if self.current_token.type == TokenType.TS: depth += 1; self.eat(TokenType.TS)
            elif self.current_token.type == TokenType.FIN:
                depth -= 1
                if depth == 0: self.eat(TokenType.FIN); break
                self.eat(TokenType.FIN)
            elif self.current_token.type == TokenType.EOF: self.error("InterfaceMissing Fin")
            else:
                if self.current_token.type == TokenType.ABSTRACT: self.eat(TokenType.ABSTRACT)
                methods.append(self.parse_abstract_method())
        self.optional_semicolon(); return InterfaceDef(name, methods)

    def _lookahead_for_assignment(self):
        if self.current_token.type != TokenType.IDENTIFIER: return None
        saved = (self.lexer.pos, self.lexer.line, self.lexer.col, self.lexer.current_char)
        st = self.current_token; nt = self.lexer.get_next_token()
        self.lexer.pos, self.lexer.line, self.lexer.col, self.lexer.current_char = saved
        self.current_token = st
        ats = [TokenType.ASSIGN, TokenType.PLUS_ASSIGN, TokenType.MINUS_ASSIGN,
               TokenType.STAR_ASSIGN, TokenType.SLASH_ASSIGN, TokenType.PERCENT_ASSIGN]
        return nt.type if nt.type in ats else None

    def _lookahead_dot_assign(self):
        if self.current_token.type not in (TokenType.IDENTIFIER, TokenType.THIS):
            return False
        saved = (self.lexer.pos, self.lexer.line, self.lexer.col, self.lexer.current_char)
        st = self.current_token; t1 = self.lexer.get_next_token()
        result = False
        if t1.type == TokenType.DOT:
            t2 = self.lexer.get_next_token()
            if t2.type == TokenType.IDENTIFIER:
                t3 = self.lexer.get_next_token()
                ats = [TokenType.ASSIGN, TokenType.PLUS_ASSIGN, TokenType.MINUS_ASSIGN,
                       TokenType.STAR_ASSIGN, TokenType.SLASH_ASSIGN, TokenType.PERCENT_ASSIGN]
                if t3.type in ats: result = True
        self.lexer.pos, self.lexer.line, self.lexer.col, self.lexer.current_char = saved
        self.current_token = st; return result

    def parse_assign(self, at):
        name = self.current_token.value; self.eat(TokenType.IDENTIFIER)
        op_tok = self.current_token; self.eat(at)
        val = self.parse_expression(); self.optional_semicolon()
        return VarDecl(name, val) if at == TokenType.ASSIGN else AssignStmt(Variable(name), op_tok.value, val)

    def parse_dot_assign(self):
        if self.current_token.type == TokenType.THIS:
            self.eat(TokenType.THIS); obj = ThisExpr()
        else:
            oname = self.current_token.value; self.eat(TokenType.IDENTIFIER); obj = Variable(oname)
        self.eat(TokenType.DOT); attr = self.current_token.value
        self.eat(TokenType.IDENTIFIER); op_tok = self.current_token; self.eat(op_tok.type)
        val = self.parse_expression(); self.optional_semicolon()
        return AssignStmt(DotAccess(obj, attr), op_tok.value, val)

    def parse_load_stmt(self):
        self.eat(TokenType.LOAD); fp = self.current_token.value; self.eat(TokenType.STRING)
        alias = None
        if self.match(TokenType.AS): alias = self.current_token.value; self.eat(TokenType.IDENTIFIER)
        self.optional_semicolon(); return LoadStmt(fp, alias)

    def parse_class_def(self):
        self.eat(TokenType.CLASS); name = self.current_token.value; self.eat(TokenType.IDENTIFIER)
        parent = None
        if self.match(TokenType.EXTENDS): parent = self.current_token.value; self.eat(TokenType.IDENTIFIER)
        self.eat(TokenType.TS)
        body = []
        depth = 1
        while depth > 0:
            if self.current_token.type == TokenType.TS: depth += 1; self.eat(TokenType.TS)
            elif self.current_token.type == TokenType.FIN:
                depth -= 1
                if depth == 0: self.eat(TokenType.FIN); break
                self.eat(TokenType.FIN)
            elif self.current_token.type == TokenType.EOF: self.error("ClassMissing Fin")
            else: body.append(self.parse_statement())
        self.optional_semicolon(); return ClassDef(name, parent, body)

    def parse_enum_def(self):
        self.eat(TokenType.ENUM); name = self.current_token.value; self.eat(TokenType.IDENTIFIER)
        self.eat(TokenType.TS); members = []
        depth = 1
        while depth > 0:
            if self.current_token.type == TokenType.TS: depth += 1; self.eat(TokenType.TS)
            elif self.current_token.type == TokenType.FIN:
                depth -= 1
                if depth == 0: self.eat(TokenType.FIN); break
                self.eat(TokenType.FIN)
            elif self.current_token.type == TokenType.EOF: self.error("EnumMissing Fin")
            else:
                m = self.current_token.value; self.eat(TokenType.IDENTIFIER)
                if len(members) == 0:
                    val = 0
                else:
                    val = members[-1][1] + 1
                if self.match(TokenType.ASSIGN): val = self.eval_literal()
                members.append((m, val)); self.optional_semicolon()
        self.optional_semicolon(); return EnumDef(name, members)

    def eval_literal(self):
        t = self.current_token
        if t.type == TokenType.REGEX:
            self.eat(TokenType.REGEX)
            return RegexLiteral(t.value[0], t.value[1])
        if t.type == TokenType.NUMBER: self.eat(TokenType.NUMBER); return t.value
        if t.type == TokenType.STRING: self.eat(TokenType.STRING); return t.value
        if t.type == TokenType.TRUE: self.eat(TokenType.TRUE); return True
        if t.type == TokenType.FALSE: self.eat(TokenType.FALSE); return False
        if t.type == TokenType.NULL: self.eat(TokenType.NULL); return None
        if t.type == TokenType.MINUS: self.eat(TokenType.MINUS); return -self.eval_literal()
        self.error("Expected literal")

    # ── try / catch ──
    def parse_try_stmt(self):
        self.eat(TokenType.TRY)
        self.eat(TokenType.TS)
        try_body, fin_consumed, stopped = self._parse_block(terminators={TokenType.CATCH})
        catch_var = None
        catch_body = []
        if stopped == TokenType.CATCH:
            self.eat(TokenType.CATCH)
            if self.current_token.type == TokenType.IDENTIFIER:
                catch_var = self.current_token.value
                self.eat(TokenType.IDENTIFIER)
            self.eat(TokenType.TS)
            catch_body, _, _ = self._parse_block()
        elif not fin_consumed:
            self.eat(TokenType.FIN)
        self.optional_semicolon()
        return TryStmt(try_body, catch_var, catch_body)

    def parse_throw_stmt(self):
        self.eat(TokenType.THROW); val = self.parse_expression()
        self.optional_semicolon(); return ThrowStmt(val)

    # ── switch ──
    def parse_switch_stmt(self):
        self.eat(TokenType.SWITCH)
        # Parse the switch expression (e.g., `switch x ts`)
        expr = self.parse_expression()
        self.eat(TokenType.TS)

        cases = []
        default_body = []
        depth = 1
        fin_consumed = False

        # Main loop: iterate through all case/default blocks until the outer Fin
        while depth > 0:
            t = self.current_token

            # Nested ts inside case body — increase depth so outer Fin won't close early
            if t.type == TokenType.TS:
                depth += 1
                self.eat(TokenType.TS)

            # Fin at depth 0 closes the entire switch; deeper Fins close inner blocks
            elif t.type == TokenType.FIN:
                depth -= 1
                if depth == 0:
                    self.eat(TokenType.FIN)
                    fin_consumed = True
                    break
                self.eat(TokenType.FIN)

            elif t.type == TokenType.EOF:
                self.error("switch missing Fin")

            # Case block: parse value, eat its ts, delegate body to _parse_block
            elif t.type == TokenType.CASE:
                self.eat(TokenType.CASE)

                # Case value can be a number, a range (num..num), a string, or a literal
                if self.current_token.type == TokenType.NUMBER:
                    start = self.current_token.value
                    self.eat(TokenType.NUMBER)
                    # Range matching: `case 0..59 ts`
                    if self.current_token.type == TokenType.RANGE:
                        self.eat(TokenType.RANGE)
                        end = self.current_token.value
                        self.eat(TokenType.NUMBER)
                        case_val = ('range', start, end)
                    else:
                        case_val = start
                elif self.current_token.type == TokenType.STRING:
                    case_val = self.current_token.value
                    self.eat(TokenType.STRING)
                else:
                    case_val = self.eval_literal()

                # Eat the ts that opens this case's body
                self.eat(TokenType.TS)
                # _parse_block stops at next CASE, DEFAULT, or the outer Fin
                case_body, _, _ = self._parse_block(terminators={TokenType.CASE, TokenType.DEFAULT})
                cases.append((case_val, case_body))

            # Default block: same logic as case but with empty terminators
            elif t.type == TokenType.DEFAULT:
                self.eat(TokenType.DEFAULT)
                self.eat(TokenType.TS)
                # Default always runs to the outer Fin (no case/default terminators)
                default_body, _, _ = self._parse_block(terminators=set())

            else:
                # Skip any unexpected tokens inside switch block
                self.eat(t.type)

        self.optional_semicolon()
        return SwitchStmt(expr, cases, default_body)

    # ── if / eif / el ──
    def parse_if_stmt(self):
        self.eat(TokenType.IF)
        cond = self.parse_expression()
        self.eat(TokenType.TS)
        then_body, fin_consumed, stopped = self._parse_block(terminators={TokenType.EIF, TokenType.EL})
        else_body = []
        while stopped == TokenType.EIF:
            self.eat(TokenType.EIF)
            ec = self.parse_expression()
            self.eat(TokenType.TS)
            eb, eb_fin, stopped = self._parse_block(terminators={TokenType.EIF, TokenType.EL})
            else_body.append((ec, eb))
            fin_consumed = eb_fin or stopped is not None
        if stopped == TokenType.EL:
            self.eat(TokenType.EL)
            self.eat(TokenType.TS)
            elb, _, _ = self._parse_block()
            else_body.append((None, elb))
        elif not fin_consumed:
            self.eat(TokenType.FIN)
        self.optional_semicolon()
        return IfStmt(cond, then_body, else_body)

    # ── skip (unless) ──
    def parse_skip_stmt(self):
        self.eat(TokenType.SKIP)
        cond = self.parse_expression()
        self.eat(TokenType.TS)
        body, fin_consumed, _ = self._parse_block()
        if not fin_consumed:
            self.eat(TokenType.FIN)
        self.optional_semicolon()
        return SkipStmt(cond, body)

    # ── go (do-while) ──
    def parse_do_while_stmt(self):
        self.eat(TokenType.GO)
        self.eat(TokenType.TS)
        body, fin_consumed, _ = self._parse_block()
        if not fin_consumed:
            self.eat(TokenType.FIN)
        self.eat(TokenType.LOOP); cond = self.parse_expression()
        self.optional_semicolon(); return DoWhileStmt(body, cond)

    # ── for-in ──
    def parse_for_in_stmt(self):
        self.eat(TokenType.FOR)
        vn = self.current_token.value
        self.eat(TokenType.IDENTIFIER)
        self.eat(TokenType.IN)
        it = self.parse_expression()
        self.eat(TokenType.TS)
        body, fin_consumed, _ = self._parse_block()
        if not fin_consumed:
            self.eat(TokenType.FIN)
        self.optional_semicolon()
        return ForInStmt(vn, it, body)

    # ── loop (while) ──
    def parse_loop_stmt(self):
        self.eat(TokenType.LOOP); cond = self.parse_expression(); self.eat(TokenType.TS)
        body, fin_consumed, _ = self._parse_block()
        if not fin_consumed:
            self.eat(TokenType.FIN)
        self.optional_semicolon(); return LoopStmt(cond, body)

    # ── function ──
    def parse_func_def(self):
        self.eat(TokenType.FUN); self.eat(TokenType.AS)
        name = self.current_token.value; self.eat(TokenType.IDENTIFIER)
        self.eat(TokenType.LPAREN); params, defaults, rest_param = self.parse_func_params()
        self.eat(TokenType.RPAREN); self.eat(TokenType.COLON)
        body, fin_consumed, _ = self._parse_block()
        if not fin_consumed:
            self.eat(TokenType.FIN)
        self.optional_semicolon()
        func_def = FuncDef(name, params, defaults, rest_param, body)
        # Build symbol table for fast variable lookup at runtime
        func_def.symbol_table = self._build_symbol_table(body, params, rest_param)
        return func_def

    def parse_func_params(self):
        params = []; defaults = {}; rest_param = None
        if self.current_token.type == TokenType.RPAREN: return params, defaults, rest_param
        if self.match(TokenType.EXPAND):
            rest_param = self.current_token.value; self.eat(TokenType.IDENTIFIER)
            return params, defaults, rest_param
        params.append(self.current_token.value); self.eat(TokenType.IDENTIFIER)
        if self.match(TokenType.ASSIGN): defaults[params[-1]] = self.parse_expression()
        while self.match(TokenType.COMMA):
            if self.match(TokenType.EXPAND):
                rest_param = self.current_token.value; self.eat(TokenType.IDENTIFIER); break
            params.append(self.current_token.value); self.eat(TokenType.IDENTIFIER)
            if self.match(TokenType.ASSIGN): defaults[params[-1]] = self.parse_expression()
        return params, defaults, rest_param

    def _build_symbol_table(self, body, params, rest_param):
        """Pre-scan function body to classify variables as local or closure."""
        from ..runtime.objects import SymbolTable
        st = SymbolTable()

        # Parameters are always local
        for p in params:
            st.local.add(p)
        if rest_param:
            st.local.add(rest_param)

        # Collect all variables assigned in the function body
        assigned = set()
        self._collect_assignments(body, assigned)
        st.local.update(assigned)

        # Collect all variables referenced in the function body
        referenced = set()
        self._collect_references(body, referenced)

        # Variables that are referenced but not local are closures
        for name in referenced:
            if name not in st.local:
                st.closure.add(name)

        return st

    def _collect_assignments(self, body, assigned):
        """Walk a statement list and collect all assigned variable names."""
        for stmt in body:
            if isinstance(stmt, VarDecl):
                assigned.add(stmt.name)
            elif isinstance(stmt, AssignStmt):
                if isinstance(stmt.target, Variable):
                    assigned.add(stmt.target.name)
            elif isinstance(stmt, (FuncDef,)):
                pass  # Nested function has its own scope
            elif isinstance(stmt, (IfStmt,)):
                self._collect_assignments(stmt.then_body, assigned)
                for _, elif_body in stmt.else_body:
                    self._collect_assignments(elif_body, assigned)
            elif isinstance(stmt, (ForInStmt, LoopStmt, DoWhileStmt, SkipStmt)):
                self._collect_assignments(stmt.body, assigned)
            elif isinstance(stmt, SwitchStmt):
                for _, case_body in stmt.cases:
                    self._collect_assignments(case_body, assigned)
                self._collect_assignments(stmt.default_body, assigned)
            elif isinstance(stmt, TryStmt):
                self._collect_assignments(stmt.try_body, assigned)
                self._collect_assignments(stmt.catch_body, assigned)
            elif isinstance(stmt, DestructureDecl):
                for name in stmt.names:
                    if isinstance(name, str):
                        assigned.add(name)
                    elif isinstance(name, tuple):
                        for sn in name[1]:
                            assigned.add(sn)

    def _collect_references(self, body, referenced):
        """Walk a statement list and collect all referenced variable names."""
        for stmt in body:
            if isinstance(stmt, (VarDecl,)):
                self._collect_refs_expr(stmt.value, referenced)
            elif isinstance(stmt, AssignStmt):
                self._collect_refs_expr(stmt.value, referenced)
                if isinstance(stmt.target, (DotAccess, IndexAccess)):
                    self._collect_refs_expr(stmt.target, referenced)
            elif isinstance(stmt, (FuncDef,)):
                pass  # Nested function, own scope
            elif isinstance(stmt, IfStmt):
                self._collect_refs_expr(stmt.condition, referenced)
                self._collect_references(stmt.then_body, referenced)
                for cond, elif_body in stmt.else_body:
                    if cond:
                        self._collect_refs_expr(cond, referenced)
                    self._collect_references(elif_body, referenced)
            elif isinstance(stmt, (ForInStmt,)):
                self._collect_refs_expr(stmt.iterable, referenced)
                self._collect_references(stmt.body, referenced)
            elif isinstance(stmt, (LoopStmt, DoWhileStmt)):
                self._collect_refs_expr(stmt.condition, referenced)
                self._collect_references(stmt.body, referenced)
            elif isinstance(stmt, (SkipStmt,)):
                self._collect_refs_expr(stmt.condition, referenced)
                self._collect_references(stmt.body, referenced)
            elif isinstance(stmt, SwitchStmt):
                self._collect_refs_expr(stmt.expr, referenced)
                for _, case_body in stmt.cases:
                    self._collect_references(case_body, referenced)
                self._collect_references(stmt.default_body, referenced)
            elif isinstance(stmt, TryStmt):
                self._collect_references(stmt.try_body, referenced)
                self._collect_references(stmt.catch_body, referenced)
            elif isinstance(stmt, ReturnStmt):
                self._collect_refs_expr(stmt.value, referenced)
            elif isinstance(stmt, ThrowStmt):
                self._collect_refs_expr(stmt.value, referenced)
            elif isinstance(stmt, SureStmt):
                self._collect_refs_expr(stmt.condition, referenced)
            elif isinstance(stmt, FuncCall):
                self._collect_refs_expr(stmt, referenced)
            else:
                self._collect_refs_expr(stmt, referenced)

    def _collect_refs_expr(self, expr, referenced):
        """Walk an expression tree and collect all Variable references."""
        if expr is None:
            return
        if isinstance(expr, Variable):
            referenced.add(expr.name)
        elif isinstance(expr, BinaryOp):
            self._collect_refs_expr(expr.left, referenced)
            self._collect_refs_expr(expr.right, referenced)
        elif isinstance(expr, UnaryOp):
            self._collect_refs_expr(expr.operand, referenced)
        elif isinstance(expr, LogicalOp):
            self._collect_refs_expr(expr.left, referenced)
            self._collect_refs_expr(expr.right, referenced)
        elif isinstance(expr, FuncCall):
            self._collect_refs_expr(expr.name, referenced)
            for arg in expr.args:
                self._collect_refs_expr(arg, referenced)
        elif isinstance(expr, DotAccess):
            self._collect_refs_expr(expr.object, referenced)
        elif isinstance(expr, IndexAccess):
            self._collect_refs_expr(expr.object, referenced)
            self._collect_refs_expr(expr.index, referenced)
        elif isinstance(expr, SliceAccess):
            self._collect_refs_expr(expr.object, referenced)
            if expr.start:
                self._collect_refs_expr(expr.start, referenced)
            if expr.end:
                self._collect_refs_expr(expr.end, referenced)
        elif isinstance(expr, InExpr):
            self._collect_refs_expr(expr.left, referenced)
            self._collect_refs_expr(expr.right, referenced)
        elif isinstance(expr, NullCoalesce):
            self._collect_refs_expr(expr.left, referenced)
            self._collect_refs_expr(expr.right, referenced)
        elif isinstance(expr, TernaryExpr):
            self._collect_refs_expr(expr.condition, referenced)
            self._collect_refs_expr(expr.then_expr, referenced)
            self._collect_refs_expr(expr.else_expr, referenced)
        elif isinstance(expr, PipeExpr):
            self._collect_refs_expr(expr.left, referenced)
            self._collect_refs_expr(expr.right, referenced)
        elif isinstance(expr, RangeExpr):
            self._collect_refs_expr(expr.start, referenced)
            self._collect_refs_expr(expr.end, referenced)
        elif isinstance(expr, OptionalChain):
            self._collect_refs_expr(expr.object, referenced)
        elif isinstance(expr, ListCompExpr):
            self._collect_refs_expr(expr.expr, referenced)
            self._collect_refs_expr(expr.iterable, referenced)
            if expr.condition:
                self._collect_refs_expr(expr.condition, referenced)
        elif isinstance(expr, ChainedCompare):
            for op in expr.operands:
                self._collect_refs_expr(op, referenced)
        elif isinstance(expr, ListLiteral):
            for el in expr.elements:
                self._collect_refs_expr(el, referenced)
        elif isinstance(expr, DictLiteral):
            for v in expr.pairs.values():
                self._collect_refs_expr(v, referenced)
        elif isinstance(expr, SetLiteral):
            for el in expr.elements:
                self._collect_refs_expr(el, referenced)
        elif isinstance(expr, InterpolatedString):
            for part in expr.parts:
                if isinstance(part, tuple):
                    self._collect_refs_expr(part[0], referenced)
                elif not isinstance(part, Literal):
                    self._collect_refs_expr(part, referenced)
        elif isinstance(expr, NewExpr):
            for arg in expr.args:
                self._collect_refs_expr(arg, referenced)
        elif isinstance(expr, ExpandExpr):
            self._collect_refs_expr(expr.expr, referenced)
        elif isinstance(expr, AwaitExpr):
            self._collect_refs_expr(expr.value, referenced)
        # Literal, ThisExpr, LambdaExpr, RegexLiteral — no variable references

    def parse_return_stmt(self):
        self.eat(TokenType.RET); val = self.parse_expression()
        self.optional_semicolon(); return ReturnStmt(val)

    def parse_sure_stmt(self):
        self.eat(TokenType.SURE); cond = self.parse_expression()
        msg = None
        if self.match(TokenType.COMMA):
            msg = self.current_token.value if self.current_token.type == TokenType.STRING else None
            if msg is not None: self.eat(TokenType.STRING)
        self.optional_semicolon(); return SureStmt(cond, msg)

    def parse_spawn(self):
        self.eat(TokenType.SPAWN)
        expr = self.parse_expression()
        self.optional_semicolon()
        return SpawnStmt(expr, None)

    def parse_expr_stmt(self):
        expr = self.parse_expression(); self.optional_semicolon(); return expr

    def parse_expression(self): return self.parse_pipe()

    def parse_pipe(self):
        left = self.parse_ternary()
        while self.match(TokenType.PIPE): left = PipeExpr(left, self.parse_ternary())
        return left

    def parse_ternary(self):
        cond = self.parse_null_coalesce()
        if self.match(TokenType.QUESTION):
            t = self.parse_expression(); self.eat(TokenType.COLON); e = self.parse_expression()
            return TernaryExpr(cond, t, e)
        return cond

    def parse_null_coalesce(self):
        left = self.parse_logical()
        while self.match(TokenType.NULL_COALESCE): left = NullCoalesce(left, self.parse_logical())
        return left

    def parse_logical(self):
        left = self.parse_in_expr()
        while self.current_token.type in (TokenType.AND, TokenType.OR):
            op = 'and' if self.current_token.value == '+and' else self.current_token.value
            self.eat(self.current_token.type); left = LogicalOp(left, op, self.parse_in_expr())
        return left

    def parse_in_expr(self):
        left = self.parse_bitwise()
        negated = False
        if self.match(TokenType.NOT):
            if self.current_token.type == TokenType.IN: negated = True
            else: return UnaryOp('not', left)
        if self.match(TokenType.IN) or (negated and self.match(TokenType.IN)):
            return InExpr(left, self.parse_bitwise(), negated=negated)
        return left

    def parse_bitwise(self):
        left = self.parse_chained_comparison()
        while self.current_token.type in (TokenType.BIT_AND, TokenType.BIT_OR, TokenType.BIT_XOR,
                                           TokenType.LSHIFT, TokenType.RSHIFT):
            op = self.current_token.value; self.eat(self.current_token.type)
            left = BinaryOp(left, op, self.parse_chained_comparison())
        return left

    def parse_chained_comparison(self):
        left = self.parse_range()
        ops = []; operands = [left]
        while self.current_token.type in (TokenType.GT, TokenType.LT, TokenType.GE,
                                           TokenType.LE, TokenType.EQ, TokenType.NEQ):
            ops.append(self.current_token.value); self.eat(self.current_token.type)
            operands.append(self.parse_range())
        if len(ops) == 0: return left
        if len(ops) == 1: return BinaryOp(operands[0], ops[0], operands[1])
        return ChainedCompare(ops, operands)

    def parse_range(self):
        left = self.parse_term()
        if self.match(TokenType.RANGE): return RangeExpr(left, self.parse_term())
        return left

    def parse_term(self):
        left = self.parse_factor()
        while self.current_token.type in (TokenType.PLUS, TokenType.MINUS):
            op = self.current_token.value; self.eat(self.current_token.type)
            left = BinaryOp(left, op, self.parse_factor())
        return left

    def parse_factor(self):
        left = self.parse_unary()
        while self.current_token.type in (TokenType.STAR, TokenType.SLASH, TokenType.PERCENT,
                                           TokenType.POWER, TokenType.FLOOR_DIV):
            op = self.current_token.value; self.eat(self.current_token.type)
            left = BinaryOp(left, op, self.parse_unary())
        return left

    def parse_unary(self):
        t = self.current_token
        if t.type in (TokenType.BANG, TokenType.MINUS, TokenType.BIT_NOT):
            self.eat(t.type); return UnaryOp(t.value, self.parse_unary())
        if t.type == TokenType.NOT: self.eat(TokenType.NOT); return UnaryOp('not', self.parse_unary())
        if t.type == TokenType.AWAIT: self.eat(TokenType.AWAIT); return AwaitExpr(self.parse_unary())
        if t.type == TokenType.EXPAND: self.eat(TokenType.EXPAND); return ExpandExpr(self.parse_unary())
        return self.parse_postfix()

    def parse_postfix(self):
        result = self.parse_primary()
        while True:
            if self.current_token.type == TokenType.QUESTION_DOT:
                self.eat(TokenType.QUESTION_DOT); result = OptionalChain(result, self.parse_primary())
            elif self.current_token.type == TokenType.LBRACKET:
                self.eat(TokenType.LBRACKET)
                if self.match(TokenType.COLON):
                    end = self.parse_expression() if self.current_token.type != TokenType.RBRACKET else None
                    self.eat(TokenType.RBRACKET); result = SliceAccess(result, Literal(0), end)
                else:
                    start = self.parse_expression()
                    if self.match(TokenType.COLON):
                        end = self.parse_expression() if self.current_token.type != TokenType.RBRACKET else None
                        self.eat(TokenType.RBRACKET); result = SliceAccess(result, start, end)
                    else:
                        self.eat(TokenType.RBRACKET); result = IndexAccess(result, start)
            elif self.current_token.type == TokenType.DOT:
                self.eat(TokenType.DOT); attr = self.current_token.value; self.eat(TokenType.IDENTIFIER)
                if self.current_token.type == TokenType.LPAREN:
                    self.eat(TokenType.LPAREN); args = self.parse_args()
                    self.eat(TokenType.RPAREN); result = FuncCall(DotAccess(result, attr), args)
                else: result = DotAccess(result, attr)
            elif self.current_token.type == TokenType.LPAREN:
                self.eat(TokenType.LPAREN); args = self.parse_args()
                self.eat(TokenType.RPAREN); result = FuncCall(result, args)
            else: break
        return result

    def parse_primary(self):
        t = self.current_token
        if t.type == TokenType.NULL: self.eat(TokenType.NULL); return Literal(None)
        if t.type == TokenType.TRUE: self.eat(TokenType.TRUE); return Literal(True)
        if t.type == TokenType.FALSE: self.eat(TokenType.FALSE); return Literal(False)
        if t.type == TokenType.THIS: self.eat(TokenType.THIS); return ThisExpr()
        if t.type == TokenType.NEW: return self.parse_new_expr()
        if t.type == TokenType.NUMBER: self.eat(TokenType.NUMBER); return Literal(t.value)
        if t.type == TokenType.STRING: return self.parse_string_or_interpolation(t)
        if t.type == TokenType.REGEX:
            pattern, flags = t.value
            self.eat(TokenType.REGEX)
            return RegexLiteral(pattern, flags)
        if t.type == TokenType.IDENTIFIER:
            name = t.value; self.eat(TokenType.IDENTIFIER)
            if self.current_token.type == TokenType.LPAREN:
                self.eat(TokenType.LPAREN); args = self.parse_args()
                self.eat(TokenType.RPAREN); return FuncCall(Variable(name), args)
            return Variable(name)
        if t.type == TokenType.LBRACKET: return self.parse_list_or_listcomp()
        if t.type == TokenType.LBRACE: return self.parse_dict_or_set()
        if t.type == TokenType.LPAREN: return self.parse_tuple_or_expr()
        if t.type == TokenType.FUN: return self.parse_lambda()
        col = t.column
        self.error(f"Cannot parse: {t.value} (token type: {t.type.name})")

    def parse_lambda(self):
        self.eat(TokenType.FUN)
        params = []
        if self.match(TokenType.LPAREN):
            self.eat(TokenType.RPAREN)
        elif self.current_token.type == TokenType.IDENTIFIER:
            params.append(self.current_token.value); self.eat(TokenType.IDENTIFIER)
            while self.match(TokenType.COMMA): params.append(self.current_token.value); self.eat(TokenType.IDENTIFIER)
        self.eat(TokenType.COLON)
        body, fin_consumed, _ = self._parse_block()
        if not fin_consumed:
            self.eat(TokenType.FIN)
        self.optional_semicolon(); return LambdaExpr(params, body)

    def parse_new_expr(self):
        self.eat(TokenType.NEW); cn = self.current_token.value; self.eat(TokenType.IDENTIFIER)
        self.eat(TokenType.LPAREN); args = self.parse_args(); self.eat(TokenType.RPAREN)
        return NewExpr(cn, args)

    def parse_string_or_interpolation(self, t):
        raw = t.value; self.eat(TokenType.STRING)
        if '{' not in raw: return Literal(raw)
        parts = []; cur = ''; i = 0
        while i < len(raw):
            if raw[i] == '{' and i + 1 < len(raw):
                if raw[i + 1] == '{': cur += '{'; i += 2; continue
                if cur: parts.append(Literal(cur)); cur = ''
                i += 1; es = ''; depth = 1; fmt = ''
                while i < len(raw) and depth > 0:
                    if raw[i] == '{': depth += 1
                    elif raw[i] == '}': depth -= 1
                    if depth == 0: break
                    if depth == 1 and raw[i] == ':':
                        i += 1
                        while i < len(raw) and depth > 0:
                            if raw[i] == '{': depth += 1
                            elif raw[i] == '}': depth -= 1
                            if depth == 0: break
                            fmt += raw[i]
                            i += 1
                        break
                    else:
                        es += raw[i]
                    i += 1
                if es.strip():
                    sl = Lexer(es); sp = Parser(sl)
                    parts.append((sp.parse_expression(), None if fmt == '' else fmt))
                i += 1
            elif raw[i] == '}' and i + 1 < len(raw) and raw[i + 1] == '}': cur += '}'; i += 2
            else: cur += raw[i]; i += 1
        if cur: parts.append(Literal(cur))
        return InterpolatedString(parts)

    def parse_list_or_listcomp(self):
        saved = (self.lexer.pos, self.lexer.line, self.lexer.col, self.lexer.current_char, self.current_token)
        self.eat(TokenType.LBRACKET)
        if self.current_token.type == TokenType.RBRACKET: self.eat(TokenType.RBRACKET); return ListLiteral([])
        first = self.parse_expression()
        if self.match(TokenType.FOR):
            var = self.current_token.value; self.eat(TokenType.IDENTIFIER)
            self.eat(TokenType.IN); it = self.parse_expression()
            cond = None
            if self.match(TokenType.IF): cond = self.parse_expression()
            self.eat(TokenType.RBRACKET); return ListCompExpr(first, var, it, cond)
        if isinstance(first, ListLiteral):
            self.eat(TokenType.RBRACKET); return first
        self._restore(saved)
        self.eat(TokenType.LBRACKET)
        if self.current_token.type == TokenType.RBRACKET: self.eat(TokenType.RBRACKET); return ListLiteral([])
        elems = [self.parse_expression()]
        while self.match(TokenType.COMMA): elems.append(self.parse_expression())
        self.eat(TokenType.RBRACKET); return ListLiteral(elems)

    def parse_dict_or_set(self):
        self.eat(TokenType.LBRACE)
        if self.current_token.type == TokenType.RBRACE: self.eat(TokenType.RBRACE); return DictLiteral({})
        saved = (self.lexer.pos, self.lexer.line, self.lexer.col, self.lexer.current_char, self.current_token)
        first = self.current_token
        if first.type in (TokenType.IDENTIFIER, TokenType.STRING):
            self.eat(first.type)
            if self.current_token.type == TokenType.COLON:
                self._restore(saved); return self._finish_dict()
            self._restore(saved)
        return self._finish_set()

    def _finish_dict(self):
        pairs = {}
        k = self.parse_dict_key(); self.eat(TokenType.COLON); v = self.parse_expression(); pairs[k] = v
        while self.match(TokenType.COMMA):
            if self.current_token.type == TokenType.RBRACE: break
            k = self.parse_dict_key(); self.eat(TokenType.COLON); v = self.parse_expression(); pairs[k] = v
        self.eat(TokenType.RBRACE); return DictLiteral(pairs)

    def _finish_set(self):
        elems = [self.parse_expression()]
        while self.match(TokenType.COMMA):
            if self.current_token.type == TokenType.RBRACE: break
            elems.append(self.parse_expression())
        self.eat(TokenType.RBRACE); return SetLiteral(elems)

    def parse_dict_key(self):
        if self.current_token.type == TokenType.IDENTIFIER: k = self.current_token.value; self.eat(TokenType.IDENTIFIER); return k
        if self.current_token.type == TokenType.STRING: k = self.current_token.value; self.eat(TokenType.STRING); return k
        self.error("Dict key must be identifier or string")

    def parse_tuple_or_expr(self):
        self.eat(TokenType.LPAREN)
        if self.current_token.type == TokenType.RPAREN: self.eat(TokenType.RPAREN); return ListLiteral([])
        first = self.parse_expression()
        if self.match(TokenType.COMMA):
            elems = [first]
            while self.current_token.type != TokenType.RPAREN:
                elems.append(self.parse_expression())
                if not self.match(TokenType.COMMA): break
            self.eat(TokenType.RPAREN); return ListLiteral(elems)
        self.eat(TokenType.RPAREN); return first

    def parse_args(self):
        args = []
        if self.current_token.type == TokenType.RPAREN: return args
        if self.current_token.type == TokenType.IDENTIFIER:
            # Peek ahead: if next token is '=', it's a named parameter (not supported)
            saved = (self.lexer.pos, self.lexer.line, self.lexer.col, self.lexer.current_char, self.current_token)
            self.eat(TokenType.IDENTIFIER)
            if self.current_token.type == TokenType.ASSIGN:
                self._restore(saved)
                self.error(
                    f"Unexpected '=' in function call arguments",
                    "ViGo does not support named parameters. Use positional arguments instead."
                )
            self._restore(saved)
        args.append(self.parse_expression())
        while self.match(TokenType.COMMA):
            if self.current_token.type == TokenType.IDENTIFIER:
                saved = (self.lexer.pos, self.lexer.line, self.lexer.col, self.lexer.current_char, self.current_token)
                self.eat(TokenType.IDENTIFIER)
                if self.current_token.type == TokenType.ASSIGN:
                    self._restore(saved)
                    self.error(
                        f"Unexpected '=' in function call arguments",
                        "ViGo does not support named parameters. Use positional arguments instead."
                    )
                self._restore(saved)
            args.append(self.parse_expression())
        return args