import { network } from "hardhat";
import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function main() {
  const activeNetwork = process.env.ACTIVE_NETWORK || "testnet";
  const hardhatNetwork = activeNetwork === "mainnet" ? "mantle_mainnet" : "mantle_testnet";
  const { ethers } = await network.create({
    network: hardhatNetwork,
  });

  const [deployer] = await ethers.getSigners();
  const provider = ethers.provider;
  const networkInfo = await provider.getNetwork();

  console.log(`\n${"=".repeat(50)}`);
  console.log(`TURING PROTOCOL — CONTRACT DEPLOYMENT`);
  console.log(`${"=".repeat(50)}`);
  console.log(`Network:  ${networkInfo.name} (chainId: ${networkInfo.chainId})`);
  console.log(`Deployer: ${deployer.address}`);
  console.log(`Balance:  ${ethers.formatEther(await provider.getBalance(deployer.address))} MNT`);
  console.log(`${"=".repeat(50)}\n`);

  // ── 1. Deploy HPSOracle ──────────────────────────
  console.log("Deploying HPSOracle...");
  const HPSOracle = await ethers.getContractFactory("HPSOracle");
  const hpsOracle = await HPSOracle.deploy(
    deployer.address,
    100,
  );
  await hpsOracle.waitForDeployment();
  const oracleAddress = await hpsOracle.getAddress();
  console.log(`✅ HPSOracle deployed: ${oracleAddress}`);

  // ── 2. Deploy ProofOfBehavior ────────────────────
  console.log("\nDeploying ProofOfBehavior...");
  const ProofOfBehavior = await ethers.getContractFactory("ProofOfBehavior");
  const pob = await ProofOfBehavior.deploy(
    deployer.address,
    7000,
  );
  await pob.waitForDeployment();
  const pobAddress = await pob.getAddress();
  console.log(`✅ ProofOfBehavior deployed: ${pobAddress}`);

  // ── 3. Deploy TuringLib ──────────────────────────
  console.log("\nDeploying TuringLib...");
  const TuringLib = await ethers.getContractFactory("TuringLib");
  const turingLib = await TuringLib.deploy();
  await turingLib.waitForDeployment();
  const libAddress = await turingLib.getAddress();
  console.log(`✅ TuringLib deployed: ${libAddress}`);

  // ── 4. Save addresses to env file ───────────────
  const envPath = path.resolve(__dirname, "../../.env");
  let envContent = fs.readFileSync(envPath, "utf8");

  envContent = envContent
    .replace(/HPS_ORACLE_ADDRESS=.*/, `HPS_ORACLE_ADDRESS=${oracleAddress}`)
    .replace(/PROOF_OF_BEHAVIOR_ADDRESS=.*/, `PROOF_OF_BEHAVIOR_ADDRESS=${pobAddress}`)
    .replace(/TURING_LIB_ADDRESS=.*/, `TURING_LIB_ADDRESS=${libAddress}`);

  fs.writeFileSync(envPath, envContent);
  console.log(`📄 Updated .env with contract addresses`);

  // ── 5. Copy ABIs to dashboard ───────────────────
  const contracts = [
    { name: "HPSOracle", address: oracleAddress },
    { name: "ProofOfBehavior", address: pobAddress },
  ];

  const artifactsDir = path.resolve(__dirname, "../artifacts/contracts");
  const abiDir = path.resolve(__dirname, "../../dashboard/src/abi");

  if (!fs.existsSync(abiDir)) {
    fs.mkdirSync(abiDir, { recursive: true });
  }

  for (const contract of contracts) {
    const artifactPath = path.join(artifactsDir, `${contract.name}.sol`, `${contract.name}.json`);
    if (fs.existsSync(artifactPath)) {
      const artifact = JSON.parse(fs.readFileSync(artifactPath, "utf8"));
      const abiPath = path.join(abiDir, `${contract.name}.json`);
      fs.writeFileSync(abiPath, JSON.stringify({
        address: contract.address,
        abi: artifact.abi,
      }, null, 2));
      console.log(`📄 ABI saved: dashboard/src/abi/${contract.name}.json`);
    }
  }

  console.log(`\n${"=".repeat(50)}`);
  console.log(`DEPLOYMENT COMPLETE`);
  console.log(`${"=".repeat(50)}`);
  console.log(`HPSOracle:        ${oracleAddress}`);
  console.log(`ProofOfBehavior:  ${pobAddress}`);
  console.log(`TuringLib:        ${libAddress}`);
  // ── 5. Configure multi-operator support ──────────
  const operatorsEnv = process.env.OPERATOR_ADDRESSES || "";
  if (operatorsEnv) {
    const operators = operatorsEnv.split(",").map(a => a.trim()).filter(a => a.startsWith("0x"));
    if (operators.length > 0) {
      console.log(`\nAdding ${operators.length} operator(s) to HPSOracle...`);
      for (const op of operators) {
        if (op.toLowerCase() === deployer.address.toLowerCase()) continue;
        const tx = await hpsOracle.addOperator(op);
        await tx.wait();
        console.log(`  ➕ Operator added: ${op}`);
      }
    }
  }

  // ── 6. Set score rate limit ──────────────────────
  const maxChange = parseInt(process.env.MAX_SCORE_CHANGE || "2500", 10);
  if (maxChange > 0) {
    const tx = await hpsOracle.setMaxScoreChange(maxChange);
    await tx.wait();
    console.log(`\n📊 Max score change set to ${maxChange}`);
  }

  console.log(`\n${"=".repeat(50)}`);
  console.log(`DEPLOYMENT COMPLETE`);
  console.log(`${"=".repeat(50)}`);
  console.log(`HPSOracle:        ${oracleAddress}`);
  console.log(`ProofOfBehavior:  ${pobAddress}`);
  console.log(`TuringLib:        ${libAddress}`);

  if (operatorsEnv) {
    const ops = operatorsEnv.split(",").filter(a => a.trim().startsWith("0x"));
    console.log(`Operators:        ${ops.length + 1} (incl. deployer)`);
  }
  console.log(`MaxScoreChange:   ${maxChange}`);
  console.log(`\nNext steps:`);
  console.log(`1. Verify contracts on Mantle Explorer`);
  console.log(`2. Set OPERATOR_PRIVATE_KEYS in .env for each operator`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
