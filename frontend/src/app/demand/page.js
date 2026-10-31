'use client';

import React, { useState, useEffect } from 'react';
import AppLayout from '@/components/layout/AppLayout';
import Badge from '@/components/ui/Badge';
import Modal from '@/components/ui/Modal';
import RecommendationBanner, { takeRecommendationParams } from '@/components/ui/RecommendationBanner';
import api from '@/lib/api';
import {
  Package,
  TrendingUp,
  AlertTriangle,
  Plus,
  History,
  Info,
  Calendar,
  CheckCircle2,
  Loader2,
  RefreshCw,
  Search,
  SlidersHorizontal,
  ArrowUpRight,
  ShieldCheck,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

export default function DemandPage() {
  const [products, setProducts] = useState([]);
  const [forecasts, setForecasts] = useState([]);
  const [forecastMeta, setForecastMeta] = useState(null);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [salesHistory, setSalesHistory] = useState(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  // Modals
  const [showAddModal, setShowAddModal] = useState(false);
  const [showAdjustModal, setShowAdjustModal] = useState(false);
  const [showMovementsModal, setShowMovementsModal] = useState(false);
  const [movementsList, setMovementsList] = useState([]);

  // Form states
  const [newProduct, setNewProduct] = useState({
    name: '',
    category: 'Grocery & Daily Essentials',
    cost_price: '',
    selling_price: '',
    current_stock: '',
    reorder_threshold: '15',
    unit: 'units',
  });

  const [adjustment, setAdjustment] = useState({
    adjustment_type: 'RESTOCK',
    quantity: 10,
    notes: '',
  });

  const [submitting, setSubmitting] = useState(false);
  // Set when the restock popup was opened from an Overview recommendation
  const [prefillInfo, setPrefillInfo] = useState(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const [prodRes, fcRes] = await Promise.all([
        api.get('/products'),
        api.get('/demand/forecasts'),
      ]);
      setProducts(prodRes.data);
      setForecasts(fcRes.data.forecasts || []);
      setForecastMeta(fcRes.data);

      if (prodRes.data.length > 0 && !selectedProduct) {
        setSelectedProduct(prodRes.data[0]);
        loadSalesHistory(prodRes.data[0].product_id);
      }

      // Arrived from an Overview recommendation ("Restock Item"): open the restock popup
      // pre-filled with the recommended quantity. Nothing changes until the merchant confirms.
      const rec = takeRecommendationParams();
      if (rec && rec.rec === 'restock') {
        const target = prodRes.data.find((p) => p.product_id === rec.product_id);
        if (target) {
          setSelectedProduct(target);
          loadSalesHistory(target.product_id);
          setAdjustment({
            adjustment_type: 'RESTOCK',
            quantity: Math.max(1, parseInt(rec.qty || '10', 10) || 10),
            notes: `Recommended on Overview (${rec.reason || 'Restock Priority'})`,
          });
          setPrefillInfo({ reason: rec.reason || 'Restock Priority', qty: rec.qty });
          setShowAdjustModal(true);
        }
      }
    } catch (err) {
      console.error('Failed to load demand data:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadSalesHistory = async (productId) => {
    setHistoryLoading(true);
    try {
      const res = await api.get(`/demand/sales-history/${productId}?days=30`);
      setSalesHistory(res.data);
    } catch (err) {
      console.error('Error fetching sales history:', err);
    } finally {
      setHistoryLoading(false);
    }
  };

  const loadMovements = async (productId) => {
    try {
      const res = await api.get(`/products/${productId}/movements`);
      setMovementsList(res.data);
      setShowMovementsModal(true);
    } catch (err) {
      console.error('Error fetching movements:', err);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSelectProduct = (p) => {
    setSelectedProduct(p);
    loadSalesHistory(p.product_id);
  };

  const handleCreateProduct = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api.post('/products', {
        name: newProduct.name,
        category: newProduct.category,
        cost_price: parseFloat(newProduct.cost_price),
        selling_price: parseFloat(newProduct.selling_price),
        current_stock: parseInt(newProduct.current_stock, 10),
        reorder_threshold: parseInt(newProduct.reorder_threshold, 10),
        unit: newProduct.unit,
      });
      setShowAddModal(false);
      setNewProduct({
        name: '',
        category: 'Grocery & Daily Essentials',
        cost_price: '',
        selling_price: '',
        current_stock: '',
        reorder_threshold: '15',
        unit: 'units',
      });
      loadData();
    } catch (err) {
      console.error(err);
      alert('Failed to create product.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleAdjustInventory = async (e) => {
    e.preventDefault();
    if (!selectedProduct) return;
    setSubmitting(true);
    try {
      await api.post(`/products/${selectedProduct.product_id}/adjust-inventory`, {
        adjustment_type: adjustment.adjustment_type,
        quantity: parseInt(adjustment.quantity, 10),
        notes: adjustment.notes,
      });
      setShowAdjustModal(false);
      setPrefillInfo(null);
      setAdjustment({ adjustment_type: 'RESTOCK', quantity: 10, notes: '' });
      loadData();
      loadSalesHistory(selectedProduct.product_id);
    } catch (err) {
      console.error(err);
      alert('Failed to adjust inventory.');
    } finally {
      setSubmitting(false);
    }
  };

  const filteredProducts = products.filter((p) =>
    p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.category.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const selectedForecast = forecasts.find(
    (f) => f.product_id === selectedProduct?.product_id
  );

  return (
    <AppLayout
      title="Demand & Inventory"
      subtitle="Catalog velocity, 7-day projected demand, and audited inventory movements"
    >
      {/* Top Controls: Search + Add Product */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-1">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-stone-200/90 bg-white text-stone-700 text-xs font-semibold shadow-2xs">
            <Calendar className="w-3.5 h-3.5 text-[#16181a]" />
            <span>7-Day Demand Forecast Cycle</span>
          </div>
          <span className="text-xs text-stone-400 font-medium hidden sm:inline">
            Deterministic weekday weighting and safety buffers
          </span>
        </div>

        {/* Right Action: Search + Add Product */}
        <div className="flex items-center gap-2.5">
          <div className="relative w-full sm:w-64">
            <Search className="w-3.5 h-3.5 text-stone-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search catalog items..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 rounded-full bg-white border border-stone-200/90 text-xs focus:outline-hidden focus:border-[#16181a] focus:ring-1 focus:ring-[#16181a]/20 shadow-2xs"
            />
          </div>

          <button
            onClick={() => setShowAddModal(true)}
            className="px-4 py-1.5 rounded-full bg-[#16181a] hover:bg-stone-800 text-white font-bold text-xs flex items-center gap-1.5 shadow-2xs transition-all shrink-0 cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5 text-[#e0fd53]" />
            <span>Add Product</span>
          </button>
        </div>
      </div>

      {/* Main Grid: Products Table & Forecasting Deep Dive */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left Column: Product Catalog Table */}
        <div className="lg:col-span-7 bg-white rounded-[28px] border border-stone-200/90 shadow-[0_4px_24px_rgba(20,24,20,0.04)] p-6">
          <div className="flex items-center justify-between pb-3.5 border-b border-stone-100 mb-3.5">
            <h2 className="text-sm font-bold text-[#16181a] flex items-center gap-2">
              <Package className="w-4 h-4 text-stone-600" />
              <span>Active Product Catalog ({products.length})</span>
            </h2>
            <span className="text-[11px] text-stone-400 font-medium">Select item to view runway</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-stone-100 text-stone-400 font-semibold uppercase tracking-wider text-[10px]">
                  <th className="pb-3 pl-2">Product</th>
                  <th className="pb-3">Category</th>
                  <th className="pb-3 text-right">Selling Price</th>
                  <th className="pb-3 text-right">Current Stock</th>
                  <th className="pb-3 text-center">Status</th>
                  <th className="pb-3 text-right pr-2">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100">
                {filteredProducts.map((p) => {
                  const isSelected = selectedProduct?.product_id === p.product_id;
                  const isLow = p.current_stock <= p.reorder_threshold;
                  return (
                    <tr
                      key={p.product_id}
                      onClick={() => handleSelectProduct(p)}
                      className={`cursor-pointer transition-colors ${
                        isSelected ? 'bg-[#f7f8f4] font-semibold' : 'hover:bg-stone-50/80'
                      }`}
                    >
                      <td className="py-3 pl-2">
                        <p className="font-bold text-[#16181a] truncate max-w-[180px]">{p.name}</p>
                        <p className="text-[10px] text-stone-400">{p.unit}</p>
                      </td>
                      <td className="py-3 text-stone-500">{p.category}</td>
                      <td className="py-3 text-right font-bold text-stone-800">
                        {p.effective_selling_price && p.effective_selling_price < p.selling_price ? (
                          <div>
                            <span className="font-bold text-emerald-700 block">₹{p.effective_selling_price}</span>
                            <span className="text-[10px] line-through text-stone-400 font-normal">₹{p.selling_price}</span>
                          </div>
                        ) : (
                          <span>₹{p.selling_price}</span>
                        )}
                      </td>
                      <td className="py-3 text-right font-bold text-[#16181a]">{p.current_stock}</td>
                      <td className="py-3 text-center">
                        <Badge variant={isLow ? 'danger' : 'success'} size="sm">
                          {isLow ? 'Low Stock' : 'Healthy'}
                        </Badge>
                      </td>
                      <td className="py-3 text-right pr-2" onClick={(e) => e.stopPropagation()}>
                        <button
                          onClick={() => {
                            setSelectedProduct(p);
                            setShowAdjustModal(true);
                          }}
                          className="px-3 py-1 rounded-full bg-white hover:bg-[#16181a] hover:text-white text-stone-800 text-[11px] font-semibold transition-all border border-stone-200/90 shadow-2xs"
                        >
                          Adjust
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right Column: Selected Product Forecast & Runway Analysis */}
        <div className="lg:col-span-5 space-y-4">
          {selectedProduct ? (
            <div className="bg-white rounded-[28px] border border-stone-200/90 shadow-[0_4px_24px_rgba(20,24,20,0.04)] p-6">
              <div className="flex items-center justify-between pb-3.5 border-b border-stone-100">
                <div>
                  <h3 className="text-sm font-bold text-[#16181a] tracking-tight">{selectedProduct.name}</h3>
                  <p className="text-[11px] text-stone-400">
                    {selectedProduct.category} • Cost ₹{selectedProduct.cost_price} /{' '}
                    {selectedProduct.effective_selling_price && selectedProduct.effective_selling_price < selectedProduct.selling_price ? (
                      <span className="text-emerald-700 font-bold">
                        Promo ₹{selectedProduct.effective_selling_price} <span className="line-through font-normal text-stone-400">₹{selectedProduct.selling_price}</span>
                      </span>
                    ) : (
                      <span>Sell ₹{selectedProduct.selling_price}</span>
                    )}
                  </p>
                </div>
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => loadMovements(selectedProduct.product_id)}
                    className="px-3 py-1 rounded-full border border-stone-200/90 text-stone-700 hover:bg-stone-50 text-xs flex items-center gap-1 shadow-2xs transition-all font-semibold"
                    title="View movement audit log"
                  >
                    <History className="w-3.5 h-3.5 text-stone-500" />
                    <span className="text-[10px]">Audit</span>
                  </button>
                  <button
                    onClick={() => setShowAdjustModal(true)}
                    className="px-3.5 py-1 rounded-full bg-[#16181a] text-white hover:bg-stone-800 text-xs font-bold shadow-2xs transition-all"
                  >
                    Adjust Stock
                  </button>
                </div>
              </div>

              {/* Forecast Metrics Cards */}
              {selectedForecast && (
                <div className="mt-4 space-y-4">
                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-3.5 bg-[#f7f8f4] border border-stone-200/80 rounded-2xl">
                      <p className="text-[10px] font-bold text-stone-400 uppercase tracking-wider">7-Day Demand</p>
                      <p className="text-xl font-black text-[#16181a] mt-0.5">
                        {selectedForecast.total_forecasted_units} <span className="text-xs font-normal text-stone-400">{selectedProduct.unit}</span>
                      </p>
                      <p className="text-[10px] text-stone-500 mt-1 font-medium">
                        Est. Rev: ₹{selectedForecast.total_projected_revenue.toLocaleString('en-IN')}
                      </p>
                    </div>

                    <div className={`p-3.5 rounded-2xl border ${selectedForecast.stockout_risk ? 'bg-[#faeed6] border-[#f2d8a5] text-[#8c5208]' : 'bg-emerald-50/80 border-emerald-200/80 text-emerald-900'}`}>
                      <p className="text-[10px] font-bold uppercase tracking-wider">Inventory Runway</p>
                      <p className="text-xl font-black mt-0.5">
                        ~{selectedForecast.days_of_inventory_remaining} <span className="text-xs font-normal">days</span>
                      </p>
                      <p className="text-[10px] mt-1 font-semibold flex items-center gap-1">
                        {selectedForecast.stockout_risk ? (
                          <>
                            <AlertTriangle className="w-3 h-3 text-[#8c5208]" />
                            <span>Replenish required</span>
                          </>
                        ) : (
                          <>
                            <CheckCircle2 className="w-3 h-3 text-emerald-700" />
                            <span>Sufficient buffer</span>
                          </>
                        )}
                      </p>
                    </div>
                  </div>

                  {/* Sufficiency Warning Alert */}
                  {selectedForecast.data_sufficiency_warning && (
                    <div className="p-3 bg-[#f7f8f4] border border-stone-200/80 rounded-2xl flex items-start gap-2 text-[11px] text-stone-700">
                      <Info className="w-4 h-4 text-stone-600 shrink-0 mt-0.5" />
                      <div>
                        <strong className="text-[#16181a]">Model: </strong>
                        <span>{selectedForecast.method_used}</span>
                        <p className="mt-0.5 text-stone-500">{selectedForecast.data_sufficiency_warning}</p>
                      </div>
                    </div>
                  )}

                  {/* Daily 7-Day Forecast Breakdown */}
                  <div>
                    <h4 className="text-xs font-bold text-[#16181a] mb-2 flex items-center gap-1.5">
                      <Calendar className="w-3.5 h-3.5 text-stone-600" />
                      <span>Daily Demand Breakdown</span>
                    </h4>
                    <div className="grid grid-cols-7 gap-1 text-center">
                      {selectedForecast.daily_forecasts.map((df) => (
                        <div
                          key={df.date}
                          className={`p-2 rounded-xl border text-[10px] ${
                            df.is_weekend
                              ? 'bg-[#16181a] text-white font-bold border-stone-800'
                              : 'bg-[#f7f8f4] border-stone-200/70 text-stone-700'
                          }`}
                        >
                          <p className={`text-[9px] ${df.is_weekend ? 'text-[#e0fd53]' : 'text-stone-400'}`}>
                            {df.day_name.slice(0, 3)}
                          </p>
                          <p className="font-bold text-xs mt-0.5">{df.predicted_units}</p>
                          <p className={`text-[8px] ${df.is_weekend ? 'text-stone-300' : 'text-stone-400'}`}>
                            ₹{df.projected_revenue.toFixed(0)}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* 30-Day Product Sales History Chart */}
              <div className="mt-5 pt-4 border-t border-stone-100">
                <h4 className="text-xs font-bold text-[#16181a] mb-2 flex items-center gap-1.5">
                  <TrendingUp className="w-3.5 h-3.5 text-stone-600" />
                  <span>30-Day Actual Sales Trend</span>
                </h4>
                {historyLoading ? (
                  <div className="h-36 flex items-center justify-center">
                    <Loader2 className="w-5 h-5 text-[#16181a] animate-spin" />
                  </div>
                ) : salesHistory ? (
                  <div className="h-36 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={salesHistory.history} margin={{ top: 5, right: 5, left: -25, bottom: 0 }}>
                        <defs>
                          <linearGradient id="productSalesGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#16181a" stopOpacity={0.2} />
                            <stop offset="95%" stopColor="#16181a" stopOpacity={0.0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="2 2" vertical={false} stroke="#f0f2eb" />
                        <XAxis dataKey="date" tickFormatter={(v) => v.slice(5)} tick={{ fontSize: 9, fill: '#8c9288' }} />
                        <YAxis tick={{ fontSize: 9, fill: '#8c9288' }} />
                        <Tooltip
                          cursor={{ stroke: '#16181a', strokeWidth: 1.5, strokeDasharray: '3 3' }}
                          content={({ active, payload }) => {
                            if (!active || !payload || !payload.length) return null;
                            const pt = payload[0].payload;
                            return (
                              <div className="bg-[#16181a] border border-stone-700/80 p-3 rounded-2xl shadow-xl text-white text-xs select-none min-w-[130px] z-50">
                                <p className="text-[10px] uppercase font-bold text-stone-400 tracking-wider mb-1">
                                  {pt.date}
                                </p>
                                <div className="flex items-baseline gap-1.5">
                                  <span className="text-sm font-black text-[#e0fd53]">
                                    {pt.units_sold} units
                                  </span>
                                  <span className="text-[10px] text-stone-400">sold</span>
                                </div>
                              </div>
                            );
                          }}
                        />
                        <Area type="monotone" dataKey="units_sold" stroke="#16181a" strokeWidth={2} fill="url(#productSalesGrad)" fillOpacity={1} />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                ) : null}
              </div>
            </div>
          ) : (
            <div className="p-8 text-center bg-white rounded-[28px] border border-stone-200/90 shadow-xs">
              <Package className="w-8 h-8 text-stone-300 mx-auto mb-2" />
              <p className="text-xs text-stone-500">Select a product to view forecast runway</p>
            </div>
          )}
        </div>
      </div>

      {/* Add Product Modal */}
      <Modal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        title="Add Product to Catalog"
      >
        <form onSubmit={handleCreateProduct} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-stone-700 mb-1">Product Name</label>
            <input
              type="text"
              required
              value={newProduct.name}
              onChange={(e) => setNewProduct({ ...newProduct, name: e.target.value })}
              className="w-full px-3 py-2 rounded-xl border border-stone-200 text-xs focus:ring-2 focus:ring-[#16181a]"
              placeholder="e.g. Royal Basmati Rice 5kg"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">Category</label>
              <input
                type="text"
                required
                value={newProduct.category}
                onChange={(e) => setNewProduct({ ...newProduct, category: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-stone-200 text-xs focus:ring-2 focus:ring-[#16181a]"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">Unit of Measure</label>
              <input
                type="text"
                required
                value={newProduct.unit}
                onChange={(e) => setNewProduct({ ...newProduct, unit: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-stone-200 text-xs focus:ring-2 focus:ring-[#16181a]"
                placeholder="units, kg, packs"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">Cost Price (₹)</label>
              <input
                type="number"
                step="0.5"
                min="0.1"
                required
                value={newProduct.cost_price}
                onChange={(e) => setNewProduct({ ...newProduct, cost_price: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-stone-200 text-xs focus:ring-2 focus:ring-[#16181a]"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">Selling Price (₹)</label>
              <input
                type="number"
                step="0.5"
                min="0.1"
                required
                value={newProduct.selling_price}
                onChange={(e) => setNewProduct({ ...newProduct, selling_price: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-stone-200 text-xs focus:ring-2 focus:ring-[#16181a]"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">Starting Stock</label>
              <input
                type="number"
                min="0"
                required
                value={newProduct.current_stock}
                onChange={(e) => setNewProduct({ ...newProduct, current_stock: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-stone-200 text-xs focus:ring-2 focus:ring-[#16181a]"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-stone-700 mb-1">Reorder Threshold</label>
              <input
                type="number"
                min="0"
                required
                value={newProduct.reorder_threshold}
                onChange={(e) => setNewProduct({ ...newProduct, reorder_threshold: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-stone-200 text-xs focus:ring-2 focus:ring-[#16181a]"
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setShowAddModal(false)}
              className="px-4 py-2 rounded-full border border-stone-200 text-xs font-semibold text-stone-600 hover:bg-stone-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-5 py-2 rounded-full bg-[#16181a] hover:bg-stone-800 text-white text-xs font-bold shadow-xs transition-all"
            >
              {submitting ? 'Saving...' : 'Add Product'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Audited Inventory Adjustment Modal */}
      <Modal
        isOpen={showAdjustModal}
        onClose={() => {
          setShowAdjustModal(false);
          setPrefillInfo(null);
        }}
        title={selectedProduct ? `Adjust Stock: ${selectedProduct.name}` : 'Adjust Inventory'}
      >
        <form onSubmit={handleAdjustInventory} className="space-y-4">
          {prefillInfo && (
            <RecommendationBanner source="Overview" reason={prefillInfo.reason}>
              Recommended restock: <strong>+{prefillInfo.qty} units</strong> to cover the next 2 weeks of forecast demand plus a safety buffer.
            </RecommendationBanner>
          )}
          <div className="p-3 bg-[#f7f8f4] rounded-2xl text-xs text-stone-700 border border-stone-200/70">
            <p>Current On-Hand Stock: <strong>{selectedProduct?.current_stock} {selectedProduct?.unit}</strong></p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-stone-700 mb-1">Adjustment Type</label>
            <select
              value={adjustment.adjustment_type}
              onChange={(e) => setAdjustment({ ...adjustment, adjustment_type: e.target.value })}
              className="w-full px-3 py-2 rounded-xl border border-stone-200 text-xs focus:ring-2 focus:ring-[#16181a] bg-white"
            >
              <option value="RESTOCK">RESTOCK (Inward Delivery / Supplier Shipment)</option>
              <option value="DAMAGE_LOSS">DAMAGE / LOSS (Spillage, Expiry, or Breakage)</option>
              <option value="AUDIT_CORRECTION">AUDIT CORRECTION (Physical Count Discrepancy)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-stone-700 mb-1">
              Quantity to {adjustment.adjustment_type === 'RESTOCK' ? 'Add' : 'Deduct / Adjust'}
            </label>
            <input
              type="number"
              min="1"
              required
              value={adjustment.quantity}
              onChange={(e) => setAdjustment({ ...adjustment, quantity: e.target.value })}
              className="w-full px-3 py-2 rounded-xl border border-stone-200 text-xs focus:ring-2 focus:ring-[#16181a]"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-stone-700 mb-1">Audit Notes / Reason</label>
            <textarea
              rows={2}
              value={adjustment.notes}
              onChange={(e) => setAdjustment({ ...adjustment, notes: e.target.value })}
              className="w-full px-3 py-2 rounded-xl border border-stone-200 text-xs focus:ring-2 focus:ring-[#16181a]"
              placeholder="e.g. Received weekly wholesale shipment from distributor"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => {
                setShowAdjustModal(false);
                setPrefillInfo(null);
              }}
              className="px-4 py-2 rounded-full border border-stone-200 text-xs font-semibold text-stone-600 hover:bg-stone-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-5 py-2 rounded-full bg-[#16181a] hover:bg-stone-800 text-white text-xs font-bold shadow-xs transition-all"
            >
              {submitting ? 'Applying...' : 'Confirm Audited Adjustment'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Movements Audit Log Modal */}
      <Modal
        isOpen={showMovementsModal}
        onClose={() => setShowMovementsModal(false)}
        title={selectedProduct ? `Audit Trail: ${selectedProduct.name}` : 'Inventory Movement History'}
        maxWidth="max-w-xl"
      >
        <div className="space-y-3">
          {movementsList.length === 0 ? (
            <p className="text-xs text-stone-400 text-center py-4">No logged movements for this product.</p>
          ) : (
            movementsList.map((m) => (
              <div key={m.movement_id} className="p-3.5 rounded-2xl bg-[#f7f8f4] border border-stone-200 text-xs flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <Badge variant={m.quantity_change > 0 ? 'success' : 'danger'} size="sm">
                      {m.adjustment_type}
                    </Badge>
                    <span className="font-bold text-[#16181a]">
                      {m.quantity_change > 0 ? `+${m.quantity_change}` : m.quantity_change} units
                    </span>
                  </div>
                  <p className="text-[11px] text-stone-500 mt-1">{m.notes || 'No description recorded'}</p>
                  <p className="text-[10px] text-stone-400 mt-0.5">{new Date(m.created_at).toLocaleString()}</p>
                </div>
                <div className="text-right text-[11px] text-stone-500">
                  <span>Balance: {m.stock_before} → <strong className="text-[#16181a]">{m.stock_after}</strong></span>
                </div>
              </div>
            ))
          )}
        </div>
      </Modal>
    </AppLayout>
  );
}
