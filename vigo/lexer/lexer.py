from .tokens import TokenType, Token, KEYWORDS


class Lexer:
    def __init__(self, source_code):
        self.source = source_code
        self.pos = 0
        self.line = 1
        self.col = 1
        self.current_char = self.source[0] if self.source else None

    def error(self, msg):
        raise Exception(f"Lexer error [Line{self.line}, Column{self.col}]: {msg}")

    def advance(self):
        if self.current_char == '\n':
            self.line += 1
            self.col = 0
        self.pos += 1
        if self.pos >= len(self.source):
            self.current_char = None
        else:
            self.current_char = self.source[self.pos]
            self.col += 1

    def peek(self):
        p = self.pos + 1
        return None if p >= len(self.source) else self.source[p]

    def skip_whitespace_and_comments(self):
        while self.current_char is not None:
            if self.current_char in ' \t\r\n':
                self.advance()
            elif self.current_char == '#':
                if self.peek() == '*':
                    self.advance()
                    self.advance()
                    while self.current_char is not None:
                        if self.current_char == '*' and self.peek() == '#':
                            self.advance()
                            self.advance()
                            break
                        self.advance()
                else:
                    while self.current_char is not None and self.current_char != '\n':
                        self.advance()
            else:
                break

    def read_identifier(self):
        start_col = self.col
        result = ''
        while self.current_char is not None and (self.current_char.isalnum() or self.current_char == '_'):
            result += self.current_char
            self.advance()
        return Token(KEYWORDS.get(result, TokenType.IDENTIFIER), result, self.line, start_col)

    def read_number(self):
        start_col = self.col
        result = ''
        has_dot = False
        while self.current_char is not None and (self.current_char.isdigit() or self.current_char == '.'):
            if self.current_char == '.':
                if has_dot:
                    break
                if self.peek() == '.':
                    break
                has_dot = True
            result += self.current_char
            self.advance()
        return Token(TokenType.NUMBER, float(result) if has_dot else int(result), self.line, start_col)

    def read_string(self):
        start_col = self.col
        start_line = self.line
        self.advance()
        result = ''
        while self.current_char is not None and self.current_char != '"':
            if self.current_char == '\\':
                self.advance()
                esc = {'n': '\n', 't': '\t', '"': '"', '\\': '\\', '{': '{'}
                result += esc.get(self.current_char, self.current_char)
            else:
                result += self.current_char
            self.advance()
        if self.current_char != '"':
            self.error("String missing closing quote")
        self.advance()
        return Token(TokenType.STRING, result, start_line, start_col)

    def read_multiline_string(self):
        """Read \"\"\"...\"\"\" Multiline string"""
        start_col = self.col
        start_line = self.line
        self.advance()  # Skip first "
        self.advance()  # Skip second "
        self.advance()  # Skip third "
        result = ''
        while self.current_char is not None:
            # Check if three consecutive "
            if self.current_char == '"' and self.peek() == '"':
                # Peek next
                p2 = self.pos + 2
                if p2 < len(self.source) and self.source[p2] == '"':
                    self.advance()  # Skip first "
                    self.advance()  # Skip second "
                    self.advance()  # Skip third "
                    break
            if self.current_char == '\\':
                self.advance()
                esc = {'n': '\n', 't': '\t', '"': '"', '\\': '\\'}
                result += esc.get(self.current_char, self.current_char)
            else:
                result += self.current_char
            self.advance()
        return Token(TokenType.STRING, result, start_line, start_col)

    def get_next_token(self):
        self.skip_whitespace_and_comments()
        if self.current_char is None:
            return Token(TokenType.EOF, None, self.line, self.col)

        c = self.current_char

        # Multiline string """
        if c == '"' and self.peek() == '"':
            p2 = self.pos + 2
            if p2 < len(self.source) and self.source[p2] == '"':
                return self.read_multiline_string()

        if c == '|':
            sc = self.col; self.advance()
            if self.current_char == '>': self.advance(); return Token(TokenType.PIPE, '|>', self.line, sc)
            if self.current_char == '|': self.advance(); return Token(TokenType.OR, 'or', self.line, sc)
            return Token(TokenType.BIT_OR, '|', self.line, sc)

        if c == '.':
            sc = self.col
            self.advance()
            if self.current_char == '.':
                self.advance()
                if self.current_char == '.':
                    self.advance()
                    return Token(TokenType.EXPAND, '...', self.line, sc)
                return Token(TokenType.RANGE, '..', self.line, sc)
            return Token(TokenType.DOT, '.', self.line, sc)

        if c == '?' and self.peek() == '.':
            sc = self.col; self.advance(); self.advance()
            return Token(TokenType.QUESTION_DOT, '?.', self.line, sc)

        if c == '?' and self.peek() == '?':
            sc = self.col; self.advance(); self.advance()
            return Token(TokenType.NULL_COALESCE, '??', self.line, sc)

        if c == '*':
            sc = self.col; self.advance()
            if self.current_char == '=': self.advance(); return Token(TokenType.STAR_ASSIGN, '*=', self.line, sc)
            if self.current_char == '*': self.advance(); return Token(TokenType.POWER, '**', self.line, sc)
            return Token(TokenType.STAR, '*', self.line, sc)

        if c == '/':
            sc = self.col; self.advance()
            if self.current_char == '=': self.advance(); return Token(TokenType.SLASH_ASSIGN, '/=', self.line, sc)
            if self.current_char == '/': self.advance(); return Token(TokenType.FLOOR_DIV, '//', self.line, sc)
            return Token(TokenType.SLASH, '/', self.line, sc)

        if c == '+':
            sc = self.col; self.advance()
            if self.current_char == '=': self.advance(); return Token(TokenType.PLUS_ASSIGN, '+=', self.line, sc)
            if self.current_char == 'a':
                saved = (self.pos, self.line, self.col, self.current_char)
                m = ''
                while self.current_char and self.current_char.isalpha():
                    m += self.current_char; self.advance()
                if m == 'and': return Token(TokenType.AND, '+and', self.line, sc)
                self.pos, self.line, self.col, self.current_char = saved
                return Token(TokenType.PLUS, '+', self.line, sc)
            return Token(TokenType.PLUS, '+', self.line, sc)

        if c == '-':
            sc = self.col; self.advance()
            if self.current_char == '=': self.advance(); return Token(TokenType.MINUS_ASSIGN, '-=', self.line, sc)
            return Token(TokenType.MINUS, '-', self.line, sc)

        if c == '%':
            sc = self.col; self.advance()
            if self.current_char == '=': self.advance(); return Token(TokenType.PERCENT_ASSIGN, '%=', self.line, sc)
            return Token(TokenType.PERCENT, '%', self.line, sc)

        if c == '&':
            sc = self.col; self.advance()
            if self.current_char == '&': self.advance(); return Token(TokenType.AND, 'and', self.line, sc)
            return Token(TokenType.BIT_AND, '&', self.line, sc)

        if c == '^':
            sc = self.col; self.advance(); return Token(TokenType.BIT_XOR, '^', self.line, sc)

        if c == '~':
            sc = self.col; self.advance(); return Token(TokenType.BIT_NOT, '~', self.line, sc)

        if c == '<':
            sc = self.col; self.advance()
            if self.current_char == '=': self.advance(); return Token(TokenType.LE, '<=', self.line, sc)
            if self.current_char == '<': self.advance(); return Token(TokenType.LSHIFT, '<<', self.line, sc)
            return Token(TokenType.LT, '<', self.line, sc)

        if c == '>':
            sc = self.col; self.advance()
            if self.current_char == '=': self.advance(); return Token(TokenType.GE, '>=', self.line, sc)
            if self.current_char == '>': self.advance(); return Token(TokenType.RSHIFT, '>>', self.line, sc)
            return Token(TokenType.GT, '>', self.line, sc)

        if c == '=':
            sc = self.col; self.advance()
            if self.current_char == '=': self.advance(); return Token(TokenType.EQ, '==', self.line, sc)
            return Token(TokenType.ASSIGN, '=', self.line, sc)

        if c == '!':
            sc = self.col; self.advance()
            if self.current_char == '=': self.advance(); return Token(TokenType.NEQ, '!=', self.line, sc)
            return Token(TokenType.BANG, '!', self.line, sc)

        if c == '?':
            sc = self.col; self.advance(); return Token(TokenType.QUESTION, '?', self.line, sc)

        single = {
            '(': TokenType.LPAREN, ')': TokenType.RPAREN,
            '[': TokenType.LBRACKET, ']': TokenType.RBRACKET,
            '{': TokenType.LBRACE, '}': TokenType.RBRACE,
            ':': TokenType.COLON, ';': TokenType.SEMICOLON, ',': TokenType.COMMA,
        }
        if c in single:
            sc = self.col; self.advance(); return Token(single[c], c, self.line, sc)

        if c.isalpha() or c == '_': return self.read_identifier()
        if c.isdigit(): return self.read_number()
        if c == '"': return self.read_string()

        self.error(f"Unrecognized character '{c}'")

    def tokenize(self):
        tokens = []
        while True:
            t = self.get_next_token()
            tokens.append(t)
            if t.type == TokenType.EOF:
                break
        return tokens