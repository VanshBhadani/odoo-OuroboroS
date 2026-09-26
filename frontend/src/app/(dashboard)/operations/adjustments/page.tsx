'use client';
import { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Operation, Product, Location } from '@/types';
import OperationTable from '@/components/operations/OperationTable';
import { FileWarning, X } from 'lucide-react';

export default function AdjustmentsPage() {
  const [operations, setOperations] = useState<Operation[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [isModalOpen, setModalOpen] = useState(false);

  // Form State
  const [selectedProductId, setSelectedProductId] = useState('');
  const [selectedLocId, setSelectedLocId] = useState('');
  const [countedQty, setCountedQty] = useState<number | ''>('');
  const [submitting, setSubmitting] = useState(false);

  const fetchData = async () => {
    try {
      const [opsRes, prodRes, locRes] = await Promise.all([
        api.get('/dashboard/filter?operation_type=ADJUSTMENT'),
        api.get('/products/?page_size=100'),
        api.get('/dashboard/locations')
      ]);
      setOperations(opsRes.data.items);
      setProducts(prodRes.data.items);
      setLocations(locRes.data.items);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Compute Delta
  const selectedProduct = products.find(p => p.id === selectedProductId) as any;
  const recordedStock = selectedProduct?.stock_by_location?.find((l: any) => l.location_id === selectedLocId)?.quantity || 0;
  const delta = (typeof countedQty === 'number' ? countedQty : 0) - recordedStock;

  const handleDelete = async (id: string) => {
    try {
      await api.delete(`/operations/${id}`);
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to delete operation');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProductId || !selectedLocId || countedQty === '') return;
    setSubmitting(true);
    try {
      const opRes = await api.post('/operations/', {
        operation_type: 'ADJUSTMENT',
        notes: `Inventory adjustment for Delta: ${delta > 0 ? '+' : ''}${delta}`,
        source_location_id: selectedLocId,
        dest_location_id: selectedLocId,
      });
      const opId = opRes.data.id;

      await api.post(`/operations/${opId}/lines`, {
        product_id: selectedProductId,
        quantity: countedQty, // Backend takes the physical count directly for adjustments
        source_location_id: selectedLocId,
        dest_location_id: selectedLocId
      });

      await api.post(`/operations/${opId}/validate`);
      
      setModalOpen(false);
      setSelectedProductId('');
      setSelectedLocId('');
      setCountedQty('');
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail || err.message || 'Error processing adjustment');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-slate-800 flex items-center gap-2">
            <FileWarning className="text-blue-600" /> Stock Adjustments
          </h1>
          <p className="text-slate-500 mt-1">Resolve mismatches between physical and recorded stock.</p>
        </div>
        <button onClick={() => setModalOpen(true)} className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700 transition-colors font-medium">
          New Adjustment
        </button>
      </div>

      <OperationTable operations={operations} onDelete={handleDelete} />

      {isModalOpen && (
        <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg">
            <div className="flex justify-between items-center p-6 border-b">
              <h2 className="text-xl font-bold text-slate-800">Physical Stock Count</h2>
              <button onClick={() => setModalOpen(false)} className="text-slate-400 hover:text-slate-600"><X size={24} /></button>
            </div>
            <form onSubmit={handleSubmit} className="p-6 space-y-5">
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1">Product</label>
                <select required className="w-full border p-2 rounded focus:ring-2 focus:ring-blue-500 outline-none" value={selectedProductId} onChange={e => setSelectedProductId(e.target.value)}>
                  <option value="">Select product...</option>
                  {products.map(p => <option key={p.id} value={p.id}>{p.name} [{p.sku}]</option>)}
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1">Location to Adjust</label>
                <select required className="w-full border p-2 rounded focus:ring-2 focus:ring-blue-500 outline-none" value={selectedLocId} onChange={e => setSelectedLocId(e.target.value)}>
                  <option value="">Select location...</option>
                  {locations.filter(l => l.location_type === 'INTERNAL').map(l => (
                    <option key={l.id} value={l.id}>{l.name} ({l.code})</option>
                  ))}
                </select>
              </div>

              {selectedProductId && selectedLocId && (
                <div className="bg-slate-50 border p-4 rounded-lg flex items-center justify-between">
                  <div>
                    <div className="text-xs text-slate-500 font-semibold uppercase tracking-wider">Recorded Stock</div>
                    <div className="text-2xl font-bold text-slate-800">{recordedStock}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs text-slate-500 font-semibold uppercase tracking-wider">Delta</div>
                    <div className="text-lg font-bold flex items-center justify-end gap-2">
                      {delta !== 0 && (
                        <span className={`px-2 py-0.5 rounded-full text-xs ${delta > 0 ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}`}>
                          {delta > 0 ? '+' : ''}{delta} (Stock {delta > 0 ? 'Gain' : 'Loss'})
                        </span>
                      )}
                      {delta === 0 ? <span className="text-slate-400">Match</span> : <span className={delta > 0 ? 'text-emerald-600' : 'text-red-600'}>{Math.abs(delta)}</span>}
                    </div>
                  </div>
                </div>
              )}

              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1">Counted Physical Quantity</label>
                <input required type="number" min="0" step="0.01" className="w-full border p-2 rounded focus:ring-2 focus:ring-blue-500 outline-none text-lg" value={countedQty} onChange={e => setCountedQty(e.target.value === '' ? '' : parseFloat(e.target.value))} />
              </div>

              <div className="pt-4 flex justify-end gap-3">
                <button type="button" onClick={() => setModalOpen(false)} className="px-4 py-2 text-slate-600 font-medium hover:bg-slate-200 rounded transition-colors">Cancel</button>
                <button type="submit" disabled={submitting || delta === 0 || !selectedProductId || !selectedLocId} className="px-4 py-2 bg-blue-600 text-white font-medium hover:bg-blue-700 rounded shadow-sm disabled:opacity-50 transition-colors">
                  {submitting ? 'Applying...' : 'Apply Adjustment'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
