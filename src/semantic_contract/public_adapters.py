"""Executable source adapters for the frozen Scorch public-patch study.

The adapters are deliberately small, dependency-free semantic models of the
changed source regions.  They do not execute Scorch, PyTorch, C++, or arbitrary
GitHub code.  Each admitted record has a separate prose proof connecting the
source diff to the model; this module checks the model and its negative controls.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations, product
import random
from typing import Any, Callable, Iterable, Sequence


# ---------------------------------------------------------------------------
# P01: exec/eval CIN construction -> direct constructor calls (72c55d...)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IVar:
    name: str

@dataclass(frozen=True)
class Access:
    tensor: str
    indices: tuple[str, ...]

    def __mul__(self, other: "Expr") -> "Mul":
        return Mul(self, other)

@dataclass(frozen=True)
class Mul:
    left: "Expr"
    right: "Expr"

    def __mul__(self, other: "Expr") -> "Mul":
        return Mul(self, other)

Expr = Access | Mul

@dataclass(frozen=True)
class Assign:
    lhs: Access
    rhs: Expr

@dataclass(frozen=True)
class Loop:
    index: str
    stmt: "Stmt"

Stmt = Assign | Loop

class TVar:
    """The relevant TensorVar overloads, with only observable AST state."""

    def __init__(self, name: str):
        self.name = name
        self.assignment: Assign | None = None

    @staticmethod
    def _indices(key: Any) -> tuple[str, ...]:
        xs = key if isinstance(key, tuple) else (key,)
        if not xs or not all(isinstance(x, IVar) for x in xs):
            raise TypeError("indices must be one or more IVar values")
        return tuple(x.name for x in xs)

    def __getitem__(self, key: Any) -> Access:
        return Access(self.name, self._indices(key))

    def __setitem__(self, key: Any, value: Expr) -> None:
        self.assignment = Assign(Access(self.name, self._indices(key)), value)

@dataclass(frozen=True)
class EinsumBuildSpec:
    operands: tuple[tuple[str, ...], ...]
    result: tuple[str, ...]
    schedule: tuple[str, ...]

    def validate(self) -> None:
        if not 1 <= len(self.operands) <= 4:
            raise ValueError("one to four operands")
        if not self.result or any(not x for x in self.operands):
            raise ValueError("the source region assumes non-scalar accesses")
        names = {x for op in self.operands for x in op} | set(self.result)
        if any(len(x) != 1 or not x.islower() for x in names):
            raise ValueError("controlled single-letter index names only")
        if len(set(self.schedule)) != len(self.schedule) or set(self.schedule) != names:
            raise ValueError("schedule must be a permutation of used names")

def _scope(spec: EinsumBuildSpec) -> tuple[list[TVar], TVar, dict[str, IVar]]:
    names = sorted(set(spec.schedule))
    return ([TVar(chr(ord("A") + i)) for i in range(len(spec.operands))],
            TVar("R"), {name: IVar(name) for name in names})

def build_cin_before(spec: EinsumBuildSpec) -> Stmt:
    """Faithful execution of the parent snippet's generated Python strings."""
    spec.validate()
    tensor_vars, result_tensor_var, index_var_dict = _scope(spec)
    input_index_strs = [list(x) for x in spec.operands]
    result_index_strs = list(spec.result)
    index_strs_by_schedule = list(spec.schedule)
    rhs = ""
    for i, _tensor_var in enumerate(tensor_vars):
        inside = ", ".join(
            [f'index_var_dict["{index_str}"]' for index_str in input_index_strs[i]]
        )
        rhs += f"tensor_vars[{i}][{inside}]"
        if i < len(tensor_vars) - 1:
            rhs += " * "
    lhs_inside = ", ".join(
        [f'index_var_dict["{index_str}"]' for index_str in result_index_strs]
    )
    code = f"result_tensor_var[{lhs_inside}] = {rhs}"
    local = {
        "tensor_vars": tensor_vars,
        "result_tensor_var": result_tensor_var,
        "index_var_dict": index_var_dict,
    }
    exec(code, {"__builtins__": {}}, local)
    if result_tensor_var.assignment is None:
        raise AssertionError("assignment was not created")
    rhs_text = "result_tensor_var.assignment"
    for index_str in index_strs_by_schedule[::-1]:
        rhs_text = f'Loop(index_var_dict["{index_str}"].name, {rhs_text})'
    return eval(rhs_text, {"__builtins__": {}, "Loop": Loop}, local)

def build_cin_after(spec: EinsumBuildSpec) -> Stmt:
    spec.validate()
    tensor_vars, result_tensor_var, index_var_dict = _scope(spec)
    rhs_expr: Expr | None = None
    for i, tensor_var in enumerate(tensor_vars):
        indices = [index_var_dict[s] for s in spec.operands[i]]
        access = tensor_var[indices[0]] if len(indices) == 1 else tensor_var[tuple(indices)]
        rhs_expr = access if rhs_expr is None else rhs_expr * access
    if rhs_expr is None:
        raise AssertionError("nonempty operands invariant")
    lhs_indices = [index_var_dict[s] for s in spec.result]
    lhs_key: Any = lhs_indices[0] if len(lhs_indices) == 1 else tuple(lhs_indices)
    result_tensor_var[lhs_key] = rhs_expr
    if result_tensor_var.assignment is None:
        raise AssertionError("assignment was not created")
    cin_stmt: Stmt = result_tensor_var.assignment
    for index_str in reversed(spec.schedule):
        cin_stmt = Loop(index_var_dict[index_str].name, cin_stmt)
    return cin_stmt

def mutate_cin(spec: EinsumBuildSpec, mutant: str) -> Stmt:
    """Plausible source-level negative controls for the direct construction."""
    spec.validate()
    tensor_vars, result_tensor_var, index_var_dict = _scope(spec)
    ops = list(spec.operands)
    if mutant == "drop-last-operand" and len(ops) > 1:
        ops = ops[:-1]
    elif mutant == "duplicate-first-operand" and len(ops) > 1:
        ops[-1] = ops[0]
    rhs: Expr | None = None
    accesses: list[Access] = []
    for i, operand in enumerate(ops):
        indices = [index_var_dict[s] for s in operand]
        accesses.append(tensor_vars[i][indices[0] if len(indices) == 1 else tuple(indices)])
    if mutant == "reverse-product":
        accesses = list(reversed(accesses))
    for access in accesses:
        rhs = access if rhs is None else rhs * access
    assert rhs is not None
    result = spec.result
    if mutant == "wrong-lhs" and spec.operands:
        result = spec.operands[0]
    lhs_indices = [index_var_dict[s] for s in result]
    result_tensor_var[lhs_indices[0] if len(lhs_indices) == 1 else tuple(lhs_indices)] = rhs
    assert result_tensor_var.assignment is not None
    stmt: Stmt = result_tensor_var.assignment
    schedule: Iterable[str] = reversed(spec.schedule)
    if mutant == "reverse-loop-nesting":
        schedule = spec.schedule
    for name in schedule:
        stmt = Loop(name, stmt)
    return stmt

P01_MUTANTS = (
    "drop-last-operand",
    "duplicate-first-operand",
    "reverse-product",
    "wrong-lhs",
    "reverse-loop-nesting",
)


def p01_exhaustive_specs() -> list[EinsumBuildSpec]:
    patterns = (("i",), ("j",), ("i", "j"), ("j", "i"), ("i", "i"), ("i", "j", "k"))
    results = (("i",), ("j",), ("i", "j"), ("j", "i"), ("i", "k"))
    out: list[EinsumBuildSpec] = []
    for nops in (1, 2, 3, 4):
        for operands in product(patterns, repeat=nops):
            used = {x for op in operands for x in op}
            for result in results:
                if not set(result).issubset(used):
                    continue
                names = sorted(used | set(result))
                for schedule in permutations(names):
                    out.append(EinsumBuildSpec(tuple(operands), tuple(result), tuple(schedule)))
    return out


# ---------------------------------------------------------------------------
# P04: monolithic LLIR renderer -> extracted helper dispatch (d7a9cdc...)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Literal: value: str
@dataclass(frozen=True)
class Var: name: str; typ: str = "int"
@dataclass(frozen=True)
class Cast: typ: str; expr: "Node"
@dataclass(frozen=True)
class Sizeof: typ: str
@dataclass(frozen=True)
class BinOp: left: "Node"; op: str; right: "Node"
@dataclass(frozen=True)
class UnaryOp: op: str; operand: "Node"
@dataclass(frozen=True)
class Call: name: str; args: tuple["Node", ...]
@dataclass(frozen=True)
class Array: values: tuple["Node", ...]
@dataclass(frozen=True)
class ArrayAccess: array: "Node"; index: "Node"
@dataclass(frozen=True)
class CallStmt: name: str; args: tuple["Node", ...]
@dataclass(frozen=True)
class VarInit: var: Var; value: "Node"; op: str = "="
@dataclass(frozen=True)
class AssignNode: var: Var; value: "Node"; op: str = "="
@dataclass(frozen=True)
class WhileLoop: cond: "Node"; body: tuple["Node", ...]
@dataclass(frozen=True)
class ForLoop: init: "Node | None"; cond: "Node"; update: "Node"; body: tuple["Node", ...]
@dataclass(frozen=True)
class ForLoopAuto: var: Var; array: "Node"; body: tuple["Node", ...]
@dataclass(frozen=True)
class IfNode:
    cond: "Node | None" = None
    then_body: tuple["Node", ...] = ()
    else_body: tuple["Node", ...] = ()
    cond_list: tuple["Node", ...] = ()
    then_body_list: tuple[tuple["Node", ...], ...] = ()
    make_last_case_else: bool = False
@dataclass(frozen=True)
class VarDecl: var: Var
@dataclass(frozen=True)
class Increment: var: Var
@dataclass(frozen=True)
class Function: name: str; args: tuple[Var, ...]; return_type: str; body: tuple["Node", ...]
@dataclass(frozen=True)
class Return: value: "Node"
@dataclass(frozen=True)
class Comment: text: str
@dataclass(frozen=True)
class Blank: pass
Node = (Literal | Var | Cast | Sizeof | BinOp | UnaryOp | Call | Array | ArrayAccess |
        CallStmt | VarInit | AssignNode | WhileLoop | ForLoop | ForLoopAuto | IfNode |
        VarDecl | Increment | Function | Return | Comment | Blank)


def _indent(text: str, level: int) -> str:
    prefix = "    " * level
    return "\n".join(prefix + line if line else line for line in text.split("\n"))

def _render_common(node: Node | str | Sequence[Node], level: int,
                   recurse: Callable[[Any, int, bool], str], no_semicolon: bool = False) -> str | None:
    if isinstance(node, str): return _indent(node, level)
    if isinstance(node, (list, tuple)): return "\n".join(recurse(x, level, False) for x in node)
    if isinstance(node, Comment): return _indent("// " + node.text, level)
    if isinstance(node, Blank): return _indent(" ", level)
    if isinstance(node, VarInit): return _indent(f"{node.var.typ} {node.var.name} {node.op} {recurse(node.value, 0, False)};", level)
    if isinstance(node, AssignNode): return _indent(f"{node.var.name} {node.op} {recurse(node.value, 0, False)};", level)
    return None

def render_before(node: Node | str | Sequence[Node], level: int = 0, no_semicolon: bool = False) -> str:
    common = _render_common(node, level, render_before, no_semicolon)
    if common is not None: return common
    if isinstance(node, Literal): return _indent(str(node.value), level)
    if isinstance(node, Cast): return _indent(f"({node.typ}) {render_before(node.expr)}", level)
    if isinstance(node, Sizeof): return _indent(f"sizeof({node.typ})", level)
    if isinstance(node, BinOp): return _indent(f"{render_before(node.left)} {node.op} {render_before(node.right)}", level)
    if isinstance(node, UnaryOp): return _indent(f"{node.op} {render_before(node.operand)}", level)
    if isinstance(node, Call): return _indent(f"{node.name}({', '.join(render_before(a) for a in node.args)})", level)
    if isinstance(node, CallStmt): return _indent(f"{node.name}({', '.join(render_before(a) for a in node.args)});", level)
    if isinstance(node, Array): return _indent("{" + ", ".join(render_before(v) for v in node.values) + "}", level)
    if isinstance(node, ArrayAccess): return _indent(f"{render_before(node.array)}[{render_before(node.index)}]", level)
    if isinstance(node, WhileLoop):
        return _indent(f"while ({render_before(node.cond)}) {{", level)+"\n"+render_before(node.body,level+1)+"\n"+_indent("}",level)
    if isinstance(node, ForLoop):
        init = render_before(node.init) if node.init is not None else ";"
        head=f"for ({init} {render_before(node.cond)}; {render_before(node.update,0,True)}) {{"
        return _indent(head,level)+"\n"+render_before(node.body,level+1)+"\n"+_indent("}",level)
    if isinstance(node, ForLoopAuto):
        head=f"for ({node.var.typ} {render_before(node.var)} : {render_before(node.array)}) {{"
        return _indent(head,level)+"\n"+render_before(node.body,level+1)+"\n"+_indent("}",level)
    if isinstance(node, IfNode): return _render_if(node,level,render_before)
    if isinstance(node, Var): return node.name
    if isinstance(node, VarDecl): return _indent(f"{node.var.typ} {node.var.name};",level)
    if isinstance(node, Increment): return _indent(f"{node.var.name}++" + ("" if no_semicolon else ";"),level)
    if isinstance(node, Function):
        head=f"{node.return_type} {node.name}({', '.join(f'{a.typ} {a.name}' for a in node.args)}) {{"
        return _indent(head,level)+"\n"+render_before(node.body,level+1)+"\n"+_indent("}",level)
    if isinstance(node, Return): return _indent(f"return {render_before(node.value)};",level)
    return _indent(f"No code gen implemented for node type: {type(node).__name__}",level)

def _render_expr(node: Node, level: int, recurse: Callable[[Any,int,bool],str]) -> str:
    if isinstance(node, Literal): return _indent(str(node.value), level)
    if isinstance(node, Cast): return _indent(f"({node.typ}) {recurse(node.expr,0,False)}", level)
    if isinstance(node, Sizeof): return _indent(f"sizeof({node.typ})", level)
    if isinstance(node, BinOp): return _indent(f"{recurse(node.left,0,False)} {node.op} {recurse(node.right,0,False)}", level)
    if isinstance(node, UnaryOp): return _indent(f"{node.op} {recurse(node.operand,0,False)}", level)
    if isinstance(node, Call): return _indent(f"{node.name}({', '.join(recurse(a,0,False) for a in node.args)})", level)
    if isinstance(node, Array): return _indent("{" + ", ".join(recurse(v,0,False) for v in node.values) + "}", level)
    if isinstance(node, ArrayAccess): return _indent(f"{recurse(node.array,0,False)}[{recurse(node.index,0,False)}]", level)
    raise ValueError(f"unknown expression {type(node).__name__}")

def _render_loop(node: WhileLoop|ForLoop|ForLoopAuto, level: int,
                 recurse: Callable[[Any,int,bool],str]) -> str:
    if isinstance(node, WhileLoop): head=f"while ({recurse(node.cond,0,False)}) {{"
    elif isinstance(node, ForLoop):
        init=recurse(node.init,0,False) if node.init is not None else ";"
        head=f"for ({init} {recurse(node.cond,0,False)}; {recurse(node.update,0,True)}) {{"
    else: head=f"for ({node.var.typ} {recurse(node.var,0,False)} : {recurse(node.array,0,False)}) {{"
    return _indent(head,level)+"\n"+recurse(node.body,level+1,False)+"\n"+_indent("}",level)

def _render_if(node: IfNode, level: int, recurse: Callable[[Any,int,bool],str]) -> str:
    result=""
    if node.cond_list:
        if len(node.cond_list)!=len(node.then_body_list): raise AssertionError("branch mismatch")
        total=len(node.cond_list)+(1 if node.else_body else 0)
        for i,(cond,body) in enumerate(zip(node.cond_list,node.then_body_list)):
            if i==0: header=f"if ({recurse(cond,0,False)}) {{"
            elif node.make_last_case_else and i==total-1: header="} else {"
            else: header=f"}} else if ({recurse(cond,0,False)}) {{"
            result += _indent(header,level)+"\n"+recurse(body,level+1,False)+"\n"
    else:
        if node.cond is None or not node.then_body: raise AssertionError("missing branch")
        result += _indent(f"if ({recurse(node.cond,0,False)}) {{",level)+"\n"+recurse(node.then_body,level+1,False)+"\n"
    if node.else_body:
        result += _indent("} else {",level)+"\n"+recurse(node.else_body,level+1,False)+"\n"
    return result+_indent("}",level)

def render_after(node: Node | str | Sequence[Node], level: int = 0, no_semicolon: bool = False) -> str:
    common = _render_common(node, level, render_after, no_semicolon)
    if common is not None: return common
    if isinstance(node,(Literal,Cast,Sizeof,BinOp,UnaryOp,Call,Array,ArrayAccess)):
        return _render_expr(node,level,render_after)
    if isinstance(node,CallStmt): return _indent(f"{node.name}({', '.join(render_after(a) for a in node.args)});",level)
    if isinstance(node,(WhileLoop,ForLoop,ForLoopAuto)): return _render_loop(node,level,render_after)
    if isinstance(node,IfNode): return _render_if(node,level,render_after)
    if isinstance(node,Var): return node.name
    if isinstance(node,VarDecl): return _indent(f"{node.var.typ} {node.var.name};",level)
    if isinstance(node,Increment): return _indent(f"{node.var.name}++"+("" if no_semicolon else ";"),level)
    if isinstance(node,Function):
        head=f"{node.return_type} {node.name}({', '.join(f'{a.typ} {a.name}' for a in node.args)}) {{"
        return _indent(head,level)+"\n"+render_after(node.body,level+1)+"\n"+_indent("}",level)
    if isinstance(node,Return): return _indent(f"return {render_after(node.value)};",level)
    return _indent(f"No code gen implemented for node type: {type(node).__name__}",level)

P04_MUTANTS=("omit-call-semicolon","reverse-function-args","drop-array-braces","increment-always-semicolon","drop-final-brace")

def render_mutant(node: Node, mutant: str) -> str:
    base=render_after(node)
    if mutant=="omit-call-semicolon" and isinstance(node,CallStmt): return base[:-1]
    if mutant=="reverse-function-args" and isinstance(node,Function):
        return render_after(Function(node.name,tuple(reversed(node.args)),node.return_type,node.body))
    if mutant=="drop-array-braces" and isinstance(node,Array): return ", ".join(render_after(v) for v in node.values)
    if mutant=="increment-always-semicolon" and isinstance(node,ForLoop):
        init=render_after(node.init) if node.init is not None else ";"
        update=render_after(node.update,0,False)
        return _indent(f"for ({init} {render_after(node.cond)}; {update}) {{",0)+"\n"+render_after(node.body,1)+"\n}"
    if mutant=="drop-final-brace" and isinstance(node,Function): return base.rsplit("\n",1)[0]
    return base

def p04_cases() -> list[Node]:
    x,y=Var("x"),Var("y")
    exprs: list[Node]=[Literal("0"),Literal("1"),x,Cast("float",x),Sizeof("int"),
        BinOp(x,"+",Literal("1")),UnaryOp("-",x),Call("f",(x,Literal("2"))),
        Array((x,Literal("3"))),ArrayAccess(Var("a"),x)]
    stmts: list[Node]=[CallStmt("f",(x,y)),VarInit(Var("z"),BinOp(x,"+",y)),
        AssignNode(x,y),WhileLoop(BinOp(x,"<",y),(Increment(x),)),
        ForLoop(VarInit(x,Literal("0")),BinOp(x,"<",Literal("4")),Increment(x),(CallStmt("g",(x,)),)),
        ForLoopAuto(Var("v","auto"),Var("arr","auto"),(CallStmt("use",(Var("v"),)),)),
        IfNode(cond=BinOp(x,"<",y),then_body=(AssignNode(x,y),),else_body=(AssignNode(y,x),)),
        IfNode(cond_list=(BinOp(x,"<",y),BinOp(x,"==",y)),then_body_list=((AssignNode(x,y),),(AssignNode(y,x),)),else_body=(Return(x),)),
        VarDecl(Var("q","float")),Increment(x),Return(x),
        Function("kernel",(Var("a","int"),Var("b","float")),"void",(CallStmt("use",(x,)),Return(Literal("0"))))]
    return exprs+stmts


# ---------------------------------------------------------------------------
# P06: monolithic coordinate resolution -> CoordinateResolver helpers
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IteratorState:
    coordinate: bool
    has_child: bool

@dataclass(frozen=True)
class CoordState:
    iterators: tuple[IteratorState,...]
    dense_universe: bool
    result_has_index: bool
    current_dense: bool
    child_compressed: bool
    dense_ready: tuple[bool,...]


def coord_before(s: CoordState) -> tuple[str,...]:
    out: list[str]=[]; n=len(s.iterators)
    if n>1 or s.dense_universe:
        if n:
            out.append("comment:load")
            out.extend(f"load:{i}" for i in range(n))
        if not s.dense_universe:
            out += ["blank","resolve:min","blank"]
    elif n==1:
        out += ["comment:resolve","resolve:single","blank"]
    if s.result_has_index and s.current_dense and s.child_compressed:
        out += ["comment:assemble","assemble:compressed"]
    ends=[]
    for i,it in enumerate(s.iterators):
        if it.coordinate and it.has_child:
            ends += [f"coord-end:{i}","blank"]
    if ends: out += ["comment:coord-ends",*ends]
    ready=[f"dense:{i}" for i,v in enumerate(s.dense_ready) if v]
    if ready: out += ["comment:dense",*ready]
    return tuple(out)

def coord_after(s: CoordState) -> tuple[str,...]:
    def load() -> list[str]:
        if not (len(s.iterators)>1 or s.dense_universe) or not s.iterators:return []
        return ["comment:load",*(f"load:{i}" for i in range(len(s.iterators)))]
    def resolve() -> list[str]:
        n=len(s.iterators)
        if n>1 or s.dense_universe:
            return [] if s.dense_universe else ["blank","resolve:min","blank"]
        if n==1:return ["comment:resolve","resolve:single","blank"]
        return []
    def assemble() -> list[str]:
        return ["comment:assemble","assemble:compressed"] if s.result_has_index and s.current_dense and s.child_compressed else []
    def ends() -> list[str]:
        x=[]
        for i,it in enumerate(s.iterators):
            if it.coordinate and it.has_child:x += [f"coord-end:{i}","blank"]
        return [] if not x else ["comment:coord-ends",*x]
    def dense() -> list[str]:
        x=[f"dense:{i}" for i,v in enumerate(s.dense_ready) if v]
        return [] if not x else ["comment:dense",*x]
    return tuple(load()+resolve()+assemble()+ends()+dense())

P06_MUTANTS=("drop-load","max-not-min","assemble-last","coord-end-off-by-one","drop-dense")
def coord_mutant(s: CoordState, mutant: str) -> tuple[str,...]:
    out=list(coord_after(s))
    if mutant=="drop-load": out=[x for x in out if not (x=="comment:load" or x.startswith("load:"))]
    elif mutant=="max-not-min": out=["resolve:max" if x=="resolve:min" else x for x in out]
    elif mutant=="assemble-last" and "assemble:compressed" in out:
        block=["comment:assemble","assemble:compressed"]
        for x in block: out.remove(x)
        out.extend(block)
    elif mutant=="coord-end-off-by-one": out=[x+":plus1" if x.startswith("coord-end:") else x for x in out]
    elif mutant=="drop-dense": out=[x for x in out if not (x=="comment:dense" or x.startswith("dense:"))]
    return tuple(out)

def p06_cases() -> list[CoordState]:
    out=[]
    iterator_options=[(),(IteratorState(False,False),),(IteratorState(True,True),),
                      (IteratorState(False,False),IteratorState(True,True)),
                      (IteratorState(True,False),IteratorState(True,True))]
    for its,dense,rhi,cur,child,ready in product(iterator_options,(False,True),(False,True),(False,True),(False,True),
                                                  ((),(False,),(True,),(False,True),(True,False))):
        out.append(CoordState(tuple(its),dense,rhi,cur,child,tuple(ready)))
    return out


# ---------------------------------------------------------------------------
# P08: equivalent mode-order initialization cleanup (33532a...)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ModeInit:
    explicit: tuple[int,...] | None
    shape_rank: int | None
    format_order: int | None


def mode_before(x: ModeInit) -> tuple[int,...] | None:
    mode: list[int] | tuple[int,...] | None
    mode = x.explicit if x.explicit else (list(range(x.shape_rank)) if x.shape_rank else None)
    if not mode:
        if x.format_order is None: raise AttributeError("format is absent")
        mode=list(range(x.format_order))
    return tuple(mode) if mode is not None else None

def mode_after(x: ModeInit) -> tuple[int,...] | None:
    if x.explicit: mode: Sequence[int] | None=x.explicit
    elif x.shape_rank: mode=list(range(x.shape_rank))
    elif x.format_order is not None: mode=list(range(x.format_order))
    else: mode=None
    return tuple(mode) if mode is not None else None

def mode_well_formed(x: ModeInit) -> bool:
    return bool(x.explicit) or bool(x.shape_rank) or x.format_order is not None

P08_MUTANTS=("ignore-explicit","shape-off-by-one","format-off-by-one","reverse-default","empty-is-explicit")
def mode_mutant(x: ModeInit, mutant: str) -> tuple[int,...] | None:
    if mutant=="empty-is-explicit" and x.explicit is not None:return tuple(x.explicit)
    if mutant!="ignore-explicit" and x.explicit:return tuple(x.explicit)
    if x.shape_rank:
        n=x.shape_rank-1 if mutant=="shape-off-by-one" else x.shape_rank
        v=tuple(range(max(n,0)))
        return tuple(reversed(v)) if mutant=="reverse-default" else v
    if x.format_order is not None:
        n=x.format_order-1 if mutant=="format-off-by-one" else x.format_order
        v=tuple(range(max(n,0)))
        return tuple(reversed(v)) if mutant=="reverse-default" else v
    return None

def p08_cases() -> list[ModeInit]:
    out=[]
    for explicit,shape,fmt in product((None,(),(0,),(1,0)),(None,0,1,2,3),(None,0,1,2,3)):
        x=ModeInit(explicit,shape,fmt)
        if mode_well_formed(x):out.append(x)
    return out


# ---------------------------------------------------------------------------
# Shared evaluation and bounded test-set construction
# ---------------------------------------------------------------------------

ADAPTERS = {
    "P01": {
        "cases": p01_exhaustive_specs,
        "before": build_cin_before,
        "after": build_cin_after,
        "mutants": P01_MUTANTS,
        "mutate": mutate_cin,
    },
    "P04": {
        "cases": p04_cases,
        "before": render_before,
        "after": render_after,
        "mutants": P04_MUTANTS,
        "mutate": render_mutant,
    },
    "P06": {
        "cases": p06_cases,
        "before": coord_before,
        "after": coord_after,
        "mutants": P06_MUTANTS,
        "mutate": coord_mutant,
    },
    "P08": {
        "cases": p08_cases,
        "before": mode_before,
        "after": mode_after,
        "mutants": P08_MUTANTS,
        "mutate": mode_mutant,
    },
}


def _safe_call(fn: Callable[[Any], Any], case: Any) -> tuple[str,Any]:
    try:return ("value",fn(case))
    except Exception as e:return ("exception",type(e).__name__)

def verify_adapter(adapter_id: str) -> dict[str,Any]:
    a=ADAPTERS[adapter_id]; cases=list(a["cases"]())
    mismatches=[]
    for i,c in enumerate(cases):
        left=_safe_call(a["before"],c);right=_safe_call(a["after"],c)
        if left!=right:mismatches.append({"index":i,"before":repr(left),"after":repr(right),"case":repr(c)})
    return {"adapter":adapter_id,"bounded_case_count":len(cases),"mismatch_count":len(mismatches),"mismatches":mismatches[:10]}

def _curated_indices(adapter_id: str, n: int) -> list[int]:
    cases=list(ADAPTERS[adapter_id]["cases"]())
    if adapter_id=="P01": preferred=[0,len(cases)//3,2*len(cases)//3,len(cases)-1]
    elif adapter_id=="P04": preferred=[0,10,11,12,13,14,15,16,17,18,19,20,21]
    elif adapter_id=="P06": preferred=[0,len(cases)//4,len(cases)//2,3*len(cases)//4,len(cases)-1]
    else: preferred=[0,len(cases)//3,2*len(cases)//3,len(cases)-1]
    out=[]
    while len(out)<n:
        out.append(preferred[len(out)%len(preferred)]%len(cases))
    return out

def _stratified_indices(adapter_id: str, n: int) -> list[int]:
    cases=list(ADAPTERS[adapter_id]["cases"]())
    if n>=len(cases):return list(range(len(cases)))
    # Evenly spaced deterministic boundary coverage, including both endpoints.
    return sorted({round(i*(len(cases)-1)/(n-1)) for i in range(n)})

def _random_indices(adapter_id: str, n: int, rng: random.Random) -> list[int]:
    cases=list(ADAPTERS[adapter_id]["cases"]())
    return [rng.randrange(len(cases)) for _ in range(n)]

def mutation_study(budget_per_adapter: int=64, seed: int=20260915) -> dict[str,Any]:
    rng=random.Random(seed); rows=[]
    for aid,a in ADAPTERS.items():
        cases=list(a["cases"]())
        methods={
            "developer-examples":_curated_indices(aid,budget_per_adapter),
            "random":_random_indices(aid,budget_per_adapter,rng),
            "stratified-boundary":_stratified_indices(aid,budget_per_adapter),
        }
        # If deduplication reduced a stratified set, cycle deterministically to keep equal executions.
        for name,idxs in methods.items():
            if not idxs:raise AssertionError("empty method")
            methods[name]=(idxs*((budget_per_adapter+len(idxs)-1)//len(idxs)))[:budget_per_adapter]
        for mutant in a["mutants"]:
            row={"adapter":aid,"mutant":mutant}
            for method,idxs in methods.items():
                detected=False;first=None
                for execution,i in enumerate(idxs,1):
                    c=cases[i]
                    expected=_safe_call(a["before"],c)
                    got=_safe_call(lambda z:a["mutate"](z,mutant),c)
                    if expected!=got:
                        detected=True;first=execution;break
                row[method]={"detected":detected,"first_detection_execution":first,"budget":budget_per_adapter}
            rows.append(row)
    summary={}
    for method in ("developer-examples","random","stratified-boundary"):
        detected=sum(1 for r in rows if r[method]["detected"])
        summary[method]={"detected":detected,"total":len(rows),"rate":detected/len(rows)}
    return {"seed":seed,"budget_per_adapter":budget_per_adapter,"mutant_count":len(rows),"rows":rows,"summary":summary}
