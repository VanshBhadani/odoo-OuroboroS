'use client';
import { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Operation, Product, Location } from '@/types';
import OperationTable from '@/components/operations/OperationTable';
import OperationModal from '@/components/operations/OperationModal';
import { PackagePlus } from 'lucide-react';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

export default function ReceiptsPage() {
  const [operations, setOperations] = useState<Operation[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [companyName, setCompanyName] = useState('StockSense Inc.');
  const [isModalOpen, setModalOpen] = useState(false);

  const fetchData = async () => {
    try {
      const [opsRes, prodRes, locRes, compRes] = await Promise.all([
        api.get('/dashboard/filter?operation_type=RECEIPT'),
        api.get('/products/?page_size=100'),
        api.get('/dashboard/locations'),
        api.get('/settings/company').catch(() => ({ data: { company_name: 'StockSense Inc.' } }))
      ]);
      setOperations(opsRes.data.items);
      setProducts(prodRes.data.items);
      setLocations(locRes.data.items);
      setCompanyName(compRes.data.company_name);
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
      alert(err.response?.data?.detail || 'Failed to validate');
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
      const vendorLoc = locations.find(l => l.location_type === 'VENDOR')?.id;
      if (!vendorLoc) throw new Error('System error: No VENDOR location found in the database. Please run the seeder.');

      // Create Header
      const opRes = await api.post('/operations/', {
        operation_type: 'RECEIPT',
        partner_name: data.partner_name,
        source_location_id: vendorLoc,
        dest_location_id: data.dest_location_id,
      });
      const opId = opRes.data.id;

      // Create Lines
      for (const line of data.lines) {
        await api.post(`/operations/${opId}/lines`, {
          product_id: line.product_id,
          quantity: line.quantity,
          source_location_id: vendorLoc,
          dest_location_id: data.dest_location_id
        });
      }

      // Validate
      await api.post(`/operations/${opId}/validate`);
      setModalOpen(false);
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail || err.message || 'Error creating receipt');
    }
  };

  const handleDownloadPdf = (op: Operation) => {
    const doc = new jsPDF();
    
    // Header
    doc.setFontSize(22);
    doc.setTextColor(30, 41, 59); // slate-800
    doc.text(companyName, 14, 22);

    doc.setFontSize(14);
    doc.text('Goods Receipt', 14, 32);
    
    doc.setFontSize(10);
    doc.setTextColor(100, 116, 139); // slate-500
    doc.text(`Reference: ${op.reference}`, 14, 42);
    doc.text(`Date: ${new Date(op.validated_at || op.created_at).toLocaleString()}`, 14, 48);
    doc.text(`Vendor: ${op.partner_name || 'N/A'}`, 14, 54);
    doc.text(`Status: ${op.status}`, 14, 60);

    // Prepare table data
    const tableData = op.lines.map((line: any) => {
      const prod = products.find(p => p.id === line.product_id);
      return [
        prod?.sku || 'Unknown',
        prod?.name || 'Unknown',
        line.quantity,
        prod?.uom || 'Units'
      ];
    });

    autoTable(doc, {
      startY: 70,
      head: [['SKU', 'Product Name', 'Quantity', 'UOM']],
      body: tableData,
      theme: 'grid',
      headStyles: { fillColor: [37, 99, 235] }, // Tailwind blue-600
      styles: { fontSize: 10 }
    });

    doc.save(`${op.reference.replace(/\//g, '_')}_Receipt.pdf`);
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-slate-800 flex items-center gap-2">
            <PackagePlus className="text-blue-600" /> Receipts
          </h1>
          <p className="text-slate-500 mt-1">Receive incoming stock from suppliers.</p>
        </div>
        <button onClick={() => setModalOpen(true)} className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700 transition-colors font-medium">
          New Receipt
        </button>
      </div>

      <OperationTable operations={operations} onValidate={handleValidate} onDelete={handleDelete} onDownloadPdf={handleDownloadPdf} />

      <OperationModal
        isOpen={isModalOpen}
        onClose={() => setModalOpen(false)}
        title="New Receipt"
        operationType="RECEIPT"
        products={products}
        locations={locations}
        onSubmit={handleSubmit}
      />
    </div>
  );
}
