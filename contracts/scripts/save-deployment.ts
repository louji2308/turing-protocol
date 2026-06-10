import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const oracleAddress = "0x824e72507C94E2A615400049167a661469351A1D";
const pobAddress = "0x3abA2F45546c81f1C680E49D84E9DAF1EDaa5029";
const libAddress = "0x3252fbd6b418511E20fda56c5631cD0D492Df390";

// Update .env
const envPath = path.resolve(__dirname, "../../.env");
let envContent = fs.readFileSync(envPath, "utf8");

envContent = envContent
  .replace(/HPS_ORACLE_ADDRESS=.*/, `HPS_ORACLE_ADDRESS=${oracleAddress}`)
  .replace(/PROOF_OF_BEHAVIOR_ADDRESS=.*/, `PROOF_OF_BEHAVIOR_ADDRESS=${pobAddress}`)
  .replace(/TURING_LIB_ADDRESS=.*/, `TURING_LIB_ADDRESS=${libAddress}`);

fs.writeFileSync(envPath, envContent);
console.log(`✅ Updated .env with contract addresses`);

// Copy ABIs to dashboard
const artifactsDir = path.resolve(__dirname, "../artifacts/contracts");
const abiDir = path.resolve(__dirname, "../../dashboard/src/abi");

if (!fs.existsSync(abiDir)) {
  fs.mkdirSync(abiDir, { recursive: true });
}

const contracts = [
  { name: "HPSOracle", address: oracleAddress },
  { name: "ProofOfBehavior", address: pobAddress },
];

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
  } else {
    console.log(`⚠️  Artifact not found: ${artifactPath}`);
  }
}

console.log(`\n✅ Deployment post-processing complete!`);
console.log(`HPSOracle:        ${oracleAddress}`);
console.log(`ProofOfBehavior:  ${pobAddress}`);
console.log(`TuringLib:        ${libAddress}`);
