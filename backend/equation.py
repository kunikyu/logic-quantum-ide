import re
import sympy as sp
from sympy.physics.quantum import TensorProduct

# --- 基本行列の定義 ---
I_mat = sp.Matrix([[1, 0], [0, 1]])
X_mat = sp.Matrix([[0, 1], [1, 0]])
Y_mat = sp.Matrix([[0, -sp.I], [sp.I, 0]])
Z_mat = sp.Matrix([[1, 0], [0, -1]])
_INV_SQRT2 = sp.sqrt(2) / 2
H_mat = _INV_SQRT2 * sp.Matrix([[1, 1], [1, -1]])

S_mat = sp.Matrix([[1, 0], [0, sp.I]])
Sdg_mat = sp.Matrix([[1, 0], [0, -sp.I]])
T_mat = sp.Matrix([[1, 0], [0, _INV_SQRT2 * (1 + sp.I)]])
Tdg_mat = sp.Matrix([[1, 0], [0, _INV_SQRT2 * (1 - sp.I)]])

P0 = sp.Matrix([[1, 0], [0, 0]])
P1 = sp.Matrix([[0, 0], [0, 1]])


def Rx_mat(theta):
    return sp.Matrix([
        [sp.cos(theta / 2), -sp.I * sp.sin(theta / 2)],
        [-sp.I * sp.sin(theta / 2), sp.cos(theta / 2)]
    ])


def Ry_mat(theta):
    return sp.Matrix([
        [sp.cos(theta / 2), -sp.sin(theta / 2)],
        [sp.sin(theta / 2), sp.cos(theta / 2)]
    ])


def Rz_mat(theta):
    return sp.Matrix([
        [sp.exp(-sp.I * theta / 2), 0],
        [0, sp.exp(sp.I * theta / 2)]
    ])


SINGLE_QUBIT_GATES = {
    'id': I_mat, 'x': X_mat, 'y': Y_mat, 'z': Z_mat, 'h': H_mat,
    's': S_mat, 'sdg': Sdg_mat, 't': T_mat, 'tdg': Tdg_mat
}


def tensor_product_qiskit(matrices: list) -> sp.Matrix:
    """matrices[i] は量子ビット i。Qiskit と同じく q_{n-1} ⊗ … ⊗ q_0（右端が q0）。"""
    op = matrices[-1]
    for i in range(len(matrices) - 2, -1, -1):
        op = TensorProduct(op, matrices[i])
    return op


def _simp(expr: sp.Expr) -> sp.Expr:
    return sp.simplify(sp.expand_complex(expr))


def _pretty_real(expr: sp.Expr) -> str:
    expr = _simp(expr)
    if expr == 0:
        return '0'
    sign = ''
    if expr.is_negative:
        sign = '-'
        expr = _simp(-expr)
    s = sp.sstr(expr)
    s = re.sub(r'sqrt\((\d+)\)', r'√\1', s)
    s = re.sub(r'sqrt\(([^)]+)\)', r'√(\1)', s)
    s = s.replace('**', '^').replace('*', '')
    return sign + s


def _times_i(i_pos: str) -> str:
    if i_pos == '1':
        return 'i'
    if i_pos.isdigit():
        return f'{i_pos}i'
    return f'({i_pos})i'


def pretty_complex(expr: sp.Expr) -> str:
    expr = _simp(expr)
    if expr == 0:
        return '0'
    re_p, im_p = expr.as_real_imag()
    r, i = _pretty_real(re_p), _pretty_real(im_p)
    if i == '0':
        return r
    sign, iabs = ('-', i[1:]) if i.startswith('-') else ('', i)
    i_term = _times_i(iabs)
    if r == '0':
        return f'{sign}{i_term}'
    if sign:
        return f'{r} - {i_term}'
    return f'{r} + {i_term}'


def dirac_str(state: sp.Matrix, num_qubits: int) -> str:
    terms = []
    dim = 2 ** num_qubits
    for idx in range(dim):
        amp = _simp(state[idx, 0])
        if amp == 0:
            continue
        coeff = pretty_complex(amp)
        ket = f'|{idx:0{num_qubits}b}⟩'
        if coeff == '1':
            terms.append(ket)
        elif coeff == '-1':
            terms.append(f'- {ket}')
        elif coeff in ('i', '-i'):
            terms.append(f'{coeff}{ket}')
        elif coeff.startswith('-'):
            terms.append(f"- ({coeff[1:]}){ket}")
        elif ' + ' in coeff or ' - ' in coeff:
            terms.append(f'({coeff}){ket}')
        else:
            terms.append(f'{coeff}{ket}')
    if not terms:
        return '0'
    out = terms[0]
    for t in terms[1:]:
        out += f' - {t[2:]}' if t.startswith('- ') else f' + {t}'
    return out


def _is_zero(expr: sp.Expr) -> bool:
    return _simp(expr) == 0


def _norm(vec: list) -> sp.Expr:
    s = sp.Integer(0)
    for x in vec:
        s += _simp(x * sp.conjugate(x))
    return _simp(sp.sqrt(_simp(s)))


def _parallel(v0: list, v1: list) -> bool:
    n = len(v0)
    for j in range(n):
        for k in range(j + 1, n):
            if not _is_zero(v0[j] * v1[k] - v0[k] * v1[j]):
                return False
    return True


def local_qubit_diracs(state: sp.Matrix, num_qubits: int) -> list:
    vec = [_simp(state[i, 0]) for i in range(2 ** num_qubits)]
    result = []
    for q in range(num_qubits):
        v0, v1 = [], []
        for idx, amp in enumerate(vec):
            (v1 if (idx >> q) & 1 else v0).append(amp)
        if not _parallel(v0, v1):
            result.append('ENTANGLED')
            continue
        n0, n1 = _norm(v0), _norm(v1)
        if _is_zero(n0) and _is_zero(n1):
            result.append('0')
            continue
        if _is_zero(n0):
            alpha, beta = sp.Integer(0), sp.Integer(1)
        else:
            j = next(j for j, x in enumerate(v0) if not _is_zero(x))
            alpha = n0
            beta = _simp(n0 * v1[j] / v0[j])
        result.append(dirac_str(sp.Matrix([alpha, beta]), 1))
    return result


class SymbolicSimulator:
    def __init__(self, num_qubits: int):
        self.num_qubits = num_qubits
        self.current_state = self._get_initial_state()
        self.history = []

    def _get_initial_state(self) -> sp.Matrix:
        dim = 2 ** self.num_qubits
        state = sp.zeros(dim, 1)
        state[0, 0] = 1
        return state

    def apply_matrix(self, op: sp.Matrix):
        old = self.current_state
        new = (op * old).applyfunc(_simp)
        self.current_state = new
        return old, new

    def display_state(self):
        return (
            dirac_str(self.current_state, self.num_qubits),
            local_qubit_diracs(self.current_state, self.num_qubits),
        )

    def state_latex(self) -> str:
        return sp.latex(self.current_state.applyfunc(_simp), fold_short_frac=True)

    def apply_qiskit_circuit(self, qc) -> list:
        gate_infos = self._extract_gate_info(qc)
        self.history.append({
            "step": 0,
            "name": "initial",
            "qargs": [],
            "params": [],
            "equation_latex": sp.latex(self.current_state, fold_short_frac=True),
            "probabilities": self._calculate_probabilities(self.current_state)
        })

        for step, info in enumerate(gate_infos, 1):
            global_op = self._build_global_matrix(info)
            old_state, new_state = self.apply_matrix(global_op)
            self.history.append({
                "step": step,
                "name": info["name"],
                "qargs": info["qargs"],
                "params": info.get("params", []),
                "equation_latex": self._generate_equation_latex(global_op, old_state, new_state),
                "probabilities": self._calculate_probabilities(new_state)
            })

        return self.history

    def _extract_gate_info(self, qc) -> list:
        gate_infos = []
        for instruction in qc.data:
            op = instruction.operation
            if op.name in ('save_statevector', 'measure', 'barrier'):
                continue
            qargs = [qc.find_bit(q).index for q in instruction.qubits]
            gate_infos.append({
                'name': op.name,
                'qargs': qargs,
                'params': op.params
            })
        return gate_infos

    def _build_global_matrix(self, info: dict) -> sp.Matrix:
        name = info['name']
        qargs = info['qargs']
        params = info.get('params', [])
        num = self.num_qubits

        if name in ('mcx', 'ccx') and len(qargs) >= 2:
            return self._build_n_controlled(num, qargs[:-1], qargs[-1], X_mat)
        if name in ('mcz', 'ccz') and len(qargs) >= 2:
            return self._build_n_controlled(num, qargs[:-1], qargs[-1], Z_mat)

        if len(qargs) == 1:
            target = qargs[0]
            if name in SINGLE_QUBIT_GATES:
                gate_mat = SINGLE_QUBIT_GATES[name]
            elif name == 'rx':
                gate_mat = Rx_mat(params[0])
            elif name == 'ry':
                gate_mat = Ry_mat(params[0])
            elif name == 'rz':
                gate_mat = Rz_mat(params[0])
            else:
                raise NotImplementedError(f"未対応の1量子ビットゲート: {name}")
            matrices = [I_mat] * num
            matrices[target] = gate_mat
            return tensor_product_qiskit(matrices)

        if len(qargs) == 2:
            ctrl, targ = qargs[0], qargs[1]
            if name == 'cx':
                return self._build_n_controlled(num, [ctrl], targ, X_mat)
            if name == 'cz':
                return self._build_n_controlled(num, [ctrl], targ, Z_mat)
            if name == 'swap':
                cx1 = self._build_n_controlled(num, [ctrl], targ, X_mat)
                cx2 = self._build_n_controlled(num, [targ], ctrl, X_mat)
                return cx1 * cx2 * cx1
            raise NotImplementedError(f"未対応の2量子ビットゲート: {name}")

        raise ValueError("サポートされていないビット数のゲートです。")

    def _build_n_controlled(self, num_qubits: int, ctrls: list, targ: int, target_gate: sp.Matrix) -> sp.Matrix:
        nctrl = len(ctrls)
        acc = sp.zeros(2 ** num_qubits, 2 ** num_qubits)
        for bits in range(2 ** nctrl):
            mats = [I_mat] * num_qubits
            all_one = True
            for i, c in enumerate(ctrls):
                bit = (bits >> (nctrl - 1 - i)) & 1
                mats[c] = P1 if bit else P0
                if not bit:
                    all_one = False
            if all_one:
                mats[targ] = target_gate
            acc += tensor_product_qiskit(mats)
        return acc

    def _generate_equation_latex(self, op: sp.Matrix, old: sp.Matrix, new: sp.Matrix) -> str:
        op_s = op.applyfunc(_simp)
        old_s = old.applyfunc(_simp)
        new_s = new.applyfunc(_simp)
        return (
            f"{sp.latex(op_s, fold_short_frac=True)} "
            f"{sp.latex(old_s, fold_short_frac=True)} = "
            f"{sp.latex(new_s, fold_short_frac=True)}"
        )

    def reset(self):
        self.current_state = self._get_initial_state()
        self.history = []

    def _calculate_probabilities(self, state_matrix: sp.Matrix) -> list:
        probabilities = []
        for i in range(2 ** self.num_qubits):
            amp = state_matrix[i, 0]
            prob = float(_simp(amp * sp.conjugate(amp)))
            bit_string = format(i, f'0{self.num_qubits}b')
            probabilities.append({
                "state": f"|{bit_string}⟩",
                "probability": round(prob, 4)
            })
        return probabilities
