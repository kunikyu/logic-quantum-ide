# Quantum IDE — 自動生成 Qiskit スクリプト
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
import numpy as np

qc = QuantumCircuit(1)
# 量子ゲートが回路にありません

# シミュレーション
qc.save_statevector()
sim = AerSimulator(method='statevector')
result = sim.run(qc).result()
sv = np.array(result.get_statevector(qc))
probs={format(i,f"0{qc.num_qubits}b"):round(float(abs(a)**2),4) for i,a in enumerate(sv) if abs(a)**2>1e-6}
print("確率分布:", probs)