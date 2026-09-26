'use client';
import { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Operation, Product, Location } from '@/types';
import OperationTable from '@/components/operations/OperationTable';
import OperationModal from '@/components/operations/OperationModal';
import { PackageMinus } from 'lucide-react';

export default function DeliveriesPage() {
  const [operations, setOperations] = useState<Operation[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [isModalOpen, setModalOpen] = useState(false);

  const fetchData = async () => {
    try {
      const [opsRes, prodRes, locRes] = await Promise.all([
        api.get('/dashboard/filter?operation_type=DELIVERY'),
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
      const customerLoc = locations.find(l => l.location_type === 'CUSTOMER')?.id;
      if (!customerLoc) throw new Error('System error: No CUSTOMER location found in the database. Please run the seeder.');

      const opRes = await api.post('/operations/', {
        operation_type: 'DELIVERY',
        partner_name: data.partner_name,
        source_location_id: data.source_location_id,
        dest_location_id: customerLoc,
      });
      const opId = opRes.data.id;

      for (const line of data.lines) {
        await api.post(`/operations/${opId}/lines`, {
          product_id: line.product_id,
          quantity: line.quantity,
          source_location_id: data.source_location_id,
          dest_location_id: customerLoc
        });
      }

      await api.post(`/operations/${opId}/validate`);
      setModalOpen(false);
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail || err.message || 'Error creating delivery');
    }
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-slate-800 flex items-center gap-2">
            <PackageMinus className="text-blue-600" /> Deliveries
          </h1>
          <p className="text-slate-500 mt-1">Ship outgoing stock to customers.</p>
        </div>
        <button onClick={() => setModalOpen(true)} className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700 transition-colors font-medium">
          New Delivery
        </button>
      </div>

      <OperationTable operations={operations} onValidate={handleValidate} onDelete={handleDelete} />

      <OperationModal
        isOpen={isModalOpen}
        onClose={() => setModalOpen(false)}
        title="New Delivery Order"
        operationType="DELIVERY"
        products={products}
        locations={locations}
        onSubmit={handleSubmit}
      />
    </div>
  );
}
