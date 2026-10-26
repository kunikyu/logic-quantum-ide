// frontend/src/constants/gates.ts
import type { GateType } from '../store/useCircuitStore';

export interface GateVisualConfig {
  label: string;
  category: 'logic' | 'quantum';
  borderColor: string;
  bgColor: string;
  textColor: string;
  glowColor: string;
  handles: { inputs: number; outputs: number };
}

export const GATE_CONFIGS: Record<GateType, GateVisualConfig> = {
  AND:      { label: 'AND',   category: 'logic',   borderColor: '#5b8df6', bgColor: 'rgba(91,141,246,0.10)',  textColor: '#7eb3fa', glowColor: 'rgba(91,141,246,0.25)', handles: { inputs: 2, outputs: 1 } },
  OR:       { label: 'OR',    category: 'logic',   borderColor: '#38bdf8', bgColor: 'rgba(56,189,248,0.10)',  textColor: '#7dd3fc', glowColor: 'rgba(56,189,248,0.25)', handles: { inputs: 2, outputs: 1 } },
  NOT:      { label: 'NOT',   category: 'logic',   borderColor: '#f87171', bgColor: 'rgba(248,113,113,0.10)', textColor: '#fca5a5', glowColor: 'rgba(248,113,113,0.25)', handles: { inputs: 1, outputs: 1 } },
  NAND:     { label: 'NAND',  category: 'logic',   borderColor: '#fb923c', bgColor: 'rgba(251,146,60,0.10)',  textColor: '#fdba74', glowColor: 'rgba(251,146,60,0.25)', handles: { inputs: 2, outputs: 1 } },
  NOR:      { label: 'NOR',   category: 'logic',   borderColor: '#eab308', bgColor: 'rgba(234,179,8,0.10)',   textColor: '#fde047', glowColor: 'rgba(234,179,8,0.25)', handles: { inputs: 2, outputs: 1 } },
  XOR:      { label: 'XOR',   category: 'logic',   borderColor: '#34d399', bgColor: 'rgba(52,211,153,0.10)',  textColor: '#6ee7b7', glowColor: 'rgba(52,211,153,0.25)', handles: { inputs: 2, outputs: 1 } },
  Switch:   { label: 'SW',    category: 'logic',   borderColor: '#22d3a0', bgColor: 'rgba(34,211,160,0.10)',  textColor: '#5eead4', glowColor: 'rgba(34,211,160,0.25)', handles: { inputs: 0, outputs: 1 } },
  LED:      { label: 'LED',   category: 'logic',   borderColor: '#facc15', bgColor: 'rgba(250,204,21,0.10)',  textColor: '#fde68a', glowColor: 'rgba(250,204,21,0.30)', handles: { inputs: 1, outputs: 0 } },
  Clock:    { label: 'CLK',   category: 'logic',   borderColor: '#f59e0b', bgColor: 'rgba(245,158,11,0.10)',  textColor: '#fcd34d', glowColor: 'rgba(245,158,11,0.30)', handles: { inputs: 0, outputs: 1 } },
  SevenSeg: { label: '7-SEG', category: 'logic',   borderColor: '#e879f9', bgColor: 'rgba(232,121,249,0.10)', textColor: '#f0abfc', glowColor: 'rgba(232,121,249,0.25)', handles: { inputs: 4, outputs: 0 } },
  H:        { label: 'H',     category: 'quantum', borderColor: '#a855f7', bgColor: 'rgba(168,85,247,0.12)',  textColor: '#c084fc', glowColor: 'rgba(168,85,247,0.30)', handles: { inputs: 1, outputs: 1 } },
  X:        { label: 'X',     category: 'quantum', borderColor: '#818cf8', bgColor: 'rgba(129,140,248,0.12)', textColor: '#a5b4fc', glowColor: 'rgba(129,140,248,0.30)', handles: { inputs: 1, outputs: 1 } },
  Y:        { label: 'Y',     category: 'quantum', borderColor: '#6366f1', bgColor: 'rgba(99,102,241,0.12)',  textColor: '#818cf8', glowColor: 'rgba(99,102,241,0.30)', handles: { inputs: 1, outputs: 1 } },
  Z:        { label: 'Z',     category: 'quantum', borderColor: '#4f78c7', bgColor: 'rgba(79,120,199,0.12)',  textColor: '#91afe6', glowColor: 'rgba(79,120,199,0.30)', handles: { inputs: 1, outputs: 1 } },
  S:        { label: 'S',     category: 'quantum', borderColor: '#9333ea', bgColor: 'rgba(147,51,234,0.12)',  textColor: '#c084fc', glowColor: 'rgba(147,51,234,0.30)', handles: { inputs: 1, outputs: 1 } },
  T:        { label: 'T',     category: 'quantum', borderColor: '#c026d3', bgColor: 'rgba(192,38,211,0.12)',  textColor: '#e879f9', glowColor: 'rgba(192,38,211,0.30)', handles: { inputs: 1, outputs: 1 } },
  CX:       { label: 'CX',    category: 'quantum', borderColor: '#7c3aed', bgColor: 'rgba(124,58,237,0.12)',  textColor: '#a78bfa', glowColor: 'rgba(124,58,237,0.30)', handles: { inputs: 2, outputs: 2 } },
  CZ:       { label: 'CZ',    category: 'quantum', borderColor: '#7c3aed', bgColor: 'rgba(124,58,237,0.12)',  textColor: '#a78bfa', glowColor: 'rgba(124,58,237,0.30)', handles: { inputs: 2, outputs: 2 } },
  CCX:      { label: 'CCX',   category: 'quantum', borderColor: '#6d28d9', bgColor: 'rgba(109,40,217,0.12)',  textColor: '#8b5cf6', glowColor: 'rgba(109,40,217,0.30)', handles: { inputs: 3, outputs: 3 } },
  CCZ:      { label: 'CCZ',   category: 'quantum', borderColor: '#4f78c7', bgColor: 'rgba(79,120,199,0.12)',  textColor: '#91afe6', glowColor: 'rgba(79,120,199,0.30)', handles: { inputs: 3, outputs: 3 } },
  MCX:      { label: 'MCX',   category: 'quantum', borderColor: '#6d28d9', bgColor: 'rgba(109,40,217,0.12)',  textColor: '#8b5cf6', glowColor: 'rgba(109,40,217,0.30)', handles: { inputs: 4, outputs: 4 } },
  MCZ:      { label: 'MCZ',   category: 'quantum', borderColor: '#4f78c7', bgColor: 'rgba(79,120,199,0.12)',  textColor: '#91afe6', glowColor: 'rgba(79,120,199,0.30)', handles: { inputs: 4, outputs: 4 } },
  CTRL:     { label: 'CTRL',  category: 'quantum', borderColor: '#6d28d9', bgColor: 'rgba(109,40,217,0.12)',  textColor: '#8b5cf6', glowColor: 'rgba(109,40,217,0.30)', handles: { inputs: 1, outputs: 1 } },
  Measure:  { label: 'M',     category: 'quantum', borderColor: '#db2777', bgColor: 'rgba(219,39,119,0.12)',  textColor: '#f472b6', glowColor: 'rgba(219,39,119,0.30)', handles: { inputs: 1, outputs: 1 } },
  CustomIC: { label: 'IC',    category: 'logic',   borderColor: '#10b981', bgColor: 'rgba(16,185,129,0.10)',  textColor: '#34d399', glowColor: 'rgba(16,185,129,0.25)', handles: { inputs: 2, outputs: 1 } },
  Junction: { label: 'JNC',   category: 'logic',   borderColor: '#60a5fa', bgColor: 'rgba(96,165,250,0.12)',  textColor: '#93c5fd', glowColor: 'rgba(96,165,250,0.40)', handles: { inputs: 1, outputs: 2 } },
};
