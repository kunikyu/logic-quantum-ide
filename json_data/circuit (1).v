// Quantum IDE — Structural Verilog
module circuit(
  input  n_gate_Switch_178703, n_gate_Switch_178703, n_gate_Clock_1787035,
  output n_gate_LED_178703531, n_gate_LED_178703531
);

  // 内部ワイヤ
  wire n_gate_AND_178703526_o0;
  wire n_gate_XOR_178703528_o0;

  // ゲートインスタンス
  and(n_gate_AND_178703526_o0,n_gate_Switch_178703,n_gate_Switch_178703);
  xor(n_gate_XOR_178703528_o0,n_gate_Switch_178703,n_gate_Clock_1787035);

  // 出力代入
  assign n_gate_LED_178703531 = n_gate_AND_178703526_o0;
  assign n_gate_LED_178703531 = n_gate_XOR_178703528_o0;

endmodule