# backend/quantum_simulator.py
import io
import base64
import logging
from typing import Any, Dict, List
from equation import SymbolicSimulator

import matplotlib.pyplot as plt
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import (
    HGate, XGate, YGate, ZGate, SGate, TGate,
    CXGate, CZGate, CCXGate, MCXGate,
)
from qiskit.quantum_info import partial_trace, Pauli, Statevector
from qiskit_aer import AerSimulator

plt.switch_backend('Agg')
logger = logging.getLogger(__name__)


def _format_complex(value: complex) -> str:
    return f'{value.real:.12f}{value.imag:+.12f}j'


def _calc_bloch_vectors(sv: Statevector, num_qubits: int) -> List[List[float]]:
    bloch_vectors: List[List[float]] = []
    for i in range(num_qubits):
        try:
            trace_over = [q for q in range(num_qubits) if q != i]
            rho_i = partial_trace(sv, trace_over)
            x = float(rho_i.expectation_value(Pauli('X')).real)
            y = float(rho_i.expectation_value(Pauli('Y')).real)
            z = float(rho_i.expectation_value(Pauli('Z')).real)
            bloch_vectors.append([x, y, z])
        except Exception as exc:
            logger.warning(f"Qubit {i} の Bloch 計算に失敗: {exc}")
            bloch_vectors.append([0.0, 0.0, 0.0])
    return bloch_vectors


def run_simulation(circuit_definition: list, shots: int = 1024, num_qubits: int = 2) -> dict:
    """
    量子回路のシミュレーションを実行し、状態ベクトル、ブロッホベクトル、ステップ履歴、作図、測定カウントを返す。
    Statevector.evolve を活用して回路と状態の二重管理を排除し、O(N)で高速かつ数学的に厳密に計算する。
    """
    try:
        safe_num_qubits = max(num_qubits, 2)
        num_classical_bits = safe_num_qubits
        qc = QuantumCircuit(safe_num_qubits, num_classical_bits)
        current_sv = Statevector.from_label('0' * safe_num_qubits)
        measure_explicitly_added = False
        measured_qubits: List[int] = []

        logger.info(f"量子回路作成: {safe_num_qubits} qubits")

        calc_steps: List[Dict[str, Any]] = []
        history: List[Dict[str, Any]] = []
        sym_sim = SymbolicSimulator(safe_num_qubits)

        def _record_step(label: str, qubits: List[int], slot: int, name: str, qargs: list, op_mat=None, old_state=None):
            dirac, qstates = sym_sim.display_state()
            calc_steps.append({
                'label': label,
                'dirac': dirac,
                'qubits_state': qstates,
                'qubits': qubits,
                'slot': slot
            })
            if op_mat is None or old_state is None:
                eq = sym_sim.state_latex()
            else:
                eq = sym_sim._generate_equation_latex(op_mat, old_state, sym_sim.current_state)
            history.append({
                'step': len(history),
                'name': name,
                'qargs': qargs,
                'params': [],
                'equation_latex': eq,
            })

        def _sym_matrix(gate_name: str, gate_op: dict):
            if gate_name in ('h', 'x', 'y', 'z', 's', 't'):
                return sym_sim._build_global_matrix({'name': gate_name, 'qargs': [gate_op['qubit']], 'params': []})
            if gate_name in ('cx', 'cz', 'ccx', 'ccz'):
                return sym_sim._build_global_matrix({'name': gate_name, 'qargs': gate_op['qubits'], 'params': []})
            if gate_name == 'mcx':
                return sym_sim._build_global_matrix({'name': 'mcx', 'qargs': list(gate_op['controls']) + [gate_op['target']], 'params': []})
            if gate_name == 'mcz':
                return sym_sim._build_global_matrix({'name': 'mcz', 'qargs': list(gate_op['controls']) + [gate_op['target']], 'params': []})
            return None

        _record_step('初期状態', [], -1, 'initial', [])

        for op in circuit_definition:
            gate = op.get('gate')
            all_op_qubits: List[int] = []
            if 'qubit' in op:
                all_op_qubits.append(op['qubit'])
            if 'qubits' in op:
                all_op_qubits.extend(op['qubits'])
            if 'controls' in op:
                all_op_qubits.extend(op['controls'])
            if 'target' in op:
                all_op_qubits.append(op['target'])

            if any(q >= safe_num_qubits for q in all_op_qubits):
                continue

            slot = op.get('slot', 0) + 1

            if gate == 'h':
                q = op['qubit']
                qc.h(q)
                current_sv = current_sv.evolve(HGate(), [q])
                label = f"q{q} → H    (q{q}, {slot})"
            elif gate == 'x':
                q = op['qubit']
                qc.x(q)
                current_sv = current_sv.evolve(XGate(), [q])
                display_gate = op.get('original_type', 'X').upper()
                label = f"q{q} → {display_gate}    (q{q}, {slot})"
            elif gate == 'y':
                q = op['qubit']
                qc.y(q)
                current_sv = current_sv.evolve(YGate(), [q])
                label = f"q{q} → Y    (q{q}, {slot})"
            elif gate == 'z':
                q = op['qubit']
                qc.z(q)
                current_sv = current_sv.evolve(ZGate(), [q])
                display_gate = op.get('original_type', 'Z').upper()
                label = f"q{q} → {display_gate}    (q{q}, {slot})"
            elif gate == 's':
                q = op['qubit']
                qc.s(q)
                current_sv = current_sv.evolve(SGate(), [q])
                label = f"q{q} → S    (q{q}, {slot})"
            elif gate == 't':
                q = op['qubit']
                qc.t(q)
                current_sv = current_sv.evolve(TGate(), [q])
                label = f"q{q} → T    (q{q}, {slot})"
            elif gate == 'cx':
                c, t = op['qubits'][0], op['qubits'][1]
                qc.cx(c, t)
                current_sv = current_sv.evolve(CXGate(), [c, t])
                label = f"q{c} (ctrl), q{t} (tgt) → CX    (ctrl: q{c}, tgt: q{t}, {slot})"
            elif gate == 'cz':
                c, t = op['qubits'][0], op['qubits'][1]
                qc.cz(c, t)
                current_sv = current_sv.evolve(CZGate(), [c, t])
                label = f"q{c} (ctrl), q{t} (tgt) → CZ    (ctrl: q{c}, tgt: q{t}, {slot})"
            elif gate == 'ccx':
                c1, c2, t = op['qubits'][0], op['qubits'][1], op['qubits'][2]
                qc.ccx(c1, c2, t)
                current_sv = current_sv.evolve(CCXGate(), [c1, c2, t])
                label = f"q{c1}, q{c2} (ctrl), q{t} (tgt) → CCX    (ctrls: q{c1}, q{c2}, tgt: q{t}, {slot})"
            elif gate == 'ccz':
                c1, c2, t = op['qubits'][0], op['qubits'][1], op['qubits'][2]
                qc.h(t)
                qc.ccx(c1, c2, t)
                qc.h(t)
                current_sv = current_sv.evolve(HGate(), [t]).evolve(CCXGate(), [c1, c2, t]).evolve(HGate(), [t])
                label = f"q{c1}, q{c2} (ctrl), q{t} (tgt) → CCZ    (ctrls: q{c1}, q{c2}, tgt: q{t}, {slot})"
            elif gate == 'mcx':
                ctrls, target = op['controls'], op['target']
                qc.mcx(ctrls, target)
                current_sv = current_sv.evolve(MCXGate(len(ctrls)), ctrls + [target])
                ctrl_str = ', '.join([f"q{c}" for c in ctrls])
                label = f"{ctrl_str} (ctrl), q{target} (tgt) → MCX    (ctrls: {ctrl_str}, tgt: q{target}, {slot})"
            elif gate == 'mcz':
                ctrls, target = op['controls'], op['target']
                qc.h(target)
                qc.mcx(ctrls, target)
                qc.h(target)
                current_sv = current_sv.evolve(HGate(), [target]).evolve(MCXGate(len(ctrls)), ctrls + [target]).evolve(HGate(), [target])
                ctrl_str = ', '.join([f"q{c}" for c in ctrls])
                label = f"{ctrl_str} (ctrl), q{target} (tgt) → MCZ    (ctrls: {ctrl_str}, tgt: q{target}, {slot})"
            elif gate == 'measure':
                q = op['qubit']
                qc.measure(q, q)
                measure_explicitly_added = True
                if q not in measured_qubits:
                    measured_qubits.append(q)
                continue
            else:
                continue

            op_mat = _sym_matrix(gate, op)
            old_state = None
            if op_mat is not None:
                old_state, _ = sym_sim.apply_matrix(op_mat)
            _record_step(label, all_op_qubits, slot - 1, gate, all_op_qubits, op_mat, old_state)

        # 回路図（Matplotlib）の描画
        fig = None
        for style in ('iqp', 'clifford', None):
            try:
                fig = qc.draw(output='mpl', style=style) if style else qc.draw(output='mpl')
                if fig:
                    break
            except Exception:
                continue

        if fig:
            buf = io.BytesIO()
            fig.savefig(buf, format='png', bbox_inches='tight', dpi=150)
            buf.seek(0)
            img_str = base64.b64encode(buf.read()).decode('utf-8')
            plt.close(fig)
        else:
            img_str = None

    except Exception as e:
        logger.error(f"回路構築中のエラー: {e}")
        return {'error': f'Error building circuit: {str(e)}'}

    try:
        # 測定カウントのシミュレーション（measureゲートが存在する場合のみ実行）
        counts: Dict[str, int] = {}
        if measure_explicitly_added:
            try:
                num_shots = int(shots)
                if num_shots <= 0:
                    num_shots = 1024
            except (ValueError, TypeError):
                num_shots = 1024

            simulator = AerSimulator()
            compiled_circuit = transpile(qc, simulator)
            job = simulator.run(compiled_circuit, shots=num_shots)
            result = job.result()
            try:
                counts = result.get_counts(qc)
            except Exception:
                counts = {}

        # 最終状態ベクトルおよびブロッホ球ベクトルの取得（二重計算を排除）
        final_statevector_list = [_format_complex(complex(v)) for v in current_sv.data]
        final_bloch_vectors = _calc_bloch_vectors(current_sv, safe_num_qubits)

        return {
            'counts': counts,
            'statevector': final_statevector_list,
            'circuit_diagram': img_str,
            'bloch_vectors': final_bloch_vectors,
            'measured_qubits': measured_qubits,
            'calc_steps': calc_steps,
            'latex': history
        }

    except Exception as e:
        logger.error(f"シミュレーション実行中のエラー: {e}")
        return {'error': f'Error during simulation: {str(e)}'}
