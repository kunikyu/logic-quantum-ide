# main.py
# Quantum IDE — FastAPI アプリケーション

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from models import CircuitGraphRequest, SimulationResponse, ChatRequest, ChatResponse, TruthTableResponse, LogicExpressionResponse, QuantumRequest
from simulator import simulate, extract_logic_expressions, generate_truth_table
from quantum_simulator import run_simulation
from ai_agent import generate_response

# ログ設定（日本語）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(__name__)

# ============================================================
# FastAPI アプリ初期化
# ============================================================
app = FastAPI(
    title="Quantum IDE バックエンドAPI",
    description="量子・論理回路シミュレーターのバックエンドAPI",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ============================================================
# CORS 設定
# フロントエンド（http://localhost:5173）からのアクセスを許可
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# エンドポイント定義
# ============================================================

@app.get("/")
def root():
    """ヘルスチェック"""
    logger.info("ルートエンドポイントへのアクセス")
    return {"message": "Quantum IDE バックエンドAPI が起動中です", "status": "ok"}


@app.post("/api/simulate", response_model=SimulationResponse)
def simulate_circuit(request: CircuitGraphRequest) -> SimulationResponse:
    """
    回路グラフ (nodes + edges) を受け取り、シミュレーション結果を返す。

    処理順序:
      1. トポロジカルソート
      2. 論理ゲートの真理値計算
      3. Qiskit による量子回路の状態ベクトル計算
      4. タイミングデータ履歴の更新・返却

    レスポンス形式:
      {
        "edgeStates":   { "<edgeId>": 0 | 1, ... },
        "quantumState": { "n_qubits": N, "probabilities": {...}, ... },
        "timingData":   { "<nodeId>": [0, 1, 1, 0, ...], ... }
      }
    """
    logger.info(
        f"シミュレーションリクエスト受信: "
        f"ノード数={len(request.nodes)}, エッジ数={len(request.edges)}"
    )
    result = simulate(request)
    logger.info(
        f"シミュレーション完了: "
        f"エッジ状態={len(result.edgeStates)}本, "
        f"タイミングノード={len(result.timingData)}個"
    )
    return result

@app.post("/api/logic-expression", response_model=LogicExpressionResponse)
def logic_expression(request: CircuitGraphRequest) -> LogicExpressionResponse:
    """
    回路グラフから論理式 (AST) を抽出し、テキストおよびLaTeX形式で返す。
    """
    logger.info(f"論理式抽出リクエスト受信: ノード数={len(request.nodes)}, エッジ数={len(request.edges)}")
    result = extract_logic_expressions(request)
    return result


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """
    AIチャットエンドポイント。
    システムプロンプト: JSON形式 { "message":"...", "suggestion":{...}|null } を強制。
    """
    logger.info(f"AIチャット: {request.message[:60]}")
    ctx = request.circuitContext or {}
    result = generate_response(request.message, ctx)
    logger.info(f"AI応答: suggestion={result.get('suggestion')}")
    return ChatResponse(**result)


# ============================================================
# エクスポートエンドポイント
# ============================================================
from fastapi.responses import PlainTextResponse
from converters import export_qasm, export_python, export_verilog, export_logisim


@app.post("/api/export/qasm", response_class=PlainTextResponse)
def export_qasm_ep(request: CircuitGraphRequest) -> str:
    """OpenQASM 2.0 文字列を返す"""
    logger.info(f"QASM エクスポート: {len(request.nodes)} ノード")
    return export_qasm(request.nodes, request.edges)


@app.post("/api/export/python", response_class=PlainTextResponse)
def export_python_ep(request: CircuitGraphRequest) -> str:
    """Qiskit Python スクリプト文字列を返す"""
    logger.info(f"Python エクスポート: {len(request.nodes)} ノード")
    return export_python(request.nodes, request.edges)


@app.post("/api/export/verilog", response_class=PlainTextResponse)
def export_verilog_ep(request: CircuitGraphRequest) -> str:
    """Structural Verilog (.v) 文字列を返す"""
    logger.info(f"Verilog エクスポート: {len(request.nodes)} ノード")
    return export_verilog(request.nodes, request.edges)


@app.post("/api/export/logisim", response_class=PlainTextResponse)
def export_logisim_ep(request: CircuitGraphRequest) -> str:
    logger.info(f"Logisim エクスポート: {len(request.nodes)} ノード")
    return export_logisim(request.nodes, request.edges)


@app.post("/api/truthtable", response_model=TruthTableResponse)
def truth_table(request: CircuitGraphRequest) -> TruthTableResponse:
    """Switch / Clock の全組み合わせを1ステップ実行し、LED / SevenSeg 出力との対応表を返す"""
    return generate_truth_table(request)


# ============================================================
# 量子回路シミュレーション エンドポイント
# ============================================================
@app.post("/api/simulate/quantum")
def simulate_quantum_endpoint(request: QuantumRequest):
    import fastapi
    logger.info(f"量子シミュレーション要求受信: {request.num_qubits} qubits, {request.shots} shots, {len(request.circuit)} ops")
    results = run_simulation(request.circuit, shots=request.shots, num_qubits=request.num_qubits)
    
    if 'error' in results:
        raise fastapi.HTTPException(status_code=400, detail=results['error'])
    
    return results
