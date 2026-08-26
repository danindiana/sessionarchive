import * as esbuild from "esbuild";

await esbuild.build({
  entryPoints: ["src/app.js"],
  bundle: true,
  minify: true,
  format: "iife",
  outfile: "dist/cosmos_bundle.js",
});

console.log("Built dist/cosmos_bundle.js");
