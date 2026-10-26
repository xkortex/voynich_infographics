// Rasterize the vector originals. Host fonts can affect PNG text rendering.
const fs = require("node:fs");
const path = require("node:path");
const sharp = require("sharp");

function outputDirectory(cliArguments) {
  if (cliArguments.length === 0) {
    return path.resolve(__dirname, "../../generated");
  }
  if (cliArguments.length !== 2 || cliArguments[0] !== "--output-dir") {
    throw new Error("Usage: node render_pngs.cjs [--output-dir DIR]");
  }
  return path.resolve(cliArguments[1]);
}

async function renderCharts(directory) {
  const chartNames = ["voynich_eva_word_positions", "word_length_comparison"];
  for (const name of chartNames) {
    const svg = fs.readFileSync(path.join(directory, name + ".svg"));
    const destination = path.join(directory, name + ".png");
    await sharp(svg).png().toFile(destination);
    console.log("Rendered " + name + ".png");
  }
}

async function main() {
  const directory = outputDirectory(process.argv.slice(2));
  await renderCharts(directory);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
