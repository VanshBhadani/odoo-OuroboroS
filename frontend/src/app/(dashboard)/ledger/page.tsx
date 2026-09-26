'use client';
import { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Move } from '@/types';

export default function LedgerPage() {
  const [moves, setMoves] = useState<Move[]>([]);

  useEffect(() => {
    api.get('/ledger/moves').then(res => setMoves(res.data.items)).catch(console.error);
  }, []);

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6 text-slate-800">Move History</h1>
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
