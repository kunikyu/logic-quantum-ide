# backend/quantum_simulator.py
import io
import base64
import logging
from typing import Any, Dict, List
from equation import SymbolicSimulator

import matplotlib.pyplot as plt
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import CCZGate, ZGate
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
    量子回路のシミュレーションを実行し、状態ベクトル、ブロッホベクトル、作図、測定カウント、
    および統合されたステップ履歴 (数式、ディラック記法、UI情報など) を返す。
    """
    try:
        safe_num_qubits = max(num_qubits, 2)
        # 測定用の古典ビットも用意しておく（QuantumCircuitの第2引数）
        qc = QuantumCircuit(safe_num_qubits, safe_num_qubits)
        
        measure_explicitly_added = False
        measured_qubits: List[int] = []
        measure_ops: List[int] = []
        gate_ui_infos: List[Dict[str, Any]] = []

        logger.info(f"量子回路作成: {safe_num_qubits} qubits")

        for op in circuit_definition:
            gate = op.get('gate')
            if not gate:
                continue

            all_op_qubits: List[int] = []
            if 'qubit' in op:
                all_op_qubits.append(op['qubit'])
            if 'qubits' in op:
                all_op_qubits.extend(op['qubits'])
            if 'controls' in op:
                all_op_qubits.extend(op['controls'])
            if 'target' in op:
                all_op_qubits.append(op['target'])

            # 回路のビット数を超えた指示があればスキップ
            if any(q >= safe_num_qubits for q in all_op_qubits):
                continue

            # UIでの表示用スロットとラベル情報
            slot = op.get('slot', 0) + 1
            label = ""

            if gate == 'h':
                q = op['qubit']
                qc.h(q)
                label = f"q{q} → H    (q{q}, {slot})"
            elif gate == 'x':
                q = op['qubit']
                qc.x(q)
                display_gate = op.get('original_type', 'X').upper()
                label = f"q{q} → {display_gate}    (q{q}, {slot})"
            elif gate == 'y':
                q = op['qubit']
                qc.y(q)
                label = f"q{q} → Y    (q{q}, {slot})"
            elif gate == 'z':
                q = op['qubit']
                qc.z(q)
                display_gate = op.get('original_type', 'Z').upper()
                label = f"q{q} → {display_gate}    (q{q}, {slot})"
            elif gate == 's':
                q = op['qubit']
                qc.s(q)
                label = f"q{q} → S    (q{q}, {slot})"
            elif gate == 't':
                q = op['qubit']
                qc.t(q)
                label = f"q{q} → T    (q{q}, {slot})"
            elif gate == 'cx':
                c, t = op['qubits'][0], op['qubits'][1]
                qc.cx(c, t)
                label = f"q{c} (ctrl), q{t} (tgt) → CX    (ctrl: q{c}, tgt: q{t}, {slot})"
            elif gate == 'cz':
                c, t = op['qubits'][0], op['qubits'][1]
                qc.cz(c, t)
                label = f"q{c} (ctrl), q{t} (tgt) → CZ    (ctrl: q{c}, tgt: q{t}, {slot})"
            elif gate == 'ccx':
                c1, c2, t = op['qubits'][0], op['qubits'][1], op['qubits'][2]
                qc.ccx(c1, c2, t)
                label = f"q{c1}, q{c2} (ctrl), q{t} (tgt) → CCX    (ctrls: q{c1}, q{c2}, tgt: q{t}, {slot})"
            elif gate == 'ccz':
                # SymbolicSimulatorとのステップ同期のため、CCZGateとして追加
                c1, c2, t = op['qubits'][0], op['qubits'][1], op['qubits'][2]
                qc.append(CCZGate(), [c1, c2, t])
                label = f"q{c1}, q{c2} (ctrl), q{t} (tgt) → CCZ    (ctrls: q{c1}, q{c2}, tgt: q{t}, {slot})"
            elif gate == 'mcx':
                ctrls, target = op['controls'], op['target']
                qc.mcx(ctrls, target)
                ctrl_str = ', '.join([f"q{c}" for c in ctrls])
                label = f"{ctrl_str} (ctrl), q{target} (tgt) → MCX    (ctrls: {ctrl_str}, tgt: q{target}, {slot})"
            elif gate == 'mcz':
                # SymbolicSimulatorとのステップ同期のため、単一のコントロールZとして追加
                ctrls, target = op['controls'], op['target']
                mcz_gate = ZGate().control(len(ctrls))
                mcz_gate.name = 'mcz'
                qc.append(mcz_gate, ctrls + [target])
                ctrl_str = ', '.join([f"q{c}" for c in ctrls])
                label = f"{ctrl_str} (ctrl), q{target} (tgt) → MCZ    (ctrls: {ctrl_str}, tgt: q{target}, {slot})"
            elif gate == 'measure':
                # 測定は数式シミュレータに影響を与えないよう別管理
                measure_explicitly_added = True
                q = op['qubit']
                if q not in measured_qubits:
                    measured_qubits.append(q)
                measure_ops.append(q)
                continue
            else:
                continue

            # 各ステップごとのメタデータを保持
            gate_ui_infos.append({'label': label, 'slot': slot, 'qubits': all_op_qubits})

        # --- Qiskitによる最終状態とブロッホベクトルの計算 ---
        # Statevector(qc) により二重計算を排除し、O(N)で状態を直接取得
        final_sv = Statevector(qc)
        final_statevector_list = [_format_complex(complex(v)) for v in final_sv.data]
        final_bloch_vectors = _calc_bloch_vectors(final_sv, safe_num_qubits)

        # --- SymbolicSimulatorの実行と履歴の取得 ---
        sym_sim = SymbolicSimulator(qc)
        sym_history = sym_sim.get_history()

        # --- 履歴とUI情報の統合 (calc_steps と history の一本化) ---
        integrated_steps = []
        if len(sym_history) > 0:
            # Step 0 (初期状態)
            integrated_steps.append({
                **sym_history[0],
                'label': '初期状態',
                'slot': -1,
                'qubits': []
            })
            
            # Step 1 以降
            for i, ui_info in enumerate(gate_ui_infos):
                step_idx = i + 1
                if step_idx < len(sym_history):
                    integrated_steps.append({
                        **sym_history[step_idx],
                        **ui_info
                    })

        # --- 回路図（Matplotlib）の描画 ---
        # 描画用と測定シミュレーション用に、測定ゲートを追加したコピー回路を作成
        qc_run = qc.copy()
        for q in measure_ops:
            qc_run.measure(q, q)

        fig = None
        for style in ('iqp', 'clifford', None):
            try:
                fig = qc_run.draw(output='mpl', style=style) if style else qc_run.draw(output='mpl')
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
        # --- 測定カウントのシミュレーション ---
        counts: Dict[str, int] = {}
        if measure_explicitly_added:
            try:
                num_shots = int(shots)
                if num_shots <= 0:
                    num_shots = 1024
            except (ValueError, TypeError):
                num_shots = 1024

            simulator = AerSimulator()
            compiled_circuit = transpile(qc_run, simulator)
            job = simulator.run(compiled_circuit, shots=num_shots)
            result = job.result()
            try:
                counts = result.get_counts(qc_run)
            except Exception:
                counts = {}

        # 戻り値を統合 (calc_stepsとlatexをhistoryにまとめる)
        return {
            'counts': counts,
            'statevector': final_statevector_list,
            'circuit_diagram': img_str,
            'bloch_vectors': final_bloch_vectors,
            'measured_qubits': measured_qubits,
            'history': integrated_steps
        }

    except Exception as e:
        logger.error(f"シミュレーション実行中のエラー: {e}")
        return {'error': f'Error during simulation: {str(e)}'}
