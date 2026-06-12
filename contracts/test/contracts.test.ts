import { expect } from "chai";
import { network } from "hardhat";

const { ethers } = await network.create();

describe("HPSOracle", function () {
  it("Should deploy with correct operator and model version", async function () {
    const [deployer] = await ethers.getSigners();
    const Oracle = await ethers.getContractFactory("HPSOracle");
    const oracle = await Oracle.deploy(deployer.address, 100);
    await oracle.waitForDeployment();

    expect(await oracle.operator()).to.equal(deployer.address);
    expect(await oracle.modelVersion()).to.equal(100);
    expect(await oracle.totalScoredWallets()).to.equal(0n);
  });

  it("Should reject zero address operator", async function () {
    const Oracle = await ethers.getContractFactory("HPSOracle");
    await expect(
      Oracle.deploy(ethers.ZeroAddress, 100)
    ).to.be.revertedWith("HPSOracle: zero address operator");
  });

  it("Should update scores via batchUpdateScores", async function () {
    const [deployer, wallet1, wallet2] = await ethers.getSigners();
    const Oracle = await ethers.getContractFactory("HPSOracle");
    const oracle = await Oracle.deploy(deployer.address, 100);
    await oracle.waitForDeployment();

    const wallets = [wallet1.address, wallet2.address];
    const scores = [7500, 3200];

    await oracle.batchUpdateScores(wallets, scores, 100);

    expect(await oracle.getScore(wallet1.address)).to.equal(7500);
    expect(await oracle.getScore(wallet2.address)).to.equal(3200);
    expect(await oracle.totalScoredWallets()).to.equal(2n);
  });

  it("Should reject non-operator batch updates", async function () {
    const [deployer, attacker] = await ethers.getSigners();
    const Oracle = await ethers.getContractFactory("HPSOracle");
    const oracle = await Oracle.deploy(deployer.address, 100);
    await oracle.waitForDeployment();

    await expect(
      oracle.connect(attacker).batchUpdateScores([attacker.address], [5000], 100)
    ).to.be.revertedWith("HPSOracle: caller is not an operator");
  });

  it("Should track new wallets correctly", async function () {
    const [deployer, w1, w2, w3] = await ethers.getSigners();
    const Oracle = await ethers.getContractFactory("HPSOracle");
    const oracle = await Oracle.deploy(deployer.address, 100);
    await oracle.waitForDeployment();

    await oracle.batchUpdateScores([w1.address], [5000], 100);
    expect(await oracle.totalScoredWallets()).to.equal(1n);

    await oracle.batchUpdateScores([w1.address], [6000], 100);
    expect(await oracle.totalScoredWallets()).to.equal(1n);

    await oracle.batchUpdateScores([w2.address, w3.address], [3000, 9000], 100);
    expect(await oracle.totalScoredWallets()).to.equal(3n);
  });

  it("Should return correct isHuman status", async function () {
    const [deployer, wallet] = await ethers.getSigners();
    const Oracle = await ethers.getContractFactory("HPSOracle");
    const oracle = await Oracle.deploy(deployer.address, 100);
    await oracle.waitForDeployment();

    await oracle.batchUpdateScores([wallet.address], [8500], 100);

    expect(await oracle.isHuman(wallet.address, 7000)).to.be.true;
    expect(await oracle.isHuman(wallet.address, 9000)).to.be.false;
  });

  it("Should support 2-step operator transfer", async function () {
    const [deployer, newOp] = await ethers.getSigners();
    const Oracle = await ethers.getContractFactory("HPSOracle");
    const oracle = await Oracle.deploy(deployer.address, 100);
    await oracle.waitForDeployment();

    await oracle.initiateOperatorTransfer(newOp.address);
    expect(await oracle.pendingOperator()).to.equal(newOp.address);

    await oracle.connect(newOp).acceptOperatorTransfer();
    expect(await oracle.operator()).to.equal(newOp.address);
  });
});

describe("ProofOfBehavior", function () {
  it("Should deploy with correct parameters", async function () {
    const [deployer] = await ethers.getSigners();
    const POB = await ethers.getContractFactory("ProofOfBehavior");
    const pob = await POB.deploy(deployer.address, 7000);
    await pob.waitForDeployment();

    expect(await pob.oracleService()).to.equal(deployer.address);
    expect(await pob.freshnessThreshold()).to.equal(7000);
    expect(await pob.name()).to.equal("Turing Protocol Proof of Behavior");
    expect(await pob.symbol()).to.equal("TPOB");
  });

  it("Should mint a proof to qualifying wallet", async function () {
    const [deployer, wallet] = await ethers.getSigners();
    const POB = await ethers.getContractFactory("ProofOfBehavior");
    const pob = await POB.deploy(deployer.address, 7000);
    await pob.waitForDeployment();

    const fingerprint = ethers.hexlify(ethers.randomBytes(32));
    await pob.mint(wallet.address, 7500, fingerprint, 100);

    expect(await pob.totalMinted()).to.equal(1n);
    expect(await pob.totalFreshProofs()).to.equal(1n);
    expect(await pob.walletToTokenId(wallet.address)).to.equal(1n);
    expect(await pob.hasFreshProof(wallet.address)).to.be.true;

    const proof = await pob.getProof(wallet.address);
    expect(proof.scoreAtMint).to.equal(7500);
    expect(proof.currentScore).to.equal(7500);
    expect(proof.isFresh).to.be.true;
    expect(proof.behaviorFingerprint).to.equal(fingerprint);
    expect(proof.modelVersionAtMint).to.equal(100);
  });

  it("Should reject duplicate minting", async function () {
    const [deployer, wallet] = await ethers.getSigners();
    const POB = await ethers.getContractFactory("ProofOfBehavior");
    const pob = await POB.deploy(deployer.address, 7000);
    await pob.waitForDeployment();

    const fingerprint = ethers.hexlify(ethers.randomBytes(32));
    await pob.mint(wallet.address, 8000, fingerprint, 100);

    await expect(
      pob.mint(wallet.address, 9000, fingerprint, 100)
    ).to.be.revertedWith("ProofOfBehavior: wallet already has a proof");
  });

  it("Should reject minting below threshold", async function () {
    const [deployer, wallet] = await ethers.getSigners();
    const POB = await ethers.getContractFactory("ProofOfBehavior");
    const pob = await POB.deploy(deployer.address, 7000);
    await pob.waitForDeployment();

    const fingerprint = ethers.hexlify(ethers.randomBytes(32));
    await expect(
      pob.mint(wallet.address, 5000, fingerprint, 100)
    ).to.be.revertedWith("ProofOfBehavior: score below threshold");
  });

  it("Should enforce soulbound (no transfers)", async function () {
    const [deployer, wallet1, wallet2] = await ethers.getSigners();
    const POB = await ethers.getContractFactory("ProofOfBehavior");
    const pob = await POB.deploy(deployer.address, 7000);
    await pob.waitForDeployment();

    const fingerprint = ethers.hexlify(ethers.randomBytes(32));
    await pob.mint(wallet1.address, 8000, fingerprint, 100);

    await expect(
      pob.connect(wallet1).transferFrom(wallet1.address, wallet2.address, 1)
    ).to.be.revertedWith("ProofOfBehavior: Soulbound token cannot be transferred");
  });

  it("Should update freshness on score changes", async function () {
    const [deployer, wallet] = await ethers.getSigners();
    const POB = await ethers.getContractFactory("ProofOfBehavior");
    const pob = await POB.deploy(deployer.address, 7000);
    await pob.waitForDeployment();

    const fingerprint = ethers.hexlify(ethers.randomBytes(32));
    await pob.mint(wallet.address, 8000, fingerprint, 100);
    expect(await pob.totalFreshProofs()).to.equal(1n);

    await pob.updateFreshness(wallet.address, 6500);
    expect(await pob.totalFreshProofs()).to.equal(0n);
    expect(await pob.hasFreshProof(wallet.address)).to.be.false;

    const proof = await pob.getProof(wallet.address);
    expect(proof.currentScore).to.equal(6500);
    expect(proof.isFresh).to.be.false;

    await pob.updateFreshness(wallet.address, 7500);
    expect(await pob.totalFreshProofs()).to.equal(1n);
    expect(await pob.hasFreshProof(wallet.address)).to.be.true;
  });

  it("Should generate valid tokenURI", async function () {
    const [deployer, wallet] = await ethers.getSigners();
    const POB = await ethers.getContractFactory("ProofOfBehavior");
    const pob = await POB.deploy(deployer.address, 7000);
    await pob.waitForDeployment();

    const fingerprint = ethers.hexlify(ethers.randomBytes(32));
    await pob.mint(wallet.address, 7500, fingerprint, 100);

    const uri = await pob.tokenURI(1);
    expect(uri).to.include("data:application/json;base64,");

    const json = Buffer.from(uri.split(",")[1], "base64").toString();
    const parsed = JSON.parse(json);
    expect(parsed.name).to.include("Proof of Behavior #1");
    expect(parsed.attributes[0].value).to.equal(7500);
  });

  it("Should only allow oracle service to mint", async function () {
    const [deployer, wallet, attacker] = await ethers.getSigners();
    const POB = await ethers.getContractFactory("ProofOfBehavior");
    const pob = await POB.deploy(deployer.address, 7000);
    await pob.waitForDeployment();

    const fingerprint = ethers.hexlify(ethers.randomBytes(32));
    await expect(
      pob.connect(attacker).mint(wallet.address, 8000, fingerprint, 100)
    ).to.be.revertedWith("ProofOfBehavior: caller is not the oracle service");
  });
});

describe("TuringLib", function () {
  it("Should be deployable", async function () {
    const Lib = await ethers.getContractFactory("TuringLib");
    const lib = await Lib.deploy();
    await lib.waitForDeployment();
    expect(await lib.getAddress()).to.be.properAddress;
  });
});
