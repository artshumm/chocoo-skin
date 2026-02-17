const PHONE_REGEX = /^\+\d{7,15}$/;
const INSTAGRAM_ALLOWED = /[^@A-Za-z0-9_.]/g;

export function formatPhone(raw: string): string {
  if (!raw.startsWith("+")) raw = "+" + raw.replace(/^\+*/, "");
  const digits = raw.slice(1).replace(/\D/g, "");
  return "+" + digits.slice(0, 15);
}

export function isPhoneValid(phone: string): boolean {
  return PHONE_REGEX.test(phone);
}

export function formatInstagram(raw: string): string {
  let v = raw.replace(INSTAGRAM_ALLOWED, "");
  if (v && !v.startsWith("@")) v = "@" + v;
  return v.slice(0, 31);
}
