import { Sankey, Tooltip, ResponsiveContainer, Rectangle } from 'recharts';

export function SmartMoneyFlow({ flows }) {
  if (!flows || !flows.top_flows?.length) {
    return (
      <div className="bg-slate-800 rounded-xl p-4 flex items-center justify-center text-slate-400 text-sm h-[260px]">
        Smart money flow data loading...
      </div>
    );
  }

  const nodes = [
    { name: `Smart Wallets (${flows.smart_wallet_count})` },
    ...flows.top_flows.map((f) => ({ name: f.protocol })),
  ];
  const links = flows.top_flows.map((f, i) => ({
    source: 0,
    target: i + 1,
    value: Math.max(f.net_flow_mnt, 0.01),
  }));

  return (
    <div className="bg-slate-800 rounded-xl p-4">
      <h3 className="text-white font-semibold mb-1">Smart Money Flow (14d)</h3>
      <p className="text-xs text-slate-400 mb-2">
        Where wallets with HPS &ge; {flows.threshold_hps} are deploying capital
      </p>
      <ResponsiveContainer width="100%" height={240}>
        <Sankey
          data={{ nodes, links }}
          node={<Rectangle radius={[2, 2, 2, 2]} fill="#3b82f6" />}
          link={{ stroke: '#475569', strokeOpacity: 0.5 }}
          margin={{ top: 10, bottom: 10, left: 10, right: 80 }}
        >
          <Tooltip
            formatter={(value) => `${value.toFixed(2)} MNT`}
            contentStyle={{ background: '#1e293b', border: 'none', color: '#fff' }}
          />
        </Sankey>
      </ResponsiveContainer>
    </div>
  );
}
