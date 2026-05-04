"""ViGo Runtime - Control flow block execution"""
from .environment import Environment
from .errors import ViGoError, BreakException, ContinueException, ReturnException


# ── Block-wide helpers ──

def eval_block(interp, stmts, env):
    """Execute a list of statements in sequence. Returns the last result."""
    result = None
    for s in stmts:
        result = interp.eval(s, env)
    return result


def is_truthy(v):
    """Determine if a value is truthy in ViGo."""
    if v is None:
        return False
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    if isinstance(v, str):
        return v != ''
    if isinstance(v, (list, tuple, dict, set)):
        return len(v) > 0
    return True


# ── Control flow blocks ──

def eval_if(interp, node, env):
    """Execute an if / eif / el block."""
    if is_truthy(interp.eval(node.condition, env)):
        return eval_block(interp, node.then_body, env)
    for bc, bb in node.else_body:
        if bc is None or is_truthy(interp.eval(bc, env)):
            return eval_block(interp, bb, env)
    return None


def eval_for_in(interp, node, env):
    """Execute a for-in loop."""
    it = interp.eval(node.iterable, env)
    result = None
    items = it if isinstance(it, (list, str)) else (it.keys() if isinstance(it, dict) else [])
    for item in items:
        env.define(node.var_name, item)
        try:
            result = eval_block(interp, node.body, env)
        except BreakException:
            break
        except ContinueException:
            continue
    return result


def eval_loop(interp, node, env):
    """Execute a while-style loop (loop ... Fin)."""
    result = None
    while is_truthy(interp.eval(node.condition, env)):
        try:
            result = eval_block(interp, node.body, env)
        except BreakException:
            break
        except ContinueException:
            continue
    return result


def eval_do_while(interp, node, env):
    """Execute a do-while loop (go ... Fin loop condition)."""
    result = None
    while True:
        try:
            result = eval_block(interp, node.body, env)
        except BreakException:
            break
        except ContinueException:
            continue
        if not is_truthy(interp.eval(node.condition, env)):
            break
    return result


def eval_switch(interp, node, env):
    """Execute a switch block with range and default support."""
    val = interp.eval(node.expr, env)
    for cv, cb in node.cases:
        if isinstance(cv, tuple) and len(cv) == 3 and cv[0] == 'range':
            if cv[1] <= val <= cv[2]:
                return eval_block(interp, cb, env)
        elif val == cv:
            return eval_block(interp, cb, env)
    if node.default_body:
        return eval_block(interp, node.default_body, env)
    return None


def eval_try(interp, node, env):
    """Execute a try/catch block."""
    try:
        return eval_block(interp, node.try_body, env)
    except ReturnException:
        raise
    except ViGoError as e:
        if node.catch_var:
            env.variables[node.catch_var] = str(e).replace("ViGo Error: ", "")
        if node.catch_body:
            return eval_block(interp, node.catch_body, env)
    except Exception as e:
        if node.catch_var:
            env.variables[node.catch_var] = str(e).replace("ViGo Error: ", "")
        if node.catch_body:
            return eval_block(interp, node.catch_body, env)


def eval_listcomp(interp, node, env):
    """Execute a list comprehension."""
    it = interp.eval(node.iterable, env)
    result = []
    items = it if isinstance(it, (list, str)) else (it.keys() if isinstance(it, dict) else [])
    for item in items:
        ie = Environment(env)
        ie.define(node.var, item)
        if node.condition is None or is_truthy(interp.eval(node.condition, ie)):
            result.append(interp.eval(node.expr, ie))
    return result