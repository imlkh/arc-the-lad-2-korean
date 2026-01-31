import struct
from PIL import Image

data = open('COMM.IMG', 'rb').read()
row_width = 896
left_bytes = 384   # 4bpp region: 384 bytes = 768 pixels
right_pixels = 256  # 16-bit region: 512 bytes = 256 pixels

img = Image.new('RGB', (768 + 256, 512), (0, 0, 0))
pix = img.load()

for y in range(512):
    # Left: 4bpp indexed (grayscale without runtime CLUT)
    for xb in range(left_bytes):
        offset = y * row_width + xb
        byte = data[offset]
        lo = (byte & 0x0F) * 17
        hi = ((byte >> 4) & 0x0F) * 17
        pix[xb * 2, y] = (lo, lo, lo)
        pix[xb * 2 + 1, y] = (hi, hi, hi)

    # Right: 16-bit RGB555
    for x in range(right_pixels):
        offset = y * row_width + left_bytes + x * 2
        val = struct.unpack_from('<H', data, offset)[0]
        r = (val & 0x1F) << 3
        g = ((val >> 5) & 0x1F) << 3
        b = ((val >> 10) & 0x1F) << 3
        pix[768 + x, y] = (r, g, b)

img.save('python/COMM_IMG.png')