// Central runtime configuration for the Turing Protocol dashboard.
//
// Every value below is PUBLIC (public RPC, public contract addresses, the
// public ghost wallet, and the publicly deployed oracle API), so the real
// production defaults are baked in here as fallbacks. This guarantees the
// dashboard shows live on-chain + oracle data out of the box, while still
// letting any `VITE_*` environment variable override a given value.

// Deployed FastAPI oracle service (Render). Accepts any of the historical
// env-var names so older configs keep working.
export const ORACLE_API = (
  import.meta.env.VITE_ORACLE_API ||
  import.meta.env.VITE_ORACLE_URL ||
  import.meta.env.VITE_API_URL ||
  'https://turing-oracle.onrender.com'
).replace(/\/$/, '');

// The protocol's live "ghost" agent wallet on Mantle Sepolia — the wallet the
// interrogator continuously scores. Has real on-chain history + an HPS.
export const GHOST_ADDRESS =
  import.meta.env.VITE_GHOST_ADDRESS ||
  '0xfdaE6B5f5A8802e47c48dEa56157406c5a54C700';

// Mantle Sepolia public RPC (chain id 5003).
export const MANTLE_RPC =
  import.meta.env.VITE_MANTLE_RPC || 'https://rpc.sepolia.mantle.xyz';

export const NETWORK_NAME =
  import.meta.env.VITE_NETWORK_NAME || 'Mantle Sepolia';

export const EXPLORER_URL =
  import.meta.env.VITE_EXPLORER_URL || 'https://explorer.testnet.mantle.xyz';

// HPSOracle contract address (used for the header explorer link).
export const ORACLE_ADDRESS =
  import.meta.env.VITE_ORACLE_ADDRESS ||
  '0x824e72507C94E2A615400049167a661469351A1D';

export const POLL_INTERVAL_MS =
  Number(import.meta.env.VITE_POLL_INTERVAL_MS) || 30000;
