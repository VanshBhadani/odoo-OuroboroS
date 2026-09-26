'use client';
import { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Product } from '@/types';

export default function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([]);

  useEffect(() => {
    api.get('/products/').then(res => setProducts(res.data.items)).catch(console.error);
  }, []);

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-slate-800">Products Catalog</h1>
        <button className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700">New Product</button>
      </div>
      <div className="bg-white rounded shadow overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-slate-100 text-slate-600 border-b">
            <tr>
              <th className="p-4 font-semibold">SKU</th>
              <th className="p-4 font-semibold">Name</th>
              <th className="p-4 font-semibold">Category</th>
              <th className="p-4 font-semibold">Stock</th>
            </tr>
          </thead>
          <tbody>
            {products.map(p => (
              <tr key={p.id} className="border-b hover:bg-slate-50">
                <td className="p-4 font-medium">{p.sku}</td>
                <td className="p-4">{p.name}</td>
                <td className="p-4"><span className="bg-slate-100 px-2 py-1 rounded text-xs">{p.category}</span></td>
                <td className="p-4">{p.stock_quantity ?? 0} {p.uom}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
