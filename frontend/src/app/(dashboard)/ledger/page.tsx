'use client';
import { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Move } from '@/types';
import { Download } from 'lucide-react';
import { downloadCSV } from '@/lib/export';

export default function LedgerPage() {
  const [moves, setMoves] = useState<Move[]>([]);

  useEffect(() => {
    api.get('/ledger/moves').then(res => setMoves(res.data.items)).catch(console.error);
  }, []);

  const handleExport = () => {
    const headers = ['Date', 'Reference', 'Product', 'From Location', 'To Location', 'Quantity'];
    const rows = moves.map(m => [
      new Date(m.created_at).toLocaleString(),
      m.reference,
      m.product_name,
      m.from_location_code,
      m.to_location_code,
      m.quantity
    ]);
    downloadCSV('StockSense_MoveHistory', headers, rows);
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-slate-800">Move History</h1>
        <button onClick={handleExport} className="bg-white border border-slate-300 text-slate-700 px-4 py-2 rounded shadow-sm hover:bg-slate-50 flex items-center gap-2">
          <Download size={18} /> Export CSV
        </button>
      </div>
      <div className="bg-white rounded shadow overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-100 text-slate-600 border-b">
            <tr>
              <th className="p-4 font-semibold">Date</th>
              <th className="p-4 font-semibold">Reference</th>
              <th className="p-4 font-semibold">Product</th>
              <th className="p-4 font-semibold">From</th>
              <th className="p-4 font-semibold">To</th>
              <th className="p-4 font-semibold text-right">Qty</th>
            </tr>
          </thead>
          <tbody>
            {moves.map(m => (
              <tr key={m.id} className="border-b hover:bg-slate-50">
                <td className="p-4">{new Date(m.created_at).toLocaleString()}</td>
                <td className="p-4 font-medium text-blue-600">{m.reference}</td>
                <td className="p-4">{m.product_name}</td>
                <td className="p-4">{m.from_location_code}</td>
                <td className="p-4">{m.to_location_code}</td>
                <td className="p-4 text-right font-semibold">{m.quantity}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

