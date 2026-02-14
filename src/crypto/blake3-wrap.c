// Fast BLAKE3 wrapper — inlined for FORTRESS.sh
#include <stdio.h>
#include <stdlib.h>
#include "blake3.h"

int main(int argc, char**argv) {
  blake3_hasher h;
  blake3_hasher_init(&h);
  // read stdin → hash → stdout
  uint8_t buf[1024];
  size_t n;
  while ((n = fread(buf, 1, sizeof(buf), stdin))) blake3_hasher_update(&h, buf, n);
  uint8_t out[BLAKE3_OUT_LEN];
  blake3_hasher_finalize(&h, out, BLAKE3_OUT_LEN);
  fwrite(out, 1, BLAKE3_OUT_LEN, stdout);
}