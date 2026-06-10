import hardhatToolboxMochaEthersPlugin from "@nomicfoundation/hardhat-toolbox-mocha-ethers";
import { defineConfig } from "hardhat/config";
import { config } from "dotenv";

config({ path: "../.env" });

const MANTLE_TESTNET_RPC = process.env.MANTLE_TESTNET_RPC || "https://rpc.sepolia.mantle.xyz";
const MANTLE_MAINNET_RPC = process.env.MANTLE_MAINNET_RPC || "https://rpc.mantle.xyz";
const OPERATOR_PRIVATE_KEY = process.env.OPERATOR_PRIVATE_KEY || "0x" + "0".repeat(64);
const ETHERSCAN_API_KEY = process.env.ETHERSCAN_API_KEY || "";

export default defineConfig({
  plugins: [hardhatToolboxMochaEthersPlugin],
  solidity: {
    profiles: {
      default: {
        version: "0.8.28",
      },
      production: {
        version: "0.8.28",
        settings: {
          optimizer: {
            enabled: true,
            runs: 200,
          },
          viaIR: true,
        },
      },
    },
  },
  verify: {
    etherscan: {
      apiKey: ETHERSCAN_API_KEY,
    },
  },
  networks: {
    hardhatMainnet: {
      type: "edr-simulated",
      chainType: "l1",
    },
    hardhatOp: {
      type: "edr-simulated",
      chainType: "op",
    },
    mantle_testnet: {
      type: "http",
      chainType: "l1",
      url: MANTLE_TESTNET_RPC,
      accounts: [OPERATOR_PRIVATE_KEY],
      blockExplorers: {
        etherscan: {
          url: "https://explorer.testnet.mantle.xyz",
          apiUrl: "https://explorer.testnet.mantle.xyz/api",
        },
      },
    },
    mantle_mainnet: {
      type: "http",
      chainType: "l1",
      url: MANTLE_MAINNET_RPC,
      accounts: [OPERATOR_PRIVATE_KEY],
      blockExplorers: {
        etherscan: {
          url: "https://explorer.mantle.xyz",
          apiUrl: "https://explorer.mantle.xyz/api",
        },
      },
    },
  },
});
