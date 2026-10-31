'use client';

import { useState } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  LabelList,
} from 'recharts';
import { BarChart3, X } from 'lucide-react';

/*
 * Minimal chart for a copilot answer, shown only when the merchant asks for it.
 * The backend sends `chart` with sales answers (top products, sales summary, comparisons):
 *   { kind: 'bars' | 'columns', title, value_label, value_prefix, points: [{label, value, full_label}], auto_open }
 * - auto_open = false -> a small "Show chart" button (the reply text also offers it)
 * - auto_open = true  -> the merchant asked for a chart, so it opens straight away
 */

const INK = '#16181a';
const MUTED = '#8c9288';

// Full value, Indian grouping: ₹2,86,307
const fullValue = (v, prefix) => `${prefix}${Number(v || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;

// Compact value for labels on the bars: ₹7.9k, ₹2.9L
const shortValue = (v, prefix) => {
  const n = Number(v || 0);
  if (Math.abs(n) >= 100000) return `${prefix}${(n / 100000).toFixed(1)}L`;
  if (Math.abs(n) >= 1000) return `${prefix}${(n / 1000).toFixed(1)}k`;
  return `${prefix}${Math.round(n)}`;
};

function MiniTooltip({ active, payload, prefix, valueLabel }) {
  if (!active || !payload || !payload.length) return null;
  const pt = payload[0].payload;
  return (
    <div className="bg-[#16181a] text-white text-[11px] px-2.5 py-1.5 rounded-xl shadow-lg max-w-[220px]">
      <p className="font-semibold text-[#e0fd53] leading-snug">{pt.full_label || pt.label}</p>
      <p className="text-stone-200">
        {valueLabel}: <strong className="text-white">{fullValue(pt.value, prefix)}</strong>
      </p>
    </div>
  );
}

// Product label on one line (the default tick wraps long names onto two lines)
function SingleLineTick({ x, y, payload }) {
  return (
    <text x={x - 6} y={y} dy={4} textAnchor="end" fontSize={10.5} fill="#44403c">
      {payload?.value}
    </text>
  );
}

function MiniChart({ chart }) {
  const prefix = chart.value_prefix || '';
  const data = chart.points || [];
  const tooltip = (
    <Tooltip
      cursor={{ fill: 'rgba(224, 253, 83, 0.18)' }}
      content={<MiniTooltip prefix={prefix} valueLabel={chart.value_label} />}
    />
  );

  if (chart.kind === 'columns') {
    // Vertical bars over time (days / weeks)
    const showLabels = data.length <= 8;
    return (
      <div style={{ height: 150 }} className="w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 16, right: 4, left: 4, bottom: 0 }}>
            <XAxis
              dataKey="label"
              tick={{ fontSize: 9.5, fill: MUTED }}
              tickLine={false}
              axisLine={false}
              interval="preserveStartEnd"
              minTickGap={6}
            />
            <YAxis hide />
            {tooltip}
            <Bar dataKey="value" fill={INK} radius={[6, 6, 2, 2]} maxBarSize={26}>
              {showLabels && (
                <LabelList
                  dataKey="value"
                  position="top"
                  formatter={(v) => shortValue(v, prefix)}
                  style={{ fontSize: 9.5, fill: MUTED }}
                />
              )}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  }

  // Horizontal bars, one per product
  const height = Math.max(60, data.length * 28 + 8);
  return (
    <div style={{ height }} className="w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 0, right: 52, left: 0, bottom: 0 }}>
          <XAxis type="number" hide />
          <YAxis
            type="category"
            dataKey="label"
            width={132}
            tick={SingleLineTick}
            tickLine={false}
            axisLine={false}
          />
          {tooltip}
          <Bar dataKey="value" fill={INK} radius={[2, 6, 6, 2]} barSize={14}>
            <LabelList
              dataKey="value"
              position="right"
              formatter={(v) => shortValue(v, prefix)}
              style={{ fontSize: 10, fill: MUTED }}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function ChartOffer({ chart }) {
  const [open, setOpen] = useState(Boolean(chart?.auto_open));
  if (!chart || !chart.points || chart.points.length === 0) return null;

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="mt-2 inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#f7f8f4] border border-stone-200/90 text-[10.5px] font-semibold text-[#16181a] hover:bg-[#e0fd53]/40 transition-colors cursor-pointer"
      >
        <BarChart3 className="w-3.5 h-3.5" />
        Show chart
      </button>
    );
  }

  return (
    <div
      className="mt-2 rounded-2xl border border-stone-200/90 bg-[#fbfbf8] px-3 pt-2.5 pb-2"
      role="img"
      aria-label={chart.title}
    >
      <div className="flex items-center justify-between mb-1.5">
        <p className="text-[10.5px] font-semibold text-stone-500">{chart.title}</p>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="p-0.5 rounded-md text-stone-400 hover:text-stone-700 hover:bg-stone-100 cursor-pointer"
          title="Hide chart"
          aria-label="Hide chart"
        >
          <X className="w-3 h-3" />
        </button>
      </div>
      <MiniChart chart={chart} />
    </div>
  );
}
