'use client';
import { useEffect, useState } from 'react';
import api from '@/lib/api';

export default function Dashboard() {
  const [kpis, setKpis] = useState<any>(null);

  useEffect(() => {
    api.get('/dashboard/kpis').then(res => setKpis(res.data)).catch(console.error);
  }, []);

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6 text-slate-800">Dashboard</h1>
      {kpis && (
        <div className="grid grid-cols-4 gap-4 mb-8">
          <div className="bg-white p-6 rounded shadow border-l-4 border-blue-500">
            <div className="text-sm text-slate-500">Total Products</div>
            <div className="text-3xl font-bold">{kpis.total_products}</div>
          </div>
          <div className="bg-white p-6 rounded shadow border-l-4 border-yellow-500">
            <div className="text-sm text-slate-500">Low Stock Items</div>
            <div className="text-3xl font-bold">{kpis.low_stock_count}</div>
          </div>
          <div className="bg-white p-6 rounded shadow border-l-4 border-green-500">
            <div className="text-sm text-slate-500">Pending Receipts</div>
            <div className="text-3xl font-bold">{kpis.pending_receipts}</div>
          </div>
          <div className="bg-white p-6 rounded shadow border-l-4 border-purple-500">
            <div className="text-sm text-slate-500">Pending Deliveries</div>
            <div className="text-3xl font-bold">{kpis.pending_deliveries}</div>
          </div>
        </div>
      )}
      <div className="bg-white rounded shadow p-6">
        <h2 className="text-xl font-bold mb-4 text-slate-800">Recent Operations</h2>
        <div className="text-slate-500 italic">Select an operation category from the left sidebar to view details.</div>
      </div>
    </div>
  );
}
