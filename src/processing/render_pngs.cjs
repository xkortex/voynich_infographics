// SVGs remain the vector originals. PNGs are raster exports; fonts may vary by OS.
const path=require('node:path'),fs=require('node:fs');
const sharp=require('sharp');
const args=process.argv.slice(2);
if(args.length && (args.length!==2 || args[0]!=='--output-dir'))throw Error('Usage: node render_pngs.cjs [--output-dir DIR]');
const root=args.length?path.resolve(args[1]):path.resolve(__dirname,'../../generated');
(async()=>{for(const name of ['voynich_eva_word_positions','word_length_comparison']){await sharp(fs.readFileSync(path.join(root,name+'.svg'))).png().toFile(path.join(root,name+'.png'));console.log('Rendered '+name+'.png')}})().catch(e=>{console.error(e);process.exit(1)});
