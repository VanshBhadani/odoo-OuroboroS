'use client';
import { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Operation, Product, Location } from '@/types';
import OperationTable from '@/components/operations/OperationTable';
import OperationModal from '@/components/operations/OperationModal';
import { ArrowRightLeft } from 'lucide-react';

export default function TransfersPage() {
  const [operations, setOperations] = useState<Operation[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [isModalOpen, setModalOpen] = useState(false);

  const fetchData = async () => {
    try {
      const [opsRes, prodRes, locRes] = await Promise.all([
        api.get('/dashboard/filter?operation_type=INTERNAL'),
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

  const handleValidate = async (id: string) => {
    try {
      await api.post(`/operations/${id}/validate`);
      alert('Operation validated successfully!');
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to validate. Insufficient stock?');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.delete(`/operations/${id}`);
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to delete operation');
    }
  };

  const handleSubmit = async (data: any) => {
    try {
      const opRes = await api.post('/operations/', {
        operation_type: 'INTERNAL',
        source_location_id: data.source_location_id,
        dest_location_id: data.dest_location_id,
      });
      const opId = opRes.data.id;

      for (const line of data.lines) {
        await api.post(`/operations/${opId}/lines`, {
          product_id: line.product_id,
          quantity: line.quantity,
          source_location_id: data.source_location_id,
          dest_location_id: data.dest_location_id
        });
      }

      await api.post(`/operations/${opId}/validate`);
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Error creating transfer');
    }
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-slate-800 flex items-center gap-2">
            <ArrowRightLeft className="text-blue-600" /> Internal Transfers
          </h1>
          <p className="text-slate-500 mt-1">Move stock between your internal locations.</p>
        </div>
        <button onClick={() => setModalOpen(true)} className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700 transition-colors font-medium">
          New Transfer
        </button>
      </div>

      <OperationTable operations={operations} onValidate={handleValidate} onDelete={handleDelete} />

      <OperationModal
        isOpen={isModalOpen}
        onClose={() => setModalOpen(false)}
        title="New Internal Transfer"
        operationType="INTERNAL"
        products={products}
        locations={locations}
        onSubmit={handleSubmit}
      />
    </div>
  );
}
