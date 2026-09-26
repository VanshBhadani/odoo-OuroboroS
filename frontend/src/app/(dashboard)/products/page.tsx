'use client';
import { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Product } from '@/types';
import { X, PackagePlus } from 'lucide-react';

export default function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [isModalOpen, setModalOpen] = useState(false);
  
  // Form State
  const [sku, setSku] = useState('');
  const [name, setName] = useState('');
  const [uom, setUom] = useState('Units');
  const [submitting, setSubmitting] = useState(false);

  const fetchProducts = async () => {
    try {
      const res = await api.get('/products/?page_size=100');
      setProducts(res.data.items);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchProducts();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api.post('/products/', {
        sku,
        name,
        uom,
        min_stock_alert: 0
      });
      setModalOpen(false);
      setSku('');
      setName('');
      fetchProducts();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to create product');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-slate-800">Products Catalog</h1>
        <button onClick={() => setModalOpen(true)} className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700 flex items-center gap-2">
          <PackagePlus size={18} /> New Product
        </button>
      </div>

      <div className="bg-white rounded shadow overflow-hidden border border-slate-200">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-600 border-b border-slate-200">
            <tr>
              <th className="p-4 font-semibold uppercase tracking-wider text-xs">SKU</th>
              <th className="p-4 font-semibold uppercase tracking-wider text-xs">Name</th>
              <th className="p-4 font-semibold uppercase tracking-wider text-xs">Category</th>
              <th className="p-4 font-semibold uppercase tracking-wider text-xs text-right">Physical Stock</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {products.map(p => {
              // Calculate total stock from all locations
              const totalStock = (p as any).stock_by_location?.reduce((sum: number, loc: any) => sum + parseFloat(loc.quantity || '0'), 0) || 0;
              
              return (
                <tr key={p.id} className="hover:bg-slate-50">
                  <td className="p-4 font-medium text-slate-900">{p.sku}</td>
                  <td className="p-4 text-slate-800">{p.name}</td>
                  <td className="p-4"><span className="bg-slate-100 px-2 py-1 rounded text-xs text-slate-600">{p.category || 'Uncategorized'}</span></td>
                  <td className="p-4 text-right font-semibold text-slate-700">{totalStock} {p.uom}</td>
                </tr>
              );
            })}
            {products.length === 0 && (
              <tr>
                <td colSpan={4} className="p-8 text-center text-slate-400">
                  No products found. Add a new product to get started.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {isModalOpen && (
        <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md">
            <div className="flex justify-between items-center p-6 border-b">
              <h2 className="text-xl font-bold text-slate-800">Create New Product</h2>
              <button onClick={() => setModalOpen(false)} className="text-slate-400 hover:text-slate-600"><X size={24} /></button>
            </div>
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1">Product Name</label>
                <input required type="text" className="w-full border p-2 rounded focus:ring-2 focus:ring-blue-500 outline-none" placeholder="e.g. Mechanical Keyboard" value={name} onChange={e => setName(e.target.value)} />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1">SKU</label>
                  <input required type="text" className="w-full border p-2 rounded focus:ring-2 focus:ring-blue-500 outline-none uppercase" placeholder="e.g. KB-001" value={sku} onChange={e => setSku(e.target.value.toUpperCase())} />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1">Unit of Measure</label>
                  <input required type="text" className="w-full border p-2 rounded focus:ring-2 focus:ring-blue-500 outline-none" placeholder="e.g. Units, kg, L" value={uom} onChange={e => setUom(e.target.value)} />
                </div>
              </div>
              <div className="pt-4 flex justify-end gap-3">
                <button type="button" onClick={() => setModalOpen(false)} className="px-4 py-2 text-slate-600 font-medium hover:bg-slate-200 rounded transition-colors">Cancel</button>
                <button type="submit" disabled={submitting} className="px-4 py-2 bg-blue-600 text-white font-medium hover:bg-blue-700 rounded shadow-sm disabled:opacity-50 transition-colors">
                  {submitting ? 'Creating...' : 'Create Product'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
