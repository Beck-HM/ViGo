from enum import Enum, auto


class TokenType(Enum):
    IF = auto(); EL = auto(); EIF = auto(); TS = auto(); FIN = auto()
    FUN = auto(); AS = auto(); RET = auto(); AND = auto(); OR = auto()
    NOT = auto(); LOOP = auto(); FOR = auto(); IN = auto()
    BREAK = auto(); CONTINUE = auto(); LOAD = auto()
    NULL = auto(); TRUE = auto(); FALSE = auto()
    CLASS = auto(); NEW = auto(); EXTENDS = auto(); THIS = auto()
    TRY = auto(); CATCH = auto(); THROW = auto()
    AWAIT = auto()
    SWITCH = auto(); CASE = auto(); DEFAULT = auto()
    ENUM = auto()
    CONST = auto()
    STATIC = auto(); ABSTRACT = auto(); INTERFACE = auto()
    GO = auto(); SKIP = auto(); SURE = auto()
    NOT_IN = auto()
    POWER = auto(); FLOOR_DIV = auto()

    NUMBER = auto(); STRING = auto(); IDENTIFIER = auto()

    PLUS = auto(); MINUS = auto(); STAR = auto(); SLASH = auto()
    PERCENT = auto(); EQ = auto(); NEQ = auto()
    LT = auto(); GT = auto(); LE = auto(); GE = auto()
    BANG = auto(); ASSIGN = auto()
    PLUS_ASSIGN = auto(); MINUS_ASSIGN = auto()
    STAR_ASSIGN = auto(); SLASH_ASSIGN = auto(); PERCENT_ASSIGN = auto()
    DOT = auto(); QUESTION = auto(); QUESTION_DOT = auto()
    NULL_COALESCE = auto()
    PIPE = auto(); RANGE = auto()
    EXPAND = auto()
    BIT_AND = auto(); BIT_OR = auto(); BIT_XOR = auto()
    BIT_NOT = auto(); LSHIFT = auto(); RSHIFT = auto()

    LPAREN = auto(); RPAREN = auto()
    LBRACKET = auto(); RBRACKET = auto()
    LBRACE = auto(); RBRACE = auto()
    COLON = auto(); SEMICOLON = auto(); COMMA = auto()
    EOF = auto()


class Token:
    def __init__(self, type_, value, line, col):
        self.type = type_
        self.value = value
        self.line = line
        self.column = col

    def __repr__(self):
        return f"Token({self.type.name}, '{self.value}', line={self.line}, col={self.column})"

    def __eq__(self, other):
        if isinstance(other, Token):
            return self.type == other.type and self.value == other.value
        return False


KEYWORDS = {
    'if': TokenType.IF, 'el': TokenType.EL, 'eif': TokenType.EIF,
    'ts': TokenType.TS, 'Fin': TokenType.FIN,
    'Fun': TokenType.FUN, 'as': TokenType.AS, 'Ret': TokenType.RET,
    'loop': TokenType.LOOP, 'for': TokenType.FOR, 'in': TokenType.IN,
    'break': TokenType.BREAK, 'continue': TokenType.CONTINUE,
    'load': TokenType.LOAD,
    'and': TokenType.AND, 'or': TokenType.OR, 'not': TokenType.NOT,
    'null': TokenType.NULL, 'true': TokenType.TRUE, 'false': TokenType.FALSE,
    'ok': TokenType.TRUE, 'no': TokenType.FALSE,
    'class': TokenType.CLASS, 'new': TokenType.NEW,
    'extends': TokenType.EXTENDS, 'this': TokenType.THIS,
    'try': TokenType.TRY, 'catch': TokenType.CATCH, 'throw': TokenType.THROW,
    'await': TokenType.AWAIT,
    'switch': TokenType.SWITCH, 'case': TokenType.CASE, 'default': TokenType.DEFAULT,
    'enum': TokenType.ENUM, 'const': TokenType.CONST,
    'static': TokenType.STATIC, 'abstract': TokenType.ABSTRACT,
    'interface': TokenType.INTERFACE,
    'go': TokenType.GO, 'skip': TokenType.SKIP, 'sure': TokenType.SURE,
}