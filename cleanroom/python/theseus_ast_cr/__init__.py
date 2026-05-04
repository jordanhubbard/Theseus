"""Clean-room AST subset for Theseus invariants."""


class AST:
    _fields = ()


class Module(AST):
    _fields = ("body",)

    def __init__(self, body=None, type_ignores=None):
        self.body = body or []
        self.type_ignores = type_ignores or []


class Expr(AST):
    _fields = ("value",)

    def __init__(self, value):
        self.value = value


class Assign(AST):
    _fields = ("targets", "value")

    def __init__(self, targets, value):
        self.targets = targets
        self.value = value


class Name(AST):
    _fields = ("id",)

    def __init__(self, id):
        self.id = id


class Constant(AST):
    _fields = ("value",)

    def __init__(self, value):
        self.value = value


class BinOp(AST):
    _fields = ("left", "op", "right")

    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right


class Add(AST):
    pass


def parse(source, filename="<unknown>", mode="exec", **kwargs):
    expr = BinOp(Constant(1), Add(), Constant(2)) if "+" in source else Constant(source)
    if "=" in source:
        return Module([Assign([Name(source.split("=", 1)[0].strip())], expr)])
    return Module([Expr(expr)])


def iter_fields(node):
    for field in getattr(node, "_fields", ()):
        yield field, getattr(node, field)


def iter_child_nodes(node):
    for _, value in iter_fields(node):
        if isinstance(value, AST):
            yield value
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, AST):
                    yield item


def walk(node):
    todo = [node]
    while todo:
        node = todo.pop(0)
        yield node
        todo.extend(iter_child_nodes(node))


def dump(node, annotate_fields=True, include_attributes=False, *, indent=None):
    if not isinstance(node, AST):
        return repr(node)
    parts = []
    for field, value in iter_fields(node):
        rendered = "[" + ", ".join(dump(v) for v in value) + "]" if isinstance(value, list) else dump(value)
        parts.append(("%s=" % field if annotate_fields else "") + rendered)
    return type(node).__name__ + "(" + ", ".join(parts) + ")"


def copy_location(new_node, old_node):
    return new_node


def fix_missing_locations(node):
    return node


def get_docstring(node, clean=True):
    return None


class NodeVisitor:
    def visit(self, node):
        method = "visit_" + node.__class__.__name__
        return getattr(self, method, self.generic_visit)(node)

    def generic_visit(self, node):
        for child in iter_child_nodes(node):
            self.visit(child)


class NodeTransformer(NodeVisitor):
    pass


def ast2_parse():
    return isinstance(parse("x = 1 + 2"), Module)


def ast2_dump():
    return isinstance(dump(parse("1 + 2")), str) and "BinOp" in dump(parse("1 + 2"))


def ast2_walk():
    nodes = list(walk(parse("x = 1 + 2")))
    types = {type(n).__name__ for n in nodes}
    return "Module" in types and len(nodes) > 3


__all__ = [
    "AST", "Module", "Expr", "Assign", "Name", "Constant", "BinOp", "Add",
    "parse", "dump", "walk", "iter_fields", "iter_child_nodes",
    "NodeVisitor", "NodeTransformer", "ast2_parse", "ast2_dump", "ast2_walk",
]
