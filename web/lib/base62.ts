const ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ";

export function base62Encode(input: string): string {
  const bytes = new TextEncoder().encode(input);
  let value = BigInt(0);
  for (const b of bytes) {
    value = (value << BigInt(8)) + BigInt(b);
  }
  if (value === BigInt(0)) return "0";
  let output = "";
  while (value > 0) {
    const rem = Number(value % BigInt(62));
    output = ALPHABET[rem] + output;
    value = value / BigInt(62);
  }
  return output;
}

export function base62Decode(input: string): string {
  let value = BigInt(0);
  for (const ch of input) {
    const idx = ALPHABET.indexOf(ch);
    if (idx === -1) throw new Error("Invalid base62 character");
    value = value * BigInt(62) + BigInt(idx);
  }
  // Convert BigInt back to bytes
  const bytes: number[] = [];
  while (value > 0) {
    bytes.unshift(Number(value & BigInt(0xff)));
    value = value >> BigInt(8);
  }
  return new TextDecoder().decode(new Uint8Array(bytes));
}
