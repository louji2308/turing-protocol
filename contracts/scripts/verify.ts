import { network } from "hardhat";
import * as path from "path";
import * as fs from "fs";

async function main() {
  const activeNetwork = process.env.ACTIVE_NETWORK || "testnet";
  const hardhatNetwork = activeNetwork === "mainnet" ? "mantle_mainnet" : "mantle_testnet";
  const isMainnet = hardhatNetwork === "mantle_mainnet";
  const { ethers } = await network.create({
    network: hardhatNetwork,
  });

  const [deployer] = await ethers.getSigners();
  console.log(`Verifying contracts on ${isMainnet ? "Mantle Mainnet" : "Mantle Testnet"}...`);

  const envPath = path.resolve(__dirname, "../../.env");
  const envContent = fs.readFileSync(envPath, "utf8");

  const oracleAddress = envContent.match(/HPS_ORACLE_ADDRESS=(0x[a-fA-F0-9]+)/)?.[1];
  const pobAddress = envContent.match(/PROOF_OF_BEHAVIOR_ADDRESS=(0x[a-fA-F0-9]+)/)?.[1];
  const libAddress = envContent.match(/TURING_LIB_ADDRESS=(0x[a-fA-F0-9]+)/)?.[1];

  if (!oracleAddress || !pobAddress || !libAddress) {
    console.error("Contract addresses not found in .env. Run deploy first.");
    process.exit(1);
  }

  console.log(`\nContract Addresses:`);
  console.log(`HPSOracle:        ${oracleAddress}`);
  console.log(`ProofOfBehavior:  ${pobAddress}`);
  console.log(`TuringLib:        ${libAddress}`);
  console.log(`Deployer:         ${deployer.address}`);

  const explorerUrl = isMainnet
    ? "https://explorer.mantle.xyz"
    : "https://explorer.testnet.mantle.xyz";
  const netArg = isMainnet ? "mantle_mainnet" : "mantle_testnet";
  console.log(`\nTo verify on Mantle Explorer:`);
  console.log(`1. Go to ${explorerUrl}/`);
  console.log(`2. Search for each contract address`);
  console.log(`3. Click "Contract" tab → "Verify and Publish"`);
  console.log(`4. Select "Solidity (Single File)" compiler type`);
  console.log(`5. Compiler version: 0.8.28`);
  console.log(`6. Paste the contract source code`);
  console.log(`\nOr use the Hardhat verify plugin:`);
  console.log(`npx hardhat verify --network ${netArg} ${oracleAddress} ${deployer.address} 100`);
  console.log(`npx hardhat verify --network ${netArg} ${pobAddress} ${deployer.address} 7000`);
}

main().catch(console.error);
