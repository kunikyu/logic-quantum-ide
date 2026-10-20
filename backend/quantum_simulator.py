# backend/quantum_simulator.py
import io
import base64
import logging
from typing import Any, Dict, List, Tuple

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
    """計算過程へ渡す複素数を、精度を落とさず文字列化する。"""
    return f'{value.real:.12f}{value.imag:+.12f}j'


def _calc_qubit_states_and_bloch(
    sv: Statevector, num_qubits: int
) -> Tuple[List[Any], List[List[float]]]:
    """
    Statevectorから各単一量子ビットの局所状態表現およびブロッホ球座標を厳密に計算する。
    - もつれ状態の場合: "ENTANGLED"
    - 純粋状態の場合: 密度行列・ブロッホ座標から厳密に再生した [α, β]
    """
    qubits_state: List[Any] = []
    bloch_vectors: List[List[float]] = []

    for i in range(num_qubits):
        try:
            trace_over = [q for q in range(num_qubits) if q != i]
            rho_i = partial_trace(sv, trace_over)
            x = float(rho_i.expectation_value(Pauli('X')).real)
            y = float(rho_i.expectation_value(Pauli('Y')).real)
            z = float(rho_i.expectation_value(Pauli('Z')).real)
            bloch_vectors.append([x, y, z])

            # ブロッホ球ベクトルのノルムの二乗（純粋度）
            r2 = x * x + y * y + z * z
            if r2 < 0.99:
                qubits_state.append("ENTANGLED")
            else:
                # 純粋状態の復元: 基準位相として α を実数にとる
                if 1.0 + z > 1e-6:
                    alpha = ((1.0 + z) / 2.0) ** 0.5
                    beta = complex(x, y) / (2.0 * alpha)
                else:
                    alpha = 0.0
                    beta = complex(1.0, 0.0)
                qubits_state.append([_format_complex(complex(alpha)), _format_complex(complex(beta))])
        except Exception as exc:
            logger.warning(f"Qubit {i} の状態計算に失敗: {exc}")
            qubits_state.append("Unknown")
            bloch_vectors.append([0.0, 0.0, 0.0])

    return qubits_state, bloch_vectors


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

        # 初期ステップの記録
        initial_qubits_state, _ = _calc_qubit_states_and_bloch(current_sv, safe_num_qubits)
        calc_steps.append({
            'label': '初期状態',
            'statevector': [_format_complex(complex(v)) for v in current_sv.data],
            'qubits_state': initial_qubits_state,
            'qubits': [],
            'slot': -1
        })

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

            # ステップ結果を記録
            step_qubits_state, _ = _calc_qubit_states_and_bloch(current_sv, safe_num_qubits)
            calc_steps.append({
                'label': label,
                'statevector': [_format_complex(complex(v)) for v in current_sv.data],
                'qubits_state': step_qubits_state,
                'qubits': all_op_qubits,
                'slot': slot - 1
            })

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
        _, final_bloch_vectors = _calc_qubit_states_and_bloch(current_sv, safe_num_qubits)

        return {
            'counts': counts,
            'statevector': final_statevector_list,
            'circuit_diagram': img_str,
            'bloch_vectors': final_bloch_vectors,
            'measured_qubits': measured_qubits,
            'calc_steps': calc_steps
        }

    except Exception as e:
        logger.error(f"シミュレーション実行中のエラー: {e}")
        return {'error': f'Error during simulation: {str(e)}'}