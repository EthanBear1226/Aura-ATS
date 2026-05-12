const fs = require('fs');
const { PNG } = require('pngjs');

const data = fs.readFileSync('candidates_ss.png');
const png = PNG.sync.read(data);

let bluePixels = 0;
let darkPixels = 0;
for (let y = 20; y < 40; y++) {
    for (let x = 0; x < 64; x++) {
        let idx = (png.width * y + x) << 2;
        let r = png.data[idx];
        let g = png.data[idx+1];
        let b = png.data[idx+2];
        if (r < 50 && g > 100 && b > 200) bluePixels++;
        if (r < 40 && g < 40 && b < 40) darkPixels++;
    }
}
console.log('Blue pixels in logo area:', bluePixels);
console.log('Dark pixels in logo area:', darkPixels);
