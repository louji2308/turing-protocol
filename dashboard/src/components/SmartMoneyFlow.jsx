import { Sankey, Tooltip, ResponsiveContainer, Rectangle } from 'recharts';

const cardStyle = {
  background: 'var(--surface-01)',
  border: '1px solid var(--border-subtle)',
  borderRadius: 'var(--radius-md)',
  padding: 'var(--space-4)',
  display: 'flex',
  flexDirection: 'column',
  minHeight: 260,
};

export function SmartMoneyFlow({ flows }) {
  if (!flows || !flows.top_flows?.length) {
    return (
      <div style={{ ...cardStyle, alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>
        Smart money flow loading\u2026
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
    <div style={cardStyle}>
      <div style={{ fontSize: 'var(--text-md)', fontWeight: 700, color: 'var(--text-primary)' }}>Smart Money Flow</div>
      <div className="label-caps" style={{ marginTop: 2, marginBottom: 'var(--space-3)' }}>
        14d &middot; where HPS &ge; {flows.threshold_hps} deploys capital
      </div>
      <div style={{ flex: 1, minHeight: 0 }}>
        <ResponsiveContainer width="100%" height={210}>
          <Sankey
            data={{ nodes, links }}
            node={<Rectangle radius={[2, 2, 2, 2]} fill="var(--accent-purple)" />}
            link={{ stroke: 'rgba(139,124,255,0.22)', strokeOpacity: 0.4 }}
            margin={{ top: 10, bottom: 10, left: 10, right: 90 }}
          >
            <Tooltip
              formatter={(value) => `${value.toFixed(2)} MNT`}
              contentStyle={{ background: 'rgba(8,10,20,0.96)', border: '1px solid var(--border-default)', borderRadius: 'var(--radius-md)', color: '#fff', fontSize: '11px' }}
            />
          </Sankey>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
