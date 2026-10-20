// frontend/src/hooks/useCircuitExport.ts
import { useState } from 'react';
import useCircuitStore from '../store/useCircuitStore';
import { API_BASE } from '../api/client';

export function useCircuitExport() {
  const [showExport, setShowExport] = useState(false);
  const { nodes, edges } = useCircuitStore();

  const downloadFile = (content: string, filename: string) => {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([content]));
    a.download = filename;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const exportFetch = async (path: string, filename: string) => {
    setShowExport(false);
    try {
      const res = await fetch(`${API_BASE}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nodes, edges }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      downloadFile(await res.text(), filename);
    } catch {
      alert('エクスポートに失敗しました。バックエンドが起動しているか確認してください。');
    }
  };

  return {
    showExport,
    setShowExport,
    downloadFile,
    exportFetch,
  };
}
