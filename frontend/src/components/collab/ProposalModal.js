'use client';

import { useEffect, useState } from 'react';
import Modal from '@/components/ui/Modal';
import RecommendationBanner from '@/components/ui/RecommendationBanner';
import api from '@/lib/api';
import { CheckCircle2, AlertTriangle } from 'lucide-react';

/*
 * Joint-bundle proposal popup, shared by the Collaborations page and the Local Map page.
 * - Pre-fills the suggested bundle (products + cost-safe discounts) when there is one.
 * - Checks both shops' margins live (12% minimum) as values change.
 * - Sends nothing until the merchant clicks "Submit Proposal to Partner";
 *   the partner then has to approve it.
 *
 * Props:
 *   partner      partner from /collaborations/discover (null = closed)
 *   myProducts   this merchant's products (from /products)
 *   merchant     the signed-in merchant
 *   source       where it was opened from, e.g. "Local Map" (shown in the banner)
 *   onClose()    close without sending
 *   onSubmitted(partner)  called after the proposal is created
 */
export default function ProposalModal({ partner, myProducts = [], merchant, source = null, onClose, onSubmitted }) {
  const [form, setForm] = useState({
    initiator_product_id: '',
    initiator_discount_pct: 10,
    partner_product_id: '',
    partner_discount_pct: 10,
    bundle_name: '',
    bundle_description: '',
  });
  const [prefillInfo, setPrefillInfo] = useState(null);
  const [validationResult, setValidationResult] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  // Fill the form whenever a (new) partner is opened
  useEffect(() => {
    if (!partner) return;
    const b = partner.suggested_bundle;
    if (b) {
      setForm({
        initiator_product_id: b.initiator_product_id,
        initiator_discount_pct: b.initiator_discount_pct,
        partner_product_id: b.partner_product_id,
        partner_discount_pct: b.partner_discount_pct,
        bundle_name: b.bundle_name,
        bundle_description: b.pitch,
      });
      setPrefillInfo({
        source: source ? `${source} · ${partner.suggestion_source || 'LocalPulse'}` : partner.suggestion_source || 'LocalPulse',
        reason: b.theme,
        summary: `${b.initiator_discount_pct}% off your ${b.initiator_product_name} + ${b.partner_discount_pct}% off their ${b.partner_product_name}: ₹${Math.round(b.discounted_bundle_price).toLocaleString('en-IN')} instead of ₹${Math.round(b.original_bundle_price).toLocaleString('en-IN')}.`,
      });
    } else {
      setForm({
        initiator_product_id: myProducts[0]?.product_id || '',
        initiator_discount_pct: 10,
        partner_product_id: partner.top_products?.[0]?.product_id || '',
        partner_discount_pct: 10,
        bundle_name: `${merchant?.business_name || 'Our'} & ${partner.business_name} Combo`,
        bundle_description: 'Cross-promoted neighborhood bundle offering exclusive discounts on complementary items.',
      });
      setPrefillInfo(null);
    }
    setValidationResult(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [partner]);

  // Live margin check (both shops must keep >= 12%)
  useEffect(() => {
    if (!partner || !form.initiator_product_id || !form.partner_product_id) return;
    let cancelled = false;
    api
      .post('/collaborations/validate-margins', {
        partner_merchant_id: partner.merchant_id,
        initiator_product_id: form.initiator_product_id,
        initiator_discount_pct: parseFloat(form.initiator_discount_pct),
        partner_product_id: form.partner_product_id,
        partner_discount_pct: parseFloat(form.partner_discount_pct),
        bundle_name: form.bundle_name || 'Joint Bundle',
      })
      .then((res) => !cancelled && setValidationResult(res.data))
      .catch((err) => console.error('Validation error:', err));
    return () => {
      cancelled = true;
    };
  }, [partner, form.initiator_product_id, form.initiator_discount_pct, form.partner_product_id, form.partner_discount_pct]);

  const submit = async (e) => {
    e.preventDefault();
    if (!validationResult?.is_financially_viable) {
      alert('Cannot propose bundle: Minimum 12% profit margin rule violated.');
      return;
    }
    setSubmitting(true);
    try {
      await api.post('/collaborations/proposals', {
        partner_merchant_id: partner.merchant_id,
        initiator_product_id: form.initiator_product_id,
        initiator_discount_pct: parseFloat(form.initiator_discount_pct),
        partner_product_id: form.partner_product_id,
        partner_discount_pct: parseFloat(form.partner_discount_pct),
        bundle_name: form.bundle_name,
        bundle_description: form.bundle_description,
      });
      if (onSubmitted) onSubmitted(partner);
    } catch (err) {
      console.error(err);
      alert(err.response?.data?.detail || 'Failed to submit proposal.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={Boolean(partner)}
      onClose={onClose}
      title={partner ? `Construct Joint Bundle with ${partner.business_name}` : 'Construct Bundle'}
      maxWidth="max-w-2xl"
    >
      <form onSubmit={submit} className="space-y-4 max-h-[75vh] overflow-y-auto pr-1">
        {prefillInfo && (
          <RecommendationBanner source={prefillInfo.source} reason={prefillInfo.reason}>
            {prefillInfo.summary} Your partner still has to approve it.
          </RecommendationBanner>
        )}
        <div>
          <label className="block text-xs font-semibold text-stone-700 mb-1">Bundle Name</label>
          <input
            type="text"
            required
            value={form.bundle_name}
            onChange={(e) => setForm({ ...form, bundle_name: e.target.value })}
            className="w-full px-3 py-2 rounded-xl border border-stone-200 text-xs focus:ring-2 focus:ring-[#16181a]"
            placeholder="e.g. Indiranagar Breakfast Hamper"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-stone-700 mb-1">Bundle Description / Marketing Pitch</label>
          <textarea
            rows={2}
            required
            value={form.bundle_description}
            onChange={(e) => setForm({ ...form, bundle_description: e.target.value })}
            className="w-full px-3 py-2 rounded-xl border border-stone-200 text-xs focus:ring-2 focus:ring-[#16181a]"
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 p-4 rounded-2xl bg-[#f7f8f4] border border-stone-200">
          {/* Your Product Choice */}
          <div>
            <p className="text-xs font-bold text-stone-800 mb-2">Your Product ({merchant?.business_name})</p>
            <select
              value={form.initiator_product_id}
              onChange={(e) => setForm({ ...form, initiator_product_id: e.target.value })}
              className="w-full px-3 py-2 rounded-xl border border-stone-200 text-xs bg-white mb-2"
            >
              {myProducts.map((p) => (
                <option key={p.product_id} value={p.product_id}>
                  {p.name} (₹{p.selling_price})
                </option>
              ))}
            </select>
            <label className="block text-[11px] font-semibold text-stone-600 mb-1">
              Your Discount Contribution (%): {form.initiator_discount_pct}%
            </label>
            <input
              type="range"
              min="0"
              max="35"
              step="1"
              value={form.initiator_discount_pct}
              onChange={(e) => setForm({ ...form, initiator_discount_pct: e.target.value })}
              className="w-full accent-[#16181a]"
            />
          </div>

          {/* Partner Product Choice */}
          <div>
            <p className="text-xs font-bold text-stone-800 mb-2">Partner Product ({partner?.business_name})</p>
            <select
              value={form.partner_product_id}
              onChange={(e) => setForm({ ...form, partner_product_id: e.target.value })}
              className="w-full px-3 py-2 rounded-xl border border-stone-200 text-xs bg-white mb-2"
            >
              {(partner?.top_products || []).map((p) => (
                <option key={p.product_id} value={p.product_id}>
                  {p.name} (₹{p.selling_price})
                </option>
              ))}
            </select>
            <label className="block text-[11px] font-semibold text-stone-600 mb-1">
              Partner Discount Contribution (%): {form.partner_discount_pct}%
            </label>
            <input
              type="range"
              min="0"
              max="35"
              step="1"
              value={form.partner_discount_pct}
              onChange={(e) => setForm({ ...form, partner_discount_pct: e.target.value })}
              className="w-full accent-[#16181a]"
            />
          </div>
        </div>

        {/* Real-time margin validation */}
        {validationResult && (
          <div
            className={`p-4 rounded-2xl border text-xs ${
              validationResult.is_financially_viable
                ? 'bg-emerald-50/70 border-emerald-200 text-emerald-900'
                : 'bg-[#faeed6] border-[#f2d8a5] text-[#8c5208]'
            }`}
          >
            <div className="flex items-center justify-between mb-2 font-bold">
              <span className="flex items-center gap-1.5">
                {validationResult.is_financially_viable ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                ) : (
                  <AlertTriangle className="w-4 h-4 text-[#8c5208]" />
                )}
                <span>
                  {validationResult.is_financially_viable ? 'Financially Viable Bundle' : 'Margin Safety Threshold Violated'}
                </span>
              </span>
              <span className="text-[11px]">
                Effective Discount: <strong>{validationResult.effective_bundle_discount_pct}%</strong>
              </span>
            </div>
            <div className="grid grid-cols-2 gap-3 text-[11px] mb-2 bg-white p-2.5 rounded-xl border border-stone-200 text-stone-800">
              <div>
                <p className="font-semibold text-stone-600">Your Unit Margin:</p>
                <p className="font-bold text-sm">
                  {validationResult.initiator_margin_pct}% (₹{validationResult.initiator_profit_per_unit} profit)
                </p>
              </div>
              <div>
                <p className="font-semibold text-stone-600">Partner Unit Margin:</p>
                <p className="font-bold text-sm">
                  {validationResult.partner_margin_pct}% (₹{validationResult.partner_profit_per_unit} profit)
                </p>
              </div>
            </div>
            <p className="text-[11px]">{validationResult.status_reason}</p>
          </div>
        )}

        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-full border border-stone-200 text-xs font-semibold text-stone-600 hover:bg-stone-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting || !validationResult?.is_financially_viable}
            className="px-5 py-2 rounded-full bg-[#16181a] hover:bg-stone-800 text-white text-xs font-bold shadow-xs transition-all disabled:opacity-50"
          >
            {submitting ? 'Submitting...' : 'Submit Proposal to Partner'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
